"""Automation rule registry (Core function 8): records ONLY.

Claim trace: PagerDuty "the platform can trigger predefined
workflows" (automation_workflows). The registry stores the rules; it
never evaluates a condition and never executes an action -- execution
engines are Extended. These tests pin that boundary.
"""

import unittest

from custsvc.errors import PermissionDenied
from custsvc_helpers import ADMIN, AGENT, make_case, make_store


class TestRules(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, _, _ = make_store()
        self.rule = self.store.create_rule(
            "page on critical", "alert_ingested", "severity == critical",
            "page on-call responder", ADMIN)

    def test_rule_shape(self):
        self.assertTrue(self.rule["id"].startswith("rule-"))
        self.assertTrue(self.rule["enabled"])
        self.assertEqual(self.rule["trigger"], "alert_ingested")

    def test_enable_disable(self):
        rule = self.store.set_rule_enabled(self.rule["id"], False, ADMIN)
        self.assertFalse(rule["enabled"])
        rule = self.store.set_rule_enabled(self.rule["id"], True, ADMIN)
        self.assertTrue(rule["enabled"])

    def test_agent_cannot_write_rules(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_rule("x", "t", "c", "a", AGENT)
        with self.assertRaises(PermissionDenied):
            self.store.set_rule_enabled(self.rule["id"], False, AGENT)

    def test_registry_never_executes(self):
        # A rule whose trigger matches an ingested critical alert must
        # change nothing by itself: no case is created, no case is
        # assigned, no alert state moves. Execution is Extended.
        before_cases = self.store.list_cases(ADMIN)
        self.store.ingest_alert("mon", "critical event", "critical", AGENT)
        after_cases = self.store.list_cases(ADMIN)
        self.assertEqual(len(before_cases), len(after_cases))
        case = make_case(self.store, self.requester)
        self.assertIsNone(case["assignee"])


if __name__ == "__main__":
    unittest.main()
