"""REST API service tests.

Traces to: Core function 10 -- REST API; contract for
``opsmgmt/service.py``: make_server(host, port, store, audit, users),
auth via X-User / X-Role against USERS {alice:admin, bob:operator,
carol:viewer}, errors JSON {error} 400/401/403/404, PermissionDenied
-> 403 with '<action>:denied' audit entry, audit_read admin-only,
?now= accepted on work-order and report endpoints.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from opsmgmt_helpers import USERS
from opsmgmt.audit import AuditLog
from opsmgmt.service import make_server
from opsmgmt.store import OpsStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "operator"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}

NOW = "2025-06-01T00:00:00Z"


class ServiceBase(unittest.TestCase):
    """Core 10: REST API -- real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = OpsStore(audit=cls.audit)
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
        """Core 10: REST API -- helper performing a real HTTP request."""
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


class TestHealthAuth(ServiceBase):
    """Core 10: REST API -- health and header auth."""

    def test_health(self):
        """Core 10: REST API. GET /health -> {status: ok} with no auth."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_401(self):
        """Core 10: REST API (IA-2). Unknown user or role mismatch -> 401 JSON error."""
        for headers in ({"X-User": "mallory", "X-Role": "admin"},
                        {"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/persons", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """Core 10: REST API. Unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core 10: REST API -- full operations flow over HTTP."""

    def test_full_flow(self):
        """Core 10: REST API. person -> org -> project+member -> asset -> work order -> assign/transition -> inspection -> usage -> workflow create/PATCH -> report/search -> audit, with ?now= derivation."""
        status, _, person = self.request(
            "POST", "/persons", headers=ALICE,
            body={"name": "Pat Person", "reference": "EXT-1001"})
        self.assertEqual(status, 201)
        self.assertTrue(person["id"].startswith("per-"))

        status, _, org = self.request(
            "POST", "/organizations", headers=BOB,
            body={"name": "Acme Vendor", "reference": "ORG-1001"})
        self.assertEqual(status, 201)
        self.assertTrue(org["id"].startswith("org-"))

        status, _, project = self.request(
            "POST", "/projects", headers=BOB,
            body={"name": "Alpha Project", "org_id": org["id"]})
        self.assertEqual(status, 201)
        self.assertTrue(project["id"].startswith("proj-"))
        status, _, project = self.request(
            "POST", "/projects/%s/members" % project["id"], headers=BOB,
            body={"person_id": person["id"]})
        self.assertEqual(status, 201)
        self.assertEqual(project["members"], [person["id"]])
        status, _, members = self.request(
            "GET", "/projects/%s/members" % project["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual([m["id"] for m in members["members"]], [person["id"]])

        status, _, asset = self.request(
            "POST", "/assets", headers=BOB,
            body={"name": "Pump Alpha", "kind": "pump", "project_id": project["id"]})
        self.assertEqual(status, 201)
        self.assertEqual(asset["status"], "in_service")
        status, _, asset_moved = self.request(
            "POST", "/assets/%s/transition" % asset["id"], headers=BOB,
            body={"to_status": "in_maintenance"})
        self.assertEqual(status, 200)
        self.assertEqual(asset_moved["status"], "in_maintenance")

        status, _, wo = self.request(
            "POST", "/work-orders", headers=BOB,
            body={"work_type": "maintenance", "subject": "Pump broken",
                  "project_id": project["id"], "asset_id": asset["id"],
                  "due_at": "2020-01-01T00:00:00Z"})
        self.assertEqual(status, 201)
        self.assertTrue(wo["id"].startswith("wo-"))
        self.assertEqual(wo["status"], "open")

        # ?now= drives the derived overdue field deterministically.
        query = urllib.parse.urlencode({"now": NOW})
        status, _, got = self.request("GET", "/work-orders/%s?%s" % (wo["id"], query), headers=CAROL)
        self.assertEqual(status, 200)
        self.assertTrue(got["overdue"])
        status, _, listing = self.request("GET", "/work-orders?%s" % query, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn(wo["id"], [w["id"] for w in listing["work_orders"]])
        self.assertTrue(
            [w for w in listing["work_orders"] if w["id"] == wo["id"]][0]["overdue"])

        status, _, assigned = self.request(
            "POST", "/work-orders/%s/assign" % wo["id"], headers=BOB,
            body={"person_id": person["id"]})
        self.assertEqual(status, 200)
        self.assertEqual(assigned["person_id"], person["id"])
        status, _, moved = self.request(
            "POST", "/work-orders/%s/transition" % wo["id"], headers=BOB,
            body={"to_status": "in_progress"})
        self.assertEqual(status, 200)
        self.assertEqual(moved["status"], "in_progress")

        status, _, insp = self.request(
            "POST", "/inspections", headers=BOB,
            body={"summary": "Pump inspection", "asset_id": asset["id"],
                  "work_order_id": wo["id"], "inspector_id": person["id"],
                  "outcome": "pass"})
        self.assertEqual(status, 201)
        self.assertTrue(insp["id"].startswith("insp-"))
        status, _, insps = self.request(
            "GET", "/inspections?asset_id=%s" % asset["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(insps["inspections"]), 1)

        status, _, usage = self.request(
            "POST", "/usage", headers=BOB,
            body={"project_id": project["id"], "metric": "hours",
                  "quantity": 3, "period": "2026-10"})
        self.assertEqual(status, 201)
        self.assertTrue(usage["id"].startswith("use-"))
        status, _, usages = self.request(
            "GET", "/usage?project_id=%s" % project["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(usages["usage"]), 1)

        # workflow_write is admin-only: bob gets 403, alice succeeds, PATCH bumps version.
        status, _, _ = self.request(
            "POST", "/workflows", headers=BOB,
            body={"name": "w", "work_type": "all", "trigger_text": "t", "action_text": "a"})
        self.assertEqual(status, 403)
        status, _, wf = self.request(
            "POST", "/workflows", headers=ALICE,
            body={"name": "w", "work_type": "all", "trigger_text": "t", "action_text": "a"})
        self.assertEqual(status, 201)
        self.assertEqual(wf["version"], 1)
        status, _, wf2 = self.request(
            "PATCH", "/workflows/%s" % wf["id"], headers=ALICE, body={"trigger_text": "t2"})
        self.assertEqual(status, 200)
        self.assertEqual(wf2["version"], 2)
        self.assertEqual(wf2["trigger_text"], "t2")
        self.assertEqual(wf2["action_text"], "a")

        status, _, rep = self.request("GET", "/report?%s" % query, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(rep["work_orders"]["overdue"], 1)
        self.assertEqual(rep["work_orders"]["total"], 1)
        self.assertEqual(rep["usage"]["by_metric"], {"hours": 3})

        q = urllib.parse.urlencode({"q": "pump"})
        status, _, result = self.request("GET", "/search?%s" % q, headers=BOB)
        self.assertEqual(status, 200)
        self.assertTrue(result["work_orders"])
        self.assertTrue(result["assets"])

        status, _, audit = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", audit)


class TestServiceAccessAndErrors(ServiceBase):
    """Core 10: REST API -- 400/403/404 and denied-audit behaviour."""

    def test_viewer_write_is_403_and_denied_audited(self):
        """Core 10: REST API / Audit. Viewer POST /persons -> 403, and a '<action>:denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request("POST", "/persons", headers=CAROL, body={"name": "X"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_operator_workflow_write_is_403_and_denied_audited(self):
        """Core 10: REST API / RBAC / Audit. Operator POST /workflows -> 403 (workflow_write is admin-only), denied attempt audited with ':denied'."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "bob"
                        and e["action"] == "workflow_write:denied"])
        before = denied_count()
        status, _, parsed = self.request(
            "POST", "/workflows", headers=BOB,
            body={"name": "w", "work_type": "all", "trigger_text": "t", "action_text": "a"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_validation_400_and_not_found_404(self):
        """Core 10: REST API (SI-10). Bad work order -> 400; unknown work order -> 404; bad now -> 400; float usage quantity -> 400."""
        status, _, parsed = self.request(
            "POST", "/work-orders", headers=BOB, body={"work_type": "bogus", "subject": "s"})
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/work-orders/wo-999999", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/work-orders?now=junk", headers=ALICE)
        self.assertEqual(status, 400)
        status, _, parsed = self.request("GET", "/report?now=junk", headers=ALICE)
        self.assertEqual(status, 400)
        status, _, parsed = self.request(
            "POST", "/usage", headers=BOB,
            body={"project_id": "proj-1", "metric": "hours", "quantity": 1.5, "period": "2026-10"})
        self.assertEqual(status, 400)

    def test_audit_admin_only(self):
        """Core 10: REST API / Audit (AU-6). GET /audit -> 403 for operator/viewer, 200 for admin with {entries}."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)


if __name__ == "__main__":
    unittest.main()
