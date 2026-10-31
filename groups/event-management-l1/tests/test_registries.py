"""Core functions 1-2: the organizer and vendor registries.

Pinned record shapes keyed by opaque references -- no field can
hold a real identifier (privacy discipline) -- ref uniqueness, and
role enforcement (AC-3, CM-6, SI-10).
"""

import unittest

from events.errors import NotFoundError, PermissionDenied, ValidationError

from events_helpers import (ADMIN, MEMBER, VIEWER, make_organizer,
                            make_store, make_vendors)

PARTY_KEYS = {"id", "ref", "label", "created_by", "created_utc"}
FORBIDDEN = ("name", "email", "phone", "address", "ssn", "contact")


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()

    def test_organizer_shape_is_pinned(self):
        organizer = make_organizer(self.store)
        self.assertEqual(set(organizer), PARTY_KEYS)
        self.assertTrue(organizer["id"].startswith("org-"))
        for key in organizer:
            for word in FORBIDDEN:
                self.assertNotIn(word, key)

    def test_vendor_shape_is_pinned(self):
        vendor, _, _ = make_vendors(self.store)
        self.assertEqual(set(vendor), PARTY_KEYS)
        self.assertTrue(vendor["id"].startswith("ven-"))

    def test_ref_must_be_unique_per_registry(self):
        make_organizer(self.store)
        with self.assertRaises(ValidationError):
            self.store.create_organizer(ADMIN, "ORG-0001", "Other office")
        # The same ref text in the other registry is a different party.
        vendor = self.store.create_vendor(ADMIN, "ORG-0001", "Vendor")
        self.assertEqual(vendor["ref"], "ORG-0001")

    def test_blank_ref_or_label_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_organizer(ADMIN, "", "Label")
        with self.assertRaises(ValidationError):
            self.store.create_vendor(ADMIN, "VEN-X", "  ")
        with self.assertRaises(ValidationError):
            self.store.create_vendor(ADMIN, None, "Label")

    def test_get_and_list(self):
        organizer = make_organizer(self.store)
        self.assertEqual(
            self.store.get_organizer(VIEWER, organizer["id"])["ref"],
            "ORG-0001")
        self.assertEqual(len(self.store.list_organizers(VIEWER)), 1)
        self.assertEqual(len(self.store.list_vendors(VIEWER)), 0)
        with self.assertRaises(NotFoundError):
            self.store.get_vendor(ADMIN, "ven-99")

    def test_viewer_cannot_register(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_organizer(VIEWER, "ORG-9", "Nope")
        with self.assertRaises(PermissionDenied):
            self.store.create_vendor(VIEWER, "VEN-9", "Nope")

    def test_failed_create_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.store.create_organizer(ADMIN, "", "Label")
        organizer = make_organizer(self.store)
        self.assertEqual(organizer["id"], "org-1")


if __name__ == "__main__":
    unittest.main()
