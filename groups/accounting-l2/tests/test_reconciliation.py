"""Reconciliation and period-close tests.

Traces to: UNION-SPEC Core function 8 (Reconciliation & period close —
the build computes an account's book balance through the end of a
period and records the difference against a stated expected balance;
closing a period locks the ledger for that period); Implementation
contract for ``accounting/store.py`` reconcile_account and
close_period methods; control families AU (reconciliations and closes
are audit records) and SI-10 (validation before mutation).
"""

import unittest

from accounting_helpers import (
    ADMIN,
    DATE_FEB,
    MEMBER,
    PERIOD_FEB,
    PERIOD_JAN,
    balanced_lines,
    build_scenario,
    make_chart,
    make_store,
    post_entry,
    post_revenue,
)
from accounting.errors import ValidationError

RECONCILIATION_KEYS = {
    "id", "book_id", "account_id", "period", "book_balance_cents",
    "expected_cents", "difference_cents", "matched", "created_by",
    "created_utc",
}
CLOSE_KEYS = {"book_id", "period", "closed_by", "closed_utc"}


class ReconciliationBase(unittest.TestCase):
    """The canonical scenario: Cash is 130000 through 2026-01."""

    def setUp(self):
        self.store, self.book_id = make_store()
        self.chart = make_chart(self.store, self.book_id)
        build_scenario(self.store, self.book_id, self.chart)
        self.cash = self.chart["cash"]["id"]


class TestReconcileAccount(ReconciliationBase):
    """Core 8: Reconciliation — book balance vs a stated expected."""

    def test_reconcile_returns_the_contract_dict(self):
        """Core 8: Reconciliation. Contract: reconcile_account returns
        {id, book_id, account_id, period, book_balance_cents,
        expected_cents, difference_cents, matched, created_by,
        created_utc} with the rec- id prefix."""
        rec = self.store.reconcile_account(
            self.book_id, self.cash, PERIOD_JAN, 130000, MEMBER
        )
        self.assertEqual(set(rec.keys()), RECONCILIATION_KEYS)
        self.assertEqual(rec["id"], "rec-1")
        self.assertEqual(rec["book_id"], self.book_id)
        self.assertEqual(rec["account_id"], self.cash)
        self.assertEqual(rec["period"], PERIOD_JAN)
        self.assertEqual(rec["created_by"], "bob")

    def test_reconcile_matched_when_expected_equals_book_balance(self):
        """Core 8: Reconciliation. Contract: book_balance_cents is the
        account's cumulative normal-direction balance over posted
        entries with period <= the given period (Cash: 130000 through
        January); 'matched is difference_cents == 0'."""
        rec = self.store.reconcile_account(
            self.book_id, self.cash, PERIOD_JAN, 130000, MEMBER
        )
        self.assertEqual(rec["book_balance_cents"], 130000)
        self.assertEqual(rec["expected_cents"], 130000)
        self.assertEqual(rec["difference_cents"], 0)
        self.assertIs(rec["matched"], True)

    def test_reconcile_with_a_difference_is_unmatched_and_signed(self):
        """Core 8: Reconciliation. Contract: 'difference_cents =
        book_balance_cents - expected_cents' (signed) and matched is
        false when it is non-zero — checked in both directions."""
        short = self.store.reconcile_account(
            self.book_id, self.cash, PERIOD_JAN, 125000, MEMBER
        )
        self.assertEqual(short["book_balance_cents"], 130000)
        self.assertEqual(short["difference_cents"], 130000 - 125000)
        self.assertIs(short["matched"], False)

        over = self.store.reconcile_account(
            self.book_id, self.cash, PERIOD_JAN, 135000, MEMBER
        )
        self.assertEqual(over["difference_cents"], 130000 - 135000)
        self.assertEqual(over["difference_cents"], -5000)
        self.assertIs(over["matched"], False)

    def test_reconcile_is_cumulative_through_the_period(self):
        """Core 8: Reconciliation. The book balance is cumulative
        through the given period: after a posted February revenue
        entry, reconciling Cash through January still sees 130000 and
        through February sees 140000."""
        post_revenue(self.store, self.book_id, self.chart,
                     amount_cents=10000, date=DATE_FEB)
        jan = self.store.reconcile_account(
            self.book_id, self.cash, PERIOD_JAN, 130000, MEMBER
        )
        self.assertEqual(jan["book_balance_cents"], 130000)
        self.assertIs(jan["matched"], True)
        feb = self.store.reconcile_account(
            self.book_id, self.cash, PERIOD_FEB, 140000, MEMBER
        )
        self.assertEqual(feb["book_balance_cents"], 140000)
        self.assertIs(feb["matched"], True)

    def test_reconcile_uses_the_normal_direction_for_a_liability(self):
        """Core 8: Reconciliation. The book balance is in the account's
        normal direction: a liability credited 7000 reconciles against
        an expected +7000."""
        post_entry(
            self.store, self.book_id, "2026-01-20", "Supplies on credit",
            balanced_lines(self.chart["rent"]["id"],
                           self.chart["payable"]["id"], 7000),
        )
        rec = self.store.reconcile_account(
            self.book_id, self.chart["payable"]["id"], PERIOD_JAN, 7000,
            MEMBER,
        )
        self.assertEqual(rec["book_balance_cents"], 7000)
        self.assertIs(rec["matched"], True)

    def test_reconcile_negative_expected_balance_is_accepted(self):
        """Core 8: Reconciliation. Contract: expected_balance_cents is
        'any int' — a negative expectation is recorded, not rejected,
        and the difference stays book - expected."""
        rec = self.store.reconcile_account(
            self.book_id, self.cash, PERIOD_JAN, -1000, MEMBER
        )
        self.assertEqual(rec["expected_cents"], -1000)
        self.assertEqual(rec["difference_cents"], 130000 - (-1000))
        self.assertIs(rec["matched"], False)

    def test_reconcile_rejects_non_int_expected_balance(self):
        """Core 8: Reconciliation (SI-10). Contract: expected must be
        an int — floats and bools raise ValidationError."""
        for bad in (130000.0, True):
            with self.subTest(expected=bad):
                with self.assertRaises(ValidationError):
                    self.store.reconcile_account(
                        self.book_id, self.cash, PERIOD_JAN, bad, MEMBER
                    )


class TestClosePeriod(ReconciliationBase):
    """Core 8: Period close — locking a period's ledger."""

    def january_lines(self, amount=1000):
        return balanced_lines(
            self.chart["cash"]["id"], self.chart["equity"]["id"], amount
        )

    def test_close_period_returns_the_contract_dict(self):
        """Core 8: Period close. Contract: close_period returns
        {book_id, period, closed_by, closed_utc}."""
        result = self.store.close_period(self.book_id, PERIOD_JAN, MEMBER)
        self.assertEqual(set(result.keys()), CLOSE_KEYS)
        self.assertEqual(result["book_id"], self.book_id)
        self.assertEqual(result["period"], PERIOD_JAN)
        self.assertEqual(result["closed_by"], "bob")
        self.assertIsNotNone(result["closed_utc"])

    def test_close_period_updates_the_book_dict(self):
        """Core 8: Period close. Contract: closing 'adds the period to
        the book's closed_periods (kept sorted)'."""
        self.store.close_period(self.book_id, PERIOD_FEB, ADMIN)
        self.store.close_period(self.book_id, PERIOD_JAN, MEMBER)
        book = self.store.get_book(self.book_id, MEMBER)
        self.assertEqual(book["closed_periods"], [PERIOD_JAN, PERIOD_FEB])

    def test_closing_twice_is_a_validation_error(self):
        """Core 8: Period close. Contract: 'closing an already-closed
        period -> ValidationError'."""
        self.store.close_period(self.book_id, PERIOD_JAN, MEMBER)
        with self.assertRaises(ValidationError):
            self.store.close_period(self.book_id, PERIOD_JAN, ADMIN)
        book = self.store.get_book(self.book_id, MEMBER)
        self.assertEqual(book["closed_periods"], [PERIOD_JAN])

    def test_create_entry_dated_in_a_closed_period_is_rejected(self):
        """Core 8: Period close. Contract: 'After a period is closed,
        create_entry with a date in it ... raise ValidationError' —
        and the rejected creation stores nothing and consumes no id."""
        self.store.close_period(self.book_id, PERIOD_JAN, MEMBER)
        before = len(self.store.list_entries(self.book_id, MEMBER))
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, "2026-01-20", "Too late",
                self.january_lines(), MEMBER,
            )
        entries = self.store.list_entries(self.book_id, MEMBER)
        self.assertEqual(len(entries), before)
        # A February entry still works and keeps the id sequence.
        feb = self.store.create_entry(
            self.book_id, DATE_FEB, "February is open",
            balanced_lines(self.chart["cash"]["id"],
                           self.chart["revenue"]["id"], 1000),
            MEMBER,
        )
        self.assertEqual(feb["id"], "je-%d" % (before + 1))

    def test_approve_of_a_pending_entry_in_a_closed_period_is_rejected(self):
        """Core 8: Period close. Contract: 'approve_entry on an entry
        in it raise ValidationError' after the period closes — the
        pending entry stays pending (it is not posted)."""
        entry = self.store.create_entry(
            self.book_id, "2026-01-20", "Pending at close",
            self.january_lines(4000), MEMBER,
        )
        self.store.submit_entry(self.book_id, entry["id"], MEMBER)
        self.store.close_period(self.book_id, PERIOD_JAN, MEMBER)
        with self.assertRaises(ValidationError):
            self.store.approve_entry(self.book_id, entry["id"], ADMIN)
        after = self.store.get_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(after["status"], "pending")
        self.assertIsNone(after["approved_by"])
        self.assertIsNone(after["posted_utc"])

    def test_entries_in_open_periods_are_unaffected_by_a_close(self):
        """Core 8: Period close. Closing January locks January only: a
        February entry can still be created, submitted and posted end
        to end, and February reports move."""
        self.store.close_period(self.book_id, PERIOD_JAN, MEMBER)
        posted = post_entry(
            self.store, self.book_id, DATE_FEB, "February revenue",
            balanced_lines(self.chart["cash"]["id"],
                           self.chart["revenue"]["id"], 10000),
        )
        self.assertEqual(posted["status"], "posted")
        balance = self.store.account_balance(
            self.book_id, self.chart["cash"]["id"], MEMBER,
            period=PERIOD_FEB,
        )
        self.assertEqual(balance["balance_cents"], 10000)

    def test_posted_entries_survive_a_close(self):
        """Core 8: Period close. Closing a period locks new writes; it
        does not erase history — January reports still show the
        scenario after the close."""
        self.store.close_period(self.book_id, PERIOD_JAN, MEMBER)
        trial = self.store.trial_balance(
            self.book_id, MEMBER, period=PERIOD_JAN
        )
        self.assertEqual(trial["total_debits_cents"], 150000)
        self.assertIs(trial["balanced"], True)


if __name__ == "__main__":
    unittest.main()
