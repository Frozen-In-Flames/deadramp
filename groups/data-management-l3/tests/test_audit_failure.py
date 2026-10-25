"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC Core function 12 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-5 (audit failure response): when the JSONL
append raises ``OSError``, ``AuditLog.record`` rolls back the
in-memory append and raises ``AuditWriteError``; the store's
snapshot rollback (``DataMgmtStore._atomic``) then rolls the whole
operation back -- no object created, no object changed, no id
consumed -- and the service layer lets the error propagate, so an
operation whose audit write fails does not proceed.
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

from datamgmt_helpers import STEWARD, VIEWER
from datamgmt.audit import AuditLog
from datamgmt.errors import AuditWriteError, DataMgmtError
from datamgmt.service import make_server
from datamgmt.store import DataMgmtStore


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
            log.record("alice", "dataset_create", "ds-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "search", "claims")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "dataset_create", "ds-1")
            log.record("alice", "search", "claims")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "export_create", "ds-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_datamgmt_error(self):
        """AU-5: AuditWriteError derives from DataMgmtError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, DataMgmtError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store rolls the whole operation back when its audit
    write fails -- no object, no state change, no id consumed."""

    def test_create_dataset_with_broken_audit_rolls_back(self):
        """AU-5: create_dataset backed by an unwritable audit log
        raises AuditWriteError, creates no dataset, and consumes no
        id: once the log path is repaired, the next create is ds-1."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DataMgmtStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_dataset("Claims Extract", "Nightly", STEWARD)
            self.assertEqual(store.list_datasets(actor=STEWARD), [])
            os.rmdir(path)  # repair: the next append recreates the file
            dataset = store.create_dataset("Claims Extract", "Nightly", STEWARD)
            self.assertEqual(dataset["id"], "ds-1")

    def test_decide_with_broken_audit_rolls_back_decision_and_grant(self):
        """AU-5: decide_access_request whose audit write fails leaves
        the request "requested" and mints no grant -- the decision
        does not proceed."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DataMgmtStore(audit=audit)
            dataset = store.create_dataset("Claims Extract", "Nightly", STEWARD)
            req = store.request_access(dataset["id"], "research use", VIEWER)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.decide_access_request(req["id"], True, STEWARD)
            # Reads do not audit, so they still answer from state.
            self.assertEqual(
                store.get_access_request(req["id"], STEWARD)["status"],
                "requested",
            )
            self.assertEqual(store.list_grants(actor=STEWARD), [])
            self.assertEqual(audit.verify_chain(), (True, None))


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_create_dataset_over_http_fails_closed(self):
        """AU-5: POST /datasets against a store whose audit log
        cannot write is not a success, and no dataset is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DataMgmtStore(audit=audit)
            _break_log_file(audit)
            server = make_server(
                "127.0.0.1", 0, store, audit, {"bob": "steward"}
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request(
                    "POST",
                    "/datasets",
                    body=json.dumps(
                        {"name": "Claims Extract", "description": "Nightly"}
                    ),
                    headers={
                        "X-User": "bob",
                        "X-Role": "steward",
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
            self.assertEqual(store.list_datasets(actor=STEWARD), [])


if __name__ == "__main__":
    unittest.main()
