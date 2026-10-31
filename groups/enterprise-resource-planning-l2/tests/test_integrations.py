"""Core function 14: integration & workflow registries --
records only, never execute (CM-6).

Registering an integration connects nothing; registering a
workflow runs nothing. The no-execution property is pinned
structurally: the store exposes no run/fire/execute/trigger
operation at all, and the HTTP surface has no such route either.
"""

import unittest

from erp.errors import ValidationError
from erp.store import ErpStore

from erp_helpers import OPERATOR, make_org, make_store

EXECUTION_VERBS = ("run", "fire", "execute", "trigger", "invoke",
                   "connect", "sync", "send", "dispatch")


class IntegrationTests(unittest.TestCase):
    def test_kinds_and_lifecycle(self):
        store, _ = make_store()
        org = make_org(store)
        platform = store.create_integration(
            OPERATOR, org["id"], "integration_platform",
            "ION integration platform (label)")
        gateway = store.create_integration(
            OPERATOR, org["id"], "api_gateway", "ION API Gateway (label)")
        self.assertEqual(platform["status"], "active")
        done = store.deactivate_integration(OPERATOR, gateway["id"])
        self.assertEqual(done["status"], "inactive")
        with self.assertRaises(ValidationError):
            store.create_integration(OPERATOR, org["id"], "email",
                                     "Not a kind")
        by_kind = store.list_integrations(
            OPERATOR, org_id=org["id"], kind="api_gateway")
        self.assertEqual([i["id"] for i in by_kind], [gateway["id"]])


class WorkflowTests(unittest.TestCase):
    def test_workflow_records_and_lifecycle(self):
        store, _ = make_store()
        org = make_org(store)
        workflow = store.create_workflow(
            OPERATOR, org["id"], "Expense approval flow (label)",
            "Expense submitted (label)")
        self.assertEqual(workflow["status"], "active")
        done = store.deactivate_workflow(OPERATOR, workflow["id"])
        self.assertEqual(done["status"], "inactive")
        with self.assertRaises(ValidationError):
            store.deactivate_workflow(OPERATOR, workflow["id"])

    def test_no_execution_surface_exists(self):
        """The registries never execute: no public operation on
        the store is an execution verb. (Private helpers and the
        record/audit internals are not operations.)"""
        operations = [name for name in dir(ErpStore)
                      if not name.startswith("_")]
        for name in operations:
            for verb in EXECUTION_VERBS:
                self.assertFalse(
                    name.startswith(verb),
                    "store exposes an execution operation: %s" % name)


if __name__ == "__main__":
    unittest.main()
