# Tests for the final GAPS batch extensions of the Customer
# Service L1 merged build (Group 26): the 10 open Extended
# entries of the group's GAPS.md section --
#   built (7): automation execution engines; GRC platform;
#              knowledge base articles; satisfaction / CSAT
#              surveys; SLA policy engine; notification delivery
#              & status-page hosting; reporting / analytics
#              engines beyond registry reporting;
#   labeled reference implementations (3): event detection,
#              diagnosis & orchestration engines; real-time
#              channels (live chat, voice / telephony); AI
#              assistance / deflection.
# See BATCH.md in the group directory for the per-entry
# dispositions. The forms mirror the Customer Service L2 batch
# unit; the three Moderate-tier sibling-domain stubs that unit also
# carried (commerce, relocation, e-signature) are not in this unit.
#
# The automation rule registry still never executes (the founding
# doctrine, pinned by tests/test_core.py), every extension record
# carries its not-here labels, derivation surfaces store nothing,
# and person-shaped refs resolve against the core's already
# registered requesters.

import unittest
from datetime import datetime, timedelta

from custsvc.access import User
from custsvc.errors import NotFoundError, PermissionDenied, ValidationError
from custsvc.extensions import CustsvcExtensions
from custsvc_helpers import (
    ADMIN,
    AGENT,
    FUTURE_DUE,
    NOW,
    PAST_DUE,
    VIEWER,
    make_case,
    make_store,
)


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, self.rsp1, self.rsp2 = (
            make_store())
        self.ext = CustsvcExtensions(self.store)
        self.ref = self.requester["ref"]

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def make_rule(self, **kwargs):
        defaults = dict(
            name="Auto-assign portal cases",
            trigger="case_created",
            condition="channel == portal",
            action_text="assign to rsp-1",
        )
        defaults.update(kwargs)
        return self.store.create_rule(actor=ADMIN, **defaults)


def at(case, **delta):
    """ISO instant offset from a case view's creation time."""
    base = datetime.fromisoformat(case["created_utc"])
    return (base + timedelta(**delta)).isoformat()


class TestAutomationExecutionRequests(BatchFixture):
    """Entry: Automation execution engines -- built as execution-
    REQUEST records plus verbatim outcome reports. The founding
    doctrine stands: the rule registry never executes, and a
    request provably changes no core state."""

    def test_request_record_labels(self):
        rule = self.make_rule()
        request = self.ext.request_rule_execution(rule["id"], ADMIN)
        self.assertEqual(request["id"], "exec-1")
        self.assertIs(request["executed_here"], False)
        self.assertEqual(request["state"], "recorded_request_only")
        self.assertEqual(request["rule_name"], rule["name"])

    def test_unknown_rule_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.request_rule_execution("rule-99", ADMIN)

    def test_agent_may_not_request_execution(self):
        rule = self.make_rule()
        with self.assertRaises(PermissionDenied):
            self.ext.request_rule_execution(rule["id"], AGENT)
        self.assertIn("ext_rule_execution_request:denied",
                      self.audit_actions())

    def test_request_changes_no_core_state(self):
        rule = self.make_rule()
        case_before = make_case(self.store, self.requester)
        rules_before = self.store.list_rules(ADMIN)
        self.ext.request_rule_execution(rule["id"], ADMIN)
        self.assertEqual(self.store.list_rules(ADMIN), rules_before)
        self.assertEqual(self.store.get_case(case_before["id"], ADMIN),
                         case_before)

    def test_report_verbatim_and_summary(self):
        rule = self.make_rule()
        request = self.ext.request_rule_execution(rule["id"], ADMIN)
        report = self.ext.record_execution_report(
            request["id"], "reported_completed", ADMIN)
        self.assertEqual(report["outcome"], "reported_completed")
        self.assertIs(report["executed_here"], False)
        summary = self.ext.execution_summary(ADMIN)
        self.assertEqual(summary["requests"], 1)
        self.assertEqual(
            summary["reports_by_outcome"]["reported_completed"], 1)
        self.assertIs(summary["executed_here"], False)


class TestGrcPlatform(BatchFixture):
    """Entry: GRC platform (this group's sole GRC claim family) --
    built as framework/control records plus case mappings, with
    posture derived at read as counts only. A framework record is a
    label set: registering one asserts no framework support."""

    def test_framework_and_control_records(self):
        framework = self.ext.register_framework("Example Framework",
                                                AGENT,
                                                version_label="v1")
        self.assertEqual(framework["id"], "fw-1")
        control = self.ext.register_control(framework["id"], "AC-2",
                                            "Account management",
                                            AGENT)
        self.assertEqual(control["id"], "ctl-1")
        self.assertEqual(control["control_ref"], "AC-2")

    def test_mapping_binds_existing_ends(self):
        framework = self.ext.register_framework("F", AGENT)
        control = self.ext.register_control(framework["id"], "X-1",
                                            "Title", AGENT)
        case = make_case(self.store, self.requester)
        mapping = self.ext.map_case_to_control(case["id"],
                                               control["id"], AGENT)
        self.assertEqual(mapping["id"], "cmap-1")
        with self.assertRaises(NotFoundError):
            self.ext.map_case_to_control("case-99", control["id"],
                                         AGENT)
        with self.assertRaises(NotFoundError):
            self.ext.map_case_to_control(case["id"], "ctl-99", AGENT)

    def test_posture_counts_derived_never_stored(self):
        framework = self.ext.register_framework("F", AGENT)
        control = self.ext.register_control(framework["id"], "X-1",
                                            "Title", AGENT)
        early = make_case(self.store, self.requester)
        late = make_case(self.store, self.requester,
                         title="Overdue case", due_at=PAST_DUE)
        self.ext.map_case_to_control(early["id"], control["id"], AGENT)
        self.ext.map_case_to_control(late["id"], control["id"], AGENT)
        posture = self.ext.framework_posture(framework["id"], ADMIN,
                                             now=NOW)
        self.assertEqual(posture["controls"], 1)
        self.assertEqual(posture["mappings"], 2)
        self.assertEqual(posture["mapped_cases"], 2)
        self.assertEqual(posture["mapped_cases_by_status"], {"new": 2})
        self.assertEqual(posture["mapped_cases_breached"], 1)
        self.assertEqual(posture["method"],
                         "counts_over_mapping_records")
        record = self.ext.get_framework(framework["id"], ADMIN)
        self.assertEqual(
            set(record.keys()),
            {"id", "name", "version_label", "created_by", "created_utc"})

    def test_viewer_may_not_register_framework(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_framework("F", VIEWER)
        self.assertIn("ext_framework_register:denied",
                      self.audit_actions())


class TestKnowledgeBase(BatchFixture):
    """Entry: Knowledge base articles -- built as article records
    with append-only revision records; the stored article record
    holds tags and provenance only."""

    def test_article_record_shape_and_first_revision(self):
        article = self.ext.create_article("Reset a password",
                                          "Use the portal.", AGENT,
                                          tags=["access"])
        self.assertEqual(article["id"], "kb-1")
        self.assertEqual(article["title"], "Reset a password")
        self.assertEqual(article["revision_count"], 1)
        stored = self.ext._records[("article", "kb-1")]
        self.assertEqual(
            set(stored.keys()),
            {"id", "tags", "created_by", "created_utc"})

    def test_revisions_append_only(self):
        self.ext.create_article("T", "first body", AGENT)
        view = self.ext.revise_article("kb-1", AGENT,
                                       body="second body")
        self.assertEqual(view["body"], "second body")
        self.assertEqual(view["revision_count"], 2)
        revisions = self.ext.list_article_revisions("kb-1", VIEWER)
        self.assertEqual([r["body"] for r in revisions],
                         ["first body", "second body"])
        self.assertEqual([r["revision"] for r in revisions], [1, 2])

    def test_empty_revision_rejected(self):
        self.ext.create_article("T", "B", AGENT)
        with self.assertRaises(ValidationError):
            self.ext.revise_article("kb-1", AGENT)

    def test_search_articles(self):
        self.ext.create_article("Reset a password", "Use the portal.",
                                AGENT)
        self.ext.create_article("File a claim", "Use the form.", AGENT)
        hits = self.ext.search_articles("portal", VIEWER)
        self.assertEqual([h["id"] for h in hits], ["kb-1"])

    def test_viewer_may_not_create_article(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_article("T", "B", VIEWER)


class TestSurveys(BatchFixture):
    """Entry: Satisfaction / CSAT surveys -- built as instrument and
    response records; responses verbatim, tallies derived at read
    with the mean as an exact rational."""

    def _survey(self, **kwargs):
        return self.ext.create_survey("How did we do?", AGENT, **kwargs)

    def test_survey_shape_and_scale_validation(self):
        survey = self._survey()
        self.assertEqual(survey["id"], "svy-1")
        self.assertEqual(survey["scale_max"], 5)
        self.assertEqual(
            set(survey.keys()),
            {"id", "title", "case_id", "scale_max", "created_by",
             "created_utc"})
        for bad in (1, 11, True, 2.5):
            with self.assertRaises(ValidationError):
                self.ext.create_survey("Bad", AGENT, scale_max=bad)

    def test_response_verbatim_and_bounds(self):
        survey = self._survey()
        response = self.ext.record_survey_response(
            survey["id"], self.ref, 5, AGENT, comment="Great help.")
        self.assertEqual(response["id"], "svr-1")
        self.assertEqual(response["rating"], 5)
        self.assertEqual(response["comment"], "Great help.")
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(survey["id"], self.ref, 6,
                                            AGENT)
        with self.assertRaises(NotFoundError):
            self.ext.record_survey_response(survey["id"], "ghost-404", 3,
                                            AGENT)
        second = self.ext.record_survey_response(survey["id"], self.ref,
                                                 4, AGENT)
        self.assertEqual(second["id"], "svr-2")

    def test_tally_derived_exact_rational(self):
        survey = self._survey()
        for rating in (5, 4, 4):
            self.ext.record_survey_response(survey["id"], self.ref,
                                            rating, AGENT)
        tally = self.ext.survey_tally(survey["id"], ADMIN)
        self.assertEqual(tally["response_count"], 3)
        self.assertEqual(tally["distribution"],
                         {"1": 0, "2": 0, "3": 0, "4": 2, "5": 1})
        self.assertEqual(tally["mean_rating"],
                         {"numerator": 13, "denominator": 3})
        self.assertEqual(tally["method"],
                         "exact_rational_mean_of_recorded_ratings")

    def test_tally_empty_survey(self):
        survey = self._survey()
        tally = self.ext.survey_tally(survey["id"], ADMIN)
        self.assertEqual(tally["response_count"], 0)
        self.assertIsNone(tally["mean_rating"])

    def test_viewer_may_not_record_response(self):
        survey = self._survey()
        with self.assertRaises(PermissionDenied):
            self.ext.record_survey_response(survey["id"], self.ref, 3,
                                            VIEWER)
        self.assertIn("ext_survey_response:denied", self.audit_actions())


class TestSlaPolicies(BatchFixture):
    """Entry: SLA policy engine -- built as policy records holding
    terms as data, with breach state derived at read from core case
    records against the recorded terms (the seam is the batch's
    fresh negative control)."""

    def _policy(self, targets=None):
        return self.ext.create_sla_policy(
            "Standard", targets or {"high": 60, "normal": 240}, ADMIN)

    def test_policy_shape_and_validation(self):
        policy = self._policy()
        self.assertEqual(policy["id"], "sla-1")
        self.assertEqual(policy["targets_minutes"],
                         {"high": 60, "normal": 240})
        self.assertEqual(
            set(policy.keys()),
            {"id", "name", "targets_minutes", "created_by", "created_utc"})
        for bad in ({"urgent": 30}, {"high": 0}, {"high": 1.5},
                    {"high": True}, {}):
            with self.assertRaises(ValidationError):
                self.ext.create_sla_policy("Bad", bad, ADMIN)

    def test_agent_may_not_create_policy(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_sla_policy("Standard", {"high": 60}, AGENT)
        self.assertIn("ext_sla_policy_create:denied", self.audit_actions())

    def test_breach_derived_from_recorded_terms(self):
        policy = self._policy()
        case = make_case(self.store, self.requester, priority="high")
        early = self.ext.sla_case_view(policy["id"], case["id"], ADMIN,
                                       now=at(case, minutes=30))
        self.assertIs(early["breached"], False)
        self.assertEqual(early["target_minutes"], 60)
        late = self.ext.sla_case_view(policy["id"], case["id"], ADMIN,
                                      now=at(case, minutes=61))
        self.assertIs(late["breached"], True)
        self.assertEqual(late["effective_due_at"], at(case, minutes=60))

    def test_uncovered_priority_never_breached(self):
        policy = self._policy({"high": 60})
        case = make_case(self.store, self.requester, priority="low")
        view = self.ext.sla_case_view(policy["id"], case["id"], ADMIN,
                                      now=at(case, minutes=6000))
        self.assertIs(view["covered"], False)
        self.assertIs(view["breached"], False)
        self.assertIsNone(view["effective_due_at"])

    def test_terminal_case_never_breached(self):
        policy = self._policy()
        case = make_case(self.store, self.requester, priority="high")
        self.store.set_case_status(case["id"], "open", AGENT)
        self.store.set_case_status(case["id"], "in_progress", AGENT)
        self.store.set_case_status(case["id"], "resolved", AGENT)
        view = self.ext.sla_case_view(policy["id"], case["id"], ADMIN,
                                      now=at(case, minutes=6000))
        self.assertIs(view["breached"], False)

    def test_breach_report_counts(self):
        policy = self._policy()
        old_case = make_case(self.store, self.requester, priority="high")
        make_case(self.store, self.requester, priority="normal",
                  title="Second case")
        report = self.ext.sla_breach_report(
            policy["id"], ADMIN, now=at(old_case, minutes=61))
        self.assertEqual(report["evaluated"], 2)
        self.assertEqual(report["breached"], 1)
        self.assertEqual(report["breached_case_ids"], [old_case["id"]])
        self.assertEqual(report["by_priority"]["high"],
                         {"evaluated": 1, "breached": 1})

    def test_policy_views_do_not_touch_core_case(self):
        policy = self._policy()
        case = make_case(self.store, self.requester, priority="high")
        self.ext.sla_case_view(policy["id"], case["id"], ADMIN,
                               now=at(case, minutes=61))
        after = self.store.get_case(case["id"], ADMIN)
        self.assertIsNone(after["due_at"])
        self.assertEqual(after["status"], "new")


class MutantCustsvcExtensions(CustsvcExtensions):
    """Mutant SLA derivation: policy breach is never derived."""

    def _is_breached_under_policy(self, case, policy, now_dt):
        """Batch negative control mutant -- no-op: a case is never
        past its recorded policy target."""
        return False


class TestSlaNegativeControl(BatchFixture):
    """Fresh negative control for the batch: breach state under a
    recorded SLA policy is DERIVED from the case record and the
    policy terms. Each leg asserts (1) the canonical expectation
    from the real implementation, (2) the mutant would NOT produce
    it, and (3) treating the mutant's outcome as the expected
    outcome fails."""

    def _fixture(self, ext_class):
        store, audit, requester, rsp1, rsp2 = make_store()
        ext = ext_class(store)
        policy = ext.create_sla_policy("Standard", {"high": 60}, ADMIN)
        case = make_case(store, requester, priority="high")
        return ext, policy, case

    def test_policy_breach_is_derived(self):
        # Canonical: the real implementation derives breach once the
        # recorded target has passed.
        ext, policy, case = self._fixture(CustsvcExtensions)
        canonical = ext.sla_case_view(policy["id"], case["id"], ADMIN,
                                      now=at(case, minutes=61))
        self.assertIs(canonical["breached"], True)

        # Mutant: the same fixture under the no-op seam would NOT
        # produce the canonical outcome.
        mext, mpolicy, mcase = self._fixture(MutantCustsvcExtensions)
        mutant_view = mext.sla_case_view(mpolicy["id"], mcase["id"],
                                         ADMIN,
                                         now=at(mcase, minutes=61))
        self.assertIs(mutant_view["breached"], False)

        # Treating the mutant's outcome as the expectation fails.
        with self.assertRaises(AssertionError):
            self.assertIs(mutant_view["breached"], True)


class TestNotificationsAndStatusPages(BatchFixture):
    """Entry: Notification delivery & status-page hosting -- built
    as notification records with reference-transport delivery
    reports (nothing is delivered) and status-page records over the
    core's derived public view (nothing is hosted)."""

    def test_notification_record_labels(self):
        case = make_case(self.store, self.requester)
        note = self.ext.record_notification(case["id"], "email",
                                            self.ref, AGENT)
        self.assertEqual(note["id"], "ntf-1")
        self.assertIs(note["reference_transport"], True)
        self.assertIs(note["delivered_here"], False)
        self.assertEqual(note["state"], "recorded_reference_only")

    def test_notification_requires_existing_ends(self):
        case = make_case(self.store, self.requester)
        with self.assertRaises(NotFoundError):
            self.ext.record_notification("case-99", "email", self.ref,
                                         AGENT)
        with self.assertRaises(NotFoundError):
            self.ext.record_notification(case["id"], "email", "ghost-1",
                                         AGENT)

    def test_delivery_report_verbatim_and_summary(self):
        case = make_case(self.store, self.requester)
        note = self.ext.record_notification(case["id"], "email",
                                            self.ref, AGENT)
        report = self.ext.record_delivery_report(
            note["id"], "reported_delivered", AGENT)
        self.assertEqual(report["outcome"], "reported_delivered")
        self.assertIs(report["reference_transport"], True)
        self.assertIs(report["delivered_here"], False)
        summary = self.ext.notification_summary(ADMIN)
        self.assertEqual(summary["notifications"], 1)
        self.assertEqual(
            summary["reports_by_outcome"]["reported_delivered"], 1)
        self.assertIs(summary["delivered_here"], False)

    def test_status_page_record_and_view(self):
        page = self.ext.record_status_page("Public status", AGENT)
        self.assertEqual(page["id"], "stp-1")
        self.assertIs(page["reference_stub"], True)
        self.assertIs(page["hosted_here"], False)
        make_case(self.store, self.requester, priority="critical")
        view = self.ext.status_page_view(page["id"], VIEWER, now=NOW)
        self.assertEqual(view["overall"], "outage")
        self.assertEqual(view["page_id"], "stp-1")
        self.assertIs(view["hosted_here"], False)
        self.assertEqual(view["served_from"],
                         "core_public_status_derivation")

    def test_viewer_may_not_record_notification(self):
        case = make_case(self.store, self.requester)
        with self.assertRaises(PermissionDenied):
            self.ext.record_notification(case["id"], "email", self.ref,
                                         VIEWER)
        self.assertIn("ext_notification_record:denied",
                      self.audit_actions())


class TestAnalyticsReport(BatchFixture):
    """Entry: Reporting / analytics engines beyond registry
    reporting -- built as deterministic derivations over core
    records at read; counts and count pairs only."""

    def test_report_counts(self):
        first = make_case(self.store, self.requester, priority="high",
                          channel="email", due_at=PAST_DUE)
        self.store.assign_case(first["id"], self.rsp1["id"], AGENT)
        make_case(self.store, self.requester, title="Phone issue",
                  channel="phone")
        alert = self.store.ingest_alert("monitor-1", "Portal slow",
                                        "major", AGENT,
                                        case_id=first["id"])
        self.store.ingest_alert("monitor-1", "Queue depth high",
                                "warning", AGENT)
        report = self.ext.analytics_report(ADMIN, now=NOW)
        self.assertEqual(report["cases"], 2)
        self.assertEqual(report["cases_by_channel"],
                         {"email": 1, "phone": 1})
        self.assertEqual(
            report["cases_by_assignee"][self.rsp1["id"]],
            {"cases": 1, "breached": 1})
        self.assertEqual(report["cases_by_assignee"]["unassigned"],
                         {"cases": 1, "breached": 0})
        self.assertEqual(report["breached_by_priority"]["high"], 1)
        self.assertEqual(report["distinct_requesters_with_cases"], 1)
        self.assertEqual(report["alerts_by_severity"],
                         {"major": 1, "warning": 1})
        self.assertEqual(report["alert_linkage"],
                         {"linked": 1, "unlinked": 1, "total": 2})
        self.assertEqual(report["method"],
                         "deterministic_counts_over_core_records")

    def test_report_is_derived_not_stored(self):
        make_case(self.store, self.requester)
        first = self.ext.analytics_report(ADMIN, now=NOW)
        make_case(self.store, self.requester, title="Another")
        second = self.ext.analytics_report(ADMIN, now=NOW)
        self.assertEqual((first["cases"], second["cases"]), (1, 2))


class TestDetectionOrchestrationStub(BatchFixture):
    """Stub entry: Event detection, diagnosis & orchestration
    engines -- source registrations and verbatim run records; the
    core alert ingest remains the only alert path."""

    def test_source_and_run_labels(self):
        source = self.ext.register_detection_source("siem-ref-1", AGENT)
        self.assertEqual(source["id"], "det-1")
        self.assertIs(source["detects_here"], False)
        run = self.ext.record_orchestration_run(
            source["id"], "reported_completed", AGENT)
        self.assertEqual(run["outcome"], "reported_completed")
        self.assertIs(run["executed_here"], False)
        self.assertIs(run["reference_stub"], True)

    def test_run_creates_no_alert(self):
        source = self.ext.register_detection_source("siem-ref-1", AGENT)
        self.ext.record_orchestration_run(source["id"],
                                          "reported_completed", AGENT)
        self.assertEqual(self.store.list_alerts(ADMIN), [])

    def test_run_may_reference_existing_alert_only(self):
        source = self.ext.register_detection_source("siem-ref-1", AGENT)
        alert = self.store.ingest_alert("siem-ref-1", "Spike", "major",
                                        AGENT)
        run = self.ext.record_orchestration_run(
            source["id"], "reported_partial", AGENT, alert_id=alert["id"])
        self.assertEqual(run["alert_id"], alert["id"])
        with self.assertRaises(NotFoundError):
            self.ext.record_orchestration_run(
                source["id"], "reported_partial", AGENT,
                alert_id="alert-99")


class TestChannelStub(BatchFixture):
    """Stub entry: Real-time channels -- channel registrations and
    reported session records; no media exists in this build."""

    def test_channel_and_session_labels(self):
        channel = self.ext.register_channel("chat-queue-1", "live_chat",
                                            AGENT)
        self.assertEqual(channel["id"], "chn-1")
        self.assertIs(channel["media_here"], False)
        case = make_case(self.store, self.requester)
        session = self.ext.record_channel_session(channel["id"],
                                                  case["id"], AGENT)
        self.assertEqual(session["id"], "chs-1")
        self.assertIs(session["connected_here"], False)
        self.assertIs(session["reference_stub"], True)

    def test_bad_kind_and_unknown_case_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_channel("x-1", "smoke_signal", AGENT)
        channel = self.ext.register_channel("voice-1", "voice", AGENT)
        with self.assertRaises(NotFoundError):
            self.ext.record_channel_session(channel["id"], "case-99",
                                            AGENT)


class TestAiAssistanceStub(BatchFixture):
    """Stub entry: AI assistance / deflection -- assistant
    registrations and verbatim deflection reports; no model runs
    and no case is decided here."""

    def test_assistant_record_labels(self):
        assistant = self.ext.register_assistant("helper-ref-1", AGENT)
        self.assertEqual(assistant["id"], "ai-1")
        self.assertIs(assistant["inference_here"], False)
        self.assertEqual(assistant["method"], "recorded_declaration_only")
        self.assertIs(assistant["reference_stub"], True)

    def test_deflection_report_verbatim_case_untouched(self):
        assistant = self.ext.register_assistant("helper-ref-1", AGENT)
        case = make_case(self.store, self.requester)
        report = self.ext.record_deflection_report(
            assistant["id"], case["id"], "reported_deflected", AGENT)
        self.assertEqual(report["outcome"], "reported_deflected")
        self.assertIs(report["decided_here"], False)
        after = self.store.get_case(case["id"], ADMIN)
        self.assertEqual(after["status"], "new")


class TestStubCoreIsolation(BatchFixture):
    """Cross-cutting: creating every stub-family record (and an
    automation execution request) changes no core record."""

    def _core_counts(self):
        return {
            "cases": len(self.store.list_cases(ADMIN)),
            "alerts": len(self.store.list_alerts(ADMIN)),
            "rules": len(self.store.list_rules(ADMIN)),
            "requesters": len(self.store.list_requesters(ADMIN)),
            "responders": len(self.store.list_responders(ADMIN)),
            "schedules": len(self.store.list_schedules(ADMIN)),
        }

    def test_stubs_change_no_core_record(self):
        rule = self.make_rule()
        case = make_case(self.store, self.requester)
        before = self._core_counts()
        self.ext.request_rule_execution(rule["id"], ADMIN)
        det = self.ext.register_detection_source("siem-1", AGENT)
        self.ext.record_orchestration_run(det["id"],
                                          "reported_completed", AGENT)
        chn = self.ext.register_channel("chat-1", "live_chat", AGENT)
        self.ext.record_channel_session(chn["id"], case["id"], AGENT)
        ai = self.ext.register_assistant("helper-1", AGENT)
        self.ext.record_deflection_report(ai["id"], case["id"],
                                          "reported_escalated", AGENT)
        self.assertEqual(self._core_counts(), before)


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins for the whole extension surface."""

    def test_ext_actions_recorded_on_core_audit(self):
        self.ext.register_framework("Example", AGENT)
        self.ext.create_article("T", "B", AGENT)
        actions = self.audit_actions()
        self.assertIn("ext_framework_register", actions)
        self.assertIn("ext_article_create", actions)

    def test_denied_attempt_audited_and_no_state_change(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_survey("Nope", VIEWER)
        self.assertIn("ext_survey_create:denied", self.audit_actions())
        self.assertEqual(self.ext.list_surveys(ADMIN), [])

    def test_unknown_extension_record(self):
        with self.assertRaises(NotFoundError):
            self.ext.get_framework("fw-99", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.get_sla_policy("sla-99", ADMIN)

    def test_audit_failure_rolls_back_record_and_id(self):
        original = self.audit.record

        def broken(*args, **kwargs):
            raise RuntimeError("audit unavailable")

        self.audit.record = broken
        try:
            with self.assertRaises(RuntimeError):
                self.ext.register_framework("Example", AGENT)
        finally:
            self.audit.record = original
        self.assertEqual(self.ext.list_frameworks(ADMIN), [])
        framework = self.ext.register_framework("Example", AGENT)
        self.assertEqual(framework["id"], "fw-1")


if __name__ == "__main__":
    unittest.main()
