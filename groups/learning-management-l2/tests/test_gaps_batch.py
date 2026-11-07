"""Final GAPS batch tests — Singleton 48, Learning Management L2.

Pins the extension surface in ``src/lms/extensions.py``
(``LmsExtensions``, wrapping the core ``LmsStore``): one test class
per open GAPS.md entry for this group (see ``../BATCH.md`` for the
per-entry disposition), plus cross-cutting pins — the founding
no-score invariant over the WHOLE extension surface (recursive key
scan), derived-never-stored values, stub/transport labels, learner
scope, RBAC denials, and ``ext_``-prefixed audit actions.

Fixtures: ``make_store()`` (learner ref "carol", course "Safety
Basics") plus a second learner (ref "erin") where scope or
separation of duties needs one.
"""

import unittest

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError
from lms.extensions import LmsExtensions


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


def _score_keys(obj):
    bad = set()
    for key in _all_keys(obj):
        lowered = key.lower()
        if (lowered == "score" or lowered.startswith("score_")
                or lowered.endswith("_score")):
            bad.add(key)
    return bad


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.learner, self.course = make_store()
        self.store.create_learner("erin", "Erin Learner", ADMIN)
        self.ext = LmsExtensions(self.store)


class TestDeliveryEngine(BatchFixture):
    """Entry: Learning delivery engine (the LMS runtime itself) —
    built as delivery-session records with derived status."""

    def test_session_shape_has_no_status_key(self):
        session = self.ext.create_delivery_session(
            "carol", self.course["id"], INSTRUCTOR)
        self.assertEqual(session["id"], "dls-1")
        self.assertNotIn("status", session)
        view = self.ext.get_delivery_session(session["id"], ADMIN)
        self.assertEqual(view["status"], "enrolled")
        self.assertEqual(view["status_method"],
                         "derived_from_core_progress_records")

    def test_status_derived_from_core_progress(self):
        self.ext.create_delivery_session("carol", self.course["id"], INSTRUCTOR)
        self.assertEqual(
            self.ext.delivery_status("carol", self.course["id"], ADMIN)["status"],
            "enrolled")
        self.store.record_progress("carol", self.course["id"], "in_progress",
                                   INSTRUCTOR)
        self.assertEqual(
            self.ext.delivery_status("carol", self.course["id"], ADMIN)["status"],
            "in_progress")
        self.store.record_progress("carol", self.course["id"], "completed",
                                   INSTRUCTOR)
        status = self.ext.delivery_status("carol", self.course["id"], ADMIN)
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["method"],
                         "derived_from_core_progress_records")

    def test_validation_scope_and_permissions(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_delivery_session("ghost", self.course["id"],
                                             INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.create_delivery_session(
                "carol", self.course["id"], INSTRUCTOR, mode="teleport")
        with self.assertRaises(PermissionDenied):
            self.ext.create_delivery_session("carol", self.course["id"], LEARNER)
        session = self.ext.create_delivery_session(
            "carol", self.course["id"], INSTRUCTOR)
        # failed attempts consumed no id
        self.assertEqual(session["id"], "dls-1")
        with self.assertRaises(PermissionDenied):
            self.ext.delivery_status("erin", self.course["id"], LEARNER)
        own = self.ext.list_delivery_sessions(LEARNER)
        self.assertEqual([s["id"] for s in own], ["dls-1"])


class TestPackaging(BatchFixture):
    """Entry: SCORM / AICC / cmi5 packaging & distribution runtime —
    built as manifest/distribution records with record conformance."""

    def _package(self):
        item = self.store.create_content_item(
            "Safety SCORM", "scorm_2004", ADMIN, course_id=self.course["id"])
        return item, self.ext.create_package(
            "Safety Pack", "scorm_2004", ADMIN,
            course_id=self.course["id"], item_refs=[item["id"]])

    def test_conformance_derived_and_distribution_recorded(self):
        _, package = self._package()
        result = self.ext.package_conformance(package["id"], ADMIN)
        self.assertTrue(result["conformant"])
        self.assertEqual(result["method"], "record_validation_only")
        dist = self.ext.record_distribution(package["id"], "enclave-a", ADMIN)
        self.assertEqual(dist["state"], "recorded")
        self.assertEqual(
            len(self.ext.list_distributions(ADMIN, package_id=package["id"])), 1)

    def test_conformance_flags_standard_mismatch(self):
        pdf = self.store.create_content_item(
            "Safety PDF", "pdf", ADMIN, course_id=self.course["id"])
        package = self.ext.create_package(
            "Mixed Pack", "scorm_2004", ADMIN, item_refs=[pdf["id"]])
        result = self.ext.package_conformance(package["id"], ADMIN)
        self.assertFalse(result["conformant"])
        self.assertEqual(result["mismatched_refs"], [pdf["id"]])
        empty = self.ext.create_package("Empty Pack", "cmi5", ADMIN)
        self.assertFalse(
            self.ext.package_conformance(empty["id"], ADMIN)["conformant"])

    def test_bad_standard_and_unknown_item_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_package("X", "xapi", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.create_package("X", "aicc", ADMIN, item_refs=["cnt-999"])


class TestXapiConformance(BatchFixture):
    """Entry: xAPI protocol runtime & LRS conformance — built as
    record conformance over the core statements + labeled forwards."""

    def test_conformance_over_core_statements(self):
        self.store.record_statement("carol", "completed", self.course["id"],
                                    INSTRUCTOR, result_text="done")
        self.store.record_statement("carol", "experienced", self.course["id"],
                                    INSTRUCTOR)
        result = self.ext.statement_conformance(ADMIN)
        self.assertEqual(result["statements_examined"], 2)
        self.assertTrue(result["conformant"])
        self.assertEqual(result["statements_by_verb"],
                         {"completed": 1, "experienced": 1})
        self.assertEqual(result["method"], "record_validation_only")
        # the core statement shape is untouched: exactly eight keys
        stmt = self.store.list_statements(ADMIN)[0]
        self.assertEqual(len(stmt), 8)

    def test_forward_record_is_labeled_transport(self):
        stmt = self.store.record_statement(
            "carol", "completed", self.course["id"], INSTRUCTOR)
        forward = self.ext.record_statement_forward(stmt["id"], "lrs-peer-1",
                                                    INSTRUCTOR)
        self.assertIs(forward["reference_transport"], True)
        self.assertEqual(forward["state"], "recorded_reference_only")
        self.assertEqual(len(self.ext.list_statement_forwards(ADMIN)), 1)
        with self.assertRaises(NotFoundError):
            self.ext.record_statement_forward("stm-999", "lrs-peer-1",
                                              INSTRUCTOR)


class TestAnalytics(BatchFixture):
    """Entry: Learning analytics & outcomes engines — built as
    deterministic count derivations, method-labeled, no scores."""

    def test_summary_counts_and_share_derived(self):
        self.store.record_progress("carol", self.course["id"], "completed",
                                   INSTRUCTOR)
        self.store.record_progress("erin", self.course["id"], "in_progress",
                                   INSTRUCTOR)
        self.store.create_compliance_assignment("carol", self.course["id"],
                                                "2026-06-01", ADMIN)
        summary = self.ext.analytics_summary(ADMIN, as_of="2026-06-15")
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["progress_records"], 2)
        self.assertEqual(summary["progress_by_status"]["completed"], 1)
        self.assertEqual(summary["completed_share_bps"], 5000)
        self.assertEqual(summary["compliance_by_status"]["completed"], 1)

    def test_outcomes_by_course_counts_only(self):
        self.store.record_progress("carol", self.course["id"], "completed",
                                   INSTRUCTOR)
        event = self.store.create_event("Safety Live", "2026-07-01T15:00:00Z",
                                        INSTRUCTOR, course_id=self.course["id"])
        self.store.register_learner(event["id"], "carol", INSTRUCTOR)
        result = self.ext.outcomes_by_course(ADMIN)
        row = result["courses"][0]
        self.assertEqual(row["course_id"], self.course["id"])
        self.assertEqual(row["progress_by_status"]["completed"], 1)
        self.assertEqual(row["registrations"], 1)

    def test_learner_denied_report_read(self):
        with self.assertRaises(PermissionDenied):
            self.ext.analytics_summary(LEARNER)


class TestCareerMapping(BatchFixture):
    """Entry: Career mapping & recommendation engine — built as
    career-path records + a deterministic gap derivation."""

    def _path(self):
        comp_a = self.store.create_competency("Safety Awareness", INSTRUCTOR)
        comp_b = self.store.create_competency("Incident Reporting", INSTRUCTOR)
        path = self.ext.create_career_path(
            "Safety Lead", INSTRUCTOR,
            competency_ids=[comp_a["id"], comp_b["id"]],
            course_ids=[self.course["id"]])
        return comp_a, comp_b, path

    def test_recommendation_is_deterministic_gap_match(self):
        comp_a, comp_b, path = self._path()
        result = self.ext.recommend_training("carol", path["id"], ADMIN)
        self.assertEqual(result["method"], "deterministic_gap_match")
        self.assertEqual(result["missing_competency_ids"],
                         [comp_a["id"], comp_b["id"]])
        self.assertEqual(result["recommended_course_ids"], [self.course["id"]])
        self.store.record_learner_competency("carol", comp_a["id"],
                                             "Level 3 (vendor scale)", INSTRUCTOR)
        self.store.record_progress("carol", self.course["id"], "completed",
                                   INSTRUCTOR)
        result = self.ext.recommend_training("carol", path["id"], ADMIN)
        self.assertEqual(result["covered_competency_ids"], [comp_a["id"]])
        self.assertEqual(result["missing_competency_ids"], [comp_b["id"]])
        self.assertEqual(result["recommended_course_ids"], [])

    def test_unknown_references_rejected_and_scope(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_career_path("X", INSTRUCTOR,
                                        competency_ids=["cpt-999"])
        _, _, path = self._path()
        with self.assertRaises(PermissionDenied):
            self.ext.recommend_training("erin", path["id"], LEARNER)


class TestSuccession(BatchFixture):
    """Entry: Leadership succession planning suite — built as
    succession-plan records + a presence-match coverage derivation."""

    def test_coverage_derived_by_presence(self):
        comp = self.store.create_competency("Safety Awareness", INSTRUCTOR)
        plan = self.ext.create_succession_plan(
            "role-site-safety-lead", INSTRUCTOR,
            candidate_refs=["carol", "erin"], competency_ids=[comp["id"]])
        coverage = self.ext.succession_coverage(plan["id"], ADMIN)
        self.assertEqual(coverage["method"], "deterministic_presence_match")
        self.assertFalse(coverage["candidates"][0]["covers_all"])
        self.store.record_learner_competency("carol", comp["id"],
                                             "ready (caller scale)", INSTRUCTOR)
        coverage = self.ext.succession_coverage(plan["id"], ADMIN)
        self.assertTrue(coverage["candidates"][0]["covers_all"])
        self.assertFalse(coverage["candidates"][1]["covers_all"])

    def test_unknown_candidate_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_succession_plan("role-x", INSTRUCTOR,
                                            candidate_refs=["ghost"])


class TestCandidateReview(BatchFixture):
    """Entry: Candidate review / talent acquisition system — built
    as application records with separation-of-duties review."""

    def test_review_flow_with_separation_of_duties(self):
        application = self.ext.create_application("cand-42", "fellowship-2026",
                                                  INSTRUCTOR)
        self.assertEqual(application["state"], "submitted")
        with self.assertRaises(PermissionDenied):
            self.ext.review_application(application["id"], "accepted",
                                        INSTRUCTOR)
        reviewed = self.ext.review_application(application["id"], "accepted",
                                               ADMIN, note="panel ok")
        self.assertEqual(reviewed["state"], "accepted")
        self.assertEqual(reviewed["reviewed_by"], "alice")
        with self.assertRaises(ValidationError):
            self.ext.review_application(application["id"], "accepted", ADMIN)

    def test_opaque_refs_need_not_be_learners(self):
        application = self.ext.create_application("cand-99", "internship-2026",
                                                  INSTRUCTOR)
        self.assertEqual(application["candidate_ref"], "cand-99")
        self.assertEqual(
            len(self.ext.list_applications(ADMIN, program_ref="internship-2026")),
            1)


class TestSurveys(BatchFixture):
    """Entry: Employee survey engine — built as instrument/response
    records with verbatim-answer tallies; answers are text only."""

    def test_response_and_summary_tallies(self):
        survey = self.ext.create_survey(
            "Engagement", INSTRUCTOR, questions=["How is the pace?"])
        self.ext.record_survey_response(survey["id"], "emp-1", ["Fast"],
                                        INSTRUCTOR)
        self.ext.record_survey_response(survey["id"], "emp-2", ["Fast"],
                                        INSTRUCTOR)
        self.ext.record_survey_response(survey["id"], "emp-3", ["Steady"],
                                        INSTRUCTOR)
        summary = self.ext.survey_summary(survey["id"], ADMIN)
        self.assertEqual(summary["responses"], 3)
        self.assertEqual(summary["per_question"][0]["answers"],
                         {"Fast": 2, "Steady": 1})
        self.assertEqual(summary["method"], "verbatim_answer_counts")

    def test_numeric_answers_rejected_no_score_shape(self):
        survey = self.ext.create_survey("Pulse", INSTRUCTOR, questions=["Rate?"])
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(survey["id"], "emp-1", [5],
                                            INSTRUCTOR)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(survey["id"], "emp-1",
                                            ["a", "b"], INSTRUCTOR)


class TestKnowledgeBase(BatchFixture):
    """Entry: Knowledge base / wiki platform (adjacent product) —
    built as article records with append-only revisions."""

    def test_article_lifecycle_version_count_derived(self):
        article = self.ext.create_kb_article(
            "Safety FAQ", "Wear PPE.", ADMIN, tags=["safety"])
        self.assertEqual(article["version_count"], 1)
        revised = self.ext.revise_kb_article(article["id"], "Wear PPE always.",
                                             ADMIN)
        self.assertEqual(revised["version_count"], 2)
        self.assertEqual(revised["body"], "Wear PPE always.")
        found = self.ext.search_kb("PPE", ADMIN)
        self.assertEqual([a["id"] for a in found], [article["id"]])


class TestCms(BatchFixture):
    """Entry: Web CMS platform (adjacent product) — built as page
    records with a recorded draft/published state; nothing served."""

    def test_page_lifecycle_and_unique_slug(self):
        page = self.ext.create_cms_page("safety-home", "Safety", "Body",
                                        ADMIN)
        self.assertEqual(page["state"], "draft")
        with self.assertRaises(ValidationError):
            self.ext.create_cms_page("safety-home", "Dupe", "Body", ADMIN)
        published = self.ext.publish_cms_page(page["id"], ADMIN)
        self.assertEqual(published["state"], "published")
        with self.assertRaises(ValidationError):
            self.ext.publish_cms_page(page["id"], ADMIN)
        self.assertEqual(
            len(self.ext.list_cms_pages(ADMIN, state="published")), 1)


class TestReportBuilder(BatchFixture):
    """Entry: Configurable report builder & dashboards — built as
    report definitions whose runs derive counts at run time."""

    def test_definition_and_run_derives_counts(self):
        definition = self.ext.create_report_definition(
            "Ops Dashboard", INSTRUCTOR, sections=["learners", "progress"])
        self.assertNotIn("results", definition)
        self.store.record_progress("carol", self.course["id"], "completed",
                                   INSTRUCTOR)
        run = self.ext.run_report_definition(definition["id"], ADMIN,
                                             as_of="2026-06-15")
        self.assertEqual(run["results"], {"learners": 2, "progress": 1})
        self.assertEqual(run["method"], "deterministic_counts")

    def test_bad_section_and_learner_run_denied(self):
        with self.assertRaises(ValidationError):
            self.ext.create_report_definition("Bad", INSTRUCTOR,
                                              sections=["scores"])
        definition = self.ext.create_report_definition(
            "Ok", INSTRUCTOR, sections=["courses"])
        with self.assertRaises(PermissionDenied):
            self.ext.run_report_definition(definition["id"], LEARNER)


class TestNotificationTransport(BatchFixture):
    """Entry: Notification automation & delivery transport — built
    as rules + an evaluation pass producing labeled receipts."""

    def test_evaluation_produces_labeled_receipts_only(self):
        self.store.create_compliance_assignment("carol", self.course["id"],
                                                "2026-06-01", ADMIN)
        rule = self.ext.create_notification_rule(
            "Overdue nudge", "compliance_overdue", "*", "Training overdue",
            INSTRUCTOR)
        receipts = self.ext.evaluate_notification_rules(INSTRUCTOR,
                                                        as_of="2026-06-15")
        self.assertEqual(len(receipts), 1)
        self.assertIs(receipts[0]["reference_transport"], True)
        self.assertEqual(receipts[0]["state"], "recorded_reference_only")
        self.assertEqual(receipts[0]["rule_id"], rule["id"])
        # the core notification registry shows the recorded notification
        notes = self.store.list_notifications(ADMIN, recipient_ref="carol")
        self.assertEqual(len(notes), 1)
        # before the due date there is nothing overdue: no receipts
        fresh_store_ext = LmsExtensions(self.store)
        self.assertEqual(
            fresh_store_ext.evaluate_notification_rules(INSTRUCTOR,
                                                        as_of="2026-05-01"),
            [])

    def test_bad_trigger_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_notification_rule("X", "whenever", "*", "S",
                                              INSTRUCTOR)


class TestEhriStub(BatchFixture):
    """Entry: EHRI integration engine — stub-engine: labeled
    reference feed records; nothing collected or transmitted."""

    def test_feed_record_labeled_reference(self):
        record = self.ext.create_ehri_feed_record(
            "2026-06", ADMIN, learner_refs=["carol", "erin"])
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertEqual(record["learner_count"], 2)
        self.assertEqual(len(self.ext.list_ehri_feed_records(ADMIN)), 1)

    def test_bad_period_and_unknown_learner_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_ehri_feed_record("2026-13", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.create_ehri_feed_record("2026-06", ADMIN,
                                             learner_refs=["ghost"])
        with self.assertRaises(PermissionDenied):
            self.ext.create_ehri_feed_record("2026-06", INSTRUCTOR)


class TestAuthoringStub(BatchFixture):
    """Entry: Content authoring tools & lesson-plan editor —
    stub-engine: labeled reference draft records."""

    def test_draft_labeled_and_revision_append_only(self):
        plan = self.store.create_lesson_plan("Safety Plan", self.course["id"],
                                             ADMIN)
        draft = self.ext.create_authoring_draft(
            "Safety Draft", ADMIN, lesson_plan_id=plan["id"],
            sections=["Intro"])
        self.assertIs(draft["reference_stub"], True)
        self.assertEqual(draft["revision_count"], 1)
        revised = self.ext.revise_authoring_draft(draft["id"],
                                                  ["Intro", "Body"], ADMIN)
        self.assertEqual(revised["revision_count"], 2)
        self.assertEqual(revised["sections"], ["Intro", "Body"])
        # the core lesson plan is unchanged by the draft surface
        self.assertEqual(
            self.store.get_lesson_plan(plan["id"], ADMIN)["item_refs"], [])


class TestFormWorkflowStub(BatchFixture):
    """Entry: SF-182 form rendering / routing / signature workflow —
    stub-engine: labeled reference records over core authorizations."""

    def test_form_record_labeled_and_core_decision_stands(self):
        auth = self.store.create_authorization("carol", "Safety Basics",
                                               INSTRUCTOR,
                                               course_id=self.course["id"])
        self.store.decide_authorization(auth["id"], "approved", ADMIN)
        record = self.ext.create_form_workflow_record(auth["id"], INSTRUCTOR)
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["steps"], ["render", "route", "sign"])
        self.assertEqual(record["authorization_state"], "approved")
        self.assertEqual(
            self.store.get_authorization(auth["id"], ADMIN)["state"], "approved")
        with self.assertRaises(NotFoundError):
            self.ext.create_form_workflow_record("aut-999", INSTRUCTOR)


class TestWorkflowExecutionStub(BatchFixture):
    """Entry: Workflow execution engine — stub-engine by triage:
    the registry still never executes; this is a labeled reference
    record that changes no other record."""

    def test_execution_record_changes_nothing(self):
        workflow = self.store.create_workflow(
            "Onboarding", ["register", "assign"], INSTRUCTOR, scope="hr")
        before_notifications = len(self.store.list_notifications(ADMIN))
        before_registrations = len(self.store.list_registrations(ADMIN))
        record = self.ext.create_execution_record(workflow["id"], INSTRUCTOR)
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertEqual(record["steps"], ["register", "assign"])
        self.assertEqual(len(self.store.list_notifications(ADMIN)),
                         before_notifications)
        self.assertEqual(len(self.store.list_registrations(ADMIN)),
                         before_registrations)
        self.assertEqual(
            self.store.get_workflow(workflow["id"], ADMIN)["steps"],
            ["register", "assign"])
        with self.assertRaises(NotFoundError):
            self.ext.create_execution_record("wfl-999", INSTRUCTOR)


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins: no score anywhere on the extension
    surface, ext_-prefixed audit, and learner write denials."""

    def test_no_score_field_anywhere_on_extension_surface(self):
        item = self.store.create_content_item(
            "Safety SCORM", "scorm_2004", ADMIN, course_id=self.course["id"])
        package = self.ext.create_package("Pack", "scorm_2004", ADMIN,
                                          item_refs=[item["id"]])
        self.store.record_progress("carol", self.course["id"], "completed",
                                   INSTRUCTOR, percent_complete=88)
        self.store.record_statement("carol", "completed", self.course["id"],
                                    INSTRUCTOR, result_text="score: 88/100")
        survey = self.ext.create_survey("Pulse", INSTRUCTOR, questions=["Q?"])
        self.ext.record_survey_response(survey["id"], "emp-1", ["ok"],
                                        INSTRUCTOR)
        auth = self.store.create_authorization("carol", "Safety", INSTRUCTOR)
        workflow = self.store.create_workflow("W", ["step"], INSTRUCTOR)
        definition = self.ext.create_report_definition(
            "Dash", INSTRUCTOR, sections=["progress", "compliance"])
        surfaces = [
            self.ext.create_delivery_session("carol", self.course["id"],
                                             INSTRUCTOR),
            self.ext.delivery_status("carol", self.course["id"], ADMIN),
            package,
            self.ext.package_conformance(package["id"], ADMIN),
            self.ext.record_distribution(package["id"], "enclave-a", ADMIN),
            self.ext.statement_conformance(ADMIN),
            self.ext.analytics_summary(ADMIN, as_of="2026-06-15"),
            self.ext.outcomes_by_course(ADMIN),
            self.ext.survey_summary(survey["id"], ADMIN),
            self.ext.create_kb_article("T", "B", ADMIN),
            self.ext.create_cms_page("s", "T", "B", ADMIN),
            self.ext.run_report_definition(definition["id"], ADMIN),
            self.ext.create_ehri_feed_record("2026-06", ADMIN,
                                             learner_refs=["carol"]),
            self.ext.create_authoring_draft("D", ADMIN),
            self.ext.create_form_workflow_record(auth["id"], INSTRUCTOR),
            self.ext.create_execution_record(workflow["id"], INSTRUCTOR),
            self.ext.create_application("cand-1", "prog-1", INSTRUCTOR),
            self.ext.create_career_path("P", INSTRUCTOR),
            self.ext.create_succession_plan("role-1", INSTRUCTOR),
        ]
        for surface in surfaces:
            with self.subTest(surface=surface.get("id", "?")):
                self.assertEqual(_score_keys(surface), set())

    def test_audit_actions_are_ext_prefixed(self):
        self.ext.create_delivery_session("carol", self.course["id"], INSTRUCTOR)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_delivery_session_create", actions)

    def test_auditor_reads_but_cannot_write_extensions(self):
        session = self.ext.create_delivery_session(
            "carol", self.course["id"], INSTRUCTOR)
        self.assertEqual(
            self.ext.get_delivery_session(session["id"], AUDITOR)["id"],
            session["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.create_delivery_session("carol", self.course["id"], AUDITOR)


if __name__ == "__main__":
    unittest.main()
