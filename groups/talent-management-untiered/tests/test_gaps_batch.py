"""Final GAPS batch tests for the Talent Management untiered set.

Traces to: ``UNION-SPEC.md`` gap list, GAPS.md section "Untiered
Set 21 -- Talent Management (2 forks, tier null)", closed by
``src/talentmgmt/extensions.py`` (``TalentMgmtExtensions``) per
``BATCH.md``. The 8 entries, by inventory idx:

- 935 "Assessment proctoring & integrity services" -- reference
- 936 "Experiential technical learning platform" -- built
- 937 "Integration & API services layer" -- reference
- 938 "Labor exchange platform" -- built
- 939 "Workforce case management system" -- built
- 940 "Employer services platform" -- built
- 941 "Unemployment insurance integration & administration" --
  reference
- 942 "Labor market information service" -- built

Every test names the entry it pins. Cross-cutting pins: tier null
binds the whole extension surface (a recursive scan finds no
tier-shaped key, no float, and no numeric list); privacy is
structural (exact key sets for every record kind, no banned key
anywhere, PII- or content-shaped keyword arguments raise
TypeError); no score is computed anywhere (no score-shaped key,
and matching is recorded as reported labels with
``matched_here`` False); and the batch's fresh negative control
proves the module bounds seam load-bearing.
"""

import inspect
import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from talentmgmt.extensions import TalentMgmtExtensions

MODULES = ["Foundations", "Guided Project", "Capstone"]


def make_extensions():
    """Fresh store + audit + org + candidate + extension surface."""
    store, audit, org = H.make_store()
    H.make_candidate(store, org)
    return store, audit, org, TalentMgmtExtensions(store)


def make_assessment(store, org):
    return store.record_assessment(
        org["id"], "ASM-1", H.CANDIDATE_REF, "Coding Challenge", H.MEMBER)


def make_program(ext, org, actor=H.MEMBER):
    return ext.create_learning_program(
        org["id"], "LRN-1", "Technical Learning", list(MODULES), actor)


def make_enrollment(ext, org, program, actor=H.MEMBER):
    return ext.enroll_candidate(
        org["id"], "ENR-1", program["id"], H.CANDIDATE_REF, actor)


class TestProctoring(unittest.TestCase):
    """Entry 935: Assessment proctoring & integrity services
    (reference implementation)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.assessment = make_assessment(self.store, self.org)

    def test_session_record_shape_and_labels(self):
        """935: a session is a reference record bound to the core
        assessment, carrying the stub labels and holding no
        identity document or session media."""
        session = self.ext.register_proctoring_session(
            self.oid, "PRO-1", self.assessment["id"],
            ["identity_document_check", "session_monitoring"], H.MEMBER)
        self.assertEqual(session["id"], "pro-1")
        self.assertEqual(session["assessment_id"], self.assessment["id"])
        self.assertEqual(session["candidate_ref"], H.CANDIDATE_REF)
        self.assertEqual(session["status"], "requested")
        self.assertIsNone(session["outcome_label"])
        self.assertIs(session["reference_stub"], True)
        self.assertIs(session["adjudicated_here"], False)
        self.assertIs(session["identity_document_held_here"], False)
        self.assertIs(session["session_media_held_here"], False)

    def test_report_is_verbatim_and_terminal(self):
        """935: the service's report is stored verbatim (label and
        reported flag count); a reported session cannot be reported
        again, and nothing is adjudicated here."""
        session = self.ext.register_proctoring_session(
            self.oid, "PRO-1", self.assessment["id"],
            ["integrity_review"], H.MEMBER)
        reported = self.ext.record_proctoring_report(
            self.oid, session["id"], "flagged for review", 2, H.MEMBER)
        self.assertEqual(reported["status"], "reported")
        self.assertEqual(reported["outcome_label"], "flagged for review")
        self.assertEqual(reported["flags_reported"], 2)
        with self.assertRaises(ValidationError):
            self.ext.record_proctoring_report(
                self.oid, session["id"], "clear", 0, H.MEMBER)

    def test_unknown_check_kind_and_unknown_assessment_rejected(self):
        """935: check kinds are a fixed label set, and the session
        must bind to a real core assessment record."""
        with self.assertRaises(ValidationError):
            self.ext.register_proctoring_session(
                self.oid, "PRO-1", self.assessment["id"],
                ["facial_recognition"], H.MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.register_proctoring_session(
                self.oid, "PRO-1", "asm-99",
                ["integrity_review"], H.MEMBER)
        self.assertEqual(
            self.ext.list_proctoring_sessions(self.oid, H.MEMBER), [])

    def test_failed_registration_consumes_no_id(self):
        """935: validation precedes allocation -- a rejected
        registration consumes no id."""
        with self.assertRaises(ValidationError):
            self.ext.register_proctoring_session(
                self.oid, "PRO-1", self.assessment["id"], [], H.MEMBER)
        session = self.ext.register_proctoring_session(
            self.oid, "PRO-1", self.assessment["id"],
            ["session_monitoring"], H.MEMBER)
        self.assertEqual(session["id"], "pro-1")


class TestLearning(unittest.TestCase):
    """Entry 936: Experiential technical learning platform (built)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.program = make_program(self.ext, self.org)
        self.enrollment = make_enrollment(self.ext, self.org, self.program)

    def test_program_is_a_definition_holding_no_content(self):
        """936: a program is an ordered module list held as data;
        no learning content is held here."""
        self.assertEqual(self.program["modules"], MODULES)
        self.assertIs(self.program["content_held_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.create_learning_program(
                self.oid, "LRN-2", "Dup", ["A", "A"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.create_learning_program(
                self.oid, "LRN-2", "Empty", [], H.MEMBER)

    def test_enrollment_binds_registered_candidate_once(self):
        """936: enrollment requires a candidate registered in the
        core registry, and a candidate enrolls once per program."""
        with self.assertRaises(ValidationError):
            self.ext.enroll_candidate(
                self.oid, "ENR-2", self.program["id"], "CAN-REF-404",
                H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.enroll_candidate(
                self.oid, "ENR-2", self.program["id"], H.CANDIDATE_REF,
                H.MEMBER)

    def test_progress_is_derived_from_checkoffs_never_stored(self):
        """936: progress derives at read from completion records;
        the stored enrollment record carries no progress key."""
        self.ext.record_module_completion(
            self.oid, "MOD-1", self.enrollment["id"], 0, H.MEMBER)
        self.ext.record_module_completion(
            self.oid, "MOD-2", self.enrollment["id"], 2, H.MEMBER)
        view = self.ext.learning_progress(
            self.oid, self.enrollment["id"], H.MEMBER)
        self.assertEqual(view["completed_module_indices"], [0, 2])
        self.assertEqual(view["completed_modules"],
                         ["Foundations", "Capstone"])
        self.assertEqual(view["completed_count"], 2)
        self.assertEqual(view["module_count"], 3)
        self.assertIs(view["program_complete"], False)
        stored = self.ext.list_learning_enrollments(self.oid, H.MEMBER)[0]
        self.assertNotIn("completed_count", stored)
        self.assertNotIn("program_complete", stored)
        self.ext.record_module_completion(
            self.oid, "MOD-3", self.enrollment["id"], 1, H.MEMBER)
        view = self.ext.learning_progress(
            self.oid, self.enrollment["id"], H.MEMBER)
        self.assertIs(view["program_complete"], True)

    def test_duplicate_checkoff_rejected(self):
        """936: a module can be checked off once per enrollment."""
        self.ext.record_module_completion(
            self.oid, "MOD-1", self.enrollment["id"], 1, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_module_completion(
                self.oid, "MOD-2", self.enrollment["id"], 1, H.MEMBER)

    def test_module_completion_out_of_bounds_rejected(self):
        """936: a check-off naming no module of the program is
        rejected whole (the bounds seam; drilled separately)."""
        with self.assertRaises(ValidationError):
            self.ext.record_module_completion(
                self.oid, "MOD-1", self.enrollment["id"], len(MODULES),
                H.MEMBER)
        self.assertEqual(
            self.ext.list_module_completions(self.oid, H.MEMBER), [])

    def test_module_completion_negative_and_bool_rejected(self):
        """936: negative and boolean module indices are rejected
        whole -- a negative index never silently names the last
        module."""
        with self.assertRaises(ValidationError):
            self.ext.record_module_completion(
                self.oid, "MOD-1", self.enrollment["id"], -1, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_module_completion(
                self.oid, "MOD-1", self.enrollment["id"], True, H.MEMBER)
        self.assertEqual(
            self.ext.list_module_completions(self.oid, H.MEMBER), [])

    def test_tutor_session_is_metadata_only(self):
        """936: a tutor session record is metadata with a verbatim
        outcome label; no session content is held."""
        session = self.ext.record_tutor_session(
            self.oid, "TUT-1", self.enrollment["id"], "tutoring",
            H.MEMBER, outcome_label="Completed guided project review")
        self.assertEqual(session["kind"], "tutoring")
        self.assertEqual(session["outcome_label"],
                         "Completed guided project review")
        self.assertIs(session["session_content_held_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_tutor_session(
                self.oid, "TUT-2", self.enrollment["id"], "lecture",
                H.MEMBER)


class MutantTalentMgmtExtensions(TalentMgmtExtensions):
    """Negative-control mutant: the module bounds seam is a no-op."""

    def _check_module_bounds(self, program, module_index):
        return None


class TestNegativeControlModuleBounds(unittest.TestCase):
    """Fresh negative control: the module bounds seam (entry 936)
    is load-bearing, not decorative."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.program = make_program(self.ext, self.org)
        self.enrollment = make_enrollment(self.ext, self.org, self.program)
        self.mutant = MutantTalentMgmtExtensions(self.store)
        self.mutant_program = make_program(self.mutant, self.org)
        self.mutant_enrollment = make_enrollment(
            self.mutant, self.org, self.mutant_program)

    def test_canonical_expectation_rejects_out_of_bounds_completion(self):
        """NC: the canonical surface rejects an out-of-bounds
        check-off whole -- nothing recorded, no id consumed."""
        with self.assertRaises(ValidationError):
            self.ext.record_module_completion(
                self.oid, "MOD-1", self.enrollment["id"], len(MODULES),
                H.MEMBER)
        self.assertEqual(
            self.ext.list_module_completions(self.oid, H.MEMBER), [])
        completion = self.ext.record_module_completion(
            self.oid, "MOD-1", self.enrollment["id"], 0, H.MEMBER)
        self.assertEqual(completion["id"], "mod-1")

    def test_mutant_accepts_and_progress_view_breaks(self):
        """NC: with the seam a no-op, the out-of-bounds check-off
        is stored, and the derived progress view then raises
        IndexError -- the stored index names no module."""
        self.mutant.record_module_completion(
            self.oid, "MOD-1", self.mutant_enrollment["id"], 99, H.MEMBER)
        with self.assertRaises(IndexError):
            self.mutant.learning_progress(
                self.oid, self.mutant_enrollment["id"], H.MEMBER)

    def test_treating_mutant_outcome_as_expectation_fails(self):
        """NC: asserting the canonical rejection of the mutant's
        behavior fails -- the divergence is the control working."""
        with self.assertRaises(AssertionError):
            with self.assertRaises(ValidationError):
                self.mutant.record_module_completion(
                    self.oid, "MOD-1", self.mutant_enrollment["id"], 99,
                    H.MEMBER)


class TestIntegrations(unittest.TestCase):
    """Entry 937: Integration & API services layer (reference)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.endpoint = self.ext.register_integration_endpoint(
            self.oid, "IEP-1", "ATS integration", "ats_integration",
            "ATS-EXT-01", "bidirectional", H.MEMBER)

    def test_endpoint_is_a_labeled_definition(self):
        """937: an endpoint is a definition record -- reference
        stub, no credentials held, nothing connected here."""
        self.assertIs(self.endpoint["reference_stub"], True)
        self.assertIs(self.endpoint["credentials_held_here"], False)
        self.assertIs(self.endpoint["connected_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_integration_endpoint(
                self.oid, "IEP-2", "Bad", "carrier_pigeon", "X-1",
                "inbound", H.MEMBER)

    def test_exchange_receipt_is_reported_counts_only(self):
        """937: an exchange receipt stores the connected system's
        reported counts and outcome verbatim; no data moved here."""
        receipt = self.ext.record_integration_exchange(
            self.oid, "IEX-1", self.endpoint["id"], 12, 3,
            "completed with warnings", H.MEMBER)
        self.assertEqual(receipt["records_in_reported"], 12)
        self.assertEqual(receipt["records_out_reported"], 3)
        self.assertEqual(receipt["outcome_label"],
                         "completed with warnings")
        self.assertIs(receipt["reference_transport"], True)
        self.assertIs(receipt["data_moved_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_integration_exchange(
                self.oid, "IEX-2", self.endpoint["id"], -1, 0, "x",
                H.MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_integration_exchange(
                self.oid, "IEX-2", "iep-99", 0, 0, "x", H.MEMBER)


class TestLaborExchange(unittest.TestCase):
    """Entry 938: Labor exchange platform (built)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.posting = self.ext.create_exchange_posting(
            self.oid, "JOB-1", "EMP-REF-001", "Program Analyst", H.MEMBER)

    def test_posting_lifecycle(self):
        """938: postings are exchange records with a guarded
        open -> closed lifecycle."""
        self.assertEqual(self.posting["status"], "open")
        closed = self.ext.close_exchange_posting(
            self.oid, self.posting["id"], H.MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.ext.close_exchange_posting(
                self.oid, self.posting["id"], H.MEMBER)

    def test_match_is_reported_never_computed(self):
        """938: a match record is a reported pairing with a
        verbatim outcome label -- matched_here is False, there is
        no score, and one record exists per posting/candidate."""
        match = self.ext.record_exchange_match(
            self.oid, "MAT-1", self.posting["id"], H.CANDIDATE_REF,
            "referred to employer", H.MEMBER)
        self.assertIs(match["matched_here"], False)
        self.assertEqual(match["outcome_label"], "referred to employer")
        with self.assertRaises(ValidationError):
            self.ext.record_exchange_match(
                self.oid, "MAT-2", self.posting["id"], H.CANDIDATE_REF,
                "referred again", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_exchange_match(
                self.oid, "MAT-2", self.posting["id"], "CAN-REF-404",
                "referred", H.MEMBER)

    def test_summary_is_derived_counts_only(self):
        """938: the exchange summary is deterministic counts
        derived at read from the posting and match records."""
        self.ext.record_exchange_match(
            self.oid, "MAT-1", self.posting["id"], H.CANDIDATE_REF,
            "referred to employer", H.MEMBER)
        summary = self.ext.exchange_summary(self.oid, H.MEMBER)
        self.assertEqual(summary["posting_count"], 1)
        self.assertEqual(summary["postings_by_status"],
                         {"open": 1, "closed": 0})
        self.assertEqual(summary["match_count"], 1)
        self.assertEqual(summary["matches_by_outcome"],
                         {"referred to employer": 1})
        self.assertEqual(summary["matched_candidate_count"], 1)


class TestWorkforceCases(unittest.TestCase):
    """Entry 939: Workforce case management system (built)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.case = self.ext.create_workforce_case(
            self.oid, "CAS-1", H.CANDIDATE_REF, "Workforce Program A",
            H.MEMBER)

    def test_case_binds_opaque_participant(self):
        """939: a case binds a registered candidate reference and
        a program label; unknown participants are rejected."""
        self.assertEqual(self.case["candidate_ref"], H.CANDIDATE_REF)
        self.assertEqual(self.case["status"], "open")
        with self.assertRaises(ValidationError):
            self.ext.create_workforce_case(
                self.oid, "CAS-2", "CAN-REF-404", "Program B", H.MEMBER)

    def test_activities_are_labels_and_counts_derive_at_read(self):
        """939: activities are kind + label records; the case
        view's counts derive at read and are never stored."""
        self.ext.record_case_activity(
            self.oid, "ACT-1", self.case["id"], "intake",
            "Initial intake recorded", H.MEMBER)
        self.ext.record_case_activity(
            self.oid, "ACT-2", self.case["id"], "referral",
            "Referred to training provider", H.MEMBER)
        self.ext.record_case_activity(
            self.oid, "ACT-3", self.case["id"], "follow_up",
            "Two-week follow-up", H.MEMBER)
        view = self.ext.get_workforce_case(self.oid, self.case["id"],
                                           H.MEMBER)
        self.assertEqual(view["activity_count"], 3)
        self.assertEqual(view["activities_by_kind"],
                         {"intake": 1, "referral": 1, "follow_up": 1})
        stored = self.ext.list_workforce_cases(self.oid, H.MEMBER)[0]
        self.assertNotIn("activity_count", stored)
        self.assertNotIn("activities_by_kind", stored)
        with self.assertRaises(ValidationError):
            self.ext.record_case_activity(
                self.oid, "ACT-4", self.case["id"], "home_visit",
                "x", H.MEMBER)

    def test_closed_case_takes_no_new_activities(self):
        """939: case lifecycle is guarded -- a closed case records
        no further activities and cannot be closed twice."""
        self.ext.close_workforce_case(self.oid, self.case["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_case_activity(
                self.oid, "ACT-1", self.case["id"], "intake", "x",
                H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.close_workforce_case(self.oid, self.case["id"],
                                          H.MEMBER)


class TestEmployerServices(unittest.TestCase):
    """Entry 940: Employer services platform (built)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.employer = self.ext.register_employer(
            self.oid, "EMP-REF-001", "Employer One", H.MEMBER)

    def test_employer_registry_and_request_lifecycle(self):
        """940: employers are opaque references; service requests
        carry a kind label and a guarded lifecycle ending in a
        verbatim outcome label."""
        request = self.ext.create_service_request(
            self.oid, "ESR-1", self.employer["id"], "job_order", H.MEMBER)
        self.assertEqual(request["status"], "open")
        self.assertIsNone(request["outcome_label"])
        completed = self.ext.complete_service_request(
            self.oid, request["id"], "Job order posted", H.MEMBER)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["outcome_label"], "Job order posted")
        with self.assertRaises(ValidationError):
            self.ext.cancel_service_request(self.oid, request["id"],
                                            H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.create_service_request(
                self.oid, "ESR-2", self.employer["id"], "catering",
                H.MEMBER)

    def test_summary_is_derived_counts(self):
        """940: the employer-services summary is deterministic
        counts derived at read, by kind and by status."""
        first = self.ext.create_service_request(
            self.oid, "ESR-1", self.employer["id"], "job_order", H.MEMBER)
        self.ext.create_service_request(
            self.oid, "ESR-2", self.employer["id"],
            "recruitment_assistance", H.MEMBER)
        self.ext.complete_service_request(
            self.oid, first["id"], "done", H.MEMBER)
        summary = self.ext.employer_services_summary(self.oid, H.MEMBER)
        self.assertEqual(summary["employer_count"], 1)
        self.assertEqual(summary["service_request_count"], 2)
        self.assertEqual(summary["service_requests_by_kind"],
                         {"job_order": 1, "recruitment_assistance": 1})
        self.assertEqual(summary["service_requests_by_status"],
                         {"open": 1, "completed": 1, "cancelled": 0})


class TestUnemploymentInsurance(unittest.TestCase):
    """Entry 941: Unemployment insurance integration &
    administration (reference implementation)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.claim = self.ext.register_ui_claim(
            self.oid, "UIC-1", H.CANDIDATE_REF, "pending review", H.MEMBER)

    def test_claim_is_a_labeled_reference_record(self):
        """941: a claim record carries the program's reported
        status label and the stub labels -- nothing is determined
        or paid here."""
        self.assertIs(self.claim["reference_stub"], True)
        self.assertIs(self.claim["determined_here"], False)
        self.assertIs(self.claim["benefits_paid_here"], False)
        view = self.ext.get_ui_claim(self.oid, self.claim["id"], H.MEMBER)
        self.assertEqual(view["current_reported_status"], "pending review")
        self.assertEqual(view["report_count"], 0)

    def test_current_status_derives_from_newest_report(self):
        """941: status reports are append-only records; the
        claim's current reported status derives at read from the
        newest one and is never stored on the claim."""
        self.ext.record_ui_claim_report(
            self.oid, "UIR-1", self.claim["id"], "under adjudication",
            H.MEMBER)
        self.ext.record_ui_claim_report(
            self.oid, "UIR-2", self.claim["id"], "approved by program",
            H.MEMBER)
        view = self.ext.get_ui_claim(self.oid, self.claim["id"], H.MEMBER)
        self.assertEqual(view["current_reported_status"],
                         "approved by program")
        self.assertEqual(view["report_count"], 2)
        stored = self.ext.list_ui_claims(self.oid, H.MEMBER)[0]
        self.assertNotIn("current_reported_status", stored)
        self.assertNotIn("report_count", stored)
        self.assertEqual(stored["initial_status_label"], "pending review")

    def test_exchange_receipt_moves_nothing(self):
        """941: a UI exchange receipt stores reported counts
        verbatim and administers nothing here."""
        receipt = self.ext.record_ui_exchange(
            self.oid, "UIE-1", "UI-PROGRAM-SYSTEM", 40, 17,
            "batch accepted", H.MEMBER)
        self.assertEqual(receipt["claims_reported"], 40)
        self.assertEqual(receipt["determinations_reported"], 17)
        self.assertIs(receipt["reference_stub"], True)
        self.assertIs(receipt["reference_transport"], True)
        self.assertIs(receipt["administered_here"], False)


class TestLaborMarketInformation(unittest.TestCase):
    """Entry 942: Labor market information service (built)."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]

    def _observe(self, ref, value, region="Region A",
                 occupation="Analysts", period="2030-Q1",
                 metric="job_openings"):
        return self.ext.record_lmi_observation(
            self.oid, ref, region, occupation, period, metric, value,
            "LMI-SOURCE-01", H.MEMBER)

    def test_observation_is_a_reported_value(self):
        """942: an observation stores the source's integer value
        verbatim; nothing is collected here, and floats and
        negative values are rejected at the boundary."""
        observation = self._observe("LMI-1", 120)
        self.assertEqual(observation["value_reported"], 120)
        self.assertIs(observation["collected_here"], False)
        with self.assertRaises(ValidationError):
            self._observe("LMI-2", -1)
        with self.assertRaises(ValidationError):
            self._observe("LMI-2", 12.5)
        with self.assertRaises(ValidationError):
            self._observe("LMI-2", True)

    def test_summary_groups_and_sums_reported_values(self):
        """942: the summary is a deterministic grouping derived at
        read -- observation counts and sums of reported values per
        (region, occupation, period, metric); no average or rate."""
        self._observe("LMI-1", 120)
        self._observe("LMI-2", 30)
        self._observe("LMI-3", 7, metric="unemployed")
        summary = self.ext.lmi_summary(self.oid, H.MEMBER)
        self.assertEqual(summary["observation_count"], 3)
        groups = {(g["metric_kind"]): g for g in summary["groups"]}
        self.assertEqual(groups["job_openings"]["observation_count"], 2)
        self.assertEqual(groups["job_openings"]["value_total_reported"],
                         150)
        self.assertEqual(groups["unemployed"]["value_total_reported"], 7)

    def test_publication_is_a_definition_and_distribution_a_receipt(self):
        """942: a publication is a definition held as data that
        delivers nothing; a distribution receipt is reported
        counts with reference_transport True."""
        publication = self.ext.create_lmi_publication(
            self.oid, "PUB-1", "Quarterly Outlook", H.MEMBER,
            region_label="Region A", metric_kind="job_openings")
        self.assertIs(publication["definition_only"], True)
        self.assertIs(publication["delivered_here"], False)
        receipt = self.ext.record_lmi_distribution(
            self.oid, "DST-1", publication["id"], 250, "distributed",
            H.MEMBER)
        self.assertEqual(receipt["recipients_reported"], 250)
        self.assertIs(receipt["reference_transport"], True)
        self.assertIs(receipt["delivered_here"], False)


class TestExtensionAccess(unittest.TestCase):
    """Cross-cutting: the extension rides the core's RBAC matrix
    and membership boundary, and audits through the core log."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        self.assessment = make_assessment(self.store, self.org)

    def test_viewer_write_denied_and_audited(self):
        """Access: a viewer (org member, read-only role) attempting
        an extension write is denied, the denial is audited with a
        :denied suffix, and nothing is recorded."""
        with self.assertRaises(PermissionDenied):
            self.ext.register_proctoring_session(
                self.oid, "PRO-1", self.assessment["id"],
                ["integrity_review"], H.VIEWER)
        self.assertEqual(
            self.ext.list_proctoring_sessions(self.oid, H.MEMBER), [])
        denied = [e for e in self.audit.entries()
                  if e["action"] == "ext_proctoring_register:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")

    def test_outsider_denied_by_membership_boundary(self):
        """Access: a platform member who is not an organization
        member is denied by the core's membership boundary."""
        with self.assertRaises(PermissionDenied):
            self.ext.create_learning_program(
                self.oid, "LRN-1", "Nope", ["A"], H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.list_learning_programs(self.oid, H.OUTSIDER)

    def test_successful_mutations_are_audited_with_ext_prefix(self):
        """Access: successful extension mutations land on the core
        audit log with ext_-prefixed action names."""
        session = self.ext.register_proctoring_session(
            self.oid, "PRO-1", self.assessment["id"],
            ["integrity_review"], H.MEMBER)
        actions = [e["action"] for e in self.audit.entries()
                   if e["target"] == session["id"]]
        self.assertIn("ext_proctoring_register", actions)

    def test_viewer_can_read_records_and_summaries(self):
        """Access: the read surface maps onto org_read /
        report_read, which the viewer role holds."""
        self.ext.create_exchange_posting(
            self.oid, "JOB-1", "EMP-REF-001", "Analyst", H.MEMBER)
        self.assertEqual(
            len(self.ext.list_exchange_postings(self.oid, H.VIEWER)), 1)
        summary = self.ext.exchange_summary(self.oid, H.VIEWER)
        self.assertEqual(summary["posting_count"], 1)


EXPECTED_SHAPES = {
    "proctoring_session": {
        "id", "org_id", "session_ref", "assessment_id", "candidate_ref",
        "check_kinds", "status", "outcome_label", "flags_reported",
        "reference_stub", "adjudicated_here",
        "identity_document_held_here", "session_media_held_here",
        "created_by", "created_utc"},
    "learning_program": {
        "id", "org_id", "program_ref", "label", "modules",
        "content_held_here", "created_by", "created_utc"},
    "learning_enrollment": {
        "id", "org_id", "enrollment_ref", "program_id", "candidate_ref",
        "created_by", "created_utc"},
    "module_completion": {
        "id", "org_id", "completion_ref", "enrollment_id", "module_index",
        "created_by", "created_utc"},
    "tutor_session": {
        "id", "org_id", "tutor_session_ref", "enrollment_id", "kind",
        "outcome_label", "session_content_held_here", "created_by",
        "created_utc"},
    "integration_endpoint": {
        "id", "org_id", "endpoint_ref", "label", "kind", "system_ref",
        "direction", "reference_stub", "credentials_held_here",
        "connected_here", "created_by", "created_utc"},
    "integration_exchange": {
        "id", "org_id", "exchange_ref", "endpoint_id",
        "records_in_reported", "records_out_reported", "outcome_label",
        "reference_transport", "data_moved_here", "created_by",
        "created_utc"},
    "exchange_posting": {
        "id", "org_id", "posting_ref", "employer_ref", "title", "status",
        "created_by", "created_utc"},
    "exchange_match": {
        "id", "org_id", "match_ref", "posting_id", "candidate_ref",
        "outcome_label", "matched_here", "created_by", "created_utc"},
    "workforce_case": {
        "id", "org_id", "case_ref", "candidate_ref", "program_label",
        "status", "created_by", "created_utc"},
    "case_activity": {
        "id", "org_id", "activity_ref", "case_id", "kind", "label",
        "created_by", "created_utc"},
    "employer": {
        "id", "org_id", "employer_ref", "label", "created_by",
        "created_utc"},
    "employer_service_request": {
        "id", "org_id", "request_ref", "employer_id", "kind", "status",
        "outcome_label", "created_by", "created_utc"},
    "ui_claim": {
        "id", "org_id", "claim_ref", "candidate_ref",
        "initial_status_label", "reference_stub", "determined_here",
        "benefits_paid_here", "created_by", "created_utc"},
    "ui_claim_report": {
        "id", "org_id", "report_ref", "claim_id", "reported_status_label",
        "reference_stub", "created_by", "created_utc"},
    "ui_exchange": {
        "id", "org_id", "exchange_ref", "system_ref", "claims_reported",
        "determinations_reported", "outcome_label", "reference_stub",
        "reference_transport", "administered_here", "created_by",
        "created_utc"},
    "lmi_observation": {
        "id", "org_id", "observation_ref", "region_label",
        "occupation_label", "period_label", "metric_kind",
        "value_reported", "source_ref", "collected_here", "created_by",
        "created_utc"},
    "lmi_publication": {
        "id", "org_id", "publication_ref", "label", "region_label",
        "metric_kind", "definition_only", "delivered_here", "created_by",
        "created_utc"},
    "lmi_distribution": {
        "id", "org_id", "distribution_ref", "publication_id",
        "recipients_reported", "outcome_label", "reference_transport",
        "delivered_here", "created_by", "created_utc"},
}

BANNED_KEYS = {
    "name", "first_name", "last_name", "email", "phone", "ssn",
    "address", "dob", "date_of_birth", "resume", "cv", "score",
    "scores", "rating", "rank", "ranking", "match_score",
    "content", "transcript", "recording", "notes", "gender",
    "race", "ethnicity", "salary",
}

TIER_KEY_PARTS = ("tier", "cmmc", "baseline", "equivalence",
                  "impact_level")
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
    """Cross-cutting: exact shapes, tier null, privacy, no score."""

    def setUp(self):
        self.store, self.audit, self.org, self.ext = make_extensions()
        self.oid = self.org["id"]
        assessment = make_assessment(self.store, self.org)
        ext = self.ext
        session = ext.register_proctoring_session(
            self.oid, "PRO-1", assessment["id"],
            ["identity_document_check"], H.MEMBER)
        ext.record_proctoring_report(self.oid, session["id"], "clear", 0,
                                     H.MEMBER)
        program = make_program(ext, self.org)
        enrollment = make_enrollment(ext, self.org, program)
        ext.record_module_completion(self.oid, "MOD-1", enrollment["id"],
                                     0, H.MEMBER)
        ext.record_tutor_session(self.oid, "TUT-1", enrollment["id"],
                                 "tutoring", H.MEMBER,
                                 outcome_label="done")
        endpoint = ext.register_integration_endpoint(
            self.oid, "IEP-1", "ATS", "ats_integration", "ATS-1",
            "inbound", H.MEMBER)
        ext.record_integration_exchange(self.oid, "IEX-1", endpoint["id"],
                                        1, 2, "ok", H.MEMBER)
        posting = ext.create_exchange_posting(
            self.oid, "JOB-1", "EMP-REF-001", "Analyst", H.MEMBER)
        ext.record_exchange_match(self.oid, "MAT-1", posting["id"],
                                  H.CANDIDATE_REF, "referred", H.MEMBER)
        case = ext.create_workforce_case(
            self.oid, "CAS-1", H.CANDIDATE_REF, "Program A", H.MEMBER)
        ext.record_case_activity(self.oid, "ACT-1", case["id"], "intake",
                                 "Intake", H.MEMBER)
        employer = ext.register_employer(self.oid, "EMP-REF-001",
                                         "Employer One", H.MEMBER)
        ext.create_service_request(self.oid, "ESR-1", employer["id"],
                                   "job_order", H.MEMBER)
        claim = ext.register_ui_claim(self.oid, "UIC-1", H.CANDIDATE_REF,
                                      "pending", H.MEMBER)
        ext.record_ui_claim_report(self.oid, "UIR-1", claim["id"],
                                   "approved by program", H.MEMBER)
        ext.record_ui_exchange(self.oid, "UIE-1", "UI-SYS", 3, 1, "ok",
                               H.MEMBER)
        ext.record_lmi_observation(self.oid, "LMI-1", "Region A",
                                   "Analysts", "2030-Q1", "job_openings",
                                   10, "SRC-1", H.MEMBER)
        publication = ext.create_lmi_publication(
            self.oid, "PUB-1", "Outlook", H.MEMBER)
        ext.record_lmi_distribution(self.oid, "DST-1", publication["id"],
                                    5, "distributed", H.MEMBER)
        self.enrollment = enrollment
        self.case = case
        self.claim = claim

    def _views(self):
        ext, oid = self.ext, self.oid
        return [
            ext.learning_progress(oid, self.enrollment["id"], H.MEMBER),
            ext.get_workforce_case(oid, self.case["id"], H.MEMBER),
            ext.get_ui_claim(oid, self.claim["id"], H.MEMBER),
            ext.exchange_summary(oid, H.MEMBER),
            ext.employer_services_summary(oid, H.MEMBER),
            ext.lmi_summary(oid, H.MEMBER),
        ]

    def test_every_extension_shape_is_pinned(self):
        """Shapes: each of the nineteen extension record kinds has
        exactly its contracted key set."""
        seen = set()
        for (kind, _id), record in self.ext._records.items():
            seen.add(kind)
            self.assertEqual(set(record), EXPECTED_SHAPES[kind],
                             (kind, record.get("id")))
        self.assertEqual(seen, set(EXPECTED_SHAPES))

    def test_no_tier_shaped_key_no_float_no_numeric_list(self):
        """Tier null: a recursive scan over every extension record
        and derived view finds no tier/baseline/equivalence key
        and no float value; a scan over the stored records
        additionally finds no numeric list (a stored list of
        numbers could be a vector value -- the progress view's
        module-index list is a derivation over the program's own
        labels, not a stored value)."""
        targets = list(self.ext._records.values()) + self._views()
        for target in targets:
            for key, value in _walk(target):
                lowered = str(key).lower()
                for part in TIER_KEY_PARTS:
                    self.assertNotIn(part, lowered, (key, target))
                self.assertNotIsInstance(value, float, (key, target))
        for record in self.ext._records.values():
            for key, value in _walk(record):
                if isinstance(value, list):
                    for item in value:
                        self.assertNotIsInstance(
                            item, (int, float), (key, record))

    def test_no_banned_or_score_shaped_key_anywhere(self):
        """Privacy / no-score doctrine: a recursive scan over every
        extension record and derived view finds no identity- or
        score-shaped key."""
        targets = list(self.ext._records.values()) + self._views()
        for target in targets:
            for key, _value in _walk(target):
                lowered = str(key).lower()
                self.assertNotIn(lowered, BANNED_KEYS, (key, target))
                for part in SCORE_KEY_PARTS:
                    self.assertNotIn(part, lowered, (key, target))

    def test_smuggled_kwargs_raise_type_error(self):
        """Privacy: extension methods have no parameter that could
        accept a name, an email, a document image, session media,
        a note's text, or a score -- smuggled keywords raise
        TypeError."""
        ext, oid = self.ext, self.oid
        assessment = self.store.record_assessment(
            oid, "ASM-9", H.CANDIDATE_REF, "Second Instrument", H.MEMBER)
        with self.assertRaises(TypeError):
            ext.register_proctoring_session(
                oid, "PRO-9", assessment["id"], ["integrity_review"],
                H.MEMBER, document_image="...")
        with self.assertRaises(TypeError):
            ext.register_proctoring_session(
                oid, "PRO-9", assessment["id"], ["integrity_review"],
                H.MEMBER, session_video="...")
        with self.assertRaises(TypeError):
            ext.register_ui_claim(oid, "UIC-9", H.CANDIDATE_REF,
                                  "pending", H.MEMBER,
                                  email="person@example.invalid")
        with self.assertRaises(TypeError):
            ext.record_exchange_match(
                oid, "MAT-9", "job-1", H.CANDIDATE_REF, "referred",
                H.MEMBER, match_score=85)
        with self.assertRaises(TypeError):
            ext.record_case_activity(
                oid, "ACT-9", self.case["id"], "intake", "Intake",
                H.MEMBER, notes="narrative text")
        with self.assertRaises(TypeError):
            ext.create_learning_program(
                oid, "LRN-9", "X", ["A"], H.MEMBER, content="lesson text")

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
