"""Negative control: the suite must reject a mutant due-status derivation.

Traces to: the contract's required negative control for Group 32.

(a) Derived due status (Core 6): a mutant store whose
``_derive_due_status`` returns "current" for the overdue branch must
NOT satisfy the canonical expectation that a past-due, uncompleted
record is "overdue".
(b) Stored-record invariant (Core 6): the stored maintenance record
carries no status key; a mutant view that stored one would break the
pinned key set.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation, and
(3) a literal assertRaises(AssertionError) showing treating the
mutant's outcome as expected fails.

This file asserts the invariant holds in the UNMUTATED code. The
mutation-verification drill (patching the real ``_derive_due_status``
in store.py so the overdue branch returns "current", running the
suite, restoring by SHA-256) is recorded in ``tests/README.md``.
"""

import unittest
from datetime import date

from fleet_helpers import ADMIN, make_store
from fleet.store import FleetStore


class MutantFleetStore(FleetStore):
    """Mutant derivation: the overdue branch returns 'current'."""

    def _derive_due_status(self, record, as_of_date):
        """Core 6 (negative control mutant) -- overdue is hidden."""
        if record.get("completed_date"):
            return "completed"
        return "current"


class TestNegativeControlDerivation(unittest.TestCase):
    """Core 6 derived due status -- negative control."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 6 (negative control): treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_overdue_canonical_but_mutant_reports_current(self):
        """Core 6, traced claim: as_of after due_date -> 'overdue'. Canonical: overdue. Mutant: current."""
        store, vehicle, operator = make_store()
        rec = store.create_maintenance(vehicle["id"], "maintenance", "2026-12-01", ADMIN)
        canonical = store.get_maintenance(rec["id"], ADMIN, as_of="2026-12-02")["derived_status"]
        self.assertEqual(canonical, "overdue")

        from fleet.audit import AuditLog
        mstore = MutantFleetStore(audit=AuditLog())
        mvehicle = mstore.create_vehicle("Pool Sedan 1", "sedan", ADMIN)
        mrec = mstore.create_maintenance(mvehicle["id"], "maintenance", "2026-12-01", ADMIN)
        mutant = mstore.get_maintenance(mrec["id"], ADMIN, as_of="2026-12-02")["derived_status"]
        self.assertEqual(mutant, "current")
        self._assert_mutant_rejected(mutant, "overdue")

    def test_current_and_completed_agree_in_both(self):
        """Core 6, traced claim: the mutant only hides overdue -- 'current' before due and 'completed' after completion match canonically, isolating the mutated branch."""
        store, vehicle, operator = make_store()
        rec = store.create_maintenance(vehicle["id"], "inspection", "2026-12-01", ADMIN)
        self.assertEqual(store._derive_due_status(store._maintenance[rec["id"]], date(2026, 11, 1)), "current")
        mutant = MutantFleetStore()
        self.assertEqual(mutant._derive_due_status(store._maintenance[rec["id"]], date(2026, 11, 1)), "current")
        store.complete_maintenance(rec["id"], ADMIN, completed_date="2026-11-20")
        self.assertEqual(store._derive_due_status(store._maintenance[rec["id"]], date(2027, 1, 1)), "completed")
        self.assertEqual(mutant._derive_due_status(store._maintenance[rec["id"]], date(2027, 1, 1)), "completed")


if __name__ == "__main__":
    unittest.main()
