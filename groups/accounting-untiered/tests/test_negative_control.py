"""Negative control: the suite must reject a mutant balance check.

Traces to: UNION-SPEC "Implementation contract" — tests 'include a
negative control: a mutant balance check (one that computes the debit
and credit sums but never compares them, treating every entry as
balanced) whose behavior the canonical expectation is shown to reject
— an unbalanced entry must raise ValidationError from the real store
and store nothing, and the mutant is demonstrated to wave it through —
proving the suite catches that defect class rather than merely
passing.'

The traced claim: **the debits-equal-credits invariant is the
SI-10 / Core 3 integrity boundary of the ledger.** Every journal entry
in the contract must balance in exact integer cents or be rejected
whole. The mutant below replaces that comparison with one that sums
both sides and then returns True unconditionally.

Each test asserts three things, per the canonical pattern: (1) the
canonical expectation — the real implementation raises ValidationError
for the unbalanced entry, stores nothing, and consumes no id; (2) the
mutant would NOT raise — run through the same gate shape, it waves the
unbalanced entry through as "balanced"; and (3) a literal
assertRaises(AssertionError) demonstration that treating the mutant's
outcome as the expected outcome is a test failure.
"""

import unittest

from accounting_helpers import MEMBER, make_chart, make_store
from accounting.errors import ValidationError


def mutant_balance_check(lines):
    """The defect under control: sums are computed, never compared."""
    total_debits = sum(int(ln.get("debit_cents") or 0) for ln in lines)
    total_credits = sum(int(ln.get("credit_cents") or 0) for ln in lines)
    # The mutant computes both totals — and then never compares them,
    # treating every entry as balanced regardless of the numbers.
    _ = (total_debits, total_credits)
    return True


def mutant_gate(lines):
    """The balance gate as the mutant would run it.

    Mirrors the real gate's shape — raise ValidationError when the
    check fails, otherwise proceed — but with the mutant check inside,
    so it returns "balanced" for an unbalanced entry instead of
    raising.
    """
    if not mutant_balance_check(lines):
        raise ValidationError("unbalanced entry")
    return "balanced"


class TestNegativeControlMutantBalanceCheck(unittest.TestCase):
    """Core 3: Double-entry journal (SI-10) — negative control for the
    balance invariant, traced claim: the debits-equal-credits
    invariant is the SI-10/core-3 integrity boundary of the ledger."""

    def setUp(self):
        self.store, self.book_id = make_store()
        self.chart = make_chart(self.store, self.book_id)
        self.cash = self.chart["cash"]["id"]
        self.equity = self.chart["equity"]["id"]
        self.revenue = self.chart["revenue"]["id"]

    def _assert_mutant_rejected(self, mutant_outcome):
        """The mutant's 'balanced' must fail the canonical expectation."""
        self.assertNotEqual(mutant_outcome, "rejected")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, "rejected")

    def _assert_real_store_rejects(self, lines):
        """Canonical expectation: ValidationError, nothing stored, and
        no entry id consumed (the next good entry is je-1)."""
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, "2026-01-05", "Unbalanced", lines, MEMBER
            )
        self.assertEqual(self.store.list_entries(self.book_id, MEMBER), [])
        good = self.store.create_entry(
            self.book_id, "2026-01-05", "Balanced",
            [
                {"account_id": self.cash, "debit_cents": 1000},
                {"account_id": self.equity, "credit_cents": 1000},
            ],
            MEMBER,
        )
        self.assertEqual(good["id"], "je-1")

    def test_unbalanced_entry_off_by_one_cent(self):
        """Core 3: Double-entry journal (SI-10), traced claim: the
        debits-equal-credits invariant is the SI-10/core-3 integrity
        boundary. Canonical case (a): debits 10000, credits 9999 — the
        real store raises ValidationError, stores nothing, consumes no
        id. Mutant: the same lines are waved through as balanced."""
        lines = [
            {"account_id": self.cash, "debit_cents": 10000},
            {"account_id": self.equity, "credit_cents": 9999},
        ]
        self._assert_real_store_rejects(lines)
        mutant_outcome = mutant_gate(lines)
        self.assertEqual(mutant_outcome, "balanced")  # mutant did not raise
        self._assert_mutant_rejected(mutant_outcome)

    def test_valid_lines_with_debits_exceeding_credits_by_one_cent(self):
        """Core 3: Double-entry journal (SI-10), traced claim: the
        debits-equal-credits invariant is the SI-10/core-3 integrity
        boundary. Canonical case (b): every line is individually valid
        (one-sided, positive, known account) but total debits exceed
        total credits by exactly 1 cent across three lines — the real
        store still raises ValidationError. Mutant: waved through."""
        lines = [
            {"account_id": self.cash, "debit_cents": 6000},
            {"account_id": self.revenue, "debit_cents": 4001},
            {"account_id": self.equity, "credit_cents": 10000},
        ]
        self._assert_real_store_rejects(lines)
        mutant_outcome = mutant_gate(lines)
        self.assertEqual(mutant_outcome, "balanced")
        self._assert_mutant_rejected(mutant_outcome)

    def test_balanced_entry_passes_both_real_store_and_mutant(self):
        """Core 3: Double-entry journal (SI-10), traced claim: the
        debits-equal-credits invariant is the SI-10/core-3 integrity
        boundary. Canonical case (c), the control sanity check: a
        genuinely balanced entry passes BOTH the real store (created
        as a draft) and the mutant check — the mutant is a weakened
        gate, not a broken one, so agreement on valid input is
        expected."""
        lines = [
            {"account_id": self.cash, "debit_cents": 10000},
            {"account_id": self.equity, "credit_cents": 10000},
        ]
        entry = self.store.create_entry(
            self.book_id, "2026-01-05", "Balanced", lines, MEMBER
        )
        self.assertEqual(entry["status"], "draft")
        self.assertEqual(entry["total_cents"], 10000)
        self.assertTrue(mutant_balance_check(lines))
        self.assertEqual(mutant_gate(lines), "balanced")


if __name__ == "__main__":
    unittest.main()
