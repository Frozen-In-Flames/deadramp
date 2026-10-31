"""Core function 1 & 2: customer and provider registries.

Shapes are pinned: a registry record carries exactly id, ref, label,
created_by, created_utc -- there is no field that could hold a real
name, address, email, phone number, or account identifier (privacy
discipline; IA-2 stays with the embedding organization).
"""

import unittest

from energy.errors import PermissionDenied, ValidationError

from energy_helpers import (ADMIN, CUSTOMER_LABEL, MEMBER, OWNER_REF,
                            PROVIDER_LABEL, PROVIDER_REF_A, VIEWER,
                            make_store)

PARTY_KEYS = {"id", "ref", "label", "created_by", "created_utc"}


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()

    def test_customer_created_with_pinned_shape(self):
        customer = self.store.create_customer(ADMIN, OWNER_REF, CUSTOMER_LABEL)
        self.assertEqual(customer["id"], "cust-1")
        self.assertEqual(set(customer.keys()), PARTY_KEYS)
        self.assertEqual(customer["ref"], OWNER_REF)
        self.assertEqual(customer["label"], CUSTOMER_LABEL)
        self.assertEqual(customer["created_by"], "alice")

    def test_provider_created_with_pinned_shape(self):
        provider = self.store.create_provider(ADMIN, PROVIDER_REF_A, PROVIDER_LABEL)
        self.assertEqual(provider["id"], "prov-1")
        self.assertEqual(set(provider.keys()), PARTY_KEYS)

    def test_duplicate_ref_rejected_and_consumes_no_id(self):
        self.store.create_customer(ADMIN, OWNER_REF, CUSTOMER_LABEL)
        with self.assertRaises(ValidationError):
            self.store.create_customer(ADMIN, OWNER_REF, "other label")
        nxt = self.store.create_customer(ADMIN, "CUST-0002", "second")
        self.assertEqual(nxt["id"], "cust-2")

    def test_blank_ref_or_label_rejected(self):
        for args in [("", "x"), ("REF", "  "), (None, "x"), ("REF", None)]:
            with self.assertRaises(ValidationError):
                self.store.create_customer(ADMIN, *args)

    def test_viewer_cannot_register(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_customer(VIEWER, OWNER_REF, CUSTOMER_LABEL)
        self.store.create_customer(MEMBER, OWNER_REF, CUSTOMER_LABEL)

    def test_get_and_list(self):
        customer = self.store.create_customer(ADMIN, OWNER_REF, CUSTOMER_LABEL)
        self.assertEqual(self.store.get_customer(VIEWER, customer["id"]),
                         customer)
        self.assertEqual(len(self.store.list_customers(VIEWER)), 1)
        self.assertEqual(len(self.store.list_providers(VIEWER)), 0)


if __name__ == "__main__":
    unittest.main()
