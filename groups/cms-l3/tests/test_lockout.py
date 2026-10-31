"""Unsuccessful-logon lockout tests (L3 High uplift, AC-7).

Traces to: UNION-SPEC.md Core functions 10 (REST API) and 11 (RBAC)
as uplifted to the FedRAMP High baseline -- AC-7 (unsuccessful logon
attempts): ``make_server(..., max_failures, lockout_seconds)`` tracks
consecutive authentication failures per username; at the threshold
the username locks, further attempts (even with the correct role) get
403 and are audited with action ``"auth:locked"``, a success before
the threshold resets the counter, other users are unaffected, and
lock expiry lets the user in again. Driven over real HTTP.
"""

import http.client
import json
import threading
import time
import unittest

from cms_helpers import USERS
from cms.audit import AuditLog
from cms.service import make_server
from cms.store import CmsStore


class LockoutBase(unittest.TestCase):
    """A fresh server per test, so failure counters never leak
    between tests (each make_server call gets its own AC-7 state)."""

    max_failures = 3
    lockout_seconds = 300

    def setUp(self):
        self.audit = AuditLog()
        self.store = CmsStore(audit=self.audit)
        self.server = make_server(
            "127.0.0.1", 0, self.store, self.audit, dict(USERS),
            max_failures=self.max_failures,
            lockout_seconds=self.lockout_seconds,
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def get_sites(self, user, role):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/sites", headers={"X-User": user, "X-Role": role})
        resp = conn.getresponse()
        resp.read()
        status = resp.status
        conn.close()
        return status

    def fail(self, user="alice", times=1):
        for _ in range(times):
            status = self.get_sites(user, "viewer")  # wrong role for alice/bob
            self.assertEqual(status, 401)


class TestLockout(LockoutBase):
    """[L3] AC-7: lockout at the threshold."""

    def test_below_threshold_still_admits(self):
        """[L3] AC-7: max_failures-1 failures do not lock; the correct role still gets in."""
        self.fail(times=self.max_failures - 1)
        self.assertEqual(self.get_sites("alice", "admin"), 200)

    def test_threshold_locks_and_correct_role_gets_403(self):
        """[L3] AC-7: at max_failures consecutive failures the username locks -- even the correct role is answered 403."""
        self.fail(times=self.max_failures)
        self.assertEqual(self.get_sites("alice", "admin"), 403)

    def test_lockout_is_audited_as_auth_locked(self):
        """[L3] AC-7 / AU-2: a locked attempt is audited with action "auth:locked"."""
        self.fail(times=self.max_failures)
        self.get_sites("alice", "admin")
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("auth:locked", actions)

    def test_lockout_is_per_user(self):
        """[L3] AC-7: locking alice does not affect bob or dana."""
        self.fail(times=self.max_failures)
        self.assertEqual(self.get_sites("alice", "admin"), 403)
        self.assertEqual(self.get_sites("bob", "publisher"), 200)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/audit", headers={"X-User": "dana", "X-Role": "auditor"})
        resp = conn.getresponse()
        resp.read()
        self.assertEqual(resp.status, 200)
        conn.close()

    def test_success_resets_counter(self):
        """[L3] AC-7: a successful logon resets the consecutive-failure counter."""
        self.fail(times=self.max_failures - 1)
        self.assertEqual(self.get_sites("alice", "admin"), 200)
        self.fail(times=self.max_failures - 1)
        self.assertEqual(self.get_sites("alice", "admin"), 200)


class TestLockoutExpiry(LockoutBase):
    """[L3] AC-7: an expired lock admits the user again."""

    max_failures = 2
    lockout_seconds = 1

    def test_lock_expires(self):
        """[L3] AC-7: after lockout_seconds elapse, the correct role is admitted again."""
        self.fail(times=2)
        self.assertEqual(self.get_sites("alice", "admin"), 403)
        time.sleep(1.2)
        self.assertEqual(self.get_sites("alice", "admin"), 200)


if __name__ == "__main__":
    unittest.main()
