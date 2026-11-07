"""Final GAPS batch tests -- Untiered Set 11, Health & Wellness.

Pins the extension surface in ``src/health/extensions.py``
(``HealthExtensions``, wrapping the core ``HealthStore``): one
test class per open GAPS.md entry for this set (see ``../BATCH.md``
for the per-entry disposition), plus cross-cutting pins -- the
category's HARD PRIVACY RULE over the whole extension surface
(no diagnosis / clinical-note / identifier-shaped key anywhere,
and forbidden fields cannot be smuggled in), this set's tier-null
discipline (no tier/baseline-shaped key anywhere), stub labels
(``reference_stub: True``) on the EMR, AI/ML, automation, and
hosting records, transport labels (``reference_transport: True``)
on engagement receipts, derived-never-stored values (engagement
counts, survey aggregates, claim current outcome and counts,
navigation step counts, slot booked/remaining counts, therapy
totals, device latest status, analytics), member scope, RBAC
denials audited with a ``:denied`` suffix, and no id consumed by
a failed operation.

Fixtures: ``make_store()`` (program "Diabetes Care", participant
under opaque ref "carol") plus a second participant (ref "erin")
where scope or capacity needs one.
"""

import unittest

from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError
from health.extensions import HealthExtensions


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

    The HARD PRIVACY RULE (no diagnosis, no clinical free text,
    no direct identifier field in any shape) and this set's
    tier-null discipline (no tier/baseline-shaped key).
    """
    privacy = {
        "diagnosis", "note", "notes", "clinical_note", "clinical_notes",
        "name", "email", "phone", "ssn", "dob", "date_of_birth",
        "member_number", "address", "first_name", "last_name",
        "insurer", "insurer_name",
    }
    bad = set()
    for key in _all_keys(obj):
        lowered = key.lower()
        if lowered in privacy:
            bad.add(key)
        elif (lowered in ("tier", "cmmc_tier", "baseline",
                          "fedramp_impact_level")
              or lowered.endswith("_tier")):
            bad.add(key)
    return bad


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.participant = make_store()
        self.ext = HealthExtensions(self.store)
        self.pid = self.participant["id"]
        self.prg = self.program["id"]
        self.other = self.store.create_participant("erin", ADMIN)

    def make_eligibility(self, participant_id=None, plan_ref="plan-ref-1"):
        return self.store.create_eligibility(
            participant_id or self.pid, plan_ref, "2026-01-01", ADMIN)


class TestEngagementChannels(BatchFixture):
    """Entry: Patient engagement channels & content (one claimant
    in this set) -- built as channel/content registry records and
    message receipts; nothing is sent."""

    def test_channel_and_content_shapes(self):
        channel = self.ext.create_engagement_channel(
            "portal-main", "portal_message", ADMIN)
        self.assertEqual(channel["id"], "chn-1")
        self.assertEqual(
            set(channel.keys()),
            {"id", "channel_ref", "kind", "created_by", "created_utc"})
        item = self.ext.create_content_item(
            "content-1", "Welcome", "article", ADMIN, program_id=self.prg)
        self.assertEqual(item["id"], "cnt-1")
        self.assertEqual(item["program_id"], self.prg)

    def test_message_receipt_is_transport_labeled_and_unsent(self):
        channel = self.ext.create_engagement_channel(
            "portal-main", "sms", ADMIN)
        message = self.ext.record_engagement_message(
            self.pid, channel["id"], "content-1", CLINICIAN)
        self.assertEqual(message["id"], "msg-1")
        self.assertIs(message["reference_transport"], True)
        self.assertIs(message["sent_here"], False)
        self.assertEqual(message["state"], "recorded_reference_only")
        self.assertEqual(message["channel_kind"], "sms")

    def test_summary_counts_derived(self):
        channel = self.ext.create_engagement_channel(
            "portal-main", "email_message", ADMIN)
        self.ext.record_engagement_message(
            self.pid, channel["id"], "content-1", CLINICIAN)
        self.ext.record_engagement_message(
            self.pid, channel["id"], "content-2", CLINICIAN)
        summary = self.ext.engagement_summary(self.pid, ADMIN)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["messages"], 2)
        self.assertEqual(summary["by_channel_kind"]["email_message"], 2)
        self.assertEqual(summary["by_channel_kind"]["sms"], 0)

    def test_duplicate_channel_ref_rejected_no_id_consumed(self):
        self.ext.create_engagement_channel("portal-main", "sms", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_engagement_channel("portal-main", "email_message", ADMIN)
        second = self.ext.create_engagement_channel("portal-alt", "email_message",
                                                    ADMIN)
        self.assertEqual(second["id"], "chn-2")

    def test_bad_channel_kind_and_unknown_channel(self):
        with self.assertRaises(ValidationError):
            self.ext.create_engagement_channel("x", "carrier_pigeon", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_engagement_message(
                self.pid, "chn-99", "content-1", CLINICIAN)


class TestSurveyInstruments(BatchFixture):
    """Entry: Survey instruments depth -- built as instrument
    records (questions are opaque references) and numeric-answer
    response records, with derived per-question aggregates."""

    def _instrument(self):
        return self.ext.create_survey_instrument(
            "phq-survey", "Wellness survey", ["q-energy", "q-sleep"], ADMIN)

    def test_instrument_shape(self):
        instrument = self._instrument()
        self.assertEqual(instrument["id"], "svi-1")
        self.assertEqual(instrument["question_refs"], ["q-energy", "q-sleep"])

    def test_response_and_derived_summary(self):
        instrument = self._instrument()
        self.ext.record_survey_response(
            self.pid, instrument["id"],
            [{"question_ref": "q-energy", "value": 3},
             {"question_ref": "q-sleep", "value": 4}],
            CLINICIAN, recorded_on="2026-06-01")
        self.ext.record_survey_response(
            self.other["id"], instrument["id"],
            [{"question_ref": "q-energy", "value": 5}],
            CLINICIAN, recorded_on="2026-06-02")
        summary = self.ext.survey_summary(instrument["id"], ADMIN)
        self.assertEqual(summary["method"], "deterministic_aggregates")
        self.assertEqual(summary["responses"], 2)
        self.assertEqual(summary["per_question"]["q-energy"],
                         {"count": 2, "min": 3, "max": 5, "mean": 4.0})
        self.assertEqual(summary["per_question"]["q-sleep"]["count"], 1)

    def test_answer_for_unknown_question_rejected(self):
        instrument = self._instrument()
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                self.pid, instrument["id"],
                [{"question_ref": "q-unknown", "value": 1}], CLINICIAN)

    def test_non_numeric_answer_rejected(self):
        instrument = self._instrument()
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                self.pid, instrument["id"],
                [{"question_ref": "q-energy", "value": "high"}], CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                self.pid, instrument["id"],
                [{"question_ref": "q-energy", "value": True}], CLINICIAN)


class TestEmrIntegrationStub(BatchFixture):
    """Entry: EMR/EHR integration engines -- stub-engine, shipped
    as labeled reference records; nothing connects."""

    def test_integration_record_is_stub_labeled(self):
        integration = self.ext.create_emr_integration(
            "ehr-main", "ehr", ADMIN)
        self.assertEqual(integration["id"], "emr-1")
        self.assertIs(integration["reference_stub"], True)
        self.assertIs(integration["connected_here"], False)
        self.assertEqual(integration["state"], "recorded_reference_only")

    def test_sync_event_is_reported_count_only(self):
        integration = self.ext.create_emr_integration(
            "ehr-main", "practice_management", ADMIN)
        event = self.ext.record_emr_sync_event(
            integration["id"], "inbound", 12, CLINICIAN,
            recorded_on="2026-06-01")
        self.assertEqual(event["id"], "esy-1")
        self.assertIs(event["reference_stub"], True)
        self.assertEqual(event["record_count"], 12)
        with self.assertRaises(ValidationError):
            self.ext.record_emr_sync_event(
                integration["id"], "sideways", 1, CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_emr_sync_event(
                integration["id"], "inbound", -1, CLINICIAN)


class TestVerificationAndClaims(BatchFixture):
    """Entry: Insurance verification, benefits discovery & claims
    adjudication engines -- built as verification and claim
    RECORDS with outcomes recorded as reported; this build
    adjudicates nothing and pays nothing."""

    def test_verification_check_binds_eligibility(self):
        eligibility = self.make_eligibility()
        check = self.ext.record_verification_check(
            self.pid, eligibility["id"], "verified", ADMIN, "2026-06-01")
        self.assertEqual(check["id"], "vrf-1")
        self.assertIs(check["verified_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_verification_check(
                self.other["id"], eligibility["id"], "verified", ADMIN,
                "2026-06-01")

    def test_claim_record_shape_has_no_amount_or_insurer(self):
        eligibility = self.make_eligibility()
        claim = self.ext.create_claim_record(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-06-01")
        self.assertEqual(
            set(claim.keys()),
            {"id", "participant_id", "eligibility_id", "claim_ref",
             "submitted_on", "adjudicated_here", "paid_here",
             "created_by", "created_utc"})
        self.assertIs(claim["adjudicated_here"], False)
        self.assertIs(claim["paid_here"], False)

    def test_current_outcome_derived_never_stored(self):
        eligibility = self.make_eligibility()
        claim = self.ext.create_claim_record(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-06-01")
        view = self.ext.get_claim_record(claim["id"], ADMIN)
        self.assertIsNone(view["current_outcome"])
        self.assertNotIn("current_outcome", claim)
        self.ext.record_claim_outcome(claim["id"], "pending", ADMIN,
                                      "2026-06-05")
        self.ext.record_claim_outcome(claim["id"], "approved", ADMIN,
                                      "2026-06-09")
        view = self.ext.get_claim_record(claim["id"], ADMIN)
        self.assertEqual(view["current_outcome"], "approved")
        self.assertEqual(view["outcome_count"], 2)

    def test_claims_summary_counts_derived(self):
        eligibility = self.make_eligibility()
        first = self.ext.create_claim_record(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-06-01")
        self.ext.create_claim_record(
            self.pid, eligibility["id"], "claim-ref-2", ADMIN, "2026-06-01")
        self.ext.record_claim_outcome(first["id"], "denied", ADMIN,
                                      "2026-06-05")
        summary = self.ext.claims_summary(ADMIN)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["claims"], 2)
        self.assertEqual(summary["by_current_outcome"]["denied"], 1)
        self.assertEqual(summary["undecided"], 1)


class TestCareCoordination(BatchFixture):
    """Entry: Care coordination & navigation platform depth --
    built as navigation case and step records with derived
    counts; no referral is sent by this substrate."""

    def test_case_and_step_counts_derived(self):
        case = self.ext.create_navigation_case(
            self.pid, "coordinator-7", CLINICIAN, program_id=self.prg)
        self.assertEqual(case["id"], "nav-1")
        view = self.ext.get_navigation_case(case["id"], ADMIN)
        self.assertEqual(view["step_count"], 0)
        self.assertIsNone(view["current_step_kind"])
        self.ext.record_navigation_step(
            case["id"], "referral_recorded", "target-ref-1", CLINICIAN)
        self.ext.record_navigation_step(
            case["id"], "follow_up_recorded", "target-ref-2", CLINICIAN)
        view = self.ext.get_navigation_case(case["id"], ADMIN)
        self.assertEqual(view["step_count"], 2)
        self.assertEqual(view["steps_by_kind"]["referral_recorded"], 1)
        self.assertEqual(view["current_step_kind"], "follow_up_recorded")
        self.assertNotIn("step_count", case)

    def test_bad_step_kind_rejected(self):
        case = self.ext.create_navigation_case(
            self.pid, "coordinator-7", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_navigation_step(
                case["id"], "teleported", "target-ref-1", CLINICIAN)


class TestIntegratedScheduling(BatchFixture):
    """Entry: Integrated scheduling engines -- built as slot
    capacity records and booking records; booked counts are
    derived, and the capacity guard refuses overbooking whole."""

    def _slot(self, capacity=1):
        return self.ext.create_schedule_slot(
            self.prg, "2026-06-01T09:00:00", "2026-06-01T10:00:00",
            capacity, CLINICIAN)

    def test_slot_view_counts_derived_never_stored(self):
        slot = self._slot(capacity=2)
        self.assertNotIn("booked_count", slot)
        self.ext.book_schedule_slot(slot["id"], self.pid, CLINICIAN)
        view = self.ext.get_schedule_slot(slot["id"], ADMIN)
        self.assertEqual(view["booked_count"], 1)
        self.assertEqual(view["remaining_capacity"], 1)

    def test_capacity_guard_refuses_overbooking_no_id_consumed(self):
        slot = self._slot(capacity=1)
        first = self.ext.book_schedule_slot(slot["id"], self.pid, CLINICIAN)
        self.assertEqual(first["id"], "bkg-1")
        with self.assertRaises(ValidationError):
            self.ext.book_schedule_slot(slot["id"], self.other["id"],
                                        CLINICIAN)
        self.ext.cancel_slot_booking(first["id"], CLINICIAN)
        second = self.ext.book_schedule_slot(slot["id"], self.other["id"],
                                             CLINICIAN)
        self.assertEqual(second["id"], "bkg-2")

    def test_duplicate_booking_rejected(self):
        slot = self._slot(capacity=3)
        self.ext.book_schedule_slot(slot["id"], self.pid, CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.book_schedule_slot(slot["id"], self.pid, CLINICIAN)

    def test_capacity_must_be_positive_int(self):
        with self.assertRaises(ValidationError):
            self.ext.create_schedule_slot(
                self.prg, "2026-06-01T09:00:00", "2026-06-01T10:00:00",
                0, CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.create_schedule_slot(
                self.prg, "2026-06-01T09:00:00", "2026-06-01T10:00:00",
                True, CLINICIAN)


class TestCapacityNegativeControl(BatchFixture):
    """Fresh negative control for the batch: the slot-capacity
    guard is load-bearing. The canonical case asserts a booking
    past capacity is refused; the mutant case runs the same flow
    against a subclass whose guard never fires and asserts the
    refusal disappears -- so if the guard were removed or
    neutralised in the real code, the canonical test fails."""

    def test_bookings_up_to_capacity_then_refused_canonical(self):
        slot = self.ext.create_schedule_slot(
            self.prg, "2026-06-01T09:00:00", "2026-06-01T10:00:00",
            1, CLINICIAN)
        self.ext.book_schedule_slot(slot["id"], self.pid, CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.book_schedule_slot(slot["id"], self.other["id"],
                                        CLINICIAN)
        self.assertEqual(
            self.ext.get_schedule_slot(slot["id"], ADMIN)["booked_count"], 1)

    def test_capacity_guard_mutant_would_allow_overbooking(self):
        class MutantExtensions(HealthExtensions):
            def _check_slot_capacity(self, slot, booked_count):
                return None  # guard neutralised

        mutant = MutantExtensions(self.store)
        slot = mutant.create_schedule_slot(
            self.prg, "2026-06-01T09:00:00", "2026-06-01T10:00:00",
            1, CLINICIAN)
        mutant.book_schedule_slot(slot["id"], self.pid, CLINICIAN)
        # Under the mutant the second booking is NOT refused --
        # exactly the outcome the canonical test forbids.
        mutant.book_schedule_slot(slot["id"], self.other["id"], CLINICIAN)
        self.assertEqual(
            mutant.get_schedule_slot(slot["id"], ADMIN)["booked_count"], 2)
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant.get_schedule_slot(slot["id"], ADMIN)["booked_count"],
                1)


class TestTherapySessions(BatchFixture):
    """Entry: At-home therapy delivery & session-metrics
    analytics -- built as session records (integer minutes) with
    a derived totals summary."""

    def test_session_record_and_derived_summary(self):
        first = self.ext.record_therapy_session(
            self.pid, "session-ref-1", 30, CLINICIAN, "2026-06-01",
            program_id=self.prg)
        self.assertEqual(first["id"], "ths-1")
        self.ext.record_therapy_session(
            self.pid, "session-ref-2", 45, CLINICIAN, "2026-06-03")
        summary = self.ext.therapy_summary(self.pid, CLINICIAN)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["sessions"], 2)
        self.assertEqual(summary["total_minutes"], 75)
        self.assertEqual(summary["sessions_by_program"][self.prg], 1)

    def test_duration_must_be_positive_int(self):
        with self.assertRaises(ValidationError):
            self.ext.record_therapy_session(
                self.pid, "s-1", 30.5, CLINICIAN, "2026-06-01")
        with self.assertRaises(ValidationError):
            self.ext.record_therapy_session(
                self.pid, "s-1", True, CLINICIAN, "2026-06-01")
        with self.assertRaises(ValidationError):
            self.ext.record_therapy_session(
                self.pid, "s-1", 0, CLINICIAN, "2026-06-01")


class TestTelehealthVisits(BatchFixture):
    """Entry: Telehealth visit support -- built as visit records
    with a recorded modality label; no media channel exists."""

    def test_visit_record_shape_and_no_media_channel(self):
        visit = self.ext.create_telehealth_visit(
            self.pid, "2026-06-10T15:00:00", "video", CLINICIAN,
            program_id=self.prg, ends_at="2026-06-10T15:30:00")
        self.assertEqual(visit["id"], "tlv-1")
        self.assertEqual(visit["state"], "scheduled")
        self.assertIs(visit["media_channel_here"], False)
        updated = self.ext.set_telehealth_visit_state(
            visit["id"], "completed", CLINICIAN)
        self.assertEqual(updated["state"], "completed")

    def test_bad_modality_and_state_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_telehealth_visit(
                self.pid, "2026-06-10T15:00:00", "hologram", CLINICIAN)
        visit = self.ext.create_telehealth_visit(
            self.pid, "2026-06-10T15:00:00", "audio", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.set_telehealth_visit_state(visit["id"], "vanished",
                                                CLINICIAN)


class TestMeasurementAnalytics(BatchFixture):
    """Entry: Measurement & outcome analytics engines -- built
    as a deterministic derivation over the core measurement
    records; no threshold or interpretation is applied."""

    def test_analytics_derived_from_core_measurements(self):
        self.store.record_measurement(
            self.pid, "resting_heart_rate", 70, "bpm", "2026-06-01",
            CLINICIAN, program_id=self.prg)
        self.store.record_measurement(
            self.pid, "resting_heart_rate", 66, "bpm", "2026-06-03",
            CLINICIAN, program_id=self.prg)
        result = self.ext.measurement_analytics(ADMIN)
        self.assertEqual(result["method"], "deterministic_aggregates")
        self.assertEqual(result["measurements"], 2)
        metric = result["metrics"]["resting_heart_rate"]
        self.assertEqual(metric["count"], 2)
        self.assertEqual(metric["mean"], 68.0)
        self.assertEqual(metric["first_value"], 70)
        self.assertEqual(metric["last_value"], 66)
        self.assertEqual(metric["change_first_to_last"], -4)

    def test_analytics_requires_report_read(self):
        with self.assertRaises(PermissionDenied):
            self.ext.measurement_analytics(MEMBER)


class TestClinicalDecisionSupport(BatchFixture):
    """Entry: Clinical decision support -- built as guideline
    REFERENCE records plus the clinician's own recorded decision
    labels; the build generates no advice of its own."""

    def test_guideline_reference_is_data_never_applied(self):
        guideline = self.ext.create_guideline_reference(
            "guideline-ref-1", "Activity guideline", "topic-activity",
            ADMIN)
        self.assertEqual(guideline["id"], "gdl-1")
        self.assertIs(guideline["applied_here"], False)

    def test_decision_label_recorded_verbatim_no_advice(self):
        guideline = self.ext.create_guideline_reference(
            "guideline-ref-1", "Activity guideline", "topic-activity",
            ADMIN)
        decision = self.ext.record_clinician_decision(
            self.pid, guideline["id"], "continue_current_plan", CLINICIAN,
            "2026-06-05")
        self.assertEqual(decision["id"], "cds-1")
        self.assertEqual(decision["decision_label"], "continue_current_plan")
        self.assertIs(decision["advice_generated_here"], False)
        self.assertEqual(decision["recorded_by_ref"], "bob")


class TestDeviceConnectivity(BatchFixture):
    """Entry: Device connectivity / sync pipelines -- built as
    pairing and sync-status records under opaque device
    references; no data flows through this substrate."""

    def test_link_and_derived_latest_status(self):
        link = self.ext.register_device_link(self.pid, "device-ref-1",
                                             CLINICIAN)
        self.assertEqual(link["id"], "dvl-1")
        self.assertIs(link["data_flows_here"], False)
        view = self.ext.get_device_link(link["id"], ADMIN)
        self.assertIsNone(view["latest_status_label"])
        self.ext.record_sync_status(link["id"], "synced", 14, CLINICIAN,
                                    "2026-06-02")
        self.ext.record_sync_status(link["id"], "pending", 0, CLINICIAN,
                                    "2026-06-03")
        view = self.ext.get_device_link(link["id"], ADMIN)
        self.assertEqual(view["sync_count"], 2)
        self.assertEqual(view["latest_status_label"], "pending")
        self.assertNotIn("latest_status_label", link)

    def test_duplicate_link_rejected(self):
        self.ext.register_device_link(self.pid, "device-ref-1", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.register_device_link(self.pid, "device-ref-1",
                                          CLINICIAN)
        # The same device reference under another participant is a
        # different pairing.
        other_link = self.ext.register_device_link(
            self.other["id"], "device-ref-1", CLINICIAN)
        self.assertEqual(other_link["id"], "dvl-2")


class TestAiMlStub(BatchFixture):
    """Entry: AI/ML models & personalization engines --
    stub-engine: labeled reference records; outputs are held as
    opaque references only, nothing is inferred here."""

    def test_profile_and_output_reference_are_stub_labeled(self):
        profile = self.ext.create_model_profile(
            "model-ref-1", "personalization_model", ADMIN)
        self.assertIs(profile["reference_stub"], True)
        self.assertIs(profile["inference_here"], False)
        self.assertEqual(profile["state"], "recorded_reference_only")
        output = self.ext.record_model_output_reference(
            profile["id"], self.pid, "output-ref-1", CLINICIAN, "2026-06-05")
        self.assertIs(output["reference_stub"], True)
        self.assertEqual(
            set(output.keys()),
            {"id", "profile_id", "participant_id", "output_ref",
             "recorded_on", "reference_stub", "state", "created_by",
             "created_utc"})


class TestAutomationStub(BatchFixture):
    """Entry: Automation / workflow engines -- stub-engine:
    definitions hold step references as data and are never
    executed; runs are recorded as reported."""

    def test_definition_and_run_are_stub_labeled(self):
        definition = self.ext.create_workflow_definition(
            "workflow-ref-1", ["step-a", "step-b"], ADMIN)
        self.assertIs(definition["reference_stub"], True)
        self.assertIs(definition["executed_here"], False)
        self.assertEqual(definition["step_refs"], ["step-a", "step-b"])
        run = self.ext.record_workflow_run_reference(
            definition["id"], self.pid, "completed", CLINICIAN, "2026-06-05")
        self.assertIs(run["reference_stub"], True)
        self.assertIs(run["executed_here"], False)
        self.assertEqual(run["outcome_label"], "completed")


class TestMultiDeviceApps(BatchFixture):
    """Entry: Multi-device native apps -- built as app-access
    registration records (an access surface), with derived
    platform counts; no app is built or tracked here."""

    def test_registration_and_derived_summary(self):
        record = self.ext.register_app_access(
            self.pid, "app-ref-1", "ios", CLINICIAN, "2026-06-01")
        self.assertEqual(record["id"], "app-1")
        self.ext.register_app_access(
            self.other["id"], "app-ref-1", "android", CLINICIAN,
            "2026-06-02")
        summary = self.ext.app_access_summary(ADMIN)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["registrations"], 2)
        self.assertEqual(summary["by_platform"]["ios"], 1)
        self.assertEqual(summary["by_platform"]["android"], 1)
        self.assertEqual(summary["by_platform"]["web"], 0)

    def test_duplicate_registration_rejected(self):
        self.ext.register_app_access(self.pid, "app-ref-1", "ios",
                                     CLINICIAN, "2026-06-01")
        with self.assertRaises(ValidationError):
            self.ext.register_app_access(self.pid, "app-ref-1", "web",
                                         CLINICIAN, "2026-06-02")


class TestHostingStub(BatchFixture):
    """Entry: Hosting platform layer -- stub-engine, per
    PLATFORM-LAYER.md decision 6: posture records hold labels as
    data and the summary states the build's own posture."""

    def test_deployment_record_and_summary(self):
        record = self.ext.create_deployment_record(
            "deployment-ref-1", "vendor-described multi-tenant",
            "vendor-described region", ADMIN)
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["hosted_here"], False)
        self.assertIs(record["multi_tenant_here"], False)
        summary = self.ext.deployment_summary(ADMIN)
        self.assertEqual(summary["records"], 1)
        self.assertEqual(summary["build_tenancy"], "single_tenant_reference")
        self.assertIs(summary["hosted_here"], False)


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins over the whole extension surface."""

    def _exercise_surface(self):
        """Build one of nearly everything and return every value
        the surface hands back."""
        out = []
        channel = self.ext.create_engagement_channel(
            "portal-main", "portal_message", ADMIN)
        out.append(channel)
        out.append(self.ext.create_content_item(
            "content-1", "Welcome", "article", ADMIN, program_id=self.prg))
        out.append(self.ext.record_engagement_message(
            self.pid, channel["id"], "content-1", CLINICIAN))
        out.append(self.ext.engagement_summary(self.pid, ADMIN))
        instrument = self.ext.create_survey_instrument(
            "survey-1", "Survey", ["q-1"], ADMIN)
        out.append(instrument)
        out.append(self.ext.record_survey_response(
            self.pid, instrument["id"],
            [{"question_ref": "q-1", "value": 2}], CLINICIAN))
        out.append(self.ext.survey_summary(instrument["id"], ADMIN))
        integration = self.ext.create_emr_integration("ehr-1", "ehr", ADMIN)
        out.append(integration)
        out.append(self.ext.record_emr_sync_event(
            integration["id"], "inbound", 3, CLINICIAN))
        eligibility = self.make_eligibility()
        out.append(self.ext.record_verification_check(
            self.pid, eligibility["id"], "verified", ADMIN, "2026-06-01"))
        claim = self.ext.create_claim_record(
            self.pid, eligibility["id"], "claim-1", ADMIN, "2026-06-01")
        out.append(claim)
        out.append(self.ext.record_claim_outcome(
            claim["id"], "approved", ADMIN, "2026-06-03"))
        out.append(self.ext.get_claim_record(claim["id"], ADMIN))
        out.append(self.ext.claims_summary(ADMIN))
        case = self.ext.create_navigation_case(
            self.pid, "coordinator-7", CLINICIAN)
        out.append(self.ext.record_navigation_step(
            case["id"], "referral_recorded", "target-1", CLINICIAN))
        out.append(self.ext.get_navigation_case(case["id"], ADMIN))
        slot = self.ext.create_schedule_slot(
            self.prg, "2026-06-01T09:00:00", "2026-06-01T10:00:00", 2,
            CLINICIAN)
        out.append(self.ext.book_schedule_slot(slot["id"], self.pid,
                                               CLINICIAN))
        out.append(self.ext.get_schedule_slot(slot["id"], ADMIN))
        out.append(self.ext.record_therapy_session(
            self.pid, "session-1", 30, CLINICIAN, "2026-06-01"))
        out.append(self.ext.therapy_summary(self.pid, CLINICIAN))
        out.append(self.ext.create_telehealth_visit(
            self.pid, "2026-06-10T15:00:00", "video", CLINICIAN))
        guideline = self.ext.create_guideline_reference(
            "guideline-1", "Guideline", "topic-1", ADMIN)
        out.append(guideline)
        out.append(self.ext.record_clinician_decision(
            self.pid, guideline["id"], "label-1", CLINICIAN, "2026-06-05"))
        link = self.ext.register_device_link(self.pid, "device-1",
                                             CLINICIAN)
        out.append(self.ext.record_sync_status(
            link["id"], "synced", 2, CLINICIAN, "2026-06-02"))
        out.append(self.ext.get_device_link(link["id"], ADMIN))
        profile = self.ext.create_model_profile(
            "model-1", "risk_model", ADMIN)
        out.append(profile)
        out.append(self.ext.record_model_output_reference(
            profile["id"], self.pid, "output-1", CLINICIAN, "2026-06-05"))
        definition = self.ext.create_workflow_definition(
            "workflow-1", ["step-a"], ADMIN)
        out.append(definition)
        out.append(self.ext.record_workflow_run_reference(
            definition["id"], self.pid, "completed", CLINICIAN,
            "2026-06-05"))
        out.append(self.ext.register_app_access(
            self.pid, "app-1", "ios", CLINICIAN, "2026-06-01"))
        out.append(self.ext.app_access_summary(ADMIN))
        out.append(self.ext.create_deployment_record(
            "deployment-1", "label-a", "label-b", ADMIN))
        out.append(self.ext.deployment_summary(ADMIN))
        out.append(self.store.record_measurement(
            self.pid, "metric_a", 5, "units", "2026-06-01", CLINICIAN))
        out.append(self.ext.measurement_analytics(ADMIN))
        return out

    def test_no_privacy_or_tier_key_anywhere_on_surface(self):
        for value in self._exercise_surface():
            self.assertEqual(_banned_keys(value), set())

    def test_forbidden_field_cannot_be_represented(self):
        # An unexpected keyword argument is a TypeError: the
        # shape has no parameter that could carry it.
        with self.assertRaises(TypeError):
            self.ext.create_content_item(
                "content-x", "Title", "article", ADMIN,
                diagnosis="smuggled")
        with self.assertRaises(TypeError):
            self.ext.create_claim_record(
                self.pid, "elg-1", "claim-x", ADMIN, "2026-06-01",
                note="smuggled")
        # A smuggled key inside a survey answer dict is refused
        # with ValidationError and nothing is stored.
        instrument = self.ext.create_survey_instrument(
            "survey-1", "Survey", ["q-1"], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                self.pid, instrument["id"],
                [{"question_ref": "q-1", "value": 1,
                  "diagnosis": "smuggled"}], CLINICIAN)
        self.assertEqual(
            self.ext.list_survey_responses(ADMIN, instrument_id="svi-1"),
            [])

    def test_member_scope_on_extension_records(self):
        visit = self.ext.create_telehealth_visit(
            self.other["id"], "2026-06-10T15:00:00", "video", CLINICIAN)
        with self.assertRaises(PermissionDenied):
            self.ext.get_telehealth_visit(visit["id"], MEMBER)
        self.assertEqual(
            self.ext.list_telehealth_visits(MEMBER, participant_id=None),
            [])
        own = self.ext.create_telehealth_visit(
            self.pid, "2026-06-11T15:00:00", "audio", CLINICIAN)
        self.assertEqual(
            [v["id"] for v in self.ext.list_telehealth_visits(MEMBER)],
            [own["id"]])

    def test_member_write_denied_and_audited(self):
        audit = self.store.audit
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            self.ext.create_engagement_channel("portal-x", "sms", MEMBER)
        entries = audit.entries()[before:]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["action"],
                         "ext_engagement_channel_create:denied")
        self.assertEqual(entries[0]["actor"], "carol")

    def test_auditor_cannot_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_deployment_record("dep-x", "a", "b", AUDITOR)

    def test_extension_mutations_use_ext_prefixed_audit_actions(self):
        self.ext.create_engagement_channel("portal-main", "sms", ADMIN)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_engagement_channel_create", actions)

    def test_unknown_records_raise_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.get_claim_record("clm-99", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.get_schedule_slot("slt-99", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.get_device_link("dvl-99", ADMIN)


if __name__ == "__main__":
    unittest.main()
