"""Core: REST API access. Traces to UNION-SPEC core function 9.
Live HTTP server: auth 401, permission 403 (audited as denied),
validation 400, missing 404, {error} envelope; the full sharing
flow (commons -> controlled dataset -> access request -> decision
-> derived grant status) runs over HTTP end to end."""

import http.client
import json
import threading
import unittest
import urllib.parse

import research_helpers as H
from research.audit import AuditLog
from research.service import make_server
from research.store import ResearchStore


class ServiceFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = ResearchStore(audit=cls.audit)
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

    def denied_count(self):
        return len([e for e in self.audit.entries()
                    if e["action"].endswith(":denied")])


class TestServiceFlow(ServiceFixture):
    def test_health_needs_no_auth(self):
        status, body = self.call("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_missing_unknown_or_mismatched_credentials_are_401(self):
        status, _ = self.call("GET", "/commons")
        self.assertEqual(status, 401)
        status, _ = self.call("GET", "/commons", user="mallory",
                              role="member")
        self.assertEqual(status, 401)
        # Role must match the registry: bob is a member, not an admin.
        status, _ = self.call("GET", "/commons", user="bob", role="admin")
        self.assertEqual(status, 401)

    def test_full_sharing_flow_over_http(self):
        status, commons = self.as_user("POST", "/commons", H.MEMBER, body={
            "name": "http-research", "title": "HTTP Research Commons",
            "kind": "commons", "sponsor_ref": "SPONSOR-9"})
        self.assertEqual(status, 201)
        cid = commons["id"]
        self.assertTrue(cid.startswith("com-"))

        status, _ = self.as_user("POST", "/commons/%s/members" % cid,
                                 H.ADMIN, body={"username": "erin"})
        self.assertEqual(status, 200)

        status, dataset = self.as_user(
            "POST", "/commons/%s/datasets" % cid, H.MEMBER, body={
                "name": "http-dataset",
                "description": "HTTP controlled dataset",
                "access_tier": "controlled", "sha256": H.SHA256_A,
                "size_bytes": 128})
        self.assertEqual(status, 201)
        did = dataset["id"]

        status, request = self.as_user(
            "POST", "/datasets/%s/access-requests" % did, H.MEMBER,
            body={"purpose": "HTTP access", "duration_days": 30})
        self.assertEqual(status, 201)
        rid = request["id"]
        self.assertEqual(request["status"], "pending")

        # The requester may not decide (AC-5), and the denial is audited.
        before = self.denied_count()
        status, body = self.as_user(
            "POST", "/access-requests/%s/decide" % rid, H.MEMBER,
            body={"approve": True, "starts_at": H.T0})
        self.assertEqual(status, 403)
        self.assertIn("error", body)
        self.assertGreater(self.denied_count(), before)

        status, result = self.as_user(
            "POST", "/access-requests/%s/decide" % rid, H.STAFF,
            body={"approve": True, "note": "ok", "starts_at": H.T0})
        self.assertEqual(status, 201)
        self.assertEqual(result["request"]["status"], "approved")
        grant = result["grant"]
        self.assertEqual(grant["grantee"], "bob")
        self.assertEqual(grant["expires_at"], H.EXPIRES_AT)
        gid = grant["id"]

        query = urllib.parse.urlencode({"now": H.INSIDE_WINDOW})
        status, view = self.as_user("GET", "/grants/%s?%s" % (gid, query),
                                    H.MEMBER)
        self.assertEqual(status, 200)
        self.assertEqual(view["status"], "active")

        query = urllib.parse.urlencode({"now": H.AFTER_EXPIRY})
        status, view = self.as_user("GET", "/grants/%s?%s" % (gid, query),
                                    H.MEMBER)
        self.assertEqual(status, 200)
        self.assertEqual(view["status"], "expired")

    def test_viewer_write_is_403_and_denied_attempt_is_audited(self):
        before = self.denied_count()
        status, body = self.as_user("POST", "/commons", H.VIEWER, body={
            "name": "viewer-commons", "title": "Viewer Commons",
            "kind": "commons", "sponsor_ref": "S"})
        self.assertEqual(status, 403)
        self.assertIn("error", body)
        self.assertGreater(self.denied_count(), before)
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertTrue(denied)

    def test_unknown_route_and_unknown_id_are_404(self):
        status, body = self.as_user("GET", "/no-such-route", H.MEMBER)
        self.assertEqual(status, 404)
        self.assertIn("error", body)
        status, body = self.as_user("GET", "/commons/com-99", H.ADMIN)
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_validation_error_is_400(self):
        status, body = self.as_user("POST", "/commons", H.MEMBER, body={
            "name": "bad-kind", "title": "Bad Kind", "kind": "portal",
            "sponsor_ref": "S"})
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
