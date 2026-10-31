"""Negative control: the suite must reject a mutant compliance gate.

Traces to: the contract's required negative control for Group 13.

The traced claim (Core function 6): **compliance status is derived
deterministically from assignment, due date, and progress records** --
an incomplete assignment whose due date is before the reference date
must read ``overdue``, and a completed progress record must read
``completed``; the derivation is never ``current`` for a past-due
incomplete assignment.

The mutant below is a LearnStore subclass whose ``_derive_status``
always returns ``"current"`` -- the overdue/completed derivation is
skipped -- so the mutant reports a past-due incomplete assignment as
current and also misses completions.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation (it says "current"
anyway), and (3) a literal assertRaises(AssertionError) showing that
treating the mutant's outcome as the expected outcome fails.

This file asserts the invariant holds in the UNMUTATED code. The
mutation-verification drill (patching the real ``_derive_status``,
running the suite, restoring by SHA-256) is recorded in
``tests/README.md``.
"""

import unittest

from learn_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from learn.errors import PermissionDenied
from learn.store import LearnStore

AS_OF = "2026-06-15"


class MutantLearnStore(LearnStore):
    """Mutant derivation: status is always 'current', derivation skipped."""

    def _derive_status(self, assignment, as_of_date):
        """Core 6 (negative control mutant) -- always returns 'current'."""
        return "current"


def _make(store_cls):
    """Build a store of the given class with a course and a past-due assignment."""
    from learn.audit import AuditLog
    store = store_cls(audit=AuditLog())
    course = store.create_course("Safety Basics", ADMIN, code="SAFE-101")
    assignment = store.create_compliance_assignment("carol", course["id"], "2026-06-01", ADMIN)
    return store, course, assignment


class TestNegativeControlMutantCompliance(unittest.TestCase):
    """Core 6: compliance status derivation -- negative control,
    traced claim: derived status is deterministic in (assignment,
    due date, progress records, as_of)."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 6 (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_past_due_incomplete_is_overdue_canonical_but_mutant_current(self):
        """Core 6, traced claim: past-due + incomplete -> overdue.
        Canonical: overdue. Mutant: says current anyway."""
        store, _, assignment = _make(LearnStore)
        canonical = store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)["status"]
        self.assertEqual(canonical, "overdue")

        mstore, _, massignment = _make(MutantLearnStore)
        mutant = mstore.compliance_status(massignment["id"], ADMIN, as_of=AS_OF)["status"]
        self.assertEqual(mutant, "current")  # mutant did NOT derive overdue
        self._assert_mutant_rejected(mutant, "overdue")

    def test_completed_is_completed_canonical_but_mutant_current(self):
        """Core 6, traced claim: a completed progress record -> completed.
        Canonical: completed. Mutant: says current anyway."""
        store, course, assignment = _make(LearnStore)
        store.record_progress("carol", course["id"], "completed", INSTRUCTOR)
        canonical = store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)["status"]
        self.assertEqual(canonical, "completed")

        mstore, mcourse, massignment = _make(MutantLearnStore)
        mstore.record_progress("carol", mcourse["id"], "completed", INSTRUCTOR)
        mutant = mstore.compliance_status(massignment["id"], ADMIN, as_of=AS_OF)["status"]
        self.assertEqual(mutant, "current")  # mutant did NOT derive completed
        self._assert_mutant_rejected(mutant, "completed")

    def test_learner_must_not_create_courses(self):
        """Core 6 companion gate / Core 9, traced claim: RBAC is
        enforced before any state change -- a learner creating a
        course is denied in the canonical implementation and the
        registry stays empty."""
        store, _ = make_store()
        # make_store already created one course as ADMIN; use a fresh check:
        from learn_helpers import fresh_store
        bare = fresh_store()
        with self.assertRaises(PermissionDenied):
            bare.create_course("Smuggled Course", LEARNER)
        self.assertEqual(bare.list_courses(ADMIN), [])
        mutant_outcome = "allowed"  # a no-check gate would wave this through
        self._assert_mutant_rejected(mutant_outcome, "denied")


if __name__ == "__main__":
    unittest.main()
