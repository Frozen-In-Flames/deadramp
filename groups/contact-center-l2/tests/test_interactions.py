"""Interaction tests: immutable records.

Traces to: Core function 5 -- Interactions; contract for
``ContactStore.record_interaction/get_interaction/list_interactions``.
Immutability traced here: the store exposes no update/delete API for
interactions, and returned records are copies.
"""

import unittest

from contact_helpers import OPERATOR, VIEWER, fresh_store, make_store
from contact.errors import NotFoundError, PermissionDenied, ValidationError


class TestRecordInteraction(unittest.TestCase):
    """Core 5: Interactions -- recording and validation."""

    def test_record_shape(self):
        """Core 5: Interactions. record_interaction returns int- id with channel/direction/summary/links."""
        store, agent, contact, queue = make_store()
        case = store.create_case(OPERATOR, "inquiry", "s", contact_id=contact["id"])
        inter = store.record_interaction(
            OPERATOR, "voice", "inbound", "Citizen called about claim",
            case_id=case["id"], contact_id=contact["id"], agent_id=agent["id"],
            outcome="resolved", external_ref="EXT-CALL-1",
        )
        self.assertEqual(inter["id"], "int-1")
        self.assertEqual(inter["channel"], "voice")
        self.assertEqual(inter["direction"], "inbound")
        self.assertEqual(inter["case_id"], case["id"])
        self.assertEqual(inter["external_ref"], "EXT-CALL-1")

    def test_all_channels_and_directions(self):
        """Core 5: Interactions. All six channels and three directions are accepted."""
        store = fresh_store()
        for channel in ("voice", "chat", "email", "in_person", "remote_session", "system"):
            inter = store.record_interaction(OPERATOR, channel, "internal", "s " + channel)
            self.assertEqual(inter["channel"], channel)
        for direction in ("inbound", "outbound", "internal"):
            inter = store.record_interaction(OPERATOR, "chat", direction, "s")
            self.assertEqual(inter["direction"], direction)

    def test_validation_no_id_on_failure(self):
        """Core 5: Interactions (SI-10). Bad channel/direction/summary -> ValidationError; unknown links -> NotFoundError; no id consumed."""
        store, agent, contact, queue = make_store()
        with self.assertRaises(ValidationError):
            store.record_interaction(OPERATOR, "fax", "inbound", "s")
        with self.assertRaises(ValidationError):
            store.record_interaction(OPERATOR, "chat", "sideways", "s")
        with self.assertRaises(ValidationError):
            store.record_interaction(OPERATOR, "chat", "inbound", "")
        with self.assertRaises(NotFoundError):
            store.record_interaction(OPERATOR, "chat", "inbound", "s", case_id="case-999")
        with self.assertRaises(NotFoundError):
            store.record_interaction(OPERATOR, "chat", "inbound", "s", contact_id="ct-999")
        with self.assertRaises(NotFoundError):
            store.record_interaction(OPERATOR, "chat", "inbound", "s", agent_id="agt-999")
        self.assertEqual(
            store.record_interaction(OPERATOR, "chat", "inbound", "ok")["id"], "int-1")

    def test_viewer_cannot_record(self):
        """Core 5/11: Interactions/RBAC. Viewer record_interaction -> PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.record_interaction(VIEWER, "chat", "inbound", "s")


class TestImmutabilityAndFilters(unittest.TestCase):
    """Core 5: Interactions -- immutability and listing."""

    def test_no_update_or_delete_api(self):
        """Core 5: Interactions (immutability). The store exposes no update/delete interaction API."""
        store = fresh_store()
        for name in ("update_interaction", "delete_interaction", "remove_interaction",
                     "edit_interaction"):
            self.assertFalse(hasattr(store, name), name)

    def test_returned_records_are_copies(self):
        """Core 5: Interactions (immutability). Mutating a returned record does not mutate the store."""
        store = fresh_store()
        inter = store.record_interaction(OPERATOR, "chat", "inbound", "original summary")
        inter["summary"] = "hacked"
        listed = store.list_interactions(OPERATOR)
        listed[0]["summary"] = "hacked again"
        self.assertEqual(
            store.get_interaction(inter["id"], OPERATOR)["summary"], "original summary")

    def test_get_and_list_with_case_filter(self):
        """Core 5: Interactions. get_interaction/list_interactions with case_id filter; unknown case -> NotFoundError."""
        store, agent, contact, queue = make_store()
        case = store.create_case(OPERATOR, "inquiry", "s")
        i1 = store.record_interaction(OPERATOR, "chat", "inbound", "a", case_id=case["id"])
        store.record_interaction(OPERATOR, "email", "outbound", "b")
        self.assertEqual(store.get_interaction(i1["id"], VIEWER)["id"], i1["id"])
        self.assertEqual(len(store.list_interactions(VIEWER)), 2)
        filtered = store.list_interactions(VIEWER, case_id=case["id"])
        self.assertEqual([i["id"] for i in filtered], [i1["id"]])
        with self.assertRaises(NotFoundError):
            store.list_interactions(OPERATOR, case_id="case-999")
        with self.assertRaises(NotFoundError):
            store.get_interaction("int-999", OPERATOR)


if __name__ == "__main__":
    unittest.main()
