"""Fail-closed audit tests (L3 High uplift, AU-5).

Traces to: UNION-SPEC Core function 11 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-5 (audit failure response): when the JSONL
append raises ``OSError``, ``AuditLog.record`` rolls back the
in-memory append and raises ``AuditWriteError``; in-memory state and
file never diverge silently, and callers (store, service) let it
propagate so an operation whose audit write fails does not proceed.
The store additionally rolls the whole operation back: no object is
created, no id is consumed, no lifecycle state moves.
"""

import http.client
import json
import os
import tempfile
import threading
import unittest

from cyber_helpers import ANALYST, make_asset, sample_finding_item
from cyber.audit import AuditLog
from cyber.errors import AuditWriteError, CyberError
from cyber.service import make_server
from cyber.store import CyberStore


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


class TestRecordFailClosed(unittest.TestCase):
    """AU-5: record() fails closed on OSError."""

    def test_failed_record_raises_audit_write_error_and_rolls_back(self):
        """AU-5: an unwritable JSONL path makes record() raise
        AuditWriteError and leaves entries() exactly as it was."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "asset_create", "asset-1")
            before = log.entries()
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "search", "find-1")
            self.assertEqual(log.entries(), before)

    def test_chain_still_verifies_after_failed_record(self):
        """AU-5 / AU-9: the rollback leaves no partial entry behind --
        the surviving chain still verifies and seq stays contiguous."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "asset_create", "asset-1")
            log.record("alice", "finding_ingest", "find-1")
            _break_log_file(log)
            with self.assertRaises(AuditWriteError):
                log.record("alice", "risk_create", "risk-1")
            self.assertEqual(log.verify_chain(), (True, None))
            self.assertEqual([e["seq"] for e in log.entries()], [0, 1])

    def test_audit_write_error_is_a_cyber_error(self):
        """AU-5: AuditWriteError derives from CyberError, so the
        package's single error hierarchy (and the service layer's
        mapping) covers audit failures."""
        self.assertTrue(issubclass(AuditWriteError, CyberError))


class TestStoreFailClosed(unittest.TestCase):
    """AU-5: the store rolls the whole operation back when its audit
    write fails -- nothing is created, no id is consumed, no state
    moves."""

    def test_create_asset_with_broken_audit_rolls_back(self):
        """AU-5: create_asset against an audit log whose write fails
        raises AuditWriteError; the asset does not exist afterwards
        and its id is not consumed (the next successful create is
        asset-1 again... here asset-2, after the fixture asset-1)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CyberStore(audit=audit)
            first = make_asset(store)
            self.assertEqual(first["id"], "asset-1")
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                make_asset(store, name="second-server")
            self.assertEqual(
                [a["id"] for a in store.list_assets(ANALYST)], ["asset-1"]
            )
            _repair_log_file(audit)
            second = make_asset(store, name="second-server")
            self.assertEqual(second["id"], "asset-2")

    def test_bulk_ingest_with_broken_audit_creates_nothing(self):
        """AU-5: ingest_findings against a broken audit log raises
        AuditWriteError and creates zero findings (the batch's
        atomicity now extends to the audit write itself)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CyberStore(audit=audit)
            asset = make_asset(store)
            _break_log_file(audit)
            items = [
                sample_finding_item(asset["id"], title="One"),
                sample_finding_item(asset["id"], title="Two"),
            ]
            with self.assertRaises(AuditWriteError):
                store.ingest_findings(items, ANALYST)
            self.assertEqual(store.list_findings(ANALYST), [])
            _repair_log_file(audit)
            created = store.ingest_findings(items, ANALYST)
            self.assertEqual(
                [f["id"] for f in created], ["find-1", "find-2"]
            )

    def test_transition_with_broken_audit_leaves_status_unchanged(self):
        """AU-5: transition_finding against a broken audit log raises
        AuditWriteError and the finding's lifecycle does not move."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CyberStore(audit=audit)
            asset = make_asset(store)
            finding = store.ingest_finding(
                sample_finding_item(asset["id"]), ANALYST
            )
            _break_log_file(audit)
            with self.assertRaises(AuditWriteError):
                store.transition_finding(finding["id"], "triaged", ANALYST)
            self.assertEqual(
                store.get_finding(finding["id"], ANALYST)["status"], "new"
            )


class TestServiceFailClosed(unittest.TestCase):
    """AU-5 over HTTP: the service does not silently proceed when the
    audit write fails."""

    def test_create_asset_over_http_fails_closed(self):
        """AU-5: POST /assets against a store whose audit log cannot
        write is not a success, and no asset is created."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path)
            store = CyberStore(audit=audit)
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
                    "/assets",
                    body=json.dumps(
                        {
                            "name": "srv-1",
                            "kind": "server",
                            "owner": "ops",
                            "criticality": "high",
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
            self.assertEqual(store.list_assets(ANALYST), [])


if __name__ == "__main__":
    unittest.main()
