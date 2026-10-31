"""Core: Configuration registries — form definitions and workflow
definitions, both held as data. Traces to UNION-SPEC core function 8
(form_design, configurable_workflows). The workflow registry NEVER
executes a definition: registering one changes no application, ever;
the execution engine is Extended."""

import unittest

import grants_helpers as H
from grants.errors import ValidationError


class TestForms(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_create_form_shape(self):
        form = self.store.create_form(
            H.MEMBER, self.program["id"], "Intake",
            [{"name": "lead", "kind": "text", "required": True},
             {"name": "ask", "kind": "money_cents", "required": True}])
        self.assertTrue(form["id"].startswith("frm-"))
        self.assertEqual(form["fields"][1]["kind"], "money_cents")

    def test_form_validation(self):
        pid = self.program["id"]
        for fields in (
            [],
            [{"name": "x", "kind": "video", "required": True}],
            [{"name": "x", "kind": "text", "required": True},
             {"name": "x", "kind": "text", "required": False}],
            [{"name": " ", "kind": "text", "required": True}],
            [{"name": "x", "kind": "text", "required": "yes"}],
            ["not-an-object"],
        ):
            with self.assertRaises(ValidationError, msg=repr(fields)):
                self.store.create_form(H.MEMBER, pid, "Bad", fields)


class TestWorkflows(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_create_workflow_shape(self):
        workflow = self.store.create_workflow(
            H.MEMBER, self.program["id"], "Standard review",
            ["submit", "review", "decide"])
        self.assertTrue(workflow["id"].startswith("wfl-"))
        self.assertEqual(workflow["steps"], ["submit", "review", "decide"])

    def test_workflow_validation(self):
        pid = self.program["id"]
        for steps in ([], ["ok", " "], "submit", [42]):
            with self.assertRaises(ValidationError, msg=repr(steps)):
                self.store.create_workflow(H.MEMBER, pid, "Bad", steps)

    def test_registry_never_executes(self):
        """Registering a workflow whose steps name the lifecycle
        transitions must not move any application: the registry is
        data, and there is no execution entry point on the store."""
        self.store.create_workflow(
            H.MEMBER, self.program["id"], "Auto flow",
            ["submit", "start_review", "decide"])
        app = H.make_application(self.store, self.program, self.org)
        self.assertEqual(
            self.store.get_application(H.MEMBER, app["id"])["status"], "draft")
        self.assertFalse(hasattr(self.store, "execute_workflow"))
        self.assertFalse(hasattr(self.store, "run_workflow"))


if __name__ == "__main__":
    unittest.main()
