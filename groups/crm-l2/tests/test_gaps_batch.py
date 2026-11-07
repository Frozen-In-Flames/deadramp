"""Final GAPS batch extension tests — Group 25 (CRM L2).

Traces to: the 8 open Extended entries of this group's GAPS.md
section (inventory idx 268-275) and their dispositions in
``BATCH.md``. Every test names the entry it pins. The fresh
mutation-verified negative control for the new code is
``TestNegativeControlGuidanceOutcomeCounts`` (the drill record is
in tests/README.md); the group's founding control (breach
derivation) is untouched in test_negative_control.py.
"""

import unittest

from crm.access import User
from crm.audit import AuditLog
from crm.errors import NotFoundError, PermissionDenied, ValidationError
from crm.extensions import CrmExtensions, SCORE_KEYS
from crm_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store


def make_ext():
    store, account, contact = make_store()
    return CrmExtensions(store), store, account, contact


class TestKnowledgeBase(unittest.TestCase):
    """Entries: casework depth; knowledge base & self-service content."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_article_created_with_derived_view(self):
        view = self.ext.create_kb_article(
            OPERATOR, "Reset a password", "Use the reset link.",
            tags=["access"])
        self.assertEqual(view["id"], "kb-1")
        self.assertEqual(view["title"], "Reset a password")
        self.assertEqual(view["body"], "Use the reset link.")
        self.assertEqual(view["revision"], 1)
        self.assertEqual(view["revision_count"], 1)
        self.assertEqual(view["tags"], ["access"])

    def test_stored_article_record_holds_no_text(self):
        # The stored article record is pinned to exactly
        # {id, tags, created_by, created_utc}: text lives only in
        # revision records (the Customer Service form).
        self.ext.create_kb_article(OPERATOR, "T", "B")
        stored = self.ext._records[("kb_article", "kb-1")]
        self.assertEqual(
            set(stored), {"id", "tags", "created_by", "created_utc"})

    def test_revision_appends_and_current_text_is_derived(self):
        self.ext.create_kb_article(OPERATOR, "Old title", "Old body")
        view = self.ext.revise_kb_article(
            OPERATOR, "kb-1", body="New body")
        self.assertEqual(view["title"], "Old title")
        self.assertEqual(view["body"], "New body")
        self.assertEqual(view["revision"], 2)
        self.assertEqual(view["revision_count"], 2)
        history = self.ext.list_kb_revisions("kb-1", VIEWER)
        self.assertEqual([r["body"] for r in history],
                         ["Old body", "New body"])

    def test_revision_must_change_something(self):
        self.ext.create_kb_article(OPERATOR, "T", "B")
        with self.assertRaises(ValidationError):
            self.ext.revise_kb_article(OPERATOR, "kb-1")

    def test_search_matches_current_text_only(self):
        self.ext.create_kb_article(OPERATOR, "Alpha", "first wording")
        self.ext.revise_kb_article(OPERATOR, "kb-1", body="second wording")
        self.assertEqual(self.ext.search_kb_articles("second", OPERATOR),
                         [self.ext.get_kb_article("kb-1", VIEWER)])
        self.assertEqual(self.ext.search_kb_articles("first", OPERATOR), [])
        with self.assertRaises(ValidationError):
            self.ext.search_kb_articles("  ", OPERATOR)

    def test_viewer_cannot_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_kb_article(VIEWER, "T", "B")


class TestCaseworkDepth(unittest.TestCase):
    """Entry: customer-service casework depth."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()
        self.case = self.store.create_case(
            OPERATOR, "problem", "Portal error",
            account_id=self.account["id"], contact_id=self.contact["id"])

    def test_desktop_composition_record(self):
        self.ext.create_kb_article(OPERATOR, "Guide A", "Body A")
        self.ext.create_self_service_topic(OPERATOR, "Topic A", "Body")
        desk = self.ext.create_agent_desktop(
            OPERATOR, "Tier 1 desktop", case_queue_ref="queue/tier1",
            kb_article_ids=["kb-1"], topic_ids=["topic-1"])
        self.assertEqual(desk["id"], "desk-1")
        self.assertFalse(desk["composed_here"])

    def test_desktop_references_must_exist(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_agent_desktop(
                OPERATOR, "Bad", kb_article_ids=["kb-99"])

    def test_topic_enable_disable(self):
        self.ext.create_self_service_topic(OPERATOR, "T", "B")
        updated = self.ext.set_self_service_topic_enabled(
            OPERATOR, "topic-1", False)
        self.assertFalse(updated["enabled"])
        self.assertFalse(updated["hosted_here"])
        with self.assertRaises(ValidationError):
            self.ext.set_self_service_topic_enabled(
                OPERATOR, "topic-1", "no")

    def test_chat_session_is_a_labeled_reference_record(self):
        session = self.ext.register_chat_session(
            OPERATOR, self.case["id"], channel_ref="chat/widget",
            agent_ref="agent-7")
        self.assertEqual(session["id"], "chats-1")
        self.assertTrue(session["reference_stub"])
        self.assertFalse(session["connected_here"])
        outcome = self.ext.record_chat_outcome(
            OPERATOR, "chats-1", "reported_resolved")
        self.assertTrue(outcome["reference_stub"])
        self.assertFalse(outcome["held_here"])

    def test_chat_session_requires_existing_case(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_chat_session(OPERATOR, "case-99")


class TestGuidanceRuntime(unittest.TestCase):
    """Entry: guidance delivery runtime (stub-engine)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()
        self.guide = self.store.create_guide(
            OPERATOR, "Onboarding tour", "walkthrough", "app/home",
            steps=["Welcome"])

    def test_session_record_labels(self):
        session = self.ext.register_guidance_session(
            OPERATOR, self.guide["id"], contact_ref=self.contact["id"],
            account_id=self.account["id"])
        self.assertEqual(session["id"], "gses-1")
        self.assertTrue(session["reference_stub"])
        self.assertFalse(session["rendered_here"])
        self.assertFalse(session["delivered_here"])
        self.assertEqual(session["guide_version"], 1)

    def test_session_snapshots_guide_version(self):
        self.store.update_guide(self.guide["id"], OPERATOR,
                                steps=["Welcome", "Next"])
        session = self.ext.register_guidance_session(
            OPERATOR, self.guide["id"])
        self.assertEqual(session["guide_version"], 2)

    def test_contact_account_linkage_enforced(self):
        other = self.store.create_account(ADMIN, "ACCT-200")
        with self.assertRaises(ValidationError):
            self.ext.register_guidance_session(
                OPERATOR, self.guide["id"],
                contact_ref=self.contact["id"], account_id=other["id"])

    def test_outcome_labels_verbatim_and_scores_refused(self):
        session = self.ext.register_guidance_session(
            OPERATOR, self.guide["id"])
        outcome = self.ext.record_guidance_outcome(
            OPERATOR, session["id"], "completed")
        self.assertEqual(outcome["outcome_label"], "completed")
        self.assertTrue(outcome["reference_stub"])
        with self.assertRaises(ValidationError):
            self.ext.record_guidance_outcome(
                OPERATOR, session["id"], "score")

    def test_authoring_definition_held_as_data(self):
        definition = self.ext.register_authoring_definition(
            OPERATOR, "Tour draft", guide_id=self.guide["id"],
            definition_text='{"steps": ["a"]}')
        self.assertTrue(definition["reference_stub"])
        self.assertFalse(definition["authored_here"])
        self.assertEqual(definition["definition_text"],
                         '{"steps": ["a"]}')


class TestGapIdentificationAnalytics(unittest.TestCase):
    """Entry: gap-identification & adoption-analytics engines."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_telemetry_report_is_reported_data(self):
        report = self.ext.record_telemetry_report(
            OPERATOR, "walkme-export", "2026-W44", 1200)
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["collected_here"])
        self.assertEqual(report["events_reported"], 1200)
        with self.assertRaises(ValidationError):
            self.ext.record_telemetry_report(
                OPERATOR, "walkme-export", "2026-W44", -1)
        with self.assertRaises(ValidationError):
            self.ext.record_telemetry_report(
                OPERATOR, "walkme-export", "2026-W44", 1.5)

    def test_detection_report_creates_no_core_finding(self):
        before = self.store.list_findings()
        report = self.ext.record_detection_report(
            OPERATOR, "detector-x", "Users abandon step 3",
            detail="Source system states 40% abandonment",
            severity="warning", account_id=self.account["id"])
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["detected_here"])
        self.assertEqual(self.store.list_findings(), before)
        self.assertEqual(self.store.report()["findings"]["total"],
                         len(before))

    def test_engagement_metrics_are_derived_counts(self):
        self.store.record_interaction(
            OPERATOR, "chat", "inbound", "Question", outcome="resolved")
        self.store.record_interaction(
            OPERATOR, "email", "outbound", "Follow-up")
        guide = self.store.create_guide(
            OPERATOR, "Tour", "walkthrough", "app/home")
        s1 = self.ext.register_guidance_session(OPERATOR, guide["id"])
        s2 = self.ext.register_guidance_session(OPERATOR, guide["id"])
        self.ext.record_guidance_outcome(OPERATOR, s1["id"], "completed")
        self.ext.record_guidance_outcome(OPERATOR, s2["id"], "completed")
        self.ext.record_guidance_outcome(OPERATOR, s2["id"], "abandoned")
        metrics = self.ext.engagement_metrics(ADMIN)
        self.assertTrue(metrics["derived"])
        self.assertEqual(metrics["interactions"]["total"], 2)
        self.assertEqual(metrics["interactions"]["by_outcome"],
                         {"resolved": 1, "none": 1})
        self.assertEqual(metrics["guidance"]["sessions_recorded"], 2)
        self.assertEqual(metrics["guidance"]["by_outcome"],
                         {"completed": 2, "abandoned": 1})


class TestModuleEnginesRejudged(unittest.TestCase):
    """Entry: customization & module engines (re-judged reference)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()
        self.module = self.store.create_module(
            ADMIN, "Routing", "cases", "route=priority")

    def test_execution_request_is_a_labeled_record(self):
        request = self.ext.request_module_execution(
            ADMIN, self.module["id"], parameters={"mode": "dry"})
        self.assertEqual(request["id"], "mexec-1")
        self.assertTrue(request["reference_stub"])
        self.assertFalse(request["executed_here"])
        self.assertEqual(request["module_version"], 1)

    def test_request_and_report_leave_core_module_untouched(self):
        before = self.store.get_module(self.module["id"])
        request = self.ext.request_module_execution(
            ADMIN, self.module["id"])
        self.ext.record_module_execution_report(
            ADMIN, request["id"], "reported_completed")
        after = self.store.get_module(self.module["id"])
        self.assertEqual(before, after)

    def test_execution_surface_is_admin_only(self):
        # config_write is admin-only in the core matrix; the
        # extension mapping inherits that, it does not widen it.
        with self.assertRaises(PermissionDenied):
            self.ext.request_module_execution(OPERATOR, self.module["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.register_runtime_parameter_set(
                OPERATOR, self.module["id"], {"a": "b"})

    def test_runtime_parameter_set_held_as_data(self):
        record = self.ext.register_runtime_parameter_set(
            ADMIN, self.module["id"], {"threshold": 3, "label": "x"})
        self.assertTrue(record["reference_stub"])
        self.assertFalse(record["applied_here"])
        self.assertEqual(record["parameters"],
                         {"threshold": 3, "label": "x"})

    def test_parameters_reject_floats_scores_and_nesting(self):
        with self.assertRaises(ValidationError):
            self.ext.request_module_execution(
                ADMIN, self.module["id"], parameters={"x": 1.5})
        with self.assertRaises(ValidationError):
            self.ext.request_module_execution(
                ADMIN, self.module["id"], parameters={"score": 3})
        with self.assertRaises(ValidationError):
            self.ext.request_module_execution(
                ADMIN, self.module["id"], parameters={"x": {"y": 1}})


class TestMarketingAutomation(unittest.TestCase):
    """Entry: marketing-automation engines & email delivery."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_segment_and_flow_kinds_do_not_collide(self):
        # Segments and flows are separate record kinds with
        # separate id namespaces (the standing segments/flows
        # lesson): creating both never cross-resolves.
        segment = self.ext.create_segment(
            OPERATOR, "Liaisons", account_refs=["ACCT-100"])
        flow = self.ext.define_marketing_flow(
            OPERATOR, "Welcome flow", segment_id=segment["id"],
            steps=[{"step": "send_welcome", "channel": "email"}])
        self.assertEqual(segment["id"], "seg-1")
        self.assertEqual(flow["id"], "mflow-1")
        self.assertEqual(flow["kind"], "marketing_flow")
        self.assertTrue(flow["reference_stub"])
        self.assertFalse(flow["executed_here"])
        self.assertEqual(self.ext.get_segment("seg-1")["name"], "Liaisons")
        with self.assertRaises(NotFoundError):
            self.ext.get_segment("mflow-1")
        with self.assertRaises(NotFoundError):
            self.ext.get_marketing_flow("seg-1")

    def test_flow_definition_executes_nothing(self):
        cases_before = self.store.list_cases()
        flow = self.ext.define_marketing_flow(OPERATOR, "F")
        self.ext.record_flow_outcome(
            OPERATOR, flow["id"], "reported_completed", delivered_count=10)
        self.assertEqual(self.store.list_cases(), cases_before)
        self.assertEqual(self.ext.list_segments(), [])

    def test_flow_outcome_is_reported_data(self):
        flow = self.ext.define_marketing_flow(OPERATOR, "F")
        outcome = self.ext.record_flow_outcome(
            OPERATOR, flow["id"], "reported_completed", delivered_count=7)
        self.assertTrue(outcome["reference_stub"])
        self.assertFalse(outcome["sent_here"])
        self.assertEqual(outcome["delivered_count"], 7)
        with self.assertRaises(ValidationError):
            self.ext.record_flow_outcome(
                OPERATOR, flow["id"], "reported_completed",
                delivered_count=-1)


class TestAiMlScoring(unittest.TestCase):
    """Entry: AI/ML models & scoring (stub-engine)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()
        self.case = self.store.create_case(OPERATOR, "inquiry", "Help")

    def test_request_record_has_no_result_surface(self):
        request = self.ext.register_ai_request(
            OPERATOR, "model-x", "summarize the case",
            case_id=self.case["id"])
        self.assertTrue(request["reference_stub"])
        self.assertFalse(request["inference_here"])
        # The signature itself refuses result content: there is no
        # parameter that could carry it.
        with self.assertRaises(TypeError):
            self.ext.register_ai_request(
                OPERATOR, "model-x", "p", result="a summary")

    def test_report_holds_reference_not_result(self):
        request = self.ext.register_ai_request(OPERATOR, "model-x", "p")
        report = self.ext.record_ai_report(
            OPERATOR, request["id"], "reported_answered",
            result_ref="ext-result-1")
        self.assertFalse(report["result_held_here"])
        self.assertEqual(report["result_ref"], "ext-result-1")
        with self.assertRaises(ValidationError):
            self.ext.record_ai_report(
                OPERATOR, request["id"], "score")

    def test_evaluation_figures_are_reported_verbatim(self):
        record = self.ext.record_ai_evaluation(
            OPERATOR, "model-x", "exact_match_percent", 87)
        self.assertEqual(record["metric_value"], 87)
        self.assertTrue(record["reference_stub"])
        self.assertFalse(record["computed_here"])
        label = self.ext.record_ai_evaluation(
            OPERATOR, "model-x", "review_outcome", "reported_pass")
        self.assertEqual(label["metric_value"], "reported_pass")
        with self.assertRaises(ValidationError):
            self.ext.record_ai_evaluation(
                OPERATOR, "model-x", "accuracy", 0.87)


class TestConnectorEngines(unittest.TestCase):
    """Entry: integration connector engines (stub-engine)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()
        self.case = self.store.create_case(OPERATOR, "request", "Sync me")

    def test_sync_receipt_labels_and_binding(self):
        sync = self.ext.record_connector_sync(
            ADMIN, "crm-bridge", "inbound", 12,
            target_kind="case", target_id=self.case["id"])
        self.assertEqual(sync["id"], "csync-1")
        self.assertTrue(sync["reference_stub"])
        self.assertTrue(sync["reference_transport"])
        self.assertFalse(sync["transmitted_here"])
        self.assertFalse(sync["synced_here"])

    def test_sync_target_must_exist_and_stays_untouched(self):
        before = self.store.get_case(self.case["id"])
        self.ext.record_connector_sync(
            ADMIN, "crm-bridge", "outbound", 3,
            target_kind="case", target_id=self.case["id"])
        self.assertEqual(self.store.get_case(self.case["id"]), before)
        with self.assertRaises(NotFoundError):
            self.ext.record_connector_sync(
                ADMIN, "crm-bridge", "inbound", 1,
                target_kind="case", target_id="case-99")

    def test_catalog_rollup_is_derived(self):
        self.ext.record_connector_sync(ADMIN, "bridge", "inbound", 5)
        self.ext.record_connector_sync(ADMIN, "bridge", "outbound", 7)
        self.ext.record_connector_sync(ADMIN, "other", "inbound", 2)
        catalog = self.ext.connector_catalog(ADMIN)
        self.assertTrue(catalog["derived"])
        self.assertEqual(catalog["total_syncs"], 3)
        self.assertEqual(catalog["total_records_reported"], 14)
        bridge = [c for c in catalog["connectors"]
                  if c["connector_ref"] == "bridge"][0]
        self.assertEqual(bridge["records_reported_total"], 12)
        self.assertEqual(bridge["by_direction"],
                         {"inbound": 1, "outbound": 1})


class TestExtensionInvariants(unittest.TestCase):
    """Cross-cutting pins: audit, rollback, privacy, no scores."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_mutations_and_denials_are_audited(self):
        self.ext.create_kb_article(OPERATOR, "T", "B")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_kb_article_create", actions)
        with self.assertRaises(PermissionDenied):
            self.ext.create_kb_article(VIEWER, "T2", "B2")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_kb_article_create:denied", actions)

    def test_failed_audit_write_rolls_back(self):
        class FailingAudit:
            def record(self, *args, **kwargs):
                raise RuntimeError("audit unavailable")

        good_audit = self.store.audit
        self.store.audit = FailingAudit()
        try:
            with self.assertRaises(RuntimeError):
                self.ext.create_kb_article(OPERATOR, "T", "B")
        finally:
            self.store.audit = good_audit
        # Nothing landed and no id was consumed.
        self.assertEqual(self.ext.list_kb_articles(), [])
        view = self.ext.create_kb_article(OPERATOR, "T", "B")
        self.assertEqual(view["id"], "kb-1")

    def test_no_score_shaped_key_anywhere(self):
        guide = self.store.create_guide(
            OPERATOR, "Tour", "walkthrough", "app/home")
        module = self.store.create_module(ADMIN, "M", "cases", "a=b")
        case = self.store.create_case(OPERATOR, "general", "C")
        self.ext.create_kb_article(OPERATOR, "T", "B")
        session = self.ext.register_guidance_session(OPERATOR, guide["id"])
        self.ext.record_guidance_outcome(OPERATOR, session["id"], "done")
        self.ext.request_module_execution(ADMIN, module["id"])
        self.ext.register_ai_request(OPERATOR, "m", "p", case_id=case["id"])
        self.ext.record_connector_sync(ADMIN, "c", "inbound", 1)

        def scan(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(str(key).lower(), SCORE_KEYS)
                    scan(item)
            elif isinstance(value, list):
                for item in value:
                    scan(item)

        for record in self.ext._records.values():
            scan(record)
        scan(self.ext.engagement_metrics(ADMIN))
        scan(self.ext.connector_catalog(ADMIN))
        scan(self.ext.extension_summary(ADMIN))

    def test_extension_summary_counts(self):
        self.ext.create_kb_article(OPERATOR, "T", "B")
        self.ext.create_segment(OPERATOR, "S")
        summary = self.ext.extension_summary(ADMIN)
        self.assertEqual(summary["by_kind"]["kb_article"], 1)
        self.assertEqual(summary["by_kind"]["kb_revision"], 1)
        self.assertEqual(summary["by_kind"]["segment"], 1)
        self.assertEqual(summary["total"], 3)


class MutantCrmExtensions(CrmExtensions):
    """The batch's fresh negative-control mutant.

    Overrides the single derivation point for the engagement
    report's guidance outcome distribution so it counts nothing:
    an implementation that never counts guidance outcomes must NOT
    produce the canonical distribution.
    """

    def _guidance_outcome_counts(self, outcome_records):
        return {}


class TestNegativeControlGuidanceOutcomeCounts(unittest.TestCase):
    """Fresh negative control: guidance outcome derivation.

    Traced claim: the engagement report's guidance outcome
    distribution is DERIVED at read from the recorded outcome
    records, counted by their verbatim reported labels.
    """

    def _fixture(self, ext_cls):
        store, account, contact = make_store()
        ext = ext_cls(store)
        guide = store.create_guide(
            OPERATOR, "Onboarding tour", "walkthrough", "app/home")
        s1 = ext.register_guidance_session(OPERATOR, guide["id"])
        s2 = ext.register_guidance_session(OPERATOR, guide["id"])
        ext.record_guidance_outcome(OPERATOR, s1["id"], "completed")
        ext.record_guidance_outcome(OPERATOR, s2["id"], "completed")
        ext.record_guidance_outcome(OPERATOR, s2["id"], "abandoned")
        return ext

    def test_canonical_counts_but_mutant_does_not(self):
        canonical = self._fixture(CrmExtensions).engagement_metrics(ADMIN)
        self.assertEqual(canonical["guidance"]["by_outcome"],
                         {"completed": 2, "abandoned": 1})
        mutant = self._fixture(MutantCrmExtensions).engagement_metrics(ADMIN)
        self.assertEqual(mutant["guidance"]["by_outcome"], {})
        self.assertNotEqual(mutant["guidance"]["by_outcome"],
                            canonical["guidance"]["by_outcome"])
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant["guidance"]["by_outcome"],
                             {"completed": 2, "abandoned": 1})


if __name__ == "__main__":
    unittest.main()
