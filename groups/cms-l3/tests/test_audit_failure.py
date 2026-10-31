"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC.md Core function 12 (Audit log) as uplifted to
the FedRAMP High baseline -- AU-5 (audit failure response): when the
JSONL append raises ``OSError``, ``AuditLog.record`` rolls back the
in-memory append and raises ``AuditWriteError``; the store wraps every
mutating operation in the ``_atomic`` snapshot guard so the whole
operation rolls back (no object, no change, no id consumed), and the
service answers 500 -- an operation whose audit write fails does not
proceed.
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

from cms_helpers import ADMIN, USERS, fresh_store
from cms.audit import AuditLog
from cms.errors import AuditWriteError, CmsError
from cms.service import make_server
from cms.store import CmsStore


def _break_log_file(log):
    """Make a file-backed log's path unwritable mid-flight: replace
    the JSONL file with a directory of the same name, so the next
    append raises IsADirectoryError (an OSError)."""
    if os.path.exists(log.path):
        os.remove(log.path)
    os.mkdir(log.path)


class TestRecordFailClosed(unittest.TestCase):
    """[L3] AU-5: record() fails closed on OSError."""

    def test_failed_record_raises_and_rolls_back(self):
        """[L3] AU-5: an unwritable JSONL path makes record() raise AuditWriteError and leaves entries() exactly as it was."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "site_create", "site-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "item_create", "ci-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """[L3] AU-5 / AU-9: the rollback leaves no partial entry -- the surviving chain verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "site_create", "site-1")
            log.record("alice", "item_create", "ci-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "item_create", "ci-2")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_cms_error(self):
        """[L3] AU-5: AuditWriteError derives from CmsError, so the package's single error hierarchy covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, CmsError))


class TestStoreFailClosed(unittest.TestCase):
    """[L3] AU-5: the store rolls the whole operation back."""

    def test_create_site_with_broken_audit_raises_and_creates_nothing(self):
        """[L3] AU-5: create_site backed by an unwritable audit log raises AuditWriteError; no site exists and no id was consumed (the next good create is site-1)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CmsStore(audit=audit)
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_site(ADMIN, "Main", "main")
            self.assertEqual(store.list_sites(ADMIN), [])
            store.audit = AuditLog()
            site = store.create_site(ADMIN, "Main", "main")
            self.assertEqual(site["id"], "site-1")

    def test_create_item_with_broken_audit_rolls_back_item_and_revision(self):
        """[L3] AU-5: a failed item_create leaves no item and no revision behind (_atomic snapshot)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CmsStore(audit=audit)
            site = store.create_site(ADMIN, "Main", "main")
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.create_item(ADMIN, site["id"], "ct-page", "T", "t-slug")
            self.assertEqual(store.list_items(actor=ADMIN), [])
            self.assertEqual(len(store._revisions), 0)


class TestServiceFailClosed(unittest.TestCase):
    """[L3] AU-5 over HTTP: the service does not proceed when the audit write fails."""

    def test_create_site_over_http_fails_closed(self):
        """[L3] AU-5: POST /sites against a store whose audit log cannot write answers 500 (not 201) and creates no site."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CmsStore(audit=audit)
            _break_log_file(audit)
            server = make_server("127.0.0.1", 0, store, audit, dict(USERS))
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request(
                    "POST", "/sites",
                    body=json.dumps({"name": "Main", "slug": "main"}),
                    headers={"X-User": "alice", "X-Role": "admin",
                             "Content-Type": "application/json"},
                )
                resp = conn.getresponse()
                resp.read()
                status = resp.status
                conn.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
            self.assertEqual(status, 500)
            self.assertEqual(store.list_sites(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
