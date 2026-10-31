"""Core function 12: search & summary. Search is literal substring
matching over record metadata (there is no content in this store
to search). The summary is counts and recorded values computed on
read -- never scores, pinned by a recursive key scan.
"""

import unittest

from storage_helpers import (ADMIN, AFTER_BOUNDARY, BEFORE_BOUNDARY,
                             OPERATOR, make_archive, make_message,
                             make_store)


def scan_no_scores(obj, path="root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            assert "score" not in key.lower(), "%s.%s" % (path, key)
            assert "rating" not in key.lower(), "%s.%s" % (path, key)
            assert "rank" not in key.lower(), "%s.%s" % (path, key)
            scan_no_scores(value, "%s.%s" % (path, key))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            scan_no_scores(value, "%s[%d]" % (path, i))


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)
        self.message = make_message(self.store, self.collection)

    def test_search_over_metadata(self):
        found = self.store.search(ADMIN, "sender-ref-1")
        self.assertEqual([m["id"] for m in found["messages"]],
                         [self.message["id"]])
        found = self.store.search(ADMIN, "recip-ref-2")
        self.assertEqual(len(found["messages"]), 1)
        found = self.store.search(ADMIN, "correspondence")
        self.assertEqual(len(found["collections"]), 1)
        self.assertEqual(len(found["organizations"]), 0)
        found = self.store.search(ADMIN, "retention")
        self.assertEqual(len(found["policies"]), 1)
        found = self.store.search(ADMIN, "RECIP-REF-1")
        self.assertEqual(len(found["messages"]), 1)  # case-insensitive

    def test_search_is_literal_not_regex(self):
        found = self.store.search(ADMIN, "MSG.*")
        self.assertEqual(found["messages"], [])
        from storage.errors import ValidationError
        with self.assertRaises(ValidationError):
            self.store.search(ADMIN, "")

    def test_summary_counts(self):
        summary = self.store.summary(ADMIN, now=BEFORE_BOUNDARY)
        self.assertEqual(summary["organizations"], 1)
        self.assertEqual(summary["policies"], 1)
        self.assertEqual(summary["collections"], 1)
        self.assertEqual(summary["messages"], 1)
        self.assertEqual(summary["messages_by_retention_state"],
                         {"retained": 1, "disposition_eligible": 0,
                          "disposed": 0})
        self.assertEqual(summary["dispositions"], 0)
        self.assertEqual(summary["integrations_by_kind"],
                         {"mail_platform": 0, "directory": 0})

    def test_summary_retention_counts_follow_the_clock(self):
        summary = self.store.summary(ADMIN, now=AFTER_BOUNDARY)
        self.assertEqual(
            summary["messages_by_retention_state"]["disposition_eligible"],
            1)
        self.store.record_disposition(ADMIN, self.message["id"],
                                      "shredded", at=AFTER_BOUNDARY)
        summary = self.store.summary(ADMIN, now=BEFORE_BOUNDARY)
        self.assertEqual(
            summary["messages_by_retention_state"]["disposed"], 1)
        self.assertEqual(summary["dispositions"], 1)

    def test_summary_activity_counts(self):
        self.store.record_discovery(OPERATOR, "MATTER-1",
                                    self.collection["id"])
        review = self.store.create_review(OPERATOR, self.message["id"],
                                          "REVIEWER-1")
        self.store.record_review_outcome(OPERATOR, review["id"],
                                         "escalated")
        self.store.record_enforcement(OPERATOR, "flag_for_review", "T", "P")
        retrieval = self.store.create_retrieval(
            OPERATOR, self.message["id"], "realtime", "interface", "R")
        self.store.complete_retrieval(OPERATOR, retrieval["id"])
        summary = self.store.summary(ADMIN, now=BEFORE_BOUNDARY)
        self.assertEqual(summary["discoveries"], 1)
        self.assertEqual(summary["supervision_by_status"],
                         {"pending": 0, "reviewed": 0, "escalated": 1})
        self.assertEqual(summary["enforcement_actions"], 1)
        self.assertEqual(summary["retrievals"], 1)
        self.assertEqual(summary["retrievals_completed"], 1)

    def test_no_scores_anywhere(self):
        self.store.record_discovery(OPERATOR, "MATTER-1",
                                    self.collection["id"])
        scan_no_scores(self.store.summary(ADMIN, now=BEFORE_BOUNDARY))
        scan_no_scores(self.store.search(ADMIN, "MSG"))
        scan_no_scores(self.store.list_messages(ADMIN))
        scan_no_scores(self.store._messages[self.message["id"]])


if __name__ == "__main__":
    unittest.main()
