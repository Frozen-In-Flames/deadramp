"""Core function 4: workflow definition registry — never executes."""

import unittest

import mdm_helpers as H
from mdm.errors import ValidationError


class TestWorkflows(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()

    def test_register_definition(self):
        workflow = self.store.create_workflow(
            H.MEMBER, self.org["id"], "MACD intake",
            ["intake", "verify", "schedule", "close"])
        self.assertEqual(workflow["steps"],
                         ["intake", "verify", "schedule", "close"])
        listed = self.store.list_workflows(H.MEMBER, self.org["id"])
        self.assertEqual(len(listed), 1)

    def test_empty_or_bad_steps_rejected(self):
        for bad in ([], "intake", ["ok", "  "]):
            with self.assertRaises(ValidationError):
                self.store.create_workflow(H.MEMBER, self.org["id"], "Bad", bad)

    def test_registry_never_executes(self):
        """Registering a workflow changes no order and no item, and
        the store exposes no execution entry point at all."""
        item = H.make_inventory(self.store, self.org)
        order = self.store.create_order(
            H.MEMBER, self.org["id"], "suspend", "Hold",
            inventory_id=item["id"])
        self.store.create_workflow(
            H.MEMBER, self.org["id"], "Auto suspend", ["suspend"])
        view = self.store.get_order(H.MEMBER, order["id"])
        self.assertEqual(view["status"], "requested")
        item_view = self.store.get_inventory_item(H.MEMBER, item["id"])
        self.assertEqual(item_view["provisioning_state"], "active")
        for name in dir(self.store):
            self.assertNotIn("execut", name.lower())
            self.assertNotIn("run_workflow", name.lower())


if __name__ == "__main__":
    unittest.main()
