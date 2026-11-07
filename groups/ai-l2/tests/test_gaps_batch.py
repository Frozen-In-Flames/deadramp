"""Final GAPS batch tests — Group 9 (Artificial Intelligence L2).

Pins the extension surface in ``src/aigateway/extensions.py``
against the group's 6 open Extended entries (see ``../BATCH.md``):

- Learned AI/ML inference (idx 81) — reference implementation:
  request/outcome records, prompt named only by digest, no core
  request record is ever created by the surface.
- Agentic & automated workflow engines (idx 82) — reference:
  definitions held as data; a run request executes nothing and
  creates no core request or session.
- Document processing & generation workloads (idx 83) —
  reference: job/result records naming documents and outputs by
  opaque reference only.
- Analytics, dashboards & reporting (idx 84) — built: dashboard
  definitions hold panel labels only and store no figure; the
  figures derive at read from the core's own records over exactly
  the records visible to the actor.
- Contact center & customer experience (idx 85) — reference:
  case/event/outcome records; no conversation content can exist.
- Vertical domain applications (idx 86) — built: application
  profiles over the core registry plus activity records and
  derived views; the verticals' own engines are stated absent.

Plus the batch's fresh negative control: the figure-inclusion
seam ``_counts_toward_figures`` — a mutant that counts only
completed request records must understate the derived figures
(blocked records count, mirroring the core's usage accounting).
"""

import unittest

import aigateway_helpers as helpers
from aigateway.errors import (
    NotFoundError,
    PermissionDenied,
    PolicyBlocked,
    ValidationError,
)
from aigateway.extensions import AIGatewayExtensions

ADMIN = helpers.ADMIN
MEMBER = helpers.MEMBER
VIEWER = helpers.VIEWER
OTHER_MEMBER = helpers.OTHER_MEMBER

DIGEST = "a" * 64


def make_ext():
    """Fresh core store (helpers fixture) + extension wrapper."""
    store, audit, model = helpers.make_store()
    return store, audit, model, AIGatewayExtensions(store)


def traffic(store):
    """One completed and one policy-blocked core invocation."""
    store.add_rule("input", "term", "badword", ADMIN)
    completed = store.invoke("echoer", "hello world", MEMBER)
    try:
        store.invoke("echoer", "a badword prompt", MEMBER)
    except PolicyBlocked:
        pass
    return completed


class TestInferenceReference(unittest.TestCase):
    """Idx 81 — learned inference ships as labeled records only."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_request_record_shape_and_labels(self):
        rec = self.ext.register_inference_request(
            "echoer", MEMBER, prompt_digest=DIGEST)
        self.assertEqual(rec["id"], "ireq-1")
        self.assertEqual(rec["model"], "echoer")
        self.assertEqual(rec["model_version"], 1)
        self.assertEqual(rec["prompt_digest"], DIGEST)
        self.assertTrue(rec["reference_stub"])
        self.assertFalse(rec["inference_here"])
        self.assertFalse(rec["executed_here"])
        self.assertEqual(rec["state"], "recorded_reference_only")
        self.assertEqual(rec["created_by"], "bob")

    def test_request_creates_no_core_request_record(self):
        self.ext.register_inference_request("echoer", MEMBER)
        self.assertEqual(self.store.list_requests(ADMIN), [])
        self.assertEqual(self.store.list_sessions(ADMIN), [])

    def test_prompt_and_output_content_have_no_parameter(self):
        with self.assertRaises(TypeError):
            self.ext.register_inference_request(
                "echoer", MEMBER, prompt="hello")
        rec = self.ext.register_inference_request("echoer", MEMBER)
        with self.assertRaises(TypeError):
            self.ext.record_inference_outcome(
                rec["id"], "done", MEMBER, output="text")

    def test_outcome_record(self):
        rec = self.ext.register_inference_request("echoer", MEMBER)
        out = self.ext.record_inference_outcome(
            rec["id"], "completed_elsewhere", MEMBER, output_ref="ext-1")
        self.assertEqual(out["id"], "iout-1")
        self.assertEqual(out["request_id"], rec["id"])
        self.assertTrue(out["reference_stub"])
        self.assertFalse(out["result_held_here"])
        self.assertEqual(
            len(self.ext.list_inference_outcomes(rec["id"], ADMIN)), 1)

    def test_unknown_model_and_bad_digest_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_inference_request("nope", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_inference_request(
                "echoer", MEMBER, prompt_digest="not-a-digest")

    def test_viewer_denied_and_denial_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_inference_request("echoer", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_inference_request_register:denied", actions)


class TestAgentWorkflowReference(unittest.TestCase):
    """Idx 82 — workflow definitions are data; nothing executes."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_definition_shape(self):
        wf = self.ext.define_agent_workflow(
            "triage", ADMIN, steps=["intake", "route"], model_name="echoer")
        self.assertEqual(wf["id"], "awf-1")
        self.assertEqual(wf["steps"], ["intake", "route"])
        self.assertEqual(wf["model"], "echoer")
        self.assertTrue(wf["definition_only"])
        self.assertTrue(wf["reference_stub"])
        self.assertFalse(wf["executed_here"])

    def test_run_request_executes_nothing(self):
        wf = self.ext.define_agent_workflow("triage", ADMIN)
        run = self.ext.request_agent_run(wf["id"], MEMBER, input_ref="in-1")
        self.assertEqual(run["state"], "recorded_request_only")
        self.assertFalse(run["executed_here"])
        self.assertEqual(self.store.list_requests(ADMIN), [])
        self.assertEqual(self.store.list_sessions(ADMIN), [])

    def test_outcome_record(self):
        wf = self.ext.define_agent_workflow("triage", ADMIN)
        run = self.ext.request_agent_run(wf["id"], MEMBER)
        out = self.ext.record_agent_run_outcome(
            run["id"], "finished", MEMBER, output_ref="out-1")
        self.assertTrue(out["reference_stub"])
        self.assertFalse(out["result_held_here"])
        with self.assertRaises(NotFoundError):
            self.ext.request_agent_run("awf-99", MEMBER)


class TestDocumentReference(unittest.TestCase):
    """Idx 83 — document jobs name documents by reference only."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_job_shape_and_labels(self):
        job = self.ext.register_document_job(
            "extraction", "doc-42", MEMBER, document_digest=DIGEST)
        self.assertEqual(job["id"], "dcj-1")
        self.assertEqual(job["document_digest"], DIGEST)
        self.assertTrue(job["reference_stub"])
        self.assertFalse(job["processed_here"])
        self.assertFalse(job["generated_here"])
        self.assertFalse(job["content_held"])

    def test_content_has_no_parameter(self):
        with self.assertRaises(TypeError):
            self.ext.register_document_job(
                "extraction", "doc-42", MEMBER, document_text="...")
        with self.assertRaises(TypeError):
            self.ext.register_document_job(
                "generation", "doc-42", MEMBER, content="...")
        job = self.ext.register_document_job("generation", "doc-42", MEMBER)
        with self.assertRaises(TypeError):
            self.ext.record_document_result(
                job["id"], "done", MEMBER, summary_text="...")

    def test_result_record_and_kind_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.register_document_job("teleport", "doc-42", MEMBER)
        job = self.ext.register_document_job("summarization", "doc-42", MEMBER)
        res = self.ext.record_document_result(
            job["id"], "summarized_elsewhere", MEMBER, result_ref="sum-1")
        self.assertFalse(res["result_held_here"])
        self.assertEqual(len(self.ext.list_document_results(job["id"])), 1)


class TestAnalyticsBuilt(unittest.TestCase):
    """Idx 84 — figures derive at read from the core's records."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_definition_stores_no_figure(self):
        dash = self.ext.define_dashboard(
            "ops", ADMIN, panels=["requests_by_status", "token_totals"])
        self.assertEqual(
            set(dash.keys()),
            {"id", "name", "panels", "created_by", "created_utc"})
        self.assertEqual(dash["panels"],
                         ["requests_by_status", "token_totals"])

    def test_unknown_panel_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.define_dashboard("ops", ADMIN, panels=["secrets"])

    def test_figures_cover_completed_and_blocked(self):
        traffic(self.store)
        view = self.ext.analytics_view(ADMIN)
        records = self.store.list_requests(ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["requests"]["total"], 2)
        self.assertEqual(view["requests"]["by_status"],
                         {"completed": 1, "blocked_input": 1})
        self.assertEqual(view["requests"]["by_model"], {"echoer": 2})
        self.assertEqual(
            view["requests"]["total_tokens"],
            sum(r["usage"]["total_tokens"] for r in records))
        self.assertEqual(view["models_total"], 1)
        self.assertEqual(view["models_by_status"], {"active": 1})
        self.assertEqual(view["usage_current_month"]["owner"], "alice")

    def test_figures_scoped_to_records_visible_to_actor(self):
        traffic(self.store)
        self.assertEqual(
            self.ext.analytics_view(MEMBER)["requests"]["total"], 2)
        self.assertEqual(
            self.ext.analytics_view(OTHER_MEMBER)["requests"]["total"], 0)

    def test_dashboard_view_panels_and_freshness(self):
        dash = self.ext.define_dashboard(
            "ops", ADMIN, panels=["requests_by_status"])
        before = self.ext.dashboard_view(dash["id"], ADMIN)
        self.assertEqual(before["panels"]["requests_by_status"]["total"], 0)
        traffic(self.store)
        after = self.ext.dashboard_view(dash["id"], ADMIN)
        self.assertEqual(
            set(after["panels"].keys()), {"requests_by_status"})
        self.assertEqual(after["panels"]["requests_by_status"]["total"], 2)
        stored = self.ext.get_dashboard(dash["id"], ADMIN)
        self.assertNotIn("panels", stored.get("figures", {}))
        self.assertEqual(
            set(stored.keys()),
            {"id", "name", "panels", "created_by", "created_utc"})


class _CompletedOnlyExtensions(AIGatewayExtensions):
    """Mutant: counts only completed request records."""

    @staticmethod
    def _counts_toward_figures(record):
        return record["status"] == "completed"


class TestFigureInclusionNegativeControl(unittest.TestCase):
    """Fresh negative control for the figure-inclusion seam.

    Canonical expectation (UNION-SPEC core function 4): blocked
    records count toward the platform's figures, as they do in
    the core's usage accounting. The mutant seam counts only
    completed records and must understate the total.
    """

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()
        traffic(self.store)
        self.mutant = _CompletedOnlyExtensions(self.store)

    def test_canonical_counts_blocked_records(self):
        view = self.ext.analytics_view(ADMIN)
        self.assertEqual(view["requests"]["total"], 2)
        self.assertEqual(
            view["requests"]["by_status"].get("blocked_input"), 1)

    def test_mutant_understates_the_figures(self):
        view = self.mutant.analytics_view(ADMIN)
        self.assertEqual(view["requests"]["total"], 1)
        self.assertNotIn("blocked_input", view["requests"]["by_status"])
        self.assertLess(view["requests"]["total_tokens"],
                        self.ext.analytics_view(ADMIN)
                        ["requests"]["total_tokens"])

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self.mutant.analytics_view(ADMIN)["requests"]["total"], 2)


class TestContactCenterReference(unittest.TestCase):
    """Idx 85 — contact cases are records; nothing is routed."""

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_case_shape_and_labels(self):
        case = self.ext.register_contact_case(
            "case-9", MEMBER, channel="chat", model_name="echoer")
        self.assertEqual(case["id"], "ccc-1")
        self.assertEqual(case["channel"], "chat")
        self.assertTrue(case["reference_stub"])
        self.assertFalse(case["routed_here"])
        self.assertFalse(case["orchestrated_here"])

    def test_no_conversation_content_parameter(self):
        with self.assertRaises(TypeError):
            self.ext.register_contact_case(
                "case-9", MEMBER, customer_name="someone")
        with self.assertRaises(TypeError):
            self.ext.register_contact_case(
                "case-9", MEMBER, transcript="...")
        with self.assertRaises(TypeError):
            self.ext.register_contact_case(
                "case-9", MEMBER, message_text="...")

    def test_events_and_outcome(self):
        case = self.ext.register_contact_case("case-9", MEMBER)
        ev = self.ext.record_contact_event(case["id"], "queued", MEMBER)
        self.assertFalse(ev["executed_here"])
        out = self.ext.record_contact_outcome(
            case["id"], "resolved_elsewhere", MEMBER, output_ref="sum-1")
        self.assertFalse(out["result_held_here"])
        self.assertEqual(len(self.ext.list_contact_events(case["id"])), 1)
        self.assertEqual(len(self.ext.list_contact_outcomes(case["id"])), 1)
        with self.assertRaises(ValidationError):
            self.ext.register_contact_case("case-9", MEMBER, channel="fax")


class TestVerticalApplicationsBuilt(unittest.TestCase):
    """Idx 86 — profiles over the registry; engines absent."""

    DOMAINS = (
        "compliance_erp_enclave",
        "it_asset_management",
        "electronics_data_exchange",
        "manufacturing_qc",
        "requirements_management",
        "acquisition_support",
        "cloud_infrastructure",
    )

    def setUp(self):
        self.store, self.audit, self.model, self.ext = make_ext()

    def test_every_named_domain_registers(self):
        for i, domain in enumerate(self.DOMAINS, start=1):
            app = self.ext.register_vertical_application(
                domain, "app-%s" % domain, ADMIN)
            self.assertEqual(app["id"], "vap-%d" % i)
            self.assertEqual(app["domain"], domain)
            self.assertFalse(app["operated_here"])
            self.assertEqual(app["state"], "recorded_profile")
        self.assertEqual(len(self.ext.list_vertical_applications()), 7)

    def test_unknown_domain_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_vertical_application("teleportation", "x", ADMIN)

    def test_model_binding_and_no_content_parameter(self):
        app = self.ext.register_vertical_application(
            "requirements_management", "reqs", ADMIN, model_name="echoer")
        self.assertEqual(app["model"], "echoer")
        with self.assertRaises(NotFoundError):
            self.ext.register_vertical_application(
                "requirements_management", "reqs", ADMIN, model_name="nope")
        with self.assertRaises(TypeError):
            self.ext.record_application_activity(
                app["id"], "reviewed", MEMBER, payload="...")

    def test_activity_records_and_derived_view(self):
        app = self.ext.register_vertical_application(
            "manufacturing_qc", "qc", ADMIN)
        self.ext.record_application_activity(
            app["id"], "inspection_reported", MEMBER, subject_ref="lot-1")
        self.ext.record_application_activity(
            app["id"], "inspection_reported", MEMBER, subject_ref="lot-2")
        self.ext.record_application_activity(
            app["id"], "disposition_reported", MEMBER, subject_ref="lot-1")
        view = self.ext.application_view(app["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["activity_total"], 3)
        self.assertEqual(view["activity_labels"],
                         ["disposition_reported", "inspection_reported"])
        stored = self.ext.get_vertical_application(app["id"], ADMIN)
        self.assertNotIn("activity_total", stored)


class TestSummaryAndAudit(unittest.TestCase):
    """Cross-cutting: the summary counts; mutations are audited."""

    def test_summary_and_audit_trail(self):
        store, audit, model, ext = make_ext()
        ext.register_inference_request("echoer", MEMBER)
        ext.define_agent_workflow("triage", ADMIN)
        ext.define_dashboard("ops", ADMIN, panels=["usage"])
        summary = ext.extension_summary(ADMIN)
        self.assertTrue(summary["derived"])
        self.assertEqual(summary["records_total"], 3)
        self.assertEqual(summary["by_kind"]["inference_request"], 1)
        self.assertEqual(summary["by_kind"]["agent_workflow"], 1)
        self.assertEqual(summary["by_kind"]["dashboard"], 1)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("ext_inference_request_register", actions)
        self.assertIn("ext_agent_workflow_define", actions)
        self.assertIn("ext_dashboard_define", actions)


if __name__ == "__main__":
    unittest.main()
