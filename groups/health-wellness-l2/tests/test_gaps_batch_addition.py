"""Final GAPS batch tests, SECOND unit -- Health & Wellness L2
remainder additions (+3 forks).

Pins the second-unit extension surface in
``src/health/extensions_addition.py``
(``HealthExtensionsAddition``, subclassing the first unit's
``HealthExtensions`` over the core ``HealthStore``): one test
class per open entry of the GAPS.md section "Remainder Addition
-- Health & Wellness L2 (+3 forks)" (see ``../BATCH-ADDITION.md``
for the per-entry disposition), plus cross-cutting pins -- the
category's HARD PRIVACY RULE over the whole addition surface
(no diagnosis / clinical-note / identifier-shaped key anywhere,
no risk-profile-shaped key anywhere, and forbidden fields cannot
be smuggled in), derived-never-stored values (package current
event label, suggestion current review outcome, CDI current
response label, report current status, console aggregates),
member scope, RBAC denials audited with a ``:denied`` suffix, no
id consumed by a failed operation, and this unit's
mutation-verified negative control: the activity-ownership seam
``_check_activity_belongs``, without which a telehealth media
session could bind to ANOTHER participant's Core visit record.

Fixtures: ``make_store()`` (program "Diabetes Care", participant
under opaque ref "carol") plus a second participant (ref "erin")
where scope or ownership needs one.
"""

import unittest

from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError
from health.extensions_addition import HealthExtensionsAddition


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
    no direct identifier field in any shape -- plus, for this
    unit, no risk-profile-shaped key (the console computes no
    risk profile; a bare ``risk_profile`` / ``risk_score`` key
    would be one).
    """
    privacy = {
        "diagnosis", "note", "notes", "clinical_note", "clinical_notes",
        "name", "email", "phone", "ssn", "dob", "date_of_birth",
        "member_number", "address", "first_name", "last_name",
        "insurer", "insurer_name",
        "risk_profile", "risk_score",
    }
    return {key for key in _all_keys(obj) if key.lower() in privacy}


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.participant = make_store()
        self.ext = HealthExtensionsAddition(self.store)
        self.pid = self.participant["id"]
        self.prg = self.program["id"]
        self.other = self.store.create_participant("erin", ADMIN)

    def make_activity(self, participant_id=None, title="Visit"):
        return self.store.create_activity(
            participant_id or self.pid, title,
            "2026-03-01T15:00:00Z", ADMIN, program_id=self.prg)


class TestTelehealthMediaEngine(AdditionFixture):
    """idx 600 -- telehealth media engine (GTS): session records,
    no media channel."""

    def test_session_record_shape_and_labels(self):
        session = self.ext.create_media_session(
            self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
            "2026-03-01T15:30:00Z", CLINICIAN)
        self.assertEqual(session["id"], "tms-1")
        self.assertEqual(session["state"], "scheduled")
        self.assertEqual(session["modality"], "video")
        self.assertIsNone(session["activity_id"])
        self.assertFalse(session["media_channel_here"])
        self.assertFalse(session["connected_here"])

    def test_session_binds_to_own_activity(self):
        activity = self.make_activity()
        session = self.ext.create_media_session(
            self.pid, "sess-1", "teleconference", "2026-03-01T15:00:00Z",
            "2026-03-01T15:30:00Z", CLINICIAN, activity_id=activity["id"])
        self.assertEqual(session["activity_id"], activity["id"])

    def test_session_refuses_other_participants_activity(self):
        foreign = self.make_activity(participant_id=self.other["id"])
        with self.assertRaises(ValidationError):
            self.ext.create_media_session(
                self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
                "2026-03-01T15:30:00Z", CLINICIAN,
                activity_id=foreign["id"])
        # The refused create consumed no id.
        session = self.ext.create_media_session(
            self.pid, "sess-2", "video", "2026-03-01T15:00:00Z",
            "2026-03-01T15:30:00Z", CLINICIAN)
        self.assertEqual(session["id"], "tms-1")

    def test_unknown_activity_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_media_session(
                self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
                "2026-03-01T15:30:00Z", CLINICIAN, activity_id="act-99")

    def test_bad_modality_and_window_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.create_media_session(
                self.pid, "sess-1", "hologram", "2026-03-01T15:00:00Z",
                "2026-03-01T15:30:00Z", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.create_media_session(
                self.pid, "sess-1", "video", "2026-03-01T15:30:00Z",
                "2026-03-01T15:00:00Z", CLINICIAN)

    def test_duplicate_session_ref_refused(self):
        self.ext.create_media_session(
            self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
            "2026-03-01T15:30:00Z", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.create_media_session(
                self.pid, "sess-1", "audio", "2026-03-02T15:00:00Z",
                "2026-03-02T15:30:00Z", CLINICIAN)

    def test_state_setter_and_summary(self):
        first = self.ext.create_media_session(
            self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
            "2026-03-01T15:30:00Z", CLINICIAN)
        self.ext.create_media_session(
            self.other["id"], "sess-2", "audio", "2026-03-01T16:00:00Z",
            "2026-03-01T16:30:00Z", CLINICIAN)
        moved = self.ext.set_media_session_state(
            first["id"], "completed", CLINICIAN)
        self.assertEqual(moved["state"], "completed")
        with self.assertRaises(ValidationError):
            self.ext.set_media_session_state(first["id"], "live", CLINICIAN)
        summary = self.ext.media_session_summary(ADMIN, participant_id=self.pid)
        self.assertEqual(summary["sessions"], 1)
        self.assertEqual(summary["by_modality"]["video"], 1)
        self.assertEqual(summary["by_state"]["completed"], 1)
        self.assertFalse(summary["media_channel_here"])

    def test_member_scope_on_sessions(self):
        self.ext.create_media_session(
            self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
            "2026-03-01T15:30:00Z", CLINICIAN)
        self.ext.create_media_session(
            self.other["id"], "sess-2", "video", "2026-03-01T16:00:00Z",
            "2026-03-01T16:30:00Z", CLINICIAN)
        own = self.ext.list_media_sessions(MEMBER)
        self.assertEqual([s["session_ref"] for s in own], ["sess-1"])


class TestStoreAndForward(AdditionFixture):
    """idx 601 -- store-and-forward clinical data service (GTS):
    package + event records; the payload is never held."""

    def _package(self, **overrides):
        kwargs = dict(participant_id=self.pid, package_ref="pkg-1",
                      content_kind="lab", direction="inbound",
                      item_count=4, actor=CLINICIAN)
        kwargs.update(overrides)
        return self.ext.create_exchange_package(**kwargs)

    def test_package_record_shape_and_labels(self):
        package = self._package()
        self.assertEqual(package["id"], "xpk-1")
        self.assertEqual(package["content_kind"], "lab")
        self.assertFalse(package["payload_held_here"])
        self.assertFalse(package["stored_here"])
        self.assertFalse(package["forwarded_here"])

    def test_bad_kind_direction_and_count_refused(self):
        with self.assertRaises(ValidationError):
            self._package(content_kind="genome")
        with self.assertRaises(ValidationError):
            self._package(direction="sideways")
        with self.assertRaises(ValidationError):
            self._package(item_count=True)
        with self.assertRaises(ValidationError):
            self._package(item_count=-1)

    def test_current_event_label_derived_at_read(self):
        package = self._package()
        view = self.ext.get_exchange_package(package["id"], ADMIN)
        self.assertEqual(view["event_count"], 0)
        self.assertIsNone(view["current_event_label"])
        self.ext.record_exchange_event(package["id"], "queued", CLINICIAN)
        event = self.ext.record_exchange_event(
            package["id"], "forwarded", CLINICIAN, occurred_on="2026-03-02")
        self.assertTrue(event["reference_transport"])
        view = self.ext.get_exchange_package(package["id"], ADMIN)
        self.assertEqual(view["event_count"], 2)
        self.assertEqual(view["current_event_label"], "forwarded")
        stored = [p for p in self.ext.list_exchange_packages(ADMIN)
                  if p["id"] == package["id"]][0]
        self.assertNotIn("current_event_label", package)
        self.assertEqual(stored["current_event_label"], "forwarded")

    def test_bad_event_label_and_unknown_package_refused(self):
        package = self._package()
        with self.assertRaises(ValidationError):
            self.ext.record_exchange_event(package["id"], "teleported",
                                           CLINICIAN)
        with self.assertRaises(NotFoundError):
            self.ext.record_exchange_event("xpk-99", "queued", CLINICIAN)

    def test_member_cannot_read_other_participants_package(self):
        package = self.ext.create_exchange_package(
            self.other["id"], "pkg-x", "image", "outbound", 1, CLINICIAN)
        with self.assertRaises(PermissionDenied):
            self.ext.get_exchange_package(package["id"], MEMBER)


class TestMedicalCoding(AdditionFixture):
    """idx 602 -- medical coding engine (Solventum): version,
    suggestion-reference, and review records; no code enters."""

    def _version(self):
        return self.ext.create_code_system_version(
            "icd10-2026", "icd10", "FY2026", ADMIN)

    def test_version_record_shape(self):
        version = self._version()
        self.assertEqual(version["id"], "ctv-1")
        self.assertFalse(version["content_held_here"])
        with self.assertRaises(ValidationError):
            self.ext.create_code_system_version("x-1", "snomed", "1", ADMIN)

    def test_suggestion_and_review_flow(self):
        version = self._version()
        suggestion = self.ext.record_code_suggestion(
            self.pid, version["id"], "sug-1", CLINICIAN,
            recorded_on="2026-03-03")
        self.assertFalse(suggestion["suggested_here"])
        self.assertFalse(suggestion["assigned_here"])
        view = self.ext.list_code_suggestions(ADMIN)[0]
        self.assertEqual(view["review_count"], 0)
        self.assertIsNone(view["current_review_outcome"])
        self.ext.record_code_review(
            suggestion["id"], "accepted", CLINICIAN, "2026-03-04")
        self.ext.record_code_review(
            suggestion["id"], "modified", CLINICIAN, "2026-03-05")
        view = self.ext.list_code_suggestions(ADMIN)[0]
        self.assertEqual(view["review_count"], 2)
        self.assertEqual(view["current_review_outcome"], "modified")

    def test_unknown_version_and_bad_outcome_refused(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_code_suggestion(self.pid, "ctv-99", "sug-1",
                                            CLINICIAN)
        version = self._version()
        suggestion = self.ext.record_code_suggestion(
            self.pid, version["id"], "sug-1", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_code_review(
                suggestion["id"], "ignored", CLINICIAN, "2026-03-04")

    def test_duplicate_suggestion_ref_refused(self):
        version = self._version()
        self.ext.record_code_suggestion(self.pid, version["id"], "sug-1",
                                        CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.record_code_suggestion(self.pid, version["id"], "sug-1",
                                            CLINICIAN)


class TestGrouperContent(AdditionFixture):
    """idx 603 -- grouper / classification & reimbursement content
    services (Solventum): definitions and reported outcomes."""

    def test_grouper_definition_shape(self):
        grouper = self.ext.create_grouper_definition(
            "gpcs-1", "GPCS", "2026.1", ADMIN)
        self.assertEqual(grouper["id"], "grp-1")
        self.assertFalse(grouper["grouped_here"])
        self.assertFalse(grouper["classified_here"])

    def test_grouping_outcome_recorded_as_reported(self):
        grouper = self.ext.create_grouper_definition(
            "gpcs-1", "GPCS", "2026.1", ADMIN)
        outcome = self.ext.record_grouping_outcome(
            self.pid, grouper["id"], "out-1", "grouped", CLINICIAN,
            recorded_on="2026-03-03")
        self.assertFalse(outcome["grouped_here"])
        with self.assertRaises(ValidationError):
            self.ext.record_grouping_outcome(
                self.pid, grouper["id"], "out-2", "priced", CLINICIAN)
        listed = self.ext.list_grouping_outcomes(ADMIN, participant_id=self.pid)
        self.assertEqual([o["outcome_ref"] for o in listed], ["out-1"])

    def test_reimbursement_content_package(self):
        package = self.ext.create_reimbursement_content_package(
            "rc-2026", "2026-edition", "2026-01-01", ADMIN,
            effective_to="2026-12-31")
        self.assertFalse(package["content_held_here"])
        with self.assertRaises(ValidationError):
            self.ext.create_reimbursement_content_package(
                "rc-bad", "v", "2026-12-31", ADMIN, effective_to="2026-01-01")
        listed = self.ext.list_reimbursement_content_packages(ADMIN)
        self.assertEqual([p["content_ref"] for p in listed], ["rc-2026"])


class TestCdiTooling(AdditionFixture):
    """idx 604 -- clinical documentation integrity tooling
    (Solventum): query + response records; no document text."""

    def test_query_and_response_flow(self):
        query = self.ext.create_cdi_query(
            self.pid, "q-1", "clarification", "doc-ref-1", CLINICIAN,
            "2026-03-03")
        self.assertFalse(query["document_text_held_here"])
        self.assertFalse(query["generated_here"])
        view = self.ext.get_cdi_query(query["id"], ADMIN)
        self.assertEqual(view["response_count"], 0)
        self.assertIsNone(view["current_response_label"])
        self.ext.record_cdi_response(query["id"], "responded", CLINICIAN,
                                     "2026-03-04")
        view = self.ext.get_cdi_query(query["id"], ADMIN)
        self.assertEqual(view["response_count"], 1)
        self.assertEqual(view["current_response_label"], "responded")

    def test_bad_kind_label_and_unknown_query_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.create_cdi_query(
                self.pid, "q-1", "rewrite", "doc-ref-1", CLINICIAN,
                "2026-03-03")
        query = self.ext.create_cdi_query(
            self.pid, "q-1", "confirmation", "doc-ref-1", CLINICIAN,
            "2026-03-03")
        with self.assertRaises(ValidationError):
            self.ext.record_cdi_response(query["id"], "essay", CLINICIAN,
                                         "2026-03-04")
        with self.assertRaises(NotFoundError):
            self.ext.record_cdi_response("cdq-99", "responded", CLINICIAN,
                                         "2026-03-04")


class TestDiagnosticReports(AdditionFixture):
    """idx 605 -- diagnostic report generation engine (Somnoware):
    request + report-reference records; nothing is generated."""

    def test_request_and_reference_flow(self):
        request = self.ext.create_report_request(
            self.pid, "req-1", "sleep", CLINICIAN, "2026-03-03",
            program_id=self.prg)
        self.assertFalse(request["generated_here"])
        self.assertFalse(request["interpreted_here"])
        view = self.ext.list_report_requests(ADMIN)[0]
        self.assertEqual(view["report_count"], 0)
        self.assertIsNone(view["current_report_status"])
        reference = self.ext.record_report_reference(
            request["id"], "rpt-1", "reported", CLINICIAN,
            recorded_on="2026-03-04")
        self.assertFalse(reference["report_held_here"])
        view = self.ext.list_report_requests(ADMIN)[0]
        self.assertEqual(view["report_count"], 1)
        self.assertEqual(view["current_report_status"], "reported")

    def test_bad_kind_status_and_unknown_request_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.create_report_request(
                self.pid, "req-1", "genomic", CLINICIAN, "2026-03-03")
        request = self.ext.create_report_request(
            self.pid, "req-1", "pulmonary", CLINICIAN, "2026-03-03")
        with self.assertRaises(ValidationError):
            self.ext.record_report_reference(
                request["id"], "rpt-1", "signed", CLINICIAN)
        with self.assertRaises(NotFoundError):
            self.ext.record_report_reference("drq-99", "rpt-1", "reported",
                                             CLINICIAN)


class TestTherapyConsole(AdditionFixture):
    """idx 606 -- therapy progress & risk-profile console
    (Somnoware): a derived view over Core records; no risk
    profile is computed."""

    def _seed_core_records(self):
        self.store.record_measurement(
            self.pid, "ahi", 4, "events/h", "2026-03-01", CLINICIAN,
            program_id=self.prg)
        self.store.record_measurement(
            self.pid, "ahi", 8, "events/h", "2026-03-08", CLINICIAN,
            program_id=self.prg)
        self.store.record_measurement(
            self.pid, "hours_used", 6.5, "h", "2026-03-08", CLINICIAN,
            program_id=self.prg)
        overdue = self.store.create_plan(
            self.pid, self.prg, "CPAP follow-up", "2026-06-01", CLINICIAN)
        done = self.store.create_plan(
            self.pid, self.prg, "Mask fitting", "2026-06-01", CLINICIAN)
        self.store.complete_plan(done["id"], "2026-05-20", CLINICIAN)
        self.make_activity()
        finished = self.make_activity(title="Check-in")
        self.store.set_activity_state(finished["id"], "completed", ADMIN)
        return overdue

    def test_console_derives_aggregates_over_core_records(self):
        self._seed_core_records()
        view = self.ext.therapy_progress_console(
            self.pid, self.prg, ADMIN, as_of="2026-06-15")
        self.assertEqual(view["method"], "deterministic_aggregates")
        self.assertEqual(view["measurements"], 3)
        self.assertEqual(view["measurements_by_metric"]["ahi"],
                         {"count": 2, "min": 4, "max": 8, "mean": 6.0})
        self.assertEqual(view["measurements_by_metric"]["hours_used"]
                         ["count"], 1)
        self.assertEqual(view["plans"], 2)
        self.assertEqual(view["plans_by_status"],
                         {"current": 0, "overdue": 1, "completed": 1})
        self.assertEqual(view["activities"], 2)
        self.assertEqual(view["activities_by_state"],
                         {"scheduled": 1, "completed": 1, "cancelled": 0})

    def test_console_computes_no_risk_profile(self):
        self._seed_core_records()
        view = self.ext.therapy_progress_console(
            self.pid, self.prg, ADMIN, as_of="2026-06-15")
        self.assertFalse(view["risk_profile_computed_here"])
        self.assertFalse(view["predicted_here"])
        self.assertEqual(_banned_keys(view), set())

    def test_console_unknown_program_and_member_denied(self):
        with self.assertRaises(NotFoundError):
            self.ext.therapy_progress_console(
                self.pid, "prg-99", ADMIN, as_of="2026-06-15")
        # The member role holds no report_read.
        with self.assertRaises(PermissionDenied):
            self.ext.therapy_progress_console(
                self.pid, self.prg, MEMBER, as_of="2026-06-15")


class TestPrivacySurfaceAddition(AdditionFixture):
    """Cross-cutting: the founding HARD PRIVACY RULE over the
    whole addition surface."""

    def _exercise_surface(self):
        activity = self.make_activity()
        session = self.ext.create_media_session(
            self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
            "2026-03-01T15:30:00Z", CLINICIAN, activity_id=activity["id"])
        self.ext.set_media_session_state(session["id"], "completed",
                                         CLINICIAN)
        package = self.ext.create_exchange_package(
            self.pid, "pkg-1", "image", "outbound", 2, CLINICIAN)
        self.ext.record_exchange_event(package["id"], "queued", CLINICIAN)
        version = self.ext.create_code_system_version(
            "cpt-2026", "cpt", "2026", ADMIN)
        suggestion = self.ext.record_code_suggestion(
            self.pid, version["id"], "sug-1", CLINICIAN)
        self.ext.record_code_review(suggestion["id"], "accepted", CLINICIAN,
                                    "2026-03-04")
        grouper = self.ext.create_grouper_definition(
            "gpcs-1", "GPCS", "2026.1", ADMIN)
        self.ext.record_grouping_outcome(
            self.pid, grouper["id"], "out-1", "grouped", CLINICIAN)
        self.ext.create_reimbursement_content_package(
            "rc-2026", "2026-edition", "2026-01-01", ADMIN)
        query = self.ext.create_cdi_query(
            self.pid, "q-1", "specificity", "doc-ref-1", CLINICIAN,
            "2026-03-03")
        self.ext.record_cdi_response(query["id"], "responded", CLINICIAN,
                                     "2026-03-04")
        request = self.ext.create_report_request(
            self.pid, "req-1", "sleep", CLINICIAN, "2026-03-03",
            program_id=self.prg)
        self.ext.record_report_reference(request["id"], "rpt-1", "reported",
                                         CLINICIAN)
        return [
            self.ext.list_media_sessions(ADMIN),
            self.ext.media_session_summary(ADMIN),
            self.ext.list_exchange_packages(ADMIN),
            self.ext.list_exchange_events(ADMIN),
            self.ext.list_code_system_versions(ADMIN),
            self.ext.list_code_suggestions(ADMIN),
            self.ext.list_grouper_definitions(ADMIN),
            self.ext.list_grouping_outcomes(ADMIN),
            self.ext.list_reimbursement_content_packages(ADMIN),
            self.ext.list_cdi_queries(ADMIN),
            self.ext.list_report_requests(ADMIN),
            self.ext.therapy_progress_console(
                self.pid, self.prg, ADMIN, as_of="2026-06-15"),
        ]

    def test_no_forbidden_key_anywhere_on_the_surface(self):
        for payload in self._exercise_surface():
            self.assertEqual(_banned_keys(payload), set())

    def test_forbidden_field_cannot_be_smuggled_as_kwarg(self):
        with self.assertRaises(TypeError):
            self.ext.create_media_session(
                self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
                "2026-03-01T15:30:00Z", CLINICIAN, transcript="smuggled")
        with self.assertRaises(TypeError):
            self.ext.create_exchange_package(
                self.pid, "pkg-1", "lab", "inbound", 1, CLINICIAN,
                payload="smuggled")
        with self.assertRaises(TypeError):
            self.ext.record_code_suggestion(
                self.pid, "ctv-1", "sug-1", CLINICIAN, code="E11.9")
        with self.assertRaises(TypeError):
            self.ext.create_cdi_query(
                self.pid, "q-1", "clarification", "doc-ref-1", CLINICIAN,
                "2026-03-03", query_text="smuggled")
        with self.assertRaises(TypeError):
            self.ext.create_report_request(
                self.pid, "req-1", "sleep", CLINICIAN, "2026-03-03",
                findings="smuggled")

    def test_denied_write_is_audited_with_denied_suffix(self):
        # The auditor holds no activity_write.
        with self.assertRaises(PermissionDenied):
            self.ext.create_media_session(
                self.pid, "sess-1", "video", "2026-03-01T15:00:00Z",
                "2026-03-01T15:30:00Z", AUDITOR)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_media_session_create:denied", actions)
        self.assertNotIn("ext_media_session_create", actions)


class _NoActivityOwnershipGuard(HealthExtensionsAddition):
    """Mutant: the activity-ownership seam neutralized."""

    def _check_activity_belongs(self, activity, participant_id):
        return None


class TestActivityOwnershipNegativeControl(AdditionFixture):
    """Negative control for this unit's fresh seam.

    A telehealth media session bound to ANOTHER participant's
    Core activity (visit) record must be refused. The mutant
    subclass (ownership seam neutralized) would NOT produce that
    result; the canonical extension does. The same mutation was
    applied to the real module and the full suite run -- see
    tests/README.md for the verified failure count.
    """

    def _attempt_bind(self, ext):
        foreign = ext.store.create_activity(
            self.other["id"], "Foreign visit", "2026-03-01T15:00:00Z",
            ADMIN, program_id=self.prg)
        try:
            ext.create_media_session(
                self.pid, "sess-x", "video", "2026-03-01T15:00:00Z",
                "2026-03-01T15:30:00Z", CLINICIAN,
                activity_id=foreign["id"])
            return "accepted"
        except ValidationError:
            return "refused"

    def test_canonical_run_refuses_cross_participant_bind(self):
        self.assertEqual(self._attempt_bind(self.ext), "refused")

    def test_mutant_would_not_produce_the_refusal(self):
        mutant = _NoActivityOwnershipGuard(self.store)
        self.assertEqual(self._attempt_bind(mutant), "accepted")

    def test_guard_restored_refuses_again(self):
        self.assertEqual(self._attempt_bind(self.ext), "refused")


if __name__ == "__main__":
    unittest.main()
