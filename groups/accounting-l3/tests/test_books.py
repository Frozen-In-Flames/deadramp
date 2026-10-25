"""Books and chart-of-accounts tests.

Traces to: UNION-SPEC Core function 1 (Books & members — named books
with an owner, a member list, and provenance) and Core function 2
(Chart of accounts — accounts inside a book, each with a code unique
per book, a name, and a type); Implementation contract for
``accounting/store.py`` book and account methods; control families
AC-2/AC-3 (membership is the boundary) and SI-10 (a failed operation
consumes no id and changes nothing).
"""

import unittest
from datetime import datetime

from accounting_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    VIEWER,
    fresh_store,
    make_store,
)
from accounting.errors import NotFoundError, PermissionDenied, ValidationError

BOOK_KEYS = {
    "id", "name", "owner", "members", "closed_periods",
    "created_by", "created_utc",
}
ACCOUNT_KEYS = {
    "id", "book_id", "code", "name", "type", "active",
    "created_by", "created_utc",
}
ACCOUNT_TYPES = {"asset", "liability", "equity", "revenue", "expense"}


class TestCreateBook(unittest.TestCase):
    """Core 1: Books — creation shape, provenance, id sequence."""

    def setUp(self):
        self.store = fresh_store()

    def test_create_returns_the_contract_dict(self):
        """Core 1: Books. Contract: create_book returns {id, name,
        owner, members, closed_periods, created_by, created_utc}."""
        book = self.store.create_book("acme-books", MEMBER)
        self.assertEqual(set(book.keys()), BOOK_KEYS)
        self.assertEqual(book["name"], "acme-books")
        self.assertEqual(book["created_by"], "bob")

    def test_creator_is_owner_and_first_member(self):
        """Core 1: Books. Contract: 'the creator is owner and first
        member'."""
        book = self.store.create_book("acme-books", MEMBER)
        self.assertEqual(book["owner"], "bob")
        self.assertEqual(book["members"], ["bob"])

    def test_closed_periods_starts_empty(self):
        """Core 1: Books. Contract: closed_periods starts empty."""
        book = self.store.create_book("acme-books", MEMBER)
        self.assertEqual(book["closed_periods"], [])

    def test_first_book_id_is_book_1_and_ids_are_sequential(self):
        """Core 1: Books. Contract: ids are sequential per object type
        with the book- prefix."""
        first = self.store.create_book("a", MEMBER)
        second = self.store.create_book("b", ADMIN)
        third = self.store.create_book("c", MEMBER)
        self.assertEqual(
            [first["id"], second["id"], third["id"]],
            ["book-1", "book-2", "book-3"],
        )

    def test_created_utc_is_a_parseable_timestamp(self):
        """Core 1: Books. Contract: all timestamps are UTC ISO-8601."""
        book = self.store.create_book("acme-books", MEMBER)
        parsed = datetime.fromisoformat(
            str(book["created_utc"]).replace("Z", "+00:00")
        )
        self.assertIsNotNone(parsed)

    def test_admin_and_member_may_create_but_viewer_may_not(self):
        """Core 1: Books + Core 12 Access control. create_book is in
        the admin and member permission sets and not in viewer's."""
        self.store.create_book("by-admin", ADMIN)
        self.store.create_book("by-member", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.create_book("by-viewer", VIEWER)

    def test_failed_create_consumes_no_id(self):
        """Core 1: Books (SI-10). A denied creation changes nothing:
        the next successful book is still book-1."""
        with self.assertRaises(PermissionDenied):
            self.store.create_book("denied", VIEWER)
        book = self.store.create_book("real", MEMBER)
        self.assertEqual(book["id"], "book-1")


class TestGetAndListBooks(unittest.TestCase):
    """Core 1: Books — visibility is membership (or platform admin)."""

    def setUp(self):
        self.store, self.book_id = make_store()

    def test_get_book_by_owner_and_member(self):
        """Core 1: Books. Members can get their book dict."""
        for actor in (MEMBER, VIEWER):
            with self.subTest(actor=actor.name):
                book = self.store.get_book(self.book_id, actor)
                self.assertEqual(book["id"], self.book_id)
                self.assertEqual(set(book.keys()), BOOK_KEYS)

    def test_get_book_by_platform_admin_non_member(self):
        """Core 1: Books + Core 12 Access control. Contract: the
        platform admin role reaches books without membership."""
        book = self.store.get_book(self.book_id, ADMIN)
        self.assertEqual(book["id"], self.book_id)

    def test_get_book_by_non_member_is_denied(self):
        """Core 1: Books (AC-3). A non-member cannot read a book,
        whatever their platform role."""
        with self.assertRaises(PermissionDenied):
            self.store.get_book(self.book_id, OUTSIDER)

    def test_get_unknown_book_is_not_found(self):
        """Core 1: Books. Unknown id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_book("book-999999", ADMIN)

    def test_list_books_shows_only_visible_books(self):
        """Core 1: Books. Contract: list_books returns the book dicts
        the actor may see (member of, or platform admin)."""
        other = self.store.create_book("admin-only-books", ADMIN)
        member_ids = [b["id"] for b in self.store.list_books(MEMBER)]
        self.assertEqual(member_ids, [self.book_id])
        viewer_ids = [b["id"] for b in self.store.list_books(VIEWER)]
        self.assertEqual(viewer_ids, [self.book_id])
        admin_ids = [b["id"] for b in self.store.list_books(ADMIN)]
        self.assertEqual(admin_ids, [self.book_id, other["id"]])
        self.assertEqual(self.store.list_books(OUTSIDER), [])


class TestAddMember(unittest.TestCase):
    """Core 1: Books — only the owner or a platform admin may add."""

    def setUp(self):
        self.store, self.book_id = make_store()

    def test_owner_can_add_member_and_gets_updated_book(self):
        """Core 1: Books. Contract: add_member returns the updated
        book dict; a member added by the owner can then read the book."""
        updated = self.store.add_member(self.book_id, "dave", MEMBER)
        self.assertEqual(set(updated.keys()), BOOK_KEYS)
        self.assertIn("dave", updated["members"])
        book = self.store.get_book(self.book_id, OUTSIDER)
        self.assertEqual(book["id"], self.book_id)

    def test_platform_admin_can_add_member(self):
        """Core 1: Books. Contract: a platform admin may add members
        to a book they do not own or belong to."""
        updated = self.store.add_member(self.book_id, "dave", ADMIN)
        self.assertIn("dave", updated["members"])

    def test_plain_member_cannot_add_member(self):
        """Core 1: Books (AC-3). A member who is neither owner nor
        platform admin cannot add members."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.book_id, "dave", VIEWER)

    def test_non_member_cannot_add_member(self):
        """Core 1: Books (AC-3). A non-member cannot add anyone."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.book_id, "erin", OUTSIDER)

    def test_adding_an_existing_member_is_a_validation_error(self):
        """Core 1: Books. Contract: 'adding an existing member raises
        ValidationError'."""
        with self.assertRaises(ValidationError):
            self.store.add_member(self.book_id, VIEWER.name, MEMBER)
        with self.assertRaises(ValidationError):
            self.store.add_member(self.book_id, MEMBER.name, MEMBER)

    def test_duplicate_add_changes_nothing(self):
        """Core 1: Books (SI-10). A failed duplicate add leaves the
        member list exactly as it was."""
        before = list(self.store.get_book(self.book_id, MEMBER)["members"])
        with self.assertRaises(ValidationError):
            self.store.add_member(self.book_id, VIEWER.name, MEMBER)
        after = self.store.get_book(self.book_id, MEMBER)["members"]
        self.assertEqual(after, before)


class TestAccounts(unittest.TestCase):
    """Core 2: Chart of accounts — shape, per-book codes, types."""

    def setUp(self):
        self.store, self.book_id = make_store()

    def test_create_account_returns_the_contract_dict(self):
        """Core 2: Chart of accounts. Contract: create_account returns
        {id, book_id, code, name, type, active, created_by,
        created_utc} with active True."""
        acct = self.store.create_account(
            self.book_id, "1000", "Cash", "asset", MEMBER
        )
        self.assertEqual(set(acct.keys()), ACCOUNT_KEYS)
        self.assertEqual(acct["book_id"], self.book_id)
        self.assertEqual(acct["code"], "1000")
        self.assertEqual(acct["name"], "Cash")
        self.assertEqual(acct["type"], "asset")
        self.assertIs(acct["active"], True)
        self.assertEqual(acct["created_by"], "bob")

    def test_account_ids_are_sequential_with_acct_prefix(self):
        """Core 2: Chart of accounts. Contract: ids are sequential per
        object type with the acct- prefix."""
        first = self.store.create_account(
            self.book_id, "1000", "Cash", "asset", MEMBER
        )
        second = self.store.create_account(
            self.book_id, "2000", "AccountsPayable", "liability", MEMBER
        )
        self.assertEqual([first["id"], second["id"]], ["acct-1", "acct-2"])

    def test_each_account_type_is_accepted(self):
        """Core 2: Chart of accounts. Contract: account_type must be
        one of asset, liability, equity, revenue, expense — all five
        are valid."""
        for i, account_type in enumerate(sorted(ACCOUNT_TYPES)):
            with self.subTest(account_type=account_type):
                acct = self.store.create_account(
                    self.book_id, "%d000" % (i + 1), "Acct", account_type,
                    MEMBER,
                )
                self.assertEqual(acct["type"], account_type)

    def test_duplicate_code_in_same_book_is_a_validation_error(self):
        """Core 2: Chart of accounts. Contract: code must be unique
        within the book (duplicate -> ValidationError)."""
        self.store.create_account(
            self.book_id, "1000", "Cash", "asset", MEMBER
        )
        with self.assertRaises(ValidationError):
            self.store.create_account(
                self.book_id, "1000", "Cash Again", "asset", MEMBER
            )
        accounts = self.store.list_accounts(self.book_id, MEMBER)
        self.assertEqual(len(accounts), 1)

    def test_same_code_in_a_different_book_is_ok(self):
        """Core 2: Chart of accounts. Code uniqueness is per book: the
        same code in another book is accepted."""
        self.store.create_account(
            self.book_id, "1000", "Cash", "asset", MEMBER
        )
        other = self.store.create_book("other-books", MEMBER)
        acct = self.store.create_account(
            other["id"], "1000", "Cash", "asset", MEMBER
        )
        self.assertEqual(acct["code"], "1000")
        self.assertEqual(acct["book_id"], other["id"])

    def test_bad_account_type_is_a_validation_error(self):
        """Core 2: Chart of accounts. Contract: an account_type outside
        the five named types -> ValidationError."""
        for bad in ("assets", "income", "", "Asset"):
            with self.subTest(account_type=bad):
                with self.assertRaises(ValidationError):
                    self.store.create_account(
                        self.book_id, "9000", "Nope", bad, MEMBER
                    )
        self.assertEqual(self.store.list_accounts(self.book_id, MEMBER), [])

    def test_failed_account_create_consumes_no_id(self):
        """Core 2: Chart of accounts (SI-10). A failed creation changes
        nothing: the next successful account keeps the sequence."""
        with self.assertRaises(ValidationError):
            self.store.create_account(
                self.book_id, "9000", "Nope", "bogus-type", MEMBER
            )
        acct = self.store.create_account(
            self.book_id, "1000", "Cash", "asset", MEMBER
        )
        self.assertEqual(acct["id"], "acct-1")

    def test_list_accounts_is_in_creation_order(self):
        """Core 2: Chart of accounts. Contract: list_accounts returns
        accounts in creation order."""
        for code, name, kind in (
            ("5000", "RentExpense", "expense"),
            ("1000", "Cash", "asset"),
            ("4000", "ServiceRevenue", "revenue"),
        ):
            self.store.create_account(self.book_id, code, name, kind, MEMBER)
        codes = [
            a["code"] for a in self.store.list_accounts(self.book_id, MEMBER)
        ]
        self.assertEqual(codes, ["5000", "1000", "4000"])

    def test_get_account_by_member_and_admin(self):
        """Core 2: Chart of accounts. Members and the platform admin
        can get an account dict."""
        acct = self.store.create_account(
            self.book_id, "1000", "Cash", "asset", MEMBER
        )
        for actor in (MEMBER, VIEWER, ADMIN):
            with self.subTest(actor=actor.name):
                got = self.store.get_account(self.book_id, acct["id"], actor)
                self.assertEqual(got["id"], acct["id"])

    def test_get_account_from_another_book_is_not_found(self):
        """Core 2: Chart of accounts. Contract: get_account with 'an id
        from another book -> NotFoundError'."""
        acct = self.store.create_account(
            self.book_id, "1000", "Cash", "asset", MEMBER
        )
        other = self.store.create_book("other-books", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_account(other["id"], acct["id"], MEMBER)

    def test_get_unknown_account_is_not_found(self):
        """Core 2: Chart of accounts. Unknown account id ->
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_account(self.book_id, "acct-999999", MEMBER)

    def test_non_member_cannot_list_or_get_accounts(self):
        """Core 2: Chart of accounts (AC-3). Book membership gates the
        chart too: a non-member can neither list nor get accounts."""
        acct = self.store.create_account(
            self.book_id, "1000", "Cash", "asset", MEMBER
        )
        with self.assertRaises(PermissionDenied):
            self.store.list_accounts(self.book_id, OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.get_account(self.book_id, acct["id"], OUTSIDER)


if __name__ == "__main__":
    unittest.main()
