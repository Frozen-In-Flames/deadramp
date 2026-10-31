"""REST API service tests.

Traces to: Core -- REST API; contract for
``construct/service.py``: make_server(host, port, store, audit, users),
auth via X-User / X-Role against USERS {alice:admin, bob:operator,
carol:viewer}, errors JSON {error} 400/401/403/404, PermissionDenied
-> 403 with '<action>:denied' audit entry, audit_read admin-only,
?now= accepted on contract/report endpoints.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from construct_helpers import USERS
from construct.audit import AuditLog
from construct.service import make_server
from construct.store import ConstructStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "operator"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"


class ServiceBase(unittest.TestCase):
    """REST API: real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = ConstructStore(audit=cls.audit)
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
        """REST API: helper performing a real HTTP request."""
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
    """REST API: health and header auth."""

    def test_health(self):
        """REST API. GET /health -> {status: ok} with no auth."""
        status, _, parsed = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_401(self):
        """REST API (IA-2). Unknown user or role mismatch -> 401 JSON error."""
        for headers in ({"X-User": "mallory", "X-Role": "admin"},
                        {"X-User": "alice", "X-Role": "viewer"},
                        {"X-User": "bob", "X-Role": "admin"},
                        {}):
            with self.subTest(headers=headers):
                status, _, parsed = self.request("GET", "/orgs", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """REST API. Unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """REST API: full construction flow over HTTP."""

    def test_full_flow(self):
        """REST API. org -> project+participants -> document/PATCH -> contract+?now= -> records -> workforce -> costs -> compliance/report/search/alerts -> audit."""
        status, _, prime = self.request(
            "POST", "/orgs", headers=ALICE, body={"name": "Prime Builders", "reference": "PRIME-1"})
        self.assertEqual(status, 201)
        self.assertTrue(prime["id"].startswith("org-"))
        status, _, sub = self.request(
            "POST", "/orgs", headers=BOB, body={"name": "Sub Trades", "reference": "SUB-1"})
        self.assertEqual(status, 201)

        status, _, project = self.request(
            "POST", "/projects", headers=BOB, body={"name": "Tower One", "location": "Dallas"})
        self.assertEqual(status, 201)
        self.assertEqual(project["status"], "planned")
        pid = project["id"]
        status, _, project = self.request(
            "POST", "/projects/%s/transition" % pid, headers=BOB, body={"to_status": "active"})
        self.assertEqual(status, 200)
        self.assertEqual(project["status"], "active")

        status, _, part = self.request(
            "POST", "/projects/%s/participants" % pid, headers=BOB,
            body={"org_id": prime["id"], "tier": 1, "role": "prime"})
        self.assertEqual(status, 201)
        status, _, part = self.request(
            "POST", "/projects/%s/participants" % pid, headers=BOB,
            body={"org_id": sub["id"], "tier": 2})
        self.assertEqual(status, 201)
        status, _, parts = self.request("GET", "/projects/%s/participants" % pid, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual([p["org_id"] for p in parts["participants"]], [prime["id"], sub["id"]])

        status, _, doc = self.request(
            "POST", "/documents", headers=BOB,
            body={"title": "Tower spec", "project_id": pid, "doc_type": "specification", "checksum": "c1"})
        self.assertEqual(status, 201)
        self.assertEqual(doc["version"], 1)
        status, _, doc2 = self.request(
            "PATCH", "/documents/%s" % doc["id"], headers=BOB, body={"note": "revised"})
        self.assertEqual(status, 200)
        self.assertEqual(doc2["version"], 2)
        self.assertEqual(doc2["checksum"], "c1")
        self.assertEqual(doc2["note"], "revised")

        status, _, con = self.request(
            "POST", "/contracts", headers=BOB,
            body={"title": "Tower deal", "project_id": pid, "org_id": prime["id"],
                  "value_cents": 5000, "end_at": PAST})
        self.assertEqual(status, 201)
        self.assertEqual(con["expiry_state"], "pre_execution")
        for to in ("in_review", "executed"):
            status, _, con = self.request(
                "POST", "/contracts/%s/transition" % con["id"], headers=BOB, body={"to_status": to})
            self.assertEqual(status, 200)
        # ?now= drives the derived expiry_state deterministically.
        query = urllib.parse.urlencode({"now": NOW})
        status, _, got = self.request("GET", "/contracts/%s?%s" % (con["id"], query), headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(got["expiry_state"], "expired")
        self.assertLess(got["days_to_expiry"], 0)
        status, _, listing = self.request(
            "GET", "/contracts?%s&project_id=%s" % (query, pid), headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn(con["id"], [c["id"] for c in listing["contracts"]])

        status, _, subt = self.request(
            "POST", "/submittals", headers=BOB,
            body={"project_id": pid, "title": "Steel package", "due_at": PAST})
        self.assertEqual(status, 201)
        status, _, got = self.request("GET", "/submittals/%s?%s" % (subt["id"], query), headers=CAROL)
        self.assertEqual(status, 200)
        self.assertTrue(got["overdue"])
        status, _, subt = self.request(
            "POST", "/submittals/%s/transition" % subt["id"], headers=BOB, body={"to_status": "submitted"})
        self.assertEqual(status, 200)

        status, _, rfi = self.request(
            "POST", "/rfis", headers=BOB,
            body={"project_id": pid, "question": "Which steel?", "due_at": PAST})
        self.assertEqual(status, 201)
        status, _, rfi = self.request(
            "POST", "/rfis/%s/transition" % rfi["id"], headers=BOB, body={"to_status": "answered"})
        self.assertEqual(status, 200)
        self.assertEqual(rfi["status"], "answered")

        status, _, ms = self.request(
            "POST", "/milestones", headers=BOB,
            body={"project_id": pid, "name": "Topping out", "due_at": PAST})
        self.assertEqual(status, 201)
        status, _, got = self.request("GET", "/milestones/%s?%s" % (ms["id"], query), headers=CAROL)
        self.assertEqual(got["due_state"], "overdue")
        status, _, ms = self.request(
            "POST", "/milestones/%s/complete" % ms["id"], headers=BOB, body={})
        self.assertEqual(status, 200)
        self.assertTrue(ms["completed"])

        status, _, dsp = self.request(
            "POST", "/dispatches", headers=BOB, body={"project_id": pid, "task": "Pour deck"})
        self.assertEqual(status, 201)
        status, _, dsp = self.request(
            "POST", "/dispatches/%s/transition" % dsp["id"], headers=BOB, body={"to_status": "in_progress"})
        self.assertEqual(status, 200)

        status, _, insp = self.request(
            "POST", "/inspections", headers=BOB,
            body={"project_id": pid, "inspection_type": "framing", "result": "fail"})
        self.assertEqual(status, 201)

        status, _, pun = self.request(
            "POST", "/punch-items", headers=BOB,
            body={"project_id": pid, "description": "Fix frame", "inspection_id": insp["id"], "due_at": PAST})
        self.assertEqual(status, 201)
        status, _, got = self.request("GET", "/punch-items/%s?%s" % (pun["id"], query), headers=CAROL)
        self.assertTrue(got["overdue"])
        status, _, pun = self.request(
            "POST", "/punch-items/%s/transition" % pun["id"], headers=BOB, body={"to_status": "corrected"})
        self.assertEqual(status, 200)

        status, _, inc = self.request(
            "POST", "/incidents", headers=BOB,
            body={"project_id": pid, "category": "safety", "description": "Near miss", "severity": "warning"})
        self.assertEqual(status, 201)
        status, _, inc = self.request(
            "POST", "/incidents/%s/transition" % inc["id"], headers=BOB, body={"to_status": "under_review"})
        self.assertEqual(status, 200)

        status, _, wrk = self.request(
            "POST", "/workers", headers=BOB,
            body={"project_id": pid, "org_id": prime["id"], "reference": "EMP-REF-1", "trade": "welder"})
        self.assertEqual(status, 201)
        status, _, entry = self.request(
            "POST", "/time-entries", headers=BOB, body={"worker_id": wrk["id"], "minutes": 480})
        self.assertEqual(status, 201)
        status, _, entries = self.request(
            "GET", "/time-entries?project_id=%s" % pid, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn(entry["id"], [e["id"] for e in entries["time_entries"]])

        status, _, pay = self.request(
            "POST", "/payrolls", headers=BOB,
            body={"project_id": pid, "org_id": prime["id"],
                  "period_start": "2025-01-01T00:00:00Z", "period_end": "2025-01-15T00:00:00Z",
                  "certified": True, "worker_count": 3, "total_wages_cents": 12000})
        self.assertEqual(status, 201)

        # violation_write is admin-only over HTTP too (operator case is in the access test class).
        status, _, vio = self.request(
            "POST", "/violations", headers=ALICE,
            body={"project_id": pid, "org_id": sub["id"], "kind": "wage", "description": "Late pay"})
        self.assertEqual(status, 201)
        status, _, comp = self.request(
            "GET", "/projects/%s/compliance?org_id=%s" % (pid, sub["id"]), headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(comp["status"], "noncompliant")
        status, _, comp = self.request(
            "GET", "/projects/%s/compliance?org_id=%s" % (pid, prime["id"]), headers=CAROL)
        self.assertEqual(comp["status"], "compliant")
        status, _, vio = self.request(
            "POST", "/violations/%s/resolve" % vio["id"], headers=ALICE, body={"resolution": "paid"})
        self.assertEqual(status, 200)
        self.assertEqual(vio["status"], "resolved")

        status, _, cost = self.request(
            "POST", "/costs", headers=BOB,
            body={"project_id": pid, "category": "materials", "description": "Steel",
                  "budgeted_cents": 1000, "actual_cents": 400})
        self.assertEqual(status, 201)
        status, _, summary = self.request("GET", "/projects/%s/cost-summary" % pid, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(summary["total_budgeted_cents"], 1000)
        self.assertEqual(summary["variance_cents"], 600)

        status, _, alerts = self.request("GET", "/alerts?%s" % query, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn("contract_expired", [a["kind"] for a in alerts["alerts"]])

        status, _, rep = self.request("GET", "/report?%s" % query, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(rep["contracts"]["by_expiry_state"].get("expired"), 1)
        self.assertIn("compliance", rep)

        q = urllib.parse.urlencode({"q": "tower"})
        status, _, result = self.request("GET", "/search?%s" % q, headers=BOB)
        self.assertEqual(status, 200)
        self.assertTrue(result["projects"])
        self.assertTrue(result["contracts"])

        status, _, audit = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", audit)


class TestServiceAccessAndErrors(ServiceBase):
    """REST API: 400/403/404 and denied-audit behaviour."""

    def test_viewer_write_is_403_and_denied_audited(self):
        """REST API / Audit. Viewer POST /orgs -> 403, and a '<action>:denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request("POST", "/orgs", headers=CAROL, body={"name": "X"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_operator_violation_create_is_403(self):
        """REST API / RBAC. Operator POST /violations -> 403 (violation_write is admin-only)."""
        status, _, project = self.request(
            "POST", "/projects", headers=ALICE, body={"name": "Vio Project %s" % self.id()})
        self.assertEqual(status, 201)
        status, _, org = self.request(
            "POST", "/orgs", headers=ALICE, body={"name": "Vio Org %s" % self.id()})
        self.assertEqual(status, 201)
        status, _, parsed = self.request(
            "POST", "/violations", headers=BOB,
            body={"project_id": project["id"], "org_id": org["id"],
                  "kind": "wage", "description": "X"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_validation_400_and_not_found_404(self):
        """REST API (SI-10). Bad contract -> 400; unknown contract -> 404; bad now -> 400; compliance without org_id -> 400."""
        status, _, project = self.request(
            "POST", "/projects", headers=ALICE, body={"name": "Err Project %s" % self.id()})
        self.assertEqual(status, 201)
        status, _, parsed = self.request(
            "POST", "/contracts", headers=BOB,
            body={"title": "X", "project_id": project["id"], "value_cents": 1.5})
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/contracts/con-999999", headers=ALICE)
        self.assertEqual(status, 404)
        status, _, parsed = self.request("GET", "/contracts?now=junk", headers=ALICE)
        self.assertEqual(status, 400)
        status, _, parsed = self.request(
            "GET", "/projects/%s/compliance" % project["id"], headers=ALICE)
        self.assertEqual(status, 400)

    def test_audit_admin_only(self):
        """REST API / Audit (AU-6). GET /audit -> 403 for operator/viewer, 200 for admin with {entries}."""
        for headers in (BOB, CAROL):
            status, _, _ = self.request("GET", "/audit", headers=headers)
            self.assertEqual(status, 403)
        status, _, payload = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)


if __name__ == "__main__":
    unittest.main()
