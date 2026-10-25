"""Unsuccessful-logon lockout tests (L3 High uplift, AC-7).

Traces to: Core functions -- REST API and Access control, as uplifted
to the High baseline -- AC-7 (unsuccessful logon attempts):
``make_server(..., max_failures=3, lockout_seconds=300)`` tracks
consecutive authentication failures per username; at the threshold
the username locks, further attempts (even with the correct role)
get 403 and are audited with action ``"auth:locked"``, a success
before the threshold resets the counter, and lock expiry lets the
user in again. Driven over real HTTP the way test_service.py drives
it, against GET /contacts (bob's correct role is operator).
"""

import http.client
import json
import threading
import time
import unittest

from comm_helpers import USERS
from comm.audit import AuditLog
from comm.service import make_server
from comm.store import CommStore


class LockoutBase(unittest.TestCase):
    """A fresh server per test, so failure counters never leak
    between tests (each make_server call gets its own AC-7 state)."""

    max_failures = 3
    lockout_seconds = 300

    def setUp(self):
        self.audit = AuditLog()
        self.store = CommStore(audit=self.audit)
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

    def get_contacts(self, user, role):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/contacts", headers={"X-User": user, "X-Role": role})
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except ValueError:
            parsed = None
        return status, parsed

    def get_health(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        resp.read()
        status = resp.status
        conn.close()
        return status

    def fail(self, user, wrong_role, times=1):
        statuses = []
        for _ in range(times):
            status, _ = self.get_contacts(user, wrong_role)
            statuses.append(status)
        return statuses


class TestLockout(LockoutBase):
    """AC-7: lockout at the failure threshold (max_failures=3)."""

    def test_locked_after_three_failures_correct_role_still_403(self):
        """AC-7: three bad-role attempts for bob are ordinary 401s;
        a fourth attempt with the CORRECT role (operator) is refused
        403 while the lock holds."""
        self.assertEqual(self.fail("bob", "admin", times=3), [401, 401, 401])
        status, parsed = self.get_contacts("bob", "operator")
        self.assertEqual(status, 403)
        self.assertIn("error", parsed)

    def test_locked_attempt_is_audited_as_auth_locked(self):
        """AC-7: an attempt made while locked is audited with action
        "auth:locked" naming the locked username."""
        self.fail("bob", "admin", times=3)
        self.get_contacts("bob", "operator")  # the locked attempt
        locked = [
            e for e in self.audit.entries()
            if e["action"] == "auth:locked" and e["actor"] == "bob"
        ]
        self.assertTrue(locked, "no auth:locked audit entry for bob")

    def test_unknown_usernames_also_accumulate_failures(self):
        """AC-7: failures are tracked per username even for users
        outside the registry -- mallory locks like anyone else."""
        self.assertEqual(self.fail("mallory", "admin", times=3), [401, 401, 401])
        status, _ = self.get_contacts("mallory", "admin")
        self.assertEqual(status, 403)

    def test_lockout_is_per_user(self):
        """AC-7: one user's lockout does not affect anyone else --
        alice still authenticates while bob is locked."""
        self.fail("bob", "admin", times=3)
        status, _ = self.get_contacts("bob", "operator")
        self.assertEqual(status, 403)
        status, _ = self.get_contacts("alice", "admin")
        self.assertEqual(status, 200)

    def test_success_before_threshold_resets_counter(self):
        """AC-7: a successful authentication resets the consecutive
        failure counter -- fail, fail, succeed, fail, fail, succeed
        is never locked (the count restarted at each success)."""
        self.assertEqual(self.fail("bob", "admin", times=2), [401, 401])
        status, _ = self.get_contacts("bob", "operator")
        self.assertEqual(status, 200)  # success resets the counter
        self.assertEqual(self.fail("bob", "admin", times=2), [401, 401])
        status, _ = self.get_contacts("bob", "operator")
        self.assertEqual(status, 200)  # only 2 consecutive: not locked

    def test_health_stays_reachable_throughout(self):
        """AC-7: GET /health needs no auth and stays reachable while
        a user is locked out."""
        self.assertEqual(self.get_health(), 200)
        self.fail("bob", "admin", times=3)
        status, _ = self.get_contacts("bob", "operator")
        self.assertEqual(status, 403)  # bob is locked
        self.assertEqual(self.get_health(), 200)


class TestLockoutExpiry(LockoutBase):
    """AC-7: lock expiry lets the user in again."""

    max_failures = 3
    lockout_seconds = 0.3

    def test_lock_expires_and_correct_attempt_succeeds(self):
        """AC-7: after a tiny lockout_seconds (0.3) elapses, a
        correct attempt for the previously locked user succeeds."""
        self.assertEqual(self.fail("bob", "admin", times=3), [401, 401, 401])
        status, _ = self.get_contacts("bob", "operator")
        self.assertEqual(status, 403)  # locked
        time.sleep(0.5)
        status, _ = self.get_contacts("bob", "operator")
        self.assertEqual(status, 200)  # lock expired, self-cleared


if __name__ == "__main__":
    unittest.main()
