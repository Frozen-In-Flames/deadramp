"""Core 7 (Control inheritance records): the recorded source of
a control for a managed system -- inherited from the underlying
hosting platform, local, or shared -- carried verbatim. The store
derives no posture, score, or compliance value from these records
(the no-score pin lives in test_store_validation.py).
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import ValidationError

CONTROL_KEYS = {"id", "org_id", "system_id", "control_ref", "source",
                "note", "created_by", "created_utc"}


class TestControls(unittest.TestCase):
    def test_record_shape_pinned(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        control = H.make_control(store, org, system)
        self.assertEqual(set(control.keys()), CONTROL_KEYS)
        self.assertEqual(control["source"], "inherited")
        self.assertEqual(control["control_ref"], "SC-7")

    def test_all_sources_accepted(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        for i, source in enumerate(("inherited", "local", "shared")):
            control = H.make_control(store, org, system,
                                     control_ref="AC-%d" % i, source=source)
            self.assertEqual(control["source"], source)

    def test_invalid_source_rejected(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        with self.assertRaises(ValidationError):
            H.make_control(store, org, system, source="waived")

    def test_duplicate_control_for_system_rejected(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        H.make_control(store, org, system)
        with self.assertRaises(ValidationError):
            H.make_control(store, org, system)
        other_system = H.make_system(store, org, ref="SYS-OS-2")
        twin = H.make_control(store, org, other_system)
        self.assertEqual(twin["control_ref"], "SC-7")

    def test_cross_org_system_rejected(self):
        store, org = H.make_store()
        system = H.make_system(store, org)
        other = H.make_org(store, ref="AGENCY-2")
        with self.assertRaises(ValidationError):
            store.create_control(H.MEMBER, other["id"], system["id"],
                                 "AC-2", "local")


if __name__ == "__main__":
    unittest.main()
