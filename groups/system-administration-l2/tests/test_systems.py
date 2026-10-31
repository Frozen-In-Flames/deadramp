"""Core 2 (Managed system registry) / SI-10, opaque-reference
privacy discipline: pinned record shape, per-org ref uniqueness,
kind validation, retire lifecycle, membership boundary.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import PermissionDenied, ValidationError

SYSTEM_KEYS = {"id", "org_id", "ref", "label", "kind", "platform_ref",
               "state", "created_by", "created_utc"}


class TestSystems(unittest.TestCase):
    def test_record_shape_pinned_no_live_identifier_field(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        self.assertEqual(set(system.keys()), SYSTEM_KEYS)
        stored = store._systems[system["id"]]
        self.assertEqual(set(stored.keys()), SYSTEM_KEYS)
        for forbidden in ("hostname", "ip_address", "address", "credential",
                          "password", "serial", "fqdn"):
            self.assertNotIn(forbidden, stored)

    def test_starts_registered(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        self.assertEqual(system["state"], "registered")
        self.assertEqual(system["kind"], "operating_system")

    def test_platform_service_kind_accepted(self):
        store, org = H.make_store()
        system = H.make_system(store, org, ref="SYS-SVC-1",
                               kind="platform_service")
        self.assertEqual(system["kind"], "platform_service")

    def test_invalid_kind_rejected(self):
        store, org = H.make_store()
        with self.assertRaises(ValidationError):
            H.make_system(store, org, kind="hypervisor")

    def test_duplicate_ref_rejected_per_org_but_not_across_orgs(self):
        store, org = H.make_store()
        H.make_system(store, org)
        with self.assertRaises(ValidationError):
            H.make_system(store, org)
        other = H.make_org(store, ref="AGENCY-2")
        twin = store.create_system(H.MEMBER, other["id"], "SYS-OS-1",
                                   "Other OS", "operating_system", "PLAT-B")
        self.assertEqual(twin["ref"], "SYS-OS-1")

    def test_retire_lifecycle(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        retired = store.retire_system(H.MEMBER, system["id"])
        self.assertEqual(retired["state"], "retired")
        with self.assertRaises(ValidationError):
            store.retire_system(H.MEMBER, system["id"])

    def test_outsider_cannot_read_or_list(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        with self.assertRaises(PermissionDenied):
            store.get_system(H.OUTSIDER, system["id"])
        with self.assertRaises(PermissionDenied):
            store.list_systems(H.OUTSIDER, org["id"])


if __name__ == "__main__":
    unittest.main()
