"""Final GAPS batch tests — Group 15, Contact Center L2.

Traces to: the eleven entries of this group's GAPS.md section
(idx 152–162 in gaps-batch/inventory.json) and the dispositions in
../BATCH.md. Pins the extension surface in
``contact.extensions.ContactExtensions``: per-entry record shapes
(exact key sets), honesty labels (``reference_stub`` /
``reference_transport`` and the ``*_here: False`` family),
derived-at-read values (PAM and clearance current state, survey
tallies, risk counts, SLA breach under a policy), the privacy
discipline (recursive forbidden-key scan; person-shaped references
are core directory ids only), RBAC mapping and denied-attempt
auditing, no-id-on-failure, audit-failure rollback, and the fresh
mutation-verified negative control for the SLA derivation seam
(:class:`TestSlaPolicyNegativeControl`).
"""

import copy
import unittest
from datetime import datetime, timedelta

from contact.audit import AuditLog
from contact.errors import NotFoundError, PermissionDenied, ValidationError
from contact.extensions import ContactExtensions
from contact_helpers import ADMIN, OPERATOR, VIEWER, make_store


def _scan_keys(value, path="root"):
    """Yield (path, key) for every dict key in a nested structure."""
    if isinstance(value, dict):
        for key, sub in value.items():
            yield (path, key)
            yield from _scan_keys(sub, "%s.%s" % (path, key))
    elif isinstance(value, (list, tuple)):
        for index, sub in enumerate(value):
            yield from _scan_keys(sub, "%s[%d]" % (path, index))


FORBIDDEN_FRAGMENTS = ("phone", "email", "ssn")


class ExtFixture(unittest.TestCase):
    """Store (agent + contact + queue) plus the extension surface."""

    def setUp(self):
        self.audit = AuditLog()
        self.store, self.agent, self.contact, self.queue = make_store(
            audit=self.audit)
        self.ext = ContactExtensions(self.store)

    def audit_actions(self):
        return [entry["action"] for entry in self.audit.entries()]


class TestPam(ExtFixture):
    """Idx 152 — PAM & Zero Trust (built, records form)."""

    def test_request_shape_and_labels(self):
        req = self.ext.create_access_request(
            OPERATOR, self.agent["id"], "target/db-prod",
            justification_ref="ticket-441",
            window_start="2026-03-01T09:00:00Z",
            window_end="2026-03-01T17:00:00Z")
        self.assertEqual(req["id"], "pam-1")
        self.assertIs(req["granted_here"], False)
        self.assertIs(req["enforced_here"], False)
        stored = self.ext._pam_requests["pam-1"]
        self.assertEqual(
            set(stored.keys()),
            {"id", "agent_id", "target_ref", "justification_ref",
             "window_start", "window_end", "granted_here",
             "enforced_here", "created_by", "created_utc",
             "updated_utc"})
        self.assertNotIn("current_state", stored)

    def test_initial_state_is_requested(self):
        req = self.ext.create_access_request(
            OPERATOR, self.agent["id"], "target/db-prod")
        view = self.ext.get_access_request(OPERATOR, req["id"])
        self.assertEqual(view["current_state"], "requested")
        self.assertEqual(view["outcome_count"], 0)
        self.assertIs(view["derived"], True)

    def test_request_requires_existing_agent(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_access_request(OPERATOR, "agt-999", "t/x")
        req = self.ext.create_access_request(
            OPERATOR, self.agent["id"], "t/x")
        self.assertEqual(req["id"], "pam-1")  # failure consumed no id

    def test_window_must_be_forward(self):
        with self.assertRaises(ValidationError):
            self.ext.create_access_request(
                OPERATOR, self.agent["id"], "t/x",
                window_start="2026-03-01T17:00:00Z",
                window_end="2026-03-01T09:00:00Z")

    def test_outcomes_derive_current_state(self):
        req = self.ext.create_access_request(
            OPERATOR, self.agent["id"], "target/db-prod")
        self.ext.record_access_outcome(ADMIN, req["id"], "reported_granted")
        view = self.ext.get_access_request(OPERATOR, req["id"])
        self.assertEqual(view["current_state"], "reported_granted")
        self.ext.record_access_outcome(ADMIN, req["id"], "reported_revoked")
        view = self.ext.get_access_request(OPERATOR, req["id"])
        self.assertEqual(view["current_state"], "reported_revoked")
        self.assertEqual(view["outcome_count"], 2)
        stored = self.ext._pam_requests[req["id"]]
        self.assertNotIn("current_state", stored)

    def test_outcome_unknown_request(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_access_outcome(ADMIN, "pam-999", "reported_x")

    def test_session_record_labels(self):
        req = self.ext.create_access_request(
            OPERATOR, self.agent["id"], "target/db-prod")
        session = self.ext.record_access_session(
            OPERATOR, req["id"], "sess-ref-9", "reported_active")
        self.assertIs(session["content_held_here"], False)
        self.assertIs(session["monitored_here"], False)
        sessions = self.ext.list_access_sessions(OPERATOR, req["id"])
        self.assertEqual([s["id"] for s in sessions], ["pams-1"])
        self.assertEqual(self.ext.list_access_sessions(OPERATOR, "pam-x"),
                         [])

    def test_viewer_write_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_access_request(
                VIEWER, self.agent["id"], "target/db-prod")


class TestIdentityRisk(ExtFixture):
    """Idx 153 — identity risk analytics (built, records form)."""

    def test_signal_shape_no_score(self):
        signal = self.ext.record_risk_signal(
            OPERATOR, self.agent["id"], "impossible_travel_reported",
            source_ref="idp-feed")
        self.assertEqual(
            set(signal.keys()),
            {"id", "agent_id", "signal_label", "source_ref",
             "computed_here", "created_by", "created_utc"})
        self.assertIs(signal["computed_here"], False)
        for _path, key in _scan_keys(signal):
            self.assertNotIn("score", key.lower())
            self.assertNotIn("risk_value", key.lower())

    def test_signal_requires_existing_agent(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_risk_signal(OPERATOR, "agt-999", "label")

    def test_recommendation_links_matching_signal(self):
        signal = self.ext.record_risk_signal(
            OPERATOR, self.agent["id"], "dormant_account_reported")
        rec = self.ext.record_recommendation(
            OPERATOR, self.agent["id"], "require_step_up_auth",
            signal_id=signal["id"])
        self.assertIs(rec["computed_here"], False)
        self.assertIs(rec["applied_here"], False)
        other = self.store.create_agent("Second Agent", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_recommendation(
                OPERATOR, other["id"], "require_step_up_auth",
                signal_id=signal["id"])

    def test_summary_is_counts_only(self):
        self.ext.record_risk_signal(OPERATOR, self.agent["id"], "label_a")
        self.ext.record_risk_signal(OPERATOR, self.agent["id"], "label_a")
        self.ext.record_risk_signal(OPERATOR, self.agent["id"], "label_b")
        self.ext.record_recommendation(
            OPERATOR, self.agent["id"], "require_step_up_auth")
        summary = self.ext.risk_summary(OPERATOR)
        self.assertEqual(summary["signals"], 3)
        self.assertEqual(summary["signals_by_label"],
                         {"label_a": 2, "label_b": 1})
        self.assertEqual(summary["recommendations"], 1)
        self.assertEqual(summary["method"],
                         "deterministic_counts_over_recorded_signals")
        for _path, key in _scan_keys(summary):
            self.assertNotIn("score", key.lower())


class TestClearance(ExtFixture):
    """Idx 157 — personnel-security / clearance depth (built)."""

    def test_case_shape_and_open_state(self):
        case = self.ext.open_clearance_case(
            OPERATOR, self.agent["id"], "secret")
        self.assertIs(case["adjudicated_here"], False)
        stored = self.ext._clearance_cases[case["id"]]
        self.assertEqual(
            set(stored.keys()),
            {"id", "subject_id", "clearance_label", "adjudicated_here",
             "created_by", "created_utc", "updated_utc"})
        view = self.ext.get_clearance_case(OPERATOR, case["id"])
        self.assertEqual(view["current_state"], "open")
        self.assertEqual(view["outcome_count"], 0)

    def test_subject_must_be_in_directory(self):
        with self.assertRaises(NotFoundError):
            self.ext.open_clearance_case(OPERATOR, "agt-999", "secret")
        case = self.ext.open_clearance_case(
            OPERATOR, self.contact["id"], "public_trust")
        self.assertEqual(case["subject_id"], self.contact["id"])

    def test_outcomes_derive_latest_state(self):
        case = self.ext.open_clearance_case(
            OPERATOR, self.agent["id"], "secret")
        self.ext.record_clearance_outcome(
            OPERATOR, case["id"], "reported_interim")
        self.ext.record_clearance_outcome(
            OPERATOR, case["id"], "reported_favorable")
        view = self.ext.get_clearance_case(OPERATOR, case["id"])
        self.assertEqual(view["current_state"], "reported_favorable")
        self.assertEqual(view["outcome_count"], 2)
        stored = self.ext._clearance_cases[case["id"]]
        self.assertNotIn("current_state", stored)


class TestKnowledgeBase(ExtFixture):
    """Idx 160 — knowledge-base articles (built)."""

    def test_article_stored_record_holds_no_text(self):
        article = self.ext.create_article(
            OPERATOR, "Reset a password", "Use the portal.",
            tags=["access"])
        stored = self.ext._articles[article["id"]]
        self.assertEqual(
            set(stored.keys()),
            {"id", "tags", "created_by", "created_utc", "updated_utc"})
        self.assertEqual(article["title"], "Reset a password")
        self.assertEqual(article["body"], "Use the portal.")
        self.assertEqual(article["revision_count"], 1)

    def test_revise_appends_and_carries_forward(self):
        article = self.ext.create_article(
            OPERATOR, "Reset a password", "Use the portal.")
        revised = self.ext.revise_article(
            OPERATOR, article["id"], body="Use the portal, then MFA.")
        self.assertEqual(revised["title"], "Reset a password")
        self.assertEqual(revised["body"], "Use the portal, then MFA.")
        self.assertEqual(revised["revision_count"], 2)
        revisions = self.ext.list_article_revisions(
            OPERATOR, article["id"])
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0]["body"], "Use the portal.")
        self.assertEqual(revisions[1]["revision"], 2)

    def test_revise_requires_a_change(self):
        article = self.ext.create_article(OPERATOR, "T", "B")
        with self.assertRaises(ValidationError):
            self.ext.revise_article(OPERATOR, article["id"])

    def test_search_articles(self):
        self.ext.create_article(OPERATOR, "Reset a password", "Portal.")
        self.ext.create_article(OPERATOR, "VPN setup", "Client install.")
        hits = self.ext.search_articles(OPERATOR, "password")
        self.assertEqual([a["title"] for a in hits], ["Reset a password"])
        self.assertEqual(self.ext.search_articles(OPERATOR, "zzz"), [])

    def test_failed_create_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.create_article(OPERATOR, "", "body")
        article = self.ext.create_article(OPERATOR, "T", "B")
        self.assertEqual(article["id"], "kb-1")


class TestCsat(ExtFixture):
    """Idx 161 — satisfaction / CSAT surveys (built)."""

    def test_survey_stored_shape_no_score(self):
        survey = self.ext.create_survey(OPERATOR, "Post-contact CSAT")
        stored = self.ext._surveys[survey["id"]]
        self.assertEqual(
            set(stored.keys()),
            {"id", "name", "scale_min", "scale_max", "case_id",
             "created_by", "created_utc"})
        for _path, key in _scan_keys(stored):
            self.assertNotIn("score", key.lower())
            self.assertNotIn("tally", key.lower())

    def test_scale_and_rating_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_survey(OPERATOR, "bad", scale_min=5,
                                   scale_max=5)
        with self.assertRaises(ValidationError):
            self.ext.create_survey(OPERATOR, "bad", scale_min=True)
        survey = self.ext.create_survey(OPERATOR, "CSAT")
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                OPERATOR, survey["id"], self.contact["id"], 4.5)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                OPERATOR, survey["id"], self.contact["id"], True)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                OPERATOR, survey["id"], self.contact["id"], 9)
        with self.assertRaises(NotFoundError):
            self.ext.record_survey_response(
                OPERATOR, survey["id"], "ct-999", 4)

    def test_tally_exact_rational_mean(self):
        survey = self.ext.create_survey(OPERATOR, "CSAT")
        for rating in (5, 4, 4):
            self.ext.record_survey_response(
                OPERATOR, survey["id"], self.contact["id"], rating)
        tally = self.ext.survey_tally(OPERATOR, survey["id"])
        self.assertEqual(tally["response_count"], 3)
        self.assertEqual(tally["distribution"],
                         {"1": 0, "2": 0, "3": 0, "4": 2, "5": 1})
        self.assertEqual(tally["mean"],
                         {"numerator": 13, "denominator": 3})
        self.assertEqual(tally["method"],
                         "exact_rational_mean_of_recorded_ratings")
        self.assertIs(tally["derived"], True)

    def test_tally_empty_survey(self):
        survey = self.ext.create_survey(OPERATOR, "CSAT")
        tally = self.ext.survey_tally(OPERATOR, survey["id"])
        self.assertEqual(tally["response_count"], 0)
        self.assertIsNone(tally["mean"])


def _plus(iso_text, **kwargs):
    return (datetime.fromisoformat(iso_text)
            + timedelta(**kwargs)).isoformat()


class TestSlaPolicy(ExtFixture):
    """Idx 162 — SLA policy engine (built, adjudicated form)."""

    def _policy(self, targets=None):
        return self.ext.create_sla_policy(
            ADMIN, "Standard tiers", targets or {"normal": 60},
            calendar_ref="cal/business-hours", escalation_ref="esc/l1")

    def _case(self, priority="normal"):
        return self.store.create_case(
            OPERATOR, "inquiry", "SLA case", priority=priority)

    def test_policy_shape_and_labels(self):
        policy = self._policy({"high": 30, "normal": 60})
        stored = self.ext._sla_policies[policy["id"]]
        self.assertEqual(
            set(stored.keys()),
            {"id", "name", "targets_minutes", "calendar_ref",
             "escalation_ref", "created_by", "created_utc"})
        self.assertEqual(stored["targets_minutes"],
                         {"high": 30, "normal": 60})
        self.assertEqual(stored["calendar_ref"], "cal/business-hours")

    def test_policy_validation(self):
        for bad in ({"urgent": 30}, {"high": 0}, {"high": -5},
                    {"high": 30.5}, {"high": True}, {}, "not-a-dict"):
            with self.assertRaises(ValidationError):
                self.ext.create_sla_policy(ADMIN, "bad", bad)
        policy = self._policy()
        self.assertEqual(policy["id"], "sla-1")  # no id consumed

    def test_policy_write_is_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_sla_policy(OPERATOR, "nope", {"normal": 60})

    def test_breach_derivation(self):
        policy = self._policy()
        case = self._case()
        created = case["created_utc"]
        early = self.ext.sla_case_view(
            ADMIN, policy["id"], case["id"], now=_plus(created, minutes=59))
        self.assertIs(early["sla"]["covered"], True)
        self.assertEqual(early["sla"]["target_minutes"], 60)
        self.assertIs(early["sla"]["breached_under_policy"], False)
        self.assertEqual(early["sla"]["effective_due_at"],
                         _plus(created, minutes=60))
        late = self.ext.sla_case_view(
            ADMIN, policy["id"], case["id"], now=_plus(created, minutes=61))
        self.assertIs(late["sla"]["breached_under_policy"], True)
        self.assertIs(late["sla"]["stored"], False)

    def test_uncovered_priority_never_breached(self):
        policy = self._policy({"high": 30})
        case = self._case(priority="low")
        view = self.ext.sla_case_view(
            ADMIN, policy["id"], case["id"],
            now=_plus(case["created_utc"], days=365))
        self.assertIs(view["sla"]["covered"], False)
        self.assertIsNone(view["sla"]["target_minutes"])
        self.assertIsNone(view["sla"]["effective_due_at"])
        self.assertIs(view["sla"]["breached_under_policy"], False)

    def test_terminal_case_never_breached(self):
        policy = self._policy()
        case = self._case()
        self.store.transition_case(case["id"], OPERATOR, "in_progress")
        self.store.transition_case(case["id"], OPERATOR, "resolved")
        view = self.ext.sla_case_view(
            ADMIN, policy["id"], case["id"],
            now=_plus(case["created_utc"], days=365))
        self.assertIs(view["sla"]["breached_under_policy"], False)

    def test_breach_report_counts(self):
        policy = self._policy()
        old = self._case()
        fresh = self._case()
        now = _plus(old["created_utc"], minutes=61)
        report = self.ext.sla_breach_report(ADMIN, policy["id"], now=now)
        self.assertEqual(report["cases_total"], 2)
        self.assertEqual(report["covered"], 2)
        self.assertEqual(report["breached"], 2)
        self.assertEqual(report["breached_by_priority"], {"normal": 2})
        self.assertIs(report["derived"], True)
        self.assertEqual(fresh["priority"], "normal")

    def test_policy_views_leave_core_case_untouched(self):
        policy = self._policy()
        case = self._case()
        before = copy.deepcopy(self.store._cases[case["id"]])
        self.ext.sla_case_view(
            ADMIN, policy["id"], case["id"],
            now=_plus(case["created_utc"], minutes=61))
        self.ext.sla_breach_report(
            ADMIN, policy["id"], now=_plus(case["created_utc"], minutes=61))
        self.assertEqual(self.store._cases[case["id"]], before)


class MutantSlaExtensions(ContactExtensions):
    """Negative-control mutant: breach under a policy never fires."""

    def _is_breached_under_policy(self, case, policy, now_dt):
        return False


class TestSlaPolicyNegativeControl(ExtFixture):
    """Fresh mutation-verified negative control for the batch.

    Traced claim: SLA breach under a recorded policy is DERIVED at
    read at the single seam ``_is_breached_under_policy`` -- a
    covered, open case past its recorded target must read
    ``breached_under_policy=True`` in the case view and count as
    breached in the report.
    """

    def _scenario(self, ext):
        policy = ext.create_sla_policy(ADMIN, "Standard", {"normal": 60})
        case = self.store.create_case(OPERATOR, "inquiry", "SLA case")
        now = _plus(case["created_utc"], minutes=61)
        view = ext.sla_case_view(ADMIN, policy["id"], case["id"], now=now)
        report = ext.sla_breach_report(ADMIN, policy["id"], now=now)
        return view["sla"]["breached_under_policy"], report["breached"]

    def test_canonical_breaches_and_mutant_does_not(self):
        canonical = self._scenario(self.ext)
        self.assertEqual(canonical, (True, 1))
        mutant = MutantSlaExtensions(self.store)
        mutant_result = self._scenario(mutant)
        self.assertEqual(mutant_result, (False, 0))
        self.assertNotEqual(mutant_result, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_result, canonical)


class TestObservabilityStub(ExtFixture):
    """Idx 154 — observability collection (reference)."""

    def test_source_and_report_labels(self):
        source = self.ext.register_collection_source(
            OPERATOR, "lm/collector-7", "collector")
        self.assertIs(source["reference_stub"], True)
        self.assertIs(source["collected_here"], False)
        report = self.ext.record_collection_report(
            OPERATOR, source["id"], "metrics_window_reported",
            reported_count=1200, window_label="2026-03-01/2026-03-02")
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["collected_here"], False)
        self.assertIs(report["forecast_computed_here"], False)
        self.assertEqual(report["reported_count"], 1200)

    def test_report_validation(self):
        source = self.ext.register_collection_source(
            OPERATOR, "lm/collector-7", "collector")
        with self.assertRaises(ValidationError):
            self.ext.record_collection_report(
                OPERATOR, source["id"], "x", reported_count=1.5)
        with self.assertRaises(NotFoundError):
            self.ext.record_collection_report(OPERATOR, "obs-999", "x")


class TestTelephonyStub(ExtFixture):
    """Idx 155 — voice/telephony & callback connection (reference)."""

    def test_session_labels(self):
        case = self.store.create_case(OPERATOR, "callback", "Callback")
        session = self.ext.record_telephony_session(
            OPERATOR, "cc-session-55", "reported_connected",
            case_id=case["id"])
        self.assertIs(session["reference_stub"], True)
        self.assertIs(session["connected_here"], False)
        self.assertIs(session["media_here"], False)
        for _path, key in _scan_keys(session):
            self.assertNotIn("phone", key.lower())

    def test_session_links_must_exist(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_telephony_session(
                OPERATOR, "cc-1", "reported_connected", case_id="case-999")

    def test_routing_changes_no_core_record(self):
        session = self.ext.record_telephony_session(
            OPERATOR, "cc-session-55", "reported_connected")
        members_before = list(self.store._queues[self.queue["id"]]["members"])
        routing = self.ext.record_routing_decision(
            OPERATOR, session["id"], self.queue["id"], "reported_routed")
        self.assertIs(routing["reference_stub"], True)
        self.assertIs(routing["routed_here"], False)
        self.assertEqual(
            self.store._queues[self.queue["id"]]["members"], members_before)


class TestFraudStub(ExtFixture):
    """Idx 156 — claims adjudication & fraud detection (reference)."""

    def test_rule_definition_labels(self):
        rule = self.ext.register_fraud_rule(
            ADMIN, "Duplicate claim", "claim",
            "same contact, two claims, 7 days", "flag for review")
        self.assertIs(rule["reference_stub"], True)
        self.assertIs(rule["executed_here"], False)
        with self.assertRaises(PermissionDenied):
            self.ext.register_fraud_rule(
                OPERATOR, "x", "claim", "c", "a")
        with self.assertRaises(ValidationError):
            self.ext.register_fraud_rule(ADMIN, "x", "bogus", "c", "a")

    def test_finding_changes_no_core_case(self):
        case = self.store.create_case(OPERATOR, "claim", "Claim")
        before = copy.deepcopy(self.store._cases[case["id"]])
        finding = self.ext.record_fraud_finding(
            OPERATOR, case["id"], "possible_duplicate_reported")
        self.assertIs(finding["reference_stub"], True)
        self.assertIs(finding["detected_here"], False)
        self.assertIs(finding["adjudicated_here"], False)
        self.assertEqual(self.store._cases[case["id"]], before)


class TestConnectorStub(ExtFixture):
    """Idx 158 — integration connectors (reference)."""

    def test_connector_and_sync_labels(self):
        connector = self.ext.register_connector(
            OPERATOR, "itsm/connector-3", "incident system")
        self.assertIs(connector["reference_stub"], True)
        self.assertIs(connector["reference_transport"], True)
        self.assertIs(connector["connected_here"], False)
        sync = self.ext.record_connector_sync(
            OPERATOR, connector["id"], "reported_synced",
            reported_count=42)
        self.assertIs(sync["reference_stub"], True)
        self.assertIs(sync["reference_transport"], True)
        self.assertIs(sync["synced_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.record_connector_sync(OPERATOR, "con-999", "x")


class TestMlStub(ExtFixture):
    """Idx 159 — AI/ML models (reference)."""

    def test_model_and_output_labels(self):
        model = self.ext.register_model(
            OPERATOR, "lm/ai-obs", "anomaly_detection")
        self.assertIs(model["reference_stub"], True)
        self.assertIs(model["inference_here"], False)
        self.assertIs(model["trained_here"], False)
        output = self.ext.record_model_output(
            OPERATOR, model["id"], "anomaly_reported",
            output_ref="ml-out-88")
        self.assertIs(output["reference_stub"], True)
        self.assertIs(output["inference_here"], False)

    def test_output_creates_no_alert(self):
        model = self.ext.register_model(OPERATOR, "lm/ai-obs", "forecast")
        alerts_before = len(self.store.list_alerts(actor=OPERATOR))
        self.ext.record_model_output(OPERATOR, model["id"], "forecast_x")
        self.assertEqual(len(self.store.list_alerts(actor=OPERATOR)),
                         alerts_before)


class TestCrossCutting(ExtFixture):
    """Privacy scan, core-untouched pins, audit behavior, rollback."""

    def _build_everything(self):
        ext = self.ext
        req = ext.create_access_request(OPERATOR, self.agent["id"], "t/x")
        ext.record_access_outcome(ADMIN, req["id"], "reported_granted")
        ext.record_access_session(OPERATOR, req["id"], "sess-1",
                                  "reported_active")
        ext.record_risk_signal(OPERATOR, self.agent["id"], "label_a")
        ext.record_recommendation(OPERATOR, self.agent["id"], "step_up")
        clearance = ext.open_clearance_case(OPERATOR, self.agent["id"],
                                            "secret")
        ext.record_clearance_outcome(OPERATOR, clearance["id"],
                                     "reported_interim")
        ext.create_article(OPERATOR, "Title", "Body")
        survey = ext.create_survey(OPERATOR, "CSAT")
        ext.record_survey_response(OPERATOR, survey["id"],
                                   self.contact["id"], 5)
        ext.create_sla_policy(ADMIN, "Std", {"normal": 60})
        source = ext.register_collection_source(OPERATOR, "lm/c", "collector")
        ext.record_collection_report(OPERATOR, source["id"], "r",
                                     reported_count=3)
        session = ext.record_telephony_session(OPERATOR, "cc-1",
                                               "reported_connected")
        ext.record_routing_decision(OPERATOR, session["id"],
                                    self.queue["id"], "reported_routed")
        ext.register_fraud_rule(ADMIN, "Dup", "claim", "cond", "act")
        case = self.store.create_case(OPERATOR, "claim", "Claim")
        ext.record_fraud_finding(OPERATOR, case["id"], "label")
        connector = ext.register_connector(OPERATOR, "c/1", "sys")
        ext.record_connector_sync(OPERATOR, connector["id"],
                                  "reported_synced")
        model = ext.register_model(OPERATOR, "m/1", "anomaly")
        ext.record_model_output(OPERATOR, model["id"], "label")

    def test_forbidden_key_scan(self):
        self._build_everything()
        collections = [
            self.ext._pam_requests, self.ext._pam_outcomes,
            self.ext._pam_sessions, self.ext._risk_signals,
            self.ext._recommendations, self.ext._clearance_cases,
            self.ext._clearance_outcomes, self.ext._articles,
            self.ext._article_revisions, self.ext._surveys,
            self.ext._survey_responses, self.ext._sla_policies,
            self.ext._obs_sources, self.ext._obs_reports,
            self.ext._tel_sessions, self.ext._routing_records,
            self.ext._fraud_rules, self.ext._fraud_findings,
            self.ext._connectors, self.ext._connector_syncs,
            self.ext._models, self.ext._model_outputs,
        ]
        scanned = 0
        for collection in collections:
            for record in collection.values():
                scanned += 1
                for _path, key in _scan_keys(record):
                    lowered = key.lower()
                    for fragment in FORBIDDEN_FRAGMENTS:
                        self.assertNotIn(fragment, lowered)
        self.assertEqual(scanned, 22)
        # No score-shaped key on the risk, survey, or policy records.
        for collection in (self.ext._risk_signals,
                           self.ext._recommendations, self.ext._surveys,
                           self.ext._survey_responses,
                           self.ext._sla_policies):
            for record in collection.values():
                for _path, key in _scan_keys(record):
                    self.assertNotIn("score", key.lower())

    def test_stub_creations_change_no_core_records(self):
        case = self.store.create_case(OPERATOR, "claim", "Claim")
        alert = self.store.raise_alert(OPERATOR, "warning", "heads up")

        def counts():
            return {name: len(getattr(self.store, name)) for name in (
                "_agents", "_contacts", "_queues", "_cases", "_callbacks",
                "_interactions", "_alerts", "_rules")}

        before = counts()
        source = self.ext.register_collection_source(
            OPERATOR, "lm/c", "collector")
        self.ext.record_collection_report(OPERATOR, source["id"], "r")
        session = self.ext.record_telephony_session(
            OPERATOR, "cc-1", "reported_connected", case_id=case["id"],
            )
        self.ext.record_routing_decision(
            OPERATOR, session["id"], self.queue["id"], "reported_routed")
        rule = self.ext.register_fraud_rule(ADMIN, "Dup", "claim", "c", "a")
        self.ext.record_fraud_finding(OPERATOR, case["id"], "label",
                                      rule_id=rule["id"])
        connector = self.ext.register_connector(OPERATOR, "c/1", "sys")
        self.ext.record_connector_sync(OPERATOR, connector["id"], "ok")
        model = self.ext.register_model(OPERATOR, "m/1", "anomaly")
        self.ext.record_model_output(OPERATOR, model["id"], "label",
                                     alert_id=alert["id"])
        self.assertEqual(counts(), before)

    def test_denied_attempt_is_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_access_request(VIEWER, self.agent["id"], "t/x")
        self.assertIn("ext_case_write:denied", self.audit_actions())

    def test_successful_mutation_is_audited(self):
        self.ext.create_survey(OPERATOR, "CSAT")
        self.assertIn("ext_survey_create", self.audit_actions())

    def test_audit_failure_rolls_back(self):
        class BrokenAudit(AuditLog):
            def record(self, *args, **kwargs):
                raise RuntimeError("audit unavailable")

        good_audit = self.store.audit
        self.store.audit = BrokenAudit()
        try:
            with self.assertRaises(RuntimeError):
                self.ext.create_survey(OPERATOR, "CSAT")
        finally:
            self.store.audit = good_audit
        self.assertEqual(self.ext._surveys, {})
        survey = self.ext.create_survey(OPERATOR, "CSAT")
        self.assertEqual(survey["id"], "svy-1")  # id rolled back too


if __name__ == "__main__":
    unittest.main()
