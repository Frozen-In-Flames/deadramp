"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC Core function 10 (RBAC + audit log) as
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

import crm_helpers as H
from crm.audit import AuditLog
from crm.errors import AuditWriteError, CrmError
from crm.service import USERS, make_server
from crm.store import CrmStore


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
            log.record("alice", "account_create", "acct-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "case_create", "case-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "account_create", "acct-1")
            log.record("alice", "case_create", "case-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "case_transition", "case-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_crm_error(self):
        """AU-5: AuditWriteError derives from CrmError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, CrmError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store rolls the operation back -- it does not
    proceed when its audit write fails."""

    def test_create_account_with_broken_audit_rolls_back(self):
        """AU-5: create_account backed by an audit log whose write
        fails raises AuditWriteError, creates NO account, and
        consumes NO id (the next successful create is acct-1)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CrmStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_account(H.ADMIN, "ACCT-1")
            self.assertEqual(store.list_accounts(H.ADMIN), [])
            # Repair the log path: a fresh file-backed log on a new
            # store proves the id sequence was rolled back too --
            # and on THIS store, swapping in a working log shows the
            # first successful id is acct-1, not acct-2.
            store.audit = AuditLog()
            account = store.create_account(H.ADMIN, "ACCT-1")
            self.assertEqual(account["id"], "acct-1")

    def test_transition_with_broken_audit_rolls_back(self):
        """AU-5: a case transition whose audit write fails leaves the
        case in its original status."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CrmStore(audit=audit)
            case = store.create_case(H.OPERATOR, "inquiry", "q")
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.transition_case(case["id"], H.OPERATOR, "in_progress")
            store.audit = AuditLog()
            self.assertEqual(
                store.get_case(case["id"], H.OPERATOR)["status"], "open")


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_create_account_over_http_fails_closed(self):
        """AU-5: POST /accounts against a store whose audit log
        cannot write is not a success, and no account is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CrmStore(audit=audit)
            _break_log_file(audit)
            server = make_server(
                "127.0.0.1", 0, store, audit, dict(USERS))
            port = server.server_address[1]
            thread = threading.Thread(
                target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection(
                    "127.0.0.1", port, timeout=10)
                conn.request(
                    "POST",
                    "/accounts",
                    body=json.dumps({"reference": "ACCT-HTTP"}),
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
            self.assertEqual(store.list_accounts(H.ADMIN), [])


if __name__ == "__main__":
    unittest.main()
