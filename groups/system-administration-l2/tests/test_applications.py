"""Core 3 (Application registry) / SI-10, privacy discipline:
pinned record shape, hosting-system linkage, per-org ref
uniqueness, retire lifecycle.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import ValidationError

APPLICATION_KEYS = {"id", "org_id", "system_id", "ref", "label", "state",
                    "created_by", "created_utc"}


class TestApplications(unittest.TestCase):
    def test_record_shape_pinned(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        self.assertEqual(set(application.keys()), APPLICATION_KEYS)
        self.assertEqual(application["system_id"], system["id"])
        self.assertEqual(application["state"], "registered")

    def test_cross_org_system_rejected(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        other = H.make_org(store, ref="AGENCY-2")
        with self.assertRaises(ValidationError):
            store.create_application(H.MEMBER, other["id"], system["id"],
                                     "APP-X", "x")

    def test_duplicate_ref_rejected(self):
        store, org = H.make_store()
        system, _ = H.make_estate(store, org)
        with self.assertRaises(ValidationError):
            H.make_application(store, org, system)

    def test_retire_lifecycle(self):
        store, org = H.make_store()
        _, application = H.make_estate(store, org)
        retired = store.retire_application(H.MEMBER, application["id"])
        self.assertEqual(retired["state"], "retired")
        with self.assertRaises(ValidationError):
            store.retire_application(H.MEMBER, application["id"])

    def test_list_filters_by_system(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        other_system = H.make_system(store, org, ref="SYS-OS-2")
        listed = store.list_applications(H.MEMBER, org["id"],
                                         system_id=system["id"])
        self.assertEqual([a["id"] for a in listed], [application["id"]])
        self.assertEqual(
            store.list_applications(H.MEMBER, org["id"],
                                    system_id=other_system["id"]), [])


if __name__ == "__main__":
    unittest.main()
