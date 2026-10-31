"""Core 10 Workflow definition registry (records only).

Traces to: UNION-SPEC.md Core 10 and Yello's pipeline-automation
claim — the registry holds workflow definitions as records; the
automation engine is Extended, so the store deliberately has no
execute-like operation at all, pinned here.
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import ValidationError


class TestWorkflows(unittest.TestCase):
    """Core 10: workflow definitions are records, never executions."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_workflow_shape(self):
        """Core 10: the workflow dict has exactly the contract's
        keys."""
        workflow = self.store.register_workflow(
            self.org["id"], "WFL-1", "Screening pipeline automation",
            H.MEMBER)
        self.assertEqual(set(workflow), {
            "id", "org_id", "workflow_ref", "label", "created_by",
            "created_utc"})
        self.assertEqual(workflow["id"], "wfl-1")

    def test_duplicate_workflow_ref_rejected(self):
        """Core 10 / SI-10: workflow_ref is unique within the
        organization."""
        self.store.register_workflow(self.org["id"], "WFL-1", "One", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_workflow(self.org["id"], "WFL-1", "Two",
                                         H.MEMBER)

    def test_registry_never_executes(self):
        """Core 10: the store exposes no execute-like operation —
        registering a definition is the whole function. (Yello's
        automation claim is answered with definition records; the
        engine is a named gap.)"""
        for name in dir(self.store):
            lowered = name.lower()
            self.assertNotIn("execute", lowered, name)
            self.assertNotIn("trigger", lowered, name)
            self.assertFalse(lowered.startswith("run_"), name)


if __name__ == "__main__":
    unittest.main()
