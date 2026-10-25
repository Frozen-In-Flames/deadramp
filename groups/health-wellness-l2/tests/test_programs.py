"""Program registry tests.

Traces to: Core function 2 (Program registry; CM-6, SI-12) --
programs (clinics, care journeys, scorecard populations) as explicit,
configuration-controlled records.
"""

import unittest

from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER, fresh_store
from health.errors import NotFoundError, PermissionDenied, ValidationError


class TestPrograms(unittest.TestCase):
    """Core 2: program registry."""

    def test_create_shape_and_kinds(self):
        """Core 2 (CM-6): created program carries exactly id/title/kind/code/description/created_by/created_utc with a prg- id; kinds program/clinic/care_journey accepted."""
        store = fresh_store()
        rec = store.create_program("Diabetes Care", ADMIN, code="DIA-101")
        self.assertEqual(rec["id"], "prg-1")
        self.assertEqual(rec["kind"], "program")
        self.assertEqual(rec["code"], "DIA-101")
        self.assertEqual(set(rec), {"id", "title", "kind", "code", "description",
                                    "created_by", "created_utc"})
        clinic = store.create_program("Clinic A", ADMIN, kind="clinic")
        self.assertEqual(clinic["kind"], "clinic")
        journey = store.create_program("Journey", ADMIN, kind="care_journey")
        self.assertEqual(journey["kind"], "care_journey")

    def test_validation(self):
        """Core 2 (SI-10): empty title / bad kind / non-string code or description -> ValidationError, no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_program("", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_program("X", ADMIN, kind="alien")
        with self.assertRaises(ValidationError):
            store.create_program("X", ADMIN, code=123)
        with self.assertRaises(ValidationError):
            store.create_program("X", ADMIN, description=123)
        rec = store.create_program("Ok", ADMIN)
        self.assertEqual(rec["id"], "prg-1")

    def test_get_list_and_unknown(self):
        """Core 2: get/list sorted by id; unknown id -> NotFoundError."""
        store = fresh_store()
        first = store.create_program("A", ADMIN)
        second = store.create_program("B", ADMIN)
        self.assertEqual([r["id"] for r in store.list_programs(AUDITOR)],
                         [first["id"], second["id"]])
        self.assertEqual(store.get_program(first["id"], MEMBER)["title"], "A")
        with self.assertRaises(NotFoundError):
            store.get_program("prg-999", ADMIN)

    def test_write_admin_only_reads_open(self):
        """Core 2 / Core 9: program_write is admin-only; programs are registry records readable by all roles without scoping (member included)."""
        store = fresh_store()
        for actor in (CLINICIAN, MEMBER, AUDITOR):
            with self.assertRaises(PermissionDenied):
                store.create_program("Nope", actor)
        rec = store.create_program("Open", ADMIN)
        for actor in (ADMIN, CLINICIAN, MEMBER, AUDITOR):
            self.assertEqual(store.get_program(rec["id"], actor)["id"], rec["id"])


if __name__ == "__main__":
    unittest.main()
