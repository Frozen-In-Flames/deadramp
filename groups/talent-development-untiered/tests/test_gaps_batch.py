"""Final GAPS batch tests — Untiered Set 20 (Talent Development).

Pins the extension surface in ``talentdev.extensions`` entry by
entry: the records form of live development delivery (idx 930),
the labeled reference form of the assessment instruments /
administration / scoring engines (idx 931), the
records-and-derivation form of the analytics / trend engine
(idx 932), and the labeled reference form of AI models
(idx 933) — including the stub labels, the untouched-core pins,
the derived-never-stored pins, and recursive scans proving the
new surface carries no tier/baseline key, no score-shaped key,
no money key, and no personal-data key, tier-null discipline
exactly as the founding build's shapes tests pin the core.

The batch's fresh negative control lives at the bottom: the
canonical latest-label check over the extension's single
derivation seam (:meth:`TalentDevExtensions._latest_label`),
proven to fail against an earliest-reading mutant and to pass
on the real seam, with the discriminating other arm (a single
record's view reports that record's label on the real seam).
"""

import inspect
import unittest

import talentdev.extensions as extensions_module
from talentdev.errors import NotFoundError, PermissionDenied, ValidationError
from talentdev.extensions import TalentDevExtensions
from talentdev_helpers import ADMIN, OPERATOR, VIEWER, make_org, make_program, make_store

FORBIDDEN_KEY_PARTS = (
    # the founding shapes scan (score / money / personal data)
    "score", "grade", "rank", "rating", "rate",
    "email", "ssn", "password", "secret",
    "salary", "wage", "price", "fee", "amount", "cost",
    "diagnosis", "health",
    # tier-null discipline: no tier/baseline/equivalence key
    "tier", "baseline", "equivalence", "cmmc", "fedramp",
    "impact_level",
    # content the substrate never holds
    "transcript", "recording", "media_content",
)


def scan_keys(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                if part in lowered:
                    hits.append("%s.%s" % (path, key))
            hits.extend(scan_keys(value, "%s.%s" % (path, key)))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            hits.extend(scan_keys(value, "%s[%d]" % (path, index)))
    return hits


def make_ext():
    store, audit = make_store()
    ext = TalentDevExtensions(store)
    org = make_org(store)
    program = make_program(store, org_id=org["id"])
    return store, audit, ext, org, program


def populate(store, ext, org, program):
    """One of everything on the extension surface."""
    participation = store.enroll(
        ADMIN, program["id"], "person-001", enrolled_at="2026-10-01")
    other = store.enroll(
        ADMIN, program["id"], "person-002", enrolled_at="2026-10-01")
    session = ext.schedule_delivery_session(
        ADMIN, program["id"], "Session One", "facilitated",
        scheduled_at="2026-10-06")
    attendance = ext.record_attendance(
        ADMIN, session["id"], participation["id"], "attended")
    ext.record_attendance(ADMIN, session["id"], other["id"], "missed")
    assessment = store.create_assessment(
        ADMIN, org["id"], "Baseline", "Instrument A")
    instrument = ext.register_instrument_reference(
        ADMIN, assessment["id"])
    report = ext.record_administration_report(
        ADMIN, instrument["id"], "person-001", "administered-offsite")
    snapshot_a = store.record_snapshot(
        ADMIN, org["id"], "trend-index", "2026-Q3", 40, 10)
    snapshot_b = store.record_snapshot(
        ADMIN, org["id"], "trend-index", "2026-Q4", 50, 15)
    definition = ext.create_trend_definition(
        ADMIN, org["id"], "Trend Index Watch", "trend-index")
    model = ext.register_model_reference(
        ADMIN, org["id"], "Model Label X", "planning support")
    model_report = ext.record_model_report(
        ADMIN, model["id"], "report-filed")
    return {
        "participation": participation, "session": session,
        "attendance": attendance, "assessment": assessment,
        "instrument": instrument, "report": report,
        "snapshots": [snapshot_a, snapshot_b],
        "definition": definition, "model": model,
        "model_report": model_report,
    }


class TestDeliverySessions(unittest.TestCase):
    """Idx 930 — live development delivery, built records form."""

    def setUp(self):
        self.store, self.audit, self.ext, self.org, self.program = make_ext()
        self.participation = self.store.enroll(
            ADMIN, self.program["id"], "person-001",
            enrolled_at="2026-10-01")

    def test_session_shape_and_labels(self):
        session = self.ext.schedule_delivery_session(
            ADMIN, self.program["id"], "Session One", "facilitated",
            scheduled_at="2026-10-06")
        self.assertEqual(
            set(session),
            {"id", "program_id", "org_id", "label", "mode_label",
             "scheduled_at", "delivered_here", "content_held_here",
             "state", "created_by", "created_utc"})
        self.assertEqual(session["id"], "ses-1")
        self.assertEqual(session["org_id"], self.org["id"])
        self.assertIs(session["delivered_here"], False)
        self.assertIs(session["content_held_here"], False)
        self.assertEqual(session["state"], "recorded_session_only")

    def test_session_requires_a_known_program(self):
        with self.assertRaises(NotFoundError):
            self.ext.schedule_delivery_session(
                ADMIN, "prg-999", "Ghost", "facilitated")
        # The failed operation consumed no id.
        session = self.ext.schedule_delivery_session(
            ADMIN, self.program["id"], "Session One", "facilitated")
        self.assertEqual(session["id"], "ses-1")

    def test_attendance_binds_participation_of_same_program(self):
        other_program = make_program(
            self.store, org_id=self.org["id"], label="Other Path")
        outsider = self.store.enroll(
            ADMIN, other_program["id"], "person-009",
            enrolled_at="2026-10-01")
        session = self.ext.schedule_delivery_session(
            ADMIN, self.program["id"], "Session One", "facilitated")
        with self.assertRaises(ValidationError):
            self.ext.record_attendance(
                ADMIN, session["id"], outsider["id"], "attended")
        attendance = self.ext.record_attendance(
            ADMIN, session["id"], self.participation["id"], "attended")
        # The refused attempt consumed no id.
        self.assertEqual(attendance["id"], "att-1")
        self.assertEqual(attendance["participant_ref"], "person-001")
        self.assertIs(attendance["delivered_here"], False)

    def test_attendance_vocabulary_and_duplicate_refused(self):
        session = self.ext.schedule_delivery_session(
            ADMIN, self.program["id"], "Session One", "facilitated")
        with self.assertRaises(ValidationError):
            self.ext.record_attendance(
                ADMIN, session["id"], self.participation["id"],
                "excellent")
        self.ext.record_attendance(
            ADMIN, session["id"], self.participation["id"], "partial")
        with self.assertRaises(ValidationError):
            self.ext.record_attendance(
                ADMIN, session["id"], self.participation["id"],
                "attended")

    def test_delivery_view_is_derived_never_stored(self):
        second = self.store.enroll(
            ADMIN, self.program["id"], "person-002",
            enrolled_at="2026-10-01")
        session = self.ext.schedule_delivery_session(
            ADMIN, self.program["id"], "Session One", "facilitated")
        self.ext.record_attendance(
            ADMIN, session["id"], self.participation["id"], "attended")
        self.ext.record_attendance(
            ADMIN, session["id"], second["id"], "missed")
        stored = self.ext._sessions[session["id"]]
        self.assertNotIn("attendance_count", stored)
        view = self.ext.program_delivery_view(self.program["id"], ADMIN)
        self.assertEqual(view["session_count"], 1)
        self.assertEqual(view["attendance_count"], 2)
        self.assertEqual(view["attendances_by_label"],
                         {"attended": 1, "missed": 1})
        self.assertEqual(view["distinct_participants"], 2)
        self.assertEqual(view["latest_attendance_label"], "missed")
        self.assertIs(view["derived"], True)


class TestInstrumentReference(unittest.TestCase):
    """Idx 931 — instruments / administration / scoring engines,
    labeled reference form."""

    def setUp(self):
        self.store, self.audit, self.ext, self.org, self.program = make_ext()
        self.assessment = self.store.create_assessment(
            ADMIN, self.org["id"], "Baseline", "Instrument A")

    def test_reference_shape_and_stub_labels(self):
        reference = self.ext.register_instrument_reference(
            ADMIN, self.assessment["id"])
        self.assertEqual(
            set(reference),
            {"id", "assessment_id", "org_id", "instrument_label",
             "reference_stub", "instrument_held_here",
             "administered_here", "judged_here", "state",
             "created_by", "created_utc"})
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["instrument_held_here"], False)
        self.assertIs(reference["administered_here"], False)
        self.assertIs(reference["judged_here"], False)
        self.assertEqual(reference["instrument_label"], "Instrument A")
        self.assertEqual(reference["state"], "recorded_reference_only")

    def test_one_reference_per_assessment(self):
        self.ext.register_instrument_reference(ADMIN, self.assessment["id"])
        with self.assertRaises(ValidationError):
            self.ext.register_instrument_reference(
                ADMIN, self.assessment["id"])

    def test_report_is_verbatim_and_carries_no_number(self):
        reference = self.ext.register_instrument_reference(
            ADMIN, self.assessment["id"])
        report = self.ext.record_administration_report(
            ADMIN, reference["id"], "person-001", "administered-offsite")
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["administered_here"], False)
        self.assertEqual(report["reported_outcome_label"],
                         "administered-offsite")
        for value in report.values():
            self.assertFalse(
                isinstance(value, (int, float))
                and not isinstance(value, bool),
                "administration reports carry no numeric field") 
        view = self.ext.instrument_view(reference["id"], ADMIN)
        self.assertEqual(view["report_count"], 1)
        self.assertEqual(view["reports_by_label"],
                         {"administered-offsite": 1})
        self.assertEqual(view["latest_reported_label"],
                         "administered-offsite")

    def test_report_subject_ref_must_be_opaque(self):
        reference = self.ext.register_instrument_reference(
            ADMIN, self.assessment["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_administration_report(
                ADMIN, reference["id"], "person@example.com", "done")

    def test_reference_and_report_change_no_core_record(self):
        before_assessment = self.store.get_assessment(
            ADMIN, self.assessment["id"])
        before_summary = self.store.summary(ADMIN)
        reference = self.ext.register_instrument_reference(
            ADMIN, self.assessment["id"])
        self.ext.record_administration_report(
            ADMIN, reference["id"], "person-001", "administered-offsite")
        self.assertEqual(
            self.store.get_assessment(ADMIN, self.assessment["id"]),
            before_assessment)
        self.assertEqual(self.store.summary(ADMIN), before_summary)
        self.assertEqual(self.store.list_results(ADMIN), [])


class TestTrendDefinitions(unittest.TestCase):
    """Idx 932 — analytics / trend engine, records-and-derivation
    form."""

    def setUp(self):
        self.store, self.audit, self.ext, self.org, self.program = make_ext()
        self.store.record_snapshot(
            ADMIN, self.org["id"], "trend-index", "2026-Q3", 40, 10)
        self.store.record_snapshot(
            ADMIN, self.org["id"], "trend-index", "2026-Q4", 50, 15)
        self.store.record_snapshot(
            ADMIN, self.org["id"], "other-metric", "2026-Q4", 20, 5)

    def test_definition_shape_is_data_only(self):
        definition = self.ext.create_trend_definition(
            ADMIN, self.org["id"], "Watch", "trend-index")
        self.assertEqual(
            set(definition),
            {"id", "org_id", "label", "metric_label",
             "definition_only", "computed_here", "state",
             "created_by", "created_utc"})
        self.assertIs(definition["definition_only"], True)
        self.assertIs(definition["computed_here"], False)

    def test_trend_view_derives_sums_over_core_snapshots(self):
        definition = self.ext.create_trend_definition(
            ADMIN, self.org["id"], "Watch", "trend-index")
        stored = self.ext._trend_definitions[definition["id"]]
        self.assertNotIn("snapshot_count", stored)
        self.assertNotIn("total_recorded_cohort", stored)
        view = self.ext.trend_view(ADMIN, definition["id"])
        # Only the two trend-index snapshots join; the other
        # metric's snapshot is excluded.
        self.assertEqual(view["snapshot_count"], 2)
        self.assertEqual(view["total_recorded_cohort"], 90)
        self.assertEqual(view["total_recorded_value"], 25)
        self.assertEqual(view["latest_period_label"], "2026-Q4")
        self.assertIs(view["derived"], True)

    def test_trend_view_with_no_snapshots_is_zeroes(self):
        definition = self.ext.create_trend_definition(
            ADMIN, self.org["id"], "Empty Watch", "no-such-metric")
        view = self.ext.trend_view(ADMIN, definition["id"])
        self.assertEqual(view["snapshot_count"], 0)
        self.assertEqual(view["total_recorded_cohort"], 0)
        self.assertEqual(view["total_recorded_value"], 0)
        self.assertIsNone(view["latest_period_label"])

    def test_definition_requires_a_known_organization(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_trend_definition(
                ADMIN, "org-999", "Ghost", "trend-index")


class TestModelReference(unittest.TestCase):
    """Idx 933 — AI models, labeled reference form."""

    def setUp(self):
        self.store, self.audit, self.ext, self.org, self.program = make_ext()

    def test_reference_shape_and_stub_labels(self):
        reference = self.ext.register_model_reference(
            ADMIN, self.org["id"], "Model Label X", "planning support")
        self.assertEqual(
            set(reference),
            {"id", "org_id", "model_label", "purpose_label",
             "reference_stub", "inference_here", "model_held_here",
             "state", "created_by", "created_utc"})
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["inference_here"], False)
        self.assertIs(reference["model_held_here"], False)
        self.assertEqual(reference["state"], "recorded_reference_only")

    def test_report_is_verbatim_and_view_derives_latest(self):
        reference = self.ext.register_model_reference(
            ADMIN, self.org["id"], "Model Label X", "planning support")
        self.ext.record_model_report(ADMIN, reference["id"], "draft-filed")
        self.ext.record_model_report(ADMIN, reference["id"], "report-filed")
        view = self.ext.model_view(reference["id"], ADMIN)
        self.assertEqual(view["report_count"], 2)
        self.assertEqual(view["reports_by_label"],
                         {"draft-filed": 1, "report-filed": 1})
        self.assertEqual(view["latest_reported_label"], "report-filed")

    def test_no_inference_shaped_method_exists(self):
        for name in ("infer", "predict", "recommend", "generate",
                     "train", "run_model", "complete"):
            self.assertFalse(
                hasattr(TalentDevExtensions, name),
                "the reference surface must not grow an inference "
                "method named %r" % (name,))

    def test_reference_changes_no_core_record(self):
        before = self.store.summary(ADMIN)
        self.ext.register_model_reference(
            ADMIN, self.org["id"], "Model Label X", "planning support")
        self.assertEqual(self.store.summary(ADMIN), before)


class TestAccessAndAudit(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext, self.org, self.program = make_ext()

    def test_viewer_writes_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.schedule_delivery_session(
                VIEWER, self.program["id"], "Session", "facilitated")
        with self.assertRaises(PermissionDenied):
            self.ext.create_trend_definition(
                VIEWER, self.org["id"], "Watch", "trend-index")
        denied = [e for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertTrue(denied)
        # The denials consumed no ids.
        session = self.ext.schedule_delivery_session(
            ADMIN, self.program["id"], "Session", "facilitated")
        self.assertEqual(session["id"], "ses-1")

    def test_viewer_reads_allowed(self):
        session = self.ext.schedule_delivery_session(
            ADMIN, self.program["id"], "Session", "facilitated")
        self.assertEqual(
            self.ext.get_session(session["id"], VIEWER)["id"],
            session["id"])
        self.assertEqual(
            self.ext.extension_summary(VIEWER)["delivery_sessions"], 1)

    def test_successful_mutations_audit_with_ext_prefix(self):
        self.ext.schedule_delivery_session(
            OPERATOR, self.program["id"], "Session", "facilitated")
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_session_record", actions)


class TestScansAndSignatures(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.ext, self.org, self.program = make_ext()
        self.data = populate(self.store, self.ext, self.org, self.program)

    def _surface(self):
        ext, data = self.ext, self.data
        return [
            ext.list_sessions(ADMIN),
            ext.list_attendances(data["session"]["id"], ADMIN),
            ext.program_delivery_view(self.program["id"], ADMIN),
            ext.list_instrument_references(ADMIN),
            ext.list_administration_reports(data["instrument"]["id"], ADMIN),
            ext.instrument_view(data["instrument"]["id"], ADMIN),
            ext.list_trend_definitions(ADMIN),
            ext.trend_view(ADMIN, data["definition"]["id"]),
            ext.list_model_references(ADMIN),
            ext.list_model_reports(data["model"]["id"], ADMIN),
            ext.model_view(data["model"]["id"], ADMIN),
            ext.extension_summary(ADMIN),
        ]

    def test_no_forbidden_or_tier_keys_anywhere_on_the_surface(self):
        for haystack in self._surface():
            self.assertEqual(scan_keys(haystack), [])

    def test_no_float_values_in_stored_extension_records(self):
        stored = (list(self.ext._sessions.values())
                  + list(self.ext._attendances.values())
                  + list(self.ext._instrument_refs.values())
                  + list(self.ext._admin_reports.values())
                  + list(self.ext._trend_definitions.values())
                  + list(self.ext._model_refs.values())
                  + list(self.ext._model_reports.values()))
        self.assertTrue(stored)
        for record in stored:
            for value in record.values():
                self.assertNotIsInstance(value, float)

    def test_summary_is_counts_only(self):
        summary = self.ext.extension_summary(ADMIN)
        self.assertEqual(
            summary,
            {"delivery_sessions": 1, "attendances": 2,
             "instrument_references": 1, "administration_reports": 1,
             "trend_definitions": 1, "model_references": 1,
             "model_reports": 1})
        for value in summary.values():
            self.assertIsInstance(value, int)

    def test_no_method_accepts_content_shaped_kwargs(self):
        methods = (
            self.ext.schedule_delivery_session,
            self.ext.record_attendance,
            self.ext.register_instrument_reference,
            self.ext.record_administration_report,
            self.ext.create_trend_definition,
            self.ext.register_model_reference,
            self.ext.record_model_report,
        )
        for method in methods:
            params = inspect.signature(method).parameters.values()
            self.assertFalse(
                any(p.kind is inspect.Parameter.VAR_KEYWORD
                    for p in params),
                "%r must not accept **kwargs" % (method,))
        session = self.data["session"]
        participation = self.data["participation"]
        with self.assertRaises(TypeError):
            self.ext.record_attendance(
                ADMIN, session["id"], participation["id"], "attended",
                content="session transcript")
        with self.assertRaises(TypeError):
            self.ext.record_administration_report(
                ADMIN, self.data["instrument"]["id"], "person-001",
                "done", email="person@example.com")
        with self.assertRaises(TypeError):
            self.ext.register_model_reference(
                ADMIN, self.org["id"], "M", "p", weights="model-bytes")


def canonical_latest_label_check(ext, store, org, program):
    """The canonical expectation, written once: a program delivery
    view's latest attendance label is the label of the MOST
    RECENTLY recorded attendance, in recording order."""
    first = store.enroll(ADMIN, program["id"], "person-101",
                         enrolled_at="2026-10-01")
    second = store.enroll(ADMIN, program["id"], "person-102",
                          enrolled_at="2026-10-01")
    session = ext.schedule_delivery_session(
        ADMIN, program["id"], "Canonical Session", "facilitated")
    ext.record_attendance(ADMIN, session["id"], first["id"], "attended")
    ext.record_attendance(ADMIN, session["id"], second["id"], "missed")
    view = ext.program_delivery_view(program["id"], ADMIN)
    assert view["latest_attendance_label"] == "missed", (
        "latest attendance label was %r, not the most recently "
        "recorded label 'missed'; the latest-label seam did not "
        "read the newest record" % (view["latest_attendance_label"],))


class TestBatchNegativeControl(unittest.TestCase):
    def test_canonical_check_passes_on_the_real_derivation(self):
        store, _audit, ext, org, program = make_ext()
        canonical_latest_label_check(ext, store, org, program)

    def test_canonical_check_fails_on_the_mutant(self):
        store, _audit, ext, org, program = make_ext()
        original = TalentDevExtensions.__dict__["_latest_label"]
        TalentDevExtensions._latest_label = staticmethod(
            lambda records, key: records[0][key] if records else None)
        try:
            with self.assertRaises(AssertionError):
                canonical_latest_label_check(ext, store, org, program)
        finally:
            TalentDevExtensions._latest_label = original

    def test_single_record_view_reports_that_label_on_the_real_seam(self):
        # The discriminating other arm: with one attendance, latest
        # is that record's label under both readings — the check
        # above discriminates only because it records two distinct
        # labels in order.
        store, _audit, ext, org, program = make_ext()
        participation = store.enroll(
            ADMIN, program["id"], "person-201", enrolled_at="2026-10-01")
        session = ext.schedule_delivery_session(
            ADMIN, program["id"], "Only Session", "facilitated")
        ext.record_attendance(
            ADMIN, session["id"], participation["id"], "partial")
        view = ext.program_delivery_view(program["id"], ADMIN)
        self.assertEqual(view["latest_attendance_label"], "partial")
        self.assertIsNotNone(extensions_module)


if __name__ == "__main__":
    unittest.main()
