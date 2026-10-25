"""Expense tests.

Traces to: UNION-SPEC Core function 6 (Expenses — expense records
running the same approval machine; an approved expense can be marked
reimbursed) and Core function 10 (Workflow & approvals, with
separation of duties); Implementation contract for
``accounting/store.py`` expense methods; control families SI-10
(integer cents) and AC-5 (separation of duties).
"""

import unittest

from accounting_helpers import ADMIN, MEMBER, make_store
from accounting.errors import NotFoundError, PermissionDenied, ValidationError

EXPENSE_KEYS = {
    "id", "book_id", "date", "category", "description", "amount_cents",
    "status", "created_by", "created_utc", "submitted_by", "approved_by",
}
DATE = "2026-01-08"


class ExpenseBase(unittest.TestCase):
    """A canonical book (expenses need no chart accounts)."""

    def setUp(self):
        self.store, self.book_id = make_store()

    def create_expense(self, amount_cents=2500, category="travel",
                       description="Taxi to client site", date=DATE,
                       actor=MEMBER):
        return self.store.create_expense(
            self.book_id, date, category, description, amount_cents, actor
        )

    def pending_expense(self, **kwargs):
        expense = self.create_expense(**kwargs)
        self.store.submit_expense(self.book_id, expense["id"], MEMBER)
        return expense

    def approved_expense(self, **kwargs):
        expense = self.pending_expense(**kwargs)
        return self.store.approve_expense(
            self.book_id, expense["id"], ADMIN
        )


class TestCreateExpense(ExpenseBase):
    """Core 6: Expenses — creation shape and validation."""

    def test_create_returns_the_contract_dict(self):
        """Core 6: Expenses. Contract: create_expense returns {id,
        book_id, date, category, description, amount_cents, status,
        created_by, created_utc, submitted_by, approved_by}."""
        expense = self.create_expense()
        self.assertEqual(set(expense.keys()), EXPENSE_KEYS)
        self.assertEqual(expense["id"], "exp-1")
        self.assertEqual(expense["book_id"], self.book_id)
        self.assertEqual(expense["date"], DATE)
        self.assertEqual(expense["category"], "travel")
        self.assertEqual(expense["description"], "Taxi to client site")
        self.assertEqual(expense["amount_cents"], 2500)
        self.assertEqual(expense["created_by"], "bob")

    def test_initial_status_is_draft_with_empty_provenance(self):
        """Core 6 / Core 10: Expenses + workflow. Contract: status
        draft; submitted_by/approved_by start as None."""
        expense = self.create_expense()
        self.assertEqual(expense["status"], "draft")
        self.assertIsNone(expense["submitted_by"])
        self.assertIsNone(expense["approved_by"])

    def test_zero_amount_is_a_validation_error(self):
        """Core 6: Expenses. Contract: amount_cents is a positive
        int."""
        with self.assertRaises(ValidationError):
            self.create_expense(amount_cents=0)
        self.assertEqual(self.store.list_expenses(self.book_id, MEMBER), [])

    def test_negative_amount_is_a_validation_error(self):
        """Core 6: Expenses. Contract: amount_cents is a positive int,
        so a negative amount is rejected."""
        with self.assertRaises(ValidationError):
            self.create_expense(amount_cents=-2500)
        self.assertEqual(self.store.list_expenses(self.book_id, MEMBER), [])

    def test_float_amount_is_a_validation_error(self):
        """Core 6: Expenses (SI-10, integer-cents rule). Floats are
        rejected even when integral, and bools are rejected."""
        for bad_amount in (25.5, 25.0, True):
            with self.subTest(amount=bad_amount):
                with self.assertRaises(ValidationError):
                    self.create_expense(amount_cents=bad_amount)
        self.assertEqual(self.store.list_expenses(self.book_id, MEMBER), [])

    def test_empty_category_is_a_validation_error(self):
        """Core 6: Expenses. Contract: category is a non-empty
        string."""
        with self.assertRaises(ValidationError):
            self.create_expense(category="")
        self.assertEqual(self.store.list_expenses(self.book_id, MEMBER), [])

    def test_empty_description_is_a_validation_error(self):
        """Core 6: Expenses. Contract: description is a non-empty
        string."""
        with self.assertRaises(ValidationError):
            self.create_expense(description="")

    def test_failed_create_consumes_no_id(self):
        """Core 6: Expenses (SI-10). A failed creation stores nothing
        and consumes no id."""
        with self.assertRaises(ValidationError):
            self.create_expense(amount_cents=0)
        expense = self.create_expense()
        self.assertEqual(expense["id"], "exp-1")

    def test_get_and_list_expenses(self):
        """Core 6: Expenses. get_expense returns the expense dict;
        list_expenses is in creation order; unknown id ->
        NotFoundError."""
        first = self.create_expense()
        second = self.create_expense(description="Hotel")
        got = self.store.get_expense(self.book_id, first["id"], MEMBER)
        self.assertEqual(got["id"], first["id"])
        listed = self.store.list_expenses(self.book_id, MEMBER)
        self.assertEqual(
            [e["id"] for e in listed], [first["id"], second["id"]]
        )
        with self.assertRaises(NotFoundError):
            self.store.get_expense(self.book_id, "exp-999999", MEMBER)


class TestExpenseStateMachine(ExpenseBase):
    """Core 10: Workflow — the expense machine and reimbursement."""

    def test_machine_runs_draft_to_approved(self):
        """Core 10 / Core 6: Workflow + expenses. Contract: submit
        moves draft -> pending (sets submitted_by); approve_expense
        moves pending -> approved (sets approved_by)."""
        expense = self.create_expense()
        submitted = self.store.submit_expense(
            self.book_id, expense["id"], MEMBER
        )
        self.assertEqual(submitted["status"], "pending")
        self.assertEqual(submitted["submitted_by"], "bob")
        approved = self.store.approve_expense(
            self.book_id, expense["id"], ADMIN
        )
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["approved_by"], "alice")

    def test_approve_by_creator_is_denied_separation_of_duties(self):
        """Core 10: Workflow (AC-5). Contract: approval requires an
        actor other than the creator — the creator's approve raises
        PermissionDenied and the expense stays pending."""
        expense = self.pending_expense()
        with self.assertRaises(PermissionDenied):
            self.store.approve_expense(self.book_id, expense["id"], MEMBER)
        after = self.store.get_expense(self.book_id, expense["id"], MEMBER)
        self.assertEqual(after["status"], "pending")
        self.assertIsNone(after["approved_by"])

    def test_reject_by_creator_is_denied_separation_of_duties(self):
        """Core 10: Workflow (AC-5). Rejection carries the same SoD
        rule as approval."""
        expense = self.pending_expense()
        with self.assertRaises(PermissionDenied):
            self.store.reject_expense(self.book_id, expense["id"], MEMBER)
        after = self.store.get_expense(self.book_id, expense["id"], MEMBER)
        self.assertEqual(after["status"], "pending")

    def test_reject_then_void(self):
        """Core 10: Workflow. Reject moves pending -> rejected, and
        void is available from rejected to the creator."""
        expense = self.pending_expense()
        rejected = self.store.reject_expense(
            self.book_id, expense["id"], ADMIN
        )
        self.assertEqual(rejected["status"], "rejected")
        voided = self.store.void_expense(self.book_id, expense["id"], MEMBER)
        self.assertEqual(voided["status"], "void")

    def test_reimburse_from_approved_moves_to_reimbursed(self):
        """Core 6: Expenses. Contract: reimburse_expense moves status
        approved -> reimbursed."""
        expense = self.approved_expense()
        reimbursed = self.store.reimburse_expense(
            self.book_id, expense["id"], MEMBER
        )
        self.assertEqual(reimbursed["status"], "reimbursed")

    def test_reimburse_from_draft_is_a_validation_error(self):
        """Core 6: Expenses. Contract: reimburse requires status
        approved — a draft cannot be reimbursed, and its status is
        unchanged."""
        expense = self.create_expense()
        with self.assertRaises(ValidationError):
            self.store.reimburse_expense(self.book_id, expense["id"], MEMBER)
        after = self.store.get_expense(self.book_id, expense["id"], MEMBER)
        self.assertEqual(after["status"], "draft")

    def test_reimburse_from_pending_is_a_validation_error(self):
        """Core 6: Expenses. A pending (submitted, not yet approved)
        expense cannot be reimbursed either."""
        expense = self.pending_expense()
        with self.assertRaises(ValidationError):
            self.store.reimburse_expense(self.book_id, expense["id"], MEMBER)
        after = self.store.get_expense(self.book_id, expense["id"], MEMBER)
        self.assertEqual(after["status"], "pending")

    def test_double_reimburse_is_a_validation_error(self):
        """Core 6: Expenses. Reimbursing an already-reimbursed expense
        is not a valid transition."""
        expense = self.approved_expense()
        self.store.reimburse_expense(self.book_id, expense["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.store.reimburse_expense(self.book_id, expense["id"], MEMBER)


if __name__ == "__main__":
    unittest.main()
