"""Final GAPS batch tests for Talent Management L2.

Traces to: ``UNION-SPEC.md`` gap list, GAPS.md section "Remainder
Group 3 -- Talent Management L2 (2 forks, new category)", closed
by ``src/talentmgmt/extensions.py`` (``TalentMgmtExtensions``) per
``BATCH.md``. The 7 open entries, by inventory idx (the eighth
entry, idx 646 identity provider / candidate identity
verification, was closed ``re-scoped`` under PLATFORM-LAYER.md
before this unit):

- 639 "Video interview platform" -- reference
- 640 "Assessment delivery & scoring engines" -- reference
- 641 "Predictive I-O models & AI" -- built
- 642 "Virtual event platform" -- built
- 643 "Pipeline automation engine" -- reference
- 644 "Analytics & visualization engines (incl. ROI
  determination)" -- built
- 645 "Talent development programs" -- built

Every test names the entry it pins. Cross-cutting pins, mirroring
the core: privacy is structural (exact key sets for every record
kind, no banned key anywhere, PII-, content-, media-, or
score-shaped keyword arguments raise TypeError); nothing is
scored, ranked, matched, or computed anywhere (a recursive scan
finds no score-shaped key and no float value; predictions,
outcomes, attendance figures, and ROI figures are caller-reported
labels or counts recorded verbatim); derived values are derived
at read and never stored; and the batch's fresh negative control
proves the development module bounds seam load-bearing.
"""

import inspect
import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from talentmgmt.extensions import TalentMgmtExtensions

DEV_MODULES = ["Onboarding Track", "Skills Lab", "Capstone Review"]


def make_extensions():
    """Fresh store + audit + org + candidate + req/pipeline +
    extension surface."""
    store, audit, org = H.make_store()
    H.make_candidate(store, org)
    requisition = H.make_requisition(store, org)
    H.make_pipeline(store, org, requisition)
    return store, audit, org, TalentMgmtExtensions(store)


def make_video_interview(store, org, ref="INT-V"):
    return store.schedule_interview(
        org["id"], ref, H.CANDIDATE_REF, "video", H.MEMBER,
        requisition_id="req-1")


def make_virtual_event(store, org):
    event = store.create_event(
        org["id"], "EVT-V", "Virtual Career Fair", "virtual",
        H.EVENT_START, H.MEMBER, requisition_id="req-1")
    registration = store.register_for_event(
        org["id"], event["id"], "REG-V", H.CANDIDATE_REF, H.MEMBER)
    return event, registration


def make_assessment(store, org):
    return store.record_assessment(
        org["id"], "ASM-1", H.CANDIDATE_REF, "Coding Challenge", H.MEMBER)


def make_dev_program(ext, org, actor=H.MEMBER):
    return ext.create_development_program(
        org["id"], "DVP-1", "New Hire Development", list(DEV_MODULES),
        actor)


def make_dev_enrollment(ext, org, program, actor=H.MEMBER):
    return ext.enroll_in_development_program(
        org["id"], "DVE-1", program["id"], H.CANDIDATE_REF, actor)


class TestVideoSessions(unittest.TestCase):
    """Entry 639: Video interview platform (reference
    implementation)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.interview = make_video_interview(self.store, self.org)

    def test_session_record_is_a_labeled_reference_stub(self):
        """639: a session record binds to the core video interview,
        carries the candidate ref read from it, and is labeled a
        reference stub with nothing streamed, recorded, or held."""
        session = self.ext.register_video_session(
            self.oid, "VID-1", self.interview["id"], H.MEMBER)
        self.assertEqual(session["id"], "vid-1")
        self.assertEqual(session["interview_id"], self.interview["id"])
        self.assertEqual(session["candidate_ref"], H.CANDIDATE_REF)
        self.assertEqual(session["status"], "declared")
        self.assertIsNone(session["outcome_label"])
        self.assertIs(session["reference_stub"], True)
        self.assertIs(session["streamed_here"], False)
        self.assertIs(session["recorded_here"], False)
        self.assertIs(session["media_held_here"], False)

    def test_session_refuses_an_in_person_interview(self):
        """639: the video platform's sessions belong to video
        interviews; binding to an in-person interview is refused
        and consumes no id."""
        in_person = self.store.schedule_interview(
            self.oid, "INT-P", H.CANDIDATE_REF, "in_person", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_video_session(
                self.oid, "VID-1", in_person["id"], H.MEMBER)
        session = self.ext.register_video_session(
            self.oid, "VID-1", self.interview["id"], H.MEMBER)
        self.assertEqual(session["id"], "vid-1")

    def test_session_report_is_a_guarded_transition(self):
        """639: a report stores the caller's outcome label
        verbatim and moves declared -> reported exactly once."""
        session = self.ext.register_video_session(
            self.oid, "VID-1", self.interview["id"], H.MEMBER)
        reported = self.ext.record_video_session_report(
            self.oid, session["id"], "session completed by provider",
            H.MEMBER)
        self.assertEqual(reported["status"], "reported")
        self.assertEqual(reported["outcome_label"],
                         "session completed by provider")
        with self.assertRaises(ValidationError):
            self.ext.record_video_session_report(
                self.oid, session["id"], "again", H.MEMBER)

    def test_session_ref_is_unique_per_org(self):
        """639: caller session references are unique within the
        organization."""
        self.ext.register_video_session(
            self.oid, "VID-1", self.interview["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_video_session(
                self.oid, "VID-1", self.interview["id"], H.MEMBER)


class TestDeliverySessions(unittest.TestCase):
    """Entry 640: Assessment delivery & scoring engines (reference
    implementation)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.assessment = make_assessment(self.store, self.org)

    def test_delivery_record_is_a_labeled_reference_stub(self):
        """640: a delivery record binds to the core assessment and
        is labeled a reference stub: nothing delivered, no
        responses held, nothing computed."""
        delivery = self.ext.register_delivery_session(
            self.oid, "DLV-1", self.assessment["id"], H.MEMBER)
        self.assertEqual(delivery["id"], "dlv-1")
        self.assertEqual(delivery["assessment_id"], self.assessment["id"])
        self.assertEqual(delivery["candidate_ref"], H.CANDIDATE_REF)
        self.assertIs(delivery["reference_stub"], True)
        self.assertIs(delivery["delivered_here"], False)
        self.assertIs(delivery["responses_held_here"], False)
        self.assertIs(delivery["computed_here"], False)

    def test_delivery_report_stores_labels_verbatim(self):
        """640: a delivery report stores the caller's delivery
        outcome label and the assessment outcome label its own
        system produced, both verbatim; the core assessment record
        is never touched."""
        before = self.store.get_assessment(
            self.oid, self.assessment["id"], H.MEMBER)
        delivery = self.ext.register_delivery_session(
            self.oid, "DLV-1", self.assessment["id"], H.MEMBER)
        reported = self.ext.record_delivery_report(
            self.oid, delivery["id"], "delivered by provider",
            "pass per provider rubric", H.MEMBER)
        self.assertEqual(reported["status"], "reported")
        self.assertEqual(reported["delivery_outcome_label"],
                         "delivered by provider")
        self.assertEqual(reported["reported_outcome_label"],
                         "pass per provider rubric")
        after = self.store.get_assessment(
            self.oid, self.assessment["id"], H.MEMBER)
        self.assertEqual(before, after)
        with self.assertRaises(ValidationError):
            self.ext.record_delivery_report(
                self.oid, delivery["id"], "again", "again", H.MEMBER)


class TestPredictions(unittest.TestCase):
    """Entry 641: Predictive I-O models & AI (built as
    caller-reported prediction records)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.assessment = make_assessment(self.store, self.org)
        self.interview = make_video_interview(self.store, self.org)

    def test_model_profile_records_a_reported_validation_label(self):
        """641: a model profile is an opaque model label plus the
        validation status the caller's process reported; nothing
        is validated or run here."""
        profile = self.ext.register_model_profile(
            self.oid, "MDL-1", "Turnover Risk Model v3", H.MEMBER,
            validation_label="validated on 2029 cohort per vendor")
        self.assertEqual(profile["id"], "mdl-1")
        self.assertEqual(profile["validation_label"],
                         "validated on 2029 cohort per vendor")
        self.assertIs(profile["validated_here"], False)
        self.assertIs(profile["inference_here"], False)

    def test_prediction_over_assessment_is_a_reported_label(self):
        """641: a prediction bound to a core assessment stores the
        model's predicted label verbatim, reads the candidate from
        the assessment, and computes nothing."""
        prediction = self.ext.record_prediction(
            self.oid, "PRD-1", "Turnover Risk Model v3",
            "likely to advance", H.MEMBER,
            assessment_id=self.assessment["id"])
        self.assertEqual(prediction["id"], "prd-1")
        self.assertEqual(prediction["candidate_ref"], H.CANDIDATE_REF)
        self.assertEqual(prediction["predicted_label"],
                         "likely to advance")
        self.assertIsNone(prediction["interview_id"])
        self.assertIs(prediction["computed_here"], False)
        self.assertIs(prediction["inference_here"], False)

    def test_prediction_over_interview_is_a_reported_label(self):
        """641: a prediction may bind to a core interview instead;
        the candidate is read from the interview record."""
        prediction = self.ext.record_prediction(
            self.oid, "PRD-1", "Interview Signal Model",
            "strong panel signal per model", H.MEMBER,
            interview_id=self.interview["id"])
        self.assertEqual(prediction["candidate_ref"], H.CANDIDATE_REF)
        self.assertIsNone(prediction["assessment_id"])

    def test_prediction_requires_exactly_one_link(self):
        """641: a prediction must name exactly one core record --
        neither or both is refused, and an unknown link is a
        NotFoundError."""
        with self.assertRaises(ValidationError):
            self.ext.record_prediction(
                self.oid, "PRD-1", "Model", "label", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_prediction(
                self.oid, "PRD-1", "Model", "label", H.MEMBER,
                assessment_id=self.assessment["id"],
                interview_id=self.interview["id"])
        with self.assertRaises(NotFoundError):
            self.ext.record_prediction(
                self.oid, "PRD-1", "Model", "label", H.MEMBER,
                assessment_id="asm-99")


class TestVirtualEvents(unittest.TestCase):
    """Entry 642: Virtual event platform (built as venue,
    attendance-report, and invitation records)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.event, self.registration = make_virtual_event(
            self.store, self.org)

    def test_venue_declaration_binds_to_a_virtual_event(self):
        """642: a venue declaration binds an opaque venue label to
        a core virtual event; the venue is declared, not hosted."""
        venue = self.ext.register_event_venue(
            self.oid, "VEN-1", self.event["id"], "Main Stage Venue",
            H.MEMBER)
        self.assertEqual(venue["id"], "ven-1")
        self.assertEqual(venue["event_id"], self.event["id"])
        self.assertIs(venue["hosted_here"], False)
        self.assertIs(venue["operated_here"], False)

    def test_venue_refuses_in_person_event_and_second_venue(self):
        """642: an in-person event takes no virtual venue, and an
        event carries at most one venue declaration."""
        in_person = self.store.create_event(
            self.oid, "EVT-P", "Onsite Fair", "in_person",
            H.EVENT_START, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_event_venue(
                self.oid, "VEN-1", in_person["id"], "Venue", H.MEMBER)
        self.ext.register_event_venue(
            self.oid, "VEN-1", self.event["id"], "Main Stage", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_event_venue(
                self.oid, "VEN-2", self.event["id"], "Second Stage",
                H.MEMBER)

    def test_attendance_report_is_recorded_as_reported(self):
        """642: an attendance report stores the venue's reported
        counts and outcome label verbatim, and changes nothing in
        the core registry -- no registration is created and no
        registration or event status moves."""
        venue = self.ext.register_event_venue(
            self.oid, "VEN-1", self.event["id"], "Main Stage", H.MEMBER)
        registrations_before = self.store.list_registrations(
            self.oid, self.event["id"], H.MEMBER)
        event_before = self.store.get_event(
            self.oid, self.event["id"], H.MEMBER)
        report = self.ext.record_venue_attendance_report(
            self.oid, "VAR-1", venue["id"], 40, 17,
            "reported by venue platform", H.MEMBER)
        self.assertEqual(report["registered_reported"], 40)
        self.assertEqual(report["checked_in_reported"], 17)
        self.assertIs(report["counted_here"], False)
        self.assertEqual(
            self.store.list_registrations(
                self.oid, self.event["id"], H.MEMBER),
            registrations_before)
        self.assertEqual(
            self.store.get_event(self.oid, self.event["id"], H.MEMBER),
            event_before)

    def test_invitation_is_a_transport_record_never_a_send(self):
        """642: an invitation record for a core registration is
        data for the communications layer (reference_transport
        True, sent_here False), and its outcome is reported
        verbatim under a guarded transition."""
        venue = self.ext.register_event_venue(
            self.oid, "VEN-1", self.event["id"], "Main Stage", H.MEMBER)
        invitation = self.ext.record_event_invitation(
            self.oid, "INV-1", venue["id"], self.registration["id"],
            H.MEMBER)
        self.assertEqual(invitation["candidate_ref"], H.CANDIDATE_REF)
        self.assertIs(invitation["reference_transport"], True)
        self.assertIs(invitation["sent_here"], False)
        reported = self.ext.record_invitation_outcome(
            self.oid, invitation["id"], "delivered per mail system",
            H.MEMBER)
        self.assertEqual(reported["status"], "reported")
        self.assertEqual(reported["outcome_label"],
                         "delivered per mail system")
        with self.assertRaises(ValidationError):
            self.ext.record_invitation_outcome(
                self.oid, invitation["id"], "again", H.MEMBER)

    def test_invitation_requires_a_registration_of_the_event(self):
        """642: an invitation must name a core registration of the
        venue's own event; an unknown registration is a
        NotFoundError, and one registration takes one invitation."""
        venue = self.ext.register_event_venue(
            self.oid, "VEN-1", self.event["id"], "Main Stage", H.MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_event_invitation(
                self.oid, "INV-1", venue["id"], "reg-99", H.MEMBER)
        self.ext.record_event_invitation(
            self.oid, "INV-1", venue["id"], self.registration["id"],
            H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_event_invitation(
                self.oid, "INV-2", venue["id"],
                self.registration["id"], H.MEMBER)


class TestAutomationRuns(unittest.TestCase):
    """Entry 643: Pipeline automation engine (reference
    implementation)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.workflow = self.store.register_workflow(
            self.oid, "WFL-1", "Stage advance automation", H.MEMBER)
        self.placement = self.store.place_candidate(
            self.oid, "pip-1", "PLC-1", H.CANDIDATE_REF, H.MEMBER)

    def test_run_record_is_a_labeled_reference_stub(self):
        """643: a run record binds to a core workflow definition
        and is labeled a reference stub: the core registry never
        executes, and neither does this surface."""
        run = self.ext.register_automation_run(
            self.oid, "RUN-1", self.workflow["id"], H.MEMBER)
        self.assertEqual(run["id"], "run-1")
        self.assertEqual(run["status"], "requested")
        self.assertIs(run["reference_stub"], True)
        self.assertIs(run["executed_here"], False)

    def test_run_requires_a_known_workflow(self):
        """643: a run must name a workflow definition in the core
        registry."""
        with self.assertRaises(NotFoundError):
            self.ext.register_automation_run(
                self.oid, "RUN-1", "wfl-99", H.MEMBER)

    def test_run_report_moves_nothing_in_the_core(self):
        """643: registering and reporting a run changes no core
        placement and creates no core movement record -- reported
        movements are a count on the report, never an action."""
        placement_before = self.store.get_placement(
            self.oid, self.placement["id"], H.MEMBER)
        run = self.ext.register_automation_run(
            self.oid, "RUN-1", self.workflow["id"], H.MEMBER)
        reported = self.ext.record_automation_report(
            self.oid, run["id"], "advance rule applied per vendor",
            H.MEMBER, movements_reported=3)
        self.assertEqual(reported["status"], "reported")
        self.assertEqual(reported["movements_reported"], 3)
        self.assertEqual(
            self.store.get_placement(
                self.oid, self.placement["id"], H.MEMBER),
            placement_before)
        self.assertEqual(
            self.store.list_movements(
                self.oid, self.placement["id"], H.MEMBER), [])
        with self.assertRaises(ValidationError):
            self.ext.record_automation_report(
                self.oid, run["id"], "again", H.MEMBER)


class TestAnalytics(unittest.TestCase):
    """Entry 644: Analytics & visualization engines (incl. ROI
    determination) -- built as definitions, a derived counts
    snapshot, and reported ROI figures."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.assessment = make_assessment(self.store, self.org)

    def test_dashboard_definition_is_data_only(self):
        """644: a dashboard definition holds its metric labels as
        data; nothing is rendered here."""
        dashboard = self.ext.register_dashboard_definition(
            self.oid, "DSH-1", "Pipeline Overview",
            ["placements_by_stage", "assessments_completed"], H.MEMBER)
        self.assertEqual(dashboard["id"], "dsh-1")
        self.assertEqual(dashboard["metric_labels"],
                         ["placements_by_stage", "assessments_completed"])
        self.assertIs(dashboard["definition_only"], True)
        self.assertIs(dashboard["rendered_here"], False)

    def test_snapshot_is_derived_counts_and_tracks_state(self):
        """644: the analytics snapshot is the core registry report
        plus counts over the extension's own records, computed at
        read: it changes as records land, and it computes no
        ratio and determines no ROI."""
        before = self.ext.analytics_snapshot(self.oid, H.MEMBER)
        self.assertEqual(
            before["extension_counts"]["prediction"]["count"], 0)
        self.assertEqual(before["core_report"]["candidate_count"], 1)
        self.assertEqual(len(before["core_report"]), 18)
        self.ext.record_prediction(
            self.oid, "PRD-1", "Model", "label", H.MEMBER,
            assessment_id=self.assessment["id"])
        after = self.ext.analytics_snapshot(self.oid, H.MEMBER)
        self.assertEqual(
            after["extension_counts"]["prediction"]["count"], 1)
        self.assertEqual(
            after["method"],
            "deterministic_counts_over_recorded_quantities")
        self.assertIs(after["ratios_computed_here"], False)
        self.assertIs(after["roi_determined_here"], False)
        self.assertIs(after["rendered_here"], False)

    def test_roi_figure_is_recorded_as_a_reported_label(self):
        """644 (ROI determination): an ROI figure is recorded
        exactly as the caller's analytics reported it -- as a
        verbatim label string. A numeric figure is refused whole:
        computing or normalizing one would pretend a determination
        happened here."""
        report = self.ext.record_roi_report(
            self.oid, "ROI-1", "1.8x as reported by recruiting analytics",
            H.MEMBER, requisition_id="req-1")
        self.assertEqual(report["figure_label"],
                         "1.8x as reported by recruiting analytics")
        self.assertIs(report["determined_here"], False)
        self.assertIs(report["computed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_roi_report(self.oid, "ROI-2", 1.8, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_roi_report(self.oid, "ROI-2", 2, H.MEMBER)


class TestDevelopmentPrograms(unittest.TestCase):
    """Entry 645: Talent development programs (built as program
    definitions, enrollments, milestone check-offs, and sessions
    over candidate refs)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.program = make_dev_program(self.ext, self.org)
        self.enrollment = make_dev_enrollment(
            self.ext, self.org, self.program)

    def test_program_definition_holds_modules_as_data(self):
        """645: a program definition is an ordered module label
        list held as data; no content is held."""
        self.assertEqual(self.program["id"], "dvp-1")
        self.assertEqual(self.program["modules"], DEV_MODULES)
        self.assertIs(self.program["content_held_here"], False)

    def test_enrollment_binds_a_registered_candidate_once(self):
        """645: enrollment binds a candidate of the core registry
        to the program, once per candidate per program; an
        unregistered candidate is refused."""
        self.assertEqual(self.enrollment["id"], "dve-1")
        self.assertEqual(self.enrollment["candidate_ref"],
                         H.CANDIDATE_REF)
        with self.assertRaises(ValidationError):
            self.ext.enroll_in_development_program(
                self.oid, "DVE-2", self.program["id"], H.CANDIDATE_REF,
                H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.enroll_in_development_program(
                self.oid, "DVE-2", self.program["id"],
                "CAN-REF-UNKNOWN", H.MEMBER)

    def test_progress_is_derived_from_milestone_records(self):
        """645: progress is derived at read from milestone
        check-off records (indices, labels, count, completion) and
        is never stored on the enrollment record."""
        self.ext.record_program_milestone(
            self.oid, "DVM-1", self.enrollment["id"], 0, H.MEMBER)
        self.ext.record_program_milestone(
            self.oid, "DVM-2", self.enrollment["id"], 2, H.MEMBER)
        progress = self.ext.development_progress(
            self.oid, self.enrollment["id"], H.MEMBER)
        self.assertEqual(progress["completed_module_indices"], [0, 2])
        self.assertEqual(progress["completed_module_labels"],
                         ["Onboarding Track", "Capstone Review"])
        self.assertEqual(progress["completed_count"], 2)
        self.assertEqual(progress["modules_total"], 3)
        self.assertIs(progress["complete"], False)
        self.ext.record_program_milestone(
            self.oid, "DVM-3", self.enrollment["id"], 1, H.MEMBER)
        progress = self.ext.development_progress(
            self.oid, self.enrollment["id"], H.MEMBER)
        self.assertIs(progress["complete"], True)
        stored = self.ext._records[
            ("development_enrollment", self.enrollment["id"])]
        self.assertEqual(
            set(stored),
            {"id", "org_id", "enrollment_ref", "program_id",
             "candidate_ref", "created_by", "created_utc"})

    def test_session_record_is_metadata_only(self):
        """645: a development session record is metadata (kind
        plus an optional reported outcome label); kinds outside
        the closed set are refused and no content is held."""
        session = self.ext.record_development_session(
            self.oid, "DVS-1", self.enrollment["id"], "coaching",
            H.MEMBER, outcome_label="first session held")
        self.assertEqual(session["id"], "dvs-1")
        self.assertIs(session["content_held_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_development_session(
                self.oid, "DVS-2", self.enrollment["id"], "lecture",
                H.MEMBER)


class MutantTalentMgmtExtensions(TalentMgmtExtensions):
    """Negative-control mutant: the module bounds seam is a no-op."""

    def _check_development_module_bounds(self, program, module_index):
        return None


class TestNegativeControlModuleBounds(unittest.TestCase):
    """Fresh negative control: the module bounds seam (entry 645)
    is load-bearing, not decorative."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.program = make_dev_program(self.ext, self.org)
        self.enrollment = make_dev_enrollment(
            self.ext, self.org, self.program)
        self.mutant = MutantTalentMgmtExtensions(self.store)
        self.mutant_program = make_dev_program(self.mutant, self.org)
        self.mutant_enrollment = make_dev_enrollment(
            self.mutant, self.org, self.mutant_program)

    def test_canonical_expectation_rejects_out_of_bounds_milestone(self):
        """NC: the canonical surface rejects an out-of-bounds
        check-off whole -- nothing recorded, no id consumed."""
        with self.assertRaises(ValidationError):
            self.ext.record_program_milestone(
                self.oid, "DVM-1", self.enrollment["id"],
                len(DEV_MODULES), H.MEMBER)
        self.assertEqual(
            self.ext.list_program_milestones(self.oid, H.MEMBER), [])
        milestone = self.ext.record_program_milestone(
            self.oid, "DVM-1", self.enrollment["id"], 0, H.MEMBER)
        self.assertEqual(milestone["id"], "dvm-1")

    def test_mutant_accepts_and_progress_view_breaks(self):
        """NC: with the seam a no-op, the out-of-bounds check-off
        is stored, and the derived progress view then raises
        IndexError -- the stored index names no module."""
        self.mutant.record_program_milestone(
            self.oid, "DVM-1", self.mutant_enrollment["id"], 99,
            H.MEMBER)
        with self.assertRaises(IndexError):
            self.mutant.development_progress(
                self.oid, self.mutant_enrollment["id"], H.MEMBER)

    def test_treating_mutant_outcome_as_expectation_fails(self):
        """NC: asserting the canonical rejection of the mutant's
        behavior fails -- the divergence is the control working."""
        with self.assertRaises(AssertionError):
            with self.assertRaises(ValidationError):
                self.mutant.record_program_milestone(
                    self.oid, "DVM-1", self.mutant_enrollment["id"], 99,
                    H.MEMBER)


class TestAccessAndAudit(unittest.TestCase):
    """Cross-cutting: the core RBAC matrix and audit log bind the
    extension surface exactly as they bind the core."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.interview = make_video_interview(self.store, self.org)

    def test_viewer_cannot_write_and_denial_is_audited(self):
        """Access: the viewer role holds no write action; a denied
        extension write raises PermissionDenied, changes nothing,
        and is recorded on the core audit log as denied."""
        with self.assertRaises(PermissionDenied):
            self.ext.register_video_session(
                self.oid, "VID-1", self.interview["id"], H.VIEWER)
        self.assertEqual(self.ext.list_video_sessions(self.oid, H.MEMBER),
                         [])
        denied = [e for e in self.audit.entries()
                  if e["action"] == "ext_video_session_register:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")

    def test_outsider_is_blocked_by_the_core_membership_boundary(self):
        """Access: a non-member is refused by the core store's
        organization resolution before any extension record can
        exist."""
        with self.assertRaises(PermissionDenied):
            self.ext.register_video_session(
                self.oid, "VID-1", self.interview["id"], H.OUTSIDER)
        self.assertEqual(self.ext.list_video_sessions(self.oid, H.MEMBER),
                         [])

    def test_extension_mutations_are_audited_with_ext_actions(self):
        """Audit: every successful extension mutation lands on the
        core audit log with an ext_-prefixed action name."""
        session = self.ext.register_video_session(
            self.oid, "VID-1", self.interview["id"], H.MEMBER)
        self.ext.record_video_session_report(
            self.oid, session["id"], "done", H.MEMBER)
        actions = [e["action"] for e in self.audit.entries()
                   if e["target"] == session["id"]]
        self.assertIn("ext_video_session_register", actions)
        self.assertIn("ext_video_session_report", actions)

    def test_viewer_can_read_derived_views(self):
        """Access: the read surface maps onto org_read /
        report_read, which the viewer role holds."""
        snapshot = self.ext.analytics_snapshot(self.oid, H.VIEWER)
        self.assertEqual(snapshot["org_id"], self.oid)
        summary = self.ext.extension_summary(self.oid, H.VIEWER)
        self.assertEqual(summary["video_session_count"], 0)


EXPECTED_SHAPES = {
    "video_session": {
        "id", "org_id", "session_ref", "interview_id", "candidate_ref",
        "status", "outcome_label", "reference_stub", "streamed_here",
        "recorded_here", "media_held_here", "created_by",
        "created_utc"},
    "delivery_session": {
        "id", "org_id", "delivery_ref", "assessment_id",
        "candidate_ref", "status", "delivery_outcome_label",
        "reported_outcome_label", "reference_stub", "delivered_here",
        "responses_held_here", "computed_here", "created_by",
        "created_utc"},
    "model_profile": {
        "id", "org_id", "profile_ref", "model_label",
        "validation_label", "validated_here", "inference_here",
        "created_by", "created_utc"},
    "prediction": {
        "id", "org_id", "prediction_ref", "assessment_id",
        "interview_id", "candidate_ref", "model_label",
        "predicted_label", "computed_here", "inference_here",
        "created_by", "created_utc"},
    "event_venue": {
        "id", "org_id", "venue_ref", "event_id", "venue_label",
        "hosted_here", "operated_here", "created_by", "created_utc"},
    "venue_attendance_report": {
        "id", "org_id", "report_ref", "venue_id", "event_id",
        "registered_reported", "checked_in_reported", "outcome_label",
        "counted_here", "created_by", "created_utc"},
    "event_invitation": {
        "id", "org_id", "invitation_ref", "venue_id", "event_id",
        "registration_id", "candidate_ref", "status", "outcome_label",
        "reference_transport", "sent_here", "created_by",
        "created_utc"},
    "automation_run": {
        "id", "org_id", "run_ref", "workflow_id", "status",
        "outcome_label", "movements_reported", "reference_stub",
        "executed_here", "created_by", "created_utc"},
    "dashboard_definition": {
        "id", "org_id", "dashboard_ref", "label", "metric_labels",
        "definition_only", "rendered_here", "created_by",
        "created_utc"},
    "roi_report": {
        "id", "org_id", "roi_ref", "requisition_id", "figure_label",
        "determined_here", "computed_here", "created_by",
        "created_utc"},
    "development_program": {
        "id", "org_id", "program_ref", "label", "modules",
        "content_held_here", "created_by", "created_utc"},
    "development_enrollment": {
        "id", "org_id", "enrollment_ref", "program_id",
        "candidate_ref", "created_by", "created_utc"},
    "program_milestone": {
        "id", "org_id", "milestone_ref", "enrollment_id",
        "module_index", "created_by", "created_utc"},
    "development_session": {
        "id", "org_id", "session_ref", "enrollment_id", "kind",
        "outcome_label", "content_held_here", "created_by",
        "created_utc"},
}

BANNED_KEYS = {
    "name", "first_name", "last_name", "email", "phone", "ssn",
    "address", "dob", "date_of_birth", "resume", "cv", "score",
    "scores", "rating", "rank", "ranking", "match_score",
    "content", "transcript", "recording", "notes", "gender",
    "race", "ethnicity", "salary",
}

SCORE_KEY_PARTS = ("score", "rating", "rank")


def _walk(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


class TestExtensionShapesAndScans(unittest.TestCase):
    """Cross-cutting: exact shapes, privacy, no score, no float."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        ext = self.ext
        interview = make_video_interview(self.store, self.org)
        session = ext.register_video_session(
            self.oid, "VID-1", interview["id"], H.MEMBER)
        ext.record_video_session_report(
            self.oid, session["id"], "done", H.MEMBER)
        assessment = make_assessment(self.store, self.org)
        delivery = ext.register_delivery_session(
            self.oid, "DLV-1", assessment["id"], H.MEMBER)
        ext.record_delivery_report(
            self.oid, delivery["id"], "delivered", "pass", H.MEMBER)
        ext.register_model_profile(
            self.oid, "MDL-1", "Model", H.MEMBER,
            validation_label="reported")
        ext.record_prediction(
            self.oid, "PRD-1", "Model", "label", H.MEMBER,
            assessment_id=assessment["id"])
        event, registration = make_virtual_event(self.store, self.org)
        venue = ext.register_event_venue(
            self.oid, "VEN-1", event["id"], "Main Stage", H.MEMBER)
        ext.record_venue_attendance_report(
            self.oid, "VAR-1", venue["id"], 5, 3, "reported", H.MEMBER)
        invitation = ext.record_event_invitation(
            self.oid, "INV-1", venue["id"], registration["id"], H.MEMBER)
        ext.record_invitation_outcome(
            self.oid, invitation["id"], "delivered", H.MEMBER)
        workflow = self.store.register_workflow(
            self.oid, "WFL-1", "Automation", H.MEMBER)
        run = ext.register_automation_run(
            self.oid, "RUN-1", workflow["id"], H.MEMBER)
        ext.record_automation_report(
            self.oid, run["id"], "done", H.MEMBER, movements_reported=1)
        ext.register_dashboard_definition(
            self.oid, "DSH-1", "Overview", ["placements_by_stage"],
            H.MEMBER)
        ext.record_roi_report(
            self.oid, "ROI-1", "1.8x as reported", H.MEMBER,
            requisition_id="req-1")
        program = make_dev_program(ext, self.org)
        enrollment = make_dev_enrollment(ext, self.org, program)
        ext.record_program_milestone(
            self.oid, "DVM-1", enrollment["id"], 0, H.MEMBER)
        ext.record_development_session(
            self.oid, "DVS-1", enrollment["id"], "coaching", H.MEMBER,
            outcome_label="held")
        self.enrollment = enrollment

    def _views(self):
        ext, oid = self.ext, self.oid
        return [
            ext.analytics_snapshot(oid, H.MEMBER),
            ext.extension_summary(oid, H.MEMBER),
            ext.development_progress(oid, self.enrollment["id"],
                                     H.MEMBER),
        ]

    def test_every_extension_shape_is_pinned(self):
        """Shapes: each of the fourteen extension record kinds has
        exactly its contracted key set."""
        seen = set()
        for (kind, _id), record in self.ext._records.items():
            seen.add(kind)
            self.assertEqual(set(record), EXPECTED_SHAPES[kind],
                             (kind, record.get("id")))
        self.assertEqual(seen, set(EXPECTED_SHAPES))

    def test_no_banned_or_score_shaped_key_and_no_float(self):
        """Privacy / no-score doctrine: a recursive scan over every
        extension record and derived view finds no identity- or
        score-shaped key and no float value."""
        targets = list(self.ext._records.values()) + self._views()
        for target in targets:
            for key, value in _walk(target):
                lowered = str(key).lower()
                self.assertNotIn(lowered, BANNED_KEYS, (key, target))
                for part in SCORE_KEY_PARTS:
                    self.assertNotIn(part, lowered, (key, target))
                self.assertNotIsInstance(value, float, (key, target))

    def test_smuggled_kwargs_raise_type_error(self):
        """Privacy: extension methods have no parameter that could
        accept a name, an email, media, responses, content, or a
        score -- smuggled keywords raise TypeError."""
        ext, oid = self.ext, self.oid
        interview = make_video_interview(self.store, self.org, "INT-V2")
        with self.assertRaises(TypeError):
            ext.register_video_session(
                oid, "VID-9", interview["id"], H.MEMBER,
                recording="session.mp4")
        with self.assertRaises(TypeError):
            ext.register_delivery_session(
                oid, "DLV-9", "asm-1", H.MEMBER,
                responses=["answer text"])
        with self.assertRaises(TypeError):
            ext.record_prediction(
                oid, "PRD-9", "Model", "label", H.MEMBER,
                assessment_id="asm-1", confidence=0.9)
        with self.assertRaises(TypeError):
            ext.record_event_invitation(
                oid, "INV-9", "ven-1", "reg-1", H.MEMBER,
                email="person@example.invalid")
        with self.assertRaises(TypeError):
            ext.record_roi_report(
                oid, "ROI-9", "label", H.MEMBER, figure=1.8)
        with self.assertRaises(TypeError):
            ext.create_development_program(
                oid, "DVP-9", "X", ["A"], H.MEMBER,
                content="lesson text")

    def test_signatures_carry_no_substance_parameters(self):
        """Privacy: no public extension method signature carries a
        substance-shaped parameter name."""
        for name in dir(TalentMgmtExtensions):
            if name.startswith("_"):
                continue
            method = getattr(TalentMgmtExtensions, name)
            if not callable(method):
                continue
            for parameter in inspect.signature(method).parameters:
                lowered = parameter.lower()
                self.assertNotIn(lowered, BANNED_KEYS, (name, parameter))
                for part in SCORE_KEY_PARTS:
                    self.assertNotIn(part, lowered, (name, parameter))


if __name__ == "__main__":
    unittest.main()
