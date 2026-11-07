"""Final GAPS batch tests — Group 10, Collaboration L1.

Pins the extension surface in ``collab/extensions.py`` per GAPS.md
entry (idx 104–112 in ``../../gaps-batch/inventory.json``; see
``../BATCH.md``): the four build-extension families (learning,
knowledge management, task/project depth, records & governance)
and the five labeled reference families (AI assistance / speech /
analytics, workflow definitions, voice / telephony, meeting
sessions, e-signature), plus the batch's fresh mutation-verified
negative control over the disposition-eligibility seam.
"""

import os
import sys
from datetime import datetime, timedelta

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

import unittest  # noqa: E402

from collab.audit import AuditLog  # noqa: E402
from collab.errors import (  # noqa: E402
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from collab.extensions import CollabExtensions  # noqa: E402
from collab_helpers import (  # noqa: E402
    ADMIN,
    MEMBER,
    OUTSIDER,
    VIEWER,
    add_sample_card,
    create_sample_board,
    create_sample_event,
    make_channel,
    make_store,
    post_sample_message,
    share_sample_file,
)


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.audit = AuditLog()
        self.store, self.ws = make_store(audit=self.audit)
        self.ext = CollabExtensions(self.store)

    def audit_actions(self):
        return [entry["action"] for entry in self.audit.entries()]


class TestLearning(BatchFixture):
    """Idx 106 — learning / training / mentoring (built)."""

    def test_course_shape_and_ids(self):
        course = self.ext.create_course(self.ws, "Onboarding", MEMBER)
        self.assertEqual(course["id"], "crs-1")
        self.assertEqual(
            set(course.keys()),
            {"id", "workspace_id", "title", "created_by", "created_utc"},
        )
        self.assertIn("ext_course_create", self.audit_actions())

    def test_enroll_and_complete_flow(self):
        course = self.ext.create_course(self.ws, "Onboarding", MEMBER)
        enrollment = self.ext.enroll_learner(
            self.ws, course["id"], VIEWER.name, MEMBER)
        self.assertEqual(enrollment["id"], "enr-1")
        completion = self.ext.record_completion(
            self.ws, enrollment["id"], "completed", MEMBER)
        self.assertEqual(completion["id"], "cmp-1")
        self.assertEqual(completion["outcome"], "completed")
        self.assertIs(completion["assessed_here"], False)
        view = self.ext.course_view(self.ws, course["id"], MEMBER)
        self.assertEqual(view["enrollment_count"], 1)
        self.assertEqual(view["completion_count"], 1)
        stored = self.ext.get_course(self.ws, course["id"], MEMBER)
        self.assertNotIn("enrollment_count", stored)

    def test_enroll_non_member_refused(self):
        course = self.ext.create_course(self.ws, "Onboarding", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.enroll_learner(self.ws, course["id"], "mallory", MEMBER)
        self.assertEqual(self.ext.list_enrollments(self.ws, MEMBER), [])

    def test_duplicate_enrollment_refused(self):
        course = self.ext.create_course(self.ws, "Onboarding", MEMBER)
        self.ext.enroll_learner(self.ws, course["id"], VIEWER.name, MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.enroll_learner(self.ws, course["id"], VIEWER.name, MEMBER)

    def test_viewer_may_read_but_not_create(self):
        course = self.ext.create_course(self.ws, "Onboarding", MEMBER)
        self.assertEqual(
            self.ext.get_course(self.ws, course["id"], VIEWER)["id"],
            course["id"],
        )
        with self.assertRaises(PermissionDenied):
            self.ext.create_course(self.ws, "Nope", VIEWER)

    def test_outsider_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_course(self.ws, "Nope", OUTSIDER)
        self.assertIn("ext_course_create:denied", self.audit_actions())
        self.assertEqual(self.ext.list_courses(self.ws, MEMBER), [])


class TestKnowledgeManagement(BatchFixture):
    """Idx 107 — knowledge management (built), the KB form."""

    def test_stored_article_shape_holds_no_text(self):
        article = self.ext.create_article(
            self.ws, "Runbook", "first body", MEMBER, tags=["ops"])
        stored = self.ext._articles[article["id"]]
        self.assertEqual(
            set(stored.keys()),
            {"id", "workspace_id", "tags", "created_by", "created_utc"},
        )
        self.assertEqual(stored["tags"], ["ops"])

    def test_current_text_derived_from_latest_revision(self):
        article = self.ext.create_article(self.ws, "Runbook", "v1", MEMBER)
        self.ext.revise_article(self.ws, article["id"], "Runbook 2", "v2",
                                 MEMBER)
        view = self.ext.get_article(self.ws, article["id"], MEMBER)
        self.assertEqual(view["title"], "Runbook 2")
        self.assertEqual(view["body"], "v2")
        self.assertEqual(view["revision_count"], 2)
        revisions = self.ext.list_article_revisions(
            self.ws, article["id"], MEMBER)
        self.assertEqual([r["body"] for r in revisions], ["v1", "v2"])
        self.assertEqual([r["revision"] for r in revisions], [1, 2])

    def test_search_articles_matches_current_text_only(self):
        article = self.ext.create_article(self.ws, "Guide", "alpha", MEMBER)
        self.ext.revise_article(self.ws, article["id"], "Guide", "beta",
                                 MEMBER)
        self.assertEqual(self.ext.search_articles(self.ws, "alpha", MEMBER),
                         [])
        hits = self.ext.search_articles(self.ws, "BETA", MEMBER)
        self.assertEqual([hit["id"] for hit in hits], [article["id"]])

    def test_revise_unknown_article(self):
        with self.assertRaises(NotFoundError):
            self.ext.revise_article(self.ws, "kb-99", "T", "B", MEMBER)


class TestTaskProjectDepth(BatchFixture):
    """Idx 109 — task & project management beyond board cards (built)."""

    def setUp(self):
        super().setUp()
        self.board = create_sample_board(self.store, self.ws)
        self.card_a = add_sample_card(self.store, self.ws, self.board["id"],
                                      text="Card A")
        self.card_b = add_sample_card(self.store, self.ws, self.board["id"],
                                      text="Card B")
        self.milestone = self.ext.create_milestone(
            self.ws, self.board["id"], "Launch", MEMBER)

    def test_milestone_over_unknown_board(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_milestone(self.ws, "bd-99", "Nope", MEMBER)

    def test_link_and_state_counts_derived(self):
        self.ext.link_card_to_milestone(
            self.ws, self.milestone["id"], self.card_a["id"], MEMBER)
        self.ext.link_card_to_milestone(
            self.ws, self.milestone["id"], self.card_b["id"], MEMBER)
        self.ext.record_card_state(
            self.ws, self.milestone["id"], self.card_a["id"], "done", MEMBER)
        self.ext.record_card_state(
            self.ws, self.milestone["id"], self.card_b["id"],
            "in progress", MEMBER)
        self.ext.record_card_state(
            self.ws, self.milestone["id"], self.card_b["id"], "done",
            MEMBER)
        view = self.ext.milestone_view(self.ws, self.milestone["id"], MEMBER)
        self.assertEqual(view["linked_card_count"], 2)
        self.assertEqual(view["state_counts"], {"done": 2})
        self.assertEqual(view["cards_with_state"], 2)
        self.assertEqual(view["cards_without_state"], 0)
        for banned in ("score", "percent", "percentage", "progress"):
            self.assertNotIn(banned, view)
        stored = self.ext.get_milestone(self.ws, self.milestone["id"], MEMBER)
        self.assertNotIn("state_counts", stored)

    def test_state_for_unlinked_card_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.record_card_state(
                self.ws, self.milestone["id"], self.card_a["id"], "done",
                MEMBER)
        view = self.ext.milestone_view(self.ws, self.milestone["id"], MEMBER)
        self.assertEqual(view["cards_with_state"], 0)

    def test_duplicate_link_refused(self):
        self.ext.link_card_to_milestone(
            self.ws, self.milestone["id"], self.card_a["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.link_card_to_milestone(
                self.ws, self.milestone["id"], self.card_a["id"], MEMBER)

    def test_card_state_record_changes_no_core_card(self):
        self.ext.link_card_to_milestone(
            self.ws, self.milestone["id"], self.card_a["id"], MEMBER)
        before = self.store.list_cards(self.ws, self.board["id"], MEMBER)
        self.ext.record_card_state(
            self.ws, self.milestone["id"], self.card_a["id"], "done", MEMBER)
        after = self.store.list_cards(self.ws, self.board["id"], MEMBER)
        self.assertEqual(before, after)


class TestGovernance(BatchFixture):
    """Idx 110 — records & governance beyond the seed (built)."""

    def setUp(self):
        super().setUp()
        self.file = share_sample_file(self.store, self.ws)

    def test_policy_validation(self):
        for bad in (-1, 1.5, True, "30"):
            with self.assertRaises(ValidationError):
                self.ext.create_retention_policy(self.ws, "P", bad, ADMIN)
        policy = self.ext.create_retention_policy(self.ws, "P", 0, ADMIN)
        self.assertEqual(policy["id"], "pol-1")

    def test_policy_create_requires_admin_action(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_retention_policy(self.ws, "P", 0, MEMBER)

    def test_hold_and_release_currency_derived(self):
        hold = self.ext.place_hold(self.ws, self.file["id"], "litigation",
                                   ADMIN)
        self.assertIs(hold["executed_here"], False)
        view = self.ext.hold_view(self.ws, hold["id"], MEMBER)
        self.assertIs(view["active"], True)
        stored = self.ext._holds[hold["id"]]
        self.assertNotIn("active", stored)
        self.ext.release_hold(self.ws, hold["id"], ADMIN)
        view = self.ext.hold_view(self.ws, hold["id"], MEMBER)
        self.assertIs(view["active"], False)
        with self.assertRaises(ValidationError):
            self.ext.release_hold(self.ws, hold["id"], ADMIN)

    def test_hold_changes_no_core_file(self):
        before = self.store.get_file(self.ws, self.file["id"], MEMBER)
        self.ext.place_hold(self.ws, self.file["id"], "litigation", ADMIN)
        after = self.store.get_file(self.ws, self.file["id"], MEMBER)
        self.assertEqual(before, after)

    def test_eligibility_derivation(self):
        policy = self.ext.create_retention_policy(self.ws, "Zero", 0, ADMIN)
        view = self.ext.disposition_eligibility(
            self.ws, self.file["id"], policy["id"], MEMBER)
        self.assertIs(view["retention_met"], True)
        self.assertIs(view["eligible"], True)
        self.assertEqual(view["active_hold_ids"], [])
        long_policy = self.ext.create_retention_policy(
            self.ws, "Century", 36500, ADMIN)
        view = self.ext.disposition_eligibility(
            self.ws, self.file["id"], long_policy["id"], MEMBER)
        self.assertIs(view["retention_met"], False)
        self.assertIs(view["eligible"], False)
        future = (
            datetime.fromisoformat(self.file["created_utc"])
            + timedelta(days=36501)
        ).isoformat()
        view = self.ext.disposition_eligibility(
            self.ws, self.file["id"], long_policy["id"], MEMBER, at=future)
        self.assertIs(view["eligible"], True)

    def test_disposition_decision_recorded_when_eligible(self):
        policy = self.ext.create_retention_policy(self.ws, "Zero", 0, ADMIN)
        before = self.store.get_file(self.ws, self.file["id"], MEMBER)
        decision = self.ext.record_disposition_decision(
            self.ws, self.file["id"], policy["id"], ADMIN)
        self.assertEqual(decision["id"], "dsp-1")
        self.assertIs(decision["executed_here"], False)
        after = self.store.get_file(self.ws, self.file["id"], MEMBER)
        self.assertEqual(before, after)


class TestDispositionEligibilityNegativeControl(BatchFixture):
    """Fresh negative control for the batch: the disposition
    eligibility seam ``_disposition_eligible`` in
    ``collab/extensions.py``.

    Traced claim: **a disposition decision may be recorded only
    when the file's recorded retention period has run AND no hold
    is active over it** — the gate that keeps the records layer
    from blessing a disposition the operator's own schedule and
    holds forbid. Each canonical case asserts (1) the real
    implementation refuses and stores nothing, (2) the mutant gate
    (always eligible) would NOT refuse, and (3) treating the
    mutant's outcome as the expectation fails.
    """

    def _setup_file_and_policy(self, retention_days=0):
        file_record = share_sample_file(self.store, self.ws)
        policy = self.ext.create_retention_policy(
            self.ws, "P", retention_days, ADMIN)
        return file_record, policy

    def _mutant(self):
        """A MutantExtensions sharing the canonical instance's
        tables, so only the eligibility seam differs."""
        mutant = MutantExtensions(self.store)
        for name, value in vars(self.ext).items():
            if isinstance(value, dict):
                setattr(mutant, name, value)
        return mutant

    def test_held_file_refused_canonically_but_mutant_allows(self):
        file_record, policy = self._setup_file_and_policy()
        self.ext.place_hold(self.ws, file_record["id"], "litigation", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_decision(
                self.ws, file_record["id"], policy["id"], ADMIN)
        self.assertEqual(
            self.ext.list_disposition_decisions(self.ws, MEMBER), [])
        mutant = self._mutant()
        decision = mutant.record_disposition_decision(
            self.ws, file_record["id"], policy["id"], ADMIN)
        self.assertEqual(decision["file_id"], file_record["id"])
        with self.assertRaises(AssertionError):
            with self.assertRaises(ValidationError):
                mutant.record_disposition_decision(
                    self.ws, file_record["id"], policy["id"], ADMIN)

    def test_within_retention_refused_canonically_but_mutant_allows(self):
        file_record, policy = self._setup_file_and_policy(
            retention_days=36500)
        view = self.ext.disposition_eligibility(
            self.ws, file_record["id"], policy["id"], MEMBER)
        self.assertIs(view["eligible"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_disposition_decision(
                self.ws, file_record["id"], policy["id"], ADMIN)
        mutant = self._mutant()
        outcome = mutant.disposition_eligibility(
            self.ws, file_record["id"], policy["id"], MEMBER)
        self.assertIs(outcome["eligible"], True)
        with self.assertRaises(AssertionError):
            self.assertIs(outcome["eligible"], False)


class MutantExtensions(CollabExtensions):
    """The negative control's mutant: every file is eligible."""

    def _disposition_eligible(self, file_record, policy, holds_active,
                              at_dt):
        return True


class TestAiSpeechAnalytics(BatchFixture):
    """Idx 104 — AI assistance / speech / analytics (reference)."""

    def test_assistant_record_is_labeled_reference(self):
        assistant = self.ext.register_assistant(self.ws, "Helper", MEMBER)
        self.assertIs(assistant["reference_stub"], True)
        self.assertIs(assistant["inference_here"], False)
        self.assertEqual(assistant["method"], "recorded_declaration_only")

    def test_assistant_report_leaves_core_message_untouched(self):
        channel = make_channel(self.store, self.ws)
        message = post_sample_message(self.store, self.ws, channel["id"])
        assistant = self.ext.register_assistant(self.ws, "Helper", MEMBER)
        before = self.store.get_message(self.ws, message["id"], MEMBER)
        report = self.ext.record_assistant_report(
            self.ws, assistant["id"], "suggested a reply", MEMBER,
            message_id=message["id"])
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["decided_here"], False)
        after = self.store.get_message(self.ws, message["id"], MEMBER)
        self.assertEqual(before, after)

    def test_transcription_report_shape_holds_no_transcript(self):
        job = self.ext.register_transcription_job(
            self.ws, "audio-ref-1", MEMBER)
        self.assertIs(job["transcribed_here"], False)
        report = self.ext.record_transcription_report(
            self.ws, job["id"], "completed", MEMBER,
            result_ref="transcript-ref-1")
        self.assertEqual(
            set(report.keys()),
            {"id", "workspace_id", "job_id", "outcome", "result_ref",
             "reference_stub", "transcribed_here", "recorded_by",
             "created_utc"},
        )
        self.assertIs(report["transcribed_here"], False)

    def test_analytics_are_deterministic_counts_derived_at_read(self):
        channel = make_channel(self.store, self.ws)
        post_sample_message(self.store, self.ws, channel["id"])
        first = self.ext.workspace_analytics(self.ws, MEMBER)
        self.assertEqual(first["messages"], 1)
        self.assertEqual(first["members"], 2)
        self.assertEqual(
            first["method"], "deterministic_counts_over_core_records")
        post_sample_message(self.store, self.ws, channel["id"],
                            text="second")
        second = self.ext.workspace_analytics(self.ws, MEMBER)
        self.assertEqual(second["messages"], 2)


class TestWorkflowDefinitions(BatchFixture):
    """Idx 105 — workflow / process automation (reference)."""

    def test_definition_held_as_data_and_never_runs(self):
        channel = make_channel(self.store, self.ws)
        message = post_sample_message(self.store, self.ws, channel["id"])
        before_ws = self.store.get_workspace(self.ws, MEMBER)
        before_msgs = self.store.list_messages(self.ws, channel["id"],
                                               MEMBER)
        definition = self.ext.register_workflow_definition(
            self.ws, "Onboarding flow", ["invite", "intro", "review"],
            MEMBER)
        self.assertIs(definition["reference_stub"], True)
        self.assertIs(definition["executed_here"], False)
        self.assertEqual(definition["state"], "recorded_reference_only")
        self.assertEqual(definition["steps"], ["invite", "intro", "review"])
        after_ws = self.store.get_workspace(self.ws, MEMBER)
        after_msgs = self.store.list_messages(self.ws, channel["id"],
                                              MEMBER)
        self.assertEqual(before_ws, after_ws)
        self.assertEqual(before_msgs, after_msgs)
        self.assertEqual(after_msgs[0]["id"], message["id"])

    def test_definition_validation(self):
        for bad in ([], ["ok", ""], "not-a-list"):
            with self.assertRaises(ValidationError):
                self.ext.register_workflow_definition(
                    self.ws, "Bad", bad, MEMBER)
        self.assertEqual(
            self.ext.list_workflow_definitions(self.ws, MEMBER), [])


class TestVoiceTelephony(BatchFixture):
    """Idx 108 — voice / telephony / contact center (reference)."""

    def test_channel_and_session_records(self):
        channel = self.ext.register_voice_channel(self.ws, "Support line",
                                                  MEMBER)
        self.assertIs(channel["reference_stub"], True)
        self.assertIs(channel["connected_here"], False)
        self.assertIs(channel["media_here"], False)
        session = self.ext.record_voice_session(
            self.ws, channel["id"], "reported_completed", MEMBER)
        self.assertIs(session["reference_stub"], True)
        self.assertIs(session["media_here"], False)
        self.assertEqual(session["outcome"], "reported_completed")

    def test_session_on_unknown_channel(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_voice_session(self.ws, "vch-99", "x", MEMBER)


class TestMeetingSessions(BatchFixture):
    """Idx 111 — meetings / video media transport (reference)."""

    def test_session_record_is_coordination_only(self):
        event = create_sample_event(self.store, self.ws)
        session = self.ext.record_meeting_session(
            self.ws, "Team sync (video)", MEMBER, event_id=event["id"])
        self.assertIs(session["reference_stub"], True)
        self.assertIs(session["media_here"], False)
        self.assertEqual(session["event_id"], event["id"])

    def test_session_with_unknown_event(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_meeting_session(
                self.ws, "Nope", MEMBER, event_id="evt-99")


class TestESignature(BatchFixture):
    """Idx 112 — e-signature (reference), the house envelope form."""

    def setUp(self):
        super().setUp()
        self.file = share_sample_file(self.store, self.ws)

    def test_envelope_shape_can_hold_no_signature(self):
        envelope = self.ext.create_envelope(self.ws, self.file["id"], MEMBER)
        self.assertEqual(
            set(envelope.keys()),
            {"id", "workspace_id", "file_id", "reference_stub", "state",
             "signed_here", "created_by", "created_utc"},
        )
        self.assertIs(envelope["reference_stub"], True)
        self.assertIs(envelope["signed_here"], False)
        self.assertEqual(envelope["state"], "recorded_reference_only")

    def test_ceremony_event_recorded_verbatim(self):
        envelope = self.ext.create_envelope(self.ws, self.file["id"], MEMBER)
        event = self.ext.record_ceremony_event(
            self.ws, envelope["id"], VIEWER.name, "reported_signed", MEMBER)
        self.assertEqual(event["event"], "reported_signed")
        self.assertIs(event["signed_here"], False)
        self.assertEqual(
            [e["id"] for e in self.ext.list_ceremony_events(
                self.ws, MEMBER, envelope_id=envelope["id"])],
            [event["id"]],
        )

    def test_ceremony_signer_must_be_member(self):
        envelope = self.ext.create_envelope(self.ws, self.file["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_ceremony_event(
                self.ws, envelope["id"], "mallory", "reported_signed",
                MEMBER)

    def test_envelope_over_unknown_file(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_envelope(self.ws, "file-99", MEMBER)


class BoomAudit:
    """An audit sink that always fails, for the rollback pin."""

    def record(self, actor, action, target, details=None):
        raise RuntimeError("audit unavailable")

    def entries(self):
        return []


class TestAuditRollback(BatchFixture):
    """Cross-cutting: if the audit write fails, the record insertion
    and its id roll back — no extension record exists whose audit
    entry does not."""

    def test_failed_audit_rolls_back_record_and_id(self):
        self.store.audit = BoomAudit()
        with self.assertRaises(RuntimeError):
            self.ext.create_course(self.ws, "Onboarding", MEMBER)
        self.store.audit = self.audit
        self.assertEqual(self.ext.list_courses(self.ws, MEMBER), [])
        course = self.ext.create_course(self.ws, "Onboarding", MEMBER)
        self.assertEqual(course["id"], "crs-1")


if __name__ == "__main__":
    unittest.main()
