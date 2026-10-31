"""Unsuccessful logon lockout tests (L3 High uplift).

Traces to: Core function 13 (REST API authentication) as uplifted
to the FedRAMP High baseline -- AC-7 (unsuccessful logon attempts):
``make_server(max_failures=3, lockout_seconds=300)`` tracks
consecutive *authentication* failures per username (unknown user
or role mismatch); at max_failures the username locks for
lockout_seconds, further attempts -- even with the correct role --
are answered 403 and audited with action ``"auth:locked"``; a
successful authentication resets the counter; lock expiry lets the
user in again. Permission 403s (authenticated but unauthorized) do
NOT count toward the lockout.

Each test builds its own server instance so the per-server lockout
state is fresh.
"""

import http.client
import json
import threading
import time
import unittest

from storage.audit import AuditLog
from storage.service import make_server
from storage.store import StorageStore

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer",
         "dana": "auditor"}


class _ServerFixture:
    def __init__(self, **kwargs):
        self.audit = AuditLog()
        self.store = StorageStore(audit=self.audit)
        self.server = make_server(
            "127.0.0.1", 0, store=self.store, audit=self.audit,
            users=USERS, **kwargs)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def get(self, path, user=None, role=None):
        headers = {}
        if user is not None:
            headers["X-User"] = user
        if role is not None:
            headers["X-Role"] = role
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except ValueError:
            payload = {}
        return status, payload


class TestLockout(unittest.TestCase):
    """AC-7: three consecutive auth failures lock the username."""

    def make_fixture(self, **kwargs):
        fixture = _ServerFixture(**kwargs)
        self.addCleanup(fixture.close)
        return fixture

    def _fail_bob(self, fixture, times):
        # bob's correct role is "operator"; "admin" is a role
        # mismatch -> an authentication failure (401).
        return [fixture.get("/organizations", "bob", "admin")[0]
                for _ in range(times)]

    def test_three_failures_then_correct_role_is_locked_out(self):
        """AC-7: after 3 consecutive authentication failures, even a
        request with the CORRECT role is refused 403 with the
        lockout error body."""
        fixture = self.make_fixture()
        self.assertEqual(self._fail_bob(fixture, 3), [401, 401, 401])
        status, payload = fixture.get("/organizations", "bob", "operator")
        self.assertEqual(status, 403)
        self.assertEqual(
            payload, {"error": "account locked: too many failed logons"})

    def test_locked_attempt_is_audited(self):
        """AC-7 / AU-2: a refused-due-to-lock attempt is audited with
        action "auth:locked"."""
        fixture = self.make_fixture()
        self._fail_bob(fixture, 3)
        fixture.get("/organizations", "bob", "operator")
        locked = [e for e in fixture.audit.entries()
                  if e["action"] == "auth:locked"]
        self.assertEqual(len(locked), 1)
        self.assertEqual(locked[0]["actor"], "bob")

    def test_lockout_is_per_user(self):
        """AC-7: locking bob does not affect alice or carol."""
        fixture = self.make_fixture()
        self._fail_bob(fixture, 3)
        status, _ = fixture.get("/organizations", "alice", "admin")
        self.assertEqual(status, 200)
        status, _ = fixture.get("/organizations", "carol", "viewer")
        self.assertEqual(status, 200)

    def test_unknown_username_also_locks(self):
        """AC-7: failures for an unknown username count too; the 4th
        attempt is refused as locked, not merely unauthenticated."""
        fixture = self.make_fixture()
        statuses = [fixture.get("/organizations", "mallory", "admin")[0]
                    for _ in range(3)]
        self.assertEqual(statuses, [401, 401, 401])
        status, payload = fixture.get("/organizations", "mallory", "admin")
        self.assertEqual(status, 403)
        self.assertIn("account locked", payload["error"])

    def test_successful_login_resets_the_counter(self):
        """AC-7: a success clears the consecutive-failure count, so
        2 failures, a success, then 2 more failures do not lock."""
        fixture = self.make_fixture()
        self.assertEqual(self._fail_bob(fixture, 2), [401, 401])
        status, _ = fixture.get("/organizations", "bob", "operator")
        self.assertEqual(status, 200)
        self.assertEqual(self._fail_bob(fixture, 2), [401, 401])
        status, _ = fixture.get("/organizations", "bob", "operator")
        self.assertEqual(status, 200)

    def test_permission_denials_do_not_count(self):
        """AC-7: authenticated-but-forbidden requests are permission
        failures, not logon failures -- they never trigger lockout."""
        fixture = self.make_fixture()
        # dana (auditor) has no "read"; GET /organizations needs it.
        for _ in range(4):
            status, _ = fixture.get("/organizations", "dana", "auditor")
            self.assertEqual(status, 403)
        # dana is not locked: an audit_read endpoint still answers.
        status, _ = fixture.get("/audit/verify", "dana", "auditor")
        self.assertEqual(status, 200)


class TestLockoutExpiry(unittest.TestCase):
    """AC-7: the lock lasts lockout_seconds, then clears itself."""

    def test_lock_expires_and_login_succeeds(self):
        """AC-7: with lockout_seconds=1, after the lock lapses the
        correct role is accepted again."""
        fixture = _ServerFixture(lockout_seconds=1)
        self.addCleanup(fixture.close)
        for _ in range(3):
            status, _ = fixture.get("/organizations", "bob", "admin")
            self.assertEqual(status, 401)
        status, _ = fixture.get("/organizations", "bob", "operator")
        self.assertEqual(status, 403)
        time.sleep(1.2)
        status, _ = fixture.get("/organizations", "bob", "operator")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
