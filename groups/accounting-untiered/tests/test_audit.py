"""Audit-log tests.

Traces to: UNION-SPEC Core function 13 (Audit log) / ranking row 9
(Audit trail & audit management, 6 siblings); Implementation contract
for ``accounting/audit.py`` and the store's audit action names in
``accounting/store.py``; control families AU-2, AU-3, AU-6, AU-9
(append-only store).
"""

import json
import os
import tempfile
import unittest
from datetime import datetime

from accounting_helpers import (
    ADMIN,
    MEMBER,
    VIEWER,
    balanced_lines,
    fresh_store,
    make_chart,
    make_store,
)
from accounting.audit import AuditLog
from accounting.errors import PermissionDenied


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLogInMemory(unittest.TestCase):
    """Core 13: Audit log — record()/entries() contract."""

    def test_record_and_entries_roundtrip(self):
        """Core 13: Audit log. entries() returns dicts with keys
        ts, actor, action, target, details (contract)."""
        log = AuditLog()
        log.record("alice", "book_create", "book-1", {"name": "acme"})
        entries = log.entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(
            set(entry.keys()), {"ts", "actor", "action", "target", "details"}
        )
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "book_create")
        self.assertEqual(entry["target"], "book-1")
        self.assertEqual(entry["details"], {"name": "acme"})

    def test_details_defaults_to_empty(self):
        """Core 13: Audit log. Contract: record(..., details=None)."""
        log = AuditLog()
        log.record("bob", "period_close", "book-1")
        self.assertIn(log.entries()[0]["details"], (None, {}))

    def test_timestamp_is_isoformat_utc_string(self):
        """Core 13: Audit log (AU-3). Each entry carries a parseable
        UTC timestamp."""
        log = AuditLog()
        log.record("alice", "book_create", "book-1")
        ts = log.entries()[0]["ts"]
        self.assertIsInstance(ts, str)
        self.assertTrue(ts)
        parsed = _parse_ts(ts)  # must not raise
        self.assertIsNotNone(parsed)

    def test_entries_preserve_record_order(self):
        """Core 13: Audit log (AU-2). A trail is chronological: entries
        come back in the order they were recorded."""
        log = AuditLog()
        for i in range(5):
            log.record("alice", "book_create", "book-%d" % i)
        targets = [e["target"] for e in log.entries()]
        self.assertEqual(
            targets, ["book-0", "book-1", "book-2", "book-3", "book-4"]
        )

    def test_append_only_earlier_entries_never_change(self):
        """Core 13: Audit log (AU-9). Recording later events must not
        mutate or drop earlier entries."""
        log = AuditLog()
        log.record("alice", "book_create", "book-1")
        first_snapshot = dict(log.entries()[0])
        log.record("alice", "entry_create", "je-1")
        log.record("carol", "entry_create:denied", "book-1")
        entries = log.entries()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0], first_snapshot)

    def test_empty_log_has_no_entries(self):
        """Core 13: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_details_dict_is_stored_verbatim(self):
        """Core 13: Audit log (AU-3 content of audit records)."""
        log = AuditLog()
        details = {"kind": "payment", "count": 2, "nested": {"ok": True}}
        log.record("bob", "payment_record", "pay-1", details)
        self.assertEqual(log.entries()[0]["details"], details)


class TestAuditLogFile(unittest.TestCase):
    """Core 13: Audit log — optional JSONL file backing (contract)."""

    def test_file_backed_log_writes_jsonl(self):
        """Core 13: Audit log. With a path, each record is one JSON
        line in the file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "book_create", "book-1", {"name": "t"})
            log.record("bob", "period_close", "book-1")
            with open(path, encoding="utf-8") as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            parsed = [json.loads(ln) for ln in lines]
            self.assertEqual(parsed[0]["actor"], "alice")
            self.assertEqual(parsed[1]["action"], "period_close")
            for entry in parsed:
                self.assertEqual(
                    set(entry.keys()),
                    {"ts", "actor", "action", "target", "details"},
                )

    def test_file_backed_log_survives_reopen(self):
        """Core 13: Audit log (AU-9 protection of audit information).
        A new AuditLog over the same file reloads the prior trail on
        construction (contract) and stays append-only across restarts."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            AuditLog(path).record("alice", "book_create", "book-1")
            reopened = AuditLog(path)
            entries = reopened.entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["target"], "book-1")
            reopened.record("alice", "account_create", "book-1")
            self.assertEqual(len(AuditLog(path).entries()), 2)


class TestStoreAuditing(unittest.TestCase):
    """Core 13: Audit log — the store records each mutation action."""

    def test_store_records_every_mutation_action_name(self):
        """Core 13: Audit log. Contract: the store records every
        successful mutation with the spec's action names: book_create,
        member_add, account_create, entry_create, entry_submit,
        entry_post, entry_reject, entry_void, invoice_create,
        invoice_submit, invoice_issue, invoice_reject, invoice_void,
        payment_record, expense_create, expense_submit,
        expense_approve, expense_reject, expense_void,
        expense_reimburse, budget_set, reconciliation_create,
        period_close."""
        audit = AuditLog()
        store, book_id = make_store(audit=audit)
        chart = make_chart(store, book_id)

        # Journal: one posted entry, one rejected-then-voided entry.
        entry = store.create_entry(
            book_id, "2026-01-05", "Invest",
            balanced_lines(chart["cash"]["id"], chart["equity"]["id"],
                           100000),
            MEMBER,
        )
        store.submit_entry(book_id, entry["id"], MEMBER)
        store.approve_entry(book_id, entry["id"], ADMIN)
        rejected = store.create_entry(
            book_id, "2026-01-06", "Rejected",
            balanced_lines(chart["cash"]["id"], chart["revenue"]["id"],
                           5000),
            MEMBER,
        )
        store.submit_entry(book_id, rejected["id"], MEMBER)
        store.reject_entry(book_id, rejected["id"], ADMIN)
        store.void_entry(book_id, rejected["id"], MEMBER)

        # Invoices: one issued and paid; one rejected then voided.
        invoice = store.create_invoice(
            book_id, "Customer Co", "2026-01-05", "2026-02-04",
            [{"description": "Services", "quantity": 1,
              "unit_price_cents": 10000}],
            MEMBER,
        )
        store.submit_invoice(book_id, invoice["id"], MEMBER)
        store.approve_invoice(book_id, invoice["id"], ADMIN)
        store.record_payment(
            book_id, invoice["id"], 4000, "2026-01-07", MEMBER
        )
        bad_invoice = store.create_invoice(
            book_id, "Other Co", "2026-01-05", "2026-02-04",
            [{"description": "Services", "quantity": 1,
              "unit_price_cents": 3000}],
            MEMBER,
        )
        store.submit_invoice(book_id, bad_invoice["id"], MEMBER)
        store.reject_invoice(book_id, bad_invoice["id"], ADMIN)
        store.void_invoice(book_id, bad_invoice["id"], MEMBER)

        # Expenses: one approved and reimbursed; one rejected/voided.
        expense = store.create_expense(
            book_id, "2026-01-08", "travel", "Taxi", 2500, MEMBER
        )
        store.submit_expense(book_id, expense["id"], MEMBER)
        store.approve_expense(book_id, expense["id"], ADMIN)
        store.reimburse_expense(book_id, expense["id"], MEMBER)
        bad_expense = store.create_expense(
            book_id, "2026-01-09", "meals", "Lunch", 1200, MEMBER
        )
        store.submit_expense(book_id, bad_expense["id"], MEMBER)
        store.reject_expense(book_id, bad_expense["id"], ADMIN)
        store.void_expense(book_id, bad_expense["id"], MEMBER)

        # Budget, reconciliation, period close.
        store.set_budget(
            book_id, "2026-01",
            [{"account_id": chart["rent"]["id"], "amount_cents": 25000}],
            MEMBER,
        )
        store.reconcile_account(
            book_id, chart["cash"]["id"], "2026-01", 100000, MEMBER
        )
        store.close_period(book_id, "2026-01", MEMBER)

        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "book_create", "member_add", "account_create",
            "entry_create", "entry_submit", "entry_post", "entry_reject",
            "entry_void", "invoice_create", "invoice_submit",
            "invoice_issue", "invoice_reject", "invoice_void",
            "payment_record", "expense_create", "expense_submit",
            "expense_approve", "expense_reject", "expense_void",
            "expense_reimburse", "budget_set", "reconciliation_create",
            "period_close",
        ):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)

    def test_store_entries_carry_actor_and_target(self):
        """Core 13: Audit log (AU-3). Store-recorded entries name the
        actor who performed the mutation."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        book = store.create_book("ops-books", ADMIN)
        entry = audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "book_create")
        self.assertEqual(entry["target"], book["id"])

    def test_failed_mutation_records_no_success_action(self):
        """Core 13: Audit log. Contract: the store records *successful*
        mutations (denials are the HTTP layer's job) — a denied account
        creation adds no account_create entry."""
        audit = AuditLog()
        store, book_id = make_store(audit=audit)
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            store.create_account(book_id, "9000", "Nope", "asset", VIEWER)
        actions = [e["action"] for e in audit.entries()[before:]]
        self.assertNotIn("account_create", actions)

    def test_store_without_audit_log_still_works(self):
        """Core 13: Audit log. Contract: AccountingStore(audit=None) —
        the audit log is optional; mutations succeed with none attached."""
        store = fresh_store()
        book = store.create_book("quiet-books", MEMBER)
        self.assertEqual(book["id"], "book-1")
        chart = make_chart(store, book["id"])
        self.assertEqual(chart["cash"]["code"], "1000")


if __name__ == "__main__":
    unittest.main()
