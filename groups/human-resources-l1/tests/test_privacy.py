"""Privacy discipline tests.

Traces to: the privacy discipline (hard rule) for the Human
Resources category, carried with the substrate at this tier --
records hold an opaque caller-supplied ``person_ref`` string only.
NO field anywhere may hold a real name, SSN, DOB, salary /
compensation figure, address, phone, or email.
"""

import unittest

from hr_helpers import ADMIN, SPECIALIST, make_store

FORBIDDEN = {
    "name", "ssn", "social_security_number", "salary", "compensation",
    "pay", "dob", "date_of_birth", "address", "phone", "email",
}


def _walk_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _walk_keys(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            keys |= _walk_keys(item)
    return keys


class TestPrivacy(unittest.TestCase):
    """Privacy discipline: no forbidden field on any record type."""

    def test_person_record_exact_key_set(self):
        """Privacy: the person record shape is EXACTLY {id, person_ref, kind, status, created_by, created_utc}."""
        store, _, person = make_store()
        self.assertEqual(
            set(person), {"id", "person_ref", "kind", "status", "created_by", "created_utc"}
        )
        self.assertEqual(person["person_ref"], "carol")

    def test_no_forbidden_keys_on_any_entity(self):
        """Privacy: walking one record of EVERY entity type finds no key in the forbidden set {name, ssn, social_security_number, salary, compensation, pay, dob, date_of_birth, address, phone, email}."""
        store, position, person = make_store()
        vacancy = store.create_vacancy(position["id"], "Opening", ADMIN)
        app = store.create_application("carol", vacancy["id"], SPECIALIST)
        evl = store.create_evaluation(app["id"], "panel", "Panel", SPECIALIST)
        evl = store.add_evaluation_entry(evl["id"], "rater-1", 4, "Ok", SPECIALIST)
        lifecycle = store.create_lifecycle_case(
            "carol", "onboarding", SPECIALIST, task_titles=["Badge"]
        )
        review = store.create_performance_review("carol", "2026", SPECIALIST)
        benefits = store.create_benefits_record("carol", "benefit_enrollment", "plan-a", SPECIALIST)
        case = store.create_case("carol", "general", "Inquiry", SPECIALIST)
        records = {
            "person": person,
            "position": position,
            "vacancy": vacancy,
            "application": app,
            "evaluation": evl,
            "lifecycle_case": lifecycle,
            "performance_review": review,
            "benefits_record": benefits,
            "case": case,
        }
        for label, record in records.items():
            with self.subTest(entity=label):
                self.assertEqual(_walk_keys(record) & FORBIDDEN, set())


if __name__ == "__main__":
    unittest.main()
