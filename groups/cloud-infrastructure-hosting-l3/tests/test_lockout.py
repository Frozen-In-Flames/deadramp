"""[L3] AC-7: unsuccessful logon lockout.

Consecutive authentication failures (unknown user or role
mismatch) are counted per username in the service layer; at
max_failures the username locks for lockout_seconds and any
further attempt — even with the correct role — is answered 403
and audited auth:locked. A successful authentication resets the
counter; an expired lock clears itself; unknown usernames lock
too; permission denials (an authenticated 403) never count.
"""

import http.client
import json
import threading
import unittest

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
    conn.request(method, path,
                 body=json.dumps(body) if body is not None else None,
                 headers=headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(raw) if raw else {}


class LockoutServerMixin:
    max_failures = 3
    lockout_seconds = 300

    def setUp(self):
        self.audit = AuditLog()
        self.store = CloudInfraStore(audit=self.audit)
        self.server = make_server(
            "127.0.0.1", 0, self.store, self.audit, dict(USERS),
            max_failures=self.max_failures,
            lockout_seconds=self.lockout_seconds)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def fail(self, name, role="member", times=1):
        status = None
        for _ in range(times):
            status, _ = call(self.port, "GET", "/organizations",
                             user=name, role=role)
        return status


class TestLockout(LockoutServerMixin, unittest.TestCase):
    def test_three_failures_lock_the_username(self):
        self.assertEqual(self.fail("alice", role="member", times=3), 401)
        # Even the correct role is now refused, with the lockout body.
        status, body = call(self.port, "GET", "/organizations",
                            user="alice", role="admin")
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "account locked: too many "
                                         "failed logons"})

    def test_locked_attempt_is_audited_auth_locked(self):
        self.fail("alice", role="member", times=3)
        call(self.port, "GET", "/organizations",
             user="alice", role="admin")
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("auth:locked", actions)

    def test_unknown_usernames_lock_too(self):
        self.assertEqual(self.fail("mallory", role="member", times=3), 401)
        status, _ = call(self.port, "GET", "/organizations",
                         user="mallory", role="member")
        self.assertEqual(status, 403)

    def test_lockout_is_per_user(self):
        self.fail("mallory", role="member", times=3)
        status, _ = call(self.port, "GET", "/organizations",
                         user="alice", role="admin")
        self.assertEqual(status, 200)

    def test_success_resets_the_counter(self):
        self.fail("bob", role="viewer", times=2)
        status, _ = call(self.port, "GET", "/organizations",
                         user="bob", role="member")
        self.assertEqual(status, 200)
        self.fail("bob", role="viewer", times=2)
        status, _ = call(self.port, "GET", "/organizations",
                         user="bob", role="member")
        self.assertEqual(status, 200)

    def test_permission_denials_never_count(self):
        # carol authenticates fine but lacks tenancy_write: three
        # authenticated 403s must not lock her out.
        status, org = call(self.port, "POST", "/organizations",
                           user="alice", role="admin",
                           body={"org_ref": "org-lock", "label": "L"})
        oid = org["id"]
        call(self.port, "POST", "/organizations/%s/members" % oid,
             user="alice", role="admin", body={"username": "carol"})
        for _ in range(3):
            status, _ = call(
                self.port, "POST", "/organizations/%s/tenancies" % oid,
                user="carol", role="viewer",
                body={"tenancy_ref": "ten-x", "label": "X",
                      "hosting_model": "shared"})
            self.assertEqual(status, 403)
        status, _ = call(self.port, "GET", "/organizations",
                         user="carol", role="viewer")
        self.assertEqual(status, 200)


class TestLockoutExpiry(LockoutServerMixin, unittest.TestCase):
    lockout_seconds = 0

    def test_expired_lock_clears_itself(self):
        self.assertEqual(self.fail("alice", role="member", times=3), 401)
        # The lock's duration is zero: by the next attempt it has
        # expired, clears itself, and the correct role succeeds.
        status, _ = call(self.port, "GET", "/organizations",
                         user="alice", role="admin")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
