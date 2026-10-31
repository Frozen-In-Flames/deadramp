"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: Core function 10 (audit log) as uplifted to the FedRAMP
High baseline -- AU-5 (audit failure response): when the JSONL
append raises ``OSError``, ``AuditLog.record`` rolls back the
in-memory append and raises ``AuditWriteError``; in-memory state
and file never diverge silently, and callers (store, service) let
it propagate so an operation whose audit write fails does not
proceed -- the store rolls the whole operation back (records and
id counters), and the service returns exactly
500 {"error": "audit write failed"}.
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

import devtools_helpers as H
from devtools.audit import AuditLog
from devtools.errors import AuditWriteError, DevToolsError
from devtools.service import USERS, make_server
from devtools.store import DevToolsStore


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
            log.record("alice", "project_create", "prj-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "issue_create", "iss-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "project_create", "prj-1")
            log.record("alice", "issue_create", "iss-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "issue_set_status", "iss-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_devtools_error(self):
        """AU-5: AuditWriteError derives from DevToolsError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, DevToolsError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store rolls the operation back -- it does not
    proceed when its audit write fails."""

    def test_create_project_with_broken_audit_rolls_back(self):
        """AU-5: create_project backed by an audit log whose write
        fails raises AuditWriteError, creates NO project, and
        consumes NO id (the next successful create is prj-1)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DevToolsStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_project("Widget Service", H.ADMIN)
            self.assertEqual(store.list_projects(H.ADMIN), [])
            # Repair: swapping in a working log shows the first
            # successful id is prj-1, not prj-2.
            store.audit = AuditLog()
            project = store.create_project("Widget Service", H.ADMIN)
            self.assertEqual(project["id"], "prj-1")

    def test_status_transition_with_broken_audit_rolls_back(self):
        """AU-5: an issue status transition whose audit write fails
        leaves the issue in its original status."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DevToolsStore(audit=audit)
            project = store.create_project("Widget Service", H.ADMIN)
            issue = store.create_issue(project["id"], "Bug", H.ADMIN)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.set_issue_status(issue["id"], "in_progress", H.ADMIN)
            store.audit = AuditLog()
            self.assertEqual(
                store.get_issue(issue["id"], H.ADMIN)["status"], "open")


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_create_project_over_http_fails_closed(self):
        """AU-5: POST /projects against a server whose audit write
        fails returns 500 with body exactly
        {"error": "audit write failed"}, and no project is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = DevToolsStore(audit=audit)
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
                    "/projects",
                    body=json.dumps({"name": "Widget Service"}),
                    headers={
                        "X-User": "alice",
                        "X-Role": "admin",
                        "Content-Type": "application/json",
                    },
                )
                resp = conn.getresponse()
                raw = resp.read()
                status = resp.status
                conn.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
            self.assertEqual(status, 500)
            self.assertEqual(
                json.loads(raw.decode("utf-8")),
                {"error": "audit write failed"},
            )
            self.assertEqual(store.list_projects(H.ADMIN), [])


if __name__ == "__main__":
    unittest.main()
