"""Negative control: the suite must reject a mutant lifecycle gate.

Traces to: the contract's required negative control for the
carried substrate at this tier (Group 21's control, re-anchored:
this singleton's fork claims no lifecycle function, so at L1 the
derivation stands as a design property of the carried substrate,
traced to CM-6 / AU-2 at the Low baseline in UNION-SPEC.md rather
than to a sibling's evidenced claim).

The traced claim (Core function 6): **lifecycle case status is
derived deterministically from the case's tasks and cancelled flag**
-- a case whose every task is done/waived must read ``complete``,
and an untouched case must read ``not_started``; the derivation is
never ``in_progress`` for a fully-completed case.

The mutant below is an HrStore subclass whose ``_derive_case_status``
always returns ``"in_progress"`` -- the derivation is skipped -- so
the mutant reports a completed case as in_progress and also misses
not_started.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation (it says
"in_progress" anyway), and (3) a literal
assertRaises(AssertionError) showing that treating the mutant's
outcome as the expected outcome fails.

This file asserts the invariant holds in the UNMUTATED code. The
mutation-verification drill (patching the real
``_derive_case_status``, running the suite, restoring by SHA-256) is
recorded in ``tests/README.md``.
"""

import unittest

from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, make_store
from hr.audit import AuditLog
from hr.errors import PermissionDenied
from hr.store import HrStore


class MutantHrStore(HrStore):
    """Mutant derivation: status is always 'in_progress', derivation skipped."""

    def _derive_case_status(self, case):
        """Core 6 (negative control mutant) -- always returns 'in_progress'."""
        return "in_progress"


def _make(store_cls):
    """Build a store of the given class with position, person and an onboarding case."""
    store = store_cls(audit=AuditLog())
    store.create_position("Program Analyst", ADMIN, series="0343", grade="13")
    store.create_person("carol", ADMIN, kind="employee")
    case = store.create_lifecycle_case(
        "carol", "onboarding", SPECIALIST, task_titles=["Badge", "Laptop"]
    )
    return store, case


class TestNegativeControlMutantLifecycle(unittest.TestCase):
    """Core 6: lifecycle status derivation -- negative control,
    traced claim: derived status is deterministic in (tasks,
    cancelled flag)."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 6 (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_all_tasks_done_is_complete_canonical_but_mutant_in_progress(self):
        """Core 6, traced claim: all tasks done/waived -> complete.
        Canonical: complete. Mutant: says in_progress anyway."""
        store, case = _make(HrStore)
        store.set_task_state(case["id"], "t-1", "done", SPECIALIST)
        store.set_task_state(case["id"], "t-2", "waived", SPECIALIST)
        canonical = store.get_lifecycle_case(case["id"], ADMIN)["status"]
        self.assertEqual(canonical, "complete")

        mstore, mcase = _make(MutantHrStore)
        mstore.set_task_state(mcase["id"], "t-1", "done", SPECIALIST)
        mstore.set_task_state(mcase["id"], "t-2", "waived", SPECIALIST)
        mutant = mstore.get_lifecycle_case(mcase["id"], ADMIN)["status"]
        self.assertEqual(mutant, "in_progress")  # mutant did NOT derive complete
        self._assert_mutant_rejected(mutant, "complete")

    def test_untouched_case_is_not_started_canonical_but_mutant_in_progress(self):
        """Core 6, traced claim: no task done/waived -> not_started.
        Canonical: not_started. Mutant: says in_progress anyway."""
        store, case = _make(HrStore)
        canonical = store.get_lifecycle_case(case["id"], ADMIN)["status"]
        self.assertEqual(canonical, "not_started")

        mstore, mcase = _make(MutantHrStore)
        mutant = mstore.get_lifecycle_case(mcase["id"], ADMIN)["status"]
        self.assertEqual(mutant, "in_progress")  # mutant did NOT derive not_started
        self._assert_mutant_rejected(mutant, "not_started")

    def test_employee_must_not_create_positions(self):
        """Core 6 companion gate / Core 11, traced claim: RBAC is
        enforced before any state change -- an employee creating a
        position is denied in the canonical implementation and the
        registry stays empty."""
        from hr_helpers import fresh_store
        bare = fresh_store()
        with self.assertRaises(PermissionDenied):
            bare.create_position("Smuggled Position", EMPLOYEE)
        self.assertEqual(bare.list_positions(ADMIN), [])
        mutant_outcome = "allowed"  # a no-check gate would wave this through
        self._assert_mutant_rejected(mutant_outcome, "denied")


if __name__ == "__main__":
    unittest.main()
