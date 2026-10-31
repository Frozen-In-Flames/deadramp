"""Negative control: the suite must reject a mutant derivation.

Traces to: the contract's required negative control, reused from
Group 25 (CRM L2) with its traced claim re-anchored for this tier
(documentation only, no logic changed; see
``../scratch/reuse-note.md``).

The traced claim: **breach derivation at read time** -- an overdue
open case must read ``breached=True`` (and a report at that ``now``
must count it breached), and it must never read breached once
resolved/closed/cancelled. The value is derived at read time by
``CrmStore._is_breached``; it is never stored. At this tier the
derivation stands as a design property of the carried substrate:
this singleton's fork claims no case function (its single claim is
the AI family, Extended), so the rule is the substrate's own,
traced to CM-6 / AU-2 at the Low baseline in UNION-SPEC.md rather
than to a sibling's evidenced claim.

The mutant below is a CrmStore subclass overriding the derivation
point so an overdue open case NEVER reads breached.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation, and
(3) a literal assertRaises(AssertionError) showing that treating
the mutant's outcome as the expected outcome fails.
"""

import unittest

import crm_helpers as H
from crm.audit import AuditLog
from crm.store import CrmStore

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"


class MutantCrmStore(CrmStore):
    """Mutant derivation: breach derivation is suppressed."""

    def _is_breached(self, case, now_dt):
        """Core 2: Cases (negative control mutant) -- never breached."""
        return False


def _make(store_cls):
    """Build a store of the given class with one overdue open case.

    Traces to: Core 2 negative control -- shared fixture for
    canonical and mutant stores.
    """
    store = store_cls(audit=AuditLog())
    case = store.create_case(H.OPERATOR, "problem", "Overdue case", due_at=PAST)
    return store, case


class TestNegativeControlMutantDerivation(unittest.TestCase):
    """Core 2: Cases -- negative control for read-time derivation,
    traced claim: breach derivation at read time."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 2 (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_overdue_case_breached_canonical_but_mutant_not(self):
        """Core 2: Cases, traced claim: breach derivation at read time.
        Canonical: overdue open case reads breached=True at now, and
        the report counts it. Mutant: same setup reads breached=False
        and its report counts zero."""
        store, case = _make(CrmStore)
        canonical = store.get_case(case["id"], H.OPERATOR, now=NOW)
        self.assertTrue(canonical["breached"])
        self.assertEqual(store.report(H.OPERATOR, now=NOW)["cases"]["breached"], 1)

        mstore, mcase = _make(MutantCrmStore)
        mutant = mstore.get_case(mcase["id"], H.OPERATOR, now=NOW)
        self.assertFalse(mutant["breached"])  # mutant did NOT derive breach
        self.assertEqual(mstore.report(H.OPERATOR, now=NOW)["cases"]["breached"], 0)
        self._assert_mutant_rejected(mutant["breached"], True)


if __name__ == "__main__":
    unittest.main()
