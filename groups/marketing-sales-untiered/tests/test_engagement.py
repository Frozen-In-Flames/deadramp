"""Core functions 12 and 13: engagement records, the engagement
report (derived counts only — never rates or scores), search, and
the summary (taxonomy family engagement_reporting)."""

import unittest

from marketsales_helpers import (ADMIN, CONTACT_A, CONTACT_B, OCCURRED,
                                 OPERATOR, make_campaign, make_org,
                                 make_store)

from marketsales.errors import ValidationError


class EngagementTests(unittest.TestCase):
    def setUp(self):
        self.store, _audit = make_store()
        self.org = make_org(self.store)
        self.campaign, self.contact_list, _seg = make_campaign(
            self.store, self.org)
        self.campaign_id = self.campaign["id"]

    def test_report_counts_only(self):
        self.store.record_delivery(OPERATOR, self.campaign_id, CONTACT_A,
                                   "delivered", OCCURRED)
        self.store.record_delivery(OPERATOR, self.campaign_id, CONTACT_B,
                                   "bounced", OCCURRED)
        self.store.record_engagement(OPERATOR, self.campaign_id, CONTACT_A,
                                     "open", OCCURRED)
        self.store.record_engagement(OPERATOR, self.campaign_id, CONTACT_A,
                                     "click", OCCURRED)
        self.store.record_suppression(OPERATOR, self.contact_list["id"],
                                      CONTACT_B, "bounce")
        report = self.store.engagement_report(ADMIN, self.campaign_id)
        self.assertEqual(report["deliveries_by_outcome"],
                         {"delivered": 1, "bounced": 1, "deferred": 0})
        self.assertEqual(report["delivered_contacts"], 1)
        self.assertEqual(report["engagements_by_kind"],
                         {"open": 1, "click": 1, "reply": 0,
                          "unsubscribe": 0})
        self.assertEqual(report["active_suppressions_on_list"], 1)
        self.assertEqual(report["status"], "reported")
        for key in report:
            self.assertNotIn("rate", key)
            self.assertNotIn("score", key)
            self.assertNotIn("percent", key)

    def test_kind_vocabulary(self):
        with self.assertRaises(ValidationError):
            self.store.record_engagement(OPERATOR, self.campaign_id,
                                         CONTACT_A, "purchase", OCCURRED)


class SearchAndSummaryTests(unittest.TestCase):
    def test_search_and_summary(self):
        store, _audit = make_store()
        org = make_org(store)
        campaign, _lst, _seg = make_campaign(store, org)
        store.record_delivery(OPERATOR, campaign["id"], CONTACT_A,
                              "delivered", OCCURRED)
        found = store.search(ADMIN, "newsletter")
        self.assertEqual([c["id"] for c in found["campaigns"]],
                         [campaign["id"]])
        found = store.search(ADMIN, "department of examples")
        self.assertEqual(found["opportunities"], [])
        summary = store.summary(ADMIN)
        self.assertEqual(summary["organizations"], 1)
        self.assertEqual(summary["campaigns_by_status"]["delivered"], 1)
        self.assertEqual(summary["deliveries_by_outcome"]["delivered"], 1)
        self.assertEqual(summary["pipeline_by_stage"]["identified"], 0)


if __name__ == "__main__":
    unittest.main()
