"""Core function 2: telecom service inventory (pinned opaque shape)."""

import unittest

import mdm_helpers as H
from mdm.errors import ValidationError

PINNED_KEYS = {
    "id", "org_id", "ref", "service_kind", "label", "plan_ref",
    "monthly_recurring_cents", "provisioning_state",
    "created_by", "created_utc",
}


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()

    def test_record_shape_is_pinned(self):
        """No field can hold a real device identifier: the shape has
        no phone-number, IMEI, serial, or MAC key at all."""
        item = H.make_inventory(self.store, self.org)
        self.assertEqual(set(item.keys()), PINNED_KEYS)
        joined = "_".join(sorted(item.keys()))
        for forbidden in ("phone", "imei", "serial", "mac_address", "device"):
            self.assertNotIn(forbidden, joined)
        self.assertEqual(item["provisioning_state"], "active")

    def test_duplicate_ref_rejected_within_org_only(self):
        H.make_inventory(self.store, self.org)
        with self.assertRaises(ValidationError):
            H.make_inventory(self.store, self.org)
        other = H.make_org(self.store, ref="AGENCY-2", label="Agency Two")
        item = H.make_inventory(self.store, other)
        self.assertEqual(item["org_id"], other["id"])

    def test_bad_kind_and_money_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_inventory(self.store, self.org, service_kind="satellite")
        for bad in (50_000.0, True, "50000", -1):
            with self.assertRaises(ValidationError):
                H.make_inventory(self.store, self.org, ref="SVC-X",
                                 monthly_recurring_cents=bad)

    def test_all_kinds_and_filters(self):
        H.make_inventory(self.store, self.org)
        H.make_inventory(self.store, self.org, ref="SVC-200",
                         service_kind="mobility", label="Field lines",
                         plan_ref="PLAN-MOB-1", monthly_recurring_cents=25_000)
        H.make_inventory(self.store, self.org, ref="SVC-300",
                         service_kind="other", label="Future service",
                         plan_ref="PLAN-FUT-1", monthly_recurring_cents=10_000)
        all_items = self.store.list_inventory(H.MEMBER, self.org["id"])
        self.assertEqual(len(all_items), 3)
        mobility = self.store.list_inventory(
            H.MEMBER, self.org["id"], service_kind="mobility")
        self.assertEqual([i["ref"] for i in mobility], ["SVC-200"])
        active = self.store.list_inventory(
            H.MEMBER, self.org["id"], state="active")
        self.assertEqual(len(active), 3)


if __name__ == "__main__":
    unittest.main()
