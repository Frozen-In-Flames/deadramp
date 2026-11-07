"""Final GAPS batch tests for Collaboration L2 (GAPS.md section
"Group 2 — Collaboration L2 (57 forks)", inventory idx 14-20, 22).

Pins the extension surface in ``collab/extensions.py``: governance
records whose current state and disposition eligibility are derived
at read (idx 19), project/milestone/card-link/dependency records
over core board cards with counts and states only (idx 17),
learning records with verbatim reported outcomes (idx 16),
knowledge-base articles whose stored shape holds exactly {id,
workspace_id, tags, created_by, created_utc} with text in
append-only revisions (idx 20), and the four labeled reference
surfaces -- workflow definitions that never execute (idx 14), AI
assistance and transcription records with no inference/transcription
here (idx 15), voice/telephony session records with no media here
(idx 18), and e-signature envelope/ceremony records with no
signature value anywhere (idx 22).

Fresh negative control: ``TestNegativeControlHoldDerivation``
three-legs the legal-hold current-state derivation
(``_current_hold_label``) -- the canonical latest-label reading
holds, the earliest-label mutant does not produce it, and the
mutant's outcome treated as the expectation fails. See
tests/README.md for the live drill record.
"""

import copy
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from collab.errors import (  # noqa: E402
    NotFoundError, PermissionDenied, ValidationError,
)
from collab.extensions import CollabExtensions  # noqa: E402
from collab_helpers import (  # noqa: E402
    ADMIN, MEMBER, OUTSIDER, OUTSIDER_VIEWER, VIEWER,
    add_sample_card, create_sample_board,
    make_store, share_sample_file,
)

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
ARTICLE_STORED_KEYS = {
    "id", "workspace_id", "tags", "created_by", "created_utc",
}
ENVELOPE_KEYS = {
    "id", "workspace_id", "envelope_ref", "file_id", "reference_stub",
    "signed_here", "created_by", "created_utc",
}
CEREMONY_KEYS = {
    "id", "workspace_id", "envelope_id", "signer_ref", "event_label",
    "reference_stub", "signed_here", "created_by", "created_utc",
}
FORBIDDEN_KEY_PARTS = ("score", "grade", "rating", "percent", "rank")


def assert_no_score_keys(case, obj, path="$"):
    """Recursively assert no score-shaped key exists anywhere."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(
                    part, lowered,
                    "score-shaped key %r under %s" % (key, path))
            assert_no_score_keys(case, value, "%s.%s" % (path, key))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            assert_no_score_keys(case, value, "%s[%d]" % (path, index))


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.ws = make_store()
        self.ext = CollabExtensions(self.store)
        self.file = share_sample_file(self.store, self.ws)
        self.board = create_sample_board(self.store, self.ws, "Delivery")
        self.card1 = add_sample_card(self.store, self.ws,
                                     self.board["id"], "First")
        self.card2 = add_sample_card(self.store, self.ws,
                                     self.board["id"], "Second")

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]


class TestGovernancePolicies(BatchFixture):
    """Idx 19 — retention-policy records."""

    def test_policy_shape(self):
        policy = self.ext.create_governance_policy(
            MEMBER, self.ws, "POL-2026-01", 365)
        self.assertEqual(policy["id"], "gpol-1")
        self.assertEqual(set(policy.keys()), POLICY_KEYS)
        self.assertIs(policy["retention_enforced_here"], False)
        self.assertEqual(policy["retention_days"], 365)

    def test_policy_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_governance_policy(MEMBER, self.ws, "P", -1)
        with self.assertRaises(ValidationError):
            self.ext.create_governance_policy(MEMBER, self.ws, "P", 1.5)
        with self.assertRaises(ValidationError):
            self.ext.create_governance_policy(MEMBER, self.ws, " ", 30)

    def test_policy_id_sequence_after_failure(self):
        with self.assertRaises(ValidationError):
            self.ext.create_governance_policy(MEMBER, self.ws, "P", -1)
        policy = self.ext.create_governance_policy(MEMBER, self.ws, "P", 1)
        self.assertEqual(policy["id"], "gpol-1")


class TestLegalHolds(BatchFixture):
    """Idx 19 — legal-hold records; current state derived at read."""

    def test_hold_requires_real_file(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_legal_hold(MEMBER, self.ws, "H", ["file-99"])
        hold = self.ext.create_legal_hold(MEMBER, self.ws, "H-1",
                                          [self.file["id"]])
        self.assertEqual(hold["id"], "hold-1")
        self.assertEqual(set(hold.keys()), HOLD_KEYS)
        self.assertIs(hold["preserved_here"], False)
        self.assertNotIn("current_state", hold)

    def test_hold_state_derivation(self):
        hold = self.ext.create_legal_hold(MEMBER, self.ws, "H-1",
                                          [self.file["id"]])
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
        with self.assertRaises(ValidationError):
            self.ext.record_hold_state(MEMBER, self.ws, hold["id"],
                                       "litigation_hold")


class TestRetentionDecisions(BatchFixture):
    """Idx 19 — disposition decisions gated on derived eligibility."""

    def _policy_and_hold(self, retention_days=0):
        policy = self.ext.create_governance_policy(
            MEMBER, self.ws, "P", retention_days)
        hold = self.ext.create_legal_hold(MEMBER, self.ws, "H",
                                          [self.file["id"]])
        return policy, hold

    def test_dispose_refused_while_hold_active(self):
        policy, hold = self._policy_and_hold()
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
        self.assertEqual(
            len(self.ext.list_retention_decisions(MEMBER, self.ws)), 0)

    def test_dispose_allowed_after_release_and_core_untouched(self):
        policy, hold = self._policy_and_hold()
        self.ext.record_hold_state(MEMBER, self.ws, hold["id"],
                                   "reported_issued")
        self.ext.record_hold_state(MEMBER, self.ws, hold["id"],
                                   "reported_released")
        before = copy.deepcopy(
            self.store.get_file(self.ws, self.file["id"], MEMBER))
        decision = self.ext.record_retention_decision(
            MEMBER, self.ws, policy["id"], self.file["id"],
            "dispose_reported")
        self.assertEqual(set(decision.keys()), DECISION_KEYS)
        self.assertIs(decision["eligible_at_record"], True)
        self.assertIs(decision["executed_here"], False)
        after = self.store.get_file(self.ws, self.file["id"], MEMBER)
        self.assertEqual(before, after)

    def test_dispose_refused_before_retention_elapses(self):
        policy = self.ext.create_governance_policy(MEMBER, self.ws, "P",
                                                   365)
        soon = "2026-11-03T00:00:00+00:00"
        view = self.ext.governance_view(MEMBER, self.ws, policy["id"],
                                        self.file["id"], now=soon)
        self.assertIs(view["retention_elapsed"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_retention_decision(
                MEMBER, self.ws, policy["id"], self.file["id"],
                "dispose_reported", now=soon)
        later = "2027-12-01T00:00:00+00:00"
        decision = self.ext.record_retention_decision(
            MEMBER, self.ws, policy["id"], self.file["id"],
            "dispose_reported", now=later)
        self.assertIs(decision["eligible_at_record"], True)


class TestProjectsAndCards(BatchFixture):
    """Idx 17 — project records over core boards/cards."""

    def _project_with_cards(self):
        project = self.ext.create_project(MEMBER, self.ws,
                                          self.board["id"], "PRJ-1",
                                          "Delivery plan")
        milestone = self.ext.create_milestone(MEMBER, self.ws,
                                              project["id"], "M1",
                                              "Phase one")
        self.ext.link_card(MEMBER, self.ws, project["id"],
                           milestone["id"], self.card1["id"])
        self.ext.link_card(MEMBER, self.ws, project["id"],
                           milestone["id"], self.card2["id"])
        return project, milestone

    def test_project_view_counts_and_states(self):
        project, _milestone = self._project_with_cards()
        self.ext.record_card_state(MEMBER, self.ws, project["id"],
                                   self.card1["id"], "reported_done")
        view = self.ext.project_view(MEMBER, self.ws, project["id"])
        self.assertEqual(view["milestone_count"], 1)
        self.assertEqual(view["card_count"], 2)
        self.assertEqual(
            view["cards_by_state"]["reported_not_started"], 1)
        self.assertEqual(view["cards_by_state"]["reported_done"], 1)
        self.assertEqual(view["dependency_count"], 0)
        assert_no_score_keys(self, view)

    def test_card_state_requires_link(self):
        project = self.ext.create_project(MEMBER, self.ws,
                                          self.board["id"], "PRJ-1", "P")
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
    """Idx 16 — learning / training / mentoring records."""

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
    """Idx 20 — knowledge management: append-only revision form."""

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
    """Idx 14 — workflow definitions as data; registry never runs."""

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
    """Idx 15 — AI assistance & speech reference records."""

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
    """Idx 18 — voice / telephony reference records."""

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


class TestEnvelopes(BatchFixture):
    """Idx 22 — e-signature reference records."""

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
    """Tier discipline: the viewer is read-only on this surface, the
    outsider is denied at the core membership boundary, and denials
    by role-holding actors are recorded on the core audit log."""

    def test_outsider_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.list_governance_policies(OUTSIDER, self.ws)
        with self.assertRaises(PermissionDenied):
            self.ext.list_governance_policies(OUTSIDER_VIEWER, self.ws)

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

    Traced claim (idx 19, records & governance; control family
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
