"""Final GAPS batch tests -- Group 18, Health & Wellness L2.

Pins the extension surface in ``src/health/extensions.py``
(``HealthExtensions``, wrapping the core ``HealthStore``): one
test class per open GAPS.md entry for this group (see ``../BATCH.md``
for the per-entry disposition), plus cross-cutting pins -- the
category's HARD PRIVACY RULE over the whole extension surface
(no diagnosis / clinical-note / identifier-shaped key anywhere,
and forbidden fields cannot be smuggled in), stub labels
(``reference_stub: True``) on the EMR, AI/ML, automation, and
hosting records, transport labels (``reference_transport: True``)
on engagement receipts, derived-never-stored values (engagement
counts, survey aggregates, claim current outcome and counts,
device latest status, app-access counts), member scope, RBAC
denials audited with a ``:denied`` suffix, no id consumed by a
failed operation, and the batch unit's mutation-verified negative
control: the eligibility-ownership seam
``_check_eligibility_belongs``, without which a verification
check or claim record could bind to ANOTHER participant's
eligibility record.

Fixtures: ``make_store()`` (program "Diabetes Care", participant
under opaque ref "carol") plus a second participant (ref "erin")
where scope or ownership needs one.
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
    """Keys that would break the founding privacy invariant.

    The HARD PRIVACY RULE: no diagnosis, no clinical free text,
    no direct identifier field in any shape.
    """
    privacy = {
        "diagnosis", "note", "notes", "clinical_note", "clinical_notes",
        "name", "email", "phone", "ssn", "dob", "date_of_birth",
        "member_number", "address", "first_name", "last_name",
        "insurer", "insurer_name",
    }
    return {key for key in _all_keys(obj) if key.lower() in privacy}


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
    """Entry: Patient engagement channels & content (2 of 5;
    care guidance 1 of 5) -- built as channel/content registry
    records and message receipts; nothing is sent."""

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

    def test_member_scope_on_messages_and_summary(self):
        channel = self.ext.create_engagement_channel(
            "portal-main", "sms", ADMIN)
        self.ext.record_engagement_message(
            self.pid, channel["id"], "content-1", CLINICIAN)
        self.ext.record_engagement_message(
            self.other["id"], channel["id"], "content-1", CLINICIAN)
        own = self.ext.list_engagement_messages(MEMBER)
        self.assertEqual(len(own), 1)
        self.assertEqual(own[0]["participant_id"], self.pid)
        with self.assertRaises(PermissionDenied):
            self.ext.engagement_summary(self.other["id"], MEMBER)


class TestSurveyInstruments(BatchFixture):
    """Entry: Survey instruments depth (within patient engagement,
    2 of 5) -- built as instruments with opaque question refs and
    numeric-only responses with derived aggregates."""

    def _instrument(self):
        return self.ext.create_survey_instrument(
            "phq-mini", "Wellbeing check", ["q-mood", "q-sleep"], ADMIN)

    def test_instrument_shape_and_duplicate_refs_rejected(self):
        instrument = self._instrument()
        self.assertEqual(instrument["id"], "svi-1")
        self.assertEqual(
            set(instrument.keys()),
            {"id", "instrument_ref", "title", "question_refs",
             "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.create_survey_instrument(
                "dup", "Dup", ["q-a", "q-a"], ADMIN)

    def test_response_and_summary_aggregates(self):
        instrument = self._instrument()
        self.ext.record_survey_response(
            self.pid, instrument["id"],
            [{"question_ref": "q-mood", "value": 3},
             {"question_ref": "q-sleep", "value": 5}], CLINICIAN,
            recorded_on="2026-02-01")
        self.ext.record_survey_response(
            self.pid, instrument["id"],
            [{"question_ref": "q-mood", "value": 5}], CLINICIAN)
        summary = self.ext.survey_summary(instrument["id"], ADMIN)
        self.assertEqual(summary["method"], "deterministic_aggregates")
        self.assertEqual(summary["responses"], 2)
        self.assertEqual(summary["per_question"]["q-mood"]["count"], 2)
        self.assertEqual(summary["per_question"]["q-mood"]["mean"], 4.0)
        self.assertEqual(summary["per_question"]["q-sleep"]["count"], 1)

    def test_answer_shape_is_exactly_two_keys(self):
        instrument = self._instrument()
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                self.pid, instrument["id"],
                [{"question_ref": "q-mood", "value": 3, "note": "smuggled"}],
                CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                self.pid, instrument["id"],
                [{"question_ref": "q-mood", "value": "high"}], CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                self.pid, instrument["id"],
                [{"question_ref": "q-unknown", "value": 1}], CLINICIAN)
        # Nothing stored, no id consumed.
        self.assertEqual(self.ext.list_survey_responses(ADMIN), [])
        ok = self.ext.record_survey_response(
            self.pid, instrument["id"],
            [{"question_ref": "q-mood", "value": 1}], CLINICIAN)
        self.assertEqual(ok["id"], "svr-1")


class TestEmrReference(BatchFixture):
    """Entry: EMR / EHR integration engines & documentation depth
    (2 of 5 claim the family) -- reference implementation: stub
    integration records, reported sync events, and documentation
    references; nothing connects or is generated."""

    def test_integration_is_labeled_reference_stub(self):
        integration = self.ext.create_emr_integration("epic-main", "ehr", ADMIN)
        self.assertEqual(integration["id"], "emr-1")
        self.assertIs(integration["reference_stub"], True)
        self.assertIs(integration["connected_here"], False)
        self.assertEqual(integration["state"], "recorded_reference_only")

    def test_sync_event_carries_count_only(self):
        integration = self.ext.create_emr_integration("epic-main", "emr", ADMIN)
        event = self.ext.record_emr_sync_event(
            integration["id"], "inbound", 42, CLINICIAN, occurred_on="2026-02-01")
        self.assertEqual(event["id"], "esy-1")
        self.assertEqual(event["record_count"], 42)
        self.assertIs(event["reference_stub"], True)
        with self.assertRaises(ValidationError):
            self.ext.record_emr_sync_event(
                integration["id"], "inbound", -1, CLINICIAN)

    def test_documentation_reference_holds_ref_only(self):
        integration = self.ext.create_emr_integration("epic-main", "ehr", ADMIN)
        doc = self.ext.record_documentation_reference(
            integration["id"], "doc-ref-7", CLINICIAN, recorded_on="2026-02-02")
        self.assertEqual(doc["id"], "doc-1")
        self.assertIs(doc["reference_stub"], True)
        self.assertIs(doc["generated_here"], False)
        self.assertEqual(doc["state"], "recorded_reference_only")
        docs = self.ext.list_documentation_references(
            ADMIN, integration_id=integration["id"])
        self.assertEqual(len(docs), 1)
        with self.assertRaises(NotFoundError):
            self.ext.record_documentation_reference(
                "emr-99", "doc-ref-8", CLINICIAN)


class TestClaimsAdjudication(BatchFixture):
    """Entry: Medical claims adjudication engine (2 of 5; the core
    keeps eligibility / coverage records only) -- built as claim
    records with recorded outcomes and derived current outcome;
    nothing is adjudicated or paid here."""

    def test_verification_check_shape_and_labels(self):
        eligibility = self.make_eligibility()
        check = self.ext.record_verification_check(
            self.pid, eligibility["id"], "verified", ADMIN, "2026-02-01")
        self.assertEqual(check["id"], "vrf-1")
        self.assertIs(check["verified_here"], False)
        self.assertEqual(check["outcome"], "verified")
        with self.assertRaises(ValidationError):
            self.ext.record_verification_check(
                self.pid, eligibility["id"], "approved", ADMIN, "2026-02-01")

    def test_verification_refuses_other_participants_eligibility(self):
        foreign = self.make_eligibility(self.other["id"], "plan-ref-2")
        with self.assertRaises(ValidationError):
            self.ext.record_verification_check(
                self.pid, foreign["id"], "verified", ADMIN, "2026-02-01")
        own = self.make_eligibility()
        ok = self.ext.record_verification_check(
            self.pid, own["id"], "verified", ADMIN, "2026-02-01")
        self.assertEqual(ok["id"], "vrf-1")

    def test_claim_shape_has_no_amount_or_identifier_fields(self):
        eligibility = self.make_eligibility()
        claim = self.ext.create_claim_record(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-02-03")
        self.assertEqual(claim["id"], "clm-1")
        self.assertEqual(
            set(claim.keys()),
            {"id", "participant_id", "eligibility_id", "claim_ref",
             "submitted_on", "adjudicated_here", "paid_here",
             "created_by", "created_utc"})
        self.assertIs(claim["adjudicated_here"], False)
        self.assertIs(claim["paid_here"], False)

    def test_claim_refuses_other_participants_eligibility(self):
        foreign = self.make_eligibility(self.other["id"], "plan-ref-2")
        with self.assertRaises(ValidationError):
            self.ext.create_claim_record(
                self.pid, foreign["id"], "claim-ref-1", ADMIN, "2026-02-03")
        own = self.make_eligibility()
        ok = self.ext.create_claim_record(
            self.pid, own["id"], "claim-ref-1", ADMIN, "2026-02-03")
        self.assertEqual(ok["id"], "clm-1")

    def test_current_outcome_derived_and_summary_counts(self):
        eligibility = self.make_eligibility()
        claim = self.ext.create_claim_record(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-02-03")
        view = self.ext.get_claim_record(claim["id"], ADMIN)
        self.assertIsNone(view["current_outcome"])
        self.assertEqual(view["outcome_count"], 0)
        self.ext.record_claim_outcome(claim["id"], "pending", ADMIN, "2026-02-04")
        self.ext.record_claim_outcome(claim["id"], "approved", ADMIN, "2026-02-05")
        view = self.ext.get_claim_record(claim["id"], ADMIN)
        self.assertEqual(view["current_outcome"], "approved")
        self.assertEqual(view["outcome_count"], 2)
        summary = self.ext.claims_summary(ADMIN)
        self.assertEqual(summary["claims"], 1)
        self.assertEqual(summary["by_current_outcome"]["approved"], 1)
        self.assertEqual(summary["undecided"], 0)

    def test_member_sees_only_own_claims(self):
        eligibility = self.make_eligibility()
        self.ext.create_claim_record(
            self.pid, eligibility["id"], "claim-ref-1", ADMIN, "2026-02-03")
        foreign = self.make_eligibility(self.other["id"], "plan-ref-2")
        self.ext.create_claim_record(
            self.other["id"], foreign["id"], "claim-ref-2", ADMIN, "2026-02-03")
        own = self.ext.list_claim_records(MEMBER)
        self.assertEqual(len(own), 1)
        self.assertEqual(own[0]["claim_ref"], "claim-ref-1")


class TestTelehealthMedia(BatchFixture):
    """Entry: Telehealth media (0 claims; named absence) -- built
    as visit records with modality labels only; the absence was
    retired at this tier by the GTS addition fork's own words,
    and the records form carries no media channel."""

    def test_visit_shape_and_media_label(self):
        visit = self.ext.create_telehealth_visit(
            self.pid, "visit-1", "video",
            "2026-03-01T15:00:00Z", "2026-03-01T15:30:00Z", CLINICIAN)
        self.assertEqual(visit["id"], "tlv-1")
        self.assertIs(visit["media_channel_here"], False)
        self.assertEqual(visit["state"], "scheduled")
        completed = self.ext.set_telehealth_visit_state(
            visit["id"], "completed", CLINICIAN)
        self.assertEqual(completed["state"], "completed")

    def test_end_before_start_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.create_telehealth_visit(
                self.pid, "visit-1", "audio",
                "2026-03-01T15:30:00Z", "2026-03-01T15:00:00Z", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.create_telehealth_visit(
                self.pid, "visit-1", "carrier-pigeon",
                "2026-03-01T15:00:00Z", "2026-03-01T15:30:00Z", CLINICIAN)


class TestClinicalDecisionSupport(BatchFixture):
    """Entry: Clinical decision support (0 standalone claims) --
    built as guideline reference records (never applied) plus
    verbatim clinician decision labels; no advice is generated."""

    def test_guideline_and_decision_shapes(self):
        guideline = self.ext.create_guideline_reference(
            "gdl-ada-2026", "Diabetes care guideline", ADMIN,
            program_id=self.prg)
        self.assertEqual(guideline["id"], "gdl-1")
        self.assertIs(guideline["applied_here"], False)
        decision = self.ext.record_clinician_decision(
            self.pid, guideline["id"], "continue_current_plan", CLINICIAN,
            "2026-02-10")
        self.assertEqual(decision["id"], "cds-1")
        self.assertEqual(decision["decision_label"], "continue_current_plan")
        self.assertIs(decision["advice_generated_here"], False)

    def test_decision_requires_existing_guideline(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_clinician_decision(
                self.pid, "gdl-99", "label", CLINICIAN, "2026-02-10")


class TestDeviceConnectivity(BatchFixture):
    """Entry: Device connectivity / sync pipelines (1 of 5) --
    built as device-link records with opaque refs and reported
    sync statuses; no data flows here."""

    def test_link_and_sync_view_derivations(self):
        link = self.ext.create_device_link(
            self.pid, "device-ref-1", CLINICIAN, linked_on="2026-01-15")
        self.assertEqual(link["id"], "dvl-1")
        self.assertIs(link["data_flows_here"], False)
        self.ext.record_sync_status(link["id"], "synced", 12, CLINICIAN)
        self.ext.record_sync_status(link["id"], "pending", 0, CLINICIAN)
        views = self.ext.list_device_links(ADMIN, participant_id=self.pid)
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0]["sync_count"], 2)
        self.assertEqual(views[0]["latest_status_label"], "pending")

    def test_duplicate_device_ref_per_participant_refused(self):
        self.ext.create_device_link(self.pid, "device-ref-1", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.create_device_link(self.pid, "device-ref-1", CLINICIAN)
        # The same opaque ref under a different participant is fine.
        other = self.ext.create_device_link(self.other["id"], "device-ref-1",
                                            CLINICIAN)
        self.assertEqual(other["id"], "dvl-2")


class TestModelReference(BatchFixture):
    """Entry: AI/ML models & personalization engines (1 of 5) --
    reference implementation: model profile records and opaque
    output references; nothing infers."""

    def test_profile_and_output_are_labeled_stubs(self):
        profile = self.ext.create_model_profile(
            "model-risk-1", "risk_model", ADMIN)
        self.assertEqual(profile["id"], "mdl-1")
        self.assertIs(profile["reference_stub"], True)
        self.assertIs(profile["inference_here"], False)
        output = self.ext.record_model_output(
            self.pid, profile["id"], "output-ref-1", CLINICIAN,
            recorded_on="2026-02-11")
        self.assertEqual(output["id"], "mdo-1")
        self.assertIs(output["reference_stub"], True)
        self.assertIs(output["inference_here"], False)
        self.assertEqual(output["state"], "recorded_reference_only")


class TestWorkflowReference(BatchFixture):
    """Entry: Automation / workflow engines (1 of 5) -- reference
    implementation: definition records whose steps are data and
    run references with reported outcomes; nothing executes."""

    def test_definition_and_run_are_labeled_stubs(self):
        workflow = self.ext.create_workflow_definition(
            "wf-onboard", "Onboarding", ["step-a", "step-b"], ADMIN)
        self.assertEqual(workflow["id"], "wfd-1")
        self.assertIs(workflow["reference_stub"], True)
        self.assertIs(workflow["executed_here"], False)
        run = self.ext.record_workflow_run(
            self.pid, workflow["id"], "completed_reported", CLINICIAN,
            recorded_on="2026-02-12")
        self.assertEqual(run["id"], "wfr-1")
        self.assertIs(run["executed_here"], False)


class TestAppAccess(BatchFixture):
    """Entry: Multi-device native apps (platform property, 2 of 5)
    -- built as app-access registration records with derived
    platform counts; nothing is distributed."""

    def test_registration_and_summary(self):
        self.ext.register_app_access(self.pid, "app-ios-1", "ios", CLINICIAN,
                                     registered_on="2026-01-20")
        self.ext.register_app_access(self.pid, "app-web-1", "web", CLINICIAN)
        self.ext.register_app_access(self.other["id"], "app-and-1", "android",
                                     CLINICIAN)
        summary = self.ext.app_access_summary(ADMIN)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["registrations"], 3)
        self.assertEqual(summary["by_platform"],
                         {"ios": 1, "android": 1, "web": 1})
        own = self.ext.app_access_summary(ADMIN, participant_id=self.pid)
        self.assertEqual(own["registrations"], 2)
        with self.assertRaises(ValidationError):
            self.ext.register_app_access(self.pid, "app-ios-1", "ios", CLINICIAN)


class TestHostingReference(BatchFixture):
    """Entry: Hosting platform (1 of 5) -- reference
    implementation per PLATFORM-LAYER.md decision 6: deployment
    records as data; nothing is hosted here."""

    def test_deployment_record_and_summary(self):
        record = self.ext.create_deployment_record(
            "dep-main", "multi_tenant_reported", "us-gov-region", ADMIN)
        self.assertEqual(record["id"], "dep-1")
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["hosted_here"], False)
        self.assertIs(record["multi_tenant_here"], False)
        summary = self.ext.deployment_summary(ADMIN)
        self.assertEqual(summary["records"], 1)
        self.assertEqual(summary["build_tenancy"], "single_tenant_reference")
        self.assertIs(summary["hosted_here"], False)


class TestPrivacySurface(BatchFixture):
    """Cross-cutting: the founding HARD PRIVACY RULE over the
    whole extension surface."""

    def _exercise_surface(self):
        channel = self.ext.create_engagement_channel("portal", "sms", ADMIN)
        self.ext.create_content_item("c-1", "Welcome", "article", ADMIN)
        self.ext.record_engagement_message(
            self.pid, channel["id"], "c-1", CLINICIAN)
        instrument = self.ext.create_survey_instrument(
            "s-1", "Check", ["q-1"], ADMIN)
        self.ext.record_survey_response(
            self.pid, instrument["id"],
            [{"question_ref": "q-1", "value": 2}], CLINICIAN)
        integration = self.ext.create_emr_integration("e-1", "ehr", ADMIN)
        self.ext.record_emr_sync_event(integration["id"], "inbound", 3, CLINICIAN)
        self.ext.record_documentation_reference(
            integration["id"], "d-1", CLINICIAN)
        eligibility = self.make_eligibility()
        self.ext.record_verification_check(
            self.pid, eligibility["id"], "verified", ADMIN, "2026-02-01")
        claim = self.ext.create_claim_record(
            self.pid, eligibility["id"], "cl-1", ADMIN, "2026-02-02")
        self.ext.record_claim_outcome(claim["id"], "pending", ADMIN, "2026-02-03")
        self.ext.create_telehealth_visit(
            self.pid, "v-1", "video", "2026-03-01T15:00:00Z",
            "2026-03-01T15:30:00Z", CLINICIAN)
        guideline = self.ext.create_guideline_reference("g-1", "Guide", ADMIN)
        self.ext.record_clinician_decision(
            self.pid, guideline["id"], "label", CLINICIAN, "2026-02-10")
        link = self.ext.create_device_link(self.pid, "dev-1", CLINICIAN)
        self.ext.record_sync_status(link["id"], "synced", 1, CLINICIAN)
        profile = self.ext.create_model_profile("m-1", "risk_model", ADMIN)
        self.ext.record_model_output(self.pid, profile["id"], "o-1", CLINICIAN)
        workflow = self.ext.create_workflow_definition(
            "w-1", "Flow", ["s-1"], ADMIN)
        self.ext.record_workflow_run(self.pid, workflow["id"], "done", CLINICIAN)
        self.ext.register_app_access(self.pid, "a-1", "ios", CLINICIAN)
        self.ext.create_deployment_record("dep-1", "single", "region", ADMIN)
        return [
            self.ext.list_engagement_messages(ADMIN),
            self.ext.list_survey_responses(ADMIN),
            self.ext.list_emr_integrations(ADMIN),
            self.ext.list_emr_sync_events(ADMIN),
            self.ext.list_documentation_references(ADMIN),
            self.ext.list_claim_records(ADMIN),
            self.ext.list_telehealth_visits(ADMIN),
            self.ext.list_clinician_decisions(ADMIN),
            self.ext.list_guideline_references(ADMIN),
            self.ext.list_device_links(ADMIN),
            self.ext.list_model_outputs(ADMIN),
            self.ext.list_workflow_runs(ADMIN),
            self.ext.engagement_summary(self.pid, ADMIN),
            self.ext.survey_summary(instrument["id"], ADMIN),
            self.ext.claims_summary(ADMIN),
            self.ext.app_access_summary(ADMIN),
            self.ext.deployment_summary(ADMIN),
        ]

    def test_no_forbidden_key_anywhere_on_the_surface(self):
        for payload in self._exercise_surface():
            self.assertEqual(_banned_keys(payload), set())

    def test_forbidden_field_cannot_be_smuggled_as_kwarg(self):
        with self.assertRaises(TypeError):
            self.ext.create_claim_record(
                self.pid, "elig-1", "cl-x", CLINICIAN, "2026-02-02",
                diagnosis="smuggled")
        with self.assertRaises(TypeError):
            self.ext.create_device_link(
                self.pid, "dev-x", CLINICIAN, serial_number="smuggled")

    def test_denied_write_is_audited_with_denied_suffix(self):
        # The auditor holds no eligibility_write.
        eligibility = self.make_eligibility()
        with self.assertRaises(PermissionDenied):
            self.ext.create_claim_record(
                self.pid, eligibility["id"], "cl-x", AUDITOR, "2026-02-02")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_claim_record_create:denied", actions)
        self.assertNotIn("ext_claim_record_create", actions)


class _NoOwnershipGuard(HealthExtensions):
    """Mutant: the eligibility-ownership seam neutralized."""

    def _check_eligibility_belongs(self, eligibility, participant_id):
        return None


class TestEligibilityOwnershipNegativeControl(BatchFixture):
    """Negative control for the batch unit's fresh seam.

    A verification check or claim record bound to ANOTHER
    participant's eligibility record must be refused. The mutant
    subclass (ownership seam neutralized) would NOT produce that
    result; the canonical extension does. The same mutation was
    applied to the real module and the full suite run -- see
    tests/README.md for the verified failure count.
    """

    def _attempt_binds(self, ext):
        foreign = ext.store.create_eligibility(
            self.other["id"], "plan-ref-foreign", "2026-01-01", ADMIN)
        results = {}
        try:
            ext.record_verification_check(
                self.pid, foreign["id"], "verified", ADMIN, "2026-02-01")
            results["verification"] = "accepted"
        except ValidationError:
            results["verification"] = "refused"
        try:
            ext.create_claim_record(
                self.pid, foreign["id"], "claim-ref-x", ADMIN, "2026-02-03")
            results["claim"] = "accepted"
        except ValidationError:
            results["claim"] = "refused"
        return results

    def test_canonical_run_refuses_cross_participant_binds(self):
        results = self._attempt_binds(self.ext)
        self.assertEqual(results, {"verification": "refused", "claim": "refused"})

    def test_mutant_would_not_produce_the_refusals(self):
        mutant = _NoOwnershipGuard(self.store)
        results = self._attempt_binds(mutant)
        self.assertEqual(results,
                         {"verification": "accepted", "claim": "accepted"})

    def test_guard_restored_refuses_again(self):
        results = self._attempt_binds(self.ext)
        self.assertEqual(results, {"verification": "refused", "claim": "refused"})
