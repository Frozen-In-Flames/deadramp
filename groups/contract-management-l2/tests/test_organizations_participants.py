"""Core 1 (organization registry & membership) and Core 2
(participant registry).

Traces to: UNION-SPEC.md core functions 1-2 and the AC control
family (membership is the boundary every scoped operation
enforces).
"""

import unittest

import contractmgmt_helpers as H
from contractmgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestOrganizations(unittest.TestCase):
    """Core 1: organizations, membership, and the boundary."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_organization_shape_pinned(self):
        """Core 1: the stored organization carries exactly the
        contract's keys."""
        self.assertEqual(
            set(self.org.keys()),
            {"id", "org_ref", "label", "members", "created_by", "created_utc"},
        )
        self.assertEqual(self.org["id"], "org-1")
        self.assertEqual(self.org["members"], ["alice", "bob", "carol"])

    def test_creator_is_first_member(self):
        """Core 1: creation makes the creator the first member."""
        store = H.fresh_store()
        org = store.create_organization("ORG-X", "X Office", H.ADMIN)
        self.assertEqual(org["members"], ["alice"])
        self.assertEqual(org["created_by"], "alice")

    def test_duplicate_org_ref_rejected_no_id_consumed(self):
        """Core 1 / SI-10: a duplicate org_ref is rejected whole and
        consumes no id."""
        store = H.fresh_store()
        store.create_organization("ORG-X", "X Office", H.ADMIN)
        with self.assertRaises(ValidationError):
            store.create_organization("ORG-X", "Clone", H.ADMIN)
        second = store.create_organization("ORG-Y", "Y Office", H.ADMIN)
        self.assertEqual(second["id"], "org-2")

    def test_member_cannot_create_organization(self):
        """AC: org_write is admin-only in the matrix."""
        with self.assertRaises(PermissionDenied):
            self.store.create_organization("ORG-Z", "Z Office", H.MEMBER)

    def test_non_member_denied_and_member_allowed(self):
        """Core 1: the membership boundary — an outsider (a platform
        member of no fixture organization) is denied a scoped read;
        organization members and the admin pass."""
        with self.assertRaises(PermissionDenied):
            self.store.get_organization(self.org["id"], H.OUTSIDER)
        self.assertEqual(
            self.store.get_organization(self.org["id"], H.MEMBER)["id"],
            self.org["id"],
        )
        self.assertEqual(
            self.store.get_organization(self.org["id"], H.ADMIN)["id"],
            self.org["id"],
        )

    def test_list_organizations_scoped(self):
        """Core 1: listing shows members their organizations only."""
        mine = self.store.list_organizations(H.MEMBER)
        self.assertEqual([o["id"] for o in mine], [self.org["id"]])
        self.assertEqual(self.store.list_organizations(H.OUTSIDER), [])
        self.assertEqual(len(self.store.list_organizations(H.ADMIN)), 1)

    def test_add_member_creator_or_admin_only(self):
        """Core 1: a plain member cannot add members; the creator
        (or an admin) can."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.org["id"], "erin", H.MEMBER)
        updated = self.store.add_member(self.org["id"], "erin", H.ADMIN)
        self.assertIn("erin", updated["members"])

    def test_add_existing_member_rejected(self):
        """Core 1 / SI-10: adding an existing member is a validation
        error, not a silent no-op."""
        with self.assertRaises(ValidationError):
            self.store.add_member(self.org["id"], "bob", H.ADMIN)

    def test_missing_organization_not_found(self):
        """Core 1: an unknown organization id is NotFound."""
        with self.assertRaises(NotFoundError):
            self.store.get_organization("org-99", H.ADMIN)


class TestParticipants(unittest.TestCase):
    """Core 2: the platform participant registry."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_participant_shape_pinned(self):
        """Core 2: the participant record carries exactly the
        contract's keys."""
        participant = H.make_participant(self.store)
        self.assertEqual(
            set(participant.keys()),
            {"id", "participant_ref", "label", "created_by", "created_utc"},
        )
        self.assertEqual(participant["id"], "par-1")

    def test_duplicate_participant_ref_rejected(self):
        """Core 2 / SI-10: participant refs are unique platform-wide."""
        H.make_participant(self.store)
        with self.assertRaises(ValidationError):
            H.make_participant(self.store, label="Clone")

    def test_viewer_cannot_register_participant(self):
        """AC: registry_write is not held by viewer."""
        with self.assertRaises(PermissionDenied):
            H.make_participant(self.store, actor=H.VIEWER)

    def test_reads_open_to_any_actor(self):
        """Core 2: participant reads are open to any actor, including
        an outsider and a plain-string actor (platform registry)."""
        participant = H.make_participant(self.store)
        self.assertEqual(
            self.store.get_participant(participant["id"], H.OUTSIDER)["id"],
            participant["id"],
        )
        self.assertEqual(len(self.store.list_participants("anyone")), 1)

    def test_missing_participant_not_found(self):
        """Core 2: an unknown participant id is NotFound."""
        with self.assertRaises(NotFoundError):
            self.store.get_participant("par-99", H.ADMIN)


if __name__ == "__main__":
    unittest.main()
