"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC Core function 11 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-5 (audit failure response): when the JSONL
append raises ``OSError``, ``AuditLog.record`` rolls back the
in-memory append and raises ``AuditWriteError``; the store is
audit-before-commit, so an operation whose audit write fails changes
nothing and consumes no id; over HTTP the failure surfaces as
500 {"error": "audit write failed"}.
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

from collab_helpers import ADMIN, USERS_REGISTRY
from collab.audit import AuditLog
from collab.errors import AuditWriteError, CollabError
from collab.service import make_server
from collab.store import CollabStore


def _break_log_file(log):
    """Make a file-backed log's path unwritable mid-flight: replace
    the JSONL file with a directory of the same name, so the next
    append raises IsADirectoryError (an OSError). (Technique adapted
    from analytics-l3's test_audit_failure.py.)"""
    if os.path.exists(log.path):
        os.remove(log.path)
    os.mkdir(log.path)


class TestRecordFailClosed(unittest.TestCase):
    """AU-5: record() fails closed on OSError, with rollback."""

    def test_failed_record_raises_and_entries_unchanged(self):
        """AU-5: an unwritable JSONL path makes record() raise
        AuditWriteError and leaves entries() exactly as it was
        (rollback -- memory and file never diverge silently)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "workspace_create", "ws-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "search", "ws-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5/AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "workspace_create", "ws-1")
            log.record("alice", "search", "ws-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "file_share", "ws-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_collab_error(self):
        """AU-5: AuditWriteError derives from CollabError, so the
        package's single error hierarchy covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, CollabError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store is audit-before-commit -- a failed audit
    write means the operation changes nothing and consumes no id."""

    def test_create_workspace_with_broken_audit_changes_nothing(self):
        """AU-5: CollabStore.create_workspace backed by a failing
        audit raises AuditWriteError, list_workspaces(admin) == [],
        and no id is consumed: after swapping in a working audit
        log, the next successful create is ws-1."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CollabStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_workspace("doomed", ADMIN)
            self.assertEqual(store.list_workspaces(ADMIN), [])
            # Prove no id was consumed by the failed operation.
            store.audit = AuditLog()
            workspace = store.create_workspace("recovered", ADMIN)
            self.assertEqual(workspace["id"], "ws-1")
            self.assertEqual(
                [w["id"] for w in store.list_workspaces(ADMIN)], ["ws-1"]
            )


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: AuditWriteError surfaces as
    500 {"error": "audit write failed"} and nothing is created."""

    def test_create_workspace_over_http_fails_closed(self):
        """AU-5: POST /workspaces against a server whose audit path
        fails on write -> 500 {"error": "audit write failed"}, and
        GET /workspaces as alice afterwards shows no workspace."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CollabStore(audit=audit)
            _break_log_file(audit)
            server = make_server(
                "127.0.0.1", 0, store, audit, dict(USERS_REGISTRY)
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request(
                    "POST",
                    "/workspaces",
                    body=json.dumps({"name": "doomed"}),
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
                self.assertEqual(status, 500)
                self.assertEqual(
                    json.loads(raw.decode("utf-8")),
                    {"error": "audit write failed"},
                )

                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request(
                    "GET",
                    "/workspaces",
                    headers={"X-User": "alice", "X-Role": "admin"},
                )
                resp = conn.getresponse()
                raw = resp.read()
                status = resp.status
                conn.close()
                self.assertEqual(status, 200)
                payload = json.loads(raw.decode("utf-8"))
                items = (
                    payload["workspaces"]
                    if isinstance(payload, dict)
                    else payload
                )
                self.assertEqual(items, [])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
            self.assertEqual(store.list_workspaces(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
