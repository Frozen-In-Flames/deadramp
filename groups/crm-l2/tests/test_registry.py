"""Account & contact registry tests.

Traces to: Core 1 (Account & contact registry, opaque references)
and the privacy discipline -- records keyed by opaque
caller-supplied references only.
"""

import unittest

import crm_helpers as H
from crm.errors import NotFoundError, PermissionDenied, ValidationError


class TestAccounts(unittest.TestCase):
    """Core 1: accounts (acct-)."""

    def setUp(self):
        self.store = H.fresh_store()

    def test_create_shape(self):
        """Core 1: account shape/provenance/defaults."""
        acct = self.store.create_account(H.ADMIN, "ACCT-1")
        self.assertEqual(acct["id"], "acct-1")
        self.assertEqual(acct["reference"], "ACCT-1")
        self.assertIsNone(acct["label"])
        self.assertEqual(acct["attributes"], {})
        self.assertEqual(acct["created_by"], "alice")
        self.assertIn("created_utc", acct)

    def test_reference_required(self):
        """Core 1 (SI-10): empty/missing reference -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_account(H.ADMIN, "")
        with self.assertRaises(ValidationError):
            self.store.create_account(H.ADMIN, None)
        with self.assertRaises(ValidationError):
            self.store.create_account(H.ADMIN, "   ")

    def test_duplicate_reference_rejected(self):
        """Core 1: account references are unique keys."""
        self.store.create_account(H.ADMIN, "ACCT-1")
        with self.assertRaises(ValidationError):
            self.store.create_account(H.ADMIN, "ACCT-1")

    def test_failed_create_consumes_no_id(self):
        """Core 1 (SI-10): failed operations consume no ids."""
        with self.assertRaises(ValidationError):
            self.store.create_account(H.ADMIN, "")
        acct = self.store.create_account(H.ADMIN, "ACCT-1")
        self.assertEqual(acct["id"], "acct-1")

    def test_get_and_list(self):
        """Core 1: get/list round-trip, sorted by id."""
        self.store.create_account(H.ADMIN, "ACCT-2")
        self.store.create_account(H.ADMIN, "ACCT-1")
        self.assertEqual(self.store.get_account("acct-1", H.VIEWER)["reference"], "ACCT-2")
        refs = [a["reference"] for a in self.store.list_accounts(H.VIEWER)]
        self.assertEqual(refs, ["ACCT-2", "ACCT-1"])

    def test_get_unknown(self):
        """Core 1: unknown id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_account("acct-99", H.ADMIN)

    def test_viewer_write_denied(self):
        """Core 1/10 (AC-3): viewer may not write the registry."""
        with self.assertRaises(PermissionDenied):
            self.store.create_account(H.VIEWER, "ACCT-1")

    def test_copies_are_copies(self):
        """Core 1: returned records are copies; mutating one does not
        corrupt the store."""
        acct = self.store.create_account(H.ADMIN, "ACCT-1", attributes={"a": 1})
        acct["attributes"]["a"] = 999
        self.assertEqual(self.store.get_account("acct-1", H.ADMIN)["attributes"]["a"], 1)


class TestContacts(unittest.TestCase):
    """Core 1: contacts (ct-) under accounts."""

    def setUp(self):
        self.store, self.account, self.contact = H.make_store()

    def test_create_shape(self):
        """Core 1: contact shape carries its account link + opaque ref."""
        self.assertEqual(self.contact["id"], "ct-1")
        self.assertEqual(self.contact["account_id"], self.account["id"])
        self.assertEqual(self.contact["reference"], "PERSON-200")

    def test_unknown_account(self):
        """Core 1: contact under an unknown account -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.create_contact(H.OPERATOR, "acct-99", "PERSON-1")

    def test_duplicate_reference_rejected(self):
        """Core 1: contact references are unique keys."""
        with self.assertRaises(ValidationError):
            self.store.create_contact(H.OPERATOR, self.account["id"], "PERSON-200")

    def test_list_filter_by_account(self):
        """Core 1: list_contacts filters by account; unknown account
        -> NotFoundError."""
        other = self.store.create_account(H.ADMIN, "ACCT-2")
        self.store.create_contact(H.OPERATOR, other["id"], "PERSON-201")
        mine = self.store.list_contacts(H.VIEWER, account_id=self.account["id"])
        self.assertEqual([c["reference"] for c in mine], ["PERSON-200"])
        with self.assertRaises(NotFoundError):
            self.store.list_contacts(H.VIEWER, account_id="acct-99")


if __name__ == "__main__":
    unittest.main()
