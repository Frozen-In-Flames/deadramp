"""Spend budget and spend-vs-budget tests.

Traces to: UNION-SPEC Core function 5 (Spend budgets & tracking — a
budget per program per period; spend-vs-budget computed from records:
non-cancelled bookings by kind, disbursed wage access under the
``earned_wage`` category); Implementation contract for
``finance/store.py`` budget methods (``set_budget``, ``get_budget``,
``spend_vs_budget``); control family SI-10 (integer cents, validation
before mutation).
"""

import unittest

from finance_helpers import (
    MEMBER,
    PERIOD,
    PERIOD_OTHER,
    disbursed_request,
    make_accrual,
    make_booking,
    make_employee,
    make_store,
    make_traveler,
)
from finance.errors import NotFoundError, ValidationError

BUDGET_KEYS = {
    "id", "program_id", "period", "lines", "total_cents", "created_by",
    "created_utc", "updated_utc",
}
SPEND_KEYS = {
    "program_id", "period", "lines", "total_budgeted_cents",
    "total_spent_cents", "total_variance_cents", "unbudgeted",
}
SPEND_LINE_KEYS = {
    "category", "limit_cents", "spent_cents", "variance_cents",
    "over_budget",
}
UNBUDGETED_KEYS = {"category", "spent_cents"}


class BudgetBase(unittest.TestCase):
    """A canonical program with one employee and one traveler."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.employee = make_employee(self.store, self.program_id)
        self.traveler = make_traveler(self.store, self.program_id)
        self.emp_id = self.employee["id"]
        self.trav_id = self.traveler["id"]

    def set_jan_budget(self):
        """Budget for 2026-01: air 50000, hotel 30000, earned_wage 20000."""
        return self.store.set_budget(
            self.program_id, PERIOD,
            [
                {"category": "air", "limit_cents": 50000},
                {"category": "hotel", "limit_cents": 30000},
                {"category": "earned_wage", "limit_cents": 20000},
            ],
            MEMBER,
        )

    def build_spend(self):
        """Records spending in 2026-01 (and decoys outside it).

        In-period spend: air booking 40000 (recorded), hotel booking
        35000 (confirmed), earned-wage disbursement 15000 dated
        2026-01-20. Excluded decoys: an air booking starting in
        February (9999), a cancelled air booking in January (5000).
        """
        make_booking(self.store, self.program_id, self.trav_id, kind="air",
                     start_date="2026-01-10", end_date="2026-01-12",
                     amount_cents=40000)
        hotel = make_booking(self.store, self.program_id, self.trav_id,
                             kind="hotel", start_date="2026-01-15",
                             end_date="2026-01-17", amount_cents=35000)
        self.store.confirm_booking(self.program_id, hotel["id"], MEMBER)
        make_booking(self.store, self.program_id, self.trav_id, kind="air",
                     start_date="2026-02-01", end_date="2026-02-03",
                     amount_cents=9999)
        cancelled = make_booking(self.store, self.program_id, self.trav_id,
                                 kind="air", start_date="2026-01-05",
                                 end_date="2026-01-06", amount_cents=5000)
        self.store.cancel_booking(self.program_id, cancelled["id"], MEMBER)
        make_accrual(self.store, self.program_id, self.emp_id, PERIOD, 100000)
        disbursed_request(
            self.store, self.program_id, self.emp_id, period=PERIOD,
            amount_cents=15000, request_date="2026-01-10",
            disbursement_date="2026-01-20",
        )


class TestSetBudget(BudgetBase):
    """Core 5: Spend budgets — set/get shape, replace, validation."""

    def test_set_budget_returns_the_contract_dict(self):
        """Core 5: Spend budgets. Contract: set_budget returns {id,
        program_id, period, lines, total_cents, created_by,
        created_utc, updated_utc} with the bud- prefix."""
        budget = self.set_jan_budget()
        self.assertEqual(set(budget.keys()), BUDGET_KEYS)
        self.assertEqual(budget["id"], "bud-1")
        self.assertEqual(budget["program_id"], self.program_id)
        self.assertEqual(budget["period"], PERIOD)
        self.assertEqual(budget["created_by"], "bob")
        self.assertEqual(len(budget["lines"]), 3)

    def test_total_cents_is_the_sum_of_lines(self):
        """Core 5: Spend budgets. Contract: total_cents is the sum of
        the lines' limit_cents."""
        budget = self.set_jan_budget()
        self.assertEqual(budget["total_cents"], 50000 + 30000 + 20000)

    def test_get_budget_roundtrip(self):
        """Core 5: Spend budgets. get_budget returns the budget set
        for the period."""
        budget = self.set_jan_budget()
        got = self.store.get_budget(self.program_id, PERIOD, MEMBER)
        self.assertEqual(got["id"], budget["id"])
        self.assertEqual(got["total_cents"], budget["total_cents"])
        self.assertEqual(got["lines"], budget["lines"])

    def test_get_budget_for_a_missing_period_is_not_found(self):
        """Core 5: Spend budgets. Contract: get_budget ->
        NotFoundError if none was set for that period."""
        with self.assertRaises(NotFoundError):
            self.store.get_budget(self.program_id, PERIOD_OTHER, MEMBER)
        self.set_jan_budget()
        with self.assertRaises(NotFoundError):
            self.store.get_budget(self.program_id, PERIOD_OTHER, MEMBER)

    def test_replace_keeps_id_and_created_utc_and_replaces_lines(self):
        """Core 5: Spend budgets. Contract: 'One budget per (program,
        period): if one exists, its lines and total are replaced, its
        id, created_by, and created_utc are kept, and updated_utc is
        refreshed.'"""
        first = self.set_jan_budget()
        replaced = self.store.set_budget(
            self.program_id, PERIOD,
            [{"category": "air", "limit_cents": 7000}], MEMBER,
        )
        self.assertEqual(replaced["id"], first["id"])
        self.assertEqual(replaced["created_by"], first["created_by"])
        self.assertEqual(replaced["created_utc"], first["created_utc"])
        self.assertIn("updated_utc", replaced)
        self.assertEqual(
            replaced["lines"], [{"category": "air", "limit_cents": 7000}]
        )
        self.assertEqual(replaced["total_cents"], 7000)
        got = self.store.get_budget(self.program_id, PERIOD, MEMBER)
        self.assertEqual(got["id"], first["id"])
        self.assertEqual(got["total_cents"], 7000)

    def test_replace_does_not_create_a_second_budget_id(self):
        """Core 5: Spend budgets. Replacing a period's budget consumes
        no new id: the next new period's budget is bud-2."""
        self.set_jan_budget()
        self.store.set_budget(
            self.program_id, PERIOD,
            [{"category": "air", "limit_cents": 1}], MEMBER,
        )
        feb = self.store.set_budget(
            self.program_id, PERIOD_OTHER,
            [{"category": "air", "limit_cents": 2}], MEMBER,
        )
        self.assertEqual(feb["id"], "bud-2")

    def test_duplicate_category_is_a_validation_error(self):
        """Core 5: Spend budgets. Contract: 'a repeated category in
        one call -> ValidationError', and nothing is stored."""
        with self.assertRaises(ValidationError):
            self.store.set_budget(
                self.program_id, PERIOD,
                [
                    {"category": "air", "limit_cents": 1000},
                    {"category": "air", "limit_cents": 2000},
                ],
                MEMBER,
            )
        with self.assertRaises(NotFoundError):
            self.store.get_budget(self.program_id, PERIOD, MEMBER)

    def test_unknown_or_bad_lines_are_validation_errors(self):
        """Core 5: Spend budgets (SI-10). Contract: lines are dicts
        {category, limit_cents} with a non-empty string category and
        an int limit >= 0 — empty lines, non-list lines, missing keys,
        an empty category, and negative/float/bool limits are all
        rejected whole."""
        bad_lines = (
            [],
            None,
            "air",
            [{"limit_cents": 1000}],
            [{"category": "air"}],
            [{"category": "", "limit_cents": 1000}],
            [{"category": 42, "limit_cents": 1000}],
            [{"category": "air", "limit_cents": -1}],
            [{"category": "air", "limit_cents": 10.0}],
            [{"category": "air", "limit_cents": True}],
            ["air"],
        )
        for lines in bad_lines:
            with self.subTest(lines=lines):
                with self.assertRaises(ValidationError):
                    self.store.set_budget(self.program_id, PERIOD, lines,
                                          MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_budget(self.program_id, PERIOD, MEMBER)

    def test_zero_limit_line_is_accepted(self):
        """Core 5: Spend budgets. limit_cents is an int >= 0, so a
        zero line is valid."""
        budget = self.store.set_budget(
            self.program_id, PERIOD,
            [{"category": "air", "limit_cents": 0}], MEMBER,
        )
        self.assertEqual(budget["total_cents"], 0)

    def test_invalid_period_is_a_validation_error(self):
        """Core 5: Spend budgets. Contract: period must be a valid
        YYYY-MM."""
        for bad in ("2026-13", "2026-1", "Jan 2026", "2026-01-05"):
            with self.subTest(period=bad):
                with self.assertRaises(ValidationError):
                    self.store.set_budget(
                        self.program_id, bad,
                        [{"category": "air", "limit_cents": 1000}], MEMBER,
                    )


class TestSpendVsBudget(BudgetBase):
    """Core 5: Spend budgets — spend-vs-budget computed from records."""

    def setUp(self):
        super().setUp()
        self.budget = self.set_jan_budget()
        self.build_spend()

    def _line_for(self, result, category):
        for line in result["lines"]:
            if line["category"] == category:
                return line
        self.fail("no spend-vs-budget line for category %s" % category)

    def test_spend_vs_budget_returns_the_contract_dict(self):
        """Core 5: Spend budgets. Contract: spend_vs_budget returns
        {program_id, period, lines, total_budgeted_cents,
        total_spent_cents, total_variance_cents, unbudgeted}; each
        line is {category, limit_cents, spent_cents, variance_cents,
        over_budget}; each unbudgeted entry is {category,
        spent_cents}."""
        result = self.store.spend_vs_budget(self.program_id, PERIOD, MEMBER)
        self.assertEqual(set(result.keys()), SPEND_KEYS)
        self.assertEqual(result["program_id"], self.program_id)
        self.assertEqual(result["period"], PERIOD)
        for line in result["lines"]:
            self.assertEqual(set(line.keys()), SPEND_LINE_KEYS)
        for entry in result["unbudgeted"]:
            self.assertEqual(set(entry.keys()), UNBUDGETED_KEYS)

    def test_spend_vs_budget_requires_a_budget(self):
        """Core 5: Spend budgets. Contract: spend_vs_budget 'requires
        a budget for the period (else NotFoundError)'."""
        with self.assertRaises(NotFoundError):
            self.store.spend_vs_budget(self.program_id, PERIOD_OTHER, MEMBER)

    def test_bookings_counted_by_kind_in_start_month(self):
        """Core 5: Spend budgets. Contract: spent for a category is
        the sum of bookings whose kind equals the category, whose
        status is recorded or confirmed, and whose start_date falls
        in the period — air 40000 (the February air booking and the
        cancelled January one excluded), hotel 35000."""
        result = self.store.spend_vs_budget(self.program_id, PERIOD, MEMBER)
        self.assertEqual(self._line_for(result, "air")["spent_cents"], 40000)
        self.assertEqual(self._line_for(result, "hotel")["spent_cents"],
                         35000)

    def test_disbursements_counted_under_earned_wage_in_disbursement_month(self):
        """Core 5: Spend budgets. Contract: for the category
        earned_wage, spent is the sum of disbursement amounts whose
        date falls in the period — 15000 disbursed 2026-01-20."""
        result = self.store.spend_vs_budget(self.program_id, PERIOD, MEMBER)
        line = self._line_for(result, "earned_wage")
        self.assertEqual(line["spent_cents"], 15000)

    def test_disbursement_in_another_month_is_not_counted(self):
        """Core 5: Spend budgets. A disbursement is counted in its
        *disbursement* month: a January-period request disbursed on
        2026-02-02 does not add to January's earned_wage spend."""
        store, audit, program_id = make_store()
        employee = make_employee(store, program_id)
        make_accrual(store, program_id, employee["id"], PERIOD, 100000)
        disbursed_request(
            store, program_id, employee["id"], period=PERIOD,
            amount_cents=9000, request_date="2026-01-28",
            disbursement_date="2026-02-02",
        )
        store.set_budget(
            program_id, PERIOD,
            [{"category": "earned_wage", "limit_cents": 20000}], MEMBER,
        )
        jan = store.spend_vs_budget(program_id, PERIOD, MEMBER)
        self.assertEqual(jan["lines"][0]["spent_cents"], 0)
        store.set_budget(
            program_id, PERIOD_OTHER,
            [{"category": "earned_wage", "limit_cents": 20000}], MEMBER,
        )
        feb = store.spend_vs_budget(program_id, PERIOD_OTHER, MEMBER)
        self.assertEqual(feb["lines"][0]["spent_cents"], 9000)

    def test_variance_is_limit_minus_spent_and_over_budget_flag(self):
        """Core 5: Spend budgets. Contract: variance_cents =
        limit_cents - spent_cents and over_budget = spent > limit —
        hotel (35000 over a 30000 limit) is over budget with variance
        -5000; air and earned_wage are not over."""
        result = self.store.spend_vs_budget(self.program_id, PERIOD, MEMBER)
        air = self._line_for(result, "air")
        self.assertEqual(air["variance_cents"], 50000 - 40000)
        self.assertIs(air["over_budget"], False)
        hotel = self._line_for(result, "hotel")
        self.assertEqual(hotel["variance_cents"], 30000 - 35000)
        self.assertIs(hotel["over_budget"], True)
        wage = self._line_for(result, "earned_wage")
        self.assertEqual(wage["variance_cents"], 20000 - 15000)
        self.assertIs(wage["over_budget"], False)
        for line in result["lines"]:
            self.assertEqual(
                line["variance_cents"],
                line["limit_cents"] - line["spent_cents"],
            )
            self.assertEqual(
                line["over_budget"], line["spent_cents"] > line["limit_cents"]
            )

    def test_totals_are_consistent(self):
        """Core 5: Spend budgets. Contract: total_budgeted is the sum
        of line limits (100000); total_spent is the sum of line spent
        plus unbudgeted spent (here 40000 + 35000 + 15000 = 90000, no
        unbudgeted categories); total_variance = budgeted - spent."""
        result = self.store.spend_vs_budget(self.program_id, PERIOD, MEMBER)
        self.assertEqual(result["unbudgeted"], [])
        self.assertEqual(result["total_budgeted_cents"], 100000)
        self.assertEqual(result["total_spent_cents"], 90000)
        self.assertEqual(result["total_variance_cents"], 100000 - 90000)
        self.assertEqual(
            result["total_variance_cents"],
            result["total_budgeted_cents"] - result["total_spent_cents"],
        )

    def test_unbudgeted_categories_are_listed_sorted(self):
        """Core 5: Spend budgets. Contract: unbudgeted lists
        {category, spent_cents} for categories with spending in the
        period but no budget line, sorted by category — with a budget
        covering only air, hotel (35000) and earned_wage (15000) are
        unbudgeted, in that sorted order, and they still count toward
        total_spent."""
        store, audit, program_id = make_store()
        employee = make_employee(store, program_id)
        traveler = make_traveler(store, program_id)
        make_booking(store, program_id, traveler["id"], kind="hotel",
                     start_date="2026-01-15", end_date="2026-01-17",
                     amount_cents=35000)
        make_accrual(store, program_id, employee["id"], PERIOD, 100000)
        disbursed_request(
            store, program_id, employee["id"], period=PERIOD,
            amount_cents=15000, disbursement_date="2026-01-20",
        )
        store.set_budget(
            program_id, PERIOD,
            [{"category": "air", "limit_cents": 50000}], MEMBER,
        )
        result = store.spend_vs_budget(program_id, PERIOD, MEMBER)
        self.assertEqual(
            result["unbudgeted"],
            [
                {"category": "earned_wage", "spent_cents": 15000},
                {"category": "hotel", "spent_cents": 35000},
            ],
        )
        self.assertEqual(result["total_budgeted_cents"], 50000)
        self.assertEqual(result["total_spent_cents"], 50000)
        self.assertEqual(result["total_variance_cents"], 0)
        self.assertEqual(result["lines"][0]["spent_cents"], 0)

    def test_spend_with_budget_but_no_records_is_zero(self):
        """Core 5: Spend budgets. With a budget but no bookings or
        disbursements, spent is 0, variance equals the limit, and
        nothing is over budget or unbudgeted."""
        store, audit, program_id = make_store()
        store.set_budget(
            program_id, PERIOD,
            [{"category": "air", "limit_cents": 4000}], MEMBER,
        )
        result = store.spend_vs_budget(program_id, PERIOD, MEMBER)
        self.assertEqual(result["total_spent_cents"], 0)
        self.assertEqual(result["total_variance_cents"], 4000)
        self.assertEqual(result["unbudgeted"], [])
        self.assertIs(result["lines"][0]["over_budget"], False)


if __name__ == "__main__":
    unittest.main()
