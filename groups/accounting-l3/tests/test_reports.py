"""Financial-reporting tests.

Traces to: UNION-SPEC Core function 9 (Financial reporting — computed
from posted entries only: trial balance, income statement, balance
sheet, per-account balance and activity) / ranking row 2 (Financial
reporting & statements, 12 siblings); Implementation contract for
``accounting/store.py`` report methods.

The coherent scenario used across this module (period 2026-01, all
posted): the owner invests 100000 cents (debit Cash / credit
OwnersEquity), the business earns 50000 (debit Cash / credit
ServiceRevenue), and pays 20000 rent (debit RentExpense / credit
Cash). Therefore: Cash 130000, total assets 130000, equity 100000,
revenue 50000, expenses 20000, net income 30000, and every statement
balances.
"""

import unittest

from accounting_helpers import (
    DATE_FEB,
    MEMBER,
    PERIOD_JAN,
    balanced_lines,
    build_scenario,
    make_chart,
    make_store,
    post_entry,
    post_investment,
    post_revenue,
)

TRIAL_KEYS = {
    "book_id", "period", "accounts", "total_debits_cents",
    "total_credits_cents", "balanced",
}
TRIAL_ROW_KEYS = {
    "account_id", "code", "name", "type", "debit_cents", "credit_cents",
}
BALANCE_KEYS = {
    "account_id", "book_id", "period", "debit_cents", "credit_cents",
    "balance_cents",
}
ACTIVITY_KEYS = {"account_id", "book_id", "period", "lines"}
ACTIVITY_LINE_KEYS = {
    "entry_id", "date", "period", "memo", "debit_cents", "credit_cents",
}
INCOME_KEYS = {
    "book_id", "period", "revenue", "total_revenue_cents", "expenses",
    "total_expense_cents", "net_income_cents",
}
STATEMENT_ROW_KEYS = {"account_id", "code", "name", "amount_cents"}
SHEET_KEYS = {
    "book_id", "through_period", "assets", "total_assets_cents",
    "liabilities", "total_liabilities_cents", "equity",
    "total_equity_cents", "net_income_cents",
    "total_liabilities_equity_cents", "balanced",
}


class ReportBase(unittest.TestCase):
    """The canonical scenario, posted in setUp."""

    def setUp(self):
        self.store, self.book_id = make_store()
        self.chart = make_chart(self.store, self.book_id)
        self.entries = build_scenario(self.store, self.book_id, self.chart)

    def row_for(self, rows, account_key):
        account_id = self.chart[account_key]["id"]
        for row in rows:
            if row["account_id"] == account_id:
                return row
        self.fail("no row for account %s" % account_key)


class TestTrialBalance(ReportBase):
    """Core 9: Financial reporting — trial balance."""

    def test_trial_balance_returns_the_contract_dict(self):
        """Core 9: Financial reporting. Contract: trial_balance
        returns {book_id, period, accounts, total_debits_cents,
        total_credits_cents, balanced}; each account row is
        {account_id, code, name, type, debit_cents, credit_cents}."""
        trial = self.store.trial_balance(self.book_id, MEMBER)
        self.assertEqual(set(trial.keys()), TRIAL_KEYS)
        self.assertEqual(trial["book_id"], self.book_id)
        for row in trial["accounts"]:
            self.assertEqual(set(row.keys()), TRIAL_ROW_KEYS)

    def test_trial_balance_totals_are_equal_and_balanced_flag_true(self):
        """Core 9: Financial reporting. Scenario totals: debits
        130000 (Cash) + 20000 (RentExpense) = 150000; credits 100000
        (Equity) + 50000 (Revenue) = 150000 — the columns total equal
        and the computed balanced flag is true."""
        trial = self.store.trial_balance(self.book_id, MEMBER)
        self.assertEqual(trial["total_debits_cents"], 150000)
        self.assertEqual(trial["total_credits_cents"], 150000)
        self.assertIs(trial["balanced"], True)
        self.assertEqual(
            trial["balanced"],
            trial["total_debits_cents"] == trial["total_credits_cents"],
        )

    def test_debit_credit_column_placement_follows_net_sign(self):
        """Core 9: Financial reporting. Contract: 'a positive net
        appears as debit_cents, a negative net as credit_cents (its
        absolute value)'. Cash and RentExpense sit in the debit column;
        Equity and Revenue in the credit column, the other side 0."""
        trial = self.store.trial_balance(self.book_id, MEMBER)
        cash = self.row_for(trial["accounts"], "cash")
        self.assertEqual((cash["debit_cents"], cash["credit_cents"]),
                         (130000, 0))
        rent = self.row_for(trial["accounts"], "rent")
        self.assertEqual((rent["debit_cents"], rent["credit_cents"]),
                         (20000, 0))
        equity = self.row_for(trial["accounts"], "equity")
        self.assertEqual((equity["debit_cents"], equity["credit_cents"]),
                         (0, 100000))
        revenue = self.row_for(trial["accounts"], "revenue")
        self.assertEqual((revenue["debit_cents"], revenue["credit_cents"]),
                         (0, 50000))

    def test_zero_net_accounts_are_omitted(self):
        """Core 9: Financial reporting. Contract: 'a zero net omits
        the account' — AccountsPayable never moved, so it has no row."""
        trial = self.store.trial_balance(self.book_id, MEMBER)
        ids = [r["account_id"] for r in trial["accounts"]]
        self.assertNotIn(self.chart["payable"]["id"], ids)
        self.assertEqual(len(trial["accounts"]), 4)

    def test_trial_balance_period_filter(self):
        """Core 9: Financial reporting. Contract: 'Posted entries only
        (all periods, or only the given period)' — with an extra
        posted February revenue entry, the January trial balance is
        unchanged and the February one shows only February movement."""
        post_revenue(self.store, self.book_id, self.chart,
                     amount_cents=10000, date=DATE_FEB)
        jan = self.store.trial_balance(
            self.book_id, MEMBER, period=PERIOD_JAN
        )
        self.assertEqual(jan["period"], PERIOD_JAN)
        self.assertEqual(jan["total_debits_cents"], 150000)
        self.assertEqual(jan["total_credits_cents"], 150000)
        self.assertIs(jan["balanced"], True)

        feb = self.store.trial_balance(
            self.book_id, MEMBER, period="2026-02"
        )
        self.assertEqual(feb["total_debits_cents"], 10000)
        self.assertEqual(feb["total_credits_cents"], 10000)
        self.assertIs(feb["balanced"], True)
        cash = self.row_for(feb["accounts"], "cash")
        self.assertEqual(cash["debit_cents"], 10000)

        all_periods = self.store.trial_balance(self.book_id, MEMBER)
        self.assertEqual(all_periods["total_debits_cents"], 160000)
        self.assertEqual(all_periods["total_credits_cents"], 160000)

    def test_trial_balance_of_an_empty_book_is_balanced_at_zero(self):
        """Core 9: Financial reporting. No posted entries: both totals
        are 0, no rows, and balanced is (honestly) true."""
        store, book_id = make_store()
        make_chart(store, book_id)
        trial = store.trial_balance(book_id, MEMBER)
        self.assertEqual(trial["accounts"], [])
        self.assertEqual(trial["total_debits_cents"], 0)
        self.assertEqual(trial["total_credits_cents"], 0)
        self.assertIs(trial["balanced"], True)


class TestAccountBalance(ReportBase):
    """Core 9: Financial reporting — per-account balance."""

    def test_account_balance_returns_the_contract_dict(self):
        """Core 9: Financial reporting. Contract: account_balance
        returns {account_id, book_id, period, debit_cents,
        credit_cents, balance_cents} — raw posted totals plus the
        normal-direction signed balance."""
        balance = self.store.account_balance(
            self.book_id, self.chart["cash"]["id"], MEMBER
        )
        self.assertEqual(set(balance.keys()), BALANCE_KEYS)
        self.assertEqual(balance["account_id"], self.chart["cash"]["id"])
        self.assertEqual(balance["book_id"], self.book_id)

    def test_asset_balance_uses_debits_minus_credits(self):
        """Core 9: Financial reporting. Cash (asset, normal direction
        debits - credits): debits 150000, credits 20000, balance
        130000."""
        balance = self.store.account_balance(
            self.book_id, self.chart["cash"]["id"], MEMBER
        )
        self.assertEqual(balance["debit_cents"], 150000)
        self.assertEqual(balance["credit_cents"], 20000)
        self.assertEqual(balance["balance_cents"], 130000)

    def test_equity_and_revenue_balances_use_credits_minus_debits(self):
        """Core 9: Financial reporting. For equity/revenue the normal
        direction is credits - debits: OwnersEquity 100000,
        ServiceRevenue 50000."""
        equity = self.store.account_balance(
            self.book_id, self.chart["equity"]["id"], MEMBER
        )
        self.assertEqual(equity["balance_cents"], 100000)
        revenue = self.store.account_balance(
            self.book_id, self.chart["revenue"]["id"], MEMBER
        )
        self.assertEqual(revenue["balance_cents"], 50000)

    def test_liability_balance_uses_credits_minus_debits(self):
        """Core 9: Financial reporting. A liability's signed balance is
        credits - debits: buying on credit (debit RentExpense / credit
        AccountsPayable 7000) gives AccountsPayable balance +7000 with
        raw totals debit 0 / credit 7000. (Isolated store so the
        canonical scenario totals stay untouched.)"""
        store, book_id = make_store()
        chart = make_chart(store, book_id)
        post_entry(
            store, book_id, "2026-01-20", "Supplies on credit",
            balanced_lines(chart["rent"]["id"], chart["payable"]["id"],
                           7000),
        )
        balance = store.account_balance(
            book_id, chart["payable"]["id"], MEMBER
        )
        self.assertEqual(balance["debit_cents"], 0)
        self.assertEqual(balance["credit_cents"], 7000)
        self.assertEqual(balance["balance_cents"], 7000)

    def test_account_balance_period_filter(self):
        """Core 9: Financial reporting. account_balance optionally
        restricts to one period: Cash in February (after a posted
        February revenue entry) shows only that movement."""
        post_revenue(self.store, self.book_id, self.chart,
                     amount_cents=10000, date=DATE_FEB)
        feb = self.store.account_balance(
            self.book_id, self.chart["cash"]["id"], MEMBER,
            period="2026-02",
        )
        self.assertEqual(feb["period"], "2026-02")
        self.assertEqual(feb["debit_cents"], 10000)
        self.assertEqual(feb["credit_cents"], 0)
        self.assertEqual(feb["balance_cents"], 10000)
        jan = self.store.account_balance(
            self.book_id, self.chart["cash"]["id"], MEMBER,
            period=PERIOD_JAN,
        )
        self.assertEqual(jan["balance_cents"], 130000)


class TestAccountActivity(ReportBase):
    """Core 9: Financial reporting — per-account activity."""

    def test_account_activity_returns_the_contract_dict(self):
        """Core 9: Financial reporting. Contract: account_activity
        returns {account_id, book_id, period, lines}; each line is
        {entry_id, date, period, memo, debit_cents, credit_cents}."""
        activity = self.store.account_activity(
            self.book_id, self.chart["cash"]["id"], MEMBER
        )
        self.assertEqual(set(activity.keys()), ACTIVITY_KEYS)
        self.assertEqual(activity["account_id"], self.chart["cash"]["id"])
        for line in activity["lines"]:
            self.assertEqual(set(line.keys()), ACTIVITY_LINE_KEYS)

    def test_account_activity_is_posted_only_and_chronological(self):
        """Core 9: Financial reporting. Cash activity lists the posted
        lines in entry creation order with their per-line amounts —
        investment debit 100000, revenue debit 50000, rent credit
        20000 — and a draft entry touching Cash is excluded."""
        self.store.create_entry(
            self.book_id, "2026-01-25", "Draft cash movement",
            balanced_lines(self.chart["cash"]["id"],
                           self.chart["equity"]["id"], 7777),
            MEMBER,
        )
        activity = self.store.account_activity(
            self.book_id, self.chart["cash"]["id"], MEMBER
        )
        lines = activity["lines"]
        self.assertEqual(len(lines), 3)
        self.assertEqual(
            [ln["entry_id"] for ln in lines],
            [e["id"] for e in self.entries],
        )
        self.assertEqual(
            [(ln["debit_cents"], ln["credit_cents"]) for ln in lines],
            [(100000, 0), (50000, 0), (0, 20000)],
        )
        self.assertEqual(
            [ln["memo"] for ln in lines],
            ["Owner investment", "Services earned", "Rent paid"],
        )
        self.assertTrue(all(ln["period"] == PERIOD_JAN for ln in lines))

    def test_account_activity_for_an_unused_account_is_empty(self):
        """Core 9: Financial reporting. An account with no posted lines
        has empty activity."""
        activity = self.store.account_activity(
            self.book_id, self.chart["payable"]["id"], MEMBER
        )
        self.assertEqual(activity["lines"], [])


class TestIncomeStatement(ReportBase):
    """Core 9: Financial reporting — income statement for a period."""

    def test_income_statement_returns_the_contract_dict(self):
        """Core 9: Financial reporting. Contract: income_statement
        returns {book_id, period, revenue, total_revenue_cents,
        expenses, total_expense_cents, net_income_cents}; each row is
        {account_id, code, name, amount_cents}."""
        statement = self.store.income_statement(
            self.book_id, PERIOD_JAN, MEMBER
        )
        self.assertEqual(set(statement.keys()), INCOME_KEYS)
        self.assertEqual(statement["book_id"], self.book_id)
        self.assertEqual(statement["period"], PERIOD_JAN)
        for row in statement["revenue"] + statement["expenses"]:
            self.assertEqual(set(row.keys()), STATEMENT_ROW_KEYS)

    def test_income_statement_rows_and_net(self):
        """Core 9: Financial reporting. Scenario: revenue row
        ServiceRevenue 50000 (credits - debits), expense row
        RentExpense 20000 (debits - credits), net = revenue -
        expenses = 30000."""
        statement = self.store.income_statement(
            self.book_id, PERIOD_JAN, MEMBER
        )
        revenue = self.row_for(statement["revenue"], "revenue")
        self.assertEqual(revenue["amount_cents"], 50000)
        self.assertEqual(revenue["code"], "4000")
        expense = self.row_for(statement["expenses"], "rent")
        self.assertEqual(expense["amount_cents"], 20000)
        self.assertEqual(statement["total_revenue_cents"], 50000)
        self.assertEqual(statement["total_expense_cents"], 20000)
        self.assertEqual(statement["net_income_cents"], 50000 - 20000)
        self.assertEqual(
            statement["net_income_cents"],
            statement["total_revenue_cents"]
            - statement["total_expense_cents"],
        )

    def test_income_statement_excludes_other_periods(self):
        """Core 9: Financial reporting. The statement covers exactly
        the given period: a posted February revenue entry appears in
        February's statement, not January's."""
        post_revenue(self.store, self.book_id, self.chart,
                     amount_cents=10000, date=DATE_FEB)
        jan = self.store.income_statement(self.book_id, PERIOD_JAN, MEMBER)
        self.assertEqual(jan["total_revenue_cents"], 50000)
        self.assertEqual(jan["net_income_cents"], 30000)
        feb = self.store.income_statement(self.book_id, "2026-02", MEMBER)
        self.assertEqual(feb["total_revenue_cents"], 10000)
        self.assertEqual(feb["total_expense_cents"], 0)
        self.assertEqual(feb["net_income_cents"], 10000)

    def test_income_statement_for_an_empty_period_is_zero(self):
        """Core 9: Financial reporting. A period with no posted
        movement has no rows and zero totals."""
        statement = self.store.income_statement(
            self.book_id, "2026-03", MEMBER
        )
        self.assertEqual(statement["revenue"], [])
        self.assertEqual(statement["expenses"], [])
        self.assertEqual(statement["net_income_cents"], 0)


class TestBalanceSheet(ReportBase):
    """Core 9: Financial reporting — balance sheet through a period."""

    def test_balance_sheet_returns_the_contract_dict(self):
        """Core 9: Financial reporting. Contract: balance_sheet
        returns {book_id, through_period, assets,
        total_assets_cents, liabilities, total_liabilities_cents,
        equity, total_equity_cents, net_income_cents,
        total_liabilities_equity_cents, balanced}; rows are
        {account_id, code, name, amount_cents}."""
        sheet = self.store.balance_sheet(self.book_id, MEMBER)
        self.assertEqual(set(sheet.keys()), SHEET_KEYS)
        self.assertEqual(sheet["book_id"], self.book_id)
        for row in (sheet["assets"] + sheet["liabilities"]
                    + sheet["equity"]):
            self.assertEqual(set(row.keys()), STATEMENT_ROW_KEYS)

    def test_balance_sheet_balances_on_the_scenario(self):
        """Core 9: Financial reporting. Scenario: assets 130000 =
        liabilities 0 + equity 100000 + cumulative net income 30000,
        so assets == liabilities + equity + net income and the
        computed balanced flag is true."""
        sheet = self.store.balance_sheet(self.book_id, MEMBER)
        cash = self.row_for(sheet["assets"], "cash")
        self.assertEqual(cash["amount_cents"], 130000)
        self.assertEqual(sheet["total_assets_cents"], 130000)
        self.assertEqual(sheet["liabilities"], [])
        self.assertEqual(sheet["total_liabilities_cents"], 0)
        equity = self.row_for(sheet["equity"], "equity")
        self.assertEqual(equity["amount_cents"], 100000)
        self.assertEqual(sheet["total_equity_cents"], 100000)
        self.assertEqual(sheet["net_income_cents"], 30000)
        self.assertEqual(
            sheet["total_liabilities_equity_cents"],
            sheet["total_liabilities_cents"]
            + sheet["total_equity_cents"]
            + sheet["net_income_cents"],
        )
        self.assertEqual(sheet["total_liabilities_equity_cents"], 130000)
        self.assertIs(sheet["balanced"], True)
        self.assertEqual(
            sheet["balanced"],
            sheet["total_assets_cents"]
            == sheet["total_liabilities_equity_cents"],
        )

    def test_balance_sheet_through_period_excludes_later_entries(self):
        """Core 9: Financial reporting. Contract: the sheet is
        'cumulative over posted entries with period <=
        through_period' — a posted February revenue entry is excluded
        through January (assets stay 130000, net income 30000) and
        included through February (assets 140000, net income 40000)."""
        post_revenue(self.store, self.book_id, self.chart,
                     amount_cents=10000, date=DATE_FEB)
        through_jan = self.store.balance_sheet(
            self.book_id, MEMBER, through_period=PERIOD_JAN
        )
        self.assertEqual(through_jan["through_period"], PERIOD_JAN)
        self.assertEqual(through_jan["total_assets_cents"], 130000)
        self.assertEqual(through_jan["net_income_cents"], 30000)
        self.assertIs(through_jan["balanced"], True)

        through_feb = self.store.balance_sheet(
            self.book_id, MEMBER, through_period="2026-02"
        )
        self.assertEqual(through_feb["total_assets_cents"], 140000)
        self.assertEqual(through_feb["net_income_cents"], 40000)
        self.assertIs(through_feb["balanced"], True)

        unrestricted = self.store.balance_sheet(self.book_id, MEMBER)
        self.assertEqual(unrestricted["total_assets_cents"], 140000)

    def test_balance_sheet_includes_liabilities(self):
        """Core 9: Financial reporting. With a credit purchase posted
        (debit RentExpense / credit AccountsPayable 7000), liabilities
        total 7000 and the sheet still balances: assets 130000 =
        liabilities 7000 + equity 100000 + net income 23000."""
        post_entry(
            self.store, self.book_id, "2026-01-20", "Supplies on credit",
            balanced_lines(self.chart["rent"]["id"],
                           self.chart["payable"]["id"], 7000),
        )
        sheet = self.store.balance_sheet(self.book_id, MEMBER)
        payable = self.row_for(sheet["liabilities"], "payable")
        self.assertEqual(payable["amount_cents"], 7000)
        self.assertEqual(sheet["total_liabilities_cents"], 7000)
        self.assertEqual(sheet["net_income_cents"], 30000 - 7000)
        self.assertEqual(sheet["total_assets_cents"], 130000)
        self.assertEqual(
            sheet["total_liabilities_equity_cents"], 130000
        )
        self.assertIs(sheet["balanced"], True)


if __name__ == "__main__":
    unittest.main()
