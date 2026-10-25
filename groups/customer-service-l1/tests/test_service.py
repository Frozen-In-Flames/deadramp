"""HTTP service layer: auth, routing, denied-attempt auditing."""

import http.client
import json
import threading
import unittest

from custsvc.audit import AuditLog
from custsvc.service import USERS, make_server
from custsvc.store import CustsvcStore

ADMIN_H = {"X-User": "alice", "X-Role": "admin"}
AGENT_H = {"X-User": "bob", "X-Role": "agent"}
VIEWER_H = {"X-User": "carol", "X-Role": "viewer"}


class ServiceFixture(unittest.TestCase):
    def setUp(self):
        self.audit = AuditLog()
        self.store = CustsvcStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit,
                                  dict(USERS))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body) if body is not None else None
        hdrs = dict(headers or {})
        if payload is not None:
            hdrs["Content-Type"] = "application/json"
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp.status, json.loads(raw) if raw else {}


class TestService(ServiceFixture):
    def test_health_is_open(self):
        status, body = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_missing_auth_is_401_and_audited_denied(self):
        status, _ = self.call("GET", "/cases")
        self.assertEqual(status, 401)
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertEqual(len(denied), 1)

    def test_wrong_role_for_user_is_401(self):
        status, _ = self.call("GET", "/cases",
                              headers={"X-User": "alice", "X-Role": "viewer"})
        self.assertEqual(status, 401)

    def test_viewer_write_is_403_and_audited_denied(self):
        status, _ = self.call("POST", "/requesters", headers=VIEWER_H,
                              body={"ref": "x", "label": "X"})
        self.assertEqual(status, 403)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "requester_write:denied"]
        self.assertEqual(len(denied), 1)

    def test_full_flow(self):
        status, req = self.call("POST", "/requesters", headers=AGENT_H,
                                body={"ref": "citizen-9", "label": "Citizen Nine"})
        self.assertEqual(status, 201)
        status, rsp = self.call("POST", "/responders", headers=AGENT_H,
                                body={"label": "Responder Nine", "team": "tier-2"})
        self.assertEqual(status, 201)
        status, case = self.call("POST", "/cases", headers=AGENT_H, body={
            "title": "Portal down", "body": "500 errors",
            "requester_ref": "citizen-9", "priority": "critical",
            "due_at": "2020-01-02T00:00:00+00:00"})
        self.assertEqual(status, 201)
        cid = case["id"]
        status, case = self.call("POST", "/cases/%s/assign" % cid,
                                 headers=AGENT_H,
                                 body={"responder_id": rsp["id"]})
        self.assertEqual(status, 200)
        self.assertEqual(case["assignee"], rsp["id"])
        status, body = self.call("GET", "/cases/%s?now=2026-10-25T12:00:00Z" % cid,
                                 headers=VIEWER_H)
        self.assertEqual(status, 200)
        self.assertTrue(body["breached"])
        status, view = self.call("GET", "/status", headers=VIEWER_H)
        self.assertEqual(view["overall"], "outage")

    def test_audit_read_is_admin_only(self):
        status, _ = self.call("GET", "/audit", headers=AGENT_H)
        self.assertEqual(status, 403)
        status, body = self.call("GET", "/audit", headers=ADMIN_H)
        self.assertEqual(status, 200)
        self.assertIn("entries", body)

    def test_agent_cannot_create_rule_over_http(self):
        status, _ = self.call("POST", "/rules", headers=AGENT_H, body={
            "name": "r", "trigger": "t", "condition": "c", "action_text": "a"})
        self.assertEqual(status, 403)
        status, rule = self.call("POST", "/rules", headers=ADMIN_H, body={
            "name": "r", "trigger": "t", "condition": "c", "action_text": "a"})
        self.assertEqual(status, 201)

    def test_unknown_route_404_and_bad_body_400(self):
        status, _ = self.call("GET", "/nope", headers=ADMIN_H)
        self.assertEqual(status, 404)
        status, _ = self.call("POST", "/cases", headers=AGENT_H,
                              body={"title": "x"})  # missing requester_ref
        self.assertEqual(status, 404)  # unknown requester ref -> NotFound


if __name__ == "__main__":
    unittest.main()
