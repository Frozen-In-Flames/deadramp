"""Core function 12: inventory records (SI-10).

Quantities are integers, change only through recorded
adjustments, and may never go negative -- stock cannot be issued
that the records do not hold.
"""

import unittest

from erp.errors import ValidationError

from erp_helpers import OPERATOR, make_org, make_store


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.store, _ = make_store()
        self.org = make_org(self.store)
        self.item = self.store.create_inventory_item(
            OPERATOR, self.org["id"], "ITEM-0001", "Fasteners, box", 40)

    def test_adjustments_move_the_quantity(self):
        item = self.store.adjust_inventory(OPERATOR, self.item["id"], -15)
        self.assertEqual(item["quantity_on_hand"], 25)
        item = self.store.adjust_inventory(OPERATOR, self.item["id"], 10)
        self.assertEqual(item["quantity_on_hand"], 35)

    def test_quantity_never_goes_negative(self):
        with self.assertRaises(ValidationError):
            self.store.adjust_inventory(OPERATOR, self.item["id"], -41)
        items = self.store.list_inventory_items(OPERATOR,
                                                org_id=self.org["id"])
        self.assertEqual(items[0]["quantity_on_hand"], 40)

    def test_quantities_are_integers(self):
        for bad in (2.5, True, "10"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.create_inventory_item(
                    OPERATOR, self.org["id"], "ITEM-X", "X", bad)
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.adjust_inventory(OPERATOR, self.item["id"], bad)
        with self.assertRaises(ValidationError):
            self.store.adjust_inventory(OPERATOR, self.item["id"], 0)


if __name__ == "__main__":
    unittest.main()
