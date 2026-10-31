"""Core functions 7-8: person records (the system of record) and
time & absence records (SI-10; privacy by shape).

The person shape is pinned to exactly the keys the substrate
needs -- an opaque reference, a department label, a role label --
and a recursive scan proves no key anywhere in the record could
hold a real identifier (no name, email, phone, or address field
exists to fill).
"""

import unittest

from erp.errors import NotFoundError, ValidationError

from erp_helpers import (OPERATOR, PERSON_REF, make_org, make_person,
                         make_store)

PERSON_KEYS = {"id", "org_id", "person_ref", "department_label",
               "role_label", "created_by", "created_utc"}
FORBIDDEN_KEY_PARTS = ("name", "email", "phone", "address", "ssn",
                       "birth", "contact")


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class PersonTests(unittest.TestCase):
    def setUp(self):
        self.store, _ = make_store()
        self.org = make_org(self.store)

    def test_shape_is_pinned_and_identifier_free(self):
        person = make_person(self.store, self.org)
        self.assertEqual(set(person.keys()), PERSON_KEYS)
        for key in _all_keys(person):
            for part in FORBIDDEN_KEY_PARTS:
                self.assertNotIn(part, key.lower(),
                                 "person record carries key %r" % key)

    def test_person_ref_unique_per_org(self):
        make_person(self.store, self.org)
        with self.assertRaises(ValidationError):
            make_person(self.store, self.org)

    def test_missing_person_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.store.get_person(OPERATOR, "per-99")


class TimeAndAbsenceTests(unittest.TestCase):
    def setUp(self):
        self.store, _ = make_store()
        self.org = make_org(self.store)
        make_person(self.store, self.org)

    def test_time_entry_records_whole_minutes(self):
        entry = self.store.create_time_entry(
            OPERATOR, self.org["id"], PERSON_REF, "2024-03-04", 480)
        self.assertEqual(entry["minutes"], 480)
        for bad in (0, -5, 90.5, True, "480"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.create_time_entry(
                    OPERATOR, self.org["id"], PERSON_REF, "2024-03-04", bad)

    def test_time_entry_requires_real_date_and_person(self):
        with self.assertRaises(ValidationError):
            self.store.create_time_entry(
                OPERATOR, self.org["id"], PERSON_REF, "2024-02-30", 60)
        with self.assertRaises(NotFoundError):
            self.store.create_time_entry(
                OPERATOR, self.org["id"], "PERSON-404", "2024-03-04", 60)

    def test_absence_range_is_validated(self):
        absence = self.store.create_absence(
            OPERATOR, self.org["id"], PERSON_REF, "Leave (label)",
            "2024-04-01", "2024-04-03")
        self.assertEqual(absence["to_date"], "2024-04-03")
        with self.assertRaises(ValidationError):
            self.store.create_absence(
                OPERATOR, self.org["id"], PERSON_REF, "Leave (label)",
                "2024-04-03", "2024-04-01")
        listed = self.store.list_absences(
            OPERATOR, org_id=self.org["id"], person_ref=PERSON_REF)
        self.assertEqual(len(listed), 1)


if __name__ == "__main__":
    unittest.main()
