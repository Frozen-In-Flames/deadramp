"""Asset tests: lifecycle.

Traces to: Core function 3 -- Assets; contract for
``OpsStore.create_asset/transition_asset/get_asset/list_assets``;
CM-8, AU-2.
"""

import unittest

from opsmgmt_helpers import OPERATOR, VIEWER, fresh_store, make_store
from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestAssetCreate(unittest.TestCase):
    """Core 3: Assets -- creation."""

    def test_create_asset_shape_and_id(self):
        """Core 3: Assets. create_asset returns ast- id, status in_service, kind/project/attributes, provenance."""
        store, person, organization, project = make_store()
        asset = store.create_asset(
            "Pump", OPERATOR, kind="pump", project_id=project["id"], attributes={"serial": "S1"})
        self.assertEqual(asset["id"], "ast-1")
        self.assertEqual(asset["name"], "Pump")
        self.assertEqual(asset["kind"], "pump")
        self.assertEqual(asset["project_id"], project["id"])
        self.assertEqual(asset["status"], "in_service")
        self.assertEqual(asset["attributes"], {"serial": "S1"})
        self.assertEqual(asset["created_by"], "bob")

    def test_create_asset_defaults(self):
        """Core 3: Assets. kind defaults to equipment; project_id None; attributes {}."""
        store = fresh_store()
        asset = store.create_asset("Pump", OPERATOR)
        self.assertEqual(asset["kind"], "equipment")
        self.assertIsNone(asset["project_id"])
        self.assertEqual(asset["attributes"], {})

    def test_create_asset_validation_no_id_on_failure(self):
        """Core 3: Assets (SI-10). Empty name/kind, bad attributes -> ValidationError; unknown project -> NotFoundError; no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_asset("", OPERATOR)
        with self.assertRaises(ValidationError):
            store.create_asset("Pump", OPERATOR, kind="")
        with self.assertRaises(ValidationError):
            store.create_asset("Pump", OPERATOR, attributes="x")
        with self.assertRaises(NotFoundError):
            store.create_asset("Pump", OPERATOR, project_id="proj-999")
        self.assertEqual(store.create_asset("Pump", OPERATOR)["id"], "ast-1")

    def test_viewer_cannot_create_asset(self):
        """Core 3/11: Assets/RBAC. Viewer create_asset -> PermissionDenied, no id consumed."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_asset("Pump", VIEWER)
        self.assertEqual(store.create_asset("Pump", OPERATOR)["id"], "ast-1")


class TestAssetLifecycle(unittest.TestCase):
    """Core 3: Assets -- lifecycle transitions."""

    def test_full_lifecycle_to_retired_via_maintenance(self):
        """Core 3: Assets. in_service->in_maintenance->in_service->in_maintenance->retired."""
        store = fresh_store()
        asset = store.create_asset("Pump", OPERATOR)
        aid = asset["id"]
        self.assertEqual(store.transition_asset(aid, OPERATOR, "in_maintenance")["status"], "in_maintenance")
        self.assertEqual(store.transition_asset(aid, OPERATOR, "in_service")["status"], "in_service")
        self.assertEqual(store.transition_asset(aid, OPERATOR, "in_maintenance")["status"], "in_maintenance")
        self.assertEqual(store.transition_asset(aid, OPERATOR, "retired")["status"], "retired")

    def test_direct_retire_from_in_service(self):
        """Core 3: Assets. in_service->retired is valid."""
        store = fresh_store()
        asset = store.create_asset("Pump", OPERATOR)
        self.assertEqual(store.transition_asset(asset["id"], OPERATOR, "retired")["status"], "retired")

    def test_invalid_transitions_and_retired_terminal(self):
        """Core 3: Assets. Invalid/self/bogus transitions -> ValidationError, status unchanged; retired is terminal."""
        store = fresh_store()
        asset = store.create_asset("Pump", OPERATOR)
        aid = asset["id"]
        for bad in ("in_service", "bogus", "closed"):
            with self.assertRaises(ValidationError):
                store.transition_asset(aid, OPERATOR, bad)
        self.assertEqual(store.get_asset(aid, OPERATOR)["status"], "in_service")
        store.transition_asset(aid, OPERATOR, "retired")
        for bad in ("in_service", "in_maintenance", "retired"):
            with self.assertRaises(ValidationError):
                store.transition_asset(aid, OPERATOR, bad)
        with self.assertRaises(NotFoundError):
            store.transition_asset("ast-999", OPERATOR, "retired")
        with self.assertRaises(NotFoundError):
            store.get_asset("ast-999", OPERATOR)

    def test_list_assets_filters(self):
        """Core 3: Assets. list_assets filters by status and project_id; viewer may read."""
        store, person, organization, project = make_store()
        a1 = store.create_asset("Pump", OPERATOR, project_id=project["id"])
        a2 = store.create_asset("Valve", OPERATOR)
        store.transition_asset(a2["id"], OPERATOR, "in_maintenance")
        self.assertEqual([a["id"] for a in store.list_assets(OPERATOR, status="in_service")], [a1["id"]])
        self.assertEqual([a["id"] for a in store.list_assets(OPERATOR, status="in_maintenance")], [a2["id"]])
        self.assertEqual([a["id"] for a in store.list_assets(OPERATOR, project_id=project["id"])], [a1["id"]])
        self.assertEqual(len(store.list_assets(VIEWER)), 2)

    def test_asset_copies_are_copies(self):
        """Core 3: Assets. Mutating a returned asset's attributes does not mutate the store."""
        store = fresh_store()
        asset = store.create_asset("Pump", OPERATOR, attributes={"k": "v"})
        asset["attributes"]["k"] = "hacked"
        self.assertEqual(store.get_asset(asset["id"], OPERATOR)["attributes"], {"k": "v"})


if __name__ == "__main__":
    unittest.main()
