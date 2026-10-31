"""Financial wellness offering registry tests.

Traces to: UNION-SPEC Core function 6 (Financial wellness offering
registry — offerings with a title and a kind registered per program,
with participant enrollment records; the wellness tools themselves are
Extended); Implementation contract for ``finance/store.py`` wellness
methods; control family SI-10 (validation before mutation).
"""

import unittest

from finance_helpers import (
    MEMBER,
    OUTSIDER,
    make_employee,
    make_store,
    make_traveler,
)
from finance.errors import NotFoundError, PermissionDenied, ValidationError

OFFERING_KEYS = {"id", "program_id", "title", "kind", "created_by",
                 "created_utc"}
ENROLLMENT_KEYS = {
    "id", "program_id", "offering_id", "participant_id", "status",
    "created_by", "created_utc",
}
WELLNESS_KINDS = {"education", "coaching", "budgeting", "savings",
                  "counseling"}


class WellnessBase(unittest.TestCase):
    """A canonical program with one employee and one traveler."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.employee = make_employee(self.store, self.program_id)
        self.traveler = make_traveler(self.store, self.program_id)

    def make_offering(self, title="Budgeting Basics", kind="budgeting"):
        return self.store.create_wellness_offering(
            self.program_id, title, kind, MEMBER
        )


class TestWellnessOfferings(WellnessBase):
    """Core 6: Wellness registry — offering creation shape/validation."""

    def test_create_offering_returns_the_contract_dict(self):
        """Core 6: Wellness registry. Contract: create_wellness_offering
        returns {id, program_id, title, kind, created_by, created_utc}
        with the wel- prefix."""
        offering = self.make_offering()
        self.assertEqual(set(offering.keys()), OFFERING_KEYS)
        self.assertEqual(offering["id"], "wel-1")
        self.assertEqual(offering["program_id"], self.program_id)
        self.assertEqual(offering["title"], "Budgeting Basics")
        self.assertEqual(offering["kind"], "budgeting")
        self.assertEqual(offering["created_by"], "bob")

    def test_each_wellness_kind_is_accepted(self):
        """Core 6: Wellness registry. Contract: kind must be one of
        education, coaching, budgeting, savings, counseling — all five
        are valid."""
        for i, kind in enumerate(sorted(WELLNESS_KINDS)):
            with self.subTest(kind=kind):
                offering = self.store.create_wellness_offering(
                    self.program_id, "Offering %d" % i, kind, MEMBER
                )
                self.assertEqual(offering["kind"], kind)

    def test_bad_kind_is_a_validation_error(self):
        """Core 6: Wellness registry. Contract: a kind outside the five
        named kinds -> ValidationError."""
        for bad in ("therapy", "Budgeting", "", None):
            with self.subTest(kind=bad):
                with self.assertRaises(ValidationError):
                    self.store.create_wellness_offering(
                        self.program_id, "Nope", bad, MEMBER
                    )
        self.assertEqual(
            self.store.list_wellness_offerings(self.program_id, MEMBER), []
        )

    def test_empty_title_is_a_validation_error(self):
        """Core 6: Wellness registry. Contract: title must be a
        non-empty string."""
        for bad in ("", None, 42):
            with self.subTest(title=bad):
                with self.assertRaises(ValidationError):
                    self.store.create_wellness_offering(
                        self.program_id, bad, "budgeting", MEMBER
                    )

    def test_failed_offering_create_consumes_no_id(self):
        """Core 6: Wellness registry (SI-10). A failed creation
        changes nothing: the next successful offering is wel-1."""
        with self.assertRaises(ValidationError):
            self.store.create_wellness_offering(
                self.program_id, "Nope", "bogus-kind", MEMBER
            )
        self.assertEqual(self.make_offering()["id"], "wel-1")

    def test_get_and_list_offerings(self):
        """Core 6: Wellness registry. get_wellness_offering returns
        one offering; list_wellness_offerings returns them in creation
        order."""
        first = self.make_offering("Budgeting Basics", "budgeting")
        second = self.make_offering("Savings 101", "savings")
        got = self.store.get_wellness_offering(
            self.program_id, first["id"], MEMBER
        )
        self.assertEqual(got["id"], first["id"])
        self.assertEqual(set(got.keys()), OFFERING_KEYS)
        offerings = self.store.list_wellness_offerings(self.program_id, MEMBER)
        self.assertEqual(
            [o["id"] for o in offerings], [first["id"], second["id"]]
        )

    def test_cross_program_offering_get_is_not_found(self):
        """Core 6: Wellness registry. Contract: an offering id that
        belongs to another program raises NotFoundError."""
        offering = self.make_offering()
        other = self.store.create_program("other-program", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_wellness_offering(other["id"], offering["id"],
                                              MEMBER)

    def test_non_member_cannot_create_offering(self):
        """Core 6: Wellness registry (AC-3). A non-member cannot create
        an offering (membership boundary)."""
        with self.assertRaises(PermissionDenied):
            self.store.create_wellness_offering(
                self.program_id, "Nope", "budgeting", OUTSIDER
            )


class TestWellnessEnrollments(WellnessBase):
    """Core 6: Wellness registry — enrollment records."""

    def test_enroll_returns_the_contract_dict(self):
        """Core 6: Wellness registry. Contract: enroll_participant
        returns {id, program_id, offering_id, participant_id, status,
        created_by, created_utc} with the enr- prefix and status
        enrolled."""
        offering = self.make_offering()
        enrollment = self.store.enroll_participant(
            self.program_id, offering["id"], self.employee["id"], MEMBER
        )
        self.assertEqual(set(enrollment.keys()), ENROLLMENT_KEYS)
        self.assertEqual(enrollment["id"], "enr-1")
        self.assertEqual(enrollment["program_id"], self.program_id)
        self.assertEqual(enrollment["offering_id"], offering["id"])
        self.assertEqual(enrollment["participant_id"], self.employee["id"])
        self.assertEqual(enrollment["status"], "enrolled")
        self.assertEqual(enrollment["created_by"], "bob")

    def test_any_participant_kind_may_enroll(self):
        """Core 6: Wellness registry. Enrollment is not kind-gated in
        the contract: both an employee and a traveler may enroll."""
        offering = self.make_offering()
        first = self.store.enroll_participant(
            self.program_id, offering["id"], self.employee["id"], MEMBER
        )
        second = self.store.enroll_participant(
            self.program_id, offering["id"], self.traveler["id"], MEMBER
        )
        self.assertEqual([first["id"], second["id"]], ["enr-1", "enr-2"])

    def test_duplicate_enrollment_is_a_validation_error(self):
        """Core 6: Wellness registry. Contract: 'a duplicate enrollment
        for the same (offering, participant) -> ValidationError', and
        the failed attempt stores nothing and consumes no id."""
        offering = self.make_offering()
        self.store.enroll_participant(
            self.program_id, offering["id"], self.employee["id"], MEMBER
        )
        with self.assertRaises(ValidationError):
            self.store.enroll_participant(
                self.program_id, offering["id"], self.employee["id"], MEMBER
            )
        enrollments = self.store.list_wellness_enrollments(
            self.program_id, MEMBER
        )
        self.assertEqual(len(enrollments), 1)
        other = self.store.enroll_participant(
            self.program_id, offering["id"], self.traveler["id"], MEMBER
        )
        self.assertEqual(other["id"], "enr-2")

    def test_same_participant_in_another_offering_is_ok(self):
        """Core 6: Wellness registry. Uniqueness is per (offering,
        participant): the same participant in a different offering is
        accepted."""
        first = self.make_offering("Budgeting Basics", "budgeting")
        second = self.make_offering("Savings 101", "savings")
        self.store.enroll_participant(
            self.program_id, first["id"], self.employee["id"], MEMBER
        )
        enrollment = self.store.enroll_participant(
            self.program_id, second["id"], self.employee["id"], MEMBER
        )
        self.assertEqual(enrollment["offering_id"], second["id"])

    def test_cross_program_offering_enroll_is_not_found(self):
        """Core 6: Wellness registry. Contract: the offering must
        exist in this program — enrolling under another program's id
        with this program's offering raises NotFoundError."""
        offering = self.make_offering()
        other = self.store.create_program("other-program", MEMBER)
        other_participant = make_employee(self.store, other["id"], ref="emp-9")
        with self.assertRaises(NotFoundError):
            self.store.enroll_participant(
                other["id"], offering["id"], other_participant["id"], MEMBER
            )

    def test_cross_program_participant_enroll_is_not_found(self):
        """Core 6: Wellness registry. Contract: the participant must
        exist in this program — enrolling another program's
        participant here raises NotFoundError."""
        offering = self.make_offering()
        other = self.store.create_program("other-program", MEMBER)
        other_participant = make_employee(self.store, other["id"], ref="emp-9")
        with self.assertRaises(NotFoundError):
            self.store.enroll_participant(
                self.program_id, offering["id"], other_participant["id"],
                MEMBER,
            )

    def test_enroll_with_unknown_ids_is_not_found(self):
        """Core 6: Wellness registry. Unknown offering or participant
        ids -> NotFoundError."""
        offering = self.make_offering()
        with self.assertRaises(NotFoundError):
            self.store.enroll_participant(
                self.program_id, "wel-999999", self.employee["id"], MEMBER
            )
        with self.assertRaises(NotFoundError):
            self.store.enroll_participant(
                self.program_id, offering["id"], "part-999999", MEMBER
            )

    def test_list_enrollments_filtered_by_offering(self):
        """Core 6: Wellness registry. Contract:
        list_wellness_enrollments returns enrollments in creation
        order, honouring offering_id=."""
        first = self.make_offering("Budgeting Basics", "budgeting")
        second = self.make_offering("Savings 101", "savings")
        enr1 = self.store.enroll_participant(
            self.program_id, first["id"], self.employee["id"], MEMBER
        )
        enr2 = self.store.enroll_participant(
            self.program_id, second["id"], self.employee["id"], MEMBER
        )
        enr3 = self.store.enroll_participant(
            self.program_id, first["id"], self.traveler["id"], MEMBER
        )
        all_enrollments = self.store.list_wellness_enrollments(
            self.program_id, MEMBER
        )
        self.assertEqual(
            [e["id"] for e in all_enrollments],
            [enr1["id"], enr2["id"], enr3["id"]],
        )
        filtered = self.store.list_wellness_enrollments(
            self.program_id, MEMBER, offering_id=first["id"]
        )
        self.assertEqual([e["id"] for e in filtered],
                         [enr1["id"], enr3["id"]])
        filtered = self.store.list_wellness_enrollments(
            self.program_id, MEMBER, offering_id=second["id"]
        )
        self.assertEqual([e["id"] for e in filtered], [enr2["id"]])


if __name__ == "__main__":
    unittest.main()
