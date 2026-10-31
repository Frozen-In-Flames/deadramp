"""Core function 5: contract & quote registries."""

import unittest

import mdm_helpers as H
from mdm.errors import ValidationError


class TestContractsQuotes(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.contract = H.make_contract(self.store, self.org)

    def test_contract_shape_and_window(self):
        contract = self.contract
        self.assertEqual(contract["ref"], "CON-1")
        self.assertEqual(contract["starts_on"], "2026-01-01")
        self.assertEqual(contract["ends_on"], "2026-12-31")
        with self.assertRaises(ValidationError):
            H.make_contract(self.store, self.org, ref="CON-2",
                            starts_on="2026-12-31", ends_on="2026-01-01")

    def test_duplicate_contract_ref_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_contract(self.store, self.org)

    def test_quote_records(self):
        item = H.make_inventory(self.store, self.org)
        quote = self.store.create_quote(
            H.MEMBER, self.org["id"], self.contract["id"], 48_500,
            inventory_id=item["id"], note="Renewal quote")
        self.assertEqual(quote["amount_cents"], 48_500)
        self.assertEqual(len(self.store.list_quotes(H.MEMBER, self.org["id"])), 1)

    def test_quote_validation(self):
        with self.assertRaises(ValidationError):
            self.store.create_quote(
                H.MEMBER, self.org["id"], self.contract["id"], 100.5)
        other = H.make_org(self.store, ref="AGENCY-2", label="Two")
        other_contract = H.make_contract(self.store, other, ref="CON-9")
        with self.assertRaises(ValidationError):
            self.store.create_quote(
                H.MEMBER, self.org["id"], other_contract["id"], 100)


if __name__ == "__main__":
    unittest.main()
