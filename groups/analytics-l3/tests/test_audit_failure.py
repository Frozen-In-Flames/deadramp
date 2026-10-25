"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC Core function 10 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-5 (audit failure response): when the JSONL
append raises ``OSError``, ``AuditLog.record`` rolls back the
in-memory append and raises ``AuditWriteError``; in-memory state and
file never diverge silently, and callers (store, service) let it
propagate so an operation whose audit write fails does not proceed.
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

from analytics_helpers import ADMIN, sales_json_text
from analytics.audit import AuditLog
from analytics.errors import AnalyticsError, AuditWriteError
from analytics.service import make_server
from analytics.store import DatasetStore


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
            log.record("alice", "ingest", "ds-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "query", "ds-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "ingest", "ds-1")
            log.record("alice", "query", "ds-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "export", "ds-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_an_analytics_error(self):
        """AU-5: AuditWriteError derives from AnalyticsError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, AnalyticsError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: callers let AuditWriteError propagate -- the operation
    does not proceed."""

    def test_ingest_with_broken_audit_raises_and_creates_no_dataset(self):
        """AU-5: a DatasetStore ingest backed by an audit log whose
        write fails raises AuditWriteError and creates no dataset
        (registry, rows and id sequence all rolled back)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DatasetStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.ingest_json("sales", sales_json_text(), ADMIN)
            self.assertEqual(store.list(), [])


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_ingest_over_http_fails_closed(self):
        """AU-5: POST /datasets against a store whose audit log
        cannot write is not a success, and no dataset is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DatasetStore(audit=audit)
            _break_log_file(audit)
            server = make_server(
                "127.0.0.1", 0, store, audit, {"bob": "analyst"}
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection(
                    "127.0.0.1", port, timeout=10
                )
                conn.request(
                    "POST",
                    "/datasets",
                    body=json.dumps(
                        {
                            "name": "sales",
                            "format": "json",
                            "data": sales_json_text(),
                        }
                    ),
                    headers={
                        "X-User": "bob",
                        "X-Role": "analyst",
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
            self.assertEqual(store.list(), [])


if __name__ == "__main__":
    unittest.main()
