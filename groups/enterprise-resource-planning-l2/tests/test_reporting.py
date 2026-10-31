"""Core function 15: search & summary reporting (AU-2/AU-3,
AC-3).

Search is a literal substring match over record metadata. The
summary is counts and recorded values computed on read; a
recursive key scan proves no key anywhere in it (or in any
record view) could hold a score, rating, or ranking.
"""

import unittest

from erp_helpers import (ADMIN, OPERATOR, PERSON_REF, make_entry,
                         make_org, make_person, make_store)

FORBIDDEN_KEY_PARTS = ("score", "rating", "rank", "grade")


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.store, _ = make_store()
        self.org = make_org(self.store)
        make_person(self.store, self.org)
        make_entry(self.store, self.org)
        self.store.create_asset(OPERATOR, self.org["id"], "ASSET-1",
                                "Pump station 4", "High (label)")
        self.store.create_document(OPERATOR, self.org["id"], "DOC-1",
                                   "Vendor agreement (label)",
                                   "Procurement (label)")

    def test_search_matches_metadata_literally(self):
        hits = self.store.search(OPERATOR, "pump")
        self.assertEqual(len(hits["assets"]), 1)
        self.assertEqual(hits["persons"], [])
        hits = self.store.search(OPERATOR, "finance")
        self.assertEqual(len(hits["persons"]), 1)
        hits = self.store.search(OPERATOR, "PERSON-0001")
        self.assertEqual(len(hits["persons"]), 1)
        hits = self.store.search(OPERATOR, "no-such-thing")
        self.assertTrue(all(not v for v in hits.values()))

    def test_summary_counts_records(self):
        summary = self.store.summary(ADMIN)
        self.assertEqual(summary["organizations"], 1)
        self.assertEqual(summary["persons"], 1)
        self.assertEqual(summary["ledger_entries"], 1)
        self.assertEqual(summary["assets"], 1)
        self.assertEqual(summary["documents"], 1)
        self.assertEqual(summary["purchase_orders"], 0)
        self.assertEqual(summary["integrations_by_kind"],
                         {"integration_platform": 0, "api_gateway": 0})

    def test_no_score_field_anywhere(self):
        views = [
            self.store.summary(ADMIN),
            self.store.search(OPERATOR, "a"),
            self.store.list_ledger_entries(OPERATOR),
            self.store.list_persons(OPERATOR),
        ]
        for view in views:
            for key in _all_keys(view):
                for part in FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(part, key.lower(),
                                     "view carries key %r" % key)


if __name__ == "__main__":
    unittest.main()
