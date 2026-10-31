"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: Core function 14 (audit log) as uplifted to the FedRAMP
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

import storage_helpers as H
from storage.audit import AuditLog
from storage.errors import AuditWriteError, StorageError
from storage.service import make_server
from storage.store import StorageStore

USERS = {"alice": "admin", "bob": "operator", "carol": "viewer",
         "dana": "auditor"}


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
            log.record("alice", "organization_create", "org-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "message_archive", "msg-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "organization_create", "org-1")
            log.record("alice", "message_archive", "msg-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "disposition_record", "dsp-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_storage_error(self):
        """AU-5: AuditWriteError derives from StorageError, so the
        package's single error hierarchy covers audit failures (and
        the service layer maps it explicitly, before StorageError)."""
        self.assertTrue(issubclass(AuditWriteError, StorageError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store rolls the operation back -- it does not
    proceed when its audit write fails."""

    def test_create_organization_with_broken_audit_rolls_back(self):
        """AU-5: create_organization backed by an audit log whose
        write fails raises AuditWriteError, creates NO organization,
        and consumes NO id (the next successful create is org-1)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = StorageStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_organization(H.ADMIN, "ORG-0001", "Records")
            self.assertEqual(store.list_organizations(H.ADMIN), [])
            # Repair: swapping in a working log shows the first
            # successful id is org-1, not org-2.
            store.audit = AuditLog()
            organization = store.create_organization(
                H.ADMIN, "ORG-0001", "Records")
            self.assertEqual(organization["id"], "org-1")

    def test_custody_retire_with_broken_audit_rolls_back(self):
        """AU-5: a custody retirement whose audit write fails leaves
        the custody record active."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = StorageStore(audit=audit)
            org, _policy, collection = H.make_archive(store)
            custody = H.make_custody(store, org, collection)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.retire_custody(H.OPERATOR, custody["id"])
            store.audit = AuditLog()
            active = store.list_custodies(
                H.ADMIN, collection_id=collection["id"], status="active")
            self.assertEqual([c["id"] for c in active], [custody["id"]])


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_create_organization_over_http_fails_closed(self):
        """AU-5: POST /organizations against a server whose audit
        write fails returns 500 with body exactly
        {"error": "audit write failed"}, and no organization is
        created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = StorageStore(audit=audit)
            _break_log_file(audit)
            server = make_server(
                "127.0.0.1", 0, store=store, audit=audit, users=USERS)
            port = server.server_address[1]
            thread = threading.Thread(
                target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection(
                    "127.0.0.1", port, timeout=10)
                conn.request(
                    "POST",
                    "/organizations",
                    body=json.dumps({"ref": "ORG-0001", "label": "Records"}),
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
            self.assertEqual(store.list_organizations(H.ADMIN), [])


if __name__ == "__main__":
    unittest.main()
