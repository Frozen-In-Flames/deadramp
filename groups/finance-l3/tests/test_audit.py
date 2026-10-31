"""Audit-log tests.

Traces to: UNION-SPEC Core function 11 (Audit log); Implementation
contract for ``finance/audit.py`` and the store's audit action names
in ``finance/store.py``; control families AU-2, AU-3, AU-6, AU-9
(append-only store).
"""

import json
import os
import tempfile
import unittest
from datetime import datetime

from finance_helpers import (
    ADMIN,
    MEMBER,
    PERIOD,
    VIEWER,
    fresh_store,
    make_accrual,
    make_booking,
    make_employee,
    make_request,
    make_store,
    make_traveler,
)
from finance.audit import AuditLog
from finance.errors import PermissionDenied


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLogInMemory(unittest.TestCase):
    """Core 11: Audit log — record()/entries() contract."""

    def test_record_and_entries_roundtrip(self):
        """Core 11: Audit log. entries() returns dicts with keys
        ts, actor, action, target, details (contract)."""
        log = AuditLog()
        log.record("alice", "program_create", "prog-1", {"name": "acme"})
        entries = log.entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertTrue(
            {"ts", "actor", "action", "target", "details"}
            <= set(entry.keys())
        )
        self.assertTrue({"seq", "prev_hash", "hash"} <= set(entry.keys()))
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "program_create")
        self.assertEqual(entry["target"], "prog-1")
        self.assertEqual(entry["details"], {"name": "acme"})

    def test_details_defaults_to_empty(self):
        """Core 11: Audit log. Contract: record(..., details=None)."""
        log = AuditLog()
        log.record("bob", "budget_set", "prog-1")
        self.assertIn(log.entries()[0]["details"], (None, {}))

    def test_timestamp_is_isoformat_utc_string(self):
        """Core 11: Audit log (AU-3). Each entry carries a parseable
        UTC timestamp."""
        log = AuditLog()
        log.record("alice", "program_create", "prog-1")
        ts = log.entries()[0]["ts"]
        self.assertIsInstance(ts, str)
        self.assertTrue(ts)
        parsed = _parse_ts(ts)  # must not raise
        self.assertIsNotNone(parsed)

    def test_entries_preserve_record_order(self):
        """Core 11: Audit log (AU-2). A trail is chronological: entries
        come back in the order they were recorded."""
        log = AuditLog()
        for i in range(5):
            log.record("alice", "program_create", "prog-%d" % i)
        targets = [e["target"] for e in log.entries()]
        self.assertEqual(
            targets, ["prog-0", "prog-1", "prog-2", "prog-3", "prog-4"]
        )

    def test_append_only_earlier_entries_never_change(self):
        """Core 11: Audit log (AU-9). Recording later events must not
        mutate or drop earlier entries."""
        log = AuditLog()
        log.record("alice", "program_create", "prog-1")
        first_snapshot = dict(log.entries()[0])
        log.record("alice", "participant_create", "part-1")
        log.record("carol", "participant_create:denied", "prog-1")
        entries = log.entries()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0], first_snapshot)

    def test_empty_log_has_no_entries(self):
        """Core 11: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_details_dict_is_stored_verbatim(self):
        """Core 11: Audit log (AU-3 content of audit records)."""
        log = AuditLog()
        details = {"kind": "booking", "count": 2, "nested": {"ok": True}}
        log.record("bob", "booking_create", "bkg-1", details)
        self.assertEqual(log.entries()[0]["details"], details)


class TestAuditLogFile(unittest.TestCase):
    """Core 11: Audit log — optional JSONL file backing (contract)."""

    def test_file_backed_log_writes_jsonl(self):
        """Core 11: Audit log. With a path, each record is one JSON
        line in the file (JSONL persistence)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "program_create", "prog-1", {"name": "t"})
            log.record("bob", "budget_set", "prog-1")
            with open(path, encoding="utf-8") as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            parsed = [json.loads(ln) for ln in lines]
            self.assertEqual(parsed[0]["actor"], "alice")
            self.assertEqual(parsed[1]["action"], "budget_set")
            for entry in parsed:
                self.assertTrue(
                    {"ts", "actor", "action", "target", "details"}
                    <= set(entry.keys())
                )
                self.assertTrue(
                    {"seq", "prev_hash", "hash"} <= set(entry.keys())
                )

    def test_file_backed_log_survives_reopen(self):
        """Core 11: Audit log (AU-9 protection of audit information).
        A new AuditLog over the same file reloads the prior trail on
        construction (contract) and stays append-only across restarts."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            AuditLog(path).record("alice", "program_create", "prog-1")
            reopened = AuditLog(path)
            entries = reopened.entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["target"], "prog-1")
            reopened.record("alice", "participant_create", "prog-1")
            self.assertEqual(len(AuditLog(path).entries()), 2)


class TestStoreAuditing(unittest.TestCase):
    """Core 11: Audit log — the store records each mutation action."""

    def test_store_records_every_mutation_action_name(self):
        """Core 11: Audit log. Contract: the store records every
        successful mutation with the spec's action names:
        program_create, member_add, participant_create,
        participant_status, accrual_record, access_request,
        access_approve, access_deny, access_void,
        disbursement_record, booking_create, booking_confirm,
        booking_cancel, budget_set, wellness_create, wellness_enroll."""
        store, audit, program_id = make_store()
        employee = make_employee(store, program_id)
        traveler = make_traveler(store, program_id)
        store.set_participant_status(
            program_id, traveler["id"], "inactive", MEMBER
        )
        store.set_participant_status(
            program_id, traveler["id"], "active", MEMBER
        )
        make_accrual(store, program_id, employee["id"], PERIOD, 100000)

        approved = make_request(
            store, program_id, employee["id"], PERIOD, 10000
        )
        store.decide_access(program_id, approved["id"], True, ADMIN)
        store.record_disbursement(
            program_id, approved["id"], "2026-01-20", MEMBER,
            method="payroll",
        )
        denied = make_request(store, program_id, employee["id"], PERIOD, 5000)
        store.decide_access(program_id, denied["id"], False, ADMIN)
        voided = make_request(store, program_id, employee["id"], PERIOD, 3000)
        store.void_access(program_id, voided["id"], MEMBER)

        booking = make_booking(store, program_id, traveler["id"])
        store.confirm_booking(program_id, booking["id"], MEMBER)
        store.cancel_booking(program_id, booking["id"], MEMBER)

        store.set_budget(
            program_id, PERIOD,
            [{"category": "air", "limit_cents": 50000}], MEMBER,
        )
        offering = store.create_wellness_offering(
            program_id, "Budgeting Basics", "budgeting", MEMBER
        )
        store.enroll_participant(
            program_id, offering["id"], employee["id"], MEMBER
        )

        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "program_create", "member_add", "participant_create",
            "participant_status", "accrual_record", "access_request",
            "access_approve", "access_deny", "access_void",
            "disbursement_record", "booking_create", "booking_confirm",
            "booking_cancel", "budget_set", "wellness_create",
            "wellness_enroll",
        ):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)

    def test_store_entries_carry_actor_and_target(self):
        """Core 11: Audit log (AU-3). Store-recorded entries name the
        actor who performed the mutation."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        program = store.create_program("ops-program", ADMIN)
        entry = audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "program_create")
        self.assertEqual(entry["target"], program["id"])

    def test_failed_mutation_records_no_success_action(self):
        """Core 11: Audit log. Contract: the store records *successful*
        mutations (denials are the HTTP layer's job) — a denied
        participant creation adds no participant_create entry."""
        store, audit, program_id = make_store()
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            store.create_participant(program_id, "emp-x", "employee", VIEWER)
        actions = [e["action"] for e in audit.entries()[before:]]
        self.assertNotIn("participant_create", actions)

    def test_store_without_audit_log_still_works(self):
        """Core 11: Audit log. Contract: FinanceStore(audit=None) —
        the audit log is optional; mutations succeed with none attached."""
        store = fresh_store()
        program = store.create_program("quiet-program", MEMBER)
        self.assertEqual(program["id"], "prog-1")
        participant = make_employee(store, program["id"])
        self.assertEqual(participant["id"], "part-1")


if __name__ == "__main__":
    unittest.main()
