"""Final GAPS batch extension tests — Remainder Singleton 56
(CRM L1).

Traces to: the 8 open Extended entries of this singleton's
GAPS.md section (inventory idx 683-690) and their dispositions in
``BATCH.md``. Every test names the entry it pins. The fresh
mutation-verified negative control for the new code is
``TestNegativeControlChannelCounts`` (the drill record is in
tests/README.md); the group's founding control (breach
derivation) is untouched in test_negative_control.py.
"""

import unittest

from crm.audit import AuditLog
from crm.errors import NotFoundError, PermissionDenied, ValidationError
from crm.extensions import CrmExtensions, SCORE_KEYS
from crm_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store


def make_ext():
    store, account, contact = make_store()
    return CrmExtensions(store), store, account, contact


class TestCxmPlatformRecords(unittest.TestCase):
    """Entry: Unified customer experience management (CXM) platform
    (closed built in the records form its own text bounds)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_surface_record_is_a_definition(self):
        surface = self.ext.register_channel_surface(
            ADMIN, "Brand social presence", "social",
            surface_ref="surface/social/main")
        self.assertEqual(surface["id"], "surface-1")
        self.assertEqual(surface["channel"], "social")
        self.assertFalse(surface["operated_here"])
        self.assertFalse(surface["hosted_here"])
        stored = self.ext._records[("channel_surface", "surface-1")]
        self.assertEqual(
            set(stored),
            {"id", "name", "channel", "surface_ref", "operated_here",
             "hosted_here", "created_by", "created_utc"})

    def test_surface_channel_must_be_known(self):
        with self.assertRaises(ValidationError):
            self.ext.register_channel_surface(ADMIN, "X", "telepathy")
        # No id was consumed by the failed call.
        surface = self.ext.register_channel_surface(ADMIN, "X", "web")
        self.assertEqual(surface["id"], "surface-1")

    def test_surface_write_is_admin_only(self):
        # Channel surfaces ride config_write, as module writes do in
        # the core: the operator is denied, and the denial is audited.
        with self.assertRaises(PermissionDenied):
            self.ext.register_channel_surface(OPERATOR, "X", "web")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_channel_surface_register:denied", actions)

    def test_overview_is_derived_counts_only(self):
        self.store.record_interaction(OPERATOR, "chat", "inbound", "s1")
        self.store.record_interaction(OPERATOR, "email", "outbound", "s2",
                                       outcome="resolved")
        self.ext.register_channel_surface(ADMIN, "Web", "web")
        overview = self.ext.experience_overview(ADMIN)
        self.assertEqual(overview["method"],
                         "deterministic_counts_over_recorded_records")
        self.assertTrue(overview["derived"])
        self.assertFalse(overview["platform_operated_here"])
        self.assertEqual(overview["interactions"]["total"], 2)
        self.assertEqual(overview["interactions"]["by_channel"],
                         {"chat": 1, "email": 1})
        self.assertEqual(overview["interactions"]["by_outcome"],
                         {"none": 1, "resolved": 1})
        self.assertEqual(overview["accounts"]["total"], 1)
        self.assertEqual(overview["channel_surfaces"]["total"], 1)


class TestSocialPublishingReference(unittest.TestCase):
    """Entry: Social media management & publishing engine
    (re-judged to reference; see BATCH.md)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_content_item_holds_reference_not_content(self):
        item = self.ext.register_content_item(
            OPERATOR, "social", "asset-store/post/42", label="Launch post")
        self.assertEqual(item["id"], "post-1")
        self.assertTrue(item["reference_stub"])
        self.assertFalse(item["content_held_here"])
        self.assertFalse(item["published_here"])
        # The signature itself refuses content: there is no
        # parameter that could carry a post's text.
        with self.assertRaises(TypeError):
            self.ext.register_content_item(
                OPERATOR, "social", "asset-store/post/43",
                content="the post text")

    def test_schedule_is_a_definition_and_executes_nothing(self):
        item = self.ext.register_content_item(OPERATOR, "social", "a/1")
        before = self.store.list_interactions()
        schedule = self.ext.define_publication_schedule(
            OPERATOR, "Launch week", item_ids=[item["id"]],
            cadence_label="weekdays 09:00")
        self.assertTrue(schedule["reference_stub"])
        self.assertFalse(schedule["executed_here"])
        self.assertEqual(schedule["state"], "recorded_definition_only")
        self.assertEqual(self.store.list_interactions(), before)

    def test_schedule_requires_existing_items(self):
        with self.assertRaises(NotFoundError):
            self.ext.define_publication_schedule(
                OPERATOR, "S", item_ids=["post-99"])

    def test_publication_outcome_is_reported_data(self):
        item = self.ext.register_content_item(OPERATOR, "social", "a/1")
        outcome = self.ext.record_publication_outcome(
            OPERATOR, item["id"], "reported_published", reach_reported=120)
        self.assertTrue(outcome["reference_stub"])
        self.assertTrue(outcome["reference_transport"])
        self.assertFalse(outcome["published_here"])
        self.assertEqual(outcome["reach_reported"], 120)
        with self.assertRaises(ValidationError):
            self.ext.record_publication_outcome(
                OPERATOR, item["id"], "reported_published",
                reach_reported=-1)


class TestSocialListeningReference(unittest.TestCase):
    """Entry: Social listening & research analytics engine
    (stub-engine, as drafted)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_topic_definition_held_as_data(self):
        topic = self.ext.define_listening_topic(
            OPERATOR, "Agency mentions", topic_ref="listen/agency",
            definition_text="brand terms as configured")
        self.assertTrue(topic["reference_stub"])
        self.assertFalse(topic["listened_here"])
        self.assertEqual(topic["definition_text"],
                         "brand terms as configured")

    def test_report_creates_no_core_finding(self):
        topic = self.ext.define_listening_topic(OPERATOR, "T")
        findings_before = self.store.list_findings()
        report = self.ext.record_listening_report(
            OPERATOR, topic["id"], "Spike in mentions",
            detail="Source system reports a spike.",
            mentions_reported=340)
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["collected_here"])
        self.assertEqual(report["mentions_reported"], 340)
        # A listening report is not a finding: the core registry is
        # unchanged, exactly as in the L2 detection-report form.
        self.assertEqual(self.store.list_findings(), findings_before)

    def test_summary_sums_reported_mentions_only(self):
        topic = self.ext.define_listening_topic(OPERATOR, "T")
        self.ext.record_listening_report(
            OPERATOR, topic["id"], "R1", mentions_reported=10)
        self.ext.record_listening_report(OPERATOR, topic["id"], "R2")
        summary = self.ext.listening_summary(ADMIN)
        self.assertEqual(summary["topics"], 1)
        self.assertEqual(summary["reports"], 2)
        self.assertEqual(summary["mentions_reported_total"], 10)

    def test_reported_mentions_must_be_exact_counts(self):
        topic = self.ext.define_listening_topic(OPERATOR, "T")
        with self.assertRaises(ValidationError):
            self.ext.record_listening_report(
                OPERATOR, topic["id"], "R", mentions_reported=1.5)
        with self.assertRaises(ValidationError):
            self.ext.record_listening_report(
                OPERATOR, topic["id"], "R", mentions_reported=-3)


class TestAdvertisingReference(unittest.TestCase):
    """Entry: Advertising campaign management engine
    (re-judged to reference; see BATCH.md)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_campaign_definition_labels(self):
        campaign = self.ext.define_ad_campaign(
            OPERATOR, "Enrollment drive", channels=["social", "web"],
            budget_cents=250000)
        self.assertEqual(campaign["id"], "adcamp-1")
        self.assertTrue(campaign["reference_stub"])
        self.assertFalse(campaign["executed_here"])
        self.assertFalse(campaign["optimized_here"])
        self.assertFalse(campaign["spent_here"])
        self.assertEqual(campaign["budget_cents"], 250000)

    def test_budget_is_an_exact_recorded_figure(self):
        with self.assertRaises(ValidationError):
            self.ext.define_ad_campaign(OPERATOR, "C", budget_cents=10.5)
        with self.assertRaises(ValidationError):
            self.ext.define_ad_campaign(OPERATOR, "C", budget_cents=True)

    def test_campaign_may_bind_a_recorded_segment(self):
        segment = self.ext.create_segment(OPERATOR, "S")
        campaign = self.ext.define_ad_campaign(
            OPERATOR, "C", segment_id=segment["id"])
        self.assertEqual(campaign["segment_id"], "seg-1")
        with self.assertRaises(NotFoundError):
            self.ext.define_ad_campaign(OPERATOR, "C", segment_id="seg-9")

    def test_ad_outcome_is_reported_data(self):
        campaign = self.ext.define_ad_campaign(OPERATOR, "C")
        outcome = self.ext.record_ad_outcome(
            OPERATOR, campaign["id"], "reported_completed",
            impressions_reported=900, clicks_reported=12)
        self.assertTrue(outcome["reference_transport"])
        self.assertFalse(outcome["executed_here"])
        self.assertEqual(outcome["impressions_reported"], 900)
        self.assertEqual(outcome["clicks_reported"], 12)


class TestCareEngagementDepth(unittest.TestCase):
    """Entry: Care engagement depth (build-extension, as drafted;
    the L2 casework form)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_desktop_composition_record(self):
        guide = self.store.create_guide(
            OPERATOR, "Care tour", "walkthrough", "care/home")
        topic = self.ext.create_self_service_topic(
            OPERATOR, "Billing help", "How billing works.")
        desktop = self.ext.create_agent_desktop(
            OPERATOR, "Care desk", case_queue_ref="queue/care",
            guide_ids=[guide["id"]], topic_ids=[topic["id"]])
        self.assertEqual(desktop["id"], "desk-1")
        self.assertFalse(desktop["composed_here"])
        self.assertEqual(desktop["guide_ids"], [guide["id"]])
        self.assertEqual(desktop["topic_ids"], [topic["id"]])

    def test_desktop_references_must_exist(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_agent_desktop(
                OPERATOR, "D", guide_ids=["guide-99"])
        with self.assertRaises(NotFoundError):
            self.ext.create_agent_desktop(
                OPERATOR, "D", topic_ids=["topic-99"])

    def test_topic_enable_disable(self):
        topic = self.ext.create_self_service_topic(OPERATOR, "T", "B")
        self.assertTrue(topic["enabled"])
        self.assertFalse(topic["hosted_here"])
        updated = self.ext.set_self_service_topic_enabled(
            OPERATOR, topic["id"], False)
        self.assertFalse(updated["enabled"])
        with self.assertRaises(ValidationError):
            self.ext.set_self_service_topic_enabled(
                OPERATOR, topic["id"], "no")

    def test_chat_session_is_a_labeled_reference_record(self):
        case = self.store.create_case(OPERATOR, "problem", "Portal error")
        session = self.ext.register_chat_session(
            OPERATOR, case["id"], channel_ref="chat/widget")
        self.assertTrue(session["reference_stub"])
        self.assertFalse(session["connected_here"])
        outcome = self.ext.record_chat_outcome(
            OPERATOR, session["id"], "resolved_in_chat")
        self.assertEqual(outcome["outcome"], "resolved_in_chat")
        self.assertFalse(outcome["held_here"])

    def test_chat_session_requires_existing_case(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_chat_session(OPERATOR, "case-99")


class TestOrchestrationReference(unittest.TestCase):
    """Entry: Engagement & messaging orchestration engine
    (stub-engine, as drafted)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_flow_definition_executes_nothing(self):
        flow = self.ext.define_orchestration_flow(
            OPERATOR, "Welcome journey",
            steps=[{"step": "send_welcome", "channel": "email"},
                   {"step": "follow_up", "channel": "messaging"}])
        self.assertEqual(flow["kind"], "orchestration_flow")
        self.assertTrue(flow["reference_stub"])
        self.assertFalse(flow["executed_here"])
        before_cases = self.store.list_cases()
        self.ext.record_orchestration_outcome(
            OPERATOR, flow["id"], "reported_completed", delivered_count=7)
        self.assertEqual(self.store.list_cases(), before_cases)

    def test_flow_kinds_do_not_collide(self):
        oflow = self.ext.define_orchestration_flow(OPERATOR, "O")
        mflow = self.ext.define_marketing_flow(OPERATOR, "M")
        self.assertEqual(oflow["id"], "oflow-1")
        self.assertEqual(mflow["id"], "mflow-1")
        with self.assertRaises(NotFoundError):
            self.ext.get_orchestration_flow(mflow["id"])
        with self.assertRaises(NotFoundError):
            self.ext.get_marketing_flow(oflow["id"])

    def test_orchestration_outcome_is_reported_data(self):
        flow = self.ext.define_orchestration_flow(OPERATOR, "O")
        outcome = self.ext.record_orchestration_outcome(
            OPERATOR, flow["id"], "reported_completed", delivered_count=3)
        self.assertTrue(outcome["reference_stub"])
        self.assertFalse(outcome["sent_here"])
        self.assertEqual(outcome["delivered_count"], 3)


class TestMarketingPlatformReference(unittest.TestCase):
    """Entry: Marketing platform functions (re-judged to
    reference; see BATCH.md)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_segment_and_flow_kinds_do_not_collide(self):
        segment = self.ext.create_segment(
            OPERATOR, "Federal accounts",
            account_refs=[self.account["reference"]])
        flow = self.ext.define_marketing_flow(
            OPERATOR, "Newsletter", segment_id=segment["id"])
        self.assertEqual(segment["id"], "seg-1")
        self.assertEqual(flow["id"], "mflow-1")
        self.assertTrue(segment["reference_stub"])
        self.assertFalse(segment["targeted_here"])
        with self.assertRaises(NotFoundError):
            self.ext.get_segment(flow["id"])
        with self.assertRaises(NotFoundError):
            self.ext.get_marketing_flow(segment["id"])

    def test_flow_definition_executes_nothing(self):
        flow = self.ext.define_marketing_flow(
            OPERATOR, "F", steps=[{"step": "send", "channel": "email"}])
        self.assertEqual(flow["kind"], "marketing_flow")
        self.assertFalse(flow["executed_here"])
        self.assertEqual(flow["state"], "recorded_definition_only")
        # Defining a flow and recording its outcome creates no
        # segment and changes no core record.
        self.ext.record_flow_outcome(OPERATOR, flow["id"], "done")
        self.assertEqual(self.ext.list_segments(), [])
        self.assertEqual(self.store.list_cases(), [])

    def test_flow_outcome_is_reported_data(self):
        flow = self.ext.define_marketing_flow(OPERATOR, "F")
        outcome = self.ext.record_flow_outcome(
            OPERATOR, flow["id"], "reported_sent", delivered_count=42)
        self.assertTrue(outcome["reference_stub"])
        self.assertFalse(outcome["sent_here"])
        self.assertEqual(outcome["delivered_count"], 42)


class TestAiBackedCoreReference(unittest.TestCase):
    """Entry: AI-backed core platform (re-judged to reference;
    see BATCH.md)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_request_record_has_no_result_surface(self):
        request = self.ext.register_ai_request(
            OPERATOR, "sprinklr-ai-core", "sentiment pass")
        self.assertEqual(request["id"], "aireq-1")
        self.assertTrue(request["reference_stub"])
        self.assertFalse(request["inference_here"])
        # The signature itself refuses result content: a result
        # enters only as a reported record, never as a parameter.
        with self.assertRaises(TypeError):
            self.ext.register_ai_request(
                OPERATOR, "m", "p", result="a sentiment value")

    def test_report_holds_reference_not_result(self):
        request = self.ext.register_ai_request(OPERATOR, "m", "p")
        report = self.ext.record_ai_report(
            OPERATOR, request["id"], "reported_completed",
            result_ref="model-store/run/7")
        self.assertFalse(report["result_held_here"])
        self.assertEqual(report["result_ref"], "model-store/run/7")

    def test_score_shaped_labels_refused(self):
        request = self.ext.register_ai_request(OPERATOR, "m", "p")
        with self.assertRaises(ValidationError):
            self.ext.record_ai_report(OPERATOR, request["id"], "score")

    def test_evaluation_figures_are_reported_verbatim(self):
        evaluation = self.ext.record_ai_evaluation(
            OPERATOR, "sprinklr-ai-core", "human_agreement", 87)
        self.assertEqual(evaluation["metric_value"], 87)
        self.assertFalse(evaluation["computed_here"])
        label_eval = self.ext.record_ai_evaluation(
            OPERATOR, "sprinklr-ai-core", "review", "passed")
        self.assertEqual(label_eval["metric_value"], "passed")
        with self.assertRaises(ValidationError):
            self.ext.record_ai_evaluation(
                OPERATOR, "m", "metric", 0.87)
        with self.assertRaises(ValidationError):
            self.ext.record_ai_evaluation(
                OPERATOR, "m", "metric", True)


class TestExtensionInvariants(unittest.TestCase):
    """Cross-cutting pins: audit, rollback, privacy, no scores."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_mutations_and_denials_are_audited(self):
        self.ext.create_segment(OPERATOR, "S")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_segment_create", actions)
        with self.assertRaises(PermissionDenied):
            self.ext.create_segment(VIEWER, "S2")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_segment_create:denied", actions)

    def test_failed_audit_write_rolls_back(self):
        class FailingAudit:
            def record(self, *args, **kwargs):
                raise RuntimeError("audit unavailable")

        good_audit = self.store.audit
        self.store.audit = FailingAudit()
        try:
            with self.assertRaises(RuntimeError):
                self.ext.create_segment(OPERATOR, "S")
        finally:
            self.store.audit = good_audit
        # Nothing landed and no id was consumed.
        self.assertEqual(self.ext.list_segments(), [])
        segment = self.ext.create_segment(OPERATOR, "S")
        self.assertEqual(segment["id"], "seg-1")

    def test_no_score_shaped_key_anywhere(self):
        case = self.store.create_case(OPERATOR, "general", "C")
        self.store.record_interaction(OPERATOR, "chat", "inbound", "s")
        self.ext.register_channel_surface(ADMIN, "Web", "web")
        item = self.ext.register_content_item(OPERATOR, "social", "a/1")
        self.ext.record_publication_outcome(OPERATOR, item["id"], "ok")
        topic = self.ext.define_listening_topic(OPERATOR, "T")
        self.ext.record_listening_report(
            OPERATOR, topic["id"], "R", mentions_reported=5)
        self.ext.define_ad_campaign(OPERATOR, "C", budget_cents=100)
        self.ext.register_chat_session(OPERATOR, case["id"])
        self.ext.define_orchestration_flow(OPERATOR, "O")
        self.ext.create_segment(OPERATOR, "S")
        self.ext.register_ai_request(OPERATOR, "m", "p", case_id=case["id"])

        def scan(value):
            if isinstance(value, dict):
                for key, item_value in value.items():
                    self.assertNotIn(str(key).lower(), SCORE_KEYS)
                    scan(item_value)
            elif isinstance(value, list):
                for item_value in value:
                    scan(item_value)

        for record in self.ext._records.values():
            scan(record)
        scan(self.ext.experience_overview(ADMIN))
        scan(self.ext.listening_summary(ADMIN))
        scan(self.ext.extension_summary(ADMIN))

    def test_extension_summary_counts(self):
        self.ext.create_segment(OPERATOR, "S")
        self.ext.register_content_item(OPERATOR, "social", "a/1")
        summary = self.ext.extension_summary(ADMIN)
        self.assertEqual(summary["by_kind"]["segment"], 1)
        self.assertEqual(summary["by_kind"]["content_item"], 1)
        self.assertEqual(summary["total"], 2)


class MutantCrmExtensions(CrmExtensions):
    """The batch's fresh negative-control mutant.

    Overrides the single derivation point for the experience
    overview's by-channel distribution so it counts nothing: an
    implementation that never counts interactions by channel must
    NOT produce the canonical distribution.
    """

    def _channel_counts(self, interactions):
        return {}


class TestNegativeControlChannelCounts(unittest.TestCase):
    """Fresh negative control: experience-overview derivation.

    Traced claim: the overview's by-channel distribution is
    DERIVED at read from the recorded core interaction records,
    counted by their recorded channel.
    """

    def _fixture(self, ext_cls):
        store, account, contact = make_store()
        ext = ext_cls(store)
        store.record_interaction(OPERATOR, "chat", "inbound", "first")
        store.record_interaction(OPERATOR, "email", "outbound", "second")
        store.record_interaction(OPERATOR, "chat", "inbound", "third")
        return ext

    def test_canonical_counts_but_mutant_does_not(self):
        canonical = self._fixture(CrmExtensions).experience_overview(ADMIN)
        self.assertEqual(canonical["interactions"]["by_channel"],
                         {"chat": 2, "email": 1})
        mutant = self._fixture(MutantCrmExtensions).experience_overview(
            ADMIN)
        self.assertEqual(mutant["interactions"]["by_channel"], {})
        self.assertNotEqual(mutant["interactions"]["by_channel"],
                            canonical["interactions"]["by_channel"])
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant["interactions"]["by_channel"],
                             {"chat": 2, "email": 1})


if __name__ == "__main__":
    unittest.main()
