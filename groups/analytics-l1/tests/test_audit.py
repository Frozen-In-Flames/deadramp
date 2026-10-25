"""Audit-log tests.

Traces to: UNION-SPEC Core function 10 (Audit log) / ranking row 11
(Audit logging & trails, 18 siblings); Implementation contract for
``analytics/audit.py``; control families AU-2, AU-3, AU-6, AU-9
(append-only store).
"""

import json
import os
import tempfile
import unittest
from datetime import datetime

from analytics.audit import AuditLog


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLogInMemory(unittest.TestCase):
    """Core: Audit log — record()/entries() contract."""

    def test_record_and_entries_roundtrip(self):
        """Core: Audit log. entries() returns dicts with keys
        ts, actor, action, target, details (contract)."""
        log = AuditLog()
        log.record("alice", "ingest", "ds-1", {"rows": 5})
        entries = log.entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(
            set(entry.keys()), {"ts", "actor", "action", "target", "details"}
        )
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "ingest")
        self.assertEqual(entry["target"], "ds-1")
        self.assertEqual(entry["details"], {"rows": 5})

    def test_details_defaults_to_empty(self):
        """Core: Audit log. Contract: record(..., details=None)."""
        log = AuditLog()
        log.record("bob", "query", "ds-1")
        self.assertIn(log.entries()[0]["details"], (None, {}))

    def test_timestamp_is_isoformat_utc_string(self):
        """Core: Audit log (AU-3). Each entry carries a parseable UTC
        timestamp."""
        log = AuditLog()
        log.record("alice", "ingest", "ds-1")
        ts = log.entries()[0]["ts"]
        self.assertIsInstance(ts, str)
        self.assertTrue(ts)
        parsed = _parse_ts(ts)  # must not raise
        self.assertIsNotNone(parsed)

    def test_entries_preserve_record_order(self):
        """Core: Audit log (AU-2). A trail is chronological: entries come
        back in the order they were recorded."""
        log = AuditLog()
        for i in range(5):
            log.record("alice", "query", "ds-%d" % i)
        targets = [e["target"] for e in log.entries()]
        self.assertEqual(targets, ["ds-0", "ds-1", "ds-2", "ds-3", "ds-4"])

    def test_append_only_earlier_entries_never_change(self):
        """Core: Audit log (AU-9). Recording later events must not mutate
        or drop earlier entries."""
        log = AuditLog()
        log.record("alice", "ingest", "ds-1")
        first_snapshot = dict(log.entries()[0])
        log.record("alice", "query", "ds-1")
        log.record("carol", "denied", "ds-1")
        entries = log.entries()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0], first_snapshot)

    def test_empty_log_has_no_entries(self):
        """Core: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_details_dict_is_stored_verbatim(self):
        """Core: Audit log (AU-3 content of audit records)."""
        log = AuditLog()
        details = {"format": "csv", "row_count": 42, "nested": {"ok": True}}
        log.record("bob", "export", "ds-2", details)
        self.assertEqual(log.entries()[0]["details"], details)


class TestAuditLogFile(unittest.TestCase):
    """Core: Audit log — optional JSONL file backing (contract)."""

    def test_file_backed_log_writes_jsonl(self):
        """Core: Audit log. With a path, each record is one JSON line."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "ingest", "ds-1", {"rows": 5})
            log.record("bob", "query", "ds-1")
            with open(path, encoding="utf-8") as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            parsed = [json.loads(ln) for ln in lines]
            self.assertEqual(parsed[0]["actor"], "alice")
            self.assertEqual(parsed[1]["action"], "query")
            for entry in parsed:
                self.assertEqual(
                    set(entry.keys()),
                    {"ts", "actor", "action", "target", "details"},
                )

    def test_file_backed_log_survives_reopen(self):
        """Core: Audit log (AU-9 protection of audit information). A new
        AuditLog over the same file sees the prior trail (append-only
        across restarts)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            AuditLog(path).record("alice", "ingest", "ds-1")
            reopened = AuditLog(path)
            entries = reopened.entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["target"], "ds-1")
            reopened.record("alice", "export", "ds-1")
            self.assertEqual(len(AuditLog(path).entries()), 2)


if __name__ == "__main__":
    unittest.main()
