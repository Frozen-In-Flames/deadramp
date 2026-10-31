"""Core functions 2 and 3: opportunity records (the records form
of the forks' discovery claims) and evaluation records — decisions
from a fixed vocabulary, with no score field anywhere (taxonomy
families opportunity_discovery / opportunity_evaluation)."""

import unittest

from marketsales_helpers import (ADMIN, DUE, OPERATOR, POSTED,
                                 make_opportunity, make_org, make_store)

from marketsales.errors import NotFoundError, ValidationError


class OpportunityTests(unittest.TestCase):
    def setUp(self):
        self.store, _audit = make_store()
        self.org = make_org(self.store)

    def test_create_and_read_back(self):
        opp = make_opportunity(self.store, self.org)
        self.assertEqual(opp["id"], "opp-1")
        self.assertEqual(opp["posted_at"], POSTED)
        self.assertEqual(opp["due_at"], DUE)
        fetched = self.store.get_opportunity(ADMIN, "opp-1")
        self.assertEqual(fetched["title_label"],
                         "Widget services IDIQ recompete")

    def test_ref_unique_per_organization(self):
        make_opportunity(self.store, self.org)
        with self.assertRaises(ValidationError):
            make_opportunity(self.store, self.org)
        other = self.store.create_organization(ADMIN, "ORG-2", "two")
        opp = make_opportunity(self.store, other)
        self.assertEqual(opp["org_id"], other["id"])

    def test_unknown_organization_and_opportunity(self):
        with self.assertRaises(NotFoundError):
            self.store.create_opportunity(OPERATOR, "org-99", "R", "A",
                                          "T", POSTED)
        with self.assertRaises(NotFoundError):
            self.store.get_opportunity(ADMIN, "opp-99")

    def test_bad_moments_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.store.create_opportunity(OPERATOR, self.org["id"], "R",
                                          "A", "T", "not-a-date")
        opp = make_opportunity(self.store, self.org)
        self.assertEqual(opp["id"], "opp-1")

    def test_list_filter_by_org(self):
        make_opportunity(self.store, self.org)
        other = self.store.create_organization(ADMIN, "ORG-2", "two")
        self.assertEqual(
            len(self.store.list_opportunities(ADMIN, org_id=other["id"])), 0)
        self.assertEqual(len(self.store.list_opportunities(ADMIN)), 1)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.store, _audit = make_store()
        self.org = make_org(self.store)
        self.opp = make_opportunity(self.store, self.org)

    def test_record_decisions(self):
        for decision in ("pursue", "watch", "no_pursue"):
            record = self.store.record_evaluation(
                OPERATOR, self.opp["id"], "EVALUATOR-REF-1", decision)
            self.assertEqual(record["decision"], decision)
        records = self.store.list_evaluations(
            ADMIN, opportunity_id=self.opp["id"])
        self.assertEqual(len(records), 3)

    def test_decision_vocabulary_enforced(self):
        with self.assertRaises(ValidationError):
            self.store.record_evaluation(
                OPERATOR, self.opp["id"], "EVALUATOR-REF-1", "definitely")

    def test_evaluation_requires_a_real_opportunity(self):
        with self.assertRaises(NotFoundError):
            self.store.record_evaluation(
                OPERATOR, "opp-99", "EVALUATOR-REF-1", "pursue")

    def test_no_score_shaped_field_exists(self):
        record = self.store.record_evaluation(
            OPERATOR, self.opp["id"], "EVALUATOR-REF-1", "pursue",
            note="fits the capture profile")
        for key in record:
            self.assertNotIn("score", key)
            self.assertNotIn("grade", key)
            self.assertNotIn("fit", key)
            self.assertNotIn("rank", key)


if __name__ == "__main__":
    unittest.main()
