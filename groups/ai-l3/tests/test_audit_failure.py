"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC Core function 10 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-5 (audit failure response): when the JSONL
append raises ``OSError``, ``AuditLog.record`` rolls back the
in-memory append and raises ``AuditWriteError``; in-memory state and
file never diverge silently, and callers (store, service) let it
propagate so an operation whose audit write fails does not proceed.
The store additionally rolls the whole operation back: no object is
created, no id is consumed, no state moves. File scratch lives only
under the group's ``scratch/`` directory, per the suite's convention.
"""

import http.client
import json
import os
import threading
import unittest

from aigateway_helpers import (
    ADMIN,
    MEMBER,
    fresh_store,
    make_scratch_dir,
    remove_scratch_dir,
)
from aigateway.audit import AuditLog
from aigateway.errors import AIGatewayError, AuditWriteError
from aigateway.service import make_server
from aigateway.store import AIGatewayStore


def _break_log_file(log):
    """Make a file-backed log's path unwritable mid-flight: replace
    the JSONL file with a directory of the same name, so the next
    append raises IsADirectoryError (an OSError)."""
    if os.path.exists(log.path):
        os.remove(log.path)
    os.mkdir(log.path)


def _repair_log_file(log):
    """Undo :func:`_break_log_file`: remove the directory so the next
    append recreates a plain file."""
    if os.path.isdir(log.path):
        os.rmdir(log.path)


class ScratchBase(unittest.TestCase):
    def setUp(self):
        self.scratch = make_scratch_dir()
        self.addCleanup(remove_scratch_dir, self.scratch)
        self.path = os.path.join(self.scratch, "audit.jsonl")


class TestRecordFailClosed(ScratchBase):
    """AU-5: record() fails closed on OSError."""

    def test_failed_record_raises_audit_write_error_and_rolls_back(self):
        """AU-5: an unwritable JSONL path makes record() raise
        AuditWriteError and leaves entries() exactly as it was."""
        log = AuditLog(self.path)
        log.record("alice", "model_register", "mdl-1")
        before = log.entries()
        _break_log_file(log)
        with self.assertRaises(AuditWriteError):
            log.record("alice", "invoke", "req-1")
        self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        log = AuditLog(self.path)
        log.record("alice", "model_register", "mdl-1")
        log.record("alice", "invoke", "req-1")
        _break_log_file(log)
        with self.assertRaises(AuditWriteError):
            log.record("alice", "policy_add", "rule-1")
        self.assertEqual(log.verify_chain(), (True, None))
        self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_an_aigateway_error(self):
        """AU-5: AuditWriteError derives from AIGatewayError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, AIGatewayError))


class TestStoreFailClosed(ScratchBase):
    """AU-5: the store rolls the whole operation back when its audit
    write fails -- nothing is created, no id is consumed, no state
    moves."""

    def test_register_model_with_broken_audit_rolls_back(self):
        """AU-5: register_model against an audit log whose write
        fails raises AuditWriteError; the model does not exist
        afterwards and its id is not consumed (the next successful
        register is mdl-2, after the fixture mdl-1)."""
        audit = AuditLog(self.path)
        store = fresh_store(audit=audit)
        first = store.register_model("first", "echo", ADMIN)
        self.assertEqual(first["id"], "mdl-1")
        _break_log_file(audit)
        with self.assertRaises(AuditWriteError):
            store.register_model("second", "echo", ADMIN)
        self.assertEqual(
            [m["id"] for m in store.list_models(ADMIN)], ["mdl-1"]
        )
        _repair_log_file(audit)
        second = store.register_model("second", "echo", ADMIN)
        self.assertEqual(second["id"], "mdl-2")

    def test_invoke_with_broken_audit_stores_no_request(self):
        """AU-5: invoke against a broken audit log raises
        AuditWriteError and stores no request record (the completion
        does not proceed unaudited); after repair the same invoke
        succeeds and mints req-1."""
        audit = AuditLog(self.path)
        store = AIGatewayStore(audit=audit)
        store.register_model("echoer", "echo", ADMIN)
        _break_log_file(audit)
        with self.assertRaises(AuditWriteError):
            store.invoke("echoer", "hello", MEMBER)
        self.assertEqual(store.list_requests(ADMIN), [])
        _repair_log_file(audit)
        record = store.invoke("echoer", "hello", MEMBER)
        self.assertEqual(record["id"], "req-1")
        self.assertEqual(record["status"], "completed")

    def test_set_model_status_with_broken_audit_leaves_status(self):
        """AU-5: set_model_status against a broken audit log raises
        AuditWriteError and the model's status does not move."""
        audit = AuditLog(self.path)
        store = AIGatewayStore(audit=audit)
        store.register_model("echoer", "echo", ADMIN)
        _break_log_file(audit)
        with self.assertRaises(AuditWriteError):
            store.set_model_status("echoer", 1, "deprecated", ADMIN)
        self.assertEqual(
            store.get_model("echoer", ADMIN)["status"], "active"
        )


class TestServiceFailClosed(ScratchBase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_create_model_over_http_fails_closed(self):
        """AU-5: POST /models against a store whose audit log cannot
        write is not a success, and no model is created."""
        audit = AuditLog(self.path)
        store = AIGatewayStore(audit=audit)
        _break_log_file(audit)
        server = make_server(
            "127.0.0.1", 0, store, audit, {"alice": "admin"}
        )
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            conn.request(
                "POST",
                "/models",
                body=json.dumps({"name": "srv-echo", "responder": "echo"}),
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
        self.assertEqual(store.list_models(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
