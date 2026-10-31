"""Core 1 Organizations & Core 2 Candidates.

Traces to: UNION-SPEC.md Core 1-2 — organizations keyed by an
opaque org_ref with a member list (membership is the boundary
every organization-scoped function enforces; only the creator or
a platform admin adds members); candidates as opaque references
with no field that can hold a real person's identity (the privacy
discipline).
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestOrganizations(unittest.TestCase):
    """Core 1: organization registry & membership."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_create_shape_and_creator_membership(self):
        """Core 1: the created dict has exactly the contract's
        keys, and the creator is the first member."""
        store = H.fresh_store()
        org = store.create_organization("ORG-X", "Label X", H.ADMIN)
        self.assertEqual(set(org), {"id", "org_ref", "label", "members",
                                    "created_by", "created_utc"})
        self.assertEqual(org["id"], "org-1")
        self.assertEqual(org["members"], ["alice"])
        self.assertEqual(org["created_by"], "alice")

    def test_duplicate_org_ref_rejected_no_id_consumed(self):
        """Core 1 / SI-10: a duplicate org_ref raises
        ValidationError and consumes no id."""
        store = H.fresh_store()
        store.create_organization("ORG-X", "Label X", H.ADMIN)
        with self.assertRaises(ValidationError):
            store.create_organization("ORG-X", "Other", H.ADMIN)
        second = store.create_organization("ORG-Y", "Label Y", H.ADMIN)
        self.assertEqual(second["id"], "org-2")

    def test_org_write_is_admin_only(self):
        """Core 1 / AC: a member-role User cannot create an
        organization (org_write is admin's alone)."""
        with self.assertRaises(PermissionDenied):
            self.store.create_organization("ORG-Z", "Label Z", H.MEMBER)

    def test_membership_boundary(self):
        """Core 1 / AC-3: a non-member non-admin is denied reads;
        a platform admin is not."""
        with self.assertRaises(PermissionDenied):
            self.store.get_organization(self.org["id"], H.OUTSIDER)
        view = self.store.get_organization(self.org["id"], H.ADMIN)
        self.assertEqual(view["org_ref"], H.ORG_REF)

    def test_list_organizations_scoped(self):
        """Core 1: listing shows members their organizations and
        an outsider none."""
        self.assertEqual(
            [o["id"] for o in self.store.list_organizations(H.MEMBER)],
            [self.org["id"]])
        self.assertEqual(self.store.list_organizations(H.OUTSIDER), [])
        self.assertEqual(
            [o["id"] for o in self.store.list_organizations(H.ADMIN)],
            [self.org["id"]])

    def test_add_member_creator_or_admin_only(self):
        """Core 1: the creator (or an admin) may add members; a
        plain member may not; duplicates are rejected."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.org["id"], "erin", H.MEMBER)
        updated = self.store.add_member(self.org["id"], "erin", H.ADMIN)
        self.assertIn("erin", updated["members"])
        with self.assertRaises(ValidationError):
            self.store.add_member(self.org["id"], "erin", H.ADMIN)

    def test_get_missing_organization(self):
        """Core 1: a missing organization raises NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_organization("org-999", H.ADMIN)


class TestCandidates(unittest.TestCase):
    """Core 2: the candidate registry (opaque references only)."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_register_shape(self):
        """Core 2: the candidate dict has exactly the contract's
        keys — no name, contact, or identifier field exists."""
        candidate = H.make_candidate(self.store, self.org)
        self.assertEqual(set(candidate), {"id", "org_id", "candidate_ref",
                                          "label", "created_by",
                                          "created_utc"})
        self.assertEqual(candidate["id"], "can-1")
        self.assertEqual(candidate["candidate_ref"], H.CANDIDATE_REF)

    def test_duplicate_ref_rejected_within_org_only(self):
        """Core 2 / SI-10: the same candidate_ref is rejected in
        the same organization but allowed in another."""
        H.make_candidate(self.store, self.org)
        with self.assertRaises(ValidationError):
            H.make_candidate(self.store, self.org)
        other = self.store.create_organization("ORG-2ND", "Second", H.ADMIN)
        twin = H.make_candidate(self.store, other, actor=H.ADMIN)
        self.assertEqual(twin["org_id"], other["id"])

    def test_viewer_cannot_register(self):
        """Core 2 / AC: candidate_write is not a viewer action."""
        with self.assertRaises(PermissionDenied):
            H.make_candidate(self.store, self.org, actor=H.VIEWER)

    def test_outsider_cannot_read_candidates(self):
        """Core 2 / AC-3: the membership boundary covers the
        candidate registry."""
        H.make_candidate(self.store, self.org)
        with self.assertRaises(PermissionDenied):
            self.store.list_candidates(self.org["id"], H.OUTSIDER)

    def test_get_candidate_cross_org_not_found(self):
        """Core 2: a candidate id read through the wrong
        organization raises NotFoundError."""
        candidate = H.make_candidate(self.store, self.org)
        other = self.store.create_organization("ORG-3RD", "Third", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_candidate(other["id"], candidate["id"], H.ADMIN)

    def test_empty_ref_or_label_rejected(self):
        """Core 2 / SI-10: blank references and labels are
        rejected whole."""
        with self.assertRaises(ValidationError):
            self.store.register_candidate(self.org["id"], "  ", "L", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_candidate(self.org["id"], "CAN-9", "", H.MEMBER)


if __name__ == "__main__":
    unittest.main()
