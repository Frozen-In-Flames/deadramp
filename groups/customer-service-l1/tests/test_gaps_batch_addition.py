# Tests for the final GAPS batch — SECOND unit of the Customer
# Service L1 merged build (Group 26): the one OPEN entry of the
# GAPS.md section "Remainder Addition — Customer Service L1
# (+1 fork)" —
#   built (1): proactive engagement & outreach, in the records
#              form this group's first batch unit adjudicated for
#              notification delivery: campaign definitions whose
#              trigger/audience terms are held as data and never
#              evaluated, suppression (opt-out) records with a
#              guard seam, outreach attempt records carrying
#              reference_transport: true / sent_here: false, and
#              outcome reports stored verbatim.
# See BATCH-ADDITION.md in the group directory for the disposition.
#
# Nothing on this surface sends, evaluates a trigger, or computes
# an engagement figure: views and summaries are counts over the
# surface's own records, no float rate/ratio/percentage is
# representable, people are named only by the core's registered
# opaque requester refs, and no signature can accept message
# content (content-shaped kwargs raise TypeError).

import unittest

from custsvc.errors import NotFoundError, PermissionDenied, ValidationError
from custsvc.extensions_addition import CustsvcExtensionsAddition
from custsvc_helpers import (
    ADMIN,
    AGENT,
    VIEWER,
    make_case,
    make_store,
)

FORBIDDEN_KEYS = {
    # content-shaped: no record or view may hold interaction content
    "message", "body", "content", "narrative", "text",
    # tally-shaped: no engagement figure may be computed or stored
    "tally", "score", "rate", "ratio", "percentage", "mean",
    "average", "rank", "ranking", "total",
}


def walk_pairs(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
            yield from walk_pairs(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            yield from walk_pairs(item)


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, self.rsp1, self.rsp2 = (
            make_store())
        self.ext = CustsvcExtensionsAddition(self.store)
        self.ref = self.requester["ref"]

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def make_campaign(self, **kwargs):
        defaults = dict(
            name="Portal re-engagement drive",
            kind="campaign",
            channel_label="portal_notice",
            trigger_label="case_resolved",
        )
        defaults.update(kwargs)
        return self.ext.create_campaign(actor=ADMIN, **defaults)

    def core_counts(self):
        return {
            "cases": len(self.store.list_cases(ADMIN)),
            "alerts": len(self.store.list_alerts(ADMIN)),
            "rules": len(self.store.list_rules(ADMIN)),
            "requesters": len(self.store.list_requesters(ADMIN)),
            "responders": len(self.store.list_responders(ADMIN)),
            "schedules": len(self.store.list_schedules(ADMIN)),
        }


class TestCampaignDefinitions(AdditionFixture):
    """Entry: proactive engagement & outreach — campaign
    definitions are records whose terms are held as data."""

    def test_definition_record_labels(self):
        campaign = self.make_campaign()
        self.assertEqual(campaign["id"], "cmp-1")
        self.assertEqual(campaign["kind"], "campaign")
        self.assertEqual(campaign["channel_label"], "portal_notice")
        self.assertEqual(campaign["trigger_label"], "case_resolved")
        self.assertIs(campaign["evaluated_here"], False)
        self.assertIs(campaign["sends_here"], False)
        self.assertEqual(campaign["state"], "definition_only")

    def test_definition_validation(self):
        with self.assertRaises(ValidationError):
            self.make_campaign(kind="blast")
        with self.assertRaises(ValidationError):
            self.make_campaign(name="  ")
        with self.assertRaises(ValidationError):
            self.make_campaign(trigger_label="")
        self.assertEqual(self.ext.list_campaigns(ADMIN), [])

    def test_definition_trigger_is_never_evaluated(self):
        # A campaign whose recorded trigger matches a core event
        # produces no attempt and touches no case: definitions are
        # data, attempts exist only when an operator records one.
        self.make_campaign(trigger_label="case_created")
        before = self.core_counts()
        case = make_case(self.store, self.requester)
        self.assertEqual(self.ext.list_outreach_attempts(ADMIN), [])
        after = self.core_counts()
        after["cases"] -= 1  # the case this test itself created
        self.assertEqual(after, before)
        self.assertEqual(
            self.store.get_case(case["id"], ADMIN)["status"], "new")

    def test_get_and_list_campaigns(self):
        first = self.make_campaign()
        second = self.make_campaign(name="Nudge", kind="nudge")
        self.assertEqual(self.ext.get_campaign(first["id"], VIEWER), first)
        self.assertEqual(
            [c["id"] for c in self.ext.list_campaigns(VIEWER)],
            [first["id"], second["id"]])
        with self.assertRaises(NotFoundError):
            self.ext.get_campaign("cmp-99", ADMIN)

    def test_content_kwargs_raise_type_error(self):
        # No signature on this surface can accept message content:
        # content-shaped arguments are refused by the signature
        # itself, before any state change.
        with self.assertRaises(TypeError):
            self.ext.create_campaign(
                "X", "campaign", "email", "case_created", ADMIN,
                message="hello")
        campaign = self.make_campaign()
        with self.assertRaises(TypeError):
            self.ext.record_outreach_attempt(
                campaign["id"], self.ref, AGENT, body="hello")
        with self.assertRaises(TypeError):
            self.ext.record_suppression(
                self.ref, ADMIN, content="hello")
        self.assertEqual(self.ext.list_outreach_attempts(ADMIN), [])
        self.assertEqual(self.ext.list_suppressions(ADMIN), [])


class TestSuppressions(AdditionFixture):
    """Suppression (opt-out) records: registered requesters only,
    exact duplicates refused."""

    def test_record_and_list(self):
        campaign = self.make_campaign()
        record = self.ext.record_suppression(
            self.ref, AGENT, campaign_id=campaign["id"])
        self.assertEqual(record["id"], "sup-1")
        self.assertEqual(record["requester_ref"], self.ref)
        self.assertEqual(record["campaign_id"], campaign["id"])
        global_record = self.ext.record_suppression(self.ref, AGENT)
        self.assertIsNone(global_record["campaign_id"])
        self.assertEqual(len(self.ext.list_suppressions(ADMIN)), 2)
        self.assertEqual(
            len(self.ext.list_suppressions(
                ADMIN, campaign_id=campaign["id"])), 1)
        self.assertEqual(
            len(self.ext.list_suppressions(
                ADMIN, requester_ref=self.ref)), 2)

    def test_unknown_requester_refused(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_suppression("ghost-404", AGENT)
        self.assertEqual(self.ext.list_suppressions(ADMIN), [])

    def test_unknown_campaign_refused(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_suppression(
                self.ref, AGENT, campaign_id="cmp-99")
        self.assertEqual(self.ext.list_suppressions(ADMIN), [])

    def test_duplicate_refused(self):
        campaign = self.make_campaign()
        self.ext.record_suppression(
            self.ref, AGENT, campaign_id=campaign["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_suppression(
                self.ref, AGENT, campaign_id=campaign["id"])
        # A different scope is a different record.
        self.ext.record_suppression(self.ref, AGENT)
        self.assertEqual(len(self.ext.list_suppressions(ADMIN)), 2)


class TestOutreachAttempts(AdditionFixture):
    """Outreach attempt records: reference-transport requests
    against registered requesters; suppressed requesters refused
    whole by the suppression seam."""

    def test_attempt_record_labels(self):
        campaign = self.make_campaign()
        attempt = self.ext.record_outreach_attempt(
            campaign["id"], self.ref, AGENT)
        self.assertEqual(attempt["id"], "out-1")
        self.assertEqual(attempt["campaign_id"], campaign["id"])
        self.assertEqual(attempt["requester_ref"], self.ref)
        self.assertIsNone(attempt["case_id"])
        self.assertIs(attempt["reference_transport"], True)
        self.assertIs(attempt["sent_here"], False)
        self.assertEqual(attempt["state"], "recorded_reference_only")

    def test_attempt_binds_existing_case(self):
        campaign = self.make_campaign()
        case = make_case(self.store, self.requester)
        attempt = self.ext.record_outreach_attempt(
            campaign["id"], self.ref, AGENT, case_id=case["id"])
        self.assertEqual(attempt["case_id"], case["id"])

    def test_unknown_ends_refused(self):
        campaign = self.make_campaign()
        with self.assertRaises(NotFoundError):
            self.ext.record_outreach_attempt("cmp-99", self.ref, AGENT)
        with self.assertRaises(NotFoundError):
            self.ext.record_outreach_attempt(
                campaign["id"], "ghost-404", AGENT)
        with self.assertRaises(NotFoundError):
            self.ext.record_outreach_attempt(
                campaign["id"], self.ref, AGENT, case_id="case-99")
        self.assertEqual(self.ext.list_outreach_attempts(ADMIN), [])

    def test_suppressed_requester_refused_whole(self):
        campaign = self.make_campaign()
        self.ext.record_suppression(
            self.ref, ADMIN, campaign_id=campaign["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_outreach_attempt(
                campaign["id"], self.ref, AGENT)
        # Refused whole: no record, and no id consumed — the next
        # successful attempt is still out-1.
        self.assertEqual(self.ext.list_outreach_attempts(ADMIN), [])
        other = self.store.create_requester("citizen-002", "Citizen Two",
                                            ADMIN)
        attempt = self.ext.record_outreach_attempt(
            campaign["id"], other["ref"], AGENT)
        self.assertEqual(attempt["id"], "out-1")

    def test_globally_suppressed_refused_for_any_campaign(self):
        first = self.make_campaign()
        second = self.make_campaign(name="Second", kind="nudge")
        self.ext.record_suppression(self.ref, ADMIN)  # global scope
        with self.assertRaises(ValidationError):
            self.ext.record_outreach_attempt(first["id"], self.ref, AGENT)
        with self.assertRaises(ValidationError):
            self.ext.record_outreach_attempt(second["id"], self.ref, AGENT)

    def test_suppression_scoped_to_one_campaign_only(self):
        first = self.make_campaign()
        second = self.make_campaign(name="Second", kind="reengagement")
        self.ext.record_suppression(
            self.ref, ADMIN, campaign_id=first["id"])
        attempt = self.ext.record_outreach_attempt(
            second["id"], self.ref, AGENT)
        self.assertEqual(attempt["campaign_id"], second["id"])


class TestOutreachReports(AdditionFixture):
    """Outcome reports: stored verbatim as a transport elsewhere
    reported them; nothing here sent anything."""

    def _attempt(self):
        campaign = self.make_campaign()
        return self.ext.record_outreach_attempt(
            campaign["id"], self.ref, AGENT)

    def test_report_verbatim_and_labels(self):
        attempt = self._attempt()
        report = self.ext.record_outreach_report(
            attempt["id"], "reported_engaged", AGENT,
            detail="transport ref t-9")
        self.assertEqual(report["id"], "outr-1")
        self.assertEqual(report["attempt_id"], attempt["id"])
        self.assertEqual(report["outcome"], "reported_engaged")
        self.assertEqual(report["detail"], "transport ref t-9")
        self.assertIs(report["reported"], True)
        self.assertIs(report["reference_transport"], True)
        self.assertIs(report["sent_here"], False)

    def test_bad_outcome_and_unknown_attempt_refused(self):
        attempt = self._attempt()
        with self.assertRaises(ValidationError):
            self.ext.record_outreach_report(
                attempt["id"], "delivered", AGENT)
        with self.assertRaises(NotFoundError):
            self.ext.record_outreach_report(
                "out-99", "reported_delivered", AGENT)
        self.assertEqual(self.ext.list_outreach_reports(ADMIN), [])

    def test_flow_changes_no_core_state(self):
        case = make_case(self.store, self.requester)
        before = self.store.get_case(case["id"], ADMIN)
        counts_before = self.core_counts()
        campaign = self.make_campaign()
        attempt = self.ext.record_outreach_attempt(
            campaign["id"], self.ref, AGENT, case_id=case["id"])
        self.ext.record_outreach_report(
            attempt["id"], "reported_delivered", AGENT)
        self.assertEqual(self.store.get_case(case["id"], ADMIN), before)
        self.assertEqual(self.core_counts(), counts_before)


class TestOutreachViews(AdditionFixture):
    """Views and summaries derive counts at read; stored records
    carry no derived key; no figure and no content anywhere."""

    def _flow(self):
        campaign = self.make_campaign()
        first = self.ext.record_outreach_attempt(
            campaign["id"], self.ref, AGENT)
        self.ext.record_outreach_report(
            first["id"], "reported_delivered", AGENT)
        other = self.store.create_requester("citizen-002", "Citizen Two",
                                            ADMIN)
        second = self.ext.record_outreach_attempt(
            campaign["id"], other["ref"], AGENT)
        self.ext.record_outreach_report(
            second["id"], "reported_engaged", AGENT)
        self.ext.record_suppression(
            other["ref"], ADMIN, campaign_id=campaign["id"])
        return campaign

    def test_campaign_view_counts_and_latest(self):
        campaign = self._flow()
        view = self.ext.campaign_view(campaign["id"], VIEWER)
        self.assertEqual(view["attempts"], 2)
        self.assertEqual(view["reports"], 2)
        self.assertEqual(
            view["reports_by_outcome"]["reported_delivered"], 1)
        self.assertEqual(
            view["reports_by_outcome"]["reported_engaged"], 1)
        self.assertEqual(
            view["reports_by_outcome"]["reported_bounced"], 0)
        self.assertEqual(
            view["latest_reported_outcome"], "reported_engaged")
        self.assertEqual(view["suppressions_scoped"], 1)
        self.assertIs(view["derived"], True)
        self.assertIs(view["stored"], False)

    def test_stored_campaign_record_key_set_pinned(self):
        campaign = self._flow()
        stored = self.ext.get_campaign(campaign["id"], ADMIN)
        self.assertEqual(
            set(stored),
            {"id", "name", "kind", "channel_label", "trigger_label",
             "segment_ref", "note", "evaluated_here", "sends_here",
             "state", "created_by", "created_utc"})

    def test_summary_counts_only(self):
        self._flow()
        summary = self.ext.outreach_summary(ADMIN)
        self.assertEqual(summary["campaigns"], 1)
        self.assertEqual(summary["campaigns_by_kind"]["campaign"], 1)
        self.assertEqual(summary["campaigns_by_kind"]["nudge"], 0)
        self.assertEqual(summary["attempts"], 2)
        self.assertEqual(summary["reports"], 2)
        self.assertEqual(summary["suppressions"], 1)
        self.assertIs(summary["sent_here"], False)
        self.assertIs(summary["derived"], True)

    def test_no_content_or_tally_keys_and_no_floats_anywhere(self):
        campaign = self._flow()
        surfaces = [
            self.ext.get_campaign(campaign["id"], ADMIN),
            self.ext.list_suppressions(ADMIN),
            self.ext.list_outreach_attempts(ADMIN),
            self.ext.list_outreach_reports(ADMIN),
            self.ext.campaign_view(campaign["id"], ADMIN),
            self.ext.outreach_summary(ADMIN),
        ]
        for surface in surfaces:
            for key, value in walk_pairs(surface):
                self.assertNotIn(key, FORBIDDEN_KEYS)
                self.assertNotIsInstance(value, float)


class MutantCustsvcExtensionsAddition(CustsvcExtensionsAddition):
    """The suppression seam with the guard removed."""

    def _is_suppressed(self, requester_ref, campaign_id):
        return False


class TestSuppressionNegativeControl(AdditionFixture):
    """The batch's fresh negative control, in-suite leg: the
    canonical seam refuses an attempt to a suppressed requester;
    the mutant (guard removed) records it; treating the mutant's
    outcome as the canonical expectation fails."""

    def test_suppression_guard_is_load_bearing(self):
        campaign = self.make_campaign()
        self.ext.record_suppression(
            self.ref, ADMIN, campaign_id=campaign["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_outreach_attempt(
                campaign["id"], self.ref, AGENT)
        mutant = MutantCustsvcExtensionsAddition(self.store)
        m_campaign = mutant.create_campaign(
            "Mutant drive", "nudge", "email", "case_created", ADMIN)
        mutant.record_suppression(
            self.ref, ADMIN, campaign_id=m_campaign["id"])
        attempt = mutant.record_outreach_attempt(
            m_campaign["id"], self.ref, AGENT)
        self.assertEqual(attempt["requester_ref"], self.ref)
        with self.assertRaises(AssertionError):
            self.assertEqual(
                len(self.ext.list_outreach_attempts(ADMIN)), 1)


class TestCrossCuttingAddition(AdditionFixture):
    """Cross-cutting pins for the addition surface: audit actions,
    denied-attempt auditing, tier role matrix, audit-failure
    rollback, and core isolation."""

    def test_exta_actions_recorded_on_core_audit(self):
        campaign = self.make_campaign()
        self.ext.record_outreach_attempt(campaign["id"], self.ref, AGENT)
        actions = self.audit_actions()
        self.assertIn("exta_campaign_create", actions)
        self.assertIn("exta_outreach_attempt", actions)

    def test_denied_attempt_audited_and_no_state_change(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_campaign(
                "Nope", "campaign", "email", "case_created", VIEWER)
        self.assertIn("exta_campaign_create:denied", self.audit_actions())
        self.assertEqual(self.ext.list_campaigns(ADMIN), [])

    def test_agent_writes_and_viewer_is_read_only(self):
        campaign = self.ext.create_campaign(
            "Agent drive", "nudge", "email", "case_created", AGENT)
        self.assertEqual(
            self.ext.get_campaign(campaign["id"], VIEWER)["id"],
            campaign["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.record_outreach_attempt(
                campaign["id"], self.ref, VIEWER)
        self.assertIn(
            "exta_outreach_attempt:denied", self.audit_actions())

    def test_audit_failure_rolls_back_record_and_id(self):
        original = self.audit.record

        def broken(*args, **kwargs):
            raise RuntimeError("audit unavailable")

        self.audit.record = broken
        try:
            with self.assertRaises(RuntimeError):
                self.make_campaign()
        finally:
            self.audit.record = original
        self.assertEqual(self.ext.list_campaigns(ADMIN), [])
        campaign = self.make_campaign()
        self.assertEqual(campaign["id"], "cmp-1")

    def test_addition_flow_changes_no_core_record(self):
        before = self.core_counts()
        campaign = self.make_campaign()
        attempt = self.ext.record_outreach_attempt(
            campaign["id"], self.ref, AGENT)
        self.ext.record_outreach_report(
            attempt["id"], "reported_opted_out", AGENT)
        self.ext.record_suppression(self.ref, AGENT)
        self.assertEqual(self.core_counts(), before)


if __name__ == "__main__":
    unittest.main()
