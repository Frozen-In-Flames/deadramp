"""Core function 2: network registry -- pinned shape (SI-10, AC-3)."""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import PermissionDenied, ValidationError


class TestNetworks(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()

    def test_create_shape_is_pinned(self):
        network = H.make_network(self.store, self.org)
        self.assertEqual(
            set(network.keys()),
            {"id", "org_id", "ref", "label", "site_ref",
             "created_by", "created_utc"})
        self.assertTrue(network["id"].startswith("net-"))
        stored = self.store._networks[network["id"]]
        self.assertEqual(set(stored.keys()), set(network.keys()))

    def test_ref_unique_per_org_but_reusable_across_orgs(self):
        H.make_network(self.store, self.org)
        with self.assertRaises(ValidationError):
            H.make_network(self.store, self.org, label="Copy")
        other = H.make_org(self.store, ref="AGENCY-2", label="Agency Two")
        network = H.make_network(self.store, other)
        self.assertEqual(network["ref"], "NET-HQ")

    def test_empty_fields_rejected(self):
        for overrides in ({"ref": " "}, {"label": ""}, {"site_ref": None}):
            with self.assertRaises(ValidationError):
                H.make_network(self.store, self.org, **overrides)

    def test_outsider_cannot_read_or_list(self):
        network = H.make_network(self.store, self.org)
        with self.assertRaises(PermissionDenied):
            self.store.get_network(H.OUTSIDER, network["id"])
        with self.assertRaises(PermissionDenied):
            self.store.list_networks(H.OUTSIDER, self.org["id"])

    def test_get_and_list(self):
        network = H.make_network(self.store, self.org)
        view = self.store.get_network(H.MEMBER, network["id"])
        self.assertEqual(view["site_ref"], "SITE-HQ")
        listed = self.store.list_networks(H.MEMBER, self.org["id"])
        self.assertEqual([n["id"] for n in listed], [network["id"]])


if __name__ == "__main__":
    unittest.main()
