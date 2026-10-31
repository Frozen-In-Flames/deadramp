"""Core 10 (API access) over live HTTP: status semantics
(401/403/404/400), the full organization / system / application /
request / change / control flow, the derived overdue flag through
``?as_of=``, denied attempts audited with ``:denied``, and the
audit endpoint restricted to audit_read.
"""

import http.client
import json
import threading
import unittest

import sysadmin_helpers as H
from sysadmin.audit import AuditLog
from sysadmin.service import make_server
from sysadmin.store import SysadminStore


class Client:
    def __init__(self, port):
        self.port = port

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


class TestService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = SysadminStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit,
                                 dict(H.USERS_REGISTRY))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        cls.client = Client(cls.port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, *args, **kwargs):
        return self.client.call(*args, **kwargs)

    def test_health_is_open(self):
        status, payload = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_unauthenticated_and_role_mismatch_are_401(self):
        status, _ = self.call("GET", "/organizations")
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/organizations",
                              user="bob", role="admin")
        self.assertEqual(status, 401)

    def test_unknown_route_is_404(self):
        status, _ = self.call("GET", "/nope", user="bob", role="member")
        self.assertEqual(status, 404)

    def test_validation_error_is_400(self):
        status, payload = self.call("POST", "/organizations",
                                    user="bob", role="member",
                                    body={"ref": "", "label": "x"})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_full_flow_over_http(self):
        c = self.client
        status, org = c.call("POST", "/organizations", user="bob",
                             role="member",
                             body={"ref": "AGENCY-1", "label": "Agency One"})
        self.assertEqual(status, 201)
        org_id = org["id"]
        status, _ = c.call("POST", "/organizations/%s/members" % org_id,
                           user="alice", role="admin",
                           body={"username": "erin"})
        self.assertEqual(status, 200)

        status, system = c.call(
            "POST", "/organizations/%s/systems" % org_id, user="bob",
            role="member",
            body={"ref": "SYS-OS-1", "label": "Primary OS instance",
                  "kind": "operating_system", "platform_ref": "PLAT-A"})
        self.assertEqual(status, 201)
        system_id = system["id"]

        status, application = c.call(
            "POST", "/organizations/%s/applications" % org_id, user="bob",
            role="member",
            body={"system_id": system_id, "ref": "APP-PORTAL",
                  "label": "Agency portal"})
        self.assertEqual(status, 201)

        status, request = c.call(
            "POST", "/organizations/%s/requests" % org_id, user="bob",
            role="member",
            body={"system_id": system_id, "request_kind": "maintenance",
                  "summary": "Apply monthly OS maintenance",
                  "due_date": H.REQUEST_DUE_DATE,
                  "application_id": application["id"]})
        self.assertEqual(status, 201)
        # Derived against the real read clock, which is after the
        # fixture due date: the open request reads overdue. The
        # pinned before/after cases run through ?as_of= below.
        self.assertTrue(request["overdue"])
        request_id = request["id"]
        status, view = c.call(
            "GET", "/requests/%s?as_of=%s" % (request_id, H.AS_OF_AFTER_DUE),
            user="bob", role="member")
        self.assertEqual(status, 200)
        self.assertTrue(view["overdue"])
        status, resolved = c.call("POST", "/requests/%s/resolve" % request_id,
                                  user="erin", role="member", body={})
        self.assertEqual(status, 200)
        self.assertEqual(resolved["status"], "resolved")
        self.assertFalse(resolved["overdue"])

        status, change = c.call(
            "POST", "/organizations/%s/changes" % org_id, user="bob",
            role="member",
            body={"system_id": system_id, "change_kind": "patch",
                  "summary": "Patch SYS-OS-1 kernel"})
        self.assertEqual(status, 201)
        change_id = change["id"]
        # Separation of duties over HTTP: bob requested, bob may not decide.
        status, _ = c.call("POST", "/changes/%s/decide" % change_id,
                           user="bob", role="member", body={"approve": True})
        self.assertEqual(status, 403)
        status, decided = c.call("POST", "/changes/%s/decide" % change_id,
                                 user="erin", role="member",
                                 body={"approve": True})
        self.assertEqual(status, 200)
        self.assertEqual(decided["status"], "approved")
        status, closed = c.call("POST", "/changes/%s/close" % change_id,
                                user="bob", role="member", body={})
        self.assertEqual(status, 200)
        self.assertEqual(closed["status"], "closed")

        status, control = c.call(
            "POST", "/organizations/%s/controls" % org_id, user="bob",
            role="member",
            body={"system_id": system_id, "control_ref": "SC-7",
                  "source": "inherited",
                  "note": "Boundary protection from the hosting platform"})
        self.assertEqual(status, 201)
        self.assertEqual(control["source"], "inherited")

        status, summary = c.call(
            "GET", "/organizations/%s/summary" % org_id,
            user="bob", role="member")
        self.assertEqual(status, 200)
        self.assertEqual(summary["systems"], 1)
        self.assertEqual(summary["applications"], 1)
        self.assertEqual(summary["requests_by_status"]["resolved"], 1)
        self.assertEqual(summary["changes_by_status"]["closed"], 1)
        self.assertEqual(summary["controls_by_source"]["inherited"], 1)

    def test_outsider_is_403(self):
        status, org = self.call("POST", "/organizations", user="erin",
                                role="member",
                                body={"ref": "AGENCY-9", "label": "Nine"})
        self.assertEqual(status, 201)
        status, _ = self.call("GET", "/organizations/%s" % org["id"],
                              user="dave", role="member")
        self.assertEqual(status, 403)

    def test_denied_attempts_are_audited(self):
        before = len(self.audit.entries())
        self.call("GET", "/organizations", user="mallory", role="member")
        self.call("GET", "/organizations/org-404", user="bob", role="member")
        denied = [e for e in self.audit.entries()[before:]
                  if e["action"].endswith(":denied")]
        self.assertTrue(denied)

    def test_audit_endpoint_is_admin_only(self):
        status, _ = self.call("GET", "/audit", user="bob", role="member")
        self.assertEqual(status, 403)
        status, payload = self.call("GET", "/audit", user="alice",
                                    role="admin")
        self.assertEqual(status, 200)
        self.assertIn("entries", payload)


if __name__ == "__main__":
    unittest.main()
