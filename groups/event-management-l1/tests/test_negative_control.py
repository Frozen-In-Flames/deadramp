"""Mutation-verified negative control for the match derivation.

An oracle that passes under both inclusion directions is testing
that code ran, not that coverage is the rule. So the canonical
match expectation is asserted here against a MUTANT seam whose
``_derive_matches`` reverses the inclusion -- a participation
qualifies when its tags are a SUBSET of the required tags -- and
the test asserts the canonical check FAILS against the mutant.
If the canonical match tests ever stopped discriminating -- if
they would pass against the mutant -- this test fails.

The external drill (the same patch applied to the real
``src/events/store.py``, suite re-run, file restored
byte-identical) is recorded in tests/README.md and
scratch/mutation-run.txt.
"""

import unittest

import events.store as store_module

from events_helpers import (ADMIN, MEMBER, make_event, make_organizer,
                            make_store, make_vendors)


def _mutant_matches(participations, required_tags):
    """Mutant: inclusion reversed -- the participation's tags must
    be a subset of the required tags."""
    required = set(required_tags)
    ordered = sorted(participations, key=lambda p: p["seq"])
    return [p for p in ordered
            if set(p["capability_tags"]).issubset(required)]


def canonical_coverage_matches(store, round_id, vendors):
    """The match suite's core expectation, stated once.

    Raises AssertionError when the store's match derivation does
    not select exactly the participations whose tags cover the
    round's required tags, in sequence order.
    """
    va, vb, vc = vendors
    store.record_participation(MEMBER, round_id, va["id"],
                               ["cloud", "security", "support"])
    store.record_participation(MEMBER, round_id, vb["id"], ["cloud"])
    store.record_participation(MEMBER, round_id, vc["id"],
                               ["security", "cloud"])
    view = store.round_matches(ADMIN, round_id)
    assert view["match_count"] == 2, (
        "match_count is %s, expected 2" % (view["match_count"],))
    assert [m["vendor_id"] for m in view["matches"]] == [va["id"], vc["id"]], (
        "matches are %s, expected the two covering vendors in "
        "sequence order" % ([m["vendor_id"] for m in view["matches"]],))


class NegativeControlTests(unittest.TestCase):
    def _fixture(self):
        store, _audit = make_store()
        organizer = make_organizer(store)
        vendors = make_vendors(store)
        event = make_event(store, organizer)
        round_ = store.create_round(ADMIN, event["id"],
                                    ["cloud", "security"])
        return store, round_, vendors

    def test_canonical_check_passes_on_the_real_store(self):
        store, round_, vendors = self._fixture()
        canonical_coverage_matches(store, round_["id"], vendors)

    def test_canonical_check_fails_on_the_mutant(self):
        store, round_, vendors = self._fixture()
        original = store_module._derive_matches
        store_module._derive_matches = _mutant_matches
        try:
            with self.assertRaises(AssertionError):
                canonical_coverage_matches(store, round_["id"], vendors)
        finally:
            store_module._derive_matches = original

    def test_exact_tag_participation_qualifies_under_both(self):
        """Honesty pin: an exactly-matching participation satisfies
        both inclusion directions, so it cannot be what discriminates.
        The discrimination lives in the superset/subset pair of the
        canonical fixture -- which is why the fixture is built the
        way it is."""
        store, round_, vendors = self._fixture()
        va = vendors[0]
        store.record_participation(MEMBER, round_["id"], va["id"],
                                   ["cloud", "security"])
        real = store.round_matches(ADMIN, round_["id"])
        self.assertEqual(real["match_count"], 1)
        original = store_module._derive_matches
        store_module._derive_matches = _mutant_matches
        try:
            mutant = store.round_matches(ADMIN, round_["id"])
            self.assertEqual(mutant["match_count"], 1)
        finally:
            store_module._derive_matches = original


ORACLE_EXPECTED = (
    "External drill (patch _derive_matches in src/events/store.py "
    "to reverse the inclusion -- participation tags subset of the "
    "required tags -- re-run the suite, restore): exactly 6 test "
    "failures -- test_matches.MatchTests.test_coverage_rule, "
    "test_matches.MatchTests."
    "test_empty_required_tags_admits_every_participation, "
    "test_matches.MatchTests.test_match_is_derived_not_stored, "
    "test_negative_control.NegativeControlTests."
    "test_canonical_check_passes_on_the_real_store, "
    "test_reporting.SummaryTests.test_matches_total_is_a_derived_count, "
    "test_service.ServiceTests.test_full_flow -- then the file "
    "restored byte-identical (SHA-256 verified) and the full suite "
    "green again. Recorded in tests/README.md and "
    "scratch/mutation-run.txt."
)

if __name__ == "__main__":
    unittest.main()
