"""Interaction record tests.

Traces to: Core 3 (Interaction & activity records) -- the record
type both siblings' claimed functions produce -- and control
families AU-2, AU-3, SI-12 (partial). Interactions are immutable.
"""

import unittest

import crm_helpers as H
from crm.errors import NotFoundError, ValidationError


class TestInteractions(unittest.TestCase):
    """Core 3: interaction records (int-)."""

    def setUp(self):
        self.store, self.account, self.contact = H.make_store()

    def test_record_shape(self):
        """Core 3: interaction shape/provenance."""
        rec = self.store.record_interaction(
            H.OPERATOR, "guidance_session", "outbound", "Walkthrough completed",
            account_id=self.account["id"], guide_id=None,
            outcome="completed", external_ref="EXT-9")
        self.assertEqual(rec["id"], "int-1")
        self.assertEqual(rec["channel"], "guidance_session")
        self.assertEqual(rec["external_ref"], "EXT-9")
        self.assertEqual(rec["created_by"], "bob")

    def test_all_channels_and_directions(self):
        """Core 3: all seven channels and three directions accepted."""
        for channel in ("guidance_session", "call", "chat", "email",
                        "portal", "in_person", "system"):
            rec = self.store.record_interaction(H.OPERATOR, channel, "inbound", "s")
            self.assertEqual(rec["channel"], channel)
        for direction in ("inbound", "outbound", "internal"):
            rec = self.store.record_interaction(H.OPERATOR, "chat", direction, "s")
            self.assertEqual(rec["direction"], direction)

    def test_validation(self):
        """Core 3 (SI-10): bad channel/direction/empty summary ->
        ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.record_interaction(H.OPERATOR, "fax", "inbound", "s")
        with self.assertRaises(ValidationError):
            self.store.record_interaction(H.OPERATOR, "chat", "sideways", "s")
        with self.assertRaises(ValidationError):
            self.store.record_interaction(H.OPERATOR, "chat", "inbound", "")

    def test_unknown_links(self):
        """Core 3: unknown linked ids -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.record_interaction(H.OPERATOR, "chat", "inbound", "s",
                                          case_id="case-99")
        with self.assertRaises(NotFoundError):
            self.store.record_interaction(H.OPERATOR, "chat", "inbound", "s",
                                          guide_id="guide-99")
        with self.assertRaises(NotFoundError):
            self.store.record_interaction(H.OPERATOR, "chat", "inbound", "s",
                                          account_id="acct-99")

    def test_contact_account_mismatch(self):
        """Core 3: contact/account inconsistency -> ValidationError."""
        other = self.store.create_account(H.ADMIN, "ACCT-2")
        with self.assertRaises(ValidationError):
            self.store.record_interaction(
                H.OPERATOR, "chat", "inbound", "s",
                account_id=other["id"], contact_id=self.contact["id"])

    def test_immutable_no_update_api(self):
        """Core 3: the store exposes no update/delete for interactions
        and returned records are copies."""
        rec = self.store.record_interaction(H.OPERATOR, "chat", "inbound", "orig")
        self.assertFalse(hasattr(self.store, "update_interaction"))
        self.assertFalse(hasattr(self.store, "delete_interaction"))
        rec["summary"] = "tampered"
        self.assertEqual(
            self.store.get_interaction(rec["id"], H.VIEWER)["summary"], "orig")

    def test_filters(self):
        """Core 3: list filters by case and by account."""
        case = self.store.create_case(H.OPERATOR, "inquiry", "q",
                                      account_id=self.account["id"])
        self.store.record_interaction(H.OPERATOR, "chat", "inbound", "a",
                                      case_id=case["id"],
                                      account_id=self.account["id"])
        self.store.record_interaction(H.OPERATOR, "email", "outbound", "b")
        self.assertEqual(
            len(self.store.list_interactions(H.VIEWER, case_id=case["id"])), 1)
        self.assertEqual(
            len(self.store.list_interactions(H.VIEWER,
                                             account_id=self.account["id"])), 1)
        self.assertEqual(len(self.store.list_interactions(H.VIEWER)), 2)


if __name__ == "__main__":
    unittest.main()
