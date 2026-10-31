"""Mutation-verified negative control around the small-cohort
guard derivation (the core's signature invariant).

The canonical expectation -- recording an insight snapshot for a
cohort below :data:`MIN_COHORT_SIZE` is refused and records
nothing -- is written once, as a plain function over a store.
One test proves the canonical expectation holds against the real
derivation in :mod:`talentdev.store`. A second test monkeypatches
the derivation seam (:func:`talentdev.store._check_cohort_allowed`)
with a mutant that allows every cohort and asserts the *same*
canonical check then fails with ``AssertionError`` -- proving the
check exercises the real seam and is not a tautology. A third
test proves the guard is a floor, not a ban: a cohort at exactly
:data:`MIN_COHORT_SIZE` records fine on the real store.

The external drill (patch the seam in the source file, run the
whole suite, record the failures, restore byte-identical) is
documented in tests/README.md.
"""

import unittest

import talentdev.store as store_module
from talentdev.errors import ValidationError
from talentdev.store import MIN_COHORT_SIZE
from talentdev_helpers import ADMIN, make_org, make_store

BELOW_FLOOR = MIN_COHORT_SIZE - 1


def canonical_cohort_check(store):
    """The canonical expectation, written once: a snapshot below
    the cohort floor is refused and leaves no record behind."""
    org = make_org(store)
    try:
        store.record_snapshot(ADMIN, org["id"], "trend-index", "2026-Q4",
                              BELOW_FLOOR, 1)
    except ValidationError:
        pass
    else:
        raise AssertionError(
            "a snapshot over a cohort of %d (below the floor of %d) "
            "was recorded; the small-cohort guard did not refuse it"
            % (BELOW_FLOOR, MIN_COHORT_SIZE))
    assert store.list_snapshots(ADMIN) == [], (
        "the refused snapshot left a record behind")


class TestNegativeControl(unittest.TestCase):
    def test_canonical_check_passes_on_the_real_derivation(self):
        store, _audit = make_store()
        canonical_cohort_check(store)

    def test_canonical_check_fails_on_the_mutant(self):
        store, _audit = make_store()
        original = store_module._check_cohort_allowed
        store_module._check_cohort_allowed = lambda cohort_size: None
        try:
            with self.assertRaises(AssertionError):
                canonical_cohort_check(store)
        finally:
            store_module._check_cohort_allowed = original

    def test_cohort_at_the_floor_records_fine(self):
        # The discriminating other arm: the guard is a floor, not a
        # ban. A cohort of exactly MIN_COHORT_SIZE records.
        store, _audit = make_store()
        org = make_org(store)
        snapshot = store.record_snapshot(
            ADMIN, org["id"], "trend-index", "2026-Q4",
            MIN_COHORT_SIZE, 2)
        self.assertEqual(snapshot["cohort_size"], MIN_COHORT_SIZE)
        self.assertEqual(len(store.list_snapshots(ADMIN)), 1)


if __name__ == "__main__":
    unittest.main()
