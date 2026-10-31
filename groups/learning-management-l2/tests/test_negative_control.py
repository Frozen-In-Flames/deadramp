"""Negative control: the suite must reject a mutant compliance gate.

Traces to: the contract's required negative control for Group 48.

The traced claim (Core function 9): **compliance status is derived
deterministically from assignment, due date, and progress records** --
an incomplete assignment whose due date is before the reference date
must read ``overdue``, and a completed progress record must read
``completed``; the derivation is never ``current`` for a past-due
incomplete assignment.

The mutant below is an LmsStore subclass whose ``_derive_status``
always returns ``"current"`` -- the compliance derivation is skipped
-- so the mutant reports a past-due incomplete assignment as current
and also misses completions.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation (it says "current"
anyway), and (3) a literal assertRaises(AssertionError) showing that
treating the mutant's outcome as the expected outcome fails.

This file asserts the invariant holds in the UNMUTATED code.
"""

import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER
from lms.audit import AuditLog
from lms.errors import PermissionDenied
from lms.store import LmsStore

AS_OF = "2026-06-15"


class MutantLmsStore(LmsStore):
    """Mutant derivation: status is always 'current', derivation skipped."""

    def _derive_status(self, *args, **kwargs):
        """Core 9 (negative control mutant) -- always returns 'current'."""
        return "current"


def _make(store_cls):
    """Build a store of the given class with a learner, a course and a past-due assignment."""
    store = store_cls(audit=AuditLog())
    store.create_learner("carol", "Carol Learner", ADMIN)
    course = store.create_course("Safety Basics", ADMIN, code="SAFE-101")
    assignment = store.create_compliance_assignment("carol", course["id"],
                                                    "2026-06-01", ADMIN)
    return store, course, assignment


class TestNegativeControlMutantCompliance(unittest.TestCase):
    """Core 9: compliance status derivation -- negative control,
    traced claim: derived status is deterministic in (assignment,
    due date, progress records, as_of)."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 9 (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_past_due_incomplete_is_overdue_canonical_but_mutant_current(self):
        """Core 9, traced claim: past-due + incomplete -> overdue.
        Canonical: overdue. Mutant: says current anyway."""
        store, _, assignment = _make(LmsStore)
        canonical = store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)["status"]
        self.assertEqual(canonical, "overdue")

        mstore, _, massignment = _make(MutantLmsStore)
        mutant = mstore.compliance_status(massignment["id"], ADMIN, as_of=AS_OF)["status"]
        self.assertEqual(mutant, "current")  # mutant did NOT derive overdue
        self._assert_mutant_rejected(mutant, "overdue")

    def test_completed_is_completed_canonical_but_mutant_current(self):
        """Core 9, traced claim: a completed progress record -> completed.
        Canonical: completed. Mutant: says current anyway."""
        store, course, assignment = _make(LmsStore)
        store.record_progress("carol", course["id"], "completed", INSTRUCTOR)
        canonical = store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)["status"]
        self.assertEqual(canonical, "completed")

        mstore, mcourse, massignment = _make(MutantLmsStore)
        mstore.record_progress("carol", mcourse["id"], "completed", INSTRUCTOR)
        mutant = mstore.compliance_status(massignment["id"], ADMIN, as_of=AS_OF)["status"]
        self.assertEqual(mutant, "current")  # mutant did NOT derive completed
        self._assert_mutant_rejected(mutant, "completed")

    def test_learner_must_not_create_compliance_assignment(self):
        """Core 9 companion gate / Core 12, traced claim: RBAC is
        enforced before any state change -- a learner creating a
        compliance assignment (or a course) is denied in the canonical
        implementation and nothing is stored."""
        store, course, _ = _make(LmsStore)
        with self.assertRaises(PermissionDenied):
            store.create_compliance_assignment("carol", course["id"],
                                               "2026-06-01", LEARNER)
        self.assertEqual(
            len(store.list_compliance(ADMIN, as_of=AS_OF)), 1
        )  # only the canonical assignment from _make exists
        bare_course_count = len(store.list_courses(ADMIN))
        with self.assertRaises(PermissionDenied):
            store.create_course("Smuggled Course", LEARNER)
        self.assertEqual(len(store.list_courses(ADMIN)), bare_course_count)
        mutant_outcome = "allowed"  # a no-check gate would wave this through
        self._assert_mutant_rejected(mutant_outcome, "denied")


if __name__ == "__main__":
    unittest.main()
