"""Journal and ledger-posting tests.

Traces to: UNION-SPEC Core function 3 (Double-entry journal & ledger
posting — every entry must balance in exact integer cents or it is
rejected whole; only posted entries touch balances) and Core function
10 (Workflow & approvals — draft -> pending -> posted, rejection, void,
separation of duties); Implementation contract for
``accounting/store.py`` entry methods; control families SI-10 (input
validation, integer cents) and AC-5 (separation of duties).
"""

import unittest
from datetime import datetime

from accounting_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    VIEWER,
    balanced_lines,
    make_chart,
    make_store,
    post_entry,
)
from accounting.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)

ENTRY_KEYS = {
    "id", "book_id", "date", "period", "memo", "lines", "total_cents",
    "status", "created_by", "created_utc", "submitted_by", "approved_by",
    "posted_utc",
}
INVEST_DATE = "2026-01-05"


class LedgerBase(unittest.TestCase):
    """A canonical book with the five-account chart."""

    def setUp(self):
        self.store, self.book_id = make_store()
        self.chart = make_chart(self.store, self.book_id)
        self.cash = self.chart["cash"]["id"]
        self.equity = self.chart["equity"]["id"]
        self.revenue = self.chart["revenue"]["id"]
        self.rent = self.chart["rent"]["id"]

    def invest_lines(self, amount=100000):
        return balanced_lines(self.cash, self.equity, amount)

    def create_investment(self, amount=100000, date=INVEST_DATE,
                          memo="Owner investment", actor=MEMBER):
        return self.store.create_entry(
            self.book_id, date, memo, self.invest_lines(amount), actor
        )

    def pending_investment(self, amount=100000):
        entry = self.create_investment(amount=amount)
        self.store.submit_entry(self.book_id, entry["id"], MEMBER)
        return entry


class TestCreateEntry(LedgerBase):
    """Core 3: Double-entry journal — creation shape and validation."""

    def test_create_returns_the_contract_dict(self):
        """Core 3: Double-entry journal. Contract: create_entry returns
        {id, book_id, date, period, memo, lines, total_cents, status,
        created_by, created_utc, submitted_by, approved_by,
        posted_utc}."""
        entry = self.create_investment()
        self.assertEqual(set(entry.keys()), ENTRY_KEYS)
        self.assertEqual(entry["id"], "je-1")
        self.assertEqual(entry["book_id"], self.book_id)
        self.assertEqual(entry["date"], INVEST_DATE)
        self.assertEqual(entry["memo"], "Owner investment")
        self.assertEqual(entry["created_by"], "bob")

    def test_period_is_derived_from_the_date(self):
        """Core 3: Double-entry journal. Contract: period is date[:7]
        (the YYYY-MM fiscal period of the entry date)."""
        entry = self.create_investment(date="2026-03-17")
        self.assertEqual(entry["period"], "2026-03")

    def test_total_cents_is_the_balanced_total(self):
        """Core 3: Double-entry journal. Contract: total_cents is the
        entry total (total debits == total credits)."""
        entry = self.create_investment(amount=123456)
        self.assertEqual(entry["total_cents"], 123456)

    def test_initial_status_is_draft_with_empty_provenance(self):
        """Core 3 / Core 10: Workflow. Contract: initial status draft;
        submitted_by/approved_by/posted_utc start as None."""
        entry = self.create_investment()
        self.assertEqual(entry["status"], "draft")
        self.assertIsNone(entry["submitted_by"])
        self.assertIsNone(entry["approved_by"])
        self.assertIsNone(entry["posted_utc"])

    def test_lines_are_normalized_to_carry_both_sides(self):
        """Core 3: Double-entry journal. Contract: 'Stored lines are
        normalized to always carry both debit_cents and credit_cents'
        (a missing side counts as 0 on input)."""
        entry = self.create_investment()
        self.assertEqual(len(entry["lines"]), 2)
        for line in entry["lines"]:
            self.assertEqual(
                set(line.keys()),
                {"account_id", "debit_cents", "credit_cents"},
            )
        by_account = {ln["account_id"]: ln for ln in entry["lines"]}
        self.assertEqual(by_account[self.cash]["debit_cents"], 100000)
        self.assertEqual(by_account[self.cash]["credit_cents"], 0)
        self.assertEqual(by_account[self.equity]["debit_cents"], 0)
        self.assertEqual(by_account[self.equity]["credit_cents"], 100000)

    def test_unbalanced_entry_is_rejected_and_stores_nothing(self):
        """Core 3: Double-entry journal (SI-10). Contract: 'total
        debits must equal total credits ... an unbalanced entry raises
        ValidationError and stores nothing', and consumes no id."""
        lines = [
            {"account_id": self.cash, "debit_cents": 10000},
            {"account_id": self.equity, "credit_cents": 9999},
        ]
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, INVEST_DATE, "Off by one", lines, MEMBER
            )
        self.assertEqual(self.store.list_entries(self.book_id, MEMBER), [])
        entry = self.create_investment()
        self.assertEqual(entry["id"], "je-1")

    def test_one_line_entry_is_a_validation_error(self):
        """Core 3: Double-entry journal. Contract: lines is a list of
        at least two dicts."""
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, INVEST_DATE, "One side only",
                [{"account_id": self.cash, "debit_cents": 1000}], MEMBER,
            )
        self.assertEqual(self.store.list_entries(self.book_id, MEMBER), [])

    def test_empty_lines_is_a_validation_error(self):
        """Core 3: Double-entry journal. Contract: at least two lines
        are required, so an empty list is rejected."""
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, INVEST_DATE, "Empty", [], MEMBER
            )

    def test_line_with_both_sides_positive_is_a_validation_error(self):
        """Core 3: Double-entry journal. Contract: 'each line must have
        exactly one side positive and the other zero' — even when the
        entry as a whole would balance."""
        lines = [
            {"account_id": self.cash, "debit_cents": 5000,
             "credit_cents": 5000},
            {"account_id": self.equity, "credit_cents": 5000},
            {"account_id": self.revenue, "debit_cents": 5000},
        ]
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, INVEST_DATE, "Both sides", lines, MEMBER
            )
        self.assertEqual(self.store.list_entries(self.book_id, MEMBER), [])

    def test_zero_total_entry_is_a_validation_error(self):
        """Core 3: Double-entry journal. Contract: the balanced total
        'must be positive' — an all-zero entry is rejected."""
        lines = [
            {"account_id": self.cash, "debit_cents": 0},
            {"account_id": self.equity, "credit_cents": 0},
        ]
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, INVEST_DATE, "Zero", lines, MEMBER
            )
        self.assertEqual(self.store.list_entries(self.book_id, MEMBER), [])

    def test_float_amounts_are_validation_errors(self):
        """Core 3: Double-entry journal (SI-10, integer-cents rule).
        Contract: floats are rejected even when integral — no binary
        floating-point value may enter a total."""
        for bad_amount in (10.5, 10.0):
            with self.subTest(amount=bad_amount):
                lines = [
                    {"account_id": self.cash, "debit_cents": bad_amount},
                    {"account_id": self.equity, "credit_cents": bad_amount},
                ]
                with self.assertRaises(ValidationError):
                    self.store.create_entry(
                        self.book_id, INVEST_DATE, "Float", lines, MEMBER
                    )
        self.assertEqual(self.store.list_entries(self.book_id, MEMBER), [])

    def test_bool_amount_is_a_validation_error(self):
        """Core 3: Double-entry journal (SI-10, integer-cents rule).
        Contract: amounts must be int — booleans are rejected even
        though bool subclasses int in Python."""
        lines = [
            {"account_id": self.cash, "debit_cents": True},
            {"account_id": self.equity, "credit_cents": True},
        ]
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, INVEST_DATE, "Bool", lines, MEMBER
            )
        self.assertEqual(self.store.list_entries(self.book_id, MEMBER), [])

    def test_unknown_account_in_a_line_is_a_validation_error(self):
        """Core 3: Double-entry journal. Contract: 'every account_id
        must name an account in this book (else ValidationError)'."""
        lines = [
            {"account_id": self.cash, "debit_cents": 1000},
            {"account_id": "acct-999999", "credit_cents": 1000},
        ]
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, INVEST_DATE, "Ghost account", lines, MEMBER
            )
        self.assertEqual(self.store.list_entries(self.book_id, MEMBER), [])

    def test_account_from_another_book_in_a_line_is_a_validation_error(self):
        """Core 3: Double-entry journal. An account that exists but
        belongs to another book does not name an account in *this*
        book -> ValidationError."""
        other_store_book = self.store.create_book("other-books", MEMBER)
        other_chart = make_chart(self.store, other_store_book["id"])
        lines = [
            {"account_id": self.cash, "debit_cents": 1000},
            {"account_id": other_chart["equity"]["id"],
             "credit_cents": 1000},
        ]
        with self.assertRaises(ValidationError):
            self.store.create_entry(
                self.book_id, INVEST_DATE, "Cross-book", lines, MEMBER
            )

    def test_invalid_date_is_a_validation_error(self):
        """Core 3: Double-entry journal. Contract: date must be a
        valid ISO calendar date."""
        for bad in ("2026-13-05", "2026-02-30", "not-a-date", "2026/01/05"):
            with self.subTest(date=bad):
                with self.assertRaises(ValidationError):
                    self.create_investment(date=bad)

    def test_get_entry_roundtrip_and_unknown_id(self):
        """Core 3: Double-entry journal. get_entry returns the entry
        dict; an unknown id -> NotFoundError."""
        entry = self.create_investment()
        got = self.store.get_entry(self.book_id, entry["id"], VIEWER)
        self.assertEqual(got["id"], entry["id"])
        self.assertEqual(got["total_cents"], 100000)
        with self.assertRaises(NotFoundError):
            self.store.get_entry(self.book_id, "je-999999", MEMBER)

    def test_list_entries_creation_order_and_status_filter(self):
        """Core 3: Double-entry journal. Contract: list_entries is in
        creation order and accepts a status filter; an unknown status
        filter -> ValidationError."""
        first = self.create_investment()
        second = self.pending_investment(amount=5000)
        all_entries = self.store.list_entries(self.book_id, MEMBER)
        self.assertEqual(
            [e["id"] for e in all_entries], [first["id"], second["id"]]
        )
        drafts = self.store.list_entries(
            self.book_id, MEMBER, status="draft"
        )
        self.assertEqual([e["id"] for e in drafts], [first["id"]])
        pending = self.store.list_entries(
            self.book_id, MEMBER, status="pending"
        )
        self.assertEqual([e["id"] for e in pending], [second["id"]])
        with self.assertRaises(ValidationError):
            self.store.list_entries(self.book_id, MEMBER, status="bogus")

    def test_draft_entry_is_not_counted_in_balances(self):
        """Core 3: Double-entry journal. Contract: 'only posted entries
        touch the ledger, the balances, and the reports' — a draft
        moves no balance and no trial-balance total."""
        self.create_investment()
        balance = self.store.account_balance(
            self.book_id, self.cash, MEMBER
        )
        self.assertEqual(balance["debit_cents"], 0)
        self.assertEqual(balance["credit_cents"], 0)
        self.assertEqual(balance["balance_cents"], 0)
        trial = self.store.trial_balance(self.book_id, MEMBER)
        self.assertEqual(trial["total_debits_cents"], 0)
        self.assertEqual(trial["total_credits_cents"], 0)
        self.assertEqual(trial["accounts"], [])


class TestEntryStateMachine(LedgerBase):
    """Core 10: Workflow & approvals — the entry state machine."""

    def test_submit_from_draft_moves_to_pending(self):
        """Core 10: Workflow. Contract: submit_entry moves draft ->
        pending and sets submitted_by."""
        entry = self.create_investment()
        submitted = self.store.submit_entry(
            self.book_id, entry["id"], MEMBER
        )
        self.assertEqual(submitted["status"], "pending")
        self.assertEqual(submitted["submitted_by"], "bob")

    def test_submit_from_rejected_moves_back_to_pending(self):
        """Core 10: Workflow. Contract: submit_entry also accepts
        status rejected -> pending (a rejected entry can be
        resubmitted)."""
        entry = self.pending_investment()
        self.store.reject_entry(self.book_id, entry["id"], ADMIN)
        resubmitted = self.store.submit_entry(
            self.book_id, entry["id"], MEMBER
        )
        self.assertEqual(resubmitted["status"], "pending")
        self.assertEqual(resubmitted["submitted_by"], "bob")

    def test_approve_by_creator_is_denied_separation_of_duties(self):
        """Core 10: Workflow (AC-5). Contract: approve_entry requires
        'the actor's name must differ from created_by (else
        PermissionDenied — separation of duties)'; the entry stays
        pending."""
        entry = self.pending_investment()
        with self.assertRaises(PermissionDenied):
            self.store.approve_entry(self.book_id, entry["id"], MEMBER)
        after = self.store.get_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(after["status"], "pending")
        self.assertIsNone(after["approved_by"])
        self.assertIsNone(after["posted_utc"])

    def test_reject_by_creator_is_denied_separation_of_duties(self):
        """Core 10: Workflow (AC-5). Contract: reject_entry carries the
        same SoD rule as approval; the entry stays pending."""
        entry = self.pending_investment()
        with self.assertRaises(PermissionDenied):
            self.store.reject_entry(self.book_id, entry["id"], MEMBER)
        after = self.store.get_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(after["status"], "pending")

    def test_approve_posts_and_sets_provenance(self):
        """Core 10 / Core 3: Workflow + ledger posting. Contract:
        approve_entry moves pending -> posted and 'sets approved_by
        and posted_utc'."""
        entry = self.pending_investment()
        posted = self.store.approve_entry(self.book_id, entry["id"], ADMIN)
        self.assertEqual(posted["status"], "posted")
        self.assertEqual(posted["approved_by"], "alice")
        self.assertIsNotNone(posted["posted_utc"])
        parsed = datetime.fromisoformat(
            str(posted["posted_utc"]).replace("Z", "+00:00")
        )
        self.assertIsNotNone(parsed)
        balance = self.store.account_balance(
            self.book_id, self.cash, MEMBER
        )
        self.assertEqual(balance["balance_cents"], 100000)

    def test_approve_by_another_book_member_posts(self):
        """Core 10: Workflow (AC-5). Any actor other than the creator
        may approve — including another book member (dave, added by the
        owner), not only the platform admin."""
        self.store.add_member(self.book_id, OUTSIDER.name, MEMBER)
        entry = self.pending_investment()
        posted = self.store.approve_entry(
            self.book_id, entry["id"], OUTSIDER
        )
        self.assertEqual(posted["status"], "posted")
        self.assertEqual(posted["approved_by"], "dave")

    def test_double_approve_is_a_validation_error(self):
        """Core 10: Workflow. Approving an already-posted entry is not
        a valid transition (approve requires status pending) ->
        ValidationError, and the entry stays posted."""
        entry = post_entry(
            self.store, self.book_id, INVEST_DATE, "Owner investment",
            self.invest_lines(),
        )
        with self.assertRaises(ValidationError):
            self.store.approve_entry(self.book_id, entry["id"], ADMIN)
        after = self.store.get_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(after["status"], "posted")

    def test_approve_a_draft_is_a_validation_error(self):
        """Core 10: Workflow. Approve requires status pending; a draft
        cannot skip submission."""
        entry = self.create_investment()
        with self.assertRaises(ValidationError):
            self.store.approve_entry(self.book_id, entry["id"], ADMIN)
        after = self.store.get_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(after["status"], "draft")

    def test_reject_moves_pending_to_rejected(self):
        """Core 10: Workflow. Contract: reject_entry moves pending ->
        rejected."""
        entry = self.pending_investment()
        rejected = self.store.reject_entry(self.book_id, entry["id"], ADMIN)
        self.assertEqual(rejected["status"], "rejected")

    def test_void_from_draft_by_creator(self):
        """Core 10: Workflow. Contract: void_entry accepts status draft
        and is available to the creator."""
        entry = self.create_investment()
        voided = self.store.void_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(voided["status"], "void")

    def test_void_from_rejected_by_creator(self):
        """Core 10: Workflow. Contract: void_entry also accepts status
        rejected ('rejected returning the object to an
        editable-by-void state')."""
        entry = self.pending_investment()
        self.store.reject_entry(self.book_id, entry["id"], ADMIN)
        voided = self.store.void_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(voided["status"], "void")

    def test_void_of_pending_is_a_validation_error(self):
        """Core 10: Workflow. Contract: void is available from
        draft/rejected only — a pending entry cannot be voided."""
        entry = self.pending_investment()
        with self.assertRaises(ValidationError):
            self.store.void_entry(self.book_id, entry["id"], MEMBER)
        after = self.store.get_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(after["status"], "pending")

    def test_void_of_posted_is_a_validation_error(self):
        """Core 3 / Core 10: Journal + workflow. Contract: 'A posted
        entry is never edited or voided — the standard correction is a
        reversing entry.'"""
        entry = post_entry(
            self.store, self.book_id, INVEST_DATE, "Owner investment",
            self.invest_lines(),
        )
        with self.assertRaises(ValidationError):
            self.store.void_entry(self.book_id, entry["id"], MEMBER)
        after = self.store.get_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(after["status"], "posted")

    def test_void_by_unrelated_member_is_denied(self):
        """Core 10: Workflow (AC-3/AC-5). Contract: void is available
        'only to the creator, the book owner, or a platform admin' —
        another book member (dave) is denied and the entry is
        unchanged."""
        self.store.add_member(self.book_id, OUTSIDER.name, MEMBER)
        entry = self.create_investment()
        with self.assertRaises(PermissionDenied):
            self.store.void_entry(self.book_id, entry["id"], OUTSIDER)
        after = self.store.get_entry(self.book_id, entry["id"], MEMBER)
        self.assertEqual(after["status"], "draft")

    def test_void_by_book_owner_and_platform_admin(self):
        """Core 10: Workflow. The book owner may void another member's
        draft, and the platform admin may void a draft."""
        self.store.add_member(self.book_id, OUTSIDER.name, MEMBER)
        by_outsider = self.store.create_entry(
            self.book_id, INVEST_DATE, "Dave draft",
            self.invest_lines(1000), OUTSIDER,
        )
        voided = self.store.void_entry(
            self.book_id, by_outsider["id"], MEMBER  # MEMBER is the owner
        )
        self.assertEqual(voided["status"], "void")
        own = self.create_investment()
        voided = self.store.void_entry(self.book_id, own["id"], ADMIN)
        self.assertEqual(voided["status"], "void")

    def test_submit_a_posted_entry_is_a_validation_error(self):
        """Core 10: Workflow. Submit requires draft/rejected; a posted
        entry cannot be resubmitted."""
        entry = post_entry(
            self.store, self.book_id, INVEST_DATE, "Owner investment",
            self.invest_lines(),
        )
        with self.assertRaises(ValidationError):
            self.store.submit_entry(self.book_id, entry["id"], MEMBER)


if __name__ == "__main__":
    unittest.main()
