"""Messages / composition tests.

Traces to: Core function -- Message composition with per-recipient
delivery records; contract for ``compose_message/get_message/
list_messages/get_delivery/list_deliveries``.
"""

import unittest

from comm_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from comm.errors import NotFoundError, PermissionDenied, ValidationError


class TestCompose(unittest.TestCase):
    """Core: Message composition."""

    def setUp(self):
        self.store, self.contact, self.group, self.channel = make_store()

    def test_compose_literal_shape_and_delivery(self):
        """Core: Messages. Literal compose returns msg-1 shape; one queued delivery per recipient x reachable kind."""
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="Body",
            contact_ids=[self.contact["id"]], channel_kinds=["email"],
        )
        self.assertEqual(msg["id"], "msg-1")
        self.assertEqual(msg["subject"], "Hi")
        self.assertIsNone(msg["template_id"])
        self.assertFalse(msg["require_ack"])
        self.assertIsNone(msg["send_at"])
        self.assertEqual(msg["skipped_recipients"], [])
        deliveries = self.store.list_deliveries(msg["id"], OPERATOR)
        self.assertEqual(len(deliveries), 1)
        d = deliveries[0]
        self.assertEqual(d["id"], "dlv-1")
        self.assertEqual(d["status"], "queued")
        self.assertEqual(d["attempts"], 0)
        self.assertIsNone(d["receipt"])
        self.assertIsNone(d["failure_reason"])
        self.assertIsNone(d["acked_utc"])
        self.assertEqual(d["address"], "dana@example.com")
        self.assertEqual(d["channel_kind"], "email")
        self.assertEqual(self.store.get_message("msg-1", VIEWER)["id"], "msg-1")
        self.assertEqual(self.store.get_delivery("dlv-1", VIEWER)["id"], "dlv-1")
        self.assertEqual(len(self.store.list_messages(VIEWER)), 1)

    def test_default_kinds_order_and_multi_kind(self):
        """Core: Messages. Default channel_kinds = email,sms,voice,push order; deliveries follow that order for reachable kinds."""
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="B", contact_ids=[self.contact["id"]]
        )
        deliveries = self.store.list_deliveries(msg["id"], OPERATOR)
        # Contact has email + sms only.
        self.assertEqual([d["channel_kind"] for d in deliveries], ["email", "sms"])

    def test_recipients_union_dedup_order_stable(self):
        """Core: Messages. Recipients = union of contact_ids and group members, deduplicated order-stable."""
        other = self.store.create_contact("Eve", {"email": "eve@x.y"}, OPERATOR)
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[other["id"], self.contact["id"]],
            group_ids=[self.group["id"]], channel_kinds=["email"],
        )
        deliveries = self.store.list_deliveries(msg["id"], OPERATOR)
        self.assertEqual(
            [d["contact_id"] for d in deliveries], [other["id"], self.contact["id"]]
        )

    def test_skipped_recipients(self):
        """Core: Messages. Recipients with no reachable kind go into skipped_recipients."""
        unreachable = self.store.create_contact("FaxOnly", {"voice": "123"}, OPERATOR)
        # voice address exists but we select email only -> skipped.
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[self.contact["id"], unreachable["id"]],
            channel_kinds=["email"],
        )
        self.assertEqual(msg["skipped_recipients"], [unreachable["id"]])
        self.assertEqual(len(self.store.list_deliveries(msg["id"], OPERATOR)), 1)

    def test_zero_deliveries_validation_no_ids(self):
        """Core: Messages (SI-10). Total deliveries == 0 -> ValidationError, no message persisted, no ids consumed."""
        unreachable = self.store.create_contact("V", {"voice": "1"}, OPERATOR)
        with self.assertRaises(ValidationError):
            self.store.compose_message(
                OPERATOR, subject="Hi", body="B",
                contact_ids=[unreachable["id"]], channel_kinds=["email"],
            )
        self.assertEqual(self.store.list_messages(OPERATOR), [])
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="B",
            contact_ids=[self.contact["id"]], channel_kinds=["email"],
        )
        self.assertEqual(msg["id"], "msg-1")
        self.assertEqual(self.store.list_deliveries(msg["id"], OPERATOR)[0]["id"], "dlv-1")

    def test_template_compose(self):
        """Core: Messages + Templates. template_id renders subject/body; literal subject with template -> ValidationError."""
        tpl = self.store.create_template("t", "Hi {n}", "Body {n}", OPERATOR)
        msg = self.store.compose_message(
            OPERATOR, template_id=tpl["id"], variables={"n": "Dana"},
            contact_ids=[self.contact["id"]], channel_kinds=["email"],
        )
        self.assertEqual(msg["subject"], "Hi Dana")
        self.assertEqual(msg["body"], "Body Dana")
        self.assertEqual(msg["template_id"], tpl["id"])
        with self.assertRaises(ValidationError):
            self.store.compose_message(
                OPERATOR, subject="lit", template_id=tpl["id"], variables={"n": "x"},
                contact_ids=[self.contact["id"]],
            )
        with self.assertRaises(ValidationError):
            self.store.compose_message(
                OPERATOR, template_id=tpl["id"], variables={},
                contact_ids=[self.contact["id"]],
            )

    def test_validation_and_not_found(self):
        """Core: Messages. Missing subject/body, zero recipients, unknown contact/group/kind, malformed send_at -> errors."""
        with self.assertRaises(ValidationError):
            self.store.compose_message(OPERATOR, body="B", contact_ids=[self.contact["id"]])
        with self.assertRaises(ValidationError):
            self.store.compose_message(OPERATOR, subject="S", body="B", contact_ids=[])
        with self.assertRaises(NotFoundError):
            self.store.compose_message(OPERATOR, subject="S", body="B", contact_ids=["ct-999"])
        with self.assertRaises(NotFoundError):
            self.store.compose_message(OPERATOR, subject="S", body="B", group_ids=["grp-999"])
        with self.assertRaises(ValidationError):
            self.store.compose_message(
                OPERATOR, subject="S", body="B",
                contact_ids=[self.contact["id"]], channel_kinds=["fax"],
            )
        with self.assertRaises(ValidationError):
            self.store.compose_message(
                OPERATOR, subject="S", body="B",
                contact_ids=[self.contact["id"]], send_at="not-a-date",
            )

    def test_viewer_cannot_compose_and_send_at_stored(self):
        """Core: Messages / Access control. Viewer message_compose denied; valid send_at stored on message."""
        with self.assertRaises(PermissionDenied):
            self.store.compose_message(
                VIEWER, subject="S", body="B", contact_ids=[self.contact["id"]]
            )
        msg = self.store.compose_message(
            OPERATOR, subject="S", body="B", contact_ids=[self.contact["id"]],
            channel_kinds=["email"], send_at="2027-01-01T00:00:00+00:00",
        )
        self.assertEqual(msg["send_at"], "2027-01-01T00:00:00+00:00")

    def test_get_unknown(self):
        """Core: Messages. Unknown message/delivery -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_message("msg-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.store.get_delivery("dlv-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.store.list_deliveries("msg-999", OPERATOR)


if __name__ == "__main__":
    unittest.main()
