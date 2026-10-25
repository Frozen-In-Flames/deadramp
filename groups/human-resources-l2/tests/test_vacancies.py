"""Vacancy announcement tests.

Traces to: Core function 3 (Vacancy announcements bound to positions,
ISO open/close dates; AU-2, CM-6).
"""

import unittest

from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


class TestVacancies(unittest.TestCase):
    """Core 3: vacancy announcements bound to position records."""

    def test_create_vacancy_record(self):
        """Core 3: a vacancy binds position, title and ISO dates with a vac- id and status draft."""
        store, position, _ = make_store()
        vac = store.create_vacancy(
            position["id"], "Analyst Opening", SPECIALIST,
            opens_on="2026-07-01", closes_on="2026-07-31",
        )
        self.assertEqual(vac["id"], "vac-1")
        self.assertEqual(vac["position_id"], position["id"])
        self.assertEqual(vac["status"], "draft")
        self.assertEqual(vac["opens_on"], "2026-07-01")

    def test_set_vacancy_status(self):
        """Core 3: status moves draft -> posted -> closed; bad status -> ValidationError."""
        store, position, _ = make_store()
        vac = store.create_vacancy(position["id"], "Opening", ADMIN)
        self.assertEqual(store.set_vacancy_status(vac["id"], "posted", SPECIALIST)["status"], "posted")
        self.assertEqual(store.set_vacancy_status(vac["id"], "closed", ADMIN)["status"], "closed")
        with self.assertRaises(ValidationError):
            store.set_vacancy_status(vac["id"], "open", ADMIN)
        with self.assertRaises(NotFoundError):
            store.set_vacancy_status("vac-999", "posted", ADMIN)

    def test_date_validation(self):
        """Core 3 (SI-10): non-ISO dates and closes before opens are validation errors; equal open/close is allowed; no id consumed."""
        store, position, _ = make_store()
        with self.assertRaises(ValidationError):
            store.create_vacancy(position["id"], "X", ADMIN, opens_on="July 1")
        with self.assertRaises(ValidationError):
            store.create_vacancy(position["id"], "X", ADMIN, opens_on="2026-07-31", closes_on="2026-07-01")
        vac = store.create_vacancy(position["id"], "X", ADMIN, opens_on="2026-07-01", closes_on="2026-07-01")
        self.assertEqual(vac["id"], "vac-1")

    def test_unknown_position_not_found(self):
        """Core 3: a vacancy against an unknown position -> NotFoundError."""
        store, _, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.create_vacancy("pos-999", "X", ADMIN)

    def test_write_roles_and_org_level_reads(self):
        """Core 3 / Core 11: employee and auditor may not write vacancies; vacancies are org-level, so an employee may read any vacancy."""
        store, position, _ = make_store()
        for actor in (EMPLOYEE, AUDITOR):
            with self.assertRaises(PermissionDenied):
                store.create_vacancy(position["id"], "Nope", actor)
        vac = store.create_vacancy(position["id"], "Opening", ADMIN)
        self.assertEqual(store.get_vacancy(vac["id"], EMPLOYEE)["id"], vac["id"])
        self.assertEqual(len(store.list_vacancies(EMPLOYEE, position_id=position["id"])), 1)


if __name__ == "__main__":
    unittest.main()
