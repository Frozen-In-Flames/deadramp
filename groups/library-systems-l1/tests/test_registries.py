"""Registries: traces to the integration claims (both forks) and the
library_automation claim (SirsiDynix). The workflow registry records
definitions only and never executes."""
import unittest
from librarysys_helpers import BOB, seeded
from librarysys.errors import ValidationError

class RegistryTests(unittest.TestCase):
    def setUp(self): self.store, self.lib, self.item = seeded()
    def test_integration_records(self):
        rec = self.store.register_integration(self.lib["id"], "int-1", "sys-7", "Discovery link", BOB)
        self.assertEqual(rec["system_ref"], "sys-7")
        with self.assertRaises(ValidationError):
            self.store.register_integration(self.lib["id"], "int-1", "sys-8", "Dup", BOB)
        self.assertEqual(len(self.store.list_integrations(self.lib["id"], BOB)), 1)
    def test_workflow_registry_never_executes(self):
        self.store.register_workflow(self.lib["id"], "wfl-1", "Intake automation", BOB)
        self.assertFalse(hasattr(self.store, "execute_workflow"))
        self.assertFalse(hasattr(self.store, "run_workflow"))
        self.assertEqual(len(self.store.list_workflows(self.lib["id"], BOB)), 1)
if __name__ == "__main__": unittest.main()
