"""GET /audit/verify endpoint tests (L3 High uplift, AU-9/AU-6).

Traces to: Core function -- Append-only audit log / REST API, as
uplifted to the High baseline -- AU-9: ``GET /audit/verify``
(audit_read) returns {"ok", "entries", "first_bad_index"}, where
``entries`` is the entry count read BEFORE this read's own
``audit_read`` entry is recorded, so immediately after a verify call
the log holds ``entries + 1`` entries.
"""

import http.client
import json
import threading
import unittest

from comm_helpers import USERS
from comm.audit import AuditLog
from comm.service import make_server
from comm.store import CommStore

ALICE = {"X-User": "alice", "X-Role": "admin"}
BOB = {"X-User": "bob", "X-Role": "operator"}
CAROL = {"X-User": "carol", "X-Role": "viewer"}
DANA = {"X-User": "dana", "X-Role": "auditor"}


class VerifyBase(unittest.TestCase):
    """AU-9: a fresh server (and audit log) per test, so entry
    counts and any tampering never leak between tests."""

    def setUp(self):
        self.audit = AuditLog()
        self.store = CommStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit, dict(USERS))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def get_verify(self, headers):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/audit/verify", headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except ValueError:
            parsed = None
        return status, parsed


class TestAuditVerifyEndpoint(VerifyBase):
    """AU-9/AU-6: /audit/verify shape, counting rule, and access."""

    def test_verify_shape_on_clean_log(self):
        """AU-9: GET /audit/verify as admin -> 200 with exactly the
        keys {ok, entries, first_bad_index}; a seeded clean log
        reports ok True, first_bad_index None, entries == seeded."""
        self.audit.record("alice", "contact_create", "ct-1")
        self.audit.record("bob", "search", "search")
        status, payload = self.get_verify(ALICE)
        self.assertEqual(status, 200)
        self.assertEqual(set(payload.keys()), {"ok", "entries", "first_bad_index"})
        self.assertIs(payload["ok"], True)
        self.assertIsNone(payload["first_bad_index"])
        self.assertEqual(payload["entries"], 2)

    def test_verify_entries_count_is_before_own_audit_read(self):
        """AU-9: entries is counted before this read's own audit_read
        entry: after the call the log holds entries+1, and a second
        call reports that higher count."""
        self.audit.record("alice", "contact_create", "ct-1")
        status, payload = self.get_verify(ALICE)
        self.assertEqual(status, 200)
        self.assertEqual(payload["entries"], 1)
        # The verify's own audit_read entry was appended after counting.
        self.assertEqual(len(self.audit.entries()), payload["entries"] + 1)
        self.assertEqual(self.audit.entries()[-1]["action"], "audit_read")
        status, payload2 = self.get_verify(ALICE)
        self.assertEqual(status, 200)
        self.assertEqual(payload2["entries"], 2)
        self.assertEqual(len(self.audit.entries()), 3)

    def test_verify_reports_tampered_chain_at_exact_index(self):
        """AU-9: after a stored entry is mutated in place, the
        endpoint reports ok False and first_bad_index at that index,
        with entries still counted before its own audit_read entry."""
        self.audit.record("alice", "contact_create", "ct-1")
        self.audit.record("bob", "message_compose", "msg-1")
        self.audit.record("alice", "channel_create", "ch-1")
        self.audit._entries[1]["actor"] = "mallory"
        status, payload = self.get_verify(DANA)
        self.assertEqual(status, 200)
        self.assertIs(payload["ok"], False)
        self.assertEqual(payload["first_bad_index"], 1)
        self.assertEqual(payload["entries"], 3)

    def test_verify_allowed_for_auditor_and_admin(self):
        """AU-6/AC-5: GET /audit/verify -> 200 for both audit_read
        holders: admin (alice) and auditor (dana)."""
        for headers in (ALICE, DANA):
            with self.subTest(headers=headers):
                status, payload = self.get_verify(headers)
                self.assertEqual(status, 200)
                self.assertIn("ok", payload)

    def test_verify_forbidden_without_audit_read(self):
        """AU-6: GET /audit/verify -> 403 for operator (bob) and
        viewer (carol), neither of whom holds audit_read."""
        for headers in (BOB, CAROL):
            with self.subTest(headers=headers):
                status, payload = self.get_verify(headers)
                self.assertEqual(status, 403)
                self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
