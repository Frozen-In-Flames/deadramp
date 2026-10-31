"""Negative control: the grant-status derivation must be
load-bearing.

The group's signature invariant is that a grant's status is
derived at read from its start, expiry, and revocation timestamp
— never stored. The canonical expectation is that a grant whose
window has ended reads ``expired`` and a revoked grant reads
``revoked``. The mutant is a ResearchStore subclass whose
``_derive_grant_status`` always returns ``"active"``: if the
suite still passed against the mutant, the derivation tests
would be testing that code ran, not that the derivation holds.
"""

import unittest

import research_helpers as H
from research.store import ResearchStore


class MutantResearchStore(ResearchStore):
    """A store with grant-status derivation removed (the mutant)."""

    def _derive_grant_status(self, grant, moment):
        return "active"


def _fixture(store):
    commons = H.make_commons(store)
    store.add_member(H.ADMIN, commons["id"], H.STAFF.name)
    dataset = H.make_dataset(store, commons)
    return commons, dataset


def _grant(store, commons, dataset, **overrides):
    return H.make_grant(store, commons, dataset, starts_at=H.T0,
                        duration_days=30, **overrides)


class TestNegativeControlGrantDerivation(unittest.TestCase):
    def test_canonical_expired_grant_reads_expired(self):
        """Canonical: a 30-day grant from T0 reads "expired" once
        the read clock is past its expiry."""
        store = H.fresh_store()
        commons, dataset = _fixture(store)
        grant = _grant(store, commons, dataset)
        view = store.get_grant(H.MEMBER, grant["id"], now=H.AFTER_EXPIRY)
        self.assertEqual(view["status"], "expired")

    def test_canonical_revoked_grant_reads_revoked(self):
        """Canonical: a revoked grant reads "revoked" at a read
        clock inside its (otherwise active) window."""
        store = H.fresh_store()
        commons, dataset = _fixture(store)
        grant = _grant(store, commons, dataset)
        store.revoke_grant(H.STAFF, grant["id"])
        view = store.get_grant(H.MEMBER, grant["id"], now=H.INSIDE_WINDOW)
        self.assertEqual(view["status"], "revoked")

    def test_mutant_reports_expired_and_revoked_as_active(self):
        """Mutant: with derivation replaced by a constant "active",
        the same expired and revoked grants read "active" — so the
        canonical expectations, applied to the mutant's output,
        fail (asserted literally with assertRaises)."""
        store = MutantResearchStore()
        commons, dataset = _fixture(store)

        expired = _grant(store, commons, dataset)
        view = store.get_grant(H.MEMBER, expired["id"], now=H.AFTER_EXPIRY)
        self.assertEqual(view["status"], "active")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["status"], "expired")

        revoked = _grant(store, commons, dataset,
                         purpose="Second planned analysis")
        store.revoke_grant(H.STAFF, revoked["id"])
        view = store.get_grant(H.MEMBER, revoked["id"],
                               now=H.INSIDE_WINDOW)
        self.assertEqual(view["status"], "active")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["status"], "revoked")


if __name__ == "__main__":
    unittest.main()
