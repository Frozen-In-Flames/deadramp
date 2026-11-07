"""Tests for the Final GAPS batch extensions (Singleton 40, CRM
L3-adjacent).

Traces to GAPS.md section "Singleton 40 — CRM L3-adjacent
(1 fork)", idx 399-403 (3 drafted build-extension, 2 drafted
stub-engine); dispositions and re-judgment grounds in BATCH.md.
All five entries close as labeled reference implementations:

- idx 399: no-code / low-code application development engine &
  model-based design tooling (build-extension, RE-JUDGED to
  reference) -- design definitions held as data, generation
  requests, and reported outcomes.
- idx 400: case management & BPM / workflow execution engines
  (stub-engine, reference as drafted) -- workflow definitions as
  data, run requests, and reported outcomes; no automation acts
  on a case.
- idx 401: decisioning engine (build-extension, RE-JUDGED to
  reference) -- decision requests whose signature refuses
  decision content, reported outcomes naming the decision only
  by opaque reference, evaluation figures verbatim as reported.
- idx 402: GenAI application tooling and AI / ML models
  generally (stub-engine, reference as drafted) -- requests and
  reported results only; no model runs, no score is computed.
- idx 403: managed cloud operations & application scaling
  platform (build-extension, RE-JUDGED to reference) --
  environment records named by opaque reference, scaling and
  operations reports stored as reported data, a deterministic
  rollup derived at read.

The core suite (test_privacy.py, test_audit.py, test_service.py,
etc.) is untouched and must still pass; these tests pin only the
new surface. All reference records carry reference_stub: True
with the corresponding *_here: False flags on their face.
"""

import copy
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"),
)

from crm.errors import NotFoundError, PermissionDenied, ValidationError  # noqa: E402
from crm.extensions import CrmExtensions  # noqa: E402
from crm_helpers import ADMIN, AUDITOR, OPERATOR, VIEWER, make_store  # noqa: E402

SCORE_KEYS = {"score", "rating", "rank", "probability", "confidence",
              "likelihood", "propensity"}
IDENTIFIER_KEYS = {"email", "phone", "phone_number", "ssn", "dob",
                   "date_of_birth", "address", "salary"}


def make_ext():
    store, account, contact = make_store()
    return CrmExtensions(store), store, account, contact


def _scan_keys(value, found):
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(key)
            _scan_keys(child, found)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _scan_keys(child, found)
    return found


class TestNoCodeDesign(unittest.TestCase):

    def test_design_definition_records_model_text_verbatim(self):
        ext, store, account, contact = make_ext()
        design = ext.register_design_definition(
            ADMIN, "onboarding-app", "MODEL: intake -> review")
        self.assertEqual(design["id"], "design-1")
        self.assertEqual(design["model_text"], "MODEL: intake -> review")
        self.assertEqual(design["revision_count"], 1)
        self.assertIsNone(design["module_id"])
        self.assertTrue(design["reference_stub"])
        self.assertFalse(design["designed_here"])
        self.assertFalse(design["generated_here"])
        self.assertEqual(design["state"], "recorded_definition_only")

    def test_design_stored_record_carries_no_derived_keys(self):
        ext, store, account, contact = make_ext()
        ext.register_design_definition(ADMIN, "app", "MODEL v1")
        stored = ext._records[("design_definition", "design-1")]
        self.assertEqual(set(stored.keys()), {
            "id", "name", "module_id", "reference_stub",
            "designed_here", "generated_here", "state",
            "created_by", "created_utc",
        })

    def test_design_revisions_append_only_and_current_derived(self):
        ext, store, account, contact = make_ext()
        ext.register_design_definition(ADMIN, "app", "MODEL v1")
        ext.revise_design_definition(ADMIN, "design-1", "MODEL v2")
        ext.revise_design_definition(ADMIN, "design-1", "MODEL v3")
        view = ext.get_design_definition("design-1", actor=VIEWER)
        self.assertEqual(view["model_text"], "MODEL v3")
        self.assertEqual(view["revision_count"], 3)
        revisions = ext.list_design_revisions("design-1", actor=VIEWER)
        self.assertEqual([r["revision"] for r in revisions], [1, 2, 3])
        self.assertEqual([r["model_text"] for r in revisions],
                         ["MODEL v1", "MODEL v2", "MODEL v3"])

    def test_design_write_is_admin_only(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(PermissionDenied):
            ext.register_design_definition(OPERATOR, "app", "MODEL")
        with self.assertRaises(PermissionDenied):
            ext.request_application_generation(OPERATOR, "design-1")
        self.assertEqual(ext.extension_summary(actor=ADMIN)["total"], 0)

    def test_generation_request_snapshots_revision_and_parameters(self):
        ext, store, account, contact = make_ext()
        ext.register_design_definition(ADMIN, "app", "MODEL v1")
        ext.revise_design_definition(ADMIN, "design-1", "MODEL v2")
        request = ext.request_application_generation(
            ADMIN, "design-1", parameters={"target": "web",
                                           "review_required": True,
                                           "builds": 2})
        self.assertEqual(request["id"], "genreq-1")
        self.assertEqual(request["design_revision"], 2)
        self.assertEqual(request["parameters"],
                         {"target": "web", "review_required": True,
                          "builds": 2})
        self.assertTrue(request["reference_stub"])
        self.assertFalse(request["generated_here"])
        self.assertFalse(request["executed_here"])
        self.assertEqual(request["state"], "recorded_request_only")

    def test_generation_parameters_refuse_scores_and_floats(self):
        ext, store, account, contact = make_ext()
        ext.register_design_definition(ADMIN, "app", "MODEL v1")
        with self.assertRaises(ValidationError):
            ext.request_application_generation(
                ADMIN, "design-1", parameters={"confidence": 90})
        with self.assertRaises(ValidationError):
            ext.request_application_generation(
                ADMIN, "design-1", parameters={"ratio": 1.5})

    def test_generation_report_outcome_vocabulary(self):
        ext, store, account, contact = make_ext()
        ext.register_design_definition(ADMIN, "app", "MODEL v1")
        ext.request_application_generation(ADMIN, "design-1")
        with self.assertRaises(ValidationError):
            ext.record_generation_report(
                ADMIN, "genreq-1", "generated")
        report = ext.record_generation_report(
            ADMIN, "genreq-1", "reported_completed",
            artifact_ref="appbuild-42")
        self.assertEqual(report["id"], "genrep-1")
        self.assertEqual(report["artifact_ref"], "appbuild-42")
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["generated_here"])
        self.assertFalse(report["artifact_held_here"])

    def test_generation_flow_leaves_bound_module_unchanged(self):
        ext, store, account, contact = make_ext()
        module = store.create_module(
            ADMIN, "intake-mod", "intake", settings_text="flag=1")
        before = copy.deepcopy(store.get_module(module["id"]))
        ext.register_design_definition(
            ADMIN, "app", "MODEL v1", module_id=module["id"])
        ext.request_application_generation(ADMIN, "design-1")
        ext.record_generation_report(
            ADMIN, "genreq-1", "reported_completed")
        after = store.get_module(module["id"])
        self.assertEqual(before, after)

    def test_design_against_missing_module_fails_without_consuming_id(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(NotFoundError):
            ext.register_design_definition(
                ADMIN, "app", "MODEL", module_id="mod-99")
        design = ext.register_design_definition(ADMIN, "app", "MODEL")
        self.assertEqual(design["id"], "design-1")


class TestWorkflowExecution(unittest.TestCase):

    def _case(self, store):
        return store.create_case(OPERATOR, "request", "casework")

    def test_workflow_definition_held_as_data(self):
        ext, store, account, contact = make_ext()
        workflow = ext.define_workflow(
            OPERATOR, "intake-flow",
            steps=[{"step": "triage", "action": "assign",
                    "ignored": "dropped"},
                   {"step": "review", "action": "decide"}])
        self.assertEqual(workflow["id"], "wflow-1")
        self.assertEqual(workflow["kind"], "bpm_workflow")
        self.assertEqual(workflow["steps"], [
            {"step": "triage", "action": "assign"},
            {"step": "review", "action": "decide"},
        ])
        self.assertTrue(workflow["reference_stub"])
        self.assertFalse(workflow["executed_here"])
        self.assertEqual(workflow["state"], "recorded_definition_only")

    def test_workflow_steps_validation(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(ValidationError):
            ext.define_workflow(OPERATOR, "bad",
                                steps=[{"step": "only"}])
        with self.assertRaises(ValidationError):
            ext.define_workflow(OPERATOR, "bad", steps="not-a-list")

    def test_run_and_report_leave_bound_case_unchanged(self):
        ext, store, account, contact = make_ext()
        case = self._case(store)
        before = copy.deepcopy(
            store.get_case(case["id"], now="2030-01-01T00:00:00Z"))
        workflow = ext.define_workflow(
            OPERATOR, "intake-flow", case_id=case["id"],
            steps=[{"step": "triage", "action": "assign"}])
        run = ext.request_workflow_run(OPERATOR, workflow["id"])
        self.assertEqual(run["id"], "wfrun-1")
        self.assertEqual(run["case_id"], case["id"])
        report = ext.record_workflow_run_report(
            OPERATOR, run["id"], "reported_completed", steps_reported=4)
        self.assertEqual(report["id"], "wfout-1")
        self.assertEqual(report["steps_reported"], 4)
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["executed_here"])
        after = store.get_case(case["id"], now="2030-01-01T00:00:00Z")
        self.assertEqual(before, after)

    def test_run_case_conflict_refused(self):
        ext, store, account, contact = make_ext()
        case_a = self._case(store)
        case_b = store.create_case(OPERATOR, "request", "other")
        workflow = ext.define_workflow(
            OPERATOR, "flow", case_id=case_a["id"])
        with self.assertRaises(ValidationError):
            ext.request_workflow_run(
                OPERATOR, workflow["id"], case_id=case_b["id"])

    def test_workflow_definition_requires_existing_case(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(NotFoundError):
            ext.define_workflow(OPERATOR, "flow", case_id="case-99")
        workflow = ext.define_workflow(OPERATOR, "flow")
        self.assertEqual(workflow["id"], "wflow-1")

    def test_run_report_rejects_negative_steps(self):
        ext, store, account, contact = make_ext()
        ext.define_workflow(OPERATOR, "flow")
        ext.request_workflow_run(OPERATOR, "wflow-1")
        with self.assertRaises(ValidationError):
            ext.record_workflow_run_report(
                OPERATOR, "wfrun-1", "reported_completed",
                steps_reported=-1)


class TestDecisioning(unittest.TestCase):

    def test_decision_request_shape_and_labels(self):
        ext, store, account, contact = make_ext()
        request = ext.register_decision_request(
            OPERATOR, "engine-7", "next best action")
        self.assertEqual(request["id"], "dreq-1")
        self.assertEqual(request["engine_ref"], "engine-7")
        self.assertTrue(request["reference_stub"])
        self.assertFalse(request["decided_here"])
        self.assertFalse(request["inference_here"])
        self.assertEqual(request["state"], "recorded_request_only")

    def test_decision_request_refuses_decision_content(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(TypeError):
            ext.register_decision_request(
                OPERATOR, "engine-7", "next best action",
                decision="approve")
        with self.assertRaises(TypeError):
            ext.register_decision_request(
                OPERATOR, "engine-7", "next best action", score=9)
        self.assertEqual(ext.extension_summary(actor=ADMIN)["total"], 0)

    def test_decision_report_names_decision_by_ref_only(self):
        ext, store, account, contact = make_ext()
        ext.register_decision_request(OPERATOR, "engine-7", "nba")
        report = ext.record_decision_report(
            OPERATOR, "dreq-1", "action_selected",
            decision_ref="decision-555")
        self.assertEqual(report["id"], "drep-1")
        self.assertEqual(report["outcome_label"], "action_selected")
        self.assertEqual(report["decision_ref"], "decision-555")
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["decided_here"])
        self.assertFalse(report["decision_held_here"])

    def test_decision_report_refuses_score_shaped_label(self):
        ext, store, account, contact = make_ext()
        ext.register_decision_request(OPERATOR, "engine-7", "nba")
        with self.assertRaises(ValidationError):
            ext.record_decision_report(
                OPERATOR, "dreq-1", "propensity")

    def test_decision_request_binding_validation(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(NotFoundError):
            ext.register_decision_request(
                OPERATOR, "engine-7", "nba", case_id="case-99")
        other = store.create_account(ADMIN, "ACCT-200")
        case = store.create_case(
            OPERATOR, "request", "bound", account_id=other["id"])
        with self.assertRaises(ValidationError):
            ext.register_decision_request(
                OPERATOR, "engine-7", "nba", case_id=case["id"],
                account_id=account["id"])
        request = ext.register_decision_request(
            OPERATOR, "engine-7", "nba", case_id=case["id"],
            account_id=other["id"])
        self.assertEqual(request["case_id"], case["id"])
        self.assertEqual(request["account_id"], other["id"])

    def test_decision_evaluation_verbatim(self):
        ext, store, account, contact = make_ext()
        evaluation = ext.record_decision_evaluation(
            OPERATOR, "engine-7", "acceptance_rate_reported", 61)
        self.assertEqual(evaluation["id"], "deval-1")
        self.assertEqual(evaluation["metric_value"], 61)
        self.assertTrue(evaluation["reference_stub"])
        self.assertFalse(evaluation["computed_here"])
        labelled = ext.record_decision_evaluation(
            OPERATOR, "engine-7", "lift", "reported_positive")
        self.assertEqual(labelled["metric_value"], "reported_positive")

    def test_decision_evaluation_rejects_floats_and_bools(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(ValidationError):
            ext.record_decision_evaluation(
                OPERATOR, "engine-7", "rate", 0.61)
        with self.assertRaises(ValidationError):
            ext.record_decision_evaluation(
                OPERATOR, "engine-7", "rate", True)


class TestGenAiTooling(unittest.TestCase):

    def test_ai_request_report_evaluation_form(self):
        ext, store, account, contact = make_ext()
        request = ext.register_ai_request(
            OPERATOR, "genai-tool-3", "draft a reply summary")
        self.assertEqual(request["id"], "aireq-1")
        self.assertTrue(request["reference_stub"])
        self.assertFalse(request["inference_here"])
        self.assertEqual(request["state"], "recorded_request_only")
        report = ext.record_ai_report(
            OPERATOR, "aireq-1", "draft_produced",
            result_ref="draft-9")
        self.assertEqual(report["id"], "air-1")
        self.assertEqual(report["result_ref"], "draft-9")
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["result_held_here"])
        evaluation = ext.record_ai_evaluation(
            OPERATOR, "genai-tool-3", "reviews_checked", 120)
        self.assertEqual(evaluation["metric_value"], 120)
        self.assertFalse(evaluation["computed_here"])

    def test_ai_request_refuses_result_content(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(TypeError):
            ext.register_ai_request(
                OPERATOR, "genai-tool-3", "draft", output="text")
        with self.assertRaises(TypeError):
            ext.register_ai_request(
                OPERATOR, "genai-tool-3", "draft", generated="text")

    def test_ai_report_refuses_score_shaped_label(self):
        ext, store, account, contact = make_ext()
        ext.register_ai_request(OPERATOR, "model-1", "classify")
        with self.assertRaises(ValidationError):
            ext.record_ai_report(OPERATOR, "aireq-1", "confidence")

    def test_ai_evaluation_rejects_floats(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(ValidationError):
            ext.record_ai_evaluation(OPERATOR, "model-1", "f1", 0.9)

    def test_ai_surface_creates_no_core_records(self):
        ext, store, account, contact = make_ext()
        before = store.report(ADMIN)
        ext.register_ai_request(OPERATOR, "model-1", "classify")
        ext.record_ai_report(OPERATOR, "aireq-1", "label_returned")
        ext.record_ai_evaluation(OPERATOR, "model-1", "cases", 10)
        after = store.report(ADMIN)
        self.assertEqual(before, after)


class TestManagedCloudOperations(unittest.TestCase):

    def _two_environments_with_reports(self, ext):
        env_a = ext.register_environment(
            ADMIN, "prod-us", platform_label="operator platform")
        env_b = ext.register_environment(ADMIN, "staging-us")
        ext.record_scaling_report(
            ADMIN, env_a["id"], "scaled_up", instances_reported=3)
        ext.record_scaling_report(
            ADMIN, env_a["id"], "scaled_up", instances_reported=4)
        ext.record_scaling_report(
            ADMIN, env_b["id"], "scaled_down")
        ext.record_operations_report(
            ADMIN, env_a["id"], "nightly_maintenance",
            detail="operator note", events_reported=12)
        return env_a, env_b

    def test_environment_record_labels(self):
        ext, store, account, contact = make_ext()
        env = ext.register_environment(ADMIN, "prod-us")
        self.assertEqual(env["id"], "env-1")
        self.assertEqual(env["environment_ref"], "prod-us")
        self.assertTrue(env["reference_stub"])
        self.assertFalse(env["hosted_here"])
        self.assertFalse(env["operated_here"])
        self.assertEqual(env["state"], "recorded_reference_only")
        with self.assertRaises(ValidationError):
            ext.register_environment(ADMIN, "prod-us")

    def test_environment_write_is_admin_only(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(PermissionDenied):
            ext.register_environment(OPERATOR, "prod-us")

    def test_scaling_and_operations_reports_verbatim(self):
        ext, store, account, contact = make_ext()
        env = ext.register_environment(ADMIN, "prod-us")
        scaling = ext.record_scaling_report(
            ADMIN, env["id"], "scaled_up", instances_reported=6)
        self.assertEqual(scaling["id"], "scale-1")
        self.assertEqual(scaling["instances_reported"], 6)
        self.assertTrue(scaling["reference_stub"])
        self.assertFalse(scaling["scaled_here"])
        ops = ext.record_operations_report(
            ADMIN, env["id"], "patch_window", detail="operator note",
            events_reported=3)
        self.assertEqual(ops["id"], "opsrep-1")
        self.assertEqual(ops["detail"], "operator note")
        self.assertEqual(ops["events_reported"], 3)
        self.assertFalse(ops["operated_here"])

    def test_reports_require_existing_environment(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(NotFoundError):
            ext.record_scaling_report(ADMIN, "env-99", "scaled_up")
        with self.assertRaises(NotFoundError):
            ext.record_operations_report(ADMIN, "env-99", "patch")
        env = ext.register_environment(ADMIN, "prod-us")
        self.assertEqual(env["id"], "env-1")

    def test_operations_summary_derived_rollup(self):
        ext, store, account, contact = make_ext()
        env_a, env_b = self._two_environments_with_reports(ext)
        summary = ext.operations_summary(actor=ADMIN)
        self.assertEqual(summary["method"], "recorded_operations_counts")
        self.assertTrue(summary["derived"])
        self.assertFalse(summary["operated_here"])
        self.assertEqual(summary["total_scaling_reports"], 3)
        self.assertEqual(summary["total_operations_reports"], 1)
        rows = {row["environment_id"]: row
                for row in summary["environments"]}
        self.assertEqual(rows[env_a["id"]]["scaling_reports"], 2)
        self.assertEqual(rows[env_a["id"]]["operations_reports"], 1)
        self.assertEqual(
            rows[env_a["id"]]["instances_reported_total"], 7)
        self.assertEqual(rows[env_b["id"]]["scaling_reports"], 1)
        self.assertEqual(rows[env_b["id"]]["operations_reports"], 0)
        self.assertEqual(
            rows[env_b["id"]]["instances_reported_total"], 0)

    def test_environment_stored_record_carries_no_derived_keys(self):
        ext, store, account, contact = make_ext()
        ext.register_environment(ADMIN, "prod-us")
        stored = ext._records[("environment", "env-1")]
        self.assertEqual(set(stored.keys()), {
            "id", "environment_ref", "platform_label",
            "reference_stub", "hosted_here", "operated_here",
            "state", "created_by", "created_utc",
        })


class TestExtensionInvariants(unittest.TestCase):

    def test_mutations_and_denials_are_audited(self):
        ext, store, account, contact = make_ext()
        ext.register_design_definition(ADMIN, "app", "MODEL")
        with self.assertRaises(PermissionDenied):
            ext.register_design_definition(OPERATOR, "app2", "MODEL")
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("ext_design_definition_register", actions)
        self.assertIn("ext_design_definition_register:denied", actions)

    def test_auditor_denied_extension_writes_and_reads(self):
        ext, store, account, contact = make_ext()
        ext.register_environment(ADMIN, "prod-us")
        with self.assertRaises(PermissionDenied):
            ext.register_environment(AUDITOR, "other")
        with self.assertRaises(PermissionDenied):
            ext.record_scaling_report(AUDITOR, "env-1", "scaled_up")
        with self.assertRaises(PermissionDenied):
            ext.list_environments(actor=AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.get_environment("env-1", actor=AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.operations_summary(actor=AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.extension_summary(actor=AUDITOR)

    def test_audit_chain_verifies_after_extension_operations(self):
        ext, store, account, contact = make_ext()
        ext.register_design_definition(ADMIN, "app", "MODEL")
        ext.request_application_generation(ADMIN, "design-1")
        ext.register_environment(ADMIN, "prod-us")
        ext.record_scaling_report(ADMIN, "env-1", "scaled_up")
        with self.assertRaises(PermissionDenied):
            ext.register_environment(OPERATOR, "other")
        self.assertEqual(store.audit.verify_chain(), (True, None))
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("ext_environment_register:denied", actions)

    def test_failed_audit_write_rolls_back(self):
        ext, store, account, contact = make_ext()
        real_audit = store.audit

        class FailingAudit:
            def record(self, actor, action, target, details=None):
                raise RuntimeError("audit backend down")

        store.audit = FailingAudit()
        try:
            with self.assertRaises(RuntimeError):
                ext.register_environment(ADMIN, "prod-us")
        finally:
            store.audit = real_audit
        self.assertEqual(ext.list_environments(), [])
        env = ext.register_environment(ADMIN, "prod-us")
        self.assertEqual(env["id"], "env-1")

    def test_failed_operations_consume_no_ids(self):
        ext, store, account, contact = make_ext()
        with self.assertRaises(NotFoundError):
            ext.request_application_generation(ADMIN, "design-99")
        with self.assertRaises(NotFoundError):
            ext.register_decision_request(
                OPERATOR, "engine-7", "nba", case_id="case-99")
        ext.register_design_definition(ADMIN, "app", "MODEL")
        request = ext.request_application_generation(ADMIN, "design-1")
        self.assertEqual(request["id"], "genreq-1")
        decision = ext.register_decision_request(
            OPERATOR, "engine-7", "nba")
        self.assertEqual(decision["id"], "dreq-1")

    def _exercise_every_surface(self, ext, store):
        case = store.create_case(OPERATOR, "request", "casework")
        module = store.create_module(ADMIN, "mod-x", "general",
                                      settings_text="flag=1")
        ext.register_design_definition(
            ADMIN, "app", "MODEL", module_id=module["id"])
        ext.request_application_generation(
            ADMIN, "design-1", parameters={"target": "web"})
        ext.record_generation_report(
            ADMIN, "genreq-1", "reported_completed",
            artifact_ref="build-1")
        ext.define_workflow(OPERATOR, "flow", case_id=case["id"],
                            steps=[{"step": "s", "action": "a"}])
        ext.request_workflow_run(OPERATOR, "wflow-1")
        ext.record_workflow_run_report(
            OPERATOR, "wfrun-1", "reported_completed",
            steps_reported=1)
        ext.register_decision_request(
            OPERATOR, "engine-7", "nba", case_id=case["id"])
        ext.record_decision_report(
            OPERATOR, "dreq-1", "action_selected",
            decision_ref="decision-1")
        ext.record_decision_evaluation(
            OPERATOR, "engine-7", "acceptance", 5)
        ext.register_ai_request(OPERATOR, "model-1", "classify",
                                case_id=case["id"])
        ext.record_ai_report(OPERATOR, "aireq-1", "label_returned",
                             result_ref="result-1")
        ext.record_ai_evaluation(OPERATOR, "model-1", "cases", 5)
        ext.register_environment(ADMIN, "prod-us")
        ext.record_scaling_report(
            ADMIN, "env-1", "scaled_up", instances_reported=2)
        ext.record_operations_report(
            ADMIN, "env-1", "patch_window", events_reported=1)

    def test_no_score_or_identifier_key_anywhere(self):
        ext, store, account, contact = make_ext()
        self._exercise_every_surface(ext, store)
        found = set()
        for record in ext._records.values():
            _scan_keys(record, found)
        views = [
            ext.get_design_definition("design-1"),
            ext.list_design_revisions("design-1"),
            ext.operations_summary(),
            ext.extension_summary(),
        ]
        for view in views:
            _scan_keys(view, found)
        self.assertFalse(found & SCORE_KEYS,
                         "score-shaped keys present: %s"
                         % (found & SCORE_KEYS,))
        self.assertFalse(found & IDENTIFIER_KEYS,
                         "identifier keys present: %s"
                         % (found & IDENTIFIER_KEYS,))

    def test_extension_summary_counts(self):
        ext, store, account, contact = make_ext()
        self._exercise_every_surface(ext, store)
        summary = ext.extension_summary(actor=ADMIN)
        self.assertEqual(summary["method"], "extension_record_counts")
        self.assertTrue(summary["derived"])
        self.assertEqual(summary["by_kind"]["design_definition"], 1)
        self.assertEqual(summary["by_kind"]["design_revision"], 1)
        self.assertEqual(summary["by_kind"]["generation_request"], 1)
        self.assertEqual(summary["by_kind"]["generation_report"], 1)
        self.assertEqual(summary["by_kind"]["workflow"], 1)
        self.assertEqual(summary["by_kind"]["workflow_run"], 1)
        self.assertEqual(summary["by_kind"]["workflow_run_report"], 1)
        self.assertEqual(summary["by_kind"]["decision_request"], 1)
        self.assertEqual(summary["by_kind"]["decision_report"], 1)
        self.assertEqual(summary["by_kind"]["decision_evaluation"], 1)
        self.assertEqual(summary["by_kind"]["ai_request"], 1)
        self.assertEqual(summary["by_kind"]["ai_report"], 1)
        self.assertEqual(summary["by_kind"]["ai_evaluation"], 1)
        self.assertEqual(summary["by_kind"]["environment"], 1)
        self.assertEqual(summary["by_kind"]["scaling_report"], 1)
        self.assertEqual(summary["by_kind"]["operations_report"], 1)
        self.assertEqual(summary["total"], 16)


class TestNegativeControlEnvironmentRollup(unittest.TestCase):
    """Mutation-verified negative control for this batch's
    derivation point.

    The load-bearing claim of the managed-operations reference
    surface (idx 403) is that ``operations_summary`` counts the
    recorded scaling reports per environment. If the rollup
    derivation is disabled, the canonical summary must visibly
    break; the mutant below overrides the single derivation
    method (``CrmExtensions._environment_rollup``) to return an
    empty mapping, proving the canonical fixture's expectations
    are carried by the derivation, not hard-coded. The drill in
    tests/README.md patches the same line in the real module.
    """

    def _fixture(self, ext):
        env_a = ext.register_environment(ADMIN, "prod-us")
        env_b = ext.register_environment(ADMIN, "staging-us")
        ext.record_scaling_report(
            ADMIN, env_a["id"], "scaled_up", instances_reported=3)
        ext.record_scaling_report(
            ADMIN, env_a["id"], "scaled_up", instances_reported=4)
        ext.record_scaling_report(
            ADMIN, env_b["id"], "scaled_down")
        ext.record_operations_report(
            ADMIN, env_a["id"], "nightly_maintenance")
        return env_a, env_b

    def _expected(self, ext, env_a, env_b):
        summary = ext.operations_summary(actor=ADMIN)
        rows = {row["environment_id"]: row
                for row in summary["environments"]}
        self.assertEqual(rows[env_a["id"]]["scaling_reports"], 2)
        self.assertEqual(rows[env_a["id"]]["operations_reports"], 1)
        self.assertEqual(
            rows[env_a["id"]]["instances_reported_total"], 7)
        self.assertEqual(rows[env_b["id"]]["scaling_reports"], 1)

    def test_canonical_rollup_but_mutant_does_not(self):
        store, account, contact = make_store()
        canonical = CrmExtensions(store)
        env_a, env_b = self._fixture(canonical)
        self._expected(canonical, env_a, env_b)

        class MutantCrmExtensions(CrmExtensions):
            def _environment_rollup(self, scaling_reports,
                                    operations_reports):
                return {}

        store2, account2, contact2 = make_store()
        mutant = MutantCrmExtensions(store2)
        m_env_a, m_env_b = self._fixture(mutant)
        with self.assertRaises(AssertionError):
            self._expected(mutant, m_env_a, m_env_b)


if __name__ == "__main__":
    unittest.main()
