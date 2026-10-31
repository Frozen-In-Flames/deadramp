"""Core: Workspace registry. Traces to UNION-SPEC core function 3
(workspaces inside a commons — the records form of the managing /
analyzing / sharing activities the workspaces host) and the
commons membership boundary of core function 10."""

import unittest

import research_helpers as H
from research.errors import NotFoundError, PermissionDenied, ValidationError

EXPECTED_KEYS = {"id", "commons_id", "name", "purpose", "created_by",
                 "created_utc"}


class TestWorkspaces(unittest.TestCase):
    def setUp(self):
        self.store, self.commons, self.org = H.make_store()

    def test_create_shape_is_pinned(self):
        workspace = H.make_workspace(self.store, self.commons)
        self.assertEqual(set(workspace.keys()), EXPECTED_KEYS)
        self.assertTrue(workspace["id"].startswith("ws-"))
        self.assertEqual(workspace["commons_id"], self.commons["id"])
        self.assertEqual(workspace["created_by"], "bob")

    def test_get_and_list_inside_commons(self):
        first = H.make_workspace(self.store, self.commons)
        H.make_workspace(self.store, self.commons,
                         name="sharing-workspace",
                         purpose="Workspace for sharing records")
        fetched = self.store.get_workspace(H.MEMBER, first["id"])
        self.assertEqual(fetched["name"], "analysis-workspace")
        workspaces = self.store.list_workspaces(H.MEMBER,
                                                self.commons["id"])
        self.assertEqual(len(workspaces), 2)
        self.assertEqual({w["commons_id"] for w in workspaces},
                         {self.commons["id"]})

    def test_empty_name_or_purpose_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_workspace(self.store, self.commons, name=" ")
        with self.assertRaises(ValidationError):
            H.make_workspace(self.store, self.commons, purpose="")

    def test_unknown_commons_and_workspace_not_found(self):
        with self.assertRaises(NotFoundError):
            self.store.create_workspace(H.MEMBER, "com-99", "Nowhere",
                                        "No such commons")
        with self.assertRaises(NotFoundError):
            self.store.get_workspace(H.MEMBER, "ws-99")

    def test_outsider_denied(self):
        workspace = H.make_workspace(self.store, self.commons)
        with self.assertRaises(PermissionDenied):
            H.make_workspace(self.store, self.commons, actor=H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.get_workspace(H.OUTSIDER, workspace["id"])
        with self.assertRaises(PermissionDenied):
            self.store.list_workspaces(H.OUTSIDER, self.commons["id"])


if __name__ == "__main__":
    unittest.main()
