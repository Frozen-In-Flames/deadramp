"""Rules-registry tests: versioning and admin-only writes.

Traces to: Core function 7 -- Rules registry; contract for
``ContactStore.create_rule/update_rule/get_rule/list_rules``.
rule_write is ADMIN-ONLY in the access matrix (operator denied).
"""

import unittest

from contact_helpers import ADMIN, OPERATOR, VIEWER, fresh_store
from contact.errors import NotFoundError, PermissionDenied, ValidationError


class TestCreateRule(unittest.TestCase):
    """Core 7: Rules -- creation."""

    def test_create_rule_shape(self):
        """Core 7: Rules. create_rule returns rule- id, version 1, enabled True, one-entry versions list."""
        store = fresh_store()
        rule = store.create_rule(ADMIN, "vip-claims", "claim", "priority == high", "page on-call")
        self.assertEqual(rule["id"], "rule-1")
        self.assertEqual(rule["version"], 1)
        self.assertTrue(rule["enabled"])
        self.assertEqual(rule["condition"], "priority == high")
        self.assertEqual(len(rule["versions"]), 1)
        first = rule["versions"][0]
        self.assertEqual(set(first.keys()), {"version", "condition", "action_text", "enabled", "ts"})
        self.assertEqual(first["version"], 1)

    def test_case_type_all_and_each_type(self):
        """Core 7: Rules. case_type accepts 'all' and every known case type."""
        store = fresh_store()
        for case_type in ("all", "claim", "callback", "activity", "inquiry", "general"):
            rule = store.create_rule(ADMIN, "r-" + case_type, case_type, "c", "a")
            self.assertEqual(rule["case_type"], case_type)

    def test_create_validation_no_id_on_failure(self):
        """Core 7: Rules (SI-10). Empty name/condition/action, bad case_type -> ValidationError; no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_rule(ADMIN, "", "all", "c", "a")
        with self.assertRaises(ValidationError):
            store.create_rule(ADMIN, "r", "bogus", "c", "a")
        with self.assertRaises(ValidationError):
            store.create_rule(ADMIN, "r", "all", "", "a")
        with self.assertRaises(ValidationError):
            store.create_rule(ADMIN, "r", "all", "c", "")
        self.assertEqual(store.create_rule(ADMIN, "r", "all", "c", "a")["id"], "rule-1")

    def test_rule_write_is_admin_only(self):
        """Core 7/11: Rules/RBAC. Operator and viewer create_rule/update_rule -> PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_rule(OPERATOR, "r", "all", "c", "a")
        with self.assertRaises(PermissionDenied):
            store.create_rule(VIEWER, "r", "all", "c", "a")
        rule = store.create_rule(ADMIN, "r", "all", "c", "a")
        with self.assertRaises(PermissionDenied):
            store.update_rule(rule["id"], OPERATOR, condition="c2")
        # Reads are open to all roles.
        self.assertEqual(store.get_rule(rule["id"], VIEWER)["id"], rule["id"])
        self.assertEqual(len(store.list_rules(VIEWER)), 1)


class TestUpdateRule(unittest.TestCase):
    """Core 7: Rules -- versioned updates."""

    def test_update_appends_version_and_carries_forward(self):
        """Core 7: Rules. update_rule bumps version, appends a version entry, carries unchanged fields forward."""
        store = fresh_store()
        rule = store.create_rule(ADMIN, "r", "claim", "cond-1", "act-1")
        updated = store.update_rule(rule["id"], ADMIN, condition="cond-2")
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["condition"], "cond-2")
        self.assertEqual(updated["action_text"], "act-1")
        self.assertTrue(updated["enabled"])
        self.assertEqual(len(updated["versions"]), 2)
        self.assertEqual(updated["versions"][0]["condition"], "cond-1")
        self.assertEqual(updated["versions"][1]["condition"], "cond-2")
        updated = store.update_rule(rule["id"], ADMIN, enabled=False)
        self.assertEqual(updated["version"], 3)
        self.assertFalse(updated["enabled"])
        self.assertEqual(updated["condition"], "cond-2")
        self.assertEqual(len(store.get_rule(rule["id"], ADMIN)["versions"]), 3)

    def test_update_validation(self):
        """Core 7: Rules (SI-10). Empty condition/action, non-bool enabled -> ValidationError; unknown rule -> NotFoundError; version unchanged."""
        store = fresh_store()
        rule = store.create_rule(ADMIN, "r", "all", "c", "a")
        with self.assertRaises(ValidationError):
            store.update_rule(rule["id"], ADMIN, condition="")
        with self.assertRaises(ValidationError):
            store.update_rule(rule["id"], ADMIN, action_text="")
        with self.assertRaises(ValidationError):
            store.update_rule(rule["id"], ADMIN, enabled="yes")
        with self.assertRaises(NotFoundError):
            store.update_rule("rule-999", ADMIN, condition="x")
        self.assertEqual(store.get_rule(rule["id"], ADMIN)["version"], 1)

    def test_rule_copies_are_copies(self):
        """Core 7: Rules. Mutating a returned rule's versions does not mutate the store."""
        store = fresh_store()
        rule = store.create_rule(ADMIN, "r", "all", "c", "a")
        rule["versions"].append({"version": 99})
        rule["versions"][0]["condition"] = "hacked"
        again = store.get_rule(rule["id"], ADMIN)
        self.assertEqual(len(again["versions"]), 1)
        self.assertEqual(again["versions"][0]["condition"], "c")


if __name__ == "__main__":
    unittest.main()
