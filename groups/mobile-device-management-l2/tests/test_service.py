"""Core function 12: REST API — live HTTP semantics (SI-10, AC-3)."""

import http.client
import json
import threading
import unittest

import mdm_helpers as H
from mdm.audit import AuditLog
from mdm.service import make_server
from mdm.store import MdmStore


class HttpFixture(unittest.TestCase):
    def setUp(self):
        self.audit = AuditLog()
        self.store = MdmStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit,
                                  dict(H.USERS_REGISTRY))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, user=None, role=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Content-Type": "application/json"}
        if user is not None:
            headers["X-User"] = user
        if role is not None:
            headers["X-Role"] = role
        conn.request(method, path,
                     body=json.dumps(body) if body is not None else None,
                     headers=headers)
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        return response.status, json.loads(raw) if raw else {}


class TestService(HttpFixture):
    def test_health_needs_no_auth(self):
        status, payload = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_unknown_user_and_role_mismatch_are_401(self):
        status, _ = self.call("GET", "/organizations", user="mallory",
                              role="member")
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/organizations", user="bob",
                              role="admin")  # bob is registered as member
        self.assertEqual(status, 401)

    def test_full_flow_over_http(self):
        status, org = self.call("POST", "/organizations", "bob", "member",
                                {"ref": "AGENCY-1", "label": "Agency One"})
        self.assertEqual(status, 201)
        org_id = org["id"]
        status, _ = self.call("POST", "/organizations/%s/members" % org_id,
                              "alice", "admin", {"username": "erin"})
        self.assertEqual(status, 200)
        status, item = self.call(
            "POST", "/organizations/%s/inventory" % org_id, "bob", "member",
            {"ref": "SVC-100", "service_kind": "wireline",
             "label": "HQ voice circuit", "plan_ref": "PLAN-VOICE-1",
             "monthly_recurring_cents": 50000})
        self.assertEqual(status, 201)
        status, order = self.call(
            "POST", "/organizations/%s/orders" % org_id, "bob", "member",
            {"order_type": "suspend", "detail": "Hold",
             "inventory_id": item["id"]})
        self.assertEqual(status, 201)
        # The requester cannot approve his own order: 403.
        status, _ = self.call("POST", "/orders/%s/approve" % order["id"],
                              "bob", "member")
        self.assertEqual(status, 403)
        status, decided = self.call("POST", "/orders/%s/approve" % order["id"],
                                    "erin", "member")
        self.assertEqual(status, 200)
        self.assertEqual(decided["status"], "approved")
        status, done = self.call("POST", "/orders/%s/fulfill" % order["id"],
                                 "bob", "member")
        self.assertEqual(status, 200)
        status, item_view = self.call("GET", "/inventory/%s" % item["id"],
                                      "bob", "member")
        self.assertEqual(item_view["provisioning_state"], "suspended")

    def test_viewer_is_read_only_over_http(self):
        status, org = self.call("POST", "/organizations", "bob", "member",
                                {"ref": "AGENCY-1", "label": "Agency One"})
        status, _ = self.call(
            "POST", "/organizations/%s/inventory" % org["id"],
            "carol", "viewer",
            {"ref": "SVC-1", "service_kind": "wireline", "label": "x",
             "plan_ref": "P", "monthly_recurring_cents": 1})
        self.assertEqual(status, 403)

    def test_validation_and_not_found(self):
        status, org = self.call("POST", "/organizations", "bob", "member",
                                {"ref": "AGENCY-1", "label": "Agency One"})
        status, payload = self.call(
            "POST", "/organizations/%s/budgets" % org["id"], "bob", "member",
            {"period": "June", "budget_cents": 100})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        status, _ = self.call("GET", "/organizations/org-99", "bob", "member")
        self.assertEqual(status, 404)
        status, _ = self.call("GET", "/nope", "bob", "member")
        self.assertEqual(status, 404)

    def test_audit_endpoint_admin_only_and_denials_audited(self):
        status, _ = self.call("GET", "/audit", "bob", "member")
        self.assertEqual(status, 403)
        status, payload = self.call("GET", "/audit", "alice", "admin")
        self.assertEqual(status, 200)
        actions = [e["action"] for e in payload["entries"]]
        self.assertTrue(any(a.endswith(":denied") for a in actions))
        self.assertIn("audit_read", actions)


if __name__ == "__main__":
    unittest.main()
