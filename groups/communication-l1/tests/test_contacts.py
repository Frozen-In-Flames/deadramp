"""Contacts tests.

Traces to: Core function -- Directory (contacts); contract for
``CommStore.create_contact/get_contact/list_contacts``.
"""

import unittest

from comm_helpers import ADMIN, OPERATOR, VIEWER, fresh_store
from comm.errors import NotFoundError, PermissionDenied, ValidationError


class TestContacts(unittest.TestCase):
    """Core: Directory contacts."""

    def setUp(self):
        self.store = fresh_store()

    def test_create_shape_and_id(self):
        """Core: Contacts. create_contact returns {id ct-1, name, addresses, created_by, created_utc}."""
        c = self.store.create_contact("Dana", {"email": "d@x.y"}, OPERATOR)
        self.assertEqual(c["id"], "ct-1")
        self.assertEqual(c["name"], "Dana")
        self.assertEqual(c["addresses"], {"email": "d@x.y"})
        self.assertEqual(c["created_by"], "bob")
        self.assertTrue(c["created_utc"])

    def test_get_and_list_sorted_by_id(self):
        """Core: Contacts. get_contact returns the contact; list_contacts sorted by id."""
        ids = []
        for i in range(3):
            ids.append(self.store.create_contact("P%d" % i, {"sms": "123"}, OPERATOR)["id"])
        self.assertEqual(self.store.get_contact(ids[1], VIEWER)["id"], ids[1])
        self.assertEqual([c["id"] for c in self.store.list_contacts(VIEWER)], ids)

    def test_get_unknown_is_not_found(self):
        """Core: Contacts. Unknown id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_contact("ct-999", OPERATOR)

    def test_validation(self):
        """Core: Contacts (SI-10). Empty name, empty addresses, bad kind, empty address -> ValidationError."""
        for args in [("", {"email": "a@b"}), ("Dana", {}), ("Dana", {"fax": "1"}), ("Dana", {"email": ""}), ("Dana", {"email": 5}), ("Dana", "notdict")]:
            with self.subTest(args=args):
                with self.assertRaises(ValidationError):
                    self.store.create_contact(args[0], args[1], OPERATOR)

    def test_failed_ops_consume_no_ids(self):
        """Core: Contacts. Failed operations consume NO ids."""
        with self.assertRaises(ValidationError):
            self.store.create_contact("", {"email": "a@b"}, OPERATOR)
        c = self.store.create_contact("Ok", {"email": "a@b"}, OPERATOR)
        self.assertEqual(c["id"], "ct-1")

    def test_viewer_cannot_write(self):
        """Core: Contacts / Access control. Viewer contact_write denied before any state change."""
        with self.assertRaises(PermissionDenied):
            self.store.create_contact("Dana", {"email": "d@x.y"}, VIEWER)
        self.assertEqual(self.store.list_contacts(ADMIN), [])

    def test_addresses_copied(self):
        """Core: Contacts. Returned addresses dict is a copy."""
        c = self.store.create_contact("Dana", {"email": "d@x.y"}, OPERATOR)
        c["addresses"]["email"] = "evil@x.y"
        self.assertEqual(self.store.get_contact(c["id"], OPERATOR)["addresses"]["email"], "d@x.y")


if __name__ == "__main__":
    unittest.main()
