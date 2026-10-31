"""Core function 10: search and summary reporting.

Literal substring search (never regex) over registered records,
and a summary computed on read from records only: counts, and a
matches total that is a count of derived matches. A recursive key
scan pins the no-score discipline over summaries, match views, and
stored records (AU-2/AU-3 Low side; CM-6).
"""

import unittest

from events.errors import ValidationError

from events_helpers import (DURING, ADMIN, MEMBER, VIEWER, make_event,
                            make_organizer, make_round, make_store,
                            make_vendors)
from test_matches import scan_keys


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)
        self.vendors = make_vendors(self.store)
        self.event = make_event(self.store, self.organizer)
        self.store.record_outreach(
            MEMBER, self.organizer["id"], self.vendors[0]["id"],
            self.event["id"], "portal", "Invitation: Spring Vendor Day")

    def test_search_matches_labels_titles_subjects(self):
        found = self.store.search(VIEWER, "vendor day")
        self.assertEqual(len(found["events"]), 1)
        self.assertEqual(len(found["outreach"]), 1)
        found = self.store.search(VIEWER, "VENDOR CO")
        self.assertEqual(len(found["vendors"]), 3)
        found = self.store.search(VIEWER, "agency events")
        self.assertEqual(len(found["organizers"]), 1)

    def test_search_is_literal_not_regex(self):
        found = self.store.search(VIEWER, "vendor.*")
        self.assertEqual(found["vendors"], [])
        self.assertEqual(found["events"], [])

    def test_search_requires_a_query(self):
        with self.assertRaises(ValidationError):
            self.store.search(VIEWER, "")
        with self.assertRaises(ValidationError):
            self.store.search(VIEWER, None)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)
        self.va, self.vb, self.vc = make_vendors(self.store)
        self.event = make_event(self.store, self.organizer)
        later = self.store.create_event(
            ADMIN, self.organizer["id"], "Autumn Expo", "onsite",
            "2026-09-01T09:00:00+00:00", "2026-09-01T17:00:00+00:00")
        self.store.create_session(
            MEMBER, self.event["id"], "webinar", "Briefing",
            "2026-03-10T10:00:00+00:00", "2026-03-10T11:00:00+00:00")
        task = self.store.add_preparation_task(
            MEMBER, self.event["id"], "Confirm room")
        self.store.add_preparation_task(MEMBER, self.event["id"], "Print")
        self.store.complete_preparation_task(MEMBER, task["id"])
        self.store.record_outreach(
            MEMBER, self.organizer["id"], self.va["id"], self.event["id"],
            "portal", "Invitation")
        self.round = make_round(self.store, self.event)
        self.store.record_participation(
            MEMBER, self.round["id"], self.va["id"],
            ["cloud", "security", "support"])
        self.store.record_participation(
            MEMBER, self.round["id"], self.vb["id"], ["cloud"])
        self.store.record_participation(
            MEMBER, self.round["id"], self.vc["id"],
            ["security", "cloud", "onsite"])

    def test_summary_counts(self):
        summary = self.store.summary(VIEWER, now=DURING)
        self.assertEqual(summary["organizers"], 1)
        self.assertEqual(summary["vendors"], 3)
        self.assertEqual(summary["events_by_status"],
                         {"upcoming": 1, "live": 1, "concluded": 0})
        self.assertEqual(summary["events_by_format"],
                         {"onsite": 1, "hybrid": 1, "virtual": 0})
        self.assertEqual(summary["sessions_by_kind"],
                         {"webinar": 1, "roundtable": 0,
                          "speaker_engagement": 0})
        self.assertEqual(summary["preparation_open"], 1)
        self.assertEqual(summary["preparation_done"], 1)
        self.assertEqual(summary["outreach"], 1)
        self.assertEqual(summary["rounds_open"], 1)
        self.assertEqual(summary["rounds_closed"], 0)
        self.assertEqual(summary["participations"], 3)

    def test_matches_total_is_a_derived_count(self):
        summary = self.store.summary(VIEWER, now=DURING)
        self.assertEqual(summary["matches_total"], 2)

    def test_no_score_keys_anywhere(self):
        summary = self.store.summary(ADMIN, now=DURING)
        view = self.store.round_matches(ADMIN, self.round["id"])
        stored = list(self.store._events.values()) \
            + list(self.store._rounds.values()) \
            + list(self.store._participations.values())
        for obj in [summary, view] + stored:
            for key in scan_keys(obj):
                for word in ("score", "rank", "rating"):
                    self.assertNotIn(word, key.lower())


if __name__ == "__main__":
    unittest.main()
