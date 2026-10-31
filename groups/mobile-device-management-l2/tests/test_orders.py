"""Core function 3: service order records & lifecycle (AC-5)."""

import unittest

import mdm_helpers as H
from mdm.errors import PermissionDenied, ValidationError


class TestOrders(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.item = H.make_inventory(self.store, self.org)

    def _order(self, **kw):
        kwargs = {"order_type": "suspend", "detail": "Suspend for site closure",
                  "inventory_id": self.item["id"]}
        kwargs.update(kw)
        return self.store.create_order(H.MEMBER, self.org["id"], **kwargs)

    def test_create_shape(self):
        order = self._order()
        self.assertEqual(order["status"], "requested")
        self.assertEqual(order["requested_by"], "bob")
        self.assertIsNone(order["decided_by"])

    def test_new_order_targets_nothing_existing(self):
        order = self.store.create_order(
            H.MEMBER, self.org["id"], "new", "New circuit for annex")
        self.assertIsNone(order["inventory_id"])
        with self.assertRaises(ValidationError):
            self.store.create_order(
                H.MEMBER, self.org["id"], "new", "Bad",
                inventory_id=self.item["id"])

    def test_non_new_order_requires_item(self):
        with self.assertRaises(ValidationError):
            self.store.create_order(
                H.MEMBER, self.org["id"], "suspend", "No target")
        with self.assertRaises(ValidationError):
            self.store.create_order(
                H.MEMBER, self.org["id"], "teleport", "Bad type",
                inventory_id=self.item["id"])

    def test_decider_is_never_requester(self):
        """AC-5: bob requested it, so bob cannot decide it."""
        order = self._order()
        with self.assertRaises(PermissionDenied):
            self.store.decide_order(H.MEMBER, order["id"], True)
        decided = self.store.decide_order(H.STAFF, order["id"], True)
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(decided["decided_by"], "erin")

    def test_reject_and_terminal_states(self):
        order = self._order()
        self.store.decide_order(H.STAFF, order["id"], False)
        view = self.store.get_order(H.MEMBER, order["id"])
        self.assertEqual(view["status"], "rejected")
        with self.assertRaises(ValidationError):
            self.store.fulfill_order(H.MEMBER, order["id"])
        with self.assertRaises(ValidationError):
            self.store.cancel_order(H.MEMBER, order["id"])

    def test_fulfill_requires_approval(self):
        order = self._order()
        with self.assertRaises(ValidationError):
            self.store.fulfill_order(H.MEMBER, order["id"])

    def test_fulfillment_moves_provisioning_state(self):
        """The only way an item's state changes: a fulfilled order."""
        order = self._order()
        self.store.decide_order(H.STAFF, order["id"], True)
        self.store.fulfill_order(H.MEMBER, order["id"])
        item = self.store.get_inventory_item(H.MEMBER, self.item["id"])
        self.assertEqual(item["provisioning_state"], "suspended")
        # Restore brings it back.
        restore = self._order(order_type="restore", detail="Reopen site")
        self.store.decide_order(H.STAFF, restore["id"], True)
        self.store.fulfill_order(H.MEMBER, restore["id"])
        item = self.store.get_inventory_item(H.MEMBER, self.item["id"])
        self.assertEqual(item["provisioning_state"], "active")
        # Disconnect ends it.
        drop = self._order(order_type="disconnect", detail="Decommission")
        self.store.decide_order(H.STAFF, drop["id"], True)
        self.store.fulfill_order(H.MEMBER, drop["id"])
        item = self.store.get_inventory_item(H.MEMBER, self.item["id"])
        self.assertEqual(item["provisioning_state"], "disconnected")

    def test_unfulfilled_order_changes_nothing(self):
        order = self._order()
        self.store.decide_order(H.STAFF, order["id"], True)
        item = self.store.get_inventory_item(H.MEMBER, self.item["id"])
        self.assertEqual(item["provisioning_state"], "active")

    def test_cancel_from_requested_and_approved(self):
        first = self._order()
        self.store.cancel_order(H.MEMBER, first["id"])
        self.assertEqual(self.store.get_order(H.MEMBER, first["id"])["status"],
                         "cancelled")
        second = self._order()
        self.store.decide_order(H.STAFF, second["id"], True)
        self.store.cancel_order(H.MEMBER, second["id"])
        self.assertEqual(self.store.get_order(H.MEMBER, second["id"])["status"],
                         "cancelled")


if __name__ == "__main__":
    unittest.main()
