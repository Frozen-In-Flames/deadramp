"""Core functions 7, 8, and 9: contact-list records (counts only),
audience-segment records, and campaign records — whose status is
DERIVED at read through the single seam and never stored
(taxonomy families contact_lists / audience_segmentation /
campaign_authoring / campaign_scheduling)."""

import unittest

from marketsales_helpers import (ADMIN, CONTACT_A, OCCURRED, OPERATOR,
                                 make_campaign, make_list, make_org,
                                 make_segment, make_store)

import marketsales.store as store_module

from marketsales.errors import NotFoundError, ValidationError


class ContactListTests(unittest.TestCase):
    def setUp(self):
        self.store, _audit = make_store()
        self.org = make_org(self.store)

    def test_counts_only_records(self):
        contact_list = make_list(self.store, self.org)
        self.assertEqual(contact_list["contact_count"], 1250)
        self.assertEqual(
            set(contact_list),
            {"id", "org_id", "label", "contact_count", "loaded_at",
             "created_by", "created_utc"})

    def test_count_validation(self):
        for bad in (True, 1.5, "12", -1):
            with self.assertRaises(ValidationError):
                self.store.create_contact_list(OPERATOR, self.org["id"],
                                               "L", bad)


class SegmentTests(unittest.TestCase):
    def test_segment_record(self):
        store, _audit = make_store()
        org = make_org(store)
        segment = make_segment(store, org)
        self.assertEqual(segment["member_count"], 300)
        self.assertEqual(segment["basis_label"],
                         "role label on loaded list")


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.store, _audit = make_store()
        self.org = make_org(self.store)
        self.campaign, self.contact_list, self.segment = make_campaign(
            self.store, self.org)

    def test_stored_record_has_no_status_key(self):
        stored = self.store._campaigns[self.campaign["id"]]
        self.assertNotIn("status", stored)
        self.assertEqual(
            set(stored),
            {"id", "org_id", "label", "segment_id", "list_id",
             "scheduled_for", "created_by", "created_utc"})

    def test_status_progression_is_derived(self):
        view = self.store.get_campaign(ADMIN, self.campaign["id"])
        self.assertEqual(view["status"], "scheduled")
        self.store.record_delivery(OPERATOR, self.campaign["id"],
                                   CONTACT_A, "delivered", OCCURRED)
        view = self.store.get_campaign(ADMIN, self.campaign["id"])
        self.assertEqual(view["status"], "delivered")
        self.store.record_engagement(OPERATOR, self.campaign["id"],
                                     CONTACT_A, "open", OCCURRED)
        view = self.store.get_campaign(ADMIN, self.campaign["id"])
        self.assertEqual(view["status"], "reported")

    def test_draft_when_unscheduled(self):
        campaign, _lst, _seg = make_campaign(self.store, self.org,
                                             scheduled_for=None)
        view = self.store.get_campaign(ADMIN, campaign["id"])
        self.assertEqual(view["status"], "draft")

    def test_derivation_seam_directly(self):
        derive = store_module._derive_campaign_status
        base = {"scheduled_for": None}
        self.assertEqual(derive(base, 0, 0), "draft")
        self.assertEqual(derive({"scheduled_for": "2026-01-10"}, 0, 0),
                         "scheduled")
        self.assertEqual(derive({"scheduled_for": "2026-01-10"}, 2, 0),
                         "delivered")
        self.assertEqual(derive({"scheduled_for": None}, 2, 1), "reported")

    def test_segment_and_list_must_share_the_org(self):
        other = self.store.create_organization(ADMIN, "ORG-2", "two")
        foreign_list = make_list(self.store, other)
        with self.assertRaises(ValidationError):
            self.store.create_campaign(
                OPERATOR, self.org["id"], "X", self.segment["id"],
                foreign_list["id"])

    def test_status_filter_uses_the_derivation(self):
        self.store.record_delivery(OPERATOR, self.campaign["id"],
                                   CONTACT_A, "delivered", OCCURRED)
        delivered = self.store.list_campaigns(ADMIN, status="delivered")
        self.assertEqual([c["id"] for c in delivered],
                         [self.campaign["id"]])
        with self.assertRaises(ValidationError):
            self.store.list_campaigns(ADMIN, status="sent")

    def test_unknown_campaign(self):
        with self.assertRaises(NotFoundError):
            self.store.get_campaign(ADMIN, "cam-99")


if __name__ == "__main__":
    unittest.main()
