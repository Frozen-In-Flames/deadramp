"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: Core function -- Append-only audit log, as uplifted to the
High baseline -- AU-5 (audit failure response): when the JSONL append
raises ``OSError``, ``AuditLog.record`` rolls back the in-memory
append and raises ``AuditWriteError`` (in ``comm.errors``); the store
is audit-before-commit, so an operation whose audit write fails
changes nothing and consumes no id; over HTTP the failure surfaces as
500 {"error": "audit write failed"}.
Scratch is inside the group ``scratch/`` directory only.
"""

import http.client
import json
import os
import shutil
import threading
import unittest

from comm_helpers import ADMIN, OPERATOR, USERS
from comm.audit import AuditLog
from comm.errors import AuditWriteError, CommError
from comm.service import make_server
from comm.store import CommStore

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch", "test_audit_failure")


def _break_log_file(log):
    """Make a file-backed log's path unwritable mid-flight: replace
    the JSONL file with a directory of the same name, so the next
    append raises IsADirectoryError (an OSError)."""
    if os.path.exists(log.path):
        os.remove(log.path)
    os.mkdir(log.path)


class ScratchBase(unittest.TestCase):
    """AU-5: per-test scratch dir in group scratch/."""

    def setUp(self):
        if os.path.isdir(SCRATCH):
            shutil.rmtree(SCRATCH)
        os.makedirs(SCRATCH, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(SCRATCH, ignore_errors=True))
        self.path = os.path.join(SCRATCH, "audit.jsonl")


class TestRecordFailClosed(ScratchBase):
    """AU-5: record() fails closed on OSError, with rollback."""

    def test_failed_record_raises_and_entries_unchanged(self):
        """AU-5: an unwritable JSONL path makes record() raise
        AuditWriteError and leaves entries() exactly as it was
        (rollback -- memory and file never diverge silently)."""
        log = AuditLog(self.path)
        log.record("alice", "contact_create", "ct-1")
        before = log.entries()
        _break_log_file(log)
        with self.assertRaises(AuditWriteError):
            log.record("alice", "search", "search")
        self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5/AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        log = AuditLog(self.path)
        log.record("alice", "contact_create", "ct-1")
        log.record("alice", "search", "search")
        _break_log_file(log)
        with self.assertRaises(AuditWriteError):
            log.record("alice", "channel_create", "ch-1")
        self.assertEqual(log.verify_chain(), (True, None))
        self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_comm_error(self):
        """AU-5: AuditWriteError derives from CommError, so the
        package's single error hierarchy covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, CommError))


class TestStoreFailClosed(ScratchBase):
    """AU-5: the store is audit-before-commit -- a failed audit
    write means the operation changes nothing and consumes no id."""

    def test_create_contact_with_broken_audit_changes_nothing(self):
        """AU-5: CommStore.create_contact backed by a failing audit
        raises AuditWriteError, list_contacts(admin) == [], and no id
        is consumed: after swapping in a working audit log, the next
        successful create is ct-1 (the first id)."""
        audit = AuditLog(self.path)
        store = CommStore(audit=audit)
        _break_log_file(audit)
        with self.assertRaises(AuditWriteError):
            store.create_contact("Doomed", {"email": "d@x.y"}, OPERATOR)
        self.assertEqual(store.list_contacts(ADMIN), [])
        # Prove no id was consumed by the failed operation.
        store.audit = AuditLog()
        contact = store.create_contact("Recovered", {"email": "r@x.y"}, OPERATOR)
        self.assertEqual(contact["id"], "ct-1")
        self.assertEqual(
            [c["id"] for c in store.list_contacts(ADMIN)], ["ct-1"]
        )


class TestServiceFailClosed(ScratchBase):
    """AU-5 over HTTP: AuditWriteError surfaces as
    500 {"error": "audit write failed"} and nothing is created."""

    def test_create_contact_over_http_fails_closed(self):
        """AU-5: POST /contacts against a server whose audit path
        fails on write -> 500 {"error": "audit write failed"} exactly,
        and GET /contacts as alice afterwards shows no contact."""
        audit = AuditLog(self.path)
        store = CommStore(audit=audit)
        _break_log_file(audit)
        server = make_server("127.0.0.1", 0, store, audit, dict(USERS))
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            conn.request(
                "POST", "/contacts",
                body=json.dumps({"name": "Doomed", "addresses": {"email": "d@x.y"}}),
                headers={"X-User": "alice", "X-Role": "admin",
                         "Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            raw = resp.read()
            status = resp.status
            conn.close()
            self.assertEqual(status, 500)
            self.assertEqual(
                json.loads(raw.decode("utf-8")),
                {"error": "audit write failed"},
            )

            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            conn.request(
                "GET", "/contacts",
                headers={"X-User": "alice", "X-Role": "admin"},
            )
            resp = conn.getresponse()
            raw = resp.read()
            status = resp.status
            conn.close()
            self.assertEqual(status, 200)
            payload = json.loads(raw.decode("utf-8"))
            self.assertEqual(payload["contacts"], [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(store.list_contacts(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
