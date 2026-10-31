"""Negative control: the suite must reject a mutant derivation.

Traces to: the contract's required negative control for Group 36.

The traced claim: **overdue derivation at read time** -- an overdue
open work order must read ``overdue=True`` (and never reads overdue
once completed/closed/cancelled, and a report at that ``now`` must
count it). The value is derived at read time by
``OpsStore._is_overdue``; it is never stored.

The mutant below is an OpsStore subclass overriding the single
derivation point so an overdue open work order NEVER reads overdue
(``_is_overdue`` always returns ``False``).

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation, and
(3) a literal assertRaises(AssertionError) showing that treating
the mutant's outcome as the expected outcome fails.
"""

import unittest

from opsmgmt_helpers import OPERATOR, fresh_store
from opsmgmt.audit import AuditLog
from opsmgmt.store import OpsStore

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"


class MutantOpsStore(OpsStore):
    """Mutant derivation: overdue derivation is suppressed."""

    def _is_overdue(self, work_order, now_dt):
        """Core 4: Work orders (negative control mutant) -- never overdue."""
        return False


def _make(store_cls):
    """Build a store of the given class with an overdue open work order.

    Traces to: Core 4 negative control -- shared fixture for
    canonical and mutant stores.
    """
    store = store_cls(audit=AuditLog())
    wo = store.create_work_order(OPERATOR, "task", "Overdue task", due_at=PAST)
    return store, wo


class TestNegativeControlMutantDerivation(unittest.TestCase):
    """Core 4: Work orders -- negative control for read-time
    derivation, traced claim: overdue derivation at read time."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 4 (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_overdue_work_order_overdue_canonical_but_mutant_not(self):
        """Core 4: Work orders, traced claim: overdue derivation at read time.
        Canonical: overdue open work order reads overdue=True at now,
        and the report counts it. Mutant: same setup reads
        overdue=False, and its report counts 0."""
        store, wo = _make(OpsStore)
        canonical = store.get_work_order(wo["id"], OPERATOR, now=NOW)
        self.assertTrue(canonical["overdue"])
        self.assertEqual(store.report(OPERATOR, now=NOW)["work_orders"]["overdue"], 1)

        mstore, mwo = _make(MutantOpsStore)
        mutant = mstore.get_work_order(mwo["id"], OPERATOR, now=NOW)
        self.assertFalse(mutant["overdue"])  # mutant did NOT derive overdue
        self.assertEqual(mstore.report(OPERATOR, now=NOW)["work_orders"]["overdue"], 0)
        self._assert_mutant_rejected(mutant["overdue"], True)

    def test_overdue_list_view_canonical_but_mutant_not(self):
        """Core 4: Work orders, traced claim: overdue derivation at read time.
        Canonical: the list view also derives overdue=True.
        Mutant: its list view reads overdue=False."""
        store, wo = _make(OpsStore)
        canonical = store.list_work_orders(OPERATOR, now=NOW)
        self.assertEqual(len(canonical), 1)
        self.assertTrue(canonical[0]["overdue"])

        mstore, mwo = _make(MutantOpsStore)
        mutant = mstore.list_work_orders(OPERATOR, now=NOW)
        self.assertEqual(len(mutant), 1)
        self.assertFalse(mutant[0]["overdue"])
        self._assert_mutant_rejected(mutant[0]["overdue"], True)


if __name__ == "__main__":
    unittest.main()
