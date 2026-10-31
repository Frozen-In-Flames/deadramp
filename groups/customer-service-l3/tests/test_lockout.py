"""[L3] Unsuccessful logon lockout (AC-7).

Consecutive authentication failures are tracked per username; at
``max_failures`` the username locks for ``lockout_seconds`` -- further
attempts, even with the correct role, get 403 and are audited as
``auth:locked``. A successful authentication resets the counter; an
expired lock clears itself.
"""

import http.client
import json
import threading
import time
import unittest

from custsvc.audit import AuditLog
from custsvc.service import USERS, make_server
from custsvc.store import CustsvcStore

ADMIN_H = {"X-User": "alice", "X-Role": "admin"}
AGENT_H = {"X-User": "bob", "X-Role": "agent"}
ALICE_WRONG = {"X-User": "alice", "X-Role": "viewer"}
BOB_WRONG = {"X-User": "bob", "X-Role": "viewer"}


class LockoutFixture(unittest.TestCase):
    max_failures = 3
    lockout_seconds = 300

    def setUp(self):
        self.audit = AuditLog()
        self.store = CustsvcStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit,
                                  dict(USERS),
                                  max_failures=self.max_failures,
                                  lockout_seconds=self.lockout_seconds)
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

    def fail_alice(self, times):
        for _ in range(times):
            status, _ = self.call("GET", "/cases", headers=ALICE_WRONG)
            self.assertEqual(status, 401)


class TestLockout(LockoutFixture):
    def test_threshold_locks_and_correct_role_gets_403(self):
        self.fail_alice(3)
        status, _ = self.call("GET", "/cases", headers=ADMIN_H)
        self.assertEqual(status, 403)

    def test_locked_attempt_is_audited(self):
        self.fail_alice(3)
        self.call("GET", "/cases", headers=ADMIN_H)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("auth:locked", actions)

    def test_lockout_is_per_user(self):
        self.fail_alice(3)
        status, _ = self.call("GET", "/cases", headers=AGENT_H)
        self.assertEqual(status, 200)

    def test_below_threshold_still_admits(self):
        self.fail_alice(2)
        status, _ = self.call("GET", "/cases", headers=ADMIN_H)
        self.assertEqual(status, 200)

    def test_success_resets_counter(self):
        self.fail_alice(2)
        status, _ = self.call("GET", "/cases", headers=ADMIN_H)
        self.assertEqual(status, 200)
        self.fail_alice(2)
        status, _ = self.call("GET", "/cases", headers=ADMIN_H)
        self.assertEqual(status, 200)


class TestLockoutExpiry(LockoutFixture):
    max_failures = 2
    lockout_seconds = 1

    def test_expired_lock_readmits(self):
        for _ in range(2):
            status, _ = self.call("GET", "/cases", headers=BOB_WRONG)
            self.assertEqual(status, 401)
        status, _ = self.call("GET", "/cases", headers=AGENT_H)
        self.assertEqual(status, 403)
        time.sleep(1.2)
        status, _ = self.call("GET", "/cases", headers=AGENT_H)
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
