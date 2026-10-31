"""HTTP service: header auth, status mapping, denied-attempt
auditing, and end-to-end flows over real requests."""

import http.client
import json
import threading
import unittest

import cloudinfra_helpers as H
from cloudinfra.audit import AuditLog
from cloudinfra.service import USERS, make_server
from cloudinfra.store import CloudInfraStore


def call(port, method, path, user=None, role=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"}
    if user is not None:
        headers["X-User"] = user
    if role is not None:
        headers["X-Role"] = role
    payload = json.dumps(body) if body is not None else None
    conn.request(method, path, body=payload, headers=headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(raw) if raw else {}


class TestService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CloudInfraStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit, dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health(self):
        status, body = call(self.port, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_missing_auth_is_401(self):
        status, _ = call(self.port, "GET", "/organizations")
        self.assertEqual(status, 401)

    def test_wrong_role_is_401(self):
        status, _ = call(self.port, "GET", "/organizations",
                         user="alice", role="member")
        self.assertEqual(status, 401)

    def test_end_to_end_flow(self):
        status, org = call(self.port, "POST", "/organizations",
                           user="alice", role="admin",
                           body={"org_ref": "org-svc", "label": "Svc Org"})
        self.assertEqual(status, 201)
        oid = org["id"]
        status, _ = call(self.port, "POST", "/organizations/%s/members" % oid,
                         user="alice", role="admin", body={"username": "bob"})
        self.assertEqual(status, 200)
        status, tenancy = call(
            self.port, "POST", "/organizations/%s/tenancies" % oid,
            user="bob", role="member",
            body={"tenancy_ref": "ten-a", "label": "A",
                  "hosting_model": "boundary_protected"})
        self.assertEqual(status, 201)
        status, dep = call(
            self.port, "POST", "/organizations/%s/deployments" % oid,
            user="bob", role="member",
            body={"tenancy_id": tenancy["id"], "deployment_ref": "dep-1",
                  "workload_ref": "wl-1"})
        self.assertEqual(status, 201)
        status, dep2 = call(
            self.port, "POST", "/organizations/%s/deployments" % oid,
            user="bob", role="member",
            body={"tenancy_id": tenancy["id"], "deployment_ref": "dep-2",
                  "workload_ref": "wl-1"})
        self.assertEqual(status, 201)
        status, active = call(
            self.port, "POST",
            "/organizations/%s/deployments/%s/activate" % (oid, dep["id"]),
            user="bob", role="member")
        self.assertEqual(status, 200)
        self.assertEqual(active["status"], "active")
        # The slot rule refuses the second activation over HTTP too.
        status, body = call(
            self.port, "POST",
            "/organizations/%s/deployments/%s/activate" % (oid, dep2["id"]),
            user="bob", role="member")
        self.assertEqual(status, 400)
        self.assertIn("error", body)
        status, report = call(
            self.port, "GET", "/organizations/%s/report" % oid,
            user="bob", role="member")
        self.assertEqual(status, 200)
        self.assertEqual(report["deployments"]["by_status"],
                         {"active": 1, "recorded": 1})

    def test_viewer_write_is_403(self):
        status, org = call(self.port, "POST", "/organizations",
                           user="alice", role="admin",
                           body={"org_ref": "org-svc2", "label": "Svc Org 2"})
        oid = org["id"]
        call(self.port, "POST", "/organizations/%s/members" % oid,
             user="alice", role="admin", body={"username": "carol"})
        status, _ = call(
            self.port, "POST", "/organizations/%s/tenancies" % oid,
            user="carol", role="viewer",
            body={"tenancy_ref": "ten-x", "label": "X",
                  "hosting_model": "shared"})
        self.assertEqual(status, 403)

    def test_not_found_is_404(self):
        status, _ = call(self.port, "GET", "/organizations/org-99",
                         user="alice", role="admin")
        self.assertEqual(status, 404)

    def test_validation_is_400(self):
        status, org = call(self.port, "POST", "/organizations",
                           user="alice", role="admin",
                           body={"org_ref": "org-svc3", "label": "Svc Org 3"})
        oid = org["id"]
        status, body = call(
            self.port, "POST", "/organizations/%s/tenancies" % oid,
            user="alice", role="admin",
            body={"tenancy_ref": "ten-x", "label": "X",
                  "hosting_model": "bogus"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_audit_endpoint_admin_only_and_denied_entries(self):
        # Produce a denied attempt first so the assertion does not
        # depend on test ordering.
        status, _ = call(self.port, "GET", "/organizations")
        self.assertEqual(status, 401)
        status, body = call(self.port, "GET", "/audit",
                            user="alice", role="admin")
        self.assertEqual(status, 200)
        actions = [e["action"] for e in body["entries"]]
        self.assertIn("audit_read", actions)
        self.assertTrue(any(a.endswith(":denied") for a in actions))
        status, _ = call(self.port, "GET", "/audit",
                         user="carol", role="viewer")
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
