"""Notification tests.

Traces to: UNION-SPEC Core function 8 (Notifications — a per-user queue
fed by mentions, event invites, and file shares; entries can be listed
and marked read) / ranking row 14 (Notifications, alerts & emergency
communications, 7 siblings); Implementation contract for
``collab/store.py`` notification methods; control families AC-3
(only the notification's user or a platform admin may mark it read).
"""

import unittest

from collab_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    VIEWER,
    create_sample_event,
    make_channel,
    make_store,
    post_sample_message,
    share_sample_file,
)
from collab.errors import NotFoundError, PermissionDenied

NOTIFICATION_KEYS = {
    "id", "user", "kind", "workspace_id", "ref_id", "created_utc", "read",
}


class NotificationBase(unittest.TestCase):
    """Fixture: carol holds three notifications, oldest first —
    a mention, a file share, and an event invite, all from bob."""

    def setUp(self):
        self.store, self.ws_id = make_store()
        channel = make_channel(self.store, self.ws_id)
        self.message = post_sample_message(
            self.store, self.ws_id, channel["id"], text="ping @carol"
        )
        self.file = share_sample_file(self.store, self.ws_id)
        self.event = create_sample_event(
            self.store, self.ws_id, attendees=["carol"]
        )
        self.notes = self.store.notifications_for("carol")


class TestNotificationQueue(NotificationBase):
    """Core: Notifications — queue shape, order, and isolation."""

    def test_notification_dict_shape(self):
        """Core: Notifications. Contract: a notification dict is {id,
        user, kind, workspace_id, ref_id, created_utc, read} with an
        ntf- id and read False on arrival."""
        self.assertEqual(len(self.notes), 3)
        for note in self.notes:
            with self.subTest(id=note["id"]):
                self.assertEqual(set(note.keys()), NOTIFICATION_KEYS)
                self.assertTrue(note["id"].startswith("ntf-"))
                self.assertEqual(note["user"], "carol")
                self.assertEqual(note["workspace_id"], self.ws_id)
                self.assertFalse(note["read"])

    def test_notification_ids_are_sequential(self):
        """Core: Notifications. Notification ids increment ntf-1,
        ntf-2, ntf-3 in creation order."""
        self.assertEqual(
            [n["id"] for n in self.notes], ["ntf-1", "ntf-2", "ntf-3"]
        )

    def test_queue_is_oldest_first_with_feed_kinds_in_order(self):
        """Core: Notifications. Contract: notifications_for returns
        dicts 'oldest first'; the feed order here is mention (message),
        file_share (file), event_invite (event), each pointing at its
        source object via ref_id."""
        self.assertEqual(
            [n["kind"] for n in self.notes],
            ["mention", "file_share", "event_invite"],
        )
        self.assertEqual(
            [n["ref_id"] for n in self.notes],
            [self.message["id"], self.file["id"], self.event["id"]],
        )

    def test_queue_for_a_user_with_none_is_empty(self):
        """Core: Notifications. Users with no notifications — including
        names the platform has never fed — get an empty list."""
        self.assertEqual(self.store.notifications_for("bob"), [])
        self.assertEqual(self.store.notifications_for("nobody"), [])

    def test_queues_are_per_user(self):
        """Core: Notifications. One user's queue never shows another
        user's entries."""
        self.store.add_member(self.ws_id, "dave", MEMBER)
        channel_id = self.store.list_channels(self.ws_id, MEMBER)[0]["id"]
        post_sample_message(
            self.store, self.ws_id, channel_id, text="ping @dave"
        )
        dave_notes = self.store.notifications_for("dave")
        # Dave was also notified of nothing before joining; the file
        # share predates his membership, so only the mention is his.
        mention_notes = [n for n in dave_notes if n["kind"] == "mention"]
        self.assertEqual(len(mention_notes), 1)
        self.assertTrue(all(n["user"] == "dave" for n in dave_notes))
        self.assertTrue(
            all(n["user"] == "carol"
                for n in self.store.notifications_for("carol"))
        )


class TestMarkRead(NotificationBase):
    """Core: Notifications — mark_read and its owner-or-admin rule."""

    def test_owner_marks_their_notification_read(self):
        """Core: Notifications. Contract: mark_read returns the
        updated dict with read: True, and the queue reflects it."""
        note = self.notes[0]
        updated = self.store.mark_read(note["id"], VIEWER)
        self.assertEqual(updated["id"], note["id"])
        self.assertTrue(updated["read"])
        reread = self.store.notifications_for("carol")
        self.assertTrue(reread[0]["read"])
        self.assertFalse(reread[1]["read"])

    def test_another_workspace_member_cannot_mark_it_read(self):
        """Core: Notifications (AC-3). A fellow workspace member who
        is not the notification's user (bob, the workspace owner)
        cannot mark carol's notification read."""
        note = self.notes[0]
        with self.assertRaises(PermissionDenied):
            self.store.mark_read(note["id"], MEMBER)
        self.assertFalse(self.store.notifications_for("carol")[0]["read"])

    def test_non_member_cannot_mark_it_read(self):
        """Core: Notifications (AC-3). A non-member is likewise
        denied."""
        with self.assertRaises(PermissionDenied):
            self.store.mark_read(self.notes[0]["id"], OUTSIDER)
        self.assertFalse(self.store.notifications_for("carol")[0]["read"])

    def test_admin_may_mark_any_notification_read(self):
        """Core: Notifications. Contract: 'only the notification's
        user or a platform admin may mark it' — the admin branch."""
        updated = self.store.mark_read(self.notes[1]["id"], ADMIN)
        self.assertTrue(updated["read"])
        self.assertEqual(updated["user"], "carol")

    def test_marking_an_unknown_notification_is_not_found(self):
        """Core: Notifications. Unknown notification id ->
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.mark_read("ntf-999999", ADMIN)

    def test_mark_read_twice_stays_read(self):
        """Core: Notifications. Marking an already-read notification
        read again leaves it read (no error, no state change)."""
        note = self.notes[0]
        self.store.mark_read(note["id"], VIEWER)
        again = self.store.mark_read(note["id"], VIEWER)
        self.assertTrue(again["read"])


if __name__ == "__main__":
    unittest.main()
