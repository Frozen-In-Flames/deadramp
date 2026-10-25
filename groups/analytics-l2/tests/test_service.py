"""REST API service tests.

Traces to: UNION-SPEC Core function 8 (API access) / ranking row 16
(API access, 12 siblings), plus functions 9 (Access control) and 10
(Audit log) as enforced over HTTP; Implementation contract for
``analytics/service.py``: make_server(host, port, store, audit, users),
auth via X-User / X-Role headers matched against the registry, errors
as JSON {error} with 400/401/403/404, denied attempts audited.
"""

import csv
import http.client
import io
import json
import threading
import unittest

from analytics_helpers import USERS_REGISTRY, sales_csv_text, sales_json_text
from analytics.audit import AuditLog
from analytics.service import make_server
from analytics.store import DatasetStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "analyst"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}


class ServiceBase(unittest.TestCase):
    """Spin a real server on an ephemeral port; talk real HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = DatasetStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(USERS_REGISTRY)
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    # -- low-level helpers -------------------------------------------------
    def request(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = None
        hdrs = dict(headers or {})
        if body is not None:
            payload = json.dumps(body)
            hdrs.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        ctype = resp.getheader("Content-Type") or ""
        conn.close()
        parsed = None
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            parsed = None
        return status, ctype, raw.decode("utf-8", "replace"), parsed

    def create_dataset(self, name, headers=None, fmt="json", data=None):
        status, _, _, parsed = self.request(
            "POST",
            "/datasets",
            headers=headers or BOB,
            body={
                "name": name,
                "format": fmt,
                "data": data if data is not None else sales_json_text(),
            },
        )
        self.assertIn(status, (200, 201), "dataset creation failed")
        self.assertIsInstance(parsed, dict)
        return parsed


class TestHealthAndAuth(ServiceBase):
    """Core: API access — health, header auth, and error envelope."""

    def test_health_endpoint(self):
        """Core: API access. Contract: GET /health succeeds."""
        status, _, _, _ = self.request("GET", "/health")
        self.assertEqual(status, 200)

    def test_missing_auth_headers_is_401(self):
        """Core: API access + Access control (IA-2). No X-User/X-Role
        headers -> 401 with a JSON {error} body."""
        status, _, _, parsed = self.request("GET", "/datasets")
        self.assertEqual(status, 401)
        self.assertIsInstance(parsed, dict)
        self.assertIn("error", parsed)

    def test_unknown_user_is_401(self):
        """Core: API access (IA-2). A user outside the registry is not
        authenticated."""
        status, _, _, parsed = self.request(
            "GET", "/datasets",
            headers={"X-User": "mallory", "X-Role": "admin"},
        )
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_role_header_must_match_registry(self):
        """Core: API access (IA-2). Contract: 'role must match the
        registry' — alice claiming viewer (or bob claiming admin) is
        rejected."""
        for headers in ({"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"}):
            with self.subTest(headers=headers):
                status, _, _, parsed = self.request("GET", "/datasets",
                                                    headers=headers)
                self.assertIn(status, (401, 403))
                self.assertIn("error", parsed)

    def test_unknown_path_is_404_json(self):
        """Core: API access. Unknown routes return JSON {error} 404."""
        status, _, _, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)


class TestDatasetEndpoints(ServiceBase):
    """Core: API access over Ingest / Storage / Query / Describe."""

    def test_create_list_and_get_dataset(self):
        """Core: API access + Storage. POST /datasets registers a
        dataset; GET /datasets lists it; GET /datasets/{id} returns it."""
        ds = self.create_dataset("svc-basic")
        self.assertTrue(str(ds["id"]).startswith("ds-"))
        self.assertEqual(ds["name"], "svc-basic")
        self.assertEqual(ds["row_count"], 5)

        status, _, _, listing = self.request("GET", "/datasets",
                                             headers=ALICE)
        self.assertEqual(status, 200)
        items = listing["datasets"] if isinstance(listing, dict) else listing
        self.assertIn(ds["id"], [d["id"] for d in items])

        status, _, _, got = self.request(
            "GET", "/datasets/%s" % ds["id"], headers=CAROL
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["id"], ds["id"])
        self.assertEqual(got["row_count"], 5)

    def test_create_dataset_from_csv(self):
        """Core: API access + Ingest. POST /datasets accepts format=csv."""
        ds = self.create_dataset(
            "svc-csv", fmt="csv", data=sales_csv_text()
        )
        self.assertEqual(ds["columns"], ["region", "product", "units",
                                         "revenue"])
        self.assertEqual(ds["row_count"], 5)

    def test_get_unknown_dataset_is_404(self):
        """Core: API access. Unknown dataset id -> 404 JSON {error}."""
        status, _, _, parsed = self.request(
            "GET", "/datasets/ds-999999", headers=ALICE
        )
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)

    def test_malformed_dataset_payload_is_400_and_stores_nothing(self):
        """Core: API access + Ingest (SI-10). Malformed data -> 400, and
        the registry is unchanged."""
        _, _, _, before = self.request("GET", "/datasets", headers=ALICE)
        before_items = (before["datasets"] if isinstance(before, dict)
                        else before)
        status, _, _, parsed = self.request(
            "POST", "/datasets", headers=BOB,
            body={"name": "svc-bad", "format": "json", "data": "{oops"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        _, _, _, after = self.request("GET", "/datasets", headers=ALICE)
        after_items = (after["datasets"] if isinstance(after, dict)
                       else after)
        self.assertEqual(len(after_items), len(before_items))

    def test_unsupported_format_is_400(self):
        """Core: API access + Ingest. format is csv|json only."""
        status, _, _, parsed = self.request(
            "POST", "/datasets", headers=BOB,
            body={"name": "svc-xml", "format": "xml", "data": "<x/>"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_query_endpoint_runs_a_query(self):
        """Core: API access + Query. POST /datasets/{id}/query returns
        {columns, rows, row_count} for the posted query."""
        ds = self.create_dataset("svc-query")
        status, _, _, result = self.request(
            "POST", "/datasets/%s/query" % ds["id"], headers=CAROL,
            body={"where": [{"column": "region", "op": "eq",
                            "value": "north"}]},
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["row_count"], 3)
        self.assertIn("columns", result)
        self.assertIn("rows", result)

    def test_query_endpoint_grouped_aggregate(self):
        """Core: API access + Descriptive statistics. Grouped aggregates
        work over HTTP."""
        ds = self.create_dataset("svc-agg")
        status, _, _, result = self.request(
            "POST", "/datasets/%s/query" % ds["id"], headers=BOB,
            body={
                "group_by": ["region"],
                "aggregates": [{"func": "sum", "column": "units",
                                "alias": "total"}],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["row_count"], 2)
        rows = result["rows"]
        dicts = (rows if rows and isinstance(rows[0], dict)
                 else [dict(zip(result["columns"], r)) for r in rows])
        totals = {r["region"]: r["total"] for r in dicts}
        self.assertEqual(totals, {"north": 90, "south": 60})

    def test_query_on_unknown_dataset_is_404(self):
        """Core: API access + Query. Querying a missing dataset -> 404."""
        status, _, _, parsed = self.request(
            "POST", "/datasets/ds-999999/query", headers=BOB, body={}
        )
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)

    def test_invalid_query_is_400(self):
        """Core: API access + Query (SI-10). A query naming a bogus
        column -> 400 JSON {error}."""
        ds = self.create_dataset("svc-badquery")
        status, _, _, parsed = self.request(
            "POST", "/datasets/%s/query" % ds["id"], headers=BOB,
            body={"where": [{"column": "nope", "op": "eq", "value": 1}]},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_describe_endpoint(self):
        """Core: API access + Descriptive statistics.
        POST /datasets/{id}/describe {column} returns the stats dict."""
        ds = self.create_dataset("svc-describe")
        status, _, _, out = self.request(
            "POST", "/datasets/%s/describe" % ds["id"], headers=BOB,
            body={"column": "units"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(out["column"], "units")
        self.assertEqual(out["count"], 5)
        self.assertAlmostEqual(float(out["mean"]), 30.0, places=6)
        self.assertEqual(out["max"], 50)


class TestExportAndChartEndpoints(ServiceBase):
    """Core: API access over Export and Visualization."""

    def test_export_csv(self):
        """Core: API access + Export. GET /datasets/{id}/export?
        format=csv returns CSV text of the dataset."""
        ds = self.create_dataset("svc-export-csv")
        status, _, text, _ = self.request(
            "GET", "/datasets/%s/export?format=csv" % ds["id"],
            headers=CAROL,
        )
        self.assertEqual(status, 200)
        parsed = list(csv.reader(io.StringIO(text)))
        self.assertEqual(parsed[0], ["region", "product", "units",
                                     "revenue"])
        self.assertEqual(len(parsed), 1 + 5)

    def test_export_json(self):
        """Core: API access + Export. format=json returns JSON rows."""
        ds = self.create_dataset("svc-export-json")
        status, _, text, parsed = self.request(
            "GET", "/datasets/%s/export?format=json" % ds["id"],
            headers=BOB,
        )
        self.assertEqual(status, 200)
        payload = parsed if parsed is not None else json.loads(text)
        rows = payload["rows"] if isinstance(payload, dict) else payload
        dicts = (rows if rows and isinstance(rows[0], dict)
                 else [dict(zip(["region", "product", "units", "revenue"],
                                r)) for r in rows])
        self.assertEqual(len(dicts), 5)
        self.assertEqual(
            sorted(float(r["units"]) for r in dicts),
            [10.0, 20.0, 30.0, 40.0, 50.0],
        )

    def test_export_bad_format_is_400(self):
        """Core: API access + Export. format is csv|json only."""
        ds = self.create_dataset("svc-export-bad")
        status, _, _, parsed = self.request(
            "GET", "/datasets/%s/export?format=yaml" % ds["id"],
            headers=BOB,
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_chart_endpoint_returns_svg(self):
        """Core: API access + Visualization. GET /datasets/{id}/chart?
        kind=&label=&value= returns a standalone SVG."""
        ds = self.create_dataset("svc-chart")
        status, _, text, _ = self.request(
            "GET",
            "/datasets/%s/chart?kind=bar&label=region&value=units"
            % ds["id"],
            headers=CAROL,
        )
        self.assertEqual(status, 200)
        self.assertIn("<svg", text)
        self.assertTrue(text.strip().endswith("</svg>"))

    def test_chart_endpoint_bad_kind_is_400(self):
        """Core: API access + Visualization (SI-10). Unknown chart kind
        -> 400."""
        ds = self.create_dataset("svc-chart-bad")
        status, _, _, parsed = self.request(
            "GET",
            "/datasets/%s/chart?kind=radar&label=region&value=units"
            % ds["id"],
            headers=BOB,
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)


class TestServiceAccessControlAndAudit(ServiceBase):
    """Core: API access — permission enforcement and audit over HTTP."""

    def test_viewer_cannot_ingest(self):
        """Core: Access control (AC-3). Viewer POST /datasets -> 403
        JSON {error}."""
        status, _, _, parsed = self.request(
            "POST", "/datasets", headers=CAROL,
            body={"name": "svc-denied", "format": "json",
                  "data": sales_json_text()},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_analyst_cannot_read_audit(self):
        """Core: Access control + Audit log (AU-6). audit_read is
        admin-only: analyst GET /audit -> 403."""
        status, _, _, parsed = self.request("GET", "/audit", headers=BOB)
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_viewer_cannot_read_audit(self):
        """Core: Access control + Audit log. Viewer GET /audit -> 403."""
        status, _, _, parsed = self.request("GET", "/audit", headers=CAROL)
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_admin_reads_audit_and_sees_activity(self):
        """Core: Audit log. GET /audit (admin) returns the recorded
        entries with actor/action/target."""
        self.create_dataset("svc-audited")
        status, _, _, entries = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        items = (entries["entries"] if isinstance(entries, dict)
                 else entries)
        self.assertIsInstance(items, list)
        self.assertTrue(items)
        for entry in items:
            for key in ("ts", "actor", "action", "target"):
                self.assertIn(key, entry)
        self.assertTrue(any(e["actor"] == "bob" for e in items))

    def test_denied_attempt_is_audited(self):
        """Core: Audit log. Contract: 'Denied attempts are audited' —
        after carol's 403, the trail contains an entry for carol."""
        _, _, _, before = self.request("GET", "/audit", headers=ALICE)
        before_items = (before["entries"] if isinstance(before, dict)
                        else before)
        carol_before = [e for e in before_items if e["actor"] == "carol"]

        status, _, _, _ = self.request(
            "POST", "/datasets", headers=CAROL,
            body={"name": "svc-denied-audit", "format": "json",
                  "data": sales_json_text()},
        )
        self.assertEqual(status, 403)

        _, _, _, after = self.request("GET", "/audit", headers=ALICE)
        after_items = (after["entries"] if isinstance(after, dict)
                       else after)
        carol_after = [e for e in after_items if e["actor"] == "carol"]
        self.assertGreater(len(carol_after), len(carol_before))


if __name__ == "__main__":
    unittest.main()
