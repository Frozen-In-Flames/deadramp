"""Core function 7: supervision review records -- an event-driven
lifecycle (pending -> reviewed / escalated -> reviewed) changed
only by recorded outcomes; ``reviewed`` is terminal.
"""

import unittest

from storage.errors import NotFoundError, ValidationError

from storage_helpers import (ADMIN, OPERATOR, make_archive, make_message,
                             make_store)


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)
        self.message = make_message(self.store, self.collection)
        self.review = self.store.create_review(
            OPERATOR, self.message["id"], "REVIEWER-REF-1")

    def test_create_shape(self):
        self.assertEqual(self.review["status"], "pending")
        self.assertEqual(self.review["message_id"], self.message["id"])
        self.assertIsNone(self.review["note"])
        with self.assertRaises(NotFoundError):
            self.store.create_review(OPERATOR, "msg-99", "REVIEWER-REF-1")
        with self.assertRaises(ValidationError):
            self.store.create_review(OPERATOR, self.message["id"], "")

    def test_reviewed_is_terminal(self):
        done = self.store.record_review_outcome(
            OPERATOR, self.review["id"], "reviewed", note="no action")
        self.assertEqual(done["status"], "reviewed")
        self.assertEqual(done["note"], "no action")
        self.assertEqual(done["outcome_by"], "bob")
        with self.assertRaises(ValidationError):
            self.store.record_review_outcome(
                OPERATOR, self.review["id"], "escalated")

    def test_escalation_path(self):
        escalated = self.store.record_review_outcome(
            OPERATOR, self.review["id"], "escalated")
        self.assertEqual(escalated["status"], "escalated")
        with self.assertRaises(ValidationError):
            self.store.record_review_outcome(
                OPERATOR, self.review["id"], "escalated")
        done = self.store.record_review_outcome(
            ADMIN, self.review["id"], "reviewed")
        self.assertEqual(done["status"], "reviewed")

    def test_outcome_validation(self):
        with self.assertRaises(ValidationError):
            self.store.record_review_outcome(
                OPERATOR, self.review["id"], "ignored")
        with self.assertRaises(NotFoundError):
            self.store.record_review_outcome(OPERATOR, "sup-99", "reviewed")
        still = self.store.list_reviews(ADMIN, status="pending")
        self.assertEqual([r["id"] for r in still], [self.review["id"]])

    def test_list_filters(self):
        self.store.record_review_outcome(OPERATOR, self.review["id"],
                                         "reviewed")
        self.assertEqual(
            self.store.list_reviews(ADMIN, message_id=self.message["id"],
                                    status="reviewed")[0]["id"],
            self.review["id"])
        with self.assertRaises(ValidationError):
            self.store.list_reviews(ADMIN, status="closed")


if __name__ == "__main__":
    unittest.main()
