"""Presence & availability tests.

Traces to: UNION-SPEC Core function 5 (Presence — a per-user
availability status (available, busy, dnd, offline) with an optional
note and an updated timestamp; a user sets their own presence, a
platform admin may set anyone's) / ranking row 21 (Presence &
availability, 2 siblings); Implementation contract for
``collab/store.py`` presence methods; control families AC-3
(self-or-admin enforcement) and SI-10 (invalid status rejected).
"""

import unittest
from datetime import datetime

from collab_helpers import ADMIN, MEMBER, VIEWER, fresh_store
from collab.errors import NotFoundError, PermissionDenied, ValidationError

PRESENCE_KEYS = {"user", "status", "note", "updated_utc"}
STATUSES = ("available", "busy", "dnd", "offline")


class TestSetAndGetPresence(unittest.TestCase):
    """Core: Presence — set/get round trip and the status vocabulary."""

    def setUp(self):
        self.store = fresh_store()

    def test_set_presence_returns_the_contract_dict(self):
        """Core: Presence. Contract: set_presence returns {user,
        status, note, updated_utc}."""
        rec = self.store.set_presence("bob", "busy", MEMBER, note="focus")
        self.assertEqual(set(rec.keys()), PRESENCE_KEYS)
        self.assertEqual(rec["user"], "bob")
        self.assertEqual(rec["status"], "busy")
        self.assertEqual(rec["note"], "focus")

    def test_note_defaults_to_empty_string(self):
        """Core: Presence. Contract: note defaults to ""."""
        rec = self.store.set_presence("bob", "available", MEMBER)
        self.assertEqual(rec["note"], "")

    def test_updated_utc_is_a_parseable_timestamp(self):
        """Core: Presence. Contract: all timestamps are UTC ISO-8601."""
        rec = self.store.set_presence("bob", "available", MEMBER)
        parsed = datetime.fromisoformat(
            str(rec["updated_utc"]).replace("Z", "+00:00")
        )
        self.assertIsNotNone(parsed)

    def test_each_status_can_be_set_and_read_back(self):
        """Core: Presence. Contract: status must be one of available,
        busy, dnd, offline — each is accepted and get_presence returns
        it."""
        for status in STATUSES:
            with self.subTest(status=status):
                self.store.set_presence("bob", status, MEMBER)
                self.assertEqual(
                    self.store.get_presence("bob")["status"], status
                )

    def test_get_presence_returns_the_set_record(self):
        """Core: Presence. get_presence returns the presence dict set
        earlier, note included."""
        self.store.set_presence("carol", "dnd", VIEWER, note="deep work")
        rec = self.store.get_presence("carol")
        self.assertEqual(rec["user"], "carol")
        self.assertEqual(rec["status"], "dnd")
        self.assertEqual(rec["note"], "deep work")

    def test_get_unset_presence_is_not_found(self):
        """Core: Presence. Contract: get_presence -> 'NotFoundError if
        never set'."""
        with self.assertRaises(NotFoundError):
            self.store.get_presence("nobody-ever-set")

    def test_resetting_presence_overwrites_status_and_note(self):
        """Core: Presence. A later set replaces the earlier record."""
        self.store.set_presence("bob", "available", MEMBER, note="here")
        self.store.set_presence("bob", "offline", MEMBER)
        rec = self.store.get_presence("bob")
        self.assertEqual(rec["status"], "offline")
        self.assertEqual(rec["note"], "")


class TestPresenceValidation(unittest.TestCase):
    """Core: Presence (SI-10) — the closed status vocabulary."""

    def setUp(self):
        self.store = fresh_store()

    def test_invalid_status_is_validation_error(self):
        """Core: Presence. Contract: a status outside {available, busy,
        dnd, offline} raises ValidationError."""
        for bad in ("away", "online", "", "AVAILABLE"):
            with self.subTest(status=bad):
                with self.assertRaises(ValidationError):
                    self.store.set_presence("bob", bad, MEMBER)

    def test_invalid_status_for_new_user_leaves_presence_unset(self):
        """Core: Presence (SI-10). A rejected set creates no record."""
        with self.assertRaises(ValidationError):
            self.store.set_presence("bob", "away", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_presence("bob")

    def test_invalid_status_does_not_overwrite_a_valid_one(self):
        """Core: Presence (SI-10). A rejected update leaves the prior
        presence untouched."""
        self.store.set_presence("bob", "busy", MEMBER, note="keep me")
        with self.assertRaises(ValidationError):
            self.store.set_presence("bob", "away", MEMBER)
        rec = self.store.get_presence("bob")
        self.assertEqual(rec["status"], "busy")
        self.assertEqual(rec["note"], "keep me")


class TestPresenceAccess(unittest.TestCase):
    """Core: Presence — self-or-admin enforcement (AC-3)."""

    def setUp(self):
        self.store = fresh_store()

    def test_member_setting_another_users_presence_is_denied(self):
        """Core: Presence. Contract: 'the actor must be username
        themself or a platform admin, else PermissionDenied'."""
        with self.assertRaises(PermissionDenied):
            self.store.set_presence("carol", "busy", MEMBER)
        with self.assertRaises(NotFoundError):
            self.store.get_presence("carol")

    def test_viewer_setting_another_users_presence_is_denied(self):
        """Core: Presence. The self-or-admin rule binds every
        non-admin role."""
        with self.assertRaises(PermissionDenied):
            self.store.set_presence("bob", "busy", VIEWER)

    def test_admin_may_set_anyones_presence(self):
        """Core: Presence. Contract: 'a platform admin may set
        anyone's' presence."""
        rec = self.store.set_presence("carol", "dnd", ADMIN, note="by admin")
        self.assertEqual(rec["status"], "dnd")
        self.assertEqual(self.store.get_presence("carol")["note"], "by admin")

    def test_admin_may_set_their_own_presence(self):
        """Core: Presence. Admin self-set is the ordinary self case."""
        rec = self.store.set_presence("alice", "available", ADMIN)
        self.assertEqual(rec["user"], "alice")

    def test_each_role_may_set_their_own_presence(self):
        """Core: Presence. Self-set is role-independent: admin, member
        and viewer alike."""
        for user in (ADMIN, MEMBER, VIEWER):
            with self.subTest(user=user.name):
                rec = self.store.set_presence(user.name, "available", user)
                self.assertEqual(rec["user"], user.name)


if __name__ == "__main__":
    unittest.main()
