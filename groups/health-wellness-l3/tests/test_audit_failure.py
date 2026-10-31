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

import health_helpers as H
from health.audit import AuditLog
from health.errors import AuditWriteError, HealthError
from health.service import USERS, make_server
from health.store import HealthStore


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
            log.record("alice", "program_create", "prg-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "enrollment_create", "enr-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "program_create", "prg-1")
            log.record("alice", "enrollment_create", "enr-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "plan_create", "pln-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_health_error(self):
        """AU-5: AuditWriteError derives from HealthError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, HealthError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store rolls the operation back -- it does not
    proceed when its audit write fails."""

    def test_create_participant_with_broken_audit_rolls_back(self):
        """AU-5: create_participant backed by an audit log whose write
        fails raises AuditWriteError, creates NO participant, and
        consumes NO id (the next successful create is par-1)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = HealthStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_participant("erin", H.ADMIN)
            self.assertEqual(store.list_participants(H.ADMIN), [])
            # Repair by swapping in a working log: on THIS store, the
            # first successful id is par-1, not par-2 -- the id
            # sequence was rolled back too.
            store.audit = AuditLog()
            participant = store.create_participant("erin", H.ADMIN)
            self.assertEqual(participant["id"], "par-1")

    def test_complete_plan_with_broken_audit_rolls_back(self):
        """AU-5: completing a plan whose audit write fails leaves the
        plan incomplete (completed_on stays None)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store, program, participant = H.make_store(audit=audit)
            plan = store.create_plan(
                participant["id"], program["id"], "Daily checks",
                "2026-06-01", H.CLINICIAN)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.complete_plan(plan["id"], "2026-06-02", H.CLINICIAN)
            store.audit = AuditLog()
            self.assertIsNone(
                store.get_plan(plan["id"], H.ADMIN)["completed_on"])


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_create_participant_over_http_fails_closed(self):
        """AU-5: POST /participants against a store whose audit log
        cannot write is not a success, and no participant is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = HealthStore(audit=audit)
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
                    "/participants",
                    body=json.dumps({"participant_ref": "ref-http"}),
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
            self.assertEqual(store.list_participants(H.ADMIN), [])


if __name__ == "__main__":
    unittest.main()
