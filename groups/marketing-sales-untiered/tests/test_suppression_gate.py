"""Core functions 10 and 11 — the signature invariant: suppression
records and the delivery gate. A ``delivered`` outcome may not be
recorded for a contact under an active suppression on the
campaign's list; other outcomes remain recordable; releasing the
suppression re-opens delivery; a suppression recorded after a
delivery does not rewrite it (taxonomy families
suppression_management / outbound_email_delivery)."""

import unittest

from marketsales_helpers import (ADMIN, CONTACT_A, CONTACT_B, OCCURRED,
                                 OPERATOR, make_campaign, make_org,
                                 make_store)

from marketsales.errors import ValidationError


class SuppressionGateTests(unittest.TestCase):
    def setUp(self):
        self.store, _audit = make_store()
        self.org = make_org(self.store)
        self.campaign, self.contact_list, _seg = make_campaign(
            self.store, self.org)
        self.list_id = self.contact_list["id"]
        self.campaign_id = self.campaign["id"]

    def suppress(self, ref=CONTACT_A, reason="unsubscribe"):
        return self.store.record_suppression(OPERATOR, self.list_id,
                                             ref, reason)

    def test_delivered_refused_for_suppressed_contact(self):
        self.suppress()
        with self.assertRaises(ValidationError):
            self.store.record_delivery(OPERATOR, self.campaign_id,
                                       CONTACT_A, "delivered", OCCURRED)
        # The refused attempt changed nothing and consumed no id.
        self.assertEqual(self.store.list_deliveries(ADMIN), [])
        delivery = self.store.record_delivery(
            OPERATOR, self.campaign_id, CONTACT_B, "delivered", OCCURRED)
        self.assertEqual(delivery["id"], "dlv-1")

    def test_other_outcomes_remain_recordable(self):
        self.suppress()
        for outcome in ("bounced", "deferred"):
            record = self.store.record_delivery(
                OPERATOR, self.campaign_id, CONTACT_A, outcome, OCCURRED)
            self.assertEqual(record["outcome"], outcome)

    def test_unsuppressed_contact_delivers(self):
        record = self.store.record_delivery(
            OPERATOR, self.campaign_id, CONTACT_A, "delivered", OCCURRED)
        self.assertEqual(record["outcome"], "delivered")

    def test_release_reopens_delivery(self):
        suppression = self.suppress()
        self.store.release_suppression(OPERATOR, suppression["id"])
        record = self.store.record_delivery(
            OPERATOR, self.campaign_id, CONTACT_A, "delivered", OCCURRED)
        self.assertEqual(record["outcome"], "delivered")
        self.assertFalse(self.store.is_suppressed(ADMIN, self.list_id,
                                                  CONTACT_A))

    def test_late_suppression_does_not_rewrite_a_delivery(self):
        self.store.record_delivery(OPERATOR, self.campaign_id, CONTACT_A,
                                   "delivered", OCCURRED)
        self.suppress()
        deliveries = self.store.list_deliveries(
            ADMIN, campaign_id=self.campaign_id)
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0]["outcome"], "delivered")

    def test_suppression_is_per_list(self):
        other_campaign, other_list, _seg = make_campaign(self.store,
                                                         self.org)
        self.suppress()
        record = self.store.record_delivery(
            OPERATOR, other_campaign["id"], CONTACT_A, "delivered",
            OCCURRED)
        self.assertEqual(record["outcome"], "delivered")
        self.assertTrue(self.store.is_suppressed(ADMIN, self.list_id,
                                                 CONTACT_A))
        self.assertFalse(self.store.is_suppressed(ADMIN, other_list["id"],
                                                  CONTACT_A))

    def test_one_active_suppression_per_pair(self):
        self.suppress()
        with self.assertRaises(ValidationError):
            self.suppress(reason="complaint")
        suppression = self.store.list_suppressions(
            ADMIN, list_id=self.list_id)[0]
        self.store.release_suppression(OPERATOR, suppression["id"])
        again = self.suppress(reason="complaint")
        self.assertEqual(again["state"], "active")
        with self.assertRaises(ValidationError):
            self.store.release_suppression(OPERATOR, suppression["id"])

    def test_reason_vocabulary_and_contact_ref_shape(self):
        with self.assertRaises(ValidationError):
            self.suppress(reason="just because")
        for bad_ref in ("someone@example.gov", "has space", "", "  "):
            with self.assertRaises(ValidationError):
                self.store.record_suppression(OPERATOR, self.list_id,
                                              bad_ref, "unsubscribe")

    def test_outcome_vocabulary(self):
        with self.assertRaises(ValidationError):
            self.store.record_delivery(OPERATOR, self.campaign_id,
                                       CONTACT_A, "opened", OCCURRED)


if __name__ == "__main__":
    unittest.main()
