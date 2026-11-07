"""Final GAPS batch tests — Group 6, Collaboration L3-adjacent.

Traces to: GAPS.md section "Group 6 — Collaboration L3-adjacent (17
forks)", inventory idx 72-80 (see ``../BATCH.md`` for the per-entry
disposition); gaps-batch/DECISION.md (batch pattern);
PLATFORM-LAYER.md decision 4 (retention enforcement is the
deployment layer's records schedule). Pins the extension surface of
``collab/extensions.py``: governance/hold/decision records with
derived-at-read state, project/milestone records over core board
cards, learning records, the knowledge-base append-only-revision
form, and the five labeled reference implementations
(``reference_stub: True`` throughout). Includes the batch's fresh
negative control: the legal-hold current-state derivation
(``CollabExtensions._current_hold_label``), three-legged in
``TestNegativeControlHoldDerivation`` and mutation-verified live
against the real module (recorded in tests/README.md).
"""

import copy
import unittest

from collab_helpers import (
    ADMIN,
    AUDITOR,
    MEMBER,
    OUTSIDER,
    VIEWER,
    add_sample_card,
    create_sample_board,
    create_sample_event,
    make_store,
    share_sample_file,
)
from collab.errors import NotFoundError, PermissionDenied, ValidationError
from collab.extensions import CollabExtensions

POLICY_KEYS = {
    "id", "workspace_id", "policy_ref", "retention_days",
    "retention_enforced_here", "created_by", "created_utc",
}
HOLD_KEYS = {
    "id", "workspace_id", "hold_ref", "file_ids", "preserved_here",
    "created_by", "created_utc",
}
DECISION_KEYS = {
    "id", "workspace_id", "policy_id", "file_id", "decision_label",
    "eligible_at_record", "executed_here", "created_by", "created_utc",
}
ARTICLE_STORED_KEYS = {"id", "workspace_id", "tags", "created_by",
                       "created_utc"}
ENVELOPE_KEYS = {
    "id", "workspace_id", "envelope_ref", "file_id", "reference_stub",
    "state", "signed_here", "created_by", "created_utc",
}
CEREMONY_KEYS = {
    "id", "workspace_id", "envelope_id", "signer_ref", "ceremony_label",
    "reference_stub", "signed_here", "created_by", "created_utc",
}

FORBIDDEN_KEY_PARTS = ("score", "grade", "rating", "percent", "rank")


def assert_no_score_keys(case, node, path="root"):
    """Recursive scan: no computed-score-shaped key anywhere."""
    if isinstance(node, dict):
        for key, value in node.items():
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(
                    part, str(key).lower(),
                    "forbidden key part %r at %s.%s" % (part, path, key))
            assert_no_score_keys(case, value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            assert_no_score_keys(case, value, "%s[%d]" % (path, index))


class BatchFixture(unittest.TestCase):
    """Canonical fixture: core store + workspace (MEMBER owns, VIEWER
    is a member), one shared file, one board with two cards."""

    def setUp(self):
        self.store, self.ws = make_store()
        self.ext = CollabExtensions(self.store)
        self.file = share_sample_file(self.store, self.ws)
        self.board = create_sample_board(self.store, self.ws)
        self.card1 = add_sample_card(self.store, self.ws, self.board["id"],
                                     text="First card")
        self.card2 = add_sample_card(self.store, self.ws, self.board["id"],
                                     text="Second card", x=30, y=40)

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]


class TestGovernancePolicies(BatchFixture):
    """Idx 74 — records & governance: policy records."""

    def test_policy_shape_and_labels(self):
        policy = self.ext.create_governance_policy(
            MEMBER, self.ws, "POL-1", 365)
        self.assertEqual(policy["id"], "gpol-1")
        self.assertEqual(set(policy.keys()), POLICY_KEYS)
        self.assertEqual(policy["retention_days"], 365)
        self.assertIs(policy["retention_enforced_here"], False)

    def test_retention_days_must_be_a_non_negative_int(self):
        for bad in (-1, 1.5, True, "365"):
            with self.assertRaises(ValidationError):
                self.ext.create_governance_policy(MEMBER, self.ws, "P", bad)
        # failed operations consumed no id
        policy = self.ext.create_governance_policy(MEMBER, self.ws, "P", 0)
        self.assertEqual(policy["id"], "gpol-1")

    def test_policy_scoped_to_workspace(self):
        policy = self.ext.create_governance_policy(MEMBER, self.ws, "P", 1)
        other = self.store.create_workspace("elsewhere", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_governance_policy(MEMBER, other["id"],
                                           policy["id"])


class TestLegalHolds(BatchFixture):
    """Idx 74 — legal holds: current state derived at read."""

    def _hold(self):
        return self.ext.create_legal_hold(MEMBER, self.ws, "HOLD-1",
                                          [self.file["id"]])

    def test_hold_shape_no_stored_state(self):
        hold = self._hold()
        self.assertEqual(hold["id"], "hold-1")
        self.assertEqual(set(hold.keys()), HOLD_KEYS)
        self.assertIs(hold["preserved_here"], False)
        stored = self.ext.get_legal_hold(MEMBER, self.ws, hold["id"])
        self.assertNotIn("current_state", stored)
        self.assertNotIn("active", stored)

    def test_current_state_derived_from_latest(self):
        hold = self._hold()
        view = self.ext.hold_view(MEMBER, self.ws, hold["id"])
        self.assertEqual(view["current_state"], "recorded")
        self.assertIs(view["active"], False)
        self.assertEqual(view["state_record_count"], 0)
        self.ext.record_hold_state(MEMBER, self.ws, hold["id"],
                                   "reported_issued")
        view = self.ext.hold_view(MEMBER, self.ws, hold["id"])
        self.assertEqual(view["current_state"], "reported_issued")
        self.assertIs(view["active"], True)
        self.ext.record_hold_state(MEMBER, self.ws, hold["id"],
                                   "reported_released")
        view = self.ext.hold_view(MEMBER, self.ws, hold["id"])
        self.assertEqual(view["current_state"], "reported_released")
        self.assertIs(view["active"], False)
        self.assertEqual(view["state_record_count"], 2)

    def test_hold_requires_existing_file(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_legal_hold(MEMBER, self.ws, "H", ["file-99"])

    def test_hold_state_label_validated(self):
        hold = self._hold()
        with self.assertRaises(ValidationError):
            self.ext.record_hold_state(MEMBER, self.ws, hold["id"],
                                       "sort_of_issued")


class TestRetentionDecisions(BatchFixture):
    """Idx 74 — disposition decisions gated by the derived state."""

    def test_dispose_refused_before_retention_elapsed(self):
        policy = self.ext.create_governance_policy(MEMBER, self.ws, "P",
                                                   36500)
        view = self.ext.governance_view(MEMBER, self.ws, policy["id"],
                                        self.file["id"])
        self.assertIs(view["retention_elapsed"], False)
        self.assertIs(view["disposition_eligible"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_retention_decision(
                MEMBER, self.ws, policy["id"], self.file["id"],
                "dispose_reported")
        # a retain decision is recordable at any time
        decision = self.ext.record_retention_decision(
            MEMBER, self.ws, policy["id"], self.file["id"],
            "retain_reported")
        self.assertEqual(decision["id"], "rdec-1")
        self.assertEqual(set(decision.keys()), DECISION_KEYS)
        self.assertIs(decision["eligible_at_record"], False)
        self.assertIs(decision["executed_here"], False)

    def test_active_hold_blocks_then_release_opens(self):
        policy = self.ext.create_governance_policy(MEMBER, self.ws, "P", 0)
        hold = self.ext.create_legal_hold(MEMBER, self.ws, "H",
                                          [self.file["id"]])
        self.ext.record_hold_state(MEMBER, self.ws, hold["id"],
                                   "reported_issued")
        view = self.ext.governance_view(MEMBER, self.ws, policy["id"],
                                        self.file["id"])
        self.assertIs(view["retention_elapsed"], True)
        self.assertEqual(view["active_hold_id"], hold["id"])
        self.assertIs(view["disposition_eligible"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_retention_decision(
                MEMBER, self.ws, policy["id"], self.file["id"],
                "dispose_reported")
        self.ext.record_hold_state(MEMBER, self.ws, hold["id"],
                                   "reported_released")
        before = copy.deepcopy(
            self.store.get_file(self.ws, self.file["id"], MEMBER))
        decision = self.ext.record_retention_decision(
            MEMBER, self.ws, policy["id"], self.file["id"],
            "dispose_reported")
        self.assertIs(decision["eligible_at_record"], True)
        after = self.store.get_file(self.ws, self.file["id"], MEMBER)
        self.assertEqual(before, after)  # no core file record changed


class TestProjects(BatchFixture):
    """Idx 76 — task & project management beyond board cards."""

    def _project_with_cards(self):
        project = self.ext.create_project(MEMBER, self.ws,
                                          self.board["id"], "PRJ-1",
                                          "Migration")
        milestone = self.ext.create_milestone(MEMBER, self.ws,
                                              project["id"], "M1",
                                              "Phase one")
        self.ext.link_card(MEMBER, self.ws, project["id"], milestone["id"],
                           self.card1["id"])
        self.ext.link_card(MEMBER, self.ws, project["id"], milestone["id"],
                           self.card2["id"])
        return project, milestone

    def test_view_derives_counts_and_states(self):
        project, milestone = self._project_with_cards()
        view = self.ext.project_view(MEMBER, self.ws, project["id"])
        self.assertEqual(view["card_count"], 2)
        self.assertEqual(view["cards_by_state"]["reported_not_started"], 2)
        cards = view["milestones"][0]["cards"]
        self.assertEqual(cards[0]["current_state"], "reported_not_started")
        self.ext.record_card_state(MEMBER, self.ws, project["id"],
                                   self.card1["id"], "reported_done")
        self.ext.record_card_state(MEMBER, self.ws, project["id"],
                                   self.card2["id"],
                                   "reported_in_progress")
        self.ext.record_card_state(MEMBER, self.ws, project["id"],
                                   self.card2["id"], "reported_done")
        before = copy.deepcopy(self.store.list_cards(
            self.ws, self.board["id"], MEMBER))
        view = self.ext.project_view(MEMBER, self.ws, project["id"])
        self.assertEqual(view["cards_by_state"]["reported_done"], 2)
        self.assertEqual(view["cards_by_state"]["reported_in_progress"], 0)
        after = self.store.list_cards(self.ws, self.board["id"], MEMBER)
        self.assertEqual(before, after)  # core cards untouched
        assert_no_score_keys(self, view)

    def test_state_for_unlinked_card_refused(self):
        project = self.ext.create_project(MEMBER, self.ws,
                                          self.board["id"], "P", "T")
        with self.assertRaises(ValidationError):
            self.ext.record_card_state(MEMBER, self.ws, project["id"],
                                       self.card1["id"], "reported_done")

    def test_dependencies(self):
        project, milestone = self._project_with_cards()
        second = self.ext.create_milestone(MEMBER, self.ws, project["id"],
                                           "M2", "Phase two")
        dep = self.ext.link_dependency(MEMBER, self.ws, project["id"],
                                       second["id"], milestone["id"])
        self.assertEqual(dep["id"], "dep-1")
        with self.assertRaises(ValidationError):
            self.ext.link_dependency(MEMBER, self.ws, project["id"],
                                     milestone["id"], milestone["id"])
        view = self.ext.project_view(MEMBER, self.ws, project["id"])
        self.assertEqual(view["dependency_count"], 1)

    def test_project_requires_existing_board(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_project(MEMBER, self.ws, "bd-99", "P", "T")


class TestLearning(BatchFixture):
    """Idx 77 — learning / training / mentoring records."""

    def test_course_enrollment_completion_flow(self):
        course = self.ext.create_course(MEMBER, self.ws, "SEC-101",
                                        "Security basics", "training")
        self.assertEqual(course["id"], "crs-1")
        enrollment = self.ext.record_enrollment(MEMBER, self.ws,
                                                course["id"],
                                                "learner-ref-7")
        completion = self.ext.record_completion(
            MEMBER, self.ws, enrollment["id"], "reported_completed")
        self.assertIs(completion["assessed_here"], False)
        view = self.ext.course_view(MEMBER, self.ws, course["id"])
        self.assertEqual(view["enrollment_count"], 1)
        self.assertEqual(
            view["completions_by_outcome"]["reported_completed"], 1)
        self.assertEqual(
            view["completions_by_outcome"]["reported_withdrawn"], 0)
        assert_no_score_keys(self, view)

    def test_course_kind_and_outcome_validated(self):
        with self.assertRaises(ValidationError):
            self.ext.create_course(MEMBER, self.ws, "X", "T", "grading")
        course = self.ext.create_course(MEMBER, self.ws, "X", "T",
                                        "mentoring")
        enrollment = self.ext.record_enrollment(MEMBER, self.ws,
                                                course["id"], "ref-1")
        with self.assertRaises(ValidationError):
            self.ext.record_completion(MEMBER, self.ws, enrollment["id"],
                                       "passed")


class TestKnowledgeBase(BatchFixture):
    """Idx 78 — knowledge management: append-only revision form."""

    def test_article_stored_shape_and_derivation(self):
        article = self.ext.create_article(
            MEMBER, self.ws, "Onboarding", "First body", tags=["hr"])
        self.assertEqual(article["id"], "kb-1")
        self.assertEqual(article["title"], "Onboarding")
        self.assertEqual(article["body"], "First body")
        self.assertEqual(article["revision_count"], 1)
        stored = self.ext._articles[article["id"]]
        self.assertEqual(set(stored.keys()), ARTICLE_STORED_KEYS)
        self.assertEqual(stored["tags"], ["hr"])

    def test_revise_appends_and_current_text_is_latest(self):
        article = self.ext.create_article(MEMBER, self.ws, "Guide", "v1")
        revised = self.ext.revise_article(MEMBER, self.ws, article["id"],
                                          "Guide", "v2")
        self.assertEqual(revised["body"], "v2")
        self.assertEqual(revised["revision_count"], 2)
        revisions = self.ext.list_article_revisions(MEMBER, self.ws,
                                                    article["id"])
        self.assertEqual([r["body"] for r in revisions], ["v1", "v2"])

    def test_search_over_current_text(self):
        self.ext.create_article(MEMBER, self.ws, "Travel policy",
                                "Book flights early")
        self.ext.create_article(MEMBER, self.ws, "VPN help",
                                "Reset the tunnel")
        hits = self.ext.search_articles(MEMBER, self.ws, "FLIGHTS")
        self.assertEqual([h["title"] for h in hits], ["Travel policy"])


class TestWorkflowDefinitions(BatchFixture):
    """Idx 72 — workflow definitions as data; registry never runs."""

    def test_definition_shape_and_labels(self):
        definition = self.ext.register_workflow_definition(
            MEMBER, self.ws, "WF-1", ["intake", "review", "close"])
        self.assertEqual(definition["id"], "wfd-1")
        self.assertIs(definition["reference_stub"], True)
        self.assertEqual(definition["state"], "recorded_reference_only")
        self.assertIs(definition["executed_here"], False)
        self.assertEqual(definition["steps"],
                         ["intake", "review", "close"])

    def test_registering_changes_no_core_record(self):
        before_file = copy.deepcopy(
            self.store.get_file(self.ws, self.file["id"], MEMBER))
        before_cards = copy.deepcopy(
            self.store.list_cards(self.ws, self.board["id"], MEMBER))
        before_ws = copy.deepcopy(self.store.get_workspace(self.ws, MEMBER))
        self.ext.register_workflow_definition(MEMBER, self.ws, "WF-1",
                                              ["a", "b"])
        self.assertEqual(before_file,
                         self.store.get_file(self.ws, self.file["id"],
                                             MEMBER))
        self.assertEqual(before_cards,
                         self.store.list_cards(self.ws, self.board["id"],
                                               MEMBER))
        self.assertEqual(before_ws,
                         self.store.get_workspace(self.ws, MEMBER))

    def test_empty_steps_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.register_workflow_definition(MEMBER, self.ws, "WF",
                                                  [])


class TestAiAssistance(BatchFixture):
    """Idx 73 — AI assistance & speech reference records."""

    def test_assistant_and_output_shapes(self):
        assistant = self.ext.register_assistant(MEMBER, self.ws, "A-1",
                                                "assistance")
        self.assertIs(assistant["reference_stub"], True)
        self.assertIs(assistant["inference_here"], False)
        output = self.ext.record_ai_output(MEMBER, self.ws,
                                           assistant["id"],
                                           "ext-output-42",
                                           target_ref=self.file["id"])
        self.assertEqual(output["output_ref"], "ext-output-42")
        self.assertIs(output["inference_here"], False)

    def test_no_output_text_can_be_smuggled(self):
        assistant = self.ext.register_assistant(MEMBER, self.ws, "A-1",
                                                "assistance")
        with self.assertRaises(TypeError):
            self.ext.record_ai_output(MEMBER, self.ws, assistant["id"],
                                      "ref", output_text="smuggled")

    def test_transcription_job_and_outcome(self):
        assistant = self.ext.register_assistant(MEMBER, self.ws, "S-1",
                                                "speech")
        job = self.ext.record_transcription_job(MEMBER, self.ws,
                                                assistant["id"], "JOB-1",
                                                "media-ref-9")
        self.assertIs(job["transcribed_here"], False)
        outcome = self.ext.record_transcription_outcome(
            MEMBER, self.ws, job["id"], "reported_completed",
            "transcript-ref-3")
        self.assertEqual(outcome["result_ref"], "transcript-ref-3")
        self.assertIs(outcome["transcribed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_transcription_outcome(
                MEMBER, self.ws, job["id"], "done-ish", "ref")


class TestVoiceChannels(BatchFixture):
    """Idx 75 — voice / telephony reference records."""

    def test_channel_and_session_shapes(self):
        channel = self.ext.register_voice_channel(MEMBER, self.ws,
                                                  "PBX-1", "telephony")
        self.assertIs(channel["reference_stub"], True)
        self.assertIs(channel["connected_here"], False)
        self.assertIs(channel["media_here"], False)
        session = self.ext.record_call_session(
            MEMBER, self.ws, channel["id"], "CALL-7",
            ["agent-ref-1", "caller-ref-2"])
        self.assertEqual(session["participant_refs"],
                         ["agent-ref-1", "caller-ref-2"])
        self.assertIs(session["media_here"], False)

    def test_session_requires_participants(self):
        channel = self.ext.register_voice_channel(MEMBER, self.ws, "V",
                                                  "voice")
        with self.assertRaises(ValidationError):
            self.ext.record_call_session(MEMBER, self.ws, channel["id"],
                                         "C-1", [])


class TestMeetingSessions(BatchFixture):
    """Idx 79 — meetings / video session records."""

    def test_session_linked_to_core_event(self):
        event = create_sample_event(self.store, self.ws)
        session = self.ext.register_meeting_session(
            MEMBER, self.ws, "MTG-1", event_id=event["id"])
        self.assertEqual(session["event_id"], event["id"])
        self.assertIs(session["media_here"], False)
        report = self.ext.record_meeting_report(
            MEMBER, self.ws, session["id"], "reported_held",
            recording_ref="rec-ref-1")
        self.assertEqual(report["recording_ref"], "rec-ref-1")
        self.assertIs(report["media_here"], False)

    def test_unknown_event_refused(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_meeting_session(MEMBER, self.ws, "M",
                                              event_id="evt-99")


class TestEnvelopes(BatchFixture):
    """Idx 80 — e-signature reference records."""

    def test_envelope_and_ceremony_key_sets(self):
        envelope = self.ext.record_envelope(MEMBER, self.ws, "ENV-1",
                                            file_id=self.file["id"])
        self.assertEqual(set(envelope.keys()), ENVELOPE_KEYS)
        self.assertIs(envelope["signed_here"], False)
        self.assertIs(envelope["reference_stub"], True)
        event = self.ext.record_ceremony_event(
            MEMBER, self.ws, envelope["id"], "signer-ref-1",
            "reported_signed")
        self.assertEqual(set(event.keys()), CEREMONY_KEYS)
        self.assertIs(event["signed_here"], False)

    def test_no_signature_value_can_be_smuggled(self):
        with self.assertRaises(TypeError):
            self.ext.record_envelope(MEMBER, self.ws, "ENV-1",
                                     signature="smuggled")
        envelope = self.ext.record_envelope(MEMBER, self.ws, "ENV-1")
        with self.assertRaises(TypeError):
            self.ext.record_ceremony_event(
                MEMBER, self.ws, envelope["id"], "s-1", "reported_sent",
                signature="smuggled")


class TestAccessDiscipline(BatchFixture):
    """Tier discipline: the auditor holds no extension permission;
    the viewer is read-only; denials are audited."""

    def test_auditor_denied_read_and_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.list_governance_policies(AUDITOR, self.ws)
        with self.assertRaises(PermissionDenied):
            self.ext.create_governance_policy(AUDITOR, self.ws, "P", 1)
        with self.assertRaises(PermissionDenied):
            self.ext.list_articles(AUDITOR, self.ws)

    def test_outsider_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.list_governance_policies(OUTSIDER, self.ws)

    def test_viewer_reads_but_write_is_denied_and_audited(self):
        self.ext.create_governance_policy(MEMBER, self.ws, "P", 30)
        self.assertEqual(
            len(self.ext.list_governance_policies(VIEWER, self.ws)), 1)
        with self.assertRaises(PermissionDenied):
            self.ext.create_governance_policy(VIEWER, self.ws, "P2", 30)
        self.assertIn("ext_governance_policy_create:denied",
                      self.audit_actions())

    def test_admin_may_write(self):
        policy = self.ext.create_governance_policy(ADMIN, self.ws, "P", 1)
        self.assertEqual(policy["created_by"], "alice")

    def test_extension_mutations_are_audited(self):
        self.ext.create_governance_policy(MEMBER, self.ws, "P", 1)
        self.assertIn("ext_governance_policy_create", self.audit_actions())
        ok, first_bad = self.store.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)


class _EarliestHoldExtensions(CollabExtensions):
    """Mutant: the hold derivation reads the earliest recorded label
    instead of the latest, so a released hold still reads active."""

    @staticmethod
    def _current_hold_label(states):
        if not states:
            return "recorded"
        return states[0]["state_label"]


class TestNegativeControlHoldDerivation(BatchFixture):
    """Fresh negative control: the legal-hold current-state
    derivation (``_current_hold_label``).

    Traced claim (idx 74, records & governance; control family
    AU-11 / PLATFORM-LAYER.md decision 4): a hold's current state
    is the LATEST recorded label, so once a release is recorded the
    hold no longer blocks disposition. Three legs: the canonical
    expectation holds on the real implementation, the mutant
    (earliest-label) does NOT produce it, and treating the mutant's
    outcome as the expectation fails.
    """

    def _released_hold(self, ext):
        policy = ext.create_governance_policy(MEMBER, self.ws, "P", 0)
        hold = ext.create_legal_hold(MEMBER, self.ws, "H",
                                     [self.file["id"]])
        ext.record_hold_state(MEMBER, self.ws, hold["id"],
                              "reported_issued")
        ext.record_hold_state(MEMBER, self.ws, hold["id"],
                              "reported_released")
        return policy, hold

    def test_canonical_latest_label_wins(self):
        policy, hold = self._released_hold(self.ext)
        view = self.ext.hold_view(MEMBER, self.ws, hold["id"])
        self.assertEqual(view["current_state"], "reported_released")
        self.assertIs(view["active"], False)
        decision = self.ext.record_retention_decision(
            MEMBER, self.ws, policy["id"], self.file["id"],
            "dispose_reported")
        self.assertIs(decision["eligible_at_record"], True)

    def test_mutant_earliest_label_does_not(self):
        mutant = _EarliestHoldExtensions(self.store)
        policy, hold = self._released_hold(mutant)
        view = mutant.hold_view(MEMBER, self.ws, hold["id"])
        self.assertEqual(view["current_state"], "reported_issued")
        self.assertIs(view["active"], True)
        with self.assertRaises(ValidationError):
            mutant.record_retention_decision(
                MEMBER, self.ws, policy["id"], self.file["id"],
                "dispose_reported")

    def test_mutant_outcome_as_expectation_fails(self):
        mutant = _EarliestHoldExtensions(self.store)
        _policy, hold = self._released_hold(mutant)
        view = mutant.hold_view(MEMBER, self.ws, hold["id"])
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_state"], "reported_released")
        with self.assertRaises(AssertionError):
            self.assertIs(view["active"], False)


if __name__ == "__main__":
    unittest.main()
