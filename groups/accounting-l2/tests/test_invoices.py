"""Invoicing and payment tests.

Traces to: UNION-SPEC Core function 4 (Invoicing & billing — line
amounts and the invoice total are computed by the build, never trusted
from the caller), Core function 5 (Payments — partial payments allowed,
overpayment rejected, an invoice whose payments reach its total becomes
paid) and Core function 10 (Workflow & approvals — the shared approval
machine, becoming issued on approval); Implementation contract for
``accounting/store.py`` invoice and payment methods; control families
SI-10 (integer cents) and AC-5 (separation of duties).
"""

import unittest

from accounting_helpers import ADMIN, MEMBER, make_store
from accounting.errors import NotFoundError, PermissionDenied, ValidationError

INVOICE_KEYS = {
    "id", "book_id", "customer", "date", "due_date", "lines",
    "total_cents", "paid_cents", "status", "created_by", "created_utc",
    "submitted_by", "approved_by", "issued_utc",
}
PAYMENT_KEYS = {
    "id", "book_id", "invoice_id", "amount_cents", "date", "method",
    "created_by", "created_utc",
}
DATE = "2026-01-05"
DUE = "2026-02-04"


def sample_lines():
    """Two lines totalling 35000 cents (2 x 15000 + 1 x 5000)."""
    return [
        {"description": "Consulting", "quantity": 2,
         "unit_price_cents": 15000},
        {"description": "Support", "quantity": 1,
         "unit_price_cents": 5000},
    ]


class InvoiceBase(unittest.TestCase):
    """A canonical book (invoices need no chart accounts)."""

    def setUp(self):
        self.store, self.book_id = make_store()

    def create_invoice(self, lines=None, customer="Customer Co",
                       date=DATE, due_date=DUE, actor=MEMBER):
        return self.store.create_invoice(
            self.book_id, customer, date, due_date,
            sample_lines() if lines is None else lines, actor,
        )

    def issued_invoice(self, lines=None):
        invoice = self.create_invoice(lines=lines)
        self.store.submit_invoice(self.book_id, invoice["id"], MEMBER)
        return self.store.approve_invoice(
            self.book_id, invoice["id"], ADMIN
        )


class TestCreateInvoice(InvoiceBase):
    """Core 4: Invoicing — creation shape and computed totals."""

    def test_create_returns_the_contract_dict(self):
        """Core 4: Invoicing. Contract: create_invoice returns {id,
        book_id, customer, date, due_date, lines, total_cents,
        paid_cents, status, created_by, created_utc, submitted_by,
        approved_by, issued_utc}."""
        invoice = self.create_invoice()
        self.assertEqual(set(invoice.keys()), INVOICE_KEYS)
        self.assertEqual(invoice["id"], "inv-1")
        self.assertEqual(invoice["book_id"], self.book_id)
        self.assertEqual(invoice["customer"], "Customer Co")
        self.assertEqual(invoice["date"], DATE)
        self.assertEqual(invoice["due_date"], DUE)
        self.assertEqual(invoice["created_by"], "bob")

    def test_line_amounts_and_total_are_computed(self):
        """Core 4: Invoicing. Contract: 'each stored line gains
        amount_cents = quantity * unit_price_cents, computed here;
        total_cents is the sum of line amounts'."""
        invoice = self.create_invoice()
        amounts = [ln["amount_cents"] for ln in invoice["lines"]]
        self.assertEqual(amounts, [30000, 5000])
        self.assertEqual(invoice["total_cents"], 35000)
        for line in invoice["lines"]:
            self.assertEqual(
                set(line.keys()),
                {"description", "quantity", "unit_price_cents",
                 "amount_cents"},
            )
            self.assertEqual(
                line["amount_cents"],
                line["quantity"] * line["unit_price_cents"],
            )

    def test_computed_amounts_are_exact_for_large_cents_values(self):
        """Core 4: Invoicing (SI-10, integer cents). Line amounts use
        exact integer arithmetic: 97 x 999999999 cents is computed
        exactly, with no floating-point rounding."""
        lines = [{"description": "Big engagement", "quantity": 97,
                  "unit_price_cents": 999999999}]
        invoice = self.create_invoice(lines=lines)
        self.assertEqual(invoice["lines"][0]["amount_cents"], 96999999903)
        self.assertEqual(invoice["total_cents"], 96999999903)
        self.assertIsInstance(invoice["total_cents"], int)

    def test_initial_status_is_draft_and_paid_cents_zero(self):
        """Core 4 / Core 10: Invoicing + workflow. Contract: paid_cents
        starts 0; status draft; approval provenance starts empty."""
        invoice = self.create_invoice()
        self.assertEqual(invoice["status"], "draft")
        self.assertEqual(invoice["paid_cents"], 0)
        self.assertIsNone(invoice["submitted_by"])
        self.assertIsNone(invoice["approved_by"])
        self.assertIsNone(invoice["issued_utc"])

    def test_zero_quantity_is_a_validation_error(self):
        """Core 4: Invoicing. Contract: quantity must be an int >= 1."""
        lines = [{"description": "Nothing", "quantity": 0,
                  "unit_price_cents": 1000}]
        with self.assertRaises(ValidationError):
            self.create_invoice(lines=lines)
        self.assertEqual(self.store.list_invoices(self.book_id, MEMBER), [])

    def test_negative_quantity_is_a_validation_error(self):
        """Core 4: Invoicing. Contract: quantity >= 1, so a negative
        quantity is rejected."""
        lines = [{"description": "Negative", "quantity": -2,
                  "unit_price_cents": 1000}]
        with self.assertRaises(ValidationError):
            self.create_invoice(lines=lines)

    def test_negative_unit_price_is_a_validation_error(self):
        """Core 4: Invoicing. Contract: unit_price_cents must be an
        int >= 0."""
        lines = [{"description": "Bad price", "quantity": 1,
                  "unit_price_cents": -1}]
        with self.assertRaises(ValidationError):
            self.create_invoice(lines=lines)
        self.assertEqual(self.store.list_invoices(self.book_id, MEMBER), [])

    def test_due_date_before_date_is_a_validation_error(self):
        """Core 4: Invoicing. Contract: 'due_date not before date'."""
        with self.assertRaises(ValidationError):
            self.create_invoice(date="2026-02-04", due_date="2026-01-05")
        self.assertEqual(self.store.list_invoices(self.book_id, MEMBER), [])

    def test_due_date_equal_to_date_is_accepted(self):
        """Core 4: Invoicing. 'Not before' permits a due date equal to
        the invoice date."""
        invoice = self.create_invoice(date=DATE, due_date=DATE)
        self.assertEqual(invoice["due_date"], DATE)

    def test_empty_lines_is_a_validation_error(self):
        """Core 4: Invoicing. Contract: lines is a list of at least one
        dict."""
        with self.assertRaises(ValidationError):
            self.create_invoice(lines=[])
        self.assertEqual(self.store.list_invoices(self.book_id, MEMBER), [])

    def test_zero_total_is_a_validation_error(self):
        """Core 4: Invoicing. Contract: 'total_cents ... must be
        positive' — an all-free invoice is rejected."""
        lines = [{"description": "Free", "quantity": 3,
                  "unit_price_cents": 0}]
        with self.assertRaises(ValidationError):
            self.create_invoice(lines=lines)

    def test_empty_customer_is_a_validation_error(self):
        """Core 4: Invoicing. Contract: customer is a non-empty
        string."""
        with self.assertRaises(ValidationError):
            self.create_invoice(customer="")

    def test_failed_create_consumes_no_id(self):
        """Core 4: Invoicing (SI-10). A failed creation stores nothing
        and consumes no id."""
        with self.assertRaises(ValidationError):
            self.create_invoice(lines=[])
        invoice = self.create_invoice()
        self.assertEqual(invoice["id"], "inv-1")

    def test_get_and_list_invoices(self):
        """Core 4: Invoicing. get_invoice returns the invoice dict and
        list_invoices is in creation order with a status filter; an
        unknown id -> NotFoundError."""
        first = self.create_invoice()
        second = self.issued_invoice()
        got = self.store.get_invoice(self.book_id, first["id"], MEMBER)
        self.assertEqual(got["id"], first["id"])
        listed = self.store.list_invoices(self.book_id, MEMBER)
        self.assertEqual(
            [i["id"] for i in listed], [first["id"], second["id"]]
        )
        issued = self.store.list_invoices(
            self.book_id, MEMBER, status="issued"
        )
        self.assertEqual([i["id"] for i in issued], [second["id"]])
        with self.assertRaises(NotFoundError):
            self.store.get_invoice(self.book_id, "inv-999999", MEMBER)


class TestInvoiceStateMachine(InvoiceBase):
    """Core 10: Workflow — the invoice machine to issued, and void."""

    def test_machine_runs_draft_to_issued(self):
        """Core 10 / Core 4: Workflow + invoicing. Contract: submit
        moves draft -> pending (sets submitted_by); approve moves
        pending -> issued and 'sets approved_by, issued_utc'."""
        invoice = self.create_invoice()
        submitted = self.store.submit_invoice(
            self.book_id, invoice["id"], MEMBER
        )
        self.assertEqual(submitted["status"], "pending")
        self.assertEqual(submitted["submitted_by"], "bob")
        issued = self.store.approve_invoice(
            self.book_id, invoice["id"], ADMIN
        )
        self.assertEqual(issued["status"], "issued")
        self.assertEqual(issued["approved_by"], "alice")
        self.assertIsNotNone(issued["issued_utc"])

    def test_approve_by_creator_is_denied_separation_of_duties(self):
        """Core 10: Workflow (AC-5). The shared machine's SoD rule
        applies to invoices: the creator cannot approve their own
        invoice; it stays pending."""
        invoice = self.create_invoice()
        self.store.submit_invoice(self.book_id, invoice["id"], MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.approve_invoice(self.book_id, invoice["id"], MEMBER)
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["status"], "pending")

    def test_reject_then_void(self):
        """Core 10: Workflow. Reject moves pending -> rejected, and
        void is available from rejected to the creator."""
        invoice = self.create_invoice()
        self.store.submit_invoice(self.book_id, invoice["id"], MEMBER)
        rejected = self.store.reject_invoice(
            self.book_id, invoice["id"], ADMIN
        )
        self.assertEqual(rejected["status"], "rejected")
        voided = self.store.void_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(voided["status"], "void")

    def test_void_issued_unpaid_invoice_is_accepted(self):
        """Core 10 / Core 4: Workflow + invoicing. Contract:
        'void_invoice additionally accepts status issued when
        paid_cents is 0.'"""
        invoice = self.issued_invoice()
        voided = self.store.void_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(voided["status"], "void")


class TestPayments(InvoiceBase):
    """Core 5: Payments — application to an issued invoice's balance."""

    def test_payment_returns_the_contract_dict(self):
        """Core 5: Payments. Contract: record_payment returns {id,
        book_id, invoice_id, amount_cents, date, method, created_by,
        created_utc} with the pay- id prefix."""
        invoice = self.issued_invoice()
        payment = self.store.record_payment(
            self.book_id, invoice["id"], 10000, "2026-01-20", MEMBER,
            method="wire",
        )
        self.assertEqual(set(payment.keys()), PAYMENT_KEYS)
        self.assertEqual(payment["id"], "pay-1")
        self.assertEqual(payment["book_id"], self.book_id)
        self.assertEqual(payment["invoice_id"], invoice["id"])
        self.assertEqual(payment["amount_cents"], 10000)
        self.assertEqual(payment["date"], "2026-01-20")
        self.assertEqual(payment["method"], "wire")
        self.assertEqual(payment["created_by"], "bob")

    def test_partial_payment_leaves_invoice_issued(self):
        """Core 5: Payments. Contract: 'partial payments are allowed'
        — a payment below the total updates paid_cents and leaves the
        invoice issued."""
        invoice = self.issued_invoice()
        self.store.record_payment(
            self.book_id, invoice["id"], 10000, "2026-01-20", MEMBER
        )
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["paid_cents"], 10000)
        self.assertEqual(after["status"], "issued")

    def test_payment_completing_the_total_marks_invoice_paid(self):
        """Core 5: Payments. Contract: 'an invoice whose payments
        reach its total becomes paid' — across partial payments, the
        completing payment flips the status."""
        invoice = self.issued_invoice()
        self.store.record_payment(
            self.book_id, invoice["id"], 10000, "2026-01-20", MEMBER
        )
        self.store.record_payment(
            self.book_id, invoice["id"], 25000, "2026-01-25", MEMBER
        )
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["paid_cents"], 35000)
        self.assertEqual(after["status"], "paid")

    def test_single_full_payment_marks_invoice_paid(self):
        """Core 5: Payments. One payment equal to the total pays the
        invoice in full."""
        invoice = self.issued_invoice()
        self.store.record_payment(
            self.book_id, invoice["id"], 35000, "2026-01-20", MEMBER
        )
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["status"], "paid")

    def test_overpayment_is_rejected_and_paid_cents_unchanged(self):
        """Core 5: Payments (SI-10). Contract: amount must not exceed
        'total_cents - paid_cents (else ValidationError)' — checked
        both from zero and after a partial payment; a rejected
        overpayment changes nothing."""
        invoice = self.issued_invoice()
        with self.assertRaises(ValidationError):
            self.store.record_payment(
                self.book_id, invoice["id"], 35001, "2026-01-20", MEMBER
            )
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["paid_cents"], 0)
        self.assertEqual(after["status"], "issued")
        self.assertEqual(self.store.list_payments(self.book_id, MEMBER), [])

        self.store.record_payment(
            self.book_id, invoice["id"], 10000, "2026-01-20", MEMBER
        )
        with self.assertRaises(ValidationError):
            self.store.record_payment(
                self.book_id, invoice["id"], 25001, "2026-01-21", MEMBER
            )
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["paid_cents"], 10000)
        self.assertEqual(len(self.store.list_payments(self.book_id, MEMBER)), 1)

    def test_payment_on_a_draft_invoice_is_a_validation_error(self):
        """Core 5: Payments. Contract: 'The invoice must be in this
        book and in status issued (else ValidationError)' — a draft
        cannot be paid."""
        invoice = self.create_invoice()
        with self.assertRaises(ValidationError):
            self.store.record_payment(
                self.book_id, invoice["id"], 1000, "2026-01-20", MEMBER
            )
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["paid_cents"], 0)

    def test_payment_on_a_paid_invoice_is_a_validation_error(self):
        """Core 5: Payments. A paid invoice is no longer in status
        issued, so a further payment is rejected."""
        invoice = self.issued_invoice()
        self.store.record_payment(
            self.book_id, invoice["id"], 35000, "2026-01-20", MEMBER
        )
        with self.assertRaises(ValidationError):
            self.store.record_payment(
                self.book_id, invoice["id"], 1, "2026-01-21", MEMBER
            )

    def test_payment_float_amount_is_a_validation_error(self):
        """Core 5: Payments (SI-10, integer-cents rule). Contract:
        amount_cents must be a positive int — floats (even integral
        ones) and bools are rejected and apply nothing."""
        invoice = self.issued_invoice()
        for bad_amount in (100.5, 100.0, True):
            with self.subTest(amount=bad_amount):
                with self.assertRaises(ValidationError):
                    self.store.record_payment(
                        self.book_id, invoice["id"], bad_amount,
                        "2026-01-20", MEMBER,
                    )
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["paid_cents"], 0)
        self.assertEqual(self.store.list_payments(self.book_id, MEMBER), [])

    def test_payment_zero_or_negative_is_a_validation_error(self):
        """Core 5: Payments. Contract: amount_cents is a positive
        int."""
        invoice = self.issued_invoice()
        for bad_amount in (0, -1000):
            with self.subTest(amount=bad_amount):
                with self.assertRaises(ValidationError):
                    self.store.record_payment(
                        self.book_id, invoice["id"], bad_amount,
                        "2026-01-20", MEMBER,
                    )

    def test_void_issued_invoice_with_a_payment_is_a_validation_error(self):
        """Core 5 / Core 10: Payments + workflow. Contract: voiding an
        issued invoice is accepted only when paid_cents is 0 — with a
        payment applied it raises ValidationError and nothing changes."""
        invoice = self.issued_invoice()
        self.store.record_payment(
            self.book_id, invoice["id"], 10000, "2026-01-20", MEMBER
        )
        with self.assertRaises(ValidationError):
            self.store.void_invoice(self.book_id, invoice["id"], MEMBER)
        after = self.store.get_invoice(self.book_id, invoice["id"], MEMBER)
        self.assertEqual(after["status"], "issued")
        self.assertEqual(after["paid_cents"], 10000)

    def test_list_payments_filtered_by_invoice(self):
        """Core 5: Payments. Contract: list_payments(book, actor,
        invoice_id=None) — with an invoice filter only that invoice's
        payments come back; without one, all payments in order."""
        first = self.issued_invoice()
        second = self.issued_invoice()
        pay1 = self.store.record_payment(
            self.book_id, first["id"], 10000, "2026-01-20", MEMBER
        )
        pay2 = self.store.record_payment(
            self.book_id, second["id"], 5000, "2026-01-21", MEMBER
        )
        filtered = self.store.list_payments(
            self.book_id, MEMBER, invoice_id=first["id"]
        )
        self.assertEqual([p["id"] for p in filtered], [pay1["id"]])
        filtered2 = self.store.list_payments(
            self.book_id, MEMBER, invoice_id=second["id"]
        )
        self.assertEqual([p["id"] for p in filtered2], [pay2["id"]])
        all_payments = self.store.list_payments(self.book_id, MEMBER)
        self.assertEqual(
            [p["id"] for p in all_payments], [pay1["id"], pay2["id"]]
        )


if __name__ == "__main__":
    unittest.main()
