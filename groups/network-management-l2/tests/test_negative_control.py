"""Negative control: the derived-status invariant must be
load-bearing.

The group's signature invariant is that a device's freshness
status is *derived at read* -- fresh when its latest telemetry
record is within 24 hours of the read clock, stale when older,
unknown when it has none -- computed from the telemetry records
every time, never stored. The canonical expectations use the
fixture reading recorded 2026-06-01T08:00:00+00:00: at
2026-06-01T20:00:00+00:00 the device is fresh, at
2026-06-03T08:00:00+00:00 it is stale. The mutant is a
NetmgmtStore subclass whose derivation always reports ``fresh``:
if the suite still passed against the mutant, the device tests
would be testing that code ran, not that the derivation holds.
(The budget sibling group verified the same derivation discipline
with the same drill shape.)
"""

import unittest

import netmgmt_helpers as H
from netmgmt.store import NetmgmtStore


class MutantNetmgmtStore(NetmgmtStore):
    """A store whose freshness derivation always reports fresh."""

    def _derive_device_status(self, device, as_of_dt):
        return "fresh"


def _fixture(store):
    org = H.make_org(store)
    store.add_member(H.ADMIN, org["id"], H.STAFF.name)
    network, device = H.make_estate(store, org)
    H.make_telemetry(store, org, device)
    return org, device


class TestNegativeControlDerivedStatus(unittest.TestCase):
    def test_canonical_expectation(self):
        """Canonical: the fixture reading is fresh 12h after it was
        recorded and stale 48h after it was recorded."""
        store = H.fresh_store()
        org, device = _fixture(store)
        fresh = store.get_device(H.MEMBER, device["id"],
                                 as_of=H.AS_OF_FRESH)
        self.assertEqual(fresh["derived_status"], "fresh")
        stale = store.get_device(H.MEMBER, device["id"],
                                 as_of=H.AS_OF_STALE)
        self.assertEqual(stale["derived_status"], "stale")

    def test_implementation_matches_canonical_in_summary(self):
        """Implementation: the org summary's derived-status counts
        (as_of = now, long after the June 2026 fixture reading)
        agree with the same derivation, not a stored status."""
        store = H.fresh_store()
        org, device = _fixture(store)
        summary = store.organization_summary(H.MEMBER, org["id"])
        self.assertEqual(
            summary["devices_by_derived_status"],
            {"fresh": 0, "stale": 1, "unknown": 0})

    def test_mutant_would_not_derive(self):
        """Mutant: with the derivation stubbed to always report
        fresh, the device reads fresh at the stale read clock --
        so the canonical expectation, applied to the mutant's
        output, fails (asserted literally)."""
        store = MutantNetmgmtStore()
        org, device = _fixture(store)
        view = store.get_device(H.MEMBER, device["id"],
                                as_of=H.AS_OF_STALE)
        self.assertEqual(view["derived_status"], "fresh")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["derived_status"], "stale")


if __name__ == "__main__":
    unittest.main()
