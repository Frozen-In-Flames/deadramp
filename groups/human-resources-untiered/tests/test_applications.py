"""Application record tests.

Traces to: Core function 4 (Applications of persons to vacancies,
with the duplicate live-application rule; AC-2, AU-2), plus employee
scope under Core function 11.
"""

import unittest

from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


def _setup():
    store, position, person = make_store()
    vacancy = store.create_vacancy(position["id"], "Analyst Opening", ADMIN)
    return store, position, person, vacancy


class TestApplications(unittest.TestCase):
    """Core 4: application records binding person_ref to vacancy."""

    def test_create_application_record(self):
        """Core 4 (AC-2): an application binds person_ref + vacancy with an app- id and stage applied."""
        store, _, _, vacancy = _setup()
        app = store.create_application("carol", vacancy["id"], SPECIALIST)
        self.assertEqual(app["id"], "app-1")
        self.assertEqual(app["stage"], "applied")
        self.assertEqual(app["person_ref"], "carol")
        self.assertEqual(app["vacancy_id"], vacancy["id"])

    def test_duplicate_live_application_rejected(self):
        """Core 4 (SI-10): a duplicate live application for the same person+vacancy is a validation error and consumes no id; after not_selected or withdrawn a new application is allowed."""
        store, _, _, vacancy = _setup()
        first = store.create_application("carol", vacancy["id"], SPECIALIST)
        with self.assertRaises(ValidationError):
            store.create_application("carol", vacancy["id"], SPECIALIST)
        store.set_application_stage(first["id"], "not_selected", SPECIALIST)
        second = store.create_application("carol", vacancy["id"], SPECIALIST)
        self.assertEqual(second["id"], "app-2")
        store.set_application_stage(second["id"], "withdrawn", SPECIALIST)
        third = store.create_application("carol", vacancy["id"], SPECIALIST)
        self.assertEqual(third["id"], "app-3")

    def test_unknown_person_and_vacancy_not_found(self):
        """Core 4: applying for an unknown person_ref -> NotFoundError; unknown vacancy -> NotFoundError."""
        store, _, _, vacancy = _setup()
        with self.assertRaises(NotFoundError):
            store.create_application("ghost", vacancy["id"], SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.create_application("carol", "vac-999", SPECIALIST)

    def test_set_application_stage(self):
        """Core 4: stage moves through the stage vocabulary; bad stage -> ValidationError; unknown id -> NotFoundError."""
        store, _, _, vacancy = _setup()
        app = store.create_application("carol", vacancy["id"], SPECIALIST)
        for stage in ("screened", "referred", "selected"):
            self.assertEqual(store.set_application_stage(app["id"], stage, SPECIALIST)["stage"], stage)
        with self.assertRaises(ValidationError):
            store.set_application_stage(app["id"], "hired", SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.set_application_stage("app-999", "screened", SPECIALIST)

    def test_employee_scope_and_write_denied(self):
        """Core 4 / Core 11: an employee may not create applications, reads her own only, and lists only her own."""
        store, _, _, vacancy = _setup()
        store.create_person("erin", ADMIN, kind="applicant")
        with self.assertRaises(PermissionDenied):
            store.create_application("carol", vacancy["id"], EMPLOYEE)
        own = store.create_application("carol", vacancy["id"], SPECIALIST)
        other = store.create_application("erin", vacancy["id"], SPECIALIST)
        self.assertEqual(store.get_application(own["id"], EMPLOYEE)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_application(other["id"], EMPLOYEE)
        with self.assertRaises(PermissionDenied):
            store.list_applications(EMPLOYEE, person_ref="erin")
        self.assertEqual([a["id"] for a in store.list_applications(EMPLOYEE)], [own["id"]])

    def test_list_filters(self):
        """Core 4: list filters by person_ref and vacancy_id for staff roles."""
        store, position, _, vacancy = _setup()
        second_vac = store.create_vacancy(position["id"], "Second Opening", ADMIN)
        store.create_application("carol", vacancy["id"], SPECIALIST)
        store.create_application("carol", second_vac["id"], SPECIALIST)
        self.assertEqual(len(store.list_applications(ADMIN, person_ref="carol")), 2)
        self.assertEqual(len(store.list_applications(ADMIN, vacancy_id=vacancy["id"])), 1)


if __name__ == "__main__":
    unittest.main()
