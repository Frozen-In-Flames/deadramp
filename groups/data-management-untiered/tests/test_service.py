"""REST API service tests.

Traces to: Core function -- REST API; contract for
``datamgmt/service.py``: make_server(host, port, store, audit, users),
auth via X-User / X-Role against USERS {alice:admin, bob:steward,
carol:viewer}, errors JSON {error} 400/401/403/404, creates 201,
GET /health unauthenticated, GET /audit admin-only (audit_read),
list wrappers {"datasets": [...]}, {"sources": [...]},
{"grants": [...]} etc. Routes are the service's dataset-nested
resources: /datasets/{id}/ingestions, /datasets/{id}/quality-rules,
/quality-rules/{id}/checks, /datasets/{id}/access-requests,
/access-requests/{id}/decide, /datasets/{id}/retention-policy,
/retention-due, /datasets/{id}/exports.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from datamgmt_helpers import USERS
from datamgmt.audit import AuditLog
from datamgmt.service import make_server
from datamgmt.store import DataMgmtStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "steward"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}


class ServiceBase(unittest.TestCase):
    """Core: REST API -- real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = DataMgmtStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit, dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, headers=None, body=None):
        """Core: REST API -- helper performing a real HTTP request."""
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
        conn.close()
        text = raw.decode("utf-8", "replace")
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        return status, text, parsed

    def make_dataset(self, name="Claims Extract", headers=None):
        """Core: REST API -- helper creating a dataset via POST /datasets."""
        status, _, parsed = self.request(
            "POST", "/datasets", headers=headers or BOB,
            body={
                "name": name, "description": "Nightly extract of claims records",
                "classification": "cui", "tags": ["claims", "nightly"],
                "schema": [
                    {"name": "patient_id", "type": "string", "required": True, "sensitive": True},
                    {"name": "amount", "type": "number", "required": True, "sensitive": False},
                ],
            },
        )
        self.assertEqual(status, 201)
        return parsed


class TestHealthAuth(ServiceBase):
    """Core: REST API -- health and header auth."""

    def test_health(self):
        """Core: REST API. GET /health -> {status: ok} with no auth."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_unknown_user_401(self):
        """Core: REST API (IA-2). Unknown user -> 401 JSON error envelope."""
        status, _, parsed = self.request(
            "GET", "/datasets", headers={"X-User": "mallory", "X-Role": "admin"}
        )
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_role_mismatch_401(self):
        """Core: REST API (IA-2). Role header mismatching the registry -> 401."""
        for headers in ({"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {"X-User": "carol", "X-Role": "steward"},
                        {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/datasets", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """Core: REST API. Unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core: REST API -- full data-management flow over HTTP."""

    def test_full_flow(self):
        """Core: REST API. dataset -> source -> ingestion -> quality rule -> check -> access request (carol) -> decide (bob) -> grants -> retention -> retention-due -> export -> search -> audit (alice)."""
        dataset = self.make_dataset(name="Flow-%s" % self.id())
        self.assertTrue(dataset["id"].startswith("ds-"))

        status, _, listing = self.request("GET", "/datasets", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn(dataset["id"], [d["id"] for d in listing["datasets"]])
        status, _, one = self.request("GET", "/datasets/%s" % dataset["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(one["id"], dataset["id"])

        status, _, source = self.request(
            "POST", "/sources", headers=BOB,
            body={"name": "ehr-feed", "kind": "api", "location": "ehr.internal"},
        )
        self.assertEqual(status, 201)
        status, _, sources = self.request("GET", "/sources", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn("sources", sources)

        status, _, ing = self.request(
            "POST", "/datasets/%s/ingestions" % dataset["id"], headers=BOB,
            body={"source_id": source["id"],
                  "mode": "full", "record_count": 42, "status": "completed"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(ing["record_count"], 42)

        status, _, rule = self.request(
            "POST", "/datasets/%s/quality-rules" % dataset["id"], headers=BOB,
            body={"name": "pid-complete",
                  "kind": "completeness", "field": "patient_id"},
        )
        self.assertEqual(status, 201)

        status, _, check = self.request(
            "POST", "/quality-rules/%s/checks" % rule["id"], headers=BOB,
            body={"records": [{"patient_id": "P1"}, {"patient_id": None}]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(check["records_checked"], 2)
        self.assertEqual(check["violations"], 1)
        self.assertFalse(check["passed"])

        # Access: carol (viewer) may request; bob (steward) decides.
        status, _, req = self.request(
            "POST", "/datasets/%s/access-requests" % dataset["id"], headers=CAROL,
            body={"purpose": "research use", "duration_days": 10},
        )
        self.assertEqual(status, 201)
        self.assertEqual(req["status"], "requested")
        self.assertEqual(req["requester"], "carol")

        status, _, decided = self.request(
            "POST", "/access-requests/%s/decide" % req["id"], headers=BOB,
            body={"approve": True},
        )
        self.assertEqual(status, 200)
        self.assertEqual(decided["status"], "approved")
        self.assertIsNotNone(decided["grant_id"])

        status, _, grants = self.request("GET", "/grants", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn(decided["grant_id"], [g["id"] for g in grants["grants"]])

        status, _, policy = self.request(
            "POST", "/datasets/%s/retention-policy" % dataset["id"], headers=BOB,
            body={"retention_days": 365, "disposition": "archive"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(policy["dataset_id"], dataset["id"])

        status, text, due = self.request("GET", "/retention-due", headers=BOB)
        self.assertEqual(status, 200)
        # A 365-day policy on a just-created dataset is not due yet.
        self.assertNotIn(dataset["id"], [e["dataset_id"] for e in due["due"]])

        status, _, manifest = self.request(
            "POST", "/datasets/%s/exports" % dataset["id"], headers=BOB,
            body={"format": "json",
                  "records": [{"patient_id": "P1", "amount": 10}]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(manifest["record_count"], 1)
        self.assertTrue(manifest["checksum"])

        query = urllib.parse.urlencode({"q": "ehr-feed"})
        status, _, result = self.request("GET", "/search?%s" % query, headers=BOB)
        self.assertEqual(status, 200)
        self.assertIn("datasets", result)
        self.assertIn("sources", result)
        self.assertIn("quality_rules", result)
        self.assertTrue(result["sources"])

        status, _, audit_payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", audit_payload)
        self.assertTrue(audit_payload["entries"])

    def test_audit_steward_and_viewer_forbidden(self):
        """Core: REST API / Audit (AU-6). GET /audit -> 403 for steward and viewer (audit_read is admin-only)."""
        for headers in (BOB, CAROL):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/audit", headers=headers)
                self.assertEqual(status, 403)
                self.assertIn("error", parsed)


class TestServiceAccessAndErrors(ServiceBase):
    """Core: REST API -- 400/403/404 and denied-audit behaviour."""

    def test_viewer_dataset_create_403_and_denied_audited(self):
        """Core: REST API / Audit. Viewer POST /datasets -> 403, and a '<action>:denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request(
            "POST", "/datasets", headers=CAROL,
            body={"name": "X", "description": "x"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_validation_400(self):
        """Core: REST API (SI-10). Bad dataset (bad classification) -> 400 JSON error."""
        status, _, parsed = self.request(
            "POST", "/datasets", headers=BOB,
            body={"name": "Bad", "description": "x", "classification": "secret"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)

    def test_not_found_404(self):
        """Core: REST API. Unknown dataset id -> 404 JSON error."""
        status, _, parsed = self.request("GET", "/datasets/ds-999999", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)


if __name__ == "__main__":
    unittest.main()
