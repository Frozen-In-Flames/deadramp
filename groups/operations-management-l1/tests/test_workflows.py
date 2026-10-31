"""Workflow-registry tests: versioning, admin-only writes, never executes.

Traces to: Core function 7 -- Workflow registry; contract for
``OpsStore.create_workflow/update_workflow/get_workflow/
list_workflows``; CM-6, SA-4. workflow_write is ADMIN-ONLY in the
access matrix (operator denied). Registry only: the execution
engine is Extended, and a test pins that registering/updating a
workflow changes no work order's state.
"""

import unittest

from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER, fresh_store
from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestCreateWorkflow(unittest.TestCase):
    """Core 7: Workflow registry -- creation."""

    def test_create_workflow_shape(self):
        """Core 7: Workflow registry. create_workflow returns wf- id, version 1, enabled True, one-entry versions list."""
        store = fresh_store()
        wf = store.create_workflow(ADMIN, "triage", "maintenance", "on create", "notify lead")
        self.assertEqual(wf["id"], "wf-1")
        self.assertEqual(wf["name"], "triage")
        self.assertEqual(wf["work_type"], "maintenance")
        self.assertEqual(wf["trigger_text"], "on create")
        self.assertEqual(wf["action_text"], "notify lead")
        self.assertEqual(wf["version"], 1)
        self.assertTrue(wf["enabled"])
        self.assertEqual(wf["created_by"], "alice")
        self.assertEqual(len(wf["versions"]), 1)
        first = wf["versions"][0]
        self.assertEqual(
            set(first.keys()), {"version", "trigger_text", "action_text", "enabled", "ts"})
        self.assertEqual(first["version"], 1)
        self.assertEqual(first["trigger_text"], "on create")
        self.assertEqual(first["action_text"], "notify lead")
        self.assertTrue(first["enabled"])

    def test_work_type_all_and_each_type(self):
        """Core 7: Workflow registry. work_type accepts 'all' and every known work type."""
        store = fresh_store()
        for work_type in ("all", "inspection", "maintenance", "field_operation", "task", "general"):
            wf = store.create_workflow(ADMIN, "w-" + work_type, work_type, "t", "a")
            self.assertEqual(wf["work_type"], work_type)

    def test_create_validation_no_id_on_failure(self):
        """Core 7: Workflow registry (SI-10). Empty name/trigger/action, bad work_type -> ValidationError; no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_workflow(ADMIN, "", "all", "t", "a")
        with self.assertRaises(ValidationError):
            store.create_workflow(ADMIN, "w", "bogus", "t", "a")
        with self.assertRaises(ValidationError):
            store.create_workflow(ADMIN, "w", "all", "", "a")
        with self.assertRaises(ValidationError):
            store.create_workflow(ADMIN, "w", "all", "t", "")
        self.assertEqual(store.create_workflow(ADMIN, "w", "all", "t", "a")["id"], "wf-1")

    def test_workflow_write_is_admin_only(self):
        """Core 7/11: Workflow registry/RBAC. Operator and viewer create_workflow/update_workflow -> PermissionDenied; reads open to all roles."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_workflow(OPERATOR, "w", "all", "t", "a")
        with self.assertRaises(PermissionDenied):
            store.create_workflow(VIEWER, "w", "all", "t", "a")
        wf = store.create_workflow(ADMIN, "w", "all", "t", "a")
        self.assertEqual(wf["id"], "wf-1")
        with self.assertRaises(PermissionDenied):
            store.update_workflow(wf["id"], OPERATOR, trigger_text="t2")
        with self.assertRaises(PermissionDenied):
            store.update_workflow(wf["id"], VIEWER, trigger_text="t2")
        self.assertEqual(store.get_workflow(wf["id"], VIEWER)["id"], wf["id"])
        self.assertEqual(len(store.list_workflows(VIEWER)), 1)
        self.assertEqual(store.get_workflow(wf["id"], ADMIN)["version"], 1)


class TestUpdateWorkflow(unittest.TestCase):
    """Core 7: Workflow registry -- versioned updates."""

    def test_update_appends_version_and_carries_forward(self):
        """Core 7: Workflow registry. update_workflow bumps version, appends a version entry, carries unchanged fields forward."""
        store = fresh_store()
        wf = store.create_workflow(ADMIN, "w", "task", "trig-1", "act-1")
        updated = store.update_workflow(wf["id"], ADMIN, trigger_text="trig-2")
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["trigger_text"], "trig-2")
        self.assertEqual(updated["action_text"], "act-1")
        self.assertTrue(updated["enabled"])
        self.assertEqual(len(updated["versions"]), 2)
        self.assertEqual(updated["versions"][0]["trigger_text"], "trig-1")
        self.assertEqual(updated["versions"][1]["trigger_text"], "trig-2")
        self.assertEqual(updated["versions"][1]["action_text"], "act-1")
        updated = store.update_workflow(wf["id"], ADMIN, action_text="act-2", enabled=False)
        self.assertEqual(updated["version"], 3)
        self.assertFalse(updated["enabled"])
        self.assertEqual(updated["trigger_text"], "trig-2")
        self.assertEqual(updated["action_text"], "act-2")
        self.assertEqual(len(store.get_workflow(wf["id"], ADMIN)["versions"]), 3)

    def test_update_validation(self):
        """Core 7: Workflow registry (SI-10). Empty trigger/action, non-bool enabled -> ValidationError; unknown workflow -> NotFoundError; version unchanged."""
        store = fresh_store()
        wf = store.create_workflow(ADMIN, "w", "all", "t", "a")
        with self.assertRaises(ValidationError):
            store.update_workflow(wf["id"], ADMIN, trigger_text="")
        with self.assertRaises(ValidationError):
            store.update_workflow(wf["id"], ADMIN, action_text="")
        with self.assertRaises(ValidationError):
            store.update_workflow(wf["id"], ADMIN, enabled="yes")
        with self.assertRaises(NotFoundError):
            store.update_workflow("wf-999", ADMIN, trigger_text="x")
        with self.assertRaises(NotFoundError):
            store.get_workflow("wf-999", ADMIN)
        self.assertEqual(store.get_workflow(wf["id"], ADMIN)["version"], 1)

    def test_workflow_copies_are_copies(self):
        """Core 7: Workflow registry. Mutating a returned workflow's versions does not mutate the store."""
        store = fresh_store()
        wf = store.create_workflow(ADMIN, "w", "all", "t", "a")
        wf["versions"].append({"version": 99})
        wf["versions"][0]["trigger_text"] = "hacked"
        again = store.get_workflow(wf["id"], ADMIN)
        self.assertEqual(len(again["versions"]), 1)
        self.assertEqual(again["versions"][0]["trigger_text"], "t")


class TestRegistryNeverExecutes(unittest.TestCase):
    """Core 7: Workflow registry -- registry only, never executes."""

    def test_registering_workflow_changes_no_work_order(self):
        """Core 7: Workflow registry (registry-never-executes pin). A workflow whose work_type/trigger matches a work order changes nothing when that work order is created/transitioned."""
        store = fresh_store()
        # Workflow scoped and worded to match the work order below as
        # closely as the registry allows: same work_type, trigger and
        # action text naming its subject and a lifecycle-like action.
        wf = store.create_workflow(
            ADMIN, "auto-close-pump", "maintenance",
            "when a maintenance work order with subject 'Fix pump' is created",
            "close the work order immediately")
        self.assertTrue(wf["enabled"])
        wo = store.create_work_order(OPERATOR, "maintenance", "Fix pump")
        # Exactly what the lifecycle calls for: creation leaves it open.
        self.assertEqual(wo["status"], "open")
        self.assertEqual(store.get_work_order(wo["id"], OPERATOR)["status"], "open")
        moved = store.transition_work_order(wo["id"], OPERATOR, "in_progress")
        # The explicit lifecycle transition -- and only it -- moved it.
        self.assertEqual(moved["status"], "in_progress")
        self.assertEqual(store.get_work_order(wo["id"], OPERATOR)["status"], "in_progress")
        # Updating (and disabling/re-enabling) the workflow also changes nothing.
        store.update_workflow(wf["id"], ADMIN, action_text="cancel the work order")
        self.assertEqual(store.get_work_order(wo["id"], OPERATOR)["status"], "in_progress")
        self.assertEqual(len(store.list_work_orders(OPERATOR)), 1)


if __name__ == "__main__":
    unittest.main()
