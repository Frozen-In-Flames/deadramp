"""Core function 5: automation definition registry -- never executes."""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import ValidationError


class TestAutomations(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()

    def test_register_definition(self):
        automation = H.make_automation(self.store, self.org)
        self.assertTrue(automation["id"].startswith("aut-"))
        self.assertEqual(automation["steps"], ["collect", "review"])
        listed = self.store.list_automations(H.MEMBER, self.org["id"])
        self.assertEqual(len(listed), 1)
        view = self.store.get_automation(H.MEMBER, automation["id"])
        self.assertEqual(view["name"], "Nightly review")

    def test_empty_or_bad_steps_rejected(self):
        for bad in ([], "collect", ["ok", "  "]):
            with self.assertRaises(ValidationError):
                self.store.create_automation(
                    H.MEMBER, self.org["id"], "Bad", bad)

    def test_registry_never_executes(self):
        """Registering a definition changes no network, device,
        change, or telemetry record, and the store exposes no
        execution entry point at all."""
        network, device = H.make_estate(self.store, self.org)
        change = H.make_change(self.store, self.org, network)
        before = self.store.organization_summary(H.MEMBER, self.org["id"])
        self.store.create_automation(
            H.MEMBER, self.org["id"], "Auto tune", ["tune"])
        after = self.store.organization_summary(H.MEMBER, self.org["id"])
        self.assertEqual(after["automations"], before["automations"] + 1)
        for key in ("networks", "devices", "telemetry_records", "changes",
                    "alerts"):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(
            self.store.get_change(H.MEMBER, change["id"])["status"],
            "requested")
        self.assertEqual(
            self.store.get_device(H.MEMBER, device["id"])["state"],
            "registered")
        for name in dir(self.store):
            self.assertNotIn("execut", name.lower())
            self.assertNotIn("run_automation", name.lower())


if __name__ == "__main__":
    unittest.main()
