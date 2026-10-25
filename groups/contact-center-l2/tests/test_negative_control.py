"""Negative control: the suite must reject a mutant derivation.

Traces to: the contract's required negative control for Group 15.

The traced claim: **breach/state derivation at read time** -- an
overdue open case must read ``breached=True`` (and never reads
breached once resolved/closed/cancelled), and an overdue scheduled
callback must read ``state='overdue'`` while its stored ``status``
stays ``scheduled``. Both values are derived at read time by
``ContactStore._is_breached`` / ``ContactStore._callback_state``;
they are never stored.

The mutant below is a ContactStore subclass overriding both
derivation points so an overdue open case NEVER reads breached and
an overdue callback NEVER reads overdue (it always reads
``scheduled``).

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation,
(2) the mutant would NOT produce that expectation, and
(3) a literal assertRaises(AssertionError) showing that treating
the mutant's outcome as the expected outcome fails.
"""

import unittest

from contact_helpers import OPERATOR, fresh_store
from contact.store import ContactStore

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"


class MutantContactStore(ContactStore):
    """Mutant derivation: breach/state derivation is suppressed."""

    def _is_breached(self, case, now_dt):
        """Core 3: Cases (negative control mutant) -- never breached."""
        return False

    def _callback_state(self, callback, now_dt):
        """Core 4: Callbacks (negative control mutant) -- never overdue."""
        if callback["status"] in ("completed", "cancelled"):
            return callback["status"]
        return "scheduled"


def _make(store_cls):
    """Build a store of the given class with an overdue open case and
    an overdue scheduled callback.

    Traces to: Core 3/4 negative control -- shared fixture for
    canonical and mutant stores.
    """
    from contact.audit import AuditLog
    store = store_cls(audit=AuditLog())
    contact = store.create_contact("Casey", OPERATOR, reference="EXT-1")
    case = store.create_case(OPERATOR, "claim", "Overdue claim", due_at=PAST)
    cb = store.schedule_callback(OPERATOR, contact["id"], PAST)
    return store, case, cb


class TestNegativeControlMutantDerivation(unittest.TestCase):
    """Core 3/4: Cases/Callbacks -- negative control for read-time
    derivation, traced claim: breach/state derivation at read time."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core 3/4 (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_overdue_case_breached_canonical_but_mutant_not(self):
        """Core 3: Cases, traced claim: breach derivation at read time.
        Canonical: overdue open case reads breached=True at now.
        Mutant: same setup reads breached=False."""
        store, case, cb = _make(ContactStore)
        canonical = store.get_case(case["id"], OPERATOR, now=NOW)
        self.assertTrue(canonical["breached"])
        self.assertEqual(store.report(OPERATOR, now=NOW)["cases"]["breached"], 1)

        mstore, mcase, mcb = _make(MutantContactStore)
        mutant = mstore.get_case(mcase["id"], OPERATOR, now=NOW)
        self.assertFalse(mutant["breached"])  # mutant did NOT derive breach
        self.assertEqual(mstore.report(OPERATOR, now=NOW)["cases"]["breached"], 0)
        self._assert_mutant_rejected(mutant["breached"], True)

    def test_overdue_callback_overdue_canonical_but_mutant_not(self):
        """Core 4: Callbacks, traced claim: state derivation at read time.
        Canonical: overdue scheduled callback reads state='overdue'.
        Mutant: same setup reads state='scheduled'."""
        store, case, cb = _make(ContactStore)
        canonical = store.get_callback(cb["id"], OPERATOR, now=NOW)
        self.assertEqual(canonical["state"], "overdue")
        self.assertEqual(canonical["status"], "scheduled")
        self.assertEqual(
            store.report(OPERATOR, now=NOW)["callbacks"]["by_state"], {"overdue": 1})

        mstore, mcase, mcb = _make(MutantContactStore)
        mutant = mstore.get_callback(mcb["id"], OPERATOR, now=NOW)
        self.assertEqual(mutant["state"], "scheduled")  # mutant did NOT derive overdue
        self.assertEqual(mutant["status"], "scheduled")
        self._assert_mutant_rejected(mutant["state"], "overdue")


if __name__ == "__main__":
    unittest.main()
