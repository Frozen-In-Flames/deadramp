"""Agency registry & membership; workspace registry.

Traces to: Core functions 1 (Agency registry & membership) and 2
(Workspace registry) in UNION-SPEC.md, and the AC control family —
membership is the boundary every agency-scoped function enforces;
only the agency's creator or a platform admin may add members.
"""

import unittest

import legalpol_helpers as H
from legalpol.errors import NotFoundError, PermissionDenied, ValidationError


class TestAgencies(unittest.TestCase):
    """Core 1: agency creation, uniqueness, membership boundary."""

    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()
        self.aid = self.agency["id"]

    def test_create_agency_shape_and_first_member(self):
        """Core 1: agency shape is pinned; creator is first member."""
        self.assertEqual(set(self.agency.keys()), {
            "id", "agency_ref", "label", "members", "created_by",
            "created_utc"})
        self.assertEqual(self.agency["id"], "agy-1")
        self.assertEqual(self.agency["agency_ref"], H.AGENCY_REF)
        self.assertEqual(self.agency["created_by"], "alice")
        self.assertEqual(self.agency["members"], ["alice", "bob", "carol"])

    def test_create_agency_validation(self):
        """Core 1 / SI-10: empty refs and labels are rejected whole."""
        store = H.fresh_store()
        with self.assertRaises(ValidationError):
            store.create_agency("", "Label", H.ADMIN)
        with self.assertRaises(ValidationError):
            store.create_agency("REF", "", H.ADMIN)
        with self.assertRaises(ValidationError):
            store.create_agency(None, "Label", H.ADMIN)
        self.assertEqual(store.list_agencies(H.ADMIN), [])

    def test_duplicate_agency_ref_rejected_and_no_id_consumed(self):
        """Core 1 / SI-10: duplicate ref rejected; next id is agy-2."""
        with self.assertRaises(ValidationError):
            self.store.create_agency(H.AGENCY_REF, "Copy", H.ADMIN)
        second = self.store.create_agency("AGY-REF-002", "Second", H.ADMIN)
        self.assertEqual(second["id"], "agy-2")

    def test_member_cannot_create_agency(self):
        """Core 1 / AC: agency_write is admin-only; member is denied."""
        with self.assertRaises(PermissionDenied):
            self.store.create_agency("AGY-X", "Nope", H.MEMBER)

    def test_list_agencies_scoped_to_membership(self):
        """Core 1: members see their agencies; outsiders see none;
        a platform admin sees all."""
        self.assertEqual(
            [a["id"] for a in self.store.list_agencies(H.MEMBER)], [self.aid])
        self.assertEqual(self.store.list_agencies(H.OUTSIDER), [])
        self.assertEqual(
            [a["id"] for a in self.store.list_agencies(H.ADMIN)], [self.aid])

    def test_get_agency_membership_boundary(self):
        """Core 1 / AC-3: non-member non-admin read is denied."""
        with self.assertRaises(PermissionDenied):
            self.store.get_agency(self.aid, H.OUTSIDER)
        with self.assertRaises(NotFoundError):
            self.store.get_agency("agy-999", H.ADMIN)
        self.assertEqual(self.store.get_agency(self.aid, H.VIEWER)["id"],
                         self.aid)

    def test_add_member_creator_or_admin_only(self):
        """Core 1: a non-creator member may not add; admin may."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.aid, "erin", H.MEMBER)
        updated = self.store.add_member(self.aid, "erin", H.ADMIN)
        self.assertIn("erin", updated["members"])
        # erin is now inside the boundary:
        self.assertEqual(self.store.get_agency(self.aid, H.MEMBER2)["id"],
                         self.aid)

    def test_add_existing_member_rejected(self):
        """Core 1 / SI-10: adding an existing member is a validation error."""
        with self.assertRaises(ValidationError):
            self.store.add_member(self.aid, "bob", H.ADMIN)

    def test_add_member_outsider_denied(self):
        """Core 1 / AC-3: a non-member non-admin cannot add members."""
        with self.assertRaises(PermissionDenied):
            self.store.add_member(self.aid, "mallory", H.OUTSIDER)

    def test_returned_agency_is_a_copy(self):
        """Core 1: mutating a returned view does not mutate the store."""
        got = self.store.get_agency(self.aid, H.ADMIN)
        got["members"].append("mallory")
        self.assertNotIn("mallory",
                         self.store.get_agency(self.aid, H.ADMIN)["members"])


class TestWorkspaces(unittest.TestCase):
    """Core 2: workspace registry inside an agency."""

    def setUp(self):
        self.store, self.audit, self.agency = H.make_store()
        self.aid = self.agency["id"]
        self.workspace = H.make_workspace(self.store, self.agency)
        self.wid = self.workspace["id"]

    def test_create_workspace_shape(self):
        """Core 2: workspace shape is pinned."""
        self.assertEqual(set(self.workspace.keys()), {
            "id", "agency_id", "workspace_ref", "title", "created_by",
            "created_utc"})
        self.assertEqual(self.workspace["id"], "wsp-1")
        self.assertEqual(self.workspace["agency_id"], self.aid)

    def test_workspace_ref_unique_within_agency_only(self):
        """Core 2: the same ref is fine in another agency, not twice
        in the same one."""
        with self.assertRaises(ValidationError):
            H.make_workspace(self.store, self.agency, title="Copy")
        other = self.store.create_agency("AGY-REF-002", "Second", H.ADMIN)
        twin = self.store.create_workspace(
            other["id"], H.WORKSPACE_REF, "Twin", H.ADMIN)
        self.assertEqual(twin["workspace_ref"], H.WORKSPACE_REF)

    def test_workspace_in_other_agency_is_not_found(self):
        """Core 2: an id from another agency reads as NotFound."""
        other = self.store.create_agency("AGY-REF-002", "Second", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_workspace(other["id"], self.wid, H.ADMIN)
        self.assertEqual(
            self.store.get_workspace(self.aid, self.wid, H.VIEWER)["id"],
            self.wid)

    def test_workspace_membership_and_viewer_write_boundary(self):
        """Core 2 / AC: outsider write denied; viewer cannot write."""
        with self.assertRaises(PermissionDenied):
            self.store.create_workspace(self.aid, "WSP-X", "X", H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.create_workspace(self.aid, "WSP-Y", "Y", H.VIEWER)
        with self.assertRaises(PermissionDenied):
            self.store.list_workspaces(self.aid, H.OUTSIDER)

    def test_list_workspaces(self):
        """Core 2: listing returns the agency's workspaces in order."""
        H.make_workspace(self.store, self.agency,
                         workspace_ref="WSP-REF-002", title="Second")
        refs = [w["workspace_ref"]
                for w in self.store.list_workspaces(self.aid, H.MEMBER)]
        self.assertEqual(refs, [H.WORKSPACE_REF, "WSP-REF-002"])


if __name__ == "__main__":
    unittest.main()
