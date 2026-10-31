"""Program and participation tests, including the derived status."""

import unittest

from talentdev.errors import NotFoundError, PermissionDenied, ValidationError
from talentdev.store import _derive_participation_status
from talentdev_helpers import ADMIN, OPERATOR, VIEWER, make_org, make_program, make_store


class TestOrganizations(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()

    def test_create_get_list(self):
        org = make_org(self.store)
        self.assertEqual(org["id"], "org-1")
        self.assertEqual(self.store.get_organization(ADMIN, "org-1")["ref"],
                         "agency-alpha")
        self.assertEqual(len(self.store.list_organizations(ADMIN)), 1)

    def test_duplicate_ref_and_unknown(self):
        make_org(self.store)
        with self.assertRaises(ValidationError):
            self.store.create_organization(ADMIN, "agency-alpha", "Dupe")
        with self.assertRaises(NotFoundError):
            self.store.get_organization(ADMIN, "org-99")
        # A failed create consumed no id.
        second = self.store.create_organization(ADMIN, "agency-beta", "Beta")
        self.assertEqual(second["id"], "org-2")

    def test_viewer_cannot_register(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_organization(VIEWER, "agency-x", "X")


class TestPrograms(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org = make_org(self.store)

    def test_both_kinds_recorded_separately(self):
        behavior = make_program(self.store, org_id=self.org["id"])
        talent = self.store.create_program(
            OPERATOR, self.org["id"], "Craft Skills", "talent_development")
        self.assertEqual(behavior["kind"], "behavioral_mindset_development")
        self.assertEqual(talent["kind"], "talent_development")
        self.assertEqual(behavior["goal_label"], "mission-readiness")
        by_kind = self.store.list_programs(ADMIN, kind="talent_development")
        self.assertEqual([p["id"] for p in by_kind], [talent["id"]])
        summary = self.store.summary(ADMIN)
        self.assertEqual(summary["programs_by_kind"],
                         {"talent_development": 1,
                          "behavioral_mindset_development": 1})

    def test_unknown_kind_refused(self):
        with self.assertRaises(ValidationError):
            self.store.create_program(
                ADMIN, self.org["id"], "Coaching Circle", "coaching")
        with self.assertRaises(ValidationError):
            self.store.create_program(
                ADMIN, self.org["id"], "LMS Track", "learning_management")
        self.assertEqual(self.store.list_programs(ADMIN), [])

    def test_unknown_org_and_goal_label_rules(self):
        with self.assertRaises(NotFoundError):
            self.store.create_program(ADMIN, "org-99", "X",
                                      "talent_development")
        program = self.store.create_program(
            ADMIN, self.org["id"], "No Goal", "talent_development")
        self.assertIsNone(program["goal_label"])


class TestParticipations(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.program = make_program(self.store)

    def test_enroll_and_derived_status(self):
        view = self.store.enroll(OPERATOR, self.program["id"], "person-001",
                                 enrolled_at="2026-10-01")
        self.assertEqual(view["status"], "enrolled")
        stored = self.store._participations[view["id"]]
        self.assertNotIn("status", stored)
        done = self.store.complete_participation(
            OPERATOR, view["id"], completed_at="2026-10-20")
        self.assertEqual(done["status"], "completed")
        self.assertEqual(
            _derive_participation_status(
                self.store._participations[view["id"]]), "completed")
        # The derivation seam is a pure function of the stored record.
        self.assertEqual(_derive_participation_status(
            {"completed_at": None}), "enrolled")
        self.assertEqual(_derive_participation_status(
            {"completed_at": "2026-10-20T00:00:00+00:00"}), "completed")

    def test_status_filters_and_summary(self):
        first = self.store.enroll(ADMIN, self.program["id"], "person-001")
        self.store.enroll(ADMIN, self.program["id"], "person-002")
        self.store.complete_participation(ADMIN, first["id"])
        enrolled = self.store.list_participations(ADMIN, status="enrolled")
        self.assertEqual(len(enrolled), 1)
        summary = self.store.summary(ADMIN)
        self.assertEqual(summary["participations_by_status"],
                         {"enrolled": 1, "completed": 1})

    def test_duplicate_enrollment_refused(self):
        self.store.enroll(ADMIN, self.program["id"], "person-001")
        with self.assertRaises(ValidationError):
            self.store.enroll(ADMIN, self.program["id"], "person-001")
        self.assertEqual(len(self.store.list_participations(ADMIN)), 1)

    def test_completion_rules(self):
        view = self.store.enroll(ADMIN, self.program["id"], "person-001",
                                 enrolled_at="2026-10-10")
        with self.assertRaises(ValidationError):
            self.store.complete_participation(ADMIN, view["id"],
                                              completed_at="2026-10-01")
        self.store.complete_participation(ADMIN, view["id"],
                                          completed_at="2026-10-15")
        with self.assertRaises(ValidationError):
            self.store.complete_participation(ADMIN, view["id"])

    def test_person_ref_cannot_be_an_email(self):
        with self.assertRaises(ValidationError):
            self.store.enroll(ADMIN, self.program["id"],
                              "someone@example.gov")
        with self.assertRaises(ValidationError):
            self.store.enroll(ADMIN, self.program["id"], "has space")
        with self.assertRaises(ValidationError):
            self.store.enroll(ADMIN, self.program["id"], "")
        # Refusals recorded nothing.
        self.assertEqual(self.store.list_participations(ADMIN), [])

    def test_viewer_cannot_enroll(self):
        with self.assertRaises(PermissionDenied):
            self.store.enroll(VIEWER, self.program["id"], "person-001")


if __name__ == "__main__":
    unittest.main()
