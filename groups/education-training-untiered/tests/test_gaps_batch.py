"""Final GAPS batch tests — Untiered Set 8, Education & Training.

Pins the extension surface in ``src/learn/extensions.py``
(``LearnExtensions``, wrapping the core ``LearnStore``): one test
class per open GAPS.md entry for this set (see ``../BATCH.md`` for
the per-entry disposition), plus cross-cutting pins — the founding
**no-score invariant over the WHOLE extension surface** (recursive
key scan: no key named like a score or grade anywhere), tier-null
discipline (no tier/baseline key anywhere either), stub/transport
labels, derived-never-stored values, learner scope, RBAC denials
(including the audited ``:denied`` record), and no-id-consumed on
failed operations.

Traces to: the 16 open entries of this set's section in the
repo-root GAPS.md and to ``../../gaps-batch/DECISION.md``. The set
is untiered: nothing here asserts a baseline or a tier, and the
tests pin that the extension surface does not either.

Fixtures: ``make_store()`` (one course, "Safety Basics") plus the
demo users from ``learn_helpers``. Learner-scoped records for the
LEARNER actor use learner_id "carol" (the actor's own name).
"""

import unittest

from learn_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_store

from learn.errors import NotFoundError, PermissionDenied, ValidationError
from learn.extensions import LearnExtensions


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(str(key))
            keys |= _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            keys |= _all_keys(value)
    return keys


def _banned_keys(obj):
    """Keys that would break the founding invariants.

    No score/grade key (the founding scoring doctrine), and no
    tier/baseline key (this set is untiered).
    """
    bad = set()
    for key in _all_keys(obj):
        lowered = key.lower()
        if (lowered == "score" or lowered.startswith("score_")
                or lowered.endswith("_score") or "grade" in lowered
                or lowered in ("tier", "cmmc_tier", "baseline")
                or lowered.endswith("_tier")):
            bad.add(key)
    return bad


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.course = make_store()
        self.ext = LearnExtensions(self.store)
        self.cid = self.course["id"]


class TestPhishingSimulation(BatchFixture):
    """Entry: Phishing simulation & security-awareness engines — built
    as campaign + reported-outcome records; nothing is sent."""

    def test_campaign_record_shape_and_no_execution(self):
        campaign = self.ext.create_phishing_campaign(
            "Q3 simulation", self.cid, INSTRUCTOR,
            learner_ids=["carol", "erin"], template_ref="tmpl-1")
        self.assertEqual(campaign["id"], "psc-1")
        self.assertIs(campaign["executed_here"], False)
        self.assertEqual(campaign["learner_ids"], ["carol", "erin"])

    def test_outcome_counts_derived_at_read(self):
        campaign = self.ext.create_phishing_campaign(
            "Q3 simulation", self.cid, INSTRUCTOR, learner_ids=["carol"])
        self.ext.record_phishing_outcome(
            campaign["id"], "carol", "reported_message", INSTRUCTOR)
        view = self.ext.get_phishing_campaign(campaign["id"], ADMIN)
        self.assertEqual(view["outcome_counts"], {"reported_message": 1})
        self.assertEqual(view["learners_with_outcomes"], 1)

    def test_outcome_for_untargeted_learner_rejected_no_id_consumed(self):
        campaign = self.ext.create_phishing_campaign(
            "Q3 simulation", self.cid, INSTRUCTOR, learner_ids=["carol"])
        with self.assertRaises(ValidationError):
            self.ext.record_phishing_outcome(
                campaign["id"], "erin", "clicked_link", INSTRUCTOR)
        outcome = self.ext.record_phishing_outcome(
            campaign["id"], "carol", "clicked_link", INSTRUCTOR)
        self.assertEqual(outcome["id"], "pso-1")

    def test_unknown_course_rejected_and_learner_cannot_write(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_phishing_campaign("X", "crs-99", INSTRUCTOR)
        with self.assertRaises(PermissionDenied):
            self.ext.create_phishing_campaign("X", self.cid, LEARNER)


class TestDeliveryEngine(BatchFixture):
    """Entry: Training content delivery & LMS engines — built as
    delivery-session records with status derived from core progress;
    no content is served."""

    def test_stored_record_has_no_status_key(self):
        session = self.ext.create_delivery_session(
            "carol", self.cid, INSTRUCTOR)
        self.assertEqual(session["id"], "dls-1")
        self.assertNotIn("status", session)
        view = self.ext.get_delivery_session(session["id"], ADMIN)
        self.assertEqual(view["status"], "enrolled")
        self.assertEqual(view["status_method"],
                         "derived_from_core_progress_records")

    def test_status_derived_from_core_progress(self):
        # No records of any kind: not started.
        self.assertEqual(
            self.ext.delivery_status("carol", self.cid, ADMIN)["status"],
            "not_started")
        # A delivery session (or a core enrollment) reads as enrolled.
        self.ext.create_delivery_session("carol", self.cid, INSTRUCTOR)
        self.assertEqual(
            self.ext.delivery_status("carol", self.cid, ADMIN)["status"],
            "enrolled")
        self.store.record_progress("carol", self.cid, "in_progress",
                                   INSTRUCTOR)
        self.assertEqual(
            self.ext.delivery_status("carol", self.cid, ADMIN)["status"],
            "in_progress")
        self.store.record_progress("carol", self.cid, "completed",
                                   INSTRUCTOR)
        status = self.ext.delivery_status("carol", self.cid, ADMIN)
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["method"],
                         "derived_from_core_progress_records")

    def test_session_from_another_course_rejected(self):
        other = self.store.create_course("Other", ADMIN)
        session = self.store.create_session(
            "S1", other["id"], "2026-06-01T09:00:00", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.create_delivery_session(
                "carol", self.cid, INSTRUCTOR, session_id=session["id"])

    def test_learner_scope_on_delivery_reads(self):
        session = self.ext.create_delivery_session(
            "erin", self.cid, INSTRUCTOR)
        with self.assertRaises(PermissionDenied):
            self.ext.get_delivery_session(session["id"], LEARNER)
        self.assertEqual(
            self.ext.list_delivery_sessions(LEARNER), [])


class TestCompetencyStub(BatchFixture):
    """Entry: Competency management & assessment-cycle engines —
    reference (stub-engine): definitions, cycles, sign-offs as data."""

    def _cycle(self):
        competency = self.ext.create_competency_definition(
            "role-nurse", "Medication administration", ADMIN,
            level_labels=["supervised", "independent"])
        return self.ext.create_assessment_cycle(
            competency["id"], ADMIN, period_label="2026-H1",
            interval_months=6)

    def test_stub_labels_on_every_record(self):
        competency = self.ext.create_competency_definition(
            "role-nurse", "Medication administration", ADMIN)
        self.assertIs(competency["reference_stub"], True)
        self.assertEqual(competency["state"], "recorded_reference_only")
        cycle = self._cycle()
        self.assertIs(cycle["reference_stub"], True)
        signoff = self.ext.record_assessor_signoff(
            cycle["id"], "carol", "assessor-7", "proficient", INSTRUCTOR)
        self.assertIs(signoff["reference_stub"], True)
        self.assertEqual(signoff["state"], "recorded_reference_only")

    def test_signoff_outcome_stored_verbatim(self):
        cycle = self._cycle()
        signoff = self.ext.record_assessor_signoff(
            cycle["id"], "carol", "assessor-7",
            "Proficient — per Dossier rating text", INSTRUCTOR)
        self.assertEqual(signoff["reported_outcome"],
                         "Proficient — per Dossier rating text")
        listed = self.ext.list_assessor_signoffs(ADMIN, cycle_id=cycle["id"])
        self.assertEqual(listed[0]["reported_outcome"],
                         "Proficient — per Dossier rating text")

    def test_interval_must_be_positive_int(self):
        competency = self.ext.create_competency_definition(
            "role-nurse", "Medication administration", ADMIN)
        for bad in (0, -3, 2.5, True):
            with self.assertRaises(ValidationError):
                self.ext.create_assessment_cycle(
                    competency["id"], ADMIN, interval_months=bad)


class TestNotificationEngine(BatchFixture):
    """Entry: Notification & reminder engine — built as rules plus a
    deterministic evaluation producing labeled transport receipts;
    nothing is sent."""

    def _overdue_assignment(self, learner="erin"):
        return self.store.create_compliance_assignment(
            learner, self.cid, "2026-06-01", ADMIN)

    def test_overdue_rule_receipt_labels_and_idempotence(self):
        self._overdue_assignment()
        rule = self.ext.create_notification_rule("assignment_overdue", ADMIN)
        created = self.ext.evaluate_notifications(ADMIN, as_of="2026-06-15")
        self.assertEqual(len(created), 1)
        receipt = created[0]
        self.assertEqual(receipt["id"], "nrc-1")
        self.assertIs(receipt["reference_transport"], True)
        self.assertEqual(receipt["state"], "recorded_reference_only")
        self.assertEqual(receipt["learner_id"], "erin")
        self.assertEqual(
            self.ext.evaluate_notifications(ADMIN, as_of="2026-06-15"), [])

    def test_completed_assignment_produces_no_receipt(self):
        self._overdue_assignment()
        self.store.record_progress("erin", self.cid, "completed", INSTRUCTOR)
        self.ext.create_notification_rule("assignment_overdue", ADMIN)
        self.assertEqual(
            self.ext.evaluate_notifications(ADMIN, as_of="2026-06-15"), [])

    def test_due_within_days_window(self):
        self.store.create_compliance_assignment(
            "erin", self.cid, "2026-06-10", ADMIN)
        self.ext.create_notification_rule(
            "assignment_due_within_days", ADMIN, within_days=7)
        created = self.ext.evaluate_notifications(ADMIN, as_of="2026-06-05")
        self.assertEqual(len(created), 1)
        self.assertEqual(
            self.ext.evaluate_notifications(ADMIN, as_of="2026-06-01"), [])

    def test_assessment_upcoming_uses_session_learners(self):
        self.store.create_session(
            "Exam", self.cid, "2026-06-20T09:00:00", INSTRUCTOR,
            kind="assessment", learner_ids=["carol", "erin"])
        self.ext.create_notification_rule(
            "assessment_upcoming", ADMIN, learner_id="carol")
        created = self.ext.evaluate_notifications(ADMIN, as_of="2026-06-15")
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["learner_id"], "carol")

    def test_rule_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_notification_rule("assignment_due_within_days",
                                              ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_notification_rule("assignment_overdue", ADMIN,
                                              within_days=3)
        with self.assertRaises(PermissionDenied):
            self.ext.create_notification_rule("assignment_overdue", LEARNER)


class TestMedicalEducation(BatchFixture):
    """Entry: Medical education management engines — built as clinical
    log records with totals derived at read."""

    def test_summary_derived_counts_and_minutes(self):
        self.ext.record_clinical_log("carol", "clinical_hours", 240,
                                     INSTRUCTOR, course_id=self.cid)
        self.ext.record_clinical_log("carol", "procedure", 45, INSTRUCTOR)
        self.ext.record_clinical_log("erin", "patient_encounter", 30,
                                     INSTRUCTOR)
        summary = self.ext.clinical_summary(ADMIN, learner_id="carol")
        self.assertEqual(summary["entries"], 2)
        self.assertEqual(summary["by_kind"]["clinical_hours"], 1)
        self.assertEqual(summary["by_kind"]["procedure"], 1)
        self.assertEqual(summary["total_minutes"], 285)
        self.assertEqual(summary["method"], "deterministic_counts")

    def test_minutes_must_be_non_negative_int(self):
        for bad in (-1, 1.5, True, "30"):
            with self.assertRaises(ValidationError):
                self.ext.record_clinical_log("carol", "procedure", bad,
                                             INSTRUCTOR)

    def test_learner_scope(self):
        self.ext.record_clinical_log("erin", "procedure", 10, INSTRUCTOR)
        self.assertEqual(self.ext.list_clinical_logs(LEARNER), [])
        with self.assertRaises(PermissionDenied):
            self.ext.clinical_summary(LEARNER, learner_id="erin")


class TestSimulationCenter(BatchFixture):
    """Entry: Simulation-center operations engines — built as resource
    and booking records; overlaps rejected as a records rule."""

    def test_booking_and_derived_schedule(self):
        resource = self.ext.create_sim_resource(
            "sim-room-1", "room", INSTRUCTOR, label="Debrief room")
        self.ext.record_sim_booking(
            resource["id"], "2026-06-20T13:00:00", "2026-06-20T14:00:00",
            INSTRUCTOR, course_id=self.cid, title="Scenario A")
        self.ext.record_sim_booking(
            resource["id"], "2026-06-20T09:00:00", "2026-06-20T10:00:00",
            INSTRUCTOR, title="Scenario B")
        view = self.ext.sim_resource_schedule(resource["id"], ADMIN)
        self.assertEqual(view["booking_count"], 2)
        self.assertEqual([b["title"] for b in view["bookings"]],
                         ["Scenario B", "Scenario A"])

    def test_overlapping_booking_rejected_no_id_consumed(self):
        resource = self.ext.create_sim_resource("sim-room-1", "room",
                                                INSTRUCTOR)
        first = self.ext.record_sim_booking(
            resource["id"], "2026-06-20T09:00:00", "2026-06-20T10:00:00",
            INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.record_sim_booking(
                resource["id"], "2026-06-20T09:30:00", "2026-06-20T10:30:00",
                INSTRUCTOR)
        second = self.ext.record_sim_booking(
            resource["id"], "2026-06-20T10:00:00", "2026-06-20T11:00:00",
            INSTRUCTOR)
        self.assertEqual((first["id"], second["id"]), ("smb-1", "smb-2"))

    def test_duplicate_resource_ref_rejected(self):
        self.ext.create_sim_resource("eq-1", "equipment", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.create_sim_resource("eq-1", "equipment", INSTRUCTOR)


class TestDigitalAdoption(BatchFixture):
    """Entry: Digital adoption & in-app guidance engines — built as
    guidance-flow records (steps verbatim) and reported usage events."""

    def test_flow_steps_verbatim_and_event_counts_derived(self):
        flow = self.ext.create_guidance_flow(
            "app-hris", "Submit a leave request", ADMIN,
            steps=["Open the time-off panel", "Pick dates"], topic="leave")
        self.assertEqual(flow["steps"],
                         ["Open the time-off panel", "Pick dates"])
        self.ext.record_guidance_event(flow["id"], "carol", "started",
                                       INSTRUCTOR)
        self.ext.record_guidance_event(flow["id"], "carol", "completed",
                                       INSTRUCTOR, step_index=1)
        view = self.ext.get_guidance_flow(flow["id"], ADMIN)
        self.assertEqual(view["event_counts"], {"started": 1, "completed": 1})

    def test_step_index_out_of_range_rejected(self):
        flow = self.ext.create_guidance_flow(
            "app-hris", "F", ADMIN, steps=["only step"])
        with self.assertRaises(ValidationError):
            self.ext.record_guidance_event(flow["id"], "carol", "completed",
                                           INSTRUCTOR, step_index=1)


class TestAiAssistants(BatchFixture):
    """Entry: AI assistants & guidance bots — labeled reference in
    substance: a deterministic lookup over held guidance records."""

    def test_lookup_is_labeled_deterministic_and_returns_records(self):
        self.ext.create_guidance_flow(
            "app-hris", "Leave walkthrough", ADMIN,
            steps=["Open panel"], topic="leave")
        self.ext.create_guidance_flow(
            "app-hris", "Pay walkthrough", ADMIN,
            steps=["Open pay"], topic="pay")
        result = self.ext.guidance_lookup("leave", ADMIN)
        self.assertEqual(result["method"], "deterministic_record_lookup")
        self.assertIs(result["reference_stub"], True)
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["steps"], ["Open panel"])

    def test_lookup_unknown_topic_returns_no_matches(self):
        result = self.ext.guidance_lookup("nonexistent", ADMIN)
        self.assertEqual(result["matches"], [])

    def test_profile_stub_label_and_duplicate_ref(self):
        profile = self.ext.create_assistant_profile(
            "bot-1", ADMIN, topics=["leave"])
        self.assertIs(profile["reference_stub"], True)
        self.assertEqual(profile["state"], "recorded_reference_only")
        with self.assertRaises(ValidationError):
            self.ext.create_assistant_profile("bot-1", ADMIN)


class TestDirectorySyncStub(BatchFixture):
    """Entry: Directory integration & provisioning sync — reference
    (stub-engine): sync snapshots as data; no core record changes."""

    def test_stub_label_and_counts(self):
        record = self.ext.create_directory_sync_record(
            "ad-main", INSTRUCTOR, added=3, changed=1, archived=2)
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertEqual(
            (record["added"], record["changed"], record["archived"]),
            (3, 1, 2))

    def test_sync_record_changes_no_core_record(self):
        before = self.store.report(ADMIN, as_of="2026-06-15")
        self.ext.create_directory_sync_record("ad-main", INSTRUCTOR, added=5)
        after = self.store.report(ADMIN, as_of="2026-06-15")
        self.assertEqual(before["enrollments"], after["enrollments"])
        self.assertEqual(before["progress_records"],
                         after["progress_records"])

    def test_negative_count_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_directory_sync_record("ad-main", INSTRUCTOR,
                                                  added=-1)


class TestCareerLadder(BatchFixture):
    """Entry: Career development & clinical ladder engines — built as
    ladder/evidence/review records; current level derived by presence
    match, with separation of duties on reviews."""

    def _ladder(self):
        return self.ext.create_ladder_program(
            "role-nurse", "Clinical ladder", ["L1", "L2", "L3"], INSTRUCTOR)

    def test_current_level_derived_from_advanced_reviews(self):
        ladder = self._ladder()
        sub1 = self.ext.record_evidence_submission(
            ladder["id"], "carol", "L1", "ev-1", INSTRUCTOR)
        self.ext.record_progression_review(sub1["id"], "advanced", ADMIN)
        sub2 = self.ext.record_evidence_submission(
            ladder["id"], "carol", "L2", "ev-2", INSTRUCTOR)
        self.ext.record_progression_review(sub2["id"], "returned", ADMIN)
        progress = self.ext.ladder_progress("carol", ladder["id"], ADMIN)
        self.assertEqual(progress["current_level"], "L1")
        self.assertEqual(progress["method"], "deterministic_presence_match")
        self.assertEqual(progress["levels"][1]["submissions"], 1)
        self.assertIs(progress["levels"][1]["advanced"], False)

    def test_reviewer_may_not_be_submission_recorder(self):
        ladder = self._ladder()
        sub = self.ext.record_evidence_submission(
            ladder["id"], "carol", "L1", "ev-1", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.record_progression_review(sub["id"], "advanced",
                                               INSTRUCTOR)

    def test_unknown_level_and_double_review_rejected(self):
        ladder = self._ladder()
        with self.assertRaises(ValidationError):
            self.ext.record_evidence_submission(
                ladder["id"], "carol", "L9", "ev-1", INSTRUCTOR)
        sub = self.ext.record_evidence_submission(
            ladder["id"], "carol", "L1", "ev-1", INSTRUCTOR)
        self.ext.record_progression_review(sub["id"], "advanced", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_progression_review(sub["id"], "advanced", ADMIN)


class TestAccreditationStub(BatchFixture):
    """Entry: Credentialing & accreditation workflow engines —
    reference (stub-engine): workflow/evidence/application records."""

    def test_stub_labels_and_credential_binding(self):
        workflow = self.ext.create_accreditation_workflow(
            "prog-med", "ACGME-style standard (label)", ADMIN)
        self.assertIs(workflow["reference_stub"], True)
        credential = self.store.create_credential(
            "carol", "State license", ADMIN, kind="licensure")
        application = self.ext.record_credentialing_application(
            workflow["id"], "carol", credential["id"], ADMIN)
        self.assertIs(application["reference_stub"], True)
        self.assertEqual(application["state"], "recorded_reference_only")

    def test_application_for_anothers_credential_rejected(self):
        workflow = self.ext.create_accreditation_workflow("prog-med", "S",
                                                          ADMIN)
        credential = self.store.create_credential("erin", "License", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_credentialing_application(
                workflow["id"], "carol", credential["id"], ADMIN)

    def test_evidence_record_stub_label(self):
        workflow = self.ext.create_accreditation_workflow("prog-med", "S",
                                                          ADMIN)
        evidence = self.ext.record_workflow_evidence(
            workflow["id"], "ev-ref-1", "Site-visit report", ADMIN)
        self.assertIs(evidence["reference_stub"], True)


class TestScoringEntry(BatchFixture):
    """Entry: Deterministic scoring & proficiency-rating engines —
    built in records form only (re-judgment option (a)): rules held
    as data and never applied; outcomes recorded verbatim as
    reported by an external assessor; nothing is computed."""

    def test_rule_record_is_data_never_applied(self):
        rule = self.ext.create_scoring_rule(
            "rule-1", "Assessor records proficient when all items done",
            INSTRUCTOR, course_id=self.cid)
        self.assertEqual(rule["method"], "recorded_rules_only")
        self.assertIs(rule["applied_here"], False)

    def test_reported_outcome_verbatim_and_core_untouched(self):
        assessment = self.store.create_assessment(
            "Safety check", "carol", INSTRUCTOR, course_id=self.cid)
        self.store.add_assessment_response(assessment["id"], "item-1",
                                           "answer text", INSTRUCTOR)
        before = self.store.get_assessment(assessment["id"], ADMIN)
        outcome = self.ext.record_reported_outcome(
            assessment["id"], "proficient", INSTRUCTOR,
            assessor_ref="assessor-7")
        self.assertEqual(outcome["reported_outcome"], "proficient")
        self.assertEqual(outcome["learner_id"], "carol")
        after = self.store.get_assessment(assessment["id"], ADMIN)
        self.assertEqual(before, after)

    def test_outcome_for_unknown_assessment_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_reported_outcome("asm-99", "proficient",
                                             INSTRUCTOR)

    def test_duplicate_rule_ref_rejected(self):
        self.ext.create_scoring_rule("rule-1", "text", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.create_scoring_rule("rule-1", "other text", INSTRUCTOR)


class TestRecruitingHcm(BatchFixture):
    """Entry: Recruiting/HCM suite — built as requisition/candidate/
    application/onboarding records with derived pipeline counts."""

    def _hired_application(self):
        requisition = self.ext.create_requisition("role-analyst", "Analyst",
                                                  INSTRUCTOR)
        candidate = self.ext.create_candidate("cand-1", INSTRUCTOR)
        application = self.ext.create_application(
            candidate["id"], requisition["id"], INSTRUCTOR)
        return application

    def test_pipeline_counts_derived(self):
        application = self._hired_application()
        self.assertEqual(application["stage"], "applied")
        self.ext.record_application_stage(application["id"], "hired",
                                          INSTRUCTOR)
        pipeline = self.ext.recruiting_pipeline(ADMIN)
        self.assertEqual(pipeline["applications_by_stage"]["hired"], 1)
        self.assertEqual(pipeline["candidates"], 1)
        self.assertEqual(pipeline["method"], "deterministic_counts")

    def test_onboarding_requires_hired_stage(self):
        application = self._hired_application()
        with self.assertRaises(ValidationError):
            self.ext.create_onboarding_record(application["id"], INSTRUCTOR)
        self.ext.record_application_stage(application["id"], "hired",
                                          INSTRUCTOR)
        enrollment = self.store.create_enrollment("carol", self.cid,
                                                  INSTRUCTOR)
        record = self.ext.create_onboarding_record(
            application["id"], INSTRUCTOR, enrollment_id=enrollment["id"])
        self.assertEqual(record["enrollment_id"], enrollment["id"])

    def test_duplicate_application_rejected(self):
        application = self._hired_application()
        with self.assertRaises(ValidationError):
            self.ext.create_application(application["candidate_id"],
                                        application["requisition_id"],
                                        INSTRUCTOR)


class TestTalentMatching(BatchFixture):
    """Entry: Talent & marketplace matching (no claimant in this set) —
    built as opportunity records plus a deterministic presence-match
    derivation over completed core progress; no ranking, no fit value."""

    def test_presence_match_over_completed_progress(self):
        other = self.store.create_course("Second", ADMIN)
        opportunity = self.ext.create_opportunity(
            "org-1", "role-tech", [self.cid, other["id"]], INSTRUCTOR)
        self.store.record_progress("carol", self.cid, "completed",
                                   INSTRUCTOR)
        result = self.ext.match_opportunities_for_learner("carol", ADMIN)
        view = result["opportunities"][0]
        self.assertEqual(view["missing_course_ids"], [other["id"]])
        self.assertIs(view["fully_matched"], False)
        self.store.record_progress("carol", other["id"], "completed",
                                   INSTRUCTOR)
        result = self.ext.match_opportunities_for_learner("carol", ADMIN)
        self.assertIs(result["opportunities"][0]["fully_matched"], True)
        self.assertEqual(result["method"], "deterministic_presence_match")

    def test_match_learners_for_opportunity(self):
        opportunity = self.ext.create_opportunity(
            "org-1", "role-tech", [self.cid], INSTRUCTOR)
        self.store.record_progress("carol", self.cid, "completed",
                                   INSTRUCTOR)
        self.store.record_progress("erin", self.cid, "in_progress",
                                   INSTRUCTOR)
        result = self.ext.match_learners_for_opportunity(opportunity["id"],
                                                         ADMIN)
        self.assertEqual(result["matched_learner_ids"], ["carol"])

    def test_opportunity_with_unknown_course_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_opportunity("org-1", "role-tech", ["crs-99"],
                                        INSTRUCTOR)


class TestProctoringStub(BatchFixture):
    """Entry: Remote proctoring & identity proofing (no claimant in
    this set) — reference (stub-engine): reported outcomes only, no
    decision, not an IdP (PLATFORM-LAYER.md decision 1)."""

    def test_proctoring_record_labels(self):
        assessment = self.store.create_assessment(
            "Exam", "carol", INSTRUCTOR, course_id=self.cid)
        record = self.ext.create_proctoring_record(
            assessment["id"], "provider-1", INSTRUCTOR)
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["decision_made"], False)
        self.assertEqual(record["learner_id"], "carol")

    def test_proofing_outcome_verbatim_no_decision_not_idp(self):
        record = self.ext.record_proofing_outcome(
            "carol", "provider-1", "verified by provider (their words)",
            INSTRUCTOR)
        self.assertEqual(record["reported_outcome"],
                         "verified by provider (their words)")
        self.assertIs(record["decision_made"], False)
        self.assertIs(record["identity_provider"], False)
        self.assertIs(record["reference_stub"], True)


class TestHostingStub(BatchFixture):
    """Entry: Hosting / multi-tenancy platform layer — reference
    (stub-engine): deployment-posture records; the build states its
    own single-tenant posture plainly."""

    def test_deployment_record_labels(self):
        record = self.ext.create_deployment_record(
            "dep-1", "multi-tenant SaaS (fork's own label)", ADMIN,
            region_label="us-east (label)")
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["multi_tenant_here"], False)
        self.assertEqual(record["state"], "recorded_reference_only")

    def test_summary_states_single_tenant_reference(self):
        summary = self.ext.deployment_summary(ADMIN)
        self.assertEqual(summary["build_tenancy"], "single_tenant_reference")
        self.assertEqual(summary["deployment_records"], 0)
        self.ext.create_deployment_record("dep-1", "label", ADMIN)
        summary = self.ext.deployment_summary(ADMIN)
        self.assertEqual(summary["deployment_records"], 1)
        self.assertEqual(summary["build_tenancy"], "single_tenant_reference")


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins for the whole extension surface."""

    def _exercise_surface(self):
        """Build one of everything and collect every returned value."""
        ext, store, cid = self.ext, self.store, self.cid
        out = []
        campaign = ext.create_phishing_campaign(
            "Sim", cid, INSTRUCTOR, learner_ids=["carol"])
        out.append(ext.record_phishing_outcome(
            campaign["id"], "carol", "reported", INSTRUCTOR))
        out.append(ext.get_phishing_campaign(campaign["id"], ADMIN))
        out.append(ext.create_delivery_session("carol", cid, INSTRUCTOR))
        out.append(ext.delivery_status("carol", cid, ADMIN))
        competency = ext.create_competency_definition("role-x", "C", ADMIN)
        cycle = ext.create_assessment_cycle(competency["id"], ADMIN)
        out.append(ext.record_assessor_signoff(
            cycle["id"], "carol", "assessor-1", "proficient", INSTRUCTOR))
        ext.create_notification_rule("assignment_overdue", ADMIN)
        store.create_compliance_assignment("erin", cid, "2026-06-01", ADMIN)
        out.append(ext.evaluate_notifications(ADMIN, as_of="2026-06-15"))
        out.append(ext.record_clinical_log("carol", "procedure", 30,
                                           INSTRUCTOR))
        out.append(ext.clinical_summary(ADMIN))
        resource = ext.create_sim_resource("res-1", "room", INSTRUCTOR)
        out.append(ext.record_sim_booking(
            resource["id"], "2026-06-20T09:00:00", "2026-06-20T10:00:00",
            INSTRUCTOR))
        out.append(ext.sim_resource_schedule(resource["id"], ADMIN))
        flow = ext.create_guidance_flow("app-1", "F", ADMIN, steps=["s"],
                                        topic="t")
        out.append(ext.record_guidance_event(flow["id"], "carol", "started",
                                             INSTRUCTOR))
        out.append(ext.guidance_lookup("t", ADMIN))
        out.append(ext.create_assistant_profile("bot-1", ADMIN))
        out.append(ext.create_directory_sync_record("ad-1", INSTRUCTOR))
        ladder = ext.create_ladder_program("role-x", "L", ["L1"], INSTRUCTOR)
        sub = ext.record_evidence_submission(ladder["id"], "carol", "L1",
                                             "ev-1", INSTRUCTOR)
        out.append(ext.record_progression_review(sub["id"], "advanced",
                                                 ADMIN))
        out.append(ext.ladder_progress("carol", ladder["id"], ADMIN))
        workflow = ext.create_accreditation_workflow("prog-1", "S", ADMIN)
        out.append(ext.record_workflow_evidence(workflow["id"], "ev-1",
                                                "label", ADMIN))
        credential = store.create_credential("carol", "Lic", ADMIN)
        out.append(ext.record_credentialing_application(
            workflow["id"], "carol", credential["id"], ADMIN))
        out.append(ext.create_scoring_rule("rule-1", "text", INSTRUCTOR))
        assessment = store.create_assessment("A", "carol", INSTRUCTOR,
                                             course_id=cid)
        out.append(ext.record_reported_outcome(assessment["id"],
                                               "proficient", INSTRUCTOR))
        requisition = ext.create_requisition("role-y", "T", INSTRUCTOR)
        candidate = ext.create_candidate("cand-1", INSTRUCTOR)
        out.append(ext.create_application(candidate["id"],
                                          requisition["id"], INSTRUCTOR))
        out.append(ext.recruiting_pipeline(ADMIN))
        opportunity = ext.create_opportunity("org-1", "role-z", [cid],
                                             INSTRUCTOR)
        out.append(ext.match_opportunities_for_learner("carol", ADMIN))
        out.append(ext.match_learners_for_opportunity(opportunity["id"],
                                                      ADMIN))
        out.append(ext.create_proctoring_record(assessment["id"], "prov-1",
                                                INSTRUCTOR))
        out.append(ext.record_proofing_outcome("carol", "prov-1",
                                               "reported ok", INSTRUCTOR))
        out.append(ext.create_deployment_record("dep-1", "label", ADMIN))
        out.append(ext.deployment_summary(ADMIN))
        out.append(ext.list_notification_receipts(ADMIN))
        out.append(ext.list_phishing_outcomes(ADMIN))
        out.append(ext.list_reported_outcomes(ADMIN))
        return out

    def test_no_score_grade_or_tier_key_anywhere_on_surface(self):
        for value in self._exercise_surface():
            self.assertEqual(_banned_keys(value), set(),
                             "banned key in %r" % (value,))

    def test_extension_mutations_use_ext_prefixed_audit_actions(self):
        self._exercise_surface()
        actions = [e["action"] for e in self.store.audit.entries()
                   if e["action"].startswith("ext_")]
        self.assertTrue(actions)
        self.assertIn("ext_delivery_session_create", actions)
        self.assertIn("ext_notification_evaluate", actions)

    def test_denied_write_is_audited_and_consumes_no_id(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_delivery_session("carol", self.cid, LEARNER)
        denied = [e for e in self.store.audit.entries()
                  if e["action"] == "ext_delivery_session_create:denied"]
        self.assertEqual(len(denied), 1)
        session = self.ext.create_delivery_session("carol", self.cid,
                                                   INSTRUCTOR)
        self.assertEqual(session["id"], "dls-1")

    def test_auditor_cannot_write_extension_records(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_scoring_rule("rule-1", "text", AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.create_deployment_record("dep-1", "label", AUDITOR)


if __name__ == "__main__":
    unittest.main()
