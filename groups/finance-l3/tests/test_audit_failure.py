"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC Core function 11 (Audit log) as
uplifted to the FedRAMP High baseline -- AU-5 (audit failure
response): when the JSONL append raises ``OSError``,
``AuditLog.record`` rolls back the in-memory append and raises
``AuditWriteError``; in-memory state and file never diverge
silently, and callers (store, service) let it propagate so an
operation whose audit write fails does not proceed -- the store
rolls the whole operation back (records and id counters).
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

import finance_helpers as H
from finance_helpers import USERS_REGISTRY
from finance.audit import AuditLog
from finance.errors import AuditWriteError, FinanceError
from finance.service import make_server
from finance.store import FinanceStore


def _break_log_file(log):
    """Make a file-backed log's path unwritable mid-flight: replace
    the JSONL file with a directory of the same name, so the next
    append raises IsADirectoryError (an OSError)."""
    if os.path.exists(log.path):
        os.remove(log.path)
    os.mkdir(log.path)


class TestRecordFailClosed(unittest.TestCase):
    """AU-5: record() fails closed on OSError."""

    def test_failed_record_raises_audit_write_error_and_rolls_back(self):
        """AU-5: an unwritable JSONL path makes record() raise
        AuditWriteError and leaves entries() exactly as it was."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "program_create", "prog-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "participant_create", "part-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "program_create", "prog-1")
            log.record("alice", "participant_create", "part-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "participant_status", "part-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_finance_error(self):
        """AU-5: AuditWriteError derives from FinanceError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, FinanceError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store rolls the operation back -- it does not
    proceed when its audit write fails."""

    def test_create_program_with_broken_audit_rolls_back(self):
        """AU-5: create_program backed by an audit log whose write
        fails raises AuditWriteError, creates NO program, and
        consumes NO id (the next successful create is prog-1)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = FinanceStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_program("rollback-program", H.ADMIN)
            self.assertEqual(store.list_programs(H.ADMIN), [])
            # Repair the log: on THIS store, swapping in a working
            # log shows the first successful id is prog-1, not prog-2
            # -- the failed create consumed no id.
            store.audit = AuditLog()
            program = store.create_program("rollback-program", H.ADMIN)
            self.assertEqual(program["id"], "prog-1")

    def test_participant_status_with_broken_audit_rolls_back(self):
        """AU-5: a participant status change whose audit write fails
        leaves the participant in its original status."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = FinanceStore(audit=audit)
            program = store.create_program("status-program", H.MEMBER)
            participant = store.create_participant(
                program["id"], "emp-1", "employee", H.MEMBER)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.set_participant_status(
                    program["id"], participant["id"], "inactive", H.MEMBER)
            store.audit = AuditLog()
            self.assertEqual(
                store.get_participant(
                    program["id"], participant["id"], H.MEMBER)["status"],
                "active")


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_create_program_over_http_fails_closed(self):
        """AU-5: POST /programs against a store whose audit log
        cannot write is not a success (not 201 -- it surfaces as an
        error via the FinanceError arm), and no program is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = FinanceStore(audit=audit)
            _break_log_file(audit)
            server = make_server(
                "127.0.0.1", 0, store, audit, dict(USERS_REGISTRY))
            port = server.server_address[1]
            thread = threading.Thread(
                target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection(
                    "127.0.0.1", port, timeout=10)
                conn.request(
                    "POST",
                    "/programs",
                    body=json.dumps({"name": "http-program"}),
                    headers={
                        "X-User": "alice",
                        "X-Role": "admin",
                        "Content-Type": "application/json",
                    },
                )
                resp = conn.getresponse()
                resp.read()
                status = resp.status
                conn.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
            self.assertNotIn(status, (200, 201))
            self.assertEqual(store.list_programs(H.ADMIN), [])


if __name__ == "__main__":
    unittest.main()
