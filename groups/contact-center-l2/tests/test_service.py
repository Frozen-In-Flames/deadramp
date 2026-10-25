"""REST API service tests.

Traces to: Core function 10 -- REST API; contract for
``contact/service.py``: make_server(host, port, store, audit, users),
auth via X-User / X-Role against USERS {alice:admin, bob:operator,
carol:viewer}, errors JSON {error} 400/401/403/404, PermissionDenied
-> 403 with '<action>:denied' audit entry, audit_read admin-only,
?now= accepted on case/callback/report endpoints.
"""

import http.client
import json
import threading
import unittest
import urllib.parse

from contact_helpers import USERS
from contact.audit import AuditLog
from contact.service import make_server
from contact.store import ContactStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "operator"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}

NOW = "2025-06-01T00:00:00Z"


class ServiceBase(unittest.TestCase):
    """Core 10: REST API -- real HTTP server on an ephemeral port."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = ContactStore(audit=cls.audit)
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
                status, _, parsed = self.request("GET", "/agents", headers=headers)
                self.assertEqual(status, 401)
                self.assertIn("error", parsed)

    def test_unknown_path_404_no_traceback(self):
        """Core 10: REST API. Unknown route -> 404 JSON, no stack trace."""
        status, text, parsed = self.request("GET", "/nope", headers=ALICE)
        self.assertEqual(status, 404)
        self.assertIn("error", parsed)
        self.assertNotIn("Traceback", text)


class TestFullFlow(ServiceBase):
    """Core 10: REST API -- full contact-center flow over HTTP."""

    def test_full_flow(self):
        """Core 10: REST API. agent -> contact -> queue+member -> case -> assign/transition -> callback -> interaction -> alert -> rule -> report/search -> audit, with ?now= derivation."""
        status, _, agent = self.request(
            "POST", "/agents", headers=ALICE,
            body={"name": "Dana Agent", "skills": ["billing"]})
        self.assertEqual(status, 201)
        self.assertTrue(agent["id"].startswith("agt-"))

        status, _, contact = self.request(
            "POST", "/contacts", headers=BOB,
            body={"name": "Casey Citizen", "reference": "EXT-1001"})
        self.assertEqual(status, 201)
        self.assertTrue(contact["id"].startswith("ct-"))

        status, _, queue = self.request("POST", "/queues", headers=BOB, body={"name": "support"})
        self.assertEqual(status, 201)
        status, _, queue = self.request(
            "POST", "/queues/%s/members" % queue["id"], headers=BOB,
            body={"agent_id": agent["id"]})
        self.assertEqual(status, 201)
        self.assertEqual(queue["members"], [agent["id"]])
        status, _, members = self.request("GET", "/queues/%s/members" % queue["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual([m["id"] for m in members["members"]], [agent["id"]])

        status, _, case = self.request(
            "POST", "/cases", headers=BOB,
            body={"case_type": "claim", "subject": "Widget broken",
                  "contact_id": contact["id"], "queue_id": queue["id"],
                  "due_at": "2020-01-01T00:00:00Z"})
        self.assertEqual(status, 201)
        self.assertEqual(case["status"], "open")

        # ?now= drives the derived breached field deterministically.
        query = urllib.parse.urlencode({"now": NOW})
        status, _, got = self.request("GET", "/cases/%s?%s" % (case["id"], query), headers=CAROL)
        self.assertEqual(status, 200)
        self.assertTrue(got["breached"])
        status, _, listing = self.request("GET", "/cases?%s" % query, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertIn(case["id"], [c["id"] for c in listing["cases"]])

        status, _, assigned = self.request(
            "POST", "/cases/%s/assign" % case["id"], headers=BOB,
            body={"agent_id": agent["id"]})
        self.assertEqual(status, 200)
        self.assertEqual(assigned["agent_id"], agent["id"])
        status, _, moved = self.request(
            "POST", "/cases/%s/transition" % case["id"], headers=BOB,
            body={"to_status": "in_progress"})
        self.assertEqual(status, 200)
        self.assertEqual(moved["status"], "in_progress")

        status, _, cb = self.request(
            "POST", "/callbacks", headers=BOB,
            body={"contact_id": contact["id"], "requested_for": "2020-01-01T00:00:00Z",
                  "case_id": case["id"]})
        self.assertEqual(status, 201)
        self.assertEqual(cb["status"], "scheduled")
        status, _, cbs = self.request("GET", "/callbacks?%s" % query, headers=CAROL)
        self.assertEqual(status, 200)
        mine = [c for c in cbs["callbacks"] if c["id"] == cb["id"]][0]
        self.assertEqual(mine["state"], "overdue")
        status, _, done = self.request(
            "POST", "/callbacks/%s/complete" % cb["id"], headers=BOB,
            body={"outcome": "reached"})
        self.assertEqual(status, 200)
        self.assertEqual(done["status"], "completed")

        status, _, inter = self.request(
            "POST", "/interactions", headers=BOB,
            body={"channel": "voice", "direction": "inbound",
                  "summary": "Call about widget", "case_id": case["id"],
                  "external_ref": "CALL-77"})
        self.assertEqual(status, 201)
        self.assertTrue(inter["id"].startswith("int-"))
        status, _, inters = self.request(
            "GET", "/interactions?case_id=%s" % case["id"], headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(len(inters["interactions"]), 1)

        status, _, alert = self.request(
            "POST", "/alerts", headers=BOB,
            body={"severity": "warning", "message": "Widget queue slow"})
        self.assertEqual(status, 201)
        status, _, acked = self.request("POST", "/alerts/%s/ack" % alert["id"], headers=BOB, body={})
        self.assertEqual(status, 200)
        self.assertEqual(acked["status"], "acknowledged")
        status, _, resolved = self.request(
            "POST", "/alerts/%s/resolve" % alert["id"], headers=BOB, body={})
        self.assertEqual(status, 200)
        self.assertEqual(resolved["status"], "resolved")

        # rule_write is admin-only: bob gets 403, alice succeeds, PATCH bumps version.
        status, _, _ = self.request(
            "POST", "/rules", headers=BOB,
            body={"name": "r", "case_type": "all", "condition": "c", "action_text": "a"})
        self.assertEqual(status, 403)
        status, _, rule = self.request(
            "POST", "/rules", headers=ALICE,
            body={"name": "r", "case_type": "all", "condition": "c", "action_text": "a"})
        self.assertEqual(status, 201)
        status, _, rule2 = self.request(
            "PATCH", "/rules/%s" % rule["id"], headers=ALICE, body={"condition": "c2"})
        self.assertEqual(status, 200)
        self.assertEqual(rule2["version"], 2)

        status, _, rep = self.request("GET", "/report?%s" % query, headers=CAROL)
        self.assertEqual(status, 200)
        self.assertEqual(rep["cases"]["breached"], 1)
        self.assertEqual(rep["callbacks"]["by_state"].get("completed"), 1)

        q = urllib.parse.urlencode({"q": "widget"})
        status, _, result = self.request("GET", "/search?%s" % q, headers=BOB)
        self.assertEqual(status, 200)
        self.assertTrue(result["cases"])

        status, _, audit = self.request("GET", "/audit", headers=ALICE)
        self.assertEqual(status, 200)
        self.assertIn("entries", audit)

    def test_callback_cancel_endpoint(self):
        """Core 10: REST API. POST /callbacks/{id}/cancel cancels a scheduled callback."""
        status, _, contact = self.request(
            "POST", "/contacts", headers=BOB,
            body={"name": "Cancel Casey %s" % self.id(), "reference": "EXT-CX"})
        self.assertEqual(status, 201)
        status, _, cb = self.request(
            "POST", "/callbacks", headers=BOB,
            body={"contact_id": contact["id"], "requested_for": "2030-01-01T00:00:00Z"})
        self.assertEqual(status, 201)
        status, _, cancelled = self.request(
            "POST", "/callbacks/%s/cancel" % cb["id"], headers=BOB, body={})
        self.assertEqual(status, 200)
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["state"], "cancelled")


class TestServiceAccessAndErrors(ServiceBase):
    """Core 10: REST API -- 400/403/404 and denied-audit behaviour."""

    def test_viewer_write_is_403_and_denied_audited(self):
        """Core 10: REST API / Audit. Viewer POST /agents -> 403, and a '<action>:denied' audit entry appears for carol."""
        def denied_count():
            _, _, payload = self.request("GET", "/audit", headers=ALICE)
            return len([e for e in payload["entries"]
                        if e["actor"] == "carol" and str(e["action"]).endswith(":denied")])
        before = denied_count()
        status, _, parsed = self.request("POST", "/agents", headers=CAROL, body={"name": "X"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)
        self.assertGreater(denied_count(), before)

    def test_operator_rule_write_is_403(self):
        """Core 10: REST API / RBAC. Operator POST /rules -> 403 (rule_write is admin-only)."""
        status, _, parsed = self.request(
            "POST", "/rules", headers=BOB,
            body={"name": "r", "case_type": "all", "condition": "c", "action_text": "a"})
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_validation_400_and_not_found_404(self):
        """Core 10: REST API (SI-10). Bad case -> 400; unknown case -> 404; bad now -> 400."""
        status, _, parsed = self.request(
            "POST", "/cases", headers=BOB, body={"case_type": "bogus", "subject": "s"})
        self.assertEqual(status, 400)
        self.assertIn("error", parsed)
        status, _, parsed = self.request("GET", "/cases/case-999999", headers=ALICE)
        self.assertEqual(status, 404)
        status, _, parsed = self.request("GET", "/cases?now=junk", headers=ALICE)
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
