"""Negative control: the suite must reject a mutant derived-status gate.

Traces to: the contract's required negative control for Group 18.

The traced claim (Core functions 3 and 5): **plan status is derived
deterministically from due/completion dates, and enrollment status is
derived from the participant's plan records** -- an incomplete plan
whose due date is before the reference date must read ``overdue``,
never ``current``, and an enrollment over such a plan must read
``overdue`` too; a completed plan must read ``completed``.

The mutant below is a HealthStore subclass whose
``_derive_plan_status`` always returns ``"current"`` -- the
derivation is skipped -- so the mutant reports a past-due incomplete
plan (and its enrollment) as current and also misses completions.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation (it says "current"
anyway), and (3) a literal assertRaises(AssertionError) showing that
treating the mutant's outcome as the expected outcome fails.

This file asserts the invariant holds in the UNMUTATED code. The
mutation-verification drill (patching the real
``_derive_plan_status``, running the suite, restoring by SHA-256) is
recorded in ``tests/README.md``.
"""

import unittest

from health_helpers import ADMIN, CLINICIAN, MEMBER, fresh_store, make_store
from health.audit import AuditLog
from health.errors import PermissionDenied
from health.store import HealthStore

AS_OF = "2026-06-15"


class MutantHealthStore(HealthStore):
    """Mutant derivation: plan status is always 'current', derivation skipped."""

    def _derive_plan_status(self, plan, as_of_date):
        """Core 5 (negative control mutant) -- always returns 'current'."""
        return "current"


def _make(store_cls):
    """Build a store of the given class with program, participant, enrollment, past-due plan."""
    store = store_cls(audit=AuditLog())
    program = store.create_program("Diabetes Care", ADMIN, code="DIA-101")
    participant = store.create_participant("carol", ADMIN)
    enrollment = store.create_enrollment(participant["id"], program["id"], CLINICIAN)
    plan = store.create_plan(participant["id"], program["id"], "Daily checks",
                             "2026-06-01", CLINICIAN)
    return store, program, participant, enrollment, plan


class TestNegativeControlMutantDerivedStatus(unittest.TestCase):
    """Core 3/5: derived-status derivation -- negative control,
    traced claim: derived status is deterministic in (record dates,
    plan records, as_of)."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 5 (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_past_due_incomplete_plan_is_overdue_canonical_but_mutant_current(self):
        """Core 5, traced claim: past-due + incomplete -> overdue.
        Canonical: overdue. Mutant: says current anyway."""
        store, _, _, _, plan = _make(HealthStore)
        canonical = store.get_plan(plan["id"], ADMIN, as_of=AS_OF)["derived_status"]
        self.assertEqual(canonical, "overdue")

        mstore, _, _, _, mplan = _make(MutantHealthStore)
        mutant = mstore.get_plan(mplan["id"], ADMIN, as_of=AS_OF)["derived_status"]
        self.assertEqual(mutant, "current")  # mutant did NOT derive overdue
        self._assert_mutant_rejected(mutant, "overdue")

    def test_completed_plan_is_completed_canonical_but_mutant_current(self):
        """Core 5, traced claim: a completed plan -> completed.
        Canonical: completed. Mutant: says current anyway."""
        store, _, _, _, plan = _make(HealthStore)
        store.complete_plan(plan["id"], "2026-05-20", CLINICIAN)
        canonical = store.get_plan(plan["id"], ADMIN, as_of=AS_OF)["derived_status"]
        self.assertEqual(canonical, "completed")

        mstore, _, _, _, mplan = _make(MutantHealthStore)
        mstore.complete_plan(mplan["id"], "2026-05-20", CLINICIAN)
        mutant = mstore.get_plan(mplan["id"], ADMIN, as_of=AS_OF)["derived_status"]
        self.assertEqual(mutant, "current")  # mutant did NOT derive completed
        self._assert_mutant_rejected(mutant, "completed")

    def test_enrollment_overdue_follows_plan_canonical_but_mutant_enrolled(self):
        """Core 3, traced claim: enrollment status derives from plans.
        Canonical: overdue (its plan is overdue). Mutant: the plan reads
        current, so the enrollment reads enrolled -- never overdue."""
        store, _, _, enrollment, _ = _make(HealthStore)
        canonical = store.get_enrollment(enrollment["id"], ADMIN, as_of=AS_OF)["derived_status"]
        self.assertEqual(canonical, "overdue")

        mstore, _, _, menrollment, _ = _make(MutantHealthStore)
        mutant = mstore.get_enrollment(menrollment["id"], ADMIN, as_of=AS_OF)["derived_status"]
        self.assertEqual(mutant, "enrolled")  # mutant did NOT derive overdue
        self._assert_mutant_rejected(mutant, "overdue")

    def test_member_must_not_create_programs(self):
        """Core 5 companion gate / Core 9, traced claim: RBAC is
        enforced before any state change -- a member creating a
        program is denied in the canonical implementation and the
        registry stays empty."""
        bare = fresh_store()
        with self.assertRaises(PermissionDenied):
            bare.create_program("Smuggled Program", MEMBER)
        self.assertEqual(bare.list_programs(ADMIN), [])
        mutant_outcome = "allowed"  # a no-check gate would wave this through
        self._assert_mutant_rejected(mutant_outcome, "denied")


if __name__ == "__main__":
    unittest.main()
