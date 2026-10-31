"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC Core function 10 (append-only audit) as
uplifted to the FedRAMP High baseline — AU-5 (audit failure
response): when the JSONL append raises ``OSError``,
``AuditLog.record`` rolls back the in-memory append and raises
``AuditWriteError``; in-memory state and file never diverge
silently, and callers (store, service) let it propagate so an
operation whose audit write fails does not proceed — the store
rolls the whole operation back (records and id counters).
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

import grc_helpers as H
from grc.audit import AuditLog
from grc.errors import AuditWriteError, GrcError
from grc.service import make_server
from grc.store import GrcStore


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
            log.record("alice", "system_create", "SYS-001")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "finding_create", "find-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind —
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "system_create", "SYS-001")
            log.record("alice", "finding_create", "find-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "finding_transition", "find-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_grc_error(self):
        """AU-5: AuditWriteError derives from GrcError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, GrcError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store rolls the operation back — it does not
    proceed when its audit write fails."""

    def test_create_system_with_broken_audit_rolls_back(self):
        """AU-5: create_system backed by an audit log whose write
        fails raises AuditWriteError and creates NO system."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = GrcStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_system("SYS-001", "example portal", H.MEMBER)
            self.assertEqual(store.list_systems(H.MEMBER), [])

    def test_create_evidence_with_broken_audit_consumes_no_id(self):
        """AU-5: create_evidence whose audit write fails creates NO
        evidence record and consumes NO id — the first successful
        create afterwards is ev-1, not ev-2."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = GrcStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_evidence(
                    "scan report", "content", ["IA-2"], [], H.MEMBER)
            self.assertEqual(store.list_evidence(H.MEMBER), [])
            store.audit = AuditLog()
            evidence = store.create_evidence(
                "scan report", "content", ["IA-2"], [], H.MEMBER)
            self.assertEqual(evidence["id"], "ev-1")

    def test_transition_with_broken_audit_rolls_back(self):
        """AU-5: a finding transition whose audit write fails leaves
        the finding in its original lifecycle status."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store, system, indicator = H.make_store(audit=audit)
            finding = H.make_finding(store)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.transition_finding(
                    finding["id"], "in_progress", H.MEMBER)
            store.audit = AuditLog()
            self.assertEqual(
                store.get_finding(finding["id"], H.MEMBER)["status"],
                "open")


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when
    the audit write fails."""

    def test_create_system_over_http_fails_closed(self):
        """AU-5: POST /systems against a store whose audit log
        cannot write is not a success, and no system is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = GrcStore(audit=audit)
            _break_log_file(audit)
            server = make_server(
                "127.0.0.1", 0, store, audit, dict(H.USERS_REGISTRY))
            port = server.server_address[1]
            thread = threading.Thread(
                target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection(
                    "127.0.0.1", port, timeout=10)
                conn.request(
                    "POST",
                    "/systems",
                    body=json.dumps(
                        {"ref": "SYS-HTTP", "name": "portal"}),
                    headers={
                        "X-User": "bob",
                        "X-Role": "member",
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
            self.assertEqual(store.list_systems(H.ADMIN), [])


if __name__ == "__main__":
    unittest.main()
