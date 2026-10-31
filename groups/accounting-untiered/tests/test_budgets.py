"""Budget tests.

Traces to: UNION-SPEC Core function 7 (Budgets — a budget per book per
fiscal period; setting a budget for a period that already has one
replaces its lines; budget-vs-actual compares planned amounts against
posted ledger movement for the period); Implementation contract for
``accounting/store.py`` budget methods; control family SI-10 (integer
cents, validation before mutation).
"""

import unittest

from accounting_helpers import (
    DATE_FEB,
    DATE_JAN,
    MEMBER,
    PERIOD_FEB,
    PERIOD_JAN,
    balanced_lines,
    make_chart,
    make_store,
    post_entry,
    post_rent,
    post_revenue,
)
from accounting.errors import NotFoundError, ValidationError

BUDGET_KEYS = {
    "id", "book_id", "period", "lines", "total_cents", "created_by",
    "created_utc", "updated_utc",
}
VS_ACTUAL_KEYS = {
    "book_id", "period", "lines", "total_budgeted_cents",
    "total_actual_cents", "total_variance_cents",
}
VS_ACTUAL_LINE_KEYS = {
    "account_id", "code", "name", "type", "budgeted_cents",
    "actual_cents", "variance_cents",
}


class BudgetBase(unittest.TestCase):
    """A canonical book with the five-account chart."""

    def setUp(self):
        self.store, self.book_id = make_store()
        self.chart = make_chart(self.store, self.book_id)

    def set_jan_budget(self):
        """Budget for 2026-01: rent 25000, revenue 60000."""
        return self.store.set_budget(
            self.book_id, PERIOD_JAN,
            [
                {"account_id": self.chart["rent"]["id"],
                 "amount_cents": 25000},
                {"account_id": self.chart["revenue"]["id"],
                 "amount_cents": 60000},
            ],
            MEMBER,
        )


class TestSetBudget(BudgetBase):
    """Core 7: Budgets — set/get shape, replace semantics, validation."""

    def test_set_budget_returns_the_contract_dict(self):
        """Core 7: Budgets. Contract: set_budget returns {id, book_id,
        period, lines, total_cents, created_by, created_utc,
        updated_utc} with the bud- id prefix."""
        budget = self.set_jan_budget()
        self.assertEqual(set(budget.keys()), BUDGET_KEYS)
        self.assertEqual(budget["id"], "bud-1")
        self.assertEqual(budget["book_id"], self.book_id)
        self.assertEqual(budget["period"], PERIOD_JAN)
        self.assertEqual(budget["created_by"], "bob")
        self.assertEqual(len(budget["lines"]), 2)

    def test_total_cents_is_the_sum_of_lines(self):
        """Core 7: Budgets. Contract: total_cents is the sum of the
        budget lines' amounts."""
        budget = self.set_jan_budget()
        self.assertEqual(budget["total_cents"], 25000 + 60000)

    def test_get_budget_roundtrip(self):
        """Core 7: Budgets. get_budget returns the budget set for the
        period."""
        budget = self.set_jan_budget()
        got = self.store.get_budget(self.book_id, PERIOD_JAN, MEMBER)
        self.assertEqual(got["id"], budget["id"])
        self.assertEqual(got["total_cents"], budget["total_cents"])
        self.assertEqual(got["lines"], budget["lines"])

    def test_get_budget_for_a_missing_period_is_not_found(self):
        """Core 7: Budgets. Contract: get_budget -> 'NotFoundError if
        none was set for that period'."""
        with self.assertRaises(NotFoundError):
            self.store.get_budget(self.book_id, PERIOD_FEB, MEMBER)
        self.set_jan_budget()
        with self.assertRaises(NotFoundError):
            self.store.get_budget(self.book_id, PERIOD_FEB, MEMBER)

    def test_replace_keeps_id_and_created_utc_and_replaces_lines(self):
        """Core 7: Budgets. Contract: 'One budget per (book, period):
        if one exists, its lines and total are replaced, its id,
        created_by, and created_utc are kept, and updated_utc is
        refreshed.'"""
        first = self.set_jan_budget()
        replaced = self.store.set_budget(
            self.book_id, PERIOD_JAN,
            [{"account_id": self.chart["cash"]["id"],
              "amount_cents": 7000}],
            MEMBER,
        )
        self.assertEqual(replaced["id"], first["id"])
        self.assertEqual(replaced["created_by"], first["created_by"])
        self.assertEqual(replaced["created_utc"], first["created_utc"])
        self.assertIn("updated_utc", replaced)
        self.assertEqual(
            replaced["lines"],
            [{"account_id": self.chart["cash"]["id"],
              "amount_cents": 7000}],
        )
        self.assertEqual(replaced["total_cents"], 7000)
        got = self.store.get_budget(self.book_id, PERIOD_JAN, MEMBER)
        self.assertEqual(got["id"], first["id"])
        self.assertEqual(got["total_cents"], 7000)

    def test_replace_does_not_create_a_second_budget_id(self):
        """Core 7: Budgets. Replacing a period's budget consumes no
        new id: the next new period's budget is bud-2."""
        self.set_jan_budget()
        self.store.set_budget(
            self.book_id, PERIOD_JAN,
            [{"account_id": self.chart["cash"]["id"],
              "amount_cents": 1}],
            MEMBER,
        )
        feb = self.store.set_budget(
            self.book_id, PERIOD_FEB,
            [{"account_id": self.chart["cash"]["id"],
              "amount_cents": 2}],
            MEMBER,
        )
        self.assertEqual(feb["id"], "bud-2")

    def test_duplicate_account_line_is_a_validation_error(self):
        """Core 7: Budgets. Contract: 'a repeated account in one call
        -> ValidationError', and nothing is stored."""
        with self.assertRaises(ValidationError):
            self.store.set_budget(
                self.book_id, PERIOD_JAN,
                [
                    {"account_id": self.chart["rent"]["id"],
                     "amount_cents": 1000},
                    {"account_id": self.chart["rent"]["id"],
                     "amount_cents": 2000},
                ],
                MEMBER,
            )
        with self.assertRaises(NotFoundError):
            self.store.get_budget(self.book_id, PERIOD_JAN, MEMBER)

    def test_unknown_account_is_a_validation_error(self):
        """Core 7: Budgets. Contract: 'every account must exist in
        this book'."""
        with self.assertRaises(ValidationError):
            self.store.set_budget(
                self.book_id, PERIOD_JAN,
                [{"account_id": "acct-999999", "amount_cents": 1000}],
                MEMBER,
            )
        with self.assertRaises(NotFoundError):
            self.store.get_budget(self.book_id, PERIOD_JAN, MEMBER)

    def test_negative_or_float_amounts_are_validation_errors(self):
        """Core 7: Budgets (SI-10). Contract: budget amounts are ints
        >= 0 — negatives, floats and bools are rejected."""
        for bad_amount in (-1, 10.5, 10.0, True):
            with self.subTest(amount=bad_amount):
                with self.assertRaises(ValidationError):
                    self.store.set_budget(
                        self.book_id, PERIOD_JAN,
                        [{"account_id": self.chart["rent"]["id"],
                          "amount_cents": bad_amount}],
                        MEMBER,
                    )

    def test_zero_amount_line_is_accepted(self):
        """Core 7: Budgets. Amounts are ints >= 0, so a zero line is
        valid."""
        budget = self.store.set_budget(
            self.book_id, PERIOD_JAN,
            [{"account_id": self.chart["rent"]["id"], "amount_cents": 0}],
            MEMBER,
        )
        self.assertEqual(budget["total_cents"], 0)

    def test_invalid_period_is_a_validation_error(self):
        """Core 7: Budgets. Contract: period must be a valid YYYY-MM
        fiscal period."""
        for bad in ("2026-13", "2026-1", "Jan 2026", "2026-01-05"):
            with self.subTest(period=bad):
                with self.assertRaises(ValidationError):
                    self.store.set_budget(
                        self.book_id, bad,
                        [{"account_id": self.chart["rent"]["id"],
                          "amount_cents": 1000}],
                        MEMBER,
                    )

    def test_empty_lines_is_a_validation_error(self):
        """Core 7: Budgets. Contract: lines is a list of at least one
        dict."""
        with self.assertRaises(ValidationError):
            self.store.set_budget(self.book_id, PERIOD_JAN, [], MEMBER)


class TestBudgetVsActual(BudgetBase):
    """Core 7: Budgets — budget-vs-actual against posted movement."""

    def setUp(self):
        super().setUp()
        self.budget = self.set_jan_budget()
        # Posted movement inside 2026-01: rent 20000, revenue 50000.
        post_rent(self.store, self.book_id, self.chart)
        post_revenue(self.store, self.book_id, self.chart)

    def _line_for(self, result, account_key):
        account_id = self.chart[account_key]["id"]
        for line in result["lines"]:
            if line["account_id"] == account_id:
                return line
        self.fail("no vs-actual line for account %s" % account_key)

    def test_vs_actual_returns_the_contract_dict(self):
        """Core 7: Budgets. Contract: budget_vs_actual returns
        {book_id, period, lines, total_budgeted_cents,
        total_actual_cents, total_variance_cents}; each line is
        {account_id, code, name, type, budgeted_cents, actual_cents,
        variance_cents}."""
        result = self.store.budget_vs_actual(
            self.book_id, PERIOD_JAN, MEMBER
        )
        self.assertEqual(set(result.keys()), VS_ACTUAL_KEYS)
        self.assertEqual(result["book_id"], self.book_id)
        self.assertEqual(result["period"], PERIOD_JAN)
        for line in result["lines"]:
            self.assertEqual(set(line.keys()), VS_ACTUAL_LINE_KEYS)

    def test_vs_actual_requires_a_budget(self):
        """Core 7: Budgets. Contract: budget_vs_actual 'requires a
        budget for the period (else NotFoundError)'."""
        with self.assertRaises(NotFoundError):
            self.store.budget_vs_actual(self.book_id, PERIOD_FEB, MEMBER)

    def test_actual_for_an_expense_account_is_in_normal_direction(self):
        """Core 7: Budgets. Contract: actual is posted movement 'in
        its normal-balance direction (asset and expense: debits -
        credits ...)'. RentExpense was debited 20000, so actual is
        20000 and variance = budgeted - actual = 5000."""
        result = self.store.budget_vs_actual(
            self.book_id, PERIOD_JAN, MEMBER
        )
        line = self._line_for(result, "rent")
        self.assertEqual(line["type"], "expense")
        self.assertEqual(line["code"], "5000")
        self.assertEqual(line["budgeted_cents"], 25000)
        self.assertEqual(line["actual_cents"], 20000)
        self.assertEqual(line["variance_cents"], 25000 - 20000)

    def test_actual_for_a_revenue_account_is_in_normal_direction(self):
        """Core 7: Budgets. Contract: for revenue the normal direction
        is credits - debits. ServiceRevenue was credited 50000, so
        actual is 50000 and variance = 60000 - 50000."""
        result = self.store.budget_vs_actual(
            self.book_id, PERIOD_JAN, MEMBER
        )
        line = self._line_for(result, "revenue")
        self.assertEqual(line["type"], "revenue")
        self.assertEqual(line["budgeted_cents"], 60000)
        self.assertEqual(line["actual_cents"], 50000)
        self.assertEqual(line["variance_cents"], 60000 - 50000)

    def test_variance_is_budgeted_minus_actual_per_line_and_total(self):
        """Core 7: Budgets. Contract: 'variance_cents = budgeted_cents
        - actual_cents', and the totals are the sums over lines."""
        result = self.store.budget_vs_actual(
            self.book_id, PERIOD_JAN, MEMBER
        )
        for line in result["lines"]:
            self.assertEqual(
                line["variance_cents"],
                line["budgeted_cents"] - line["actual_cents"],
            )
        self.assertEqual(result["total_budgeted_cents"], 85000)
        self.assertEqual(result["total_actual_cents"], 70000)
        self.assertEqual(result["total_variance_cents"], 85000 - 70000)

    def test_entries_in_other_periods_are_excluded(self):
        """Core 7: Budgets. Actual counts posted movement 'within the
        period' only — a posted February rent entry does not move the
        January actual."""
        post_rent(self.store, self.book_id, self.chart,
                  amount_cents=7000, date=DATE_FEB)
        result = self.store.budget_vs_actual(
            self.book_id, PERIOD_JAN, MEMBER
        )
        self.assertEqual(self._line_for(result, "rent")["actual_cents"],
                         20000)

    def test_draft_entries_are_excluded(self):
        """Core 7: Budgets. Actual is *posted* movement — a draft entry
        in the period changes nothing."""
        self.store.create_entry(
            self.book_id, DATE_JAN, "Draft rent",
            balanced_lines(self.chart["rent"]["id"],
                           self.chart["cash"]["id"], 9999),
            MEMBER,
        )
        result = self.store.budget_vs_actual(
            self.book_id, PERIOD_JAN, MEMBER
        )
        self.assertEqual(self._line_for(result, "rent")["actual_cents"],
                         20000)

    def test_pending_entries_are_excluded(self):
        """Core 7: Budgets. A submitted-but-unapproved (pending) entry
        is not posted, so it is excluded from actuals like a draft."""
        entry = self.store.create_entry(
            self.book_id, DATE_JAN, "Pending rent",
            balanced_lines(self.chart["rent"]["id"],
                           self.chart["cash"]["id"], 8888),
            MEMBER,
        )
        self.store.submit_entry(self.book_id, entry["id"], MEMBER)
        result = self.store.budget_vs_actual(
            self.book_id, PERIOD_JAN, MEMBER
        )
        self.assertEqual(self._line_for(result, "rent")["actual_cents"],
                         20000)

    def test_vs_actual_with_no_movement_reports_zero_actual(self):
        """Core 7: Budgets. With a budget but no posted entries, actual
        is 0 and variance equals the budgeted amount. (Checked on a
        fresh book/period so the setUp movement does not interfere:
        February has entries in some tests, so this uses a new store.)
        """
        store, book_id = make_store()
        chart = make_chart(store, book_id)
        store.set_budget(
            book_id, PERIOD_FEB,
            [{"account_id": chart["rent"]["id"], "amount_cents": 4000}],
            MEMBER,
        )
        result = store.budget_vs_actual(book_id, PERIOD_FEB, MEMBER)
        self.assertEqual(result["total_actual_cents"], 0)
        self.assertEqual(result["total_variance_cents"], 4000)


if __name__ == "__main__":
    unittest.main()
