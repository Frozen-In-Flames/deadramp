"""REST API service tests.

Traces to: UNION-SPEC Core function 9 (API access) plus functions 10
(Access control) and 11 (Audit log) as enforced over HTTP;
Implementation contract for ``cyber/service.py``:
make_server(host, port, store, audit, users), auth via X-User / X-Role
headers matched against the registry, errors as JSON {error} with
400/401/403/404, denied attempts audited with the action name suffixed
``:denied``.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from cyber_helpers import USERS_REGISTRY
from cyber.audit import AuditLog
from cyber.service import make_server
from cyber.store import CyberStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "analyst"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}


class ServiceBase(unittest.TestCase):
    """Spin a real server on an ephemeral port; talk real HTTP."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CyberStore(audit=cls.audit)
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

    # -- low-level helper --------------------------------------------------
    def request(self, method, path, headers=None, body=None):
        """One raw HTTP request; returns (status, text, parsed_json)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port,
                                          timeout=10)
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

    # -- flow helpers --------------------------------------------------------
    def create_asset(self, name, criticality="critical", headers=None):
        """POST /assets as bob (analyst) and assert 201."""
        status, _, parsed = self.request(
            "POST", "/assets", headers=headers or BOB,
            body={"name": name, "kind": "server", "owner": "it-ops",
                  "criticality": criticality},
        )
        self.assertEqual(status, 201, "asset creation failed")
        self.assertIsInstance(parsed, dict)
        return parsed

    def create_finding(self, asset_id, title="http finding",
                       severity="critical", headers=None, **extra):
        """POST /findings as bob (analyst) and assert 201."""
        body = {"title": title, "severity": severity,
                "asset_id": asset_id, "source": "scanner"}
        body.update(extra)
        status, _, parsed = self.request(
            "POST", "/findings", headers=headers or BOB, body=body
        )
        self.assertEqual(status, 201, "finding creation failed")
        return parsed


class TestHealthAndAuth(ServiceBase):
    """Core: API access — health, header auth, and error envelope."""

    def test_health_endpoint_needs_no_auth(self):
        """Core: API access. Contract: GET /health (no auth) ->
        {"status": "ok"}."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_missing_auth_headers_is_401(self):
        """Core: API access + Access control (IA-2). No X-User/X-Role
        headers -> 401 with a JSON {error} body."""
        status, _, parsed = self.request("GET", "/assets")
        self.assertEqual(status, 401)
        self.assertIsInstance(parsed, dict)
        self.assertIn("error", parsed)

    def test_unknown_user_is_401(self):
        """Core: API access (IA-2). Contract: an unknown user -> 401."""
        status, _, parsed = self.request(
            "GET", "/assets",
            headers={"X-User": "mallory", "X-Role": "admin"},
        )
        self.assertEqual(status, 401)
        self.assertIn("error", parsed)

    def test_role_mismatch_is_401(self):
        """Core: API access (IA-2). Contract: 'the role must match the
        registry' — a mismatched X-Role -> 401 (alice claiming viewer,
        bob claiming admin, carol claiming analyst)."""
        for headers in ({"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {"X-User": "carol", "X-Role": "analyst"}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/assets",
                                                 headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_is_404_json_without_stack_trace(self):
        """Core: API access. Unknown routes return JSON {error} 404,
        and 'no stack trace is ever returned'."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core: API access — the whole security-operations surface."""

    def test_full_flow_asset_to_audit(self):
        """Core: API access + Asset inventory / Finding ingestion /
        Lifecycle / Risk register / Control mapping / Posture / Search
        / Audit. Full flow: asset -> finding -> bulk -> CSV ->
        transition -> assign -> risk -> risk transition -> control
        assess -> posture -> search -> audit, with audit_read
        forbidden for analyst and allowed for admin."""
        asset = self.create_asset("srv-01")
        asset_id = asset["id"]
        self.assertTrue(asset_id.startswith("asset-"))
        self.assertEqual(asset["created_by"], "bob")

        status, _, got = self.request(
            "GET", "/assets/%s" % asset_id, headers=CAROL
        )
        self.assertEqual(status, 200)
        self.assertEqual(got["id"], asset_id)

        finding = self.create_finding(
            asset_id, title="Flow critical hole", severity="critical",
            control_ids=["RA-5"],
        )
        finding_id = finding["id"]
        self.assertTrue(finding_id.startswith("find-"))
        self.assertEqual((finding["score"], finding["band"]),
                         (10.0, "critical"))
        self.assertEqual(finding["status"], "new")

        status, _, payload = self.request(
            "POST", "/findings/bulk", headers=BOB,
            body={"findings": [
                {"title": "Bulk one", "severity": "high",
                 "asset_id": asset_id, "source": "scanner"},
                {"title": "Bulk two", "severity": "low",
                 "asset_id": asset_id, "source": "scanner"},
            ]},
        )
        self.assertEqual(status, 201)
        bulk = payload["findings"]
        self.assertEqual(len(bulk), 2)

        csv_text = (
            "title,severity,asset_id,source,description,cve,control_ids\n"
            "CSV hole,medium,%s,nessus,,,SI-2\n" % asset_id
        )
        status, _, payload = self.request(
            "POST", "/findings/csv", headers=BOB, body={"csv": csv_text}
        )
        self.assertEqual(status, 201)
        self.assertEqual(len(payload["findings"]), 1)
        self.assertEqual(payload["findings"][0]["control_ids"], ["SI-2"])

        status, _, updated = self.request(
            "POST", "/findings/%s/transition" % finding_id, headers=BOB,
            body={"status": "triaged"},
        )
        self.assertIn(status, (200, 201))
        self.assertEqual(updated["status"], "triaged")

        status, _, updated = self.request(
            "POST", "/findings/%s/assign" % finding_id, headers=BOB,
            body={"assignee": "bob"},
        )
        self.assertIn(status, (200, 201))
        self.assertEqual(updated["assignee"], "bob")

        status, _, risk = self.request(
            "POST", "/risks", headers=BOB,
            body={"title": "Flow risk", "description": "flow exposure",
                  "likelihood": 4, "impact": 5, "owner": "ciso",
                  "finding_ids": [finding_id]},
        )
        self.assertEqual(status, 201)
        risk_id = risk["id"]
        self.assertTrue(risk_id.startswith("risk-"))
        self.assertEqual((risk["score"], risk["band"]), (20, "critical"))

        status, _, updated = self.request(
            "POST", "/risks/%s/transition" % risk_id, headers=BOB,
            body={"status": "monitoring"},
        )
        self.assertIn(status, (200, 201))
        self.assertEqual(updated["status"], "monitoring")

        status, _, control = self.request(
            "POST", "/controls/RA-5/assess", headers=BOB,
            body={"status": "implemented", "evidence": "scan schedule"},
        )
        self.assertIn(status, (200, 201))
        self.assertEqual(control["status"], "implemented")
        self.assertEqual(control["finding_count"], 1)

        status, _, summary = self.request("GET", "/posture", headers=CAROL)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(summary["findings"]["total"], 4)
        self.assertEqual(summary["controls"]["implemented"], 1)

        query = urllib.parse.urlencode({"q": "flow"})
        status, _, result = self.request(
            "GET", "/search?%s" % query, headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            [f["id"] for f in result["findings"]], [finding_id]
        )
        self.assertEqual([r["id"] for r in result["risks"]], [risk_id])
        self.assertEqual(result["assets"], [])

        status, _, parsed = self.request("GET", "/audit", headers=BOB)
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        entries = payload["entries"]
        self.assertIsInstance(entries, list)
        self.assertTrue(entries)
        for entry in entries:
            for key in ("ts", "actor", "action", "target"):
                self.assertIn(key, entry)
        actions = [e["action"] for e in entries]
        for expected in (
            "asset_create", "finding_ingest", "finding_transition",
            "finding_assign", "risk_create", "risk_transition",
            "control_assess", "search",
        ):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)

    def test_list_and_filter_endpoints(self):
        """Core: API access + Search & filtering. GET /assets?q=,
        GET /findings with severity/asset filters, GET /risks?status=
        and GET /controls all answer with their contract wrappers."""
        asset = self.create_asset("listable-server")
        finding = self.create_finding(asset["id"], title="Listable hole")

        status, _, payload = self.request(
            "GET", "/assets?q=listable", headers=CAROL
        )
        self.assertEqual(status, 200)
        self.assertEqual([a["id"] for a in payload["assets"]],
                         [asset["id"]])

        query = urllib.parse.urlencode(
            {"severity": "critical", "asset_id": asset["id"]}
        )
        status, _, payload = self.request(
            "GET", "/findings?%s" % query, headers=BOB
        )
        self.assertEqual(status, 200)
        self.assertIn(finding["id"],
                      [f["id"] for f in payload["findings"]])
        for item in payload["findings"]:
            self.assertEqual(item["severity"], "critical")
            self.assertEqual(item["asset_id"], asset["id"])

        status, _, risk = self.request(
            "POST", "/risks", headers=BOB,
            body={"title": "Listable risk", "description": "d",
                  "likelihood": 3, "impact": 3},
        )
        self.assertEqual(status, 201)
        status, _, payload = self.request(
            "GET", "/risks?status=open", headers=CAROL
        )
        self.assertEqual(status, 200)
        self.assertIn(risk["id"], [r["id"] for r in payload["risks"]])

        status, _, payload = self.request("GET", "/controls",
                                          headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["controls"]), 34)

    def test_asset_update_endpoint(self):
        """Core: API access + Asset inventory. POST /assets/{id}/update
        changes the owner and returns the updated asset."""
        asset = self.create_asset("updatable-server")
        status, _, updated = self.request(
            "POST", "/assets/%s/update" % asset["id"], headers=BOB,
            body={"owner": "sec-ops"},
        )
        self.assertIn(status, (200, 201))
        self.assertEqual(updated["owner"], "sec-ops")

    def test_get_unknown_asset_and_finding_are_404(self):
        """Core: API access. Unknown asset/finding ids -> 404 JSON
        {error}."""
        for path in ("/assets/asset-999999", "/findings/find-999999",
                     "/risks/risk-999999"):
            with self.subTest(path=path):
                status, _, parsed = self.request("GET", path,
                                                 headers=ALICE)
                self.assertEqual(status, 404)
                self.assertIn("error", parsed)

    def test_invalid_asset_body_is_400(self):
        """Core: API access + Asset inventory (SI-10). An asset with an
        unknown kind -> 400 JSON {error}, no stack trace."""
        status, text, parsed = self.request(
            "POST", "/assets", headers=BOB,
            body={"name": "bad", "kind": "toaster", "owner": "it-ops",
                  "criticality": "high"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)

    def test_invalid_transition_is_400(self):
        """Core: API access + Finding lifecycle. A forbidden transition
        (new -> closed) over HTTP -> 400 JSON {error}."""
        asset = self.create_asset("lifecycle-server")
        finding = self.create_finding(asset["id"])
        status, _, parsed = self.request(
            "POST", "/findings/%s/transition" % finding["id"],
            headers=BOB, body={"status": "closed"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)


class TestServiceAccessControlAndAudit(ServiceBase):
    """Core: API access — permission enforcement and audit over HTTP."""

    def test_viewer_ingesting_a_finding_is_403(self):
        """Core: Access control (AC-3). A viewer POST /findings -> 403
        JSON {error} (viewer lacks ingest)."""
        asset = self.create_asset("viewer-ingest-server")
        status, _, parsed = self.request(
            "POST", "/findings", headers=CAROL,
            body={"title": "viewer attempt", "severity": "high",
                  "asset_id": asset["id"], "source": "scanner"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_viewer_cannot_create_an_asset_or_assess_a_control(self):
        """Core: Access control. Viewer POST /assets -> 403 (lacks
        manage_assets) and POST /controls/{id}/assess -> 403 (lacks
        assess_controls)."""
        status, _, parsed = self.request(
            "POST", "/assets", headers=CAROL,
            body={"name": "nope", "kind": "server", "owner": "x",
                  "criticality": "low"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        status, _, parsed = self.request(
            "POST", "/controls/AC-2/assess", headers=CAROL,
            body={"status": "implemented"},
        )
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_viewer_can_read(self):
        """Core: Access control. Viewer holds read: GET /assets,
        /findings, /controls, /posture all answer 200 for carol."""
        for path in ("/assets", "/findings", "/controls", "/posture",
                     "/risks"):
            with self.subTest(path=path):
                status, _, _ = self.request("GET", path, headers=CAROL)
                self.assertEqual(status, 200)

    def test_analyst_and_viewer_cannot_read_audit(self):
        """Core: Access control + Audit log (AU-6). audit_read is
        admin-only in the matrix: analyst and viewer GET /audit ->
        403."""
        for headers in (BOB, CAROL):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/audit",
                                                 headers=headers)
                self.assertEqual(status, 403)
                self.assertIn("error", parsed)

    def test_denied_ingest_appears_in_audit_with_denied_suffix(self):
        """Core: Audit log. Contract: 'denied attempts (401 and 403)
        are audited with the action name suffixed :denied' — after
        carol's 403 ingest attempt, admin's audit read contains a
        carol entry whose action ends with :denied."""
        asset = self.create_asset("denied-audit-server")

        def carol_denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            entries = payload["entries"]
            return len([
                e for e in entries
                if e["actor"] == "carol"
                and str(e["action"]).endswith(":denied")
            ])

        before = carol_denied_count()
        status, _, _ = self.request(
            "POST", "/findings", headers=CAROL,
            body={"title": "denied attempt", "severity": "high",
                  "asset_id": asset["id"], "source": "scanner"},
        )
        self.assertEqual(status, 403)
        self.assertGreater(carol_denied_count(), before)


if __name__ == "__main__":
    unittest.main()
