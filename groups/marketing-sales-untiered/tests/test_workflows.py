"""Core function 6: the workflow registry — records only, NEVER
executes (taxonomy family workflow_automation). Registering or
toggling a workflow runs nothing, sends nothing, and changes no
other record; the package exposes no execution entry point."""

import inspect
import unittest

from marketsales_helpers import ADMIN, OPERATOR, make_org, make_store

import marketsales.store as store_module

from marketsales.errors import ValidationError


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org = make_org(self.store)

    def test_register_and_toggle(self):
        workflow = self.store.create_workflow(
            OPERATOR, self.org["id"], "Weekly opportunity digest",
            "new opportunity posted", cadence_label="weekly")
        self.assertTrue(workflow["active"])
        toggled = self.store.set_workflow_active(OPERATOR, workflow["id"],
                                                 False)
        self.assertFalse(toggled["active"])
        with self.assertRaises(ValidationError):
            self.store.set_workflow_active(OPERATOR, workflow["id"], "yes")

    def test_registering_executes_nothing(self):
        before = self.store.summary(ADMIN)
        self.store.create_workflow(
            OPERATOR, self.org["id"], "Digest", "new opportunity posted")
        after = self.store.summary(ADMIN)
        self.assertEqual(after["workflows"], before["workflows"] + 1)
        for key in ("opportunities", "evaluations", "campaigns",
                    "deliveries", "engagements", "suppressions",
                    "content_versions", "pipeline_entries"):
            self.assertEqual(after[key], before[key], key)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertEqual(actions[-1], "create_workflow")

    def test_no_execution_entry_point_exists(self):
        store_methods = [name for name, _ in
                         inspect.getmembers(store_module.MarketSalesStore,
                                            inspect.isfunction)]
        for name in store_methods:
            self.assertNotIn("execut", name)
            self.assertNotIn("run_", name)
        self.assertFalse(hasattr(store_module, "execute_workflow"))


if __name__ == "__main__":
    unittest.main()
