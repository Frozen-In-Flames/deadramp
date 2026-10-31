"""Core function 9: match derivation -- THE SIGNATURE INVARIANT.

Claim traced: business_matchmaking. A round's matches are the
participations whose recorded capability tags COVER the round's
recorded required tags (set inclusion), derived at read by the
single seam ``_derive_matches`` and never stored. Coverage is a
yes-or-no fact about recorded tags: no score, rating, or ranking
of any vendor is computed anywhere -- pinned here by a recursive
key scan.
"""

import unittest

from events_helpers import (ADMIN, MEMBER, VIEWER, make_event,
                            make_organizer, make_round, make_store,
                            make_vendors)

ROUND_KEYS = {"id", "event_id", "required_tags", "status",
              "created_by", "created_utc"}


def scan_keys(obj, path=""):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= scan_keys(value, path + "/" + str(key))
    elif isinstance(obj, list):
        for value in obj:
            keys |= scan_keys(value, path)
    return keys


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)
        self.va, self.vb, self.vc = make_vendors(self.store)
        self.event = make_event(self.store, self.organizer)
        self.round = make_round(self.store, self.event)

    def seed_participations(self):
        self.store.record_participation(
            MEMBER, self.round["id"], self.va["id"],
            ["cloud", "security", "support"])
        self.store.record_participation(
            MEMBER, self.round["id"], self.vb["id"], ["cloud"])
        self.store.record_participation(
            MEMBER, self.round["id"], self.vc["id"],
            ["security", "cloud"])

    def test_coverage_rule(self):
        self.seed_participations()
        view = self.store.round_matches(VIEWER, self.round["id"])
        self.assertEqual(view["match_count"], 2)
        self.assertEqual(view["participation_count"], 3)
        self.assertEqual([m["vendor_id"] for m in view["matches"]],
                         [self.va["id"], self.vc["id"]])
        self.assertEqual(view["required_tags"], ["cloud", "security"])

    def test_match_is_derived_not_stored(self):
        stored = self.store._rounds[self.round["id"]]
        self.assertEqual(set(stored), ROUND_KEYS)
        self.assertNotIn("matches", stored)
        self.store.record_participation(
            MEMBER, self.round["id"], self.va["id"],
            ["cloud", "security"])
        first = self.store.round_matches(ADMIN, self.round["id"])
        self.assertEqual(first["match_count"], 1)
        # A participation recorded after the first read changes the
        # next read: the matches were derived, not stored.
        self.store.record_participation(
            MEMBER, self.round["id"], self.vc["id"],
            ["cloud", "security", "onsite"])
        second = self.store.round_matches(ADMIN, self.round["id"])
        self.assertEqual(second["match_count"], 2)

    def test_empty_required_tags_admits_every_participation(self):
        open_round = self.store.create_round(ADMIN, self.event["id"], [])
        self.store.record_participation(
            MEMBER, open_round["id"], self.va["id"], ["anything"])
        self.store.record_participation(
            MEMBER, open_round["id"], self.vb["id"], [])
        view = self.store.round_matches(VIEWER, open_round["id"])
        self.assertEqual(view["match_count"], 2)

    def test_matches_survive_round_close(self):
        self.seed_participations()
        self.store.close_round(ADMIN, self.round["id"])
        view = self.store.round_matches(VIEWER, self.round["id"])
        self.assertEqual(view["round_status"], "closed")
        self.assertEqual(view["match_count"], 2)

    def test_no_score_anywhere(self):
        self.seed_participations()
        view = self.store.round_matches(ADMIN, self.round["id"])
        for key in scan_keys(view):
            for word in ("score", "rank", "rating", "percent", "quality"):
                self.assertNotIn(word, key.lower())
        for match in view["matches"]:
            self.assertEqual(set(match), {"participation_id", "vendor_id",
                                          "capability_tags"})

    def test_no_participations_no_matches(self):
        view = self.store.round_matches(VIEWER, self.round["id"])
        self.assertEqual(view["match_count"], 0)
        self.assertEqual(view["matches"], [])


if __name__ == "__main__":
    unittest.main()
