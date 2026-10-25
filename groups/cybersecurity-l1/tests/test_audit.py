"""Audit-log tests.

Traces to: UNION-SPEC Core function 11 (Audit log); Implementation
contract for ``cyber/audit.py`` and the store's audit action names in
``cyber/store.py``; control families AU-2, AU-3, AU-6, AU-9
(append-only store).
"""

import json
import os
import tempfile
import unittest
from datetime import datetime

from cyber_helpers import (
    ADMIN,
    ANALYST,
    VIEWER,
    create_sample_risk,
    fresh_store,
    ingest_sample_finding,
    make_asset,
    make_store,
)
from cyber.audit import AuditLog
from cyber.errors import PermissionDenied


def _parse_ts(ts):
    """Parse a contract UTC ISO-8601 timestamp (must not raise)."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLogInMemory(unittest.TestCase):
    """Core: Audit log — record()/entries() contract."""

    def test_record_and_entries_roundtrip(self):
        """Core: Audit log. Contract: entries() returns dicts with keys
        ts, actor, action, target, details."""
        log = AuditLog()
        log.record("alice", "asset_create", "asset-1", {"name": "srv"})
        entries = log.entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(
            set(entry.keys()), {"ts", "actor", "action", "target", "details"}
        )
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "asset_create")
        self.assertEqual(entry["target"], "asset-1")
        self.assertEqual(entry["details"], {"name": "srv"})

    def test_details_defaults_to_empty(self):
        """Core: Audit log. Contract: record(..., details=None)."""
        log = AuditLog()
        log.record("bob", "search", "find-1")
        self.assertIn(log.entries()[0]["details"], (None, {}))

    def test_timestamp_is_isoformat_utc_string(self):
        """Core: Audit log (AU-3). Contract: all timestamps are UTC
        ISO-8601 — each entry carries a parseable timestamp string."""
        log = AuditLog()
        log.record("alice", "asset_create", "asset-1")
        ts = log.entries()[0]["ts"]
        self.assertIsInstance(ts, str)
        self.assertTrue(ts)
        parsed = _parse_ts(ts)  # must not raise
        self.assertIsNotNone(parsed)

    def test_entries_preserve_record_order(self):
        """Core: Audit log (AU-2). A trail is chronological: entries
        come back in the order they were recorded."""
        log = AuditLog()
        for i in range(5):
            log.record("alice", "search", "find-%d" % i)
        targets = [e["target"] for e in log.entries()]
        self.assertEqual(
            targets, ["find-0", "find-1", "find-2", "find-3", "find-4"]
        )

    def test_append_only_earlier_entries_never_change(self):
        """Core: Audit log (AU-9). Recording later events must not
        mutate or drop earlier entries."""
        log = AuditLog()
        log.record("alice", "asset_create", "asset-1")
        first_snapshot = dict(log.entries()[0])
        log.record("alice", "finding_ingest", "find-1")
        log.record("carol", "finding_ingest:denied", "asset-1")
        entries = log.entries()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0], first_snapshot)

    def test_empty_log_has_no_entries(self):
        """Core: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_details_dict_is_stored_verbatim(self):
        """Core: Audit log (AU-3 content of audit records)."""
        log = AuditLog()
        details = {"count": 2, "ids": ["find-1", "find-2"]}
        log.record("bob", "finding_ingest", "asset-1", details)
        self.assertEqual(log.entries()[0]["details"], details)


class TestAuditLogFile(unittest.TestCase):
    """Core: Audit log — optional JSONL file backing (contract)."""

    def test_file_backed_log_writes_jsonl(self):
        """Core: Audit log. Contract: 'optional JSONL file
        persistence' — with a path, each record is one JSON line."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "asset_create", "asset-1", {"name": "s"})
            log.record("bob", "search", "find-1")
            with open(path, encoding="utf-8") as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            parsed = [json.loads(ln) for ln in lines]
            self.assertEqual(parsed[0]["actor"], "alice")
            self.assertEqual(parsed[1]["action"], "search")
            for entry in parsed:
                self.assertEqual(
                    set(entry.keys()),
                    {"ts", "actor", "action", "target", "details"},
                )

    def test_file_backed_log_survives_reopen(self):
        """Core: Audit log (AU-9). Contract: the log 'reloads an
        existing file on construction' and stays append-only across
        restarts."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            AuditLog(path).record("alice", "asset_create", "asset-1")
            reopened = AuditLog(path)
            entries = reopened.entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["target"], "asset-1")
            reopened.record("alice", "finding_ingest", "asset-1")
            self.assertEqual(len(AuditLog(path).entries()), 2)


class TestStoreAuditing(unittest.TestCase):
    """Core: Audit log — the store records each mutation action name."""

    def test_store_records_the_full_mutation_flow(self):
        """Core: Audit log. Contract: the store records every
        successful mutation and every search with the spec's action
        names: asset_create, asset_update, finding_ingest,
        finding_transition, finding_assign, risk_create,
        risk_transition, control_assess, search."""
        audit = AuditLog()
        store, asset, finding = make_store(audit=audit)
        store.update_asset(asset["id"], actor=ANALYST, owner="sec-ops")
        store.transition_finding(finding["id"], "triaged", actor=ANALYST)
        store.assign_finding(finding["id"], "bob", actor=ANALYST)
        risk = create_sample_risk(store, finding_ids=[finding["id"]])
        store.transition_risk(risk["id"], "monitoring", actor=ANALYST)
        store.assess_control("AC-2", "implemented", actor=ANALYST,
                             evidence="account review")
        store.search(actor=ANALYST, q="openssl")

        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "asset_create", "asset_update", "finding_ingest",
            "finding_transition", "finding_assign", "risk_create",
            "risk_transition", "control_assess", "search",
        ):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)

    def test_store_entries_carry_actor_and_target(self):
        """Core: Audit log (AU-3). Store-recorded entries name the
        actor who performed the mutation and its target."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        asset = make_asset(store, actor=ADMIN)
        entry = audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "asset_create")
        self.assertEqual(entry["target"], asset["id"])

    def test_finding_ingest_details_carry_count_and_ids(self):
        """Core: Finding ingestion / Audit log. Contract:
        ingest_finding audits finding_ingest with details
        {"count": 1, "ids": [id]}."""
        audit = AuditLog()
        store, asset, finding = make_store(audit=audit)
        ingest_entries = [
            e for e in audit.entries() if e["action"] == "finding_ingest"
        ]
        self.assertEqual(len(ingest_entries), 1)
        self.assertEqual(
            ingest_entries[0]["details"],
            {"count": 1, "ids": [finding["id"]]},
        )

    def test_transition_details_carry_from_and_to(self):
        """Core: Finding lifecycle / Audit log. Contract:
        transition_finding audits finding_transition with details
        {"from": old, "to": new} (and risk_transition likewise)."""
        audit = AuditLog()
        store, asset, finding = make_store(audit=audit)
        store.transition_finding(finding["id"], "triaged", actor=ANALYST)
        risk = create_sample_risk(store)
        store.transition_risk(risk["id"], "treated", actor=ANALYST)
        by_action = {}
        for entry in audit.entries():
            by_action.setdefault(entry["action"], entry)
        self.assertEqual(
            by_action["finding_transition"]["details"],
            {"from": "new", "to": "triaged"},
        )
        self.assertEqual(
            by_action["risk_transition"]["details"],
            {"from": "open", "to": "treated"},
        )

    def test_control_assess_and_search_details(self):
        """Core: Control mapping / Search / Audit log. Contract:
        assess_control audits control_assess with details
        {"status": status}; search audits search with {"q": q}."""
        audit = AuditLog()
        store, asset, finding = make_store(audit=audit)
        store.assess_control("RA-5", "partially_implemented",
                             actor=ANALYST)
        store.search(actor=ANALYST, q="openssl")
        by_action = {}
        for entry in audit.entries():
            by_action.setdefault(entry["action"], entry)
        self.assertEqual(
            by_action["control_assess"]["details"],
            {"status": "partially_implemented"},
        )
        self.assertEqual(by_action["search"]["details"], {"q": "openssl"})

    def test_posture_summary_does_not_audit(self):
        """Core: Posture reporting / Audit log. Contract:
        posture_summary 'Does not audit' — the entry count is unchanged
        across a summary call."""
        audit = AuditLog()
        store, asset, finding = make_store(audit=audit)
        before = len(audit.entries())
        store.posture_summary(actor=ANALYST)
        self.assertEqual(len(audit.entries()), before)

    def test_failed_mutation_records_no_audit_entry(self):
        """Core: Audit log. Contract: 'a failed operation changes
        nothing, consumes no id, and writes no audit entry' — a denied
        ingest (viewer lacks ingest) adds no finding_ingest entry."""
        audit = AuditLog()
        store, asset, finding = make_store(audit=audit)
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            ingest_sample_finding(store, asset["id"], actor=VIEWER,
                                  title="viewer attempt")
        self.assertEqual(len(audit.entries()), before)

    def test_store_without_audit_log_still_works(self):
        """Core: Audit log. Contract: CyberStore(audit=None) — the
        audit log is optional; mutations succeed with none attached."""
        store = fresh_store()
        asset = make_asset(store)
        self.assertEqual(asset["id"], "asset-1")
        finding = ingest_sample_finding(store, asset["id"])
        self.assertEqual(finding["id"], "find-1")


if __name__ == "__main__":
    unittest.main()
