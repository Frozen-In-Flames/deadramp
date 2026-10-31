import unittest

from travel.errors import ValidationError

from travel_helpers import MEMBER, make_store


class TestIntegrations(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()

    def test_register_and_list(self):
        integration = self.store.register_integration(
            MEMBER, self.org["id"], "Expense feed", "api", "Expense system")
        self.assertEqual(integration["kind"], "api")
        listed = self.store.list_integrations(MEMBER, self.org["id"])
        self.assertEqual([i["id"] for i in listed], [integration["id"]])

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.register_integration(MEMBER, self.org["id"], "X",
                                            "webhook", "Y")

    def test_registry_never_executes(self):
        # There is no execute path anywhere on the store.
        for name in dir(self.store):
            self.assertNotIn("execute", name.lower())
            self.assertNotIn("invoke", name.lower())
            self.assertNotIn("run_integration", name.lower())

    def test_definition_carries_no_execution_state(self):
        integration = self.store.register_integration(
            MEMBER, self.org["id"], "Nightly file", "file", "Archive")
        for key in integration:
            self.assertNotIn(key, ("status", "last_run", "last_run_utc",
                                   "runs", "result"))


if __name__ == "__main__":
    unittest.main()
