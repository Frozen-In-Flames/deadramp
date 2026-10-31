"""Core function 5: procurement records -- purchase orders with
derived totals and a recorded lifecycle (CM-6, AU-2/AU-3, SI-10).

The order total is computed at read from quantity x unit-price
lines and is never stored. Suppliers are opaque references.
"""

import unittest

from erp.errors import ValidationError

from erp_helpers import OPERATOR, VIEWER, make_org, make_store

LINES = [
    {"item_label": "Paper, case", "quantity": 3, "unit_price_cents": 499},
    {"item_label": "Toner", "quantity": 2, "unit_price_cents": 2500},
]


def make_order(store, org, actor=OPERATOR, ref="PO-0001"):
    return store.create_purchase_order(actor, org["id"], ref, "SUPPLIER-1",
                                       LINES)


class PurchaseOrderTests(unittest.TestCase):
    def test_total_is_derived_and_never_stored(self):
        store, _ = make_store()
        org = make_org(store)
        order = make_order(store, org)
        self.assertEqual(order["total_cents"], 3 * 499 + 2 * 2500)
        stored = store._purchase_orders[order["id"]]
        self.assertNotIn("total_cents", stored)

    def test_lifecycle_transitions(self):
        store, _ = make_store()
        org = make_org(store)
        order = make_order(store, org)
        received = store.transition_purchase_order(OPERATOR, order["id"],
                                                   "received")
        self.assertEqual(received["status"], "received")
        closed = store.transition_purchase_order(OPERATOR, order["id"],
                                                 "closed")
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            store.transition_purchase_order(OPERATOR, order["id"], "open")

    def test_open_can_close_directly_but_not_reopen(self):
        store, _ = make_store()
        org = make_org(store)
        order = make_order(store, org)
        store.transition_purchase_order(OPERATOR, order["id"], "closed")
        with self.assertRaises(ValidationError):
            store.transition_purchase_order(OPERATOR, order["id"], "received")

    def test_line_validation(self):
        store, _ = make_store()
        org = make_org(store)
        for lines in (
            [],
            [{"item_label": "X", "quantity": 0, "unit_price_cents": 1}],
            [{"item_label": "X", "quantity": 1.5, "unit_price_cents": 1}],
            [{"item_label": "X", "quantity": 1, "unit_price_cents": -1}],
            [{"item_label": "X", "quantity": 1, "unit_price_cents": True}],
        ):
            with self.assertRaises(ValidationError, msg=repr(lines)):
                store.create_purchase_order(OPERATOR, org["id"], "PO-X",
                                            "SUPPLIER-1", lines)
        self.assertEqual(store.list_purchase_orders(VIEWER), [])

    def test_po_ref_unique_per_org(self):
        store, _ = make_store()
        org = make_org(store)
        make_order(store, org)
        with self.assertRaises(ValidationError):
            make_order(store, org)


if __name__ == "__main__":
    unittest.main()
