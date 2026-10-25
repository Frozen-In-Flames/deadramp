"""Audit-log tests.

Traces to: UNION-SPEC Core function 11 (Audit log) / ranking row 6
(Audit logging & trails, 11 siblings); Implementation contract for
``collab/audit.py`` and the store's audit action names in
``collab/store.py``; control families AU-2, AU-3, AU-6, AU-9
(append-only store).
"""

import json
import os
import tempfile
import unittest
from datetime import datetime

from collab_helpers import (
    ADMIN,
    MEMBER,
    VIEWER,
    add_sample_card,
    create_sample_board,
    create_sample_event,
    fresh_store,
    make_channel,
    make_store,
    post_sample_message,
    share_sample_file,
)
from collab.audit import AuditLog
from collab.errors import PermissionDenied


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLogInMemory(unittest.TestCase):
    """Core: Audit log — record()/entries() contract."""

    def test_record_and_entries_roundtrip(self):
        """Core: Audit log. entries() returns dicts with keys
        ts, actor, action, target, details (contract)."""
        log = AuditLog()
        log.record("alice", "workspace_create", "ws-1", {"name": "team"})
        entries = log.entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(
            set(entry.keys()), {"ts", "actor", "action", "target", "details"}
        )
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "workspace_create")
        self.assertEqual(entry["target"], "ws-1")
        self.assertEqual(entry["details"], {"name": "team"})

    def test_details_defaults_to_empty(self):
        """Core: Audit log. Contract: record(..., details=None)."""
        log = AuditLog()
        log.record("bob", "search", "ws-1")
        self.assertIn(log.entries()[0]["details"], (None, {}))

    def test_timestamp_is_isoformat_utc_string(self):
        """Core: Audit log (AU-3). Each entry carries a parseable UTC
        timestamp."""
        log = AuditLog()
        log.record("alice", "workspace_create", "ws-1")
        ts = log.entries()[0]["ts"]
        self.assertIsInstance(ts, str)
        self.assertTrue(ts)
        parsed = _parse_ts(ts)  # must not raise
        self.assertIsNotNone(parsed)

    def test_entries_preserve_record_order(self):
        """Core: Audit log (AU-2). A trail is chronological: entries come
        back in the order they were recorded."""
        log = AuditLog()
        for i in range(5):
            log.record("alice", "search", "ws-%d" % i)
        targets = [e["target"] for e in log.entries()]
        self.assertEqual(targets, ["ws-0", "ws-1", "ws-2", "ws-3", "ws-4"])

    def test_append_only_earlier_entries_never_change(self):
        """Core: Audit log (AU-9). Recording later events must not mutate
        or drop earlier entries."""
        log = AuditLog()
        log.record("alice", "workspace_create", "ws-1")
        first_snapshot = dict(log.entries()[0])
        log.record("alice", "message_post", "msg-1")
        log.record("carol", "message_post:denied", "ws-1")
        entries = log.entries()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0], first_snapshot)

    def test_empty_log_has_no_entries(self):
        """Core: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_details_dict_is_stored_verbatim(self):
        """Core: Audit log (AU-3 content of audit records)."""
        log = AuditLog()
        details = {"kind": "mention", "count": 2, "nested": {"ok": True}}
        log.record("bob", "message_post", "msg-2", details)
        self.assertEqual(log.entries()[0]["details"], details)


class TestAuditLogFile(unittest.TestCase):
    """Core: Audit log — optional JSONL file backing (contract)."""

    def test_file_backed_log_writes_jsonl(self):
        """Core: Audit log. With a path, each record is one JSON line."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "workspace_create", "ws-1", {"name": "t"})
            log.record("bob", "search", "ws-1")
            with open(path, encoding="utf-8") as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            parsed = [json.loads(ln) for ln in lines]
            self.assertEqual(parsed[0]["actor"], "alice")
            self.assertEqual(parsed[1]["action"], "search")
            for entry in parsed:
                self.assertEqual(
                    set(entry.keys()),
                    {"ts", "actor", "action", "target", "details"},
                )

    def test_file_backed_log_survives_reopen(self):
        """Core: Audit log (AU-9 protection of audit information). A new
        AuditLog over the same file reloads the prior trail on
        construction (contract) and stays append-only across restarts."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            AuditLog(path).record("alice", "workspace_create", "ws-1")
            reopened = AuditLog(path)
            entries = reopened.entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["target"], "ws-1")
            reopened.record("alice", "file_share", "ws-1")
            self.assertEqual(len(AuditLog(path).entries()), 2)


class TestStoreAuditing(unittest.TestCase):
    """Core: Audit log — the store records each mutation action."""

    def test_store_records_the_full_mutation_flow(self):
        """Core: Audit log. Contract: the store records every successful
        mutation and every search with the spec's action names:
        workspace_create, member_add, channel_create, message_post,
        file_share, event_create, presence_set, board_create, card_add,
        card_move, search, notification_read."""
        audit = AuditLog()
        store, ws_id = make_store(audit=audit)
        channel = make_channel(store, ws_id)
        message = post_sample_message(
            store, ws_id, channel["id"], text="hi @carol"
        )
        share_sample_file(store, ws_id)
        create_sample_event(store, ws_id, attendees=["carol"])
        store.set_presence("bob", "busy", MEMBER)
        board = create_sample_board(store, ws_id)
        card = add_sample_card(store, ws_id, board["id"])
        store.move_card(ws_id, board["id"], card["id"], 99, 88, MEMBER)
        store.search(ws_id, "hi", MEMBER)
        note = store.notifications_for("carol")[0]
        store.mark_read(note["id"], VIEWER)

        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "workspace_create", "member_add", "channel_create",
            "message_post", "file_share", "event_create", "presence_set",
            "board_create", "card_add", "card_move", "search",
            "notification_read",
        ):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)
        self.assertEqual(message["id"], "msg-1")

    def test_store_entries_carry_actor_and_target(self):
        """Core: Audit log (AU-3). Store-recorded entries name the actor
        who performed the mutation."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        workspace = store.create_workspace("ops", ADMIN)
        entry = audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "workspace_create")
        self.assertEqual(entry["target"], workspace["id"])

    def test_failed_mutation_records_no_success_action(self):
        """Core: Audit log. Contract: the store records *successful*
        mutations (denials are the HTTP layer's job) — a denied post
        adds no message_post entry."""
        audit = AuditLog()
        store, ws_id = make_store(audit=audit)
        channel = make_channel(store, ws_id)
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            post_sample_message(store, ws_id, channel["id"], actor=VIEWER)
        actions = [e["action"] for e in audit.entries()[before:]]
        self.assertNotIn("message_post", actions)

    def test_store_without_audit_log_still_works(self):
        """Core: Audit log. Contract: CollabStore(audit=None) — the
        audit log is optional; mutations succeed with none attached."""
        store = fresh_store()
        workspace = store.create_workspace("quiet", MEMBER)
        self.assertEqual(workspace["id"], "ws-1")
        channel = make_channel(store, workspace["id"])
        post_sample_message(store, workspace["id"], channel["id"])


if __name__ == "__main__":
    unittest.main()
