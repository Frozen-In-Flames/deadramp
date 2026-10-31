"""Core: REST API access. Traces to UNION-SPEC core function 11.
Live HTTP server: auth 401, permission 403 (audited as denied),
validation 400, missing 404, {error} envelope; the full grant flow
runs over HTTP end to end."""

import http.client
import json
import threading
import unittest

import grants_helpers as H
from grants.audit import AuditLog
from grants.service import make_server
from grants.store import GrantsStore


class ServiceFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = GrantsStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit,
                                 dict(H.USERS_REGISTRY))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      kwargs={"poll_interval": 0.05})
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def call(self, method, path, user=None, role=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Content-Type": "application/json"}
        if user is not None:
            headers["X-User"] = user
        if role is not None:
            headers["X-Role"] = role
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        return response.status, json.loads(raw) if raw else {}

    def as_user(self, method, path, user, body=None):
        return self.call(method, path, user=user.name, role=user.role,
                         body=body)


class TestServiceFlow(ServiceFixture):
    def test_health_needs_no_auth(self):
        status, body = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_missing_or_wrong_credentials_are_401(self):
        status, _ = self.call("GET", "/programs")
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/programs", user="bob", role="admin")
        self.assertEqual(status, 401)

    def test_full_grant_flow_over_http(self):
        status, program = self.as_user("POST", "/programs", H.MEMBER, body={
            "name": "http-grants", "title": "HTTP Grants",
            "sponsor_ref": "SPONSOR-9", "opens_at": "2026-01-01",
            "closes_at": "2026-12-31", "budget_cents": 500_000})
        self.assertEqual(status, 201)
        pid = program["id"]

        status, _ = self.as_user("POST", "/programs/%s/members" % pid,
                                 H.ADMIN, body={"username": "erin"})
        self.assertEqual(status, 200)

        status, org = self.as_user("POST", "/organizations", H.MEMBER,
                                   body={"ref": "ORG-HTTP",
                                         "label": "HTTP Applicants"})
        self.assertEqual(status, 201)

        status, app = self.as_user(
            "POST", "/programs/%s/applications" % pid, H.MEMBER,
            body={"org_id": org["id"], "requested_cents": 100_000,
                  "summary": "HTTP application"})
        self.assertEqual(status, 201)
        aid = app["id"]

        status, _ = self.as_user("POST", "/applications/%s/submit" % aid,
                                 H.MEMBER)
        self.assertEqual(status, 200)
        status, _ = self.as_user("POST",
                                 "/applications/%s/start-review" % aid,
                                 H.STAFF)
        self.assertEqual(status, 200)

        # The submitter may not decide (AC-5), and the denial is audited.
        status, body = self.as_user("POST", "/applications/%s/decide" % aid,
                                    H.MEMBER,
                                    body={"approve": True,
                                          "amount_cents": 100_000})
        self.assertEqual(status, 403)
        self.assertIn("error", body)

        status, result = self.as_user("POST",
                                      "/applications/%s/decide" % aid,
                                      H.STAFF,
                                      body={"approve": True,
                                            "amount_cents": 100_000,
                                            "note": "ok"})
        self.assertEqual(status, 201)
        self.assertEqual(result["award"]["amount_cents"], 100_000)

        status, summary = self.as_user("GET",
                                       "/programs/%s/summary" % pid, H.MEMBER)
        self.assertEqual(status, 200)
        self.assertEqual(summary["awarded_cents"], 100_000)

        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertTrue(denied)

    def test_viewer_write_is_403_and_unknown_route_404(self):
        status, _ = self.as_user("POST", "/programs", H.VIEWER, body={
            "name": "nope", "title": "Nope", "sponsor_ref": "S",
            "opens_at": "2026-01-01", "closes_at": "2026-12-31",
            "budget_cents": 1})
        self.assertEqual(status, 403)
        status, body = self.as_user("GET", "/no-such-route", H.MEMBER)
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_validation_error_is_400(self):
        status, body = self.as_user("POST", "/programs", H.MEMBER, body={
            "name": "bad", "title": "Bad", "sponsor_ref": "S",
            "opens_at": "2026-01-01", "closes_at": "2026-12-31",
            "budget_cents": 10.5})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_audit_endpoint_admin_only(self):
        status, _ = self.as_user("GET", "/audit", H.VIEWER)
        self.assertEqual(status, 403)
        status, body = self.as_user("GET", "/audit", H.ADMIN)
        self.assertEqual(status, 200)
        self.assertIn("entries", body)


if __name__ == "__main__":
    unittest.main()
