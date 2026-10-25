"""Workspace tests.

Traces to: UNION-SPEC Core function 1 (Workspaces — named shared
workspaces with an owner, a member list, and provenance) / ranking row
10 (Shared workspaces & team collaboration, 10 siblings); Implementation
contract for ``collab/store.py`` workspace methods; control families
AC-2/AC-3 (membership is the boundary) and SI-10 (a failed operation
consumes no id and changes nothing).
"""

import unittest
from datetime import datetime

from collab_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    OUTSIDER_VIEWER,
    VIEWER,
    fresh_store,
    make_store,
)
from collab.errors import NotFoundError, PermissionDenied, ValidationError

WORKSPACE_KEYS = {"id", "name", "owner", "members", "created_by", "created_utc"}


class TestCreateWorkspace(unittest.TestCase):
    """Core: Workspaces — creation shape, provenance, id sequence."""

    def setUp(self):
        self.store = fresh_store()

    def test_create_returns_the_contract_dict(self):
        """Core: Workspaces. Contract: create_workspace returns {id,
        name, owner, members, created_by, created_utc}."""
        ws = self.store.create_workspace("team-room", MEMBER)
        self.assertEqual(set(ws.keys()), WORKSPACE_KEYS)
        self.assertEqual(ws["name"], "team-room")
        self.assertEqual(ws["created_by"], "bob")

    def test_creator_is_owner_and_first_member(self):
        """Core: Workspaces. Contract: 'the creator is owner and first
        member'."""
        ws = self.store.create_workspace("team-room", MEMBER)
        self.assertEqual(ws["owner"], "bob")
        self.assertEqual(ws["members"], ["bob"])

    def test_first_workspace_id_is_ws_1_and_ids_are_sequential(self):
        """Core: Workspaces. Contract: ids are sequential per object
        type with the ws- prefix."""
        first = self.store.create_workspace("a", MEMBER)
        second = self.store.create_workspace("b", ADMIN)
        third = self.store.create_workspace("c", MEMBER)
        self.assertEqual(
            [first["id"], second["id"], third["id"]],
            ["ws-1", "ws-2", "ws-3"],
        )

    def test_created_utc_is_a_parseable_timestamp(self):
        """Core: Workspaces. Contract: all timestamps are UTC ISO-8601."""
        ws = self.store.create_workspace("team-room", MEMBER)
        parsed = datetime.fromisoformat(
            str(ws["created_utc"]).replace("Z", "+00:00")
        )
        self.assertIsNotNone(parsed)

    def test_admin_and_member_may_create_but_viewer_may_not(self):
        """Core: Workspaces + Access control. create_workspace is in the
        admin and member permission sets and not in viewer's."""
        self.store.create_workspace("by-admin", ADMIN)
        self.store.create_workspace("by-member", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.create_workspace("by-viewer", VIEWER)

    def test_failed_create_consumes_no_id(self):
        """Core: Workspaces (SI-10). A denied creation changes nothing:
        the next successful workspace is still ws-1."""
        with self.assertRaises(PermissionDenied):
            self.store.create_workspace("denied", VIEWER)
        ws = self.store.create_workspace("real", MEMBER)
        self.assertEqual(ws["id"], "ws-1")


class TestGetAndListWorkspaces(unittest.TestCase):
    """Core: Workspaces — visibility is membership (or platform admin)."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_get_workspace_by_owner_and_member(self):
        """Core: Workspaces. Members can get their workspace dict."""
        for actor in (MEMBER, VIEWER):
            with self.subTest(actor=actor.name):
                ws = self.store.get_workspace(self.ws_id, actor)
                self.assertEqual(ws["id"], self.ws_id)
                self.assertEqual(set(ws.keys()), WORKSPACE_KEYS)

    def test_get_workspace_by_platform_admin_non_member(self):
        """Core: Workspaces + Access control. Contract: the platform
        admin role reaches workspaces without membership."""
        ws = self.store.get_workspace(self.ws_id, ADMIN)
        self.assertEqual(ws["id"], self.ws_id)

    def test_get_workspace_by_non_member_is_denied(self):
        """Core: Workspaces (AC-3). A non-member cannot read a
        workspace, whatever their platform role."""
        with self.assertRaises(PermissionDenied):
            self.store.get_workspace(self.ws_id, OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.get_workspace(self.ws_id, OUTSIDER_VIEWER)

    def test_get_unknown_workspace_is_not_found(self):
        """Core: Workspaces. Unknown id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_workspace("ws-999999", ADMIN)

    def test_list_workspaces_shows_only_visible_workspaces(self):
        """Core: Workspaces. Contract: list_workspaces returns the
        workspace dicts the actor may see (member of, or platform
        admin)."""
        other = self.store.create_workspace("dave-space", OUTSIDER)
        bob_ids = [w["id"] for w in self.store.list_workspaces(MEMBER)]
        dave_ids = [w["id"] for w in self.store.list_workspaces(OUTSIDER)]
        admin_ids = [w["id"] for w in self.store.list_workspaces(ADMIN)]
        self.assertEqual(bob_ids, [self.ws_id])
        self.assertEqual(dave_ids, [other["id"]])
        self.assertEqual(sorted(admin_ids), sorted([self.ws_id, other["id"]]))

    def test_list_workspaces_for_user_with_none_is_empty(self):
        """Core: Workspaces. A user in no workspace sees an empty list."""
        self.assertEqual(self.store.list_workspaces(OUTSIDER_VIEWER), [])


class TestAddMember(unittest.TestCase):
    """Core: Workspaces — membership management (owner or admin only)."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_owner_adds_a_member(self):
        """Core: Workspaces. Contract: add_member returns the updated
        workspace dict with the new member present."""
        ws = self.store.add_member(self.ws_id, "dave", MEMBER)
        self.assertEqual(ws["id"], self.ws_id)
        self.assertIn("dave", ws["members"])
        self.assertEqual(
            self.store.get_workspace(self.ws_id, MEMBER)["members"],
            ["bob", "carol", "dave"],
        )

    def test_platform_admin_adds_a_member(self):
        """Core: Workspaces. Contract: 'only the workspace owner or a
        platform admin may add' — the admin need not be a member."""
        ws = self.store.add_member(self.ws_id, "dave", ADMIN)
        self.assertIn("dave", ws["members"])

    def test_non_owner_member_cannot_add(self):
        """Core: Workspaces (AC-6). A member who is not the owner cannot
        add members."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.ws_id, "dave", VIEWER)
        self.assertNotIn(
            "dave", self.store.get_workspace(self.ws_id, MEMBER)["members"]
        )

    def test_non_member_cannot_add(self):
        """Core: Workspaces (AC-3). A non-member cannot add anyone,
        including themself."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.ws_id, "dave", OUTSIDER)

    def test_duplicate_add_raises_validation_error(self):
        """Core: Workspaces (SI-10). Contract: 'adding an existing
        member raises ValidationError' — for a member added earlier and
        for the owner alike."""
        with self.assertRaises(ValidationError):
            self.store.add_member(self.ws_id, "carol", MEMBER)
        with self.assertRaises(ValidationError):
            self.store.add_member(self.ws_id, "bob", MEMBER)

    def test_failed_adds_change_nothing(self):
        """Core: Workspaces (SI-10). Denied and duplicate adds leave the
        member list exactly as it was, and a later valid add still
        succeeds."""
        before = self.store.get_workspace(self.ws_id, MEMBER)["members"]
        for actor, name in ((VIEWER, "dave"), (MEMBER, "carol")):
            with self.assertRaises((PermissionDenied, ValidationError)):
                self.store.add_member(self.ws_id, name, actor)
        self.assertEqual(
            self.store.get_workspace(self.ws_id, MEMBER)["members"], before
        )
        ws = self.store.add_member(self.ws_id, "dave", MEMBER)
        self.assertEqual(ws["members"], ["bob", "carol", "dave"])

    def test_add_member_to_unknown_workspace_is_not_found(self):
        """Core: Workspaces. add_member on a missing workspace ->
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.add_member("ws-999999", "dave", ADMIN)

    def test_new_member_gains_workspace_access(self):
        """Core: Workspaces. Once added, the new member can read the
        workspace (membership is the boundary, AC-3)."""
        with self.assertRaises(PermissionDenied):
            self.store.get_workspace(self.ws_id, OUTSIDER)
        self.store.add_member(self.ws_id, "dave", MEMBER)
        ws = self.store.get_workspace(self.ws_id, OUTSIDER)
        self.assertEqual(ws["id"], self.ws_id)


if __name__ == "__main__":
    unittest.main()
