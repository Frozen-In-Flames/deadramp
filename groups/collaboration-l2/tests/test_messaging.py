"""Messaging & chat tests.

Traces to: UNION-SPEC Core function 2 (Messaging & chat — channels
inside a workspace; messages with optional threading; @name mentions of
workspace members generate notifications) / ranking row 5 (Messaging &
chat, 11 siblings); Implementation contract for ``collab/store.py``
channel/message methods; control families AC-3 (membership boundary)
and SI-10 (failed operations consume no id).
"""

import unittest

from collab_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    VIEWER,
    fresh_store,
    make_channel,
    make_store,
    post_sample_message,
)
from collab.errors import NotFoundError, PermissionDenied, ValidationError

CHANNEL_KEYS = {"id", "workspace_id", "name", "created_by", "created_utc"}
MESSAGE_KEYS = {
    "id", "workspace_id", "channel_id", "author", "text", "parent_id",
    "created_utc",
}


class TestChannels(unittest.TestCase):
    """Core: Messaging — channel creation and listing."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_create_channel_returns_the_contract_dict(self):
        """Core: Messaging. Contract: create_channel returns {id,
        workspace_id, name, created_by, created_utc} with a ch- id."""
        channel = make_channel(self.store, self.ws_id, name="general")
        self.assertEqual(set(channel.keys()), CHANNEL_KEYS)
        self.assertEqual(channel["id"], "ch-1")
        self.assertEqual(channel["workspace_id"], self.ws_id)
        self.assertEqual(channel["name"], "general")
        self.assertEqual(channel["created_by"], "bob")

    def test_channel_ids_are_sequential(self):
        """Core: Messaging. Channel ids increment ch-1, ch-2."""
        first = make_channel(self.store, self.ws_id, name="a")
        second = make_channel(self.store, self.ws_id, name="b")
        self.assertEqual([first["id"], second["id"]], ["ch-1", "ch-2"])

    def test_list_channels_returns_created_channels(self):
        """Core: Messaging. list_channels returns the workspace's
        channels for a member (read)."""
        make_channel(self.store, self.ws_id, name="general")
        make_channel(self.store, self.ws_id, name="random")
        names = [c["name"] for c in self.store.list_channels(self.ws_id, VIEWER)]
        self.assertEqual(names, ["general", "random"])

    def test_viewer_member_cannot_create_channel(self):
        """Core: Messaging + Access control. create_channel requires the
        post action, which viewer lacks — even as a workspace member."""
        with self.assertRaises(PermissionDenied):
            make_channel(self.store, self.ws_id, name="nope", actor=VIEWER)

    def test_non_member_cannot_create_or_list_channels(self):
        """Core: Messaging (AC-3). Membership is enforced on channels."""
        with self.assertRaises(PermissionDenied):
            make_channel(self.store, self.ws_id, name="nope", actor=OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.list_channels(self.ws_id, OUTSIDER)

    def test_platform_admin_may_create_and_list_channels(self):
        """Core: Messaging + Access control. The platform admin role
        satisfies the membership rule."""
        channel = make_channel(self.store, self.ws_id, name="admin-made",
                               actor=ADMIN)
        listed = self.store.list_channels(self.ws_id, ADMIN)
        self.assertEqual([c["id"] for c in listed], [channel["id"]])

    def test_failed_channel_create_consumes_no_id(self):
        """Core: Messaging (SI-10). A denied channel creation leaves the
        next successful id at ch-1."""
        store = fresh_store()
        ws = store.create_workspace("solo", MEMBER)
        with self.assertRaises(PermissionDenied):
            store.create_channel(ws["id"], "nope", VIEWER)
        channel = store.create_channel(ws["id"], "general", MEMBER)
        self.assertEqual(channel["id"], "ch-1")


class TestPostAndListMessages(unittest.TestCase):
    """Core: Messaging — posting, threading, listing, getting."""

    def setUp(self):
        self.store, self.ws_id = make_store()
        self.channel = make_channel(self.store, self.ws_id)

    def test_post_message_returns_the_contract_dict(self):
        """Core: Messaging. Contract: post_message returns {id,
        workspace_id, channel_id, author, text, parent_id,
        created_utc} with a msg- id and parent_id None by default."""
        msg = post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="hello team"
        )
        self.assertEqual(set(msg.keys()), MESSAGE_KEYS)
        self.assertEqual(msg["id"], "msg-1")
        self.assertEqual(msg["workspace_id"], self.ws_id)
        self.assertEqual(msg["channel_id"], self.channel["id"])
        self.assertEqual(msg["author"], "bob")
        self.assertEqual(msg["text"], "hello team")
        self.assertIsNone(msg["parent_id"])

    def test_reply_in_same_channel_is_accepted(self):
        """Core: Messaging. Contract: a message may reply to another in
        the same channel via parent_id."""
        parent = post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="parent"
        )
        reply = post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="reply",
            parent_id=parent["id"],
        )
        self.assertEqual(reply["parent_id"], parent["id"])

    def test_reply_to_parent_in_another_channel_is_validation_error(self):
        """Core: Messaging (SI-10). Contract: parent_id 'must name a
        message in the same channel, else ValidationError'."""
        other = make_channel(self.store, self.ws_id, name="other")
        parent = post_sample_message(
            self.store, self.ws_id, other["id"], text="elsewhere"
        )
        with self.assertRaises(ValidationError):
            post_sample_message(
                self.store, self.ws_id, self.channel["id"], text="bad reply",
                parent_id=parent["id"],
            )

    def test_reply_to_unknown_parent_is_rejected(self):
        """Core: Messaging (SI-10). A parent_id naming no message is
        rejected, never partially applied."""
        with self.assertRaises((ValidationError, NotFoundError)):
            post_sample_message(
                self.store, self.ws_id, self.channel["id"], text="orphan",
                parent_id="msg-999999",
            )

    def test_failed_post_consumes_no_message_id(self):
        """Core: Messaging (SI-10). A rejected threaded post consumes no
        id: the next valid post takes the next sequential id."""
        other = make_channel(self.store, self.ws_id, name="other")
        parent = post_sample_message(
            self.store, self.ws_id, other["id"], text="elsewhere"
        )
        with self.assertRaises(ValidationError):
            post_sample_message(
                self.store, self.ws_id, self.channel["id"], text="bad",
                parent_id=parent["id"],
            )
        msg = post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="good"
        )
        self.assertEqual(msg["id"], "msg-2")

    def test_list_messages_is_chronological(self):
        """Core: Messaging. Contract: list_messages returns
        chronological message dicts."""
        for text in ("first", "second", "third"):
            post_sample_message(self.store, self.ws_id, self.channel["id"],
                                text=text)
        texts = [
            m["text"]
            for m in self.store.list_messages(
                self.ws_id, self.channel["id"], MEMBER
            )
        ]
        self.assertEqual(texts, ["first", "second", "third"])

    def test_list_messages_limit_returns_the_latest_n_chronologically(self):
        """Core: Messaging. Contract: list_messages(..., limit) bounds
        the chronological list — the shipped implementation returns
        the latest N messages, still in chronological order (the spec
        leaves which end open; see tests/README.md)."""
        for text in ("first", "second", "third"):
            post_sample_message(self.store, self.ws_id, self.channel["id"],
                                text=text)
        limited = self.store.list_messages(
            self.ws_id, self.channel["id"], MEMBER, limit=2
        )
        self.assertEqual([m["text"] for m in limited], ["second", "third"])
        everything = self.store.list_messages(
            self.ws_id, self.channel["id"], MEMBER, limit=99
        )
        self.assertEqual(len(everything), 3)

    def test_list_messages_is_scoped_to_the_channel(self):
        """Core: Messaging. One channel's list never shows another
        channel's messages."""
        other = make_channel(self.store, self.ws_id, name="other")
        post_sample_message(self.store, self.ws_id, self.channel["id"],
                            text="in general")
        post_sample_message(self.store, self.ws_id, other["id"],
                            text="in other")
        texts = [
            m["text"]
            for m in self.store.list_messages(
                self.ws_id, self.channel["id"], MEMBER
            )
        ]
        self.assertEqual(texts, ["in general"])

    def test_get_message_roundtrip(self):
        """Core: Messaging. get_message returns the posted dict."""
        msg = post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="fetch me"
        )
        got = self.store.get_message(self.ws_id, msg["id"], VIEWER)
        self.assertEqual(got["id"], msg["id"])
        self.assertEqual(got["text"], "fetch me")

    def test_get_unknown_message_is_not_found(self):
        """Core: Messaging. Unknown message id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_message(self.ws_id, "msg-999999", MEMBER)

    def test_viewer_member_can_read_but_cannot_post(self):
        """Core: Messaging + Access control. Viewer holds read, not
        post: listing works, posting is denied and stores nothing."""
        post_sample_message(self.store, self.ws_id, self.channel["id"])
        listed = self.store.list_messages(
            self.ws_id, self.channel["id"], VIEWER
        )
        self.assertEqual(len(listed), 1)
        with self.assertRaises(PermissionDenied):
            post_sample_message(
                self.store, self.ws_id, self.channel["id"], actor=VIEWER
            )
        self.assertEqual(
            len(self.store.list_messages(self.ws_id, self.channel["id"],
                                         MEMBER)),
            1,
        )

    def test_non_member_cannot_post_list_or_get(self):
        """Core: Messaging (AC-3). A platform member who is not a
        workspace member is denied on every message operation."""
        msg = post_sample_message(self.store, self.ws_id, self.channel["id"])
        with self.assertRaises(PermissionDenied):
            post_sample_message(
                self.store, self.ws_id, self.channel["id"], actor=OUTSIDER
            )
        with self.assertRaises(PermissionDenied):
            self.store.list_messages(self.ws_id, self.channel["id"], OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.get_message(self.ws_id, msg["id"], OUTSIDER)

    def test_post_to_unknown_channel_is_rejected(self):
        """Core: Messaging. Posting into a channel that does not exist
        is rejected and consumes no message id."""
        with self.assertRaises((NotFoundError, ValidationError)):
            post_sample_message(self.store, self.ws_id, "ch-999999")
        msg = post_sample_message(self.store, self.ws_id, self.channel["id"])
        self.assertEqual(msg["id"], "msg-1")


class TestMentions(unittest.TestCase):
    """Core: Messaging + Notifications — @name mention notifications."""

    def setUp(self):
        self.store, self.ws_id = make_store()
        self.channel = make_channel(self.store, self.ws_id)

    def test_mention_notifies_the_mentioned_member(self):
        """Core: Messaging. Contract: each @name token naming a
        workspace member other than the author creates a notification
        (kind mention, ref_id = the message id)."""
        msg = post_sample_message(
            self.store, self.ws_id, self.channel["id"],
            text="hi @carol please review",
        )
        notes = self.store.notifications_for("carol")
        self.assertEqual(len(notes), 1)
        note = notes[0]
        self.assertEqual(note["kind"], "mention")
        self.assertEqual(note["ref_id"], msg["id"])
        self.assertEqual(note["user"], "carol")
        self.assertEqual(note["workspace_id"], self.ws_id)
        self.assertFalse(note["read"])

    def test_mention_of_a_non_member_creates_no_notification(self):
        """Core: Messaging. @name only notifies workspace members:
        @dave (not a member) notifies nobody."""
        post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="hi @dave"
        )
        self.assertEqual(self.store.notifications_for("dave"), [])
        self.assertEqual(self.store.notifications_for("carol"), [])

    def test_author_mentioning_themself_creates_no_notification(self):
        """Core: Messaging. Contract: mentions notify members 'other
        than the author' — a self-mention is silent."""
        post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="note @bob"
        )
        self.assertEqual(self.store.notifications_for("bob"), [])

    def test_message_without_mentions_notifies_nobody(self):
        """Core: Messaging. Plain messages create no notifications."""
        post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="plain update"
        )
        self.assertEqual(self.store.notifications_for("carol"), [])
        self.assertEqual(self.store.notifications_for("bob"), [])

    def test_one_message_can_mention_two_members(self):
        """Core: Messaging. Distinct mentioned members each get their
        own mention notification for the same message."""
        self.store.add_member(self.ws_id, "dave", MEMBER)
        msg = post_sample_message(
            self.store, self.ws_id, self.channel["id"],
            text="@carol and @dave standup",
        )
        for name in ("carol", "dave"):
            with self.subTest(user=name):
                notes = self.store.notifications_for(name)
                self.assertEqual(len(notes), 1)
                self.assertEqual(notes[0]["kind"], "mention")
                self.assertEqual(notes[0]["ref_id"], msg["id"])


if __name__ == "__main__":
    unittest.main()
