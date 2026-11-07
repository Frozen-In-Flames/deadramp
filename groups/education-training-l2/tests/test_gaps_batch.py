"""Final GAPS batch tests — Group 13, Education & Training L2.

Pins the extension surface in ``src/learn/extensions.py``
(``LearnExtensions``, wrapping the core ``LearnStore``): one test
class per open GAPS.md entry for this group (see ``../BATCH.md``
for the per-entry disposition), plus cross-cutting pins — the
founding **no-score invariant over the WHOLE extension surface**
(recursive key scan: no key named like a score or grade anywhere),
stub/transport labels, derived-never-stored values, learner scope,
RBAC denials (including the audited ``:denied`` record), and
no-id-consumed on failed operations.

Traces to: the 11 open entries of this group's section in the
repo-root GAPS.md and to ``../../gaps-batch/DECISION.md``. This
group is the category's founding tier; the forms follow this
group's UNION-SPEC.md, mirroring the adjudicated records forms the
untiered set's and the L1 group's batch units shipped for the same
families where the tiers agree.

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
    """Keys that would break the founding no-score invariant."""
    bad = set()
    for key in _all_keys(obj):
        lowered = key.lower()
        if (lowered == "score" or lowered.startswith("score_")
                or lowered.endswith("_score") or "grade" in lowered):
            bad.add(key)
    return bad


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.course = make_store()
        self.ext = LearnExtensions(self.store)
        self.cid = self.course["id"]


class TestTalentMatching(BatchFixture):
    """Entry: Talent, skills & marketplace matching (incl. career
    exploration / coaching and AI career assistants) — built as
    opportunity records plus a deterministic presence-match
    derivation (evidence per match, no ranking, no fit value);
    career assistants are profile records with a deterministic
    record lookup (no generated text)."""

    def test_presence_match_missing_course_not_fully_matched(self):
        other = self.store.create_course("Second", ADMIN)
        self.ext.create_opportunity(
            "org-1", "role-tech", [self.cid, other["id"]], INSTRUCTOR)
        self.store.record_progress("carol", self.cid, "completed",
                                   INSTRUCTOR)
        result = self.ext.match_opportunities_for_learner("carol", ADMIN)
        view = result["opportunities"][0]
        self.assertEqual(view["missing_course_ids"], [other["id"]])
        self.assertEqual(view["completed_course_ids"], [self.cid])
        self.assertIs(view["fully_matched"], False)
        self.assertEqual(result["method"], "deterministic_presence_match")

    def test_presence_match_complete_when_all_completed(self):
        self.ext.create_opportunity("org-1", "role-tech", [self.cid],
                                    INSTRUCTOR)
        self.store.record_progress("carol", self.cid, "completed",
                                   INSTRUCTOR)
        result = self.ext.match_opportunities_for_learner("carol", ADMIN)
        self.assertIs(result["opportunities"][0]["fully_matched"], True)
        self.assertEqual(result["opportunities"][0]["missing_course_ids"],
                         [])

    def test_match_learners_excludes_incomplete(self):
        opportunity = self.ext.create_opportunity(
            "org-1", "role-tech", [self.cid], INSTRUCTOR)
        self.store.record_progress("carol", self.cid, "completed",
                                   INSTRUCTOR)
        self.store.record_progress("erin", self.cid, "in_progress",
                                   INSTRUCTOR)
        result = self.ext.match_learners_for_opportunity(opportunity["id"],
                                                         ADMIN)
        self.assertEqual(result["matched_learner_ids"], ["carol"])

    def test_opportunity_with_unknown_course_rejected_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_opportunity("org-1", "role-tech", ["crs-99"],
                                        INSTRUCTOR)
        opportunity = self.ext.create_opportunity(
            "org-1", "role-tech", [self.cid], INSTRUCTOR)
        self.assertEqual(opportunity["id"], "opp-1")

    def test_career_profile_and_assistant_lookup(self):
        profile = self.ext.create_career_profile(
            "carol", INSTRUCTOR, interests=["simulation instruction"])
        self.assertEqual(profile["interests"], ["simulation instruction"])
        self.ext.create_guidance_flow(
            "app-career", "Explore instructor roles", ADMIN,
            steps=["Open roles panel"], topic="instruction")
        self.ext.create_guidance_flow(
            "app-career", "Explore admin roles", ADMIN,
            steps=["Open admin panel"], topic="admin")
        result = self.ext.guidance_lookup("instruction", ADMIN)
        self.assertEqual(result["method"], "deterministic_record_lookup")
        self.assertIs(result["reference_stub"], True)
        self.assertEqual(len(result["matches"]), 1)
        self.assertEqual(result["matches"][0]["steps"], ["Open roles panel"])
        assistant = self.ext.create_assistant_profile(
            "career-bot-1", ADMIN, topics=["instruction"])
        self.assertIs(assistant["reference_stub"], True)
        self.assertEqual(assistant["state"], "recorded_reference_only")


class TestRecruitingHcm(BatchFixture):
    """Entry: Recruiting, HCM / HRIS & workforce management suites
    (incl. performance and policy management) — built as pipeline
    records with derived counts; performance outcomes verbatim;
    policy text held as data, never enforced."""

    def _applied_application(self):
        requisition = self.ext.create_requisition("role-analyst", "Analyst",
                                                  INSTRUCTOR)
        candidate = self.ext.create_candidate("cand-1", INSTRUCTOR)
        return self.ext.create_application(candidate["id"],
                                           requisition["id"], INSTRUCTOR)

    def test_pipeline_counts_derived(self):
        application = self._applied_application()
        self.assertEqual(application["stage"], "applied")
        self.ext.record_application_stage(application["id"], "hired",
                                          INSTRUCTOR)
        pipeline = self.ext.recruiting_pipeline(ADMIN)
        self.assertEqual(pipeline["applications_by_stage"]["hired"], 1)
        self.assertEqual(pipeline["candidates"], 1)
        self.assertEqual(pipeline["method"], "deterministic_counts")

    def test_onboarding_requires_hired_stage(self):
        application = self._applied_application()
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
        application = self._applied_application()
        with self.assertRaises(ValidationError):
            self.ext.create_application(application["candidate_id"],
                                        application["requisition_id"],
                                        INSTRUCTOR)

    def test_performance_verbatim_and_policy_never_enforced(self):
        record = self.ext.record_performance_record(
            "person-7", "Meets expectations per manager report",
            INSTRUCTOR, period_label="2026-H1")
        self.assertEqual(record["reported_outcome"],
                         "Meets expectations per manager report")
        self.assertIs(record["evaluated_here"], False)
        policy = self.ext.create_policy_record(
            "pol-leave", "Leave policy text as adopted", ADMIN)
        self.assertIs(policy["enforced_here"], False)
        self.assertEqual(policy["policy_text"], "Leave policy text as adopted")


class TestContentStub(BatchFixture):
    """Entry: Course content authoring & delivery, media streaming —
    reference (stub-engine): package declarations and reported
    delivery receipts as data; nothing authored or streamed."""

    def test_stub_labels_on_every_record(self):
        package = self.ext.create_content_package(
            "pkg-1", "Simulation video package", ADMIN, course_id=self.cid,
            media_label="video (label)")
        self.assertIs(package["reference_stub"], True)
        self.assertEqual(package["state"], "recorded_reference_only")
        self.assertIs(package["authored_here"], False)
        self.assertIs(package["streamed_here"], False)
        receipt = self.ext.record_delivery_receipt(
            package["id"], "carol", "delivered per platform report",
            INSTRUCTOR)
        self.assertIs(receipt["reference_stub"], True)
        self.assertIs(receipt["reference_transport"], True)
        self.assertIs(receipt["delivered_here"], False)
        self.assertEqual(receipt["reported_state"],
                         "delivered per platform report")

    def test_duplicate_package_ref_rejected(self):
        self.ext.create_content_package("pkg-1", "P", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_content_package("pkg-1", "P2", ADMIN)


class TestSimulation(BatchFixture):
    """Entry: Simulation engines (capture, debriefing & playback);
    the simulation records are Core, the engine is not — built as
    session/event records with recorded states; the session's
    current state is derived from the latest recorded event;
    nothing is captured or played back here."""

    def test_stored_session_has_no_state_and_view_derives_it(self):
        session = self.ext.create_simulation_session(
            "Clinical scenario", self.cid, INSTRUCTOR,
            learner_ids=["carol"])
        self.assertNotIn("current_state", session)
        view = self.ext.get_simulation_session(session["id"], ADMIN)
        self.assertEqual(view["current_state"], "scheduled")
        self.assertEqual(view["state_method"], "latest_recorded_event")
        self.ext.record_simulation_event(session["id"], "captured",
                                         INSTRUCTOR)
        self.ext.record_simulation_event(session["id"], "debriefed",
                                         INSTRUCTOR)
        view = self.ext.get_simulation_session(session["id"], ADMIN)
        self.assertEqual(view["current_state"], "debriefed")
        self.assertEqual(view["event_count"], 2)

    def test_event_labels_and_no_capture(self):
        session = self.ext.create_simulation_session(
            "Scenario", self.cid, INSTRUCTOR)
        event = self.ext.record_simulation_event(
            session["id"], "played_back", INSTRUCTOR)
        self.assertIs(event["captured_here"], False)
        self.assertIs(event["played_back_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_simulation_event(session["id"], "rendered",
                                             INSTRUCTOR)


class TestProctoringStub(BatchFixture):
    """Entry: Remote proctoring & identity proofing (0 of 8 claims;
    explicitly not inferred from "secure assessment delivery") —
    reference (stub-engine): reported outcomes only, no decision,
    not an IdP (PLATFORM-LAYER.md decision 1)."""

    def test_proctoring_record_labels(self):
        assessment = self.store.create_assessment(
            "Exam", "carol", INSTRUCTOR, course_id=self.cid)
        record = self.ext.create_proctoring_record(
            assessment["id"], "provider-1", INSTRUCTOR)
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["decision_made"], False)
        self.assertIs(record["monitored_here"], False)
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


class TestScoringStub(BatchFixture):
    """Entry: Deterministic scoring & AI grading (0 of 8;
    assessments are administration records only, no score field
    exists by design) — reference (stub-engine), consistent with
    the founding design: rule records held as data and never
    applied; outcomes recorded verbatim as reported by an external
    assessor; the core record is untouched."""

    def test_rule_record_is_labeled_data_never_applied(self):
        rule = self.ext.create_rule_record(
            "rule-1", "Assessor records pass when all items done",
            INSTRUCTOR, course_id=self.cid)
        self.assertEqual(rule["method"], "recorded_rules_only")
        self.assertIs(rule["applied_here"], False)
        self.assertIs(rule["reference_stub"], True)
        self.assertEqual(rule["state"], "recorded_reference_only")

    def test_reported_outcome_verbatim_and_core_untouched(self):
        assessment = self.store.create_assessment(
            "Safety check", "carol", INSTRUCTOR, course_id=self.cid)
        self.store.add_assessment_response(assessment["id"], "item-1",
                                           "answer text", INSTRUCTOR)
        before = self.store.get_assessment(assessment["id"], ADMIN)
        outcome = self.ext.record_reported_outcome(
            assessment["id"], "pass per external assessor", INSTRUCTOR,
            assessor_ref="assessor-7")
        self.assertEqual(outcome["reported_outcome"],
                         "pass per external assessor")
        self.assertIs(outcome["computed_here"], False)
        self.assertIs(outcome["reference_stub"], True)
        after = self.store.get_assessment(assessment["id"], ADMIN)
        self.assertEqual(before, after)

    def test_outcome_for_unknown_assessment_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_reported_outcome("asm-99", "pass", INSTRUCTOR)

    def test_duplicate_rule_ref_rejected(self):
        self.ext.create_rule_record("rule-1", "text", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.create_rule_record("rule-1", "other text", INSTRUCTOR)


class TestCollaboration(BatchFixture):
    """Entry: Collaboration & social learning — built as group and
    activity records over core enrollments; counts derived."""

    def test_activity_counts_derived_and_membership_checked(self):
        group = self.ext.create_study_group(
            "Safety study circle", self.cid, INSTRUCTOR,
            member_ids=["carol", "erin"])
        self.ext.record_group_activity(group["id"], "carol", "posted",
                                       INSTRUCTOR)
        self.ext.record_group_activity(group["id"], "carol", "replied",
                                       INSTRUCTOR)
        self.ext.record_group_activity(group["id"], "erin", "posted",
                                       INSTRUCTOR)
        view = self.ext.get_study_group(group["id"], ADMIN)
        self.assertEqual(view["activity_counts"],
                         {"posted": 2, "replied": 1})
        self.assertEqual(view["activity_total"], 3)
        with self.assertRaises(ValidationError):
            self.ext.record_group_activity(group["id"], "mallory", "posted",
                                           INSTRUCTOR)

    def test_learner_scope_on_activities(self):
        group = self.ext.create_study_group(
            "Circle", self.cid, INSTRUCTOR, member_ids=["carol", "erin"])
        self.ext.record_group_activity(group["id"], "erin", "posted",
                                       INSTRUCTOR)
        self.assertEqual(self.ext.list_group_activities(LEARNER), [])


class TestDataServices(BatchFixture):
    """Entry: Data storage & processing services beyond the
    substrate's own records — built as dataset declaration records
    projected over core records; no rows stored."""

    def test_declaration_shape_and_projection_counts(self):
        declaration = self.ext.create_dataset_declaration(
            "ds-warehouse", ADMIN, source_label="warehouse (label)",
            reported_rows=5000)
        self.assertIs(declaration["rows_stored_here"], False)
        self.assertEqual(declaration["reported_rows"], 5000)
        projection = self.ext.dataset_projection(declaration["id"], ADMIN,
                                                 as_of="2026-06-15")
        self.assertEqual(projection["core_counts"]["courses"], 1)
        self.assertEqual(projection["core_counts"]["enrollments"], 0)
        self.assertEqual(projection["reported_rows"], 5000)
        self.assertIs(projection["rows_stored_here"], False)
        self.assertEqual(projection["method"],
                         "deterministic_projection_over_core_records")

    def test_reported_rows_must_be_non_negative_int(self):
        for bad in (-1, 1.5, True, "10"):
            with self.assertRaises(ValidationError):
                self.ext.create_dataset_declaration(
                    "ds-x", ADMIN, reported_rows=bad)

    def test_duplicate_dataset_ref_rejected(self):
        self.ext.create_dataset_declaration("ds-1", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_dataset_declaration("ds-1", ADMIN)


class TestNotifications(BatchFixture):
    """Entry: Notifications & reminders (0 of 8) — built as rules
    plus a deterministic evaluation producing labeled transport
    receipts; nothing is sent."""

    def test_overdue_rule_receipt_labels_and_idempotence(self):
        self.store.create_compliance_assignment(
            "erin", self.cid, "2026-06-01", ADMIN)
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
        self.store.create_compliance_assignment(
            "erin", self.cid, "2026-06-01", ADMIN)
        self.store.record_progress("erin", self.cid, "completed", INSTRUCTOR)
        self.ext.create_notification_rule("assignment_overdue", ADMIN)
        self.assertEqual(
            self.ext.evaluate_notifications(ADMIN, as_of="2026-06-15"), [])

    def test_rule_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_notification_rule("assignment_due_within_days",
                                              ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.create_notification_rule("assignment_overdue", LEARNER)


class TestHostingStub(BatchFixture):
    """Entry: General cloud hosting / PaaS (4 of 8; multi-tenancy is
    a deployment property) — reference (stub-engine), per
    PLATFORM-LAYER.md decision 6: deployment-posture records only;
    the build's own posture is stated plainly by the summary."""

    def test_deployment_record_labels(self):
        record = self.ext.create_deployment_record(
            "dep-vendor-cloud", "multi-tenant (vendor label)", ADMIN,
            region_label="vendor region (label)")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["hosted_here"], False)
        self.assertIs(record["multi_tenant_here"], False)
        self.assertEqual(record["tenancy_label"],
                         "multi-tenant (vendor label)")

    def test_summary_states_build_posture(self):
        self.ext.create_deployment_record("dep-1", "hosted (label)", ADMIN)
        summary = self.ext.deployment_summary(ADMIN)
        self.assertEqual(summary["deployment_records"], 1)
        self.assertEqual(summary["build_tenancy"], "single_tenant_reference")
        self.assertEqual(summary["method"], "recorded_deployment_posture")

    def test_duplicate_deployment_ref_rejected(self):
        self.ext.create_deployment_record("dep-1", "label", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_deployment_record("dep-1", "label", ADMIN)


class TestIntegrationsStub(BatchFixture):
    """Entry: Integrations & APIs as a union function (0 of 8) —
    reference (stub-engine): integration declarations as data;
    creating one changes no core record and calls nothing."""

    def test_stub_labels(self):
        record = self.ext.create_integration_record(
            "int-hris", "HRIS endpoint (label)", ADMIN)
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["executed_here"], False)
        self.assertIs(record["connected_here"], False)

    def test_integration_record_changes_no_core_record(self):
        before = self.store.report(ADMIN, as_of="2026-06-15")
        self.ext.create_integration_record("int-hris", "label", ADMIN)
        after = self.store.report(ADMIN, as_of="2026-06-15")
        self.assertEqual(before["enrollments"], after["enrollments"])
        self.assertEqual(before["courses"], after["courses"])

    def test_duplicate_ref_rejected(self):
        self.ext.create_integration_record("int-1", "label", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_integration_record("int-1", "label", ADMIN)


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins for the whole extension surface."""

    def _exercise_surface(self):
        """Build one of everything and collect every returned value."""
        ext, store, cid = self.ext, self.store, self.cid
        out = []
        opportunity = ext.create_opportunity("org-1", "role-z", [cid],
                                             INSTRUCTOR)
        out.append(ext.match_opportunities_for_learner("carol", ADMIN))
        out.append(ext.match_learners_for_opportunity(opportunity["id"],
                                                      ADMIN))
        out.append(ext.create_career_profile("carol", INSTRUCTOR))
        ext.create_guidance_flow("app-1", "F", ADMIN, steps=["s"], topic="t")
        out.append(ext.guidance_lookup("t", ADMIN))
        out.append(ext.create_assistant_profile("bot-1", ADMIN))
        requisition = ext.create_requisition("role-y", "T", INSTRUCTOR)
        candidate = ext.create_candidate("cand-1", INSTRUCTOR)
        out.append(ext.create_application(candidate["id"],
                                          requisition["id"], INSTRUCTOR))
        out.append(ext.recruiting_pipeline(ADMIN))
        out.append(ext.record_performance_record("person-1", "reported",
                                                 INSTRUCTOR))
        out.append(ext.create_policy_record("pol-1", "text", ADMIN))
        package = ext.create_content_package("pkg-1", "P", ADMIN,
                                             course_id=cid)
        out.append(ext.record_delivery_receipt(package["id"], "carol",
                                               "reported", INSTRUCTOR))
        session = ext.create_simulation_session("S", cid, INSTRUCTOR,
                                                learner_ids=["carol"])
        out.append(ext.record_simulation_event(session["id"], "captured",
                                               INSTRUCTOR))
        out.append(ext.get_simulation_session(session["id"], ADMIN))
        assessment = store.create_assessment("A", "carol", INSTRUCTOR,
                                             course_id=cid)
        out.append(ext.create_proctoring_record(assessment["id"], "prov-1",
                                                INSTRUCTOR))
        out.append(ext.record_proofing_outcome("carol", "prov-1",
                                               "reported ok", INSTRUCTOR))
        out.append(ext.create_rule_record("rule-1", "text", INSTRUCTOR))
        out.append(ext.record_reported_outcome(assessment["id"],
                                               "reported pass", INSTRUCTOR))
        group = ext.create_study_group("G", cid, INSTRUCTOR,
                                       member_ids=["carol"])
        out.append(ext.record_group_activity(group["id"], "carol", "posted",
                                             INSTRUCTOR))
        out.append(ext.get_study_group(group["id"], ADMIN))
        declaration = ext.create_dataset_declaration("ds-1", ADMIN)
        out.append(ext.dataset_projection(declaration["id"], ADMIN,
                                          as_of="2026-06-15"))
        ext.create_notification_rule("assignment_overdue", ADMIN)
        store.create_compliance_assignment("erin", cid, "2026-06-01", ADMIN)
        out.append(ext.evaluate_notifications(ADMIN, as_of="2026-06-15"))
        out.append(ext.create_deployment_record("dep-1", "label", ADMIN))
        out.append(ext.deployment_summary(ADMIN))
        out.append(ext.create_integration_record("int-1", "label", ADMIN))
        out.append(ext.list_notification_receipts(ADMIN))
        out.append(ext.list_reported_outcomes(ADMIN))
        return out

    def test_no_score_or_grade_key_anywhere_on_surface(self):
        for value in self._exercise_surface():
            self.assertEqual(_banned_keys(value), set(),
                             "banned key in %r" % (value,))

    def test_extension_mutations_use_ext_prefixed_audit_actions(self):
        self._exercise_surface()
        actions = [e["action"] for e in self.store.audit.entries()
                   if e["action"].startswith("ext_")]
        self.assertTrue(actions)
        self.assertIn("ext_opportunity_create", actions)
        self.assertIn("ext_notification_evaluate", actions)

    def test_denied_write_is_audited_and_consumes_no_id(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_opportunity("org-1", "role-x", [self.cid],
                                        LEARNER)
        denied = [e for e in self.store.audit.entries()
                  if e["action"] == "ext_opportunity_create:denied"]
        self.assertEqual(len(denied), 1)
        opportunity = self.ext.create_opportunity(
            "org-1", "role-x", [self.cid], INSTRUCTOR)
        self.assertEqual(opportunity["id"], "opp-1")

    def test_auditor_cannot_write_extension_records(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_rule_record("rule-1", "text", AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.create_integration_record("int-1", "label", AUDITOR)


if __name__ == "__main__":
    unittest.main()
