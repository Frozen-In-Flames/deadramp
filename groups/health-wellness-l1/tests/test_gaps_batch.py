"""Final GAPS batch tests — Health & Wellness L1 singleton.

Covers the extension surface in ``health.extensions`` (see
``../BATCH.md`` for the per-entry dispositions): the two open
entries of the "Remainder Singleton 61 — Health & Wellness L1"
section, both shipped as labeled reference implementations after
re-judgment (idx 711 dispatch & device initialization; idx 712
results collection & provider review).

Traces to: the category's HARD PRIVACY RULE (UNION-SPEC.md) —
records and opaque references only; no diagnosis, clinical note,
identifier, study-data, result, or hardware-identifier field
exists in any shape — the L1 baseline (Low / FAR 52.204-21:
plain append-only audit, no hash chain / lockout / auditor
tightening inherited downward), and the core doctrines
(derived-never-stored, RBAC before mutation, member scope).

Run with: PYTHONPATH=src python3 -m unittest discover -s tests
"""

import unittest

from health.access import User
from health.errors import NotFoundError, PermissionDenied, ValidationError
from health.extensions import HealthExtensions
from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER, make_store

FORBIDDEN_KEYS = {
    "name", "email", "phone", "address", "dob", "date_of_birth", "ssn",
    "diagnosis", "note", "notes", "clinical_note", "member_number",
    "insurer", "insurance_number", "result", "results", "test_result",
    "finding", "findings", "waveform", "signal", "study_data",
    "payload", "serial", "serial_number", "imei", "score", "rating",
}


def _scan_forbidden(obj, path="root"):
    """Recursively assert no forbidden key appears anywhere."""
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                hits.append("%s.%s" % (path, key))
            hits.extend(_scan_forbidden(value, "%s.%s" % (path, key)))
    elif isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            hits.extend(_scan_forbidden(value, "%s[%d]" % (path, i)))
    return hits


def make_extensions():
    store, program, participant = make_store()
    return store, program, participant, HealthExtensions(store)


class TestDispatchReferences(unittest.TestCase):
    """Idx 711: dispatch references — reference_stub form, labels."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_extensions()

    def test_create_shape_and_labels(self):
        record = self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN,
            program_id=self.program["id"], requested_on="2026-06-01")
        self.assertEqual(record["id"], "dsp-1")
        self.assertEqual(record["participant_id"], self.participant["id"])
        self.assertEqual(record["program_id"], self.program["id"])
        self.assertEqual(record["device_ref"], "watchpat-unit-7")
        self.assertTrue(record["reference_stub"])
        self.assertFalse(record["dispatched_here"])
        self.assertFalse(record["initialized_here"])
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertNotIn("outcome_count", record)
        self.assertNotIn("latest_outcome_label", record)

    def test_program_optional_and_unknown_refs_refused(self):
        record = self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN)
        self.assertIsNone(record["program_id"])
        with self.assertRaises(NotFoundError):
            self.ext.create_dispatch_reference(
                "par-999", "watchpat-unit-8", CLINICIAN)
        with self.assertRaises(NotFoundError):
            self.ext.create_dispatch_reference(
                self.participant["id"], "watchpat-unit-8", CLINICIAN,
                program_id="prg-999")

    def test_bad_date_and_empty_device_ref_refused_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_dispatch_reference(
                self.participant["id"], "watchpat-unit-7", CLINICIAN,
                requested_on="June 1 2026")
        with self.assertRaises(ValidationError):
            self.ext.create_dispatch_reference(
                self.participant["id"], "  ", CLINICIAN)
        record = self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN)
        self.assertEqual(record["id"], "dsp-1")

    def test_duplicate_device_for_same_participant_refused(self):
        self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.create_dispatch_reference(
                self.participant["id"], "watchpat-unit-7", CLINICIAN)
        other = self.store.create_participant("dave", ADMIN)
        record = self.ext.create_dispatch_reference(
            other["id"], "watchpat-unit-7", CLINICIAN)
        self.assertEqual(record["id"], "dsp-2")

    def test_member_and_auditor_writes_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_dispatch_reference(
                self.participant["id"], "watchpat-unit-7", MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.create_dispatch_reference(
                self.participant["id"], "watchpat-unit-7", AUDITOR)
        denied = [e for e in self.store.audit.entries()
                  if e["action"] == "ext_dispatch_reference_create:denied"]
        self.assertEqual(len(denied), 2)
        record = self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN)
        self.assertEqual(record["id"], "dsp-1")


class TestInitializationOutcomes(unittest.TestCase):
    """Idx 711: initialization outcomes recorded verbatim; view derives."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_extensions()
        self.dispatch = self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN,
            program_id=self.program["id"])

    def test_outcome_records_and_derived_view(self):
        first = self.ext.record_initialization_outcome(
            self.dispatch["id"], "initialized", CLINICIAN,
            occurred_on="2026-06-02")
        self.assertEqual(first["id"], "ini-1")
        self.assertEqual(first["participant_id"], self.participant["id"])
        self.assertTrue(first["reference_stub"])
        self.assertFalse(first["initialized_here"])
        view = self.ext.get_dispatch_reference(self.dispatch["id"], CLINICIAN)
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome_label"], "initialized")
        self.ext.record_initialization_outcome(
            self.dispatch["id"], "initialization_failed", CLINICIAN)
        view = self.ext.get_dispatch_reference(self.dispatch["id"], CLINICIAN)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome_label"], "initialization_failed")
        stored = self.ext.list_dispatch_references(CLINICIAN)[0]
        self.assertIn("outcome_count", stored)  # views derive; raw lists too
        raw = self.ext._dispatch_references[self.dispatch["id"]]
        self.assertNotIn("outcome_count", raw)
        self.assertNotIn("latest_outcome_label", raw)

    def test_unknown_dispatch_refused(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_initialization_outcome(
                "dsp-999", "initialized", CLINICIAN)

    def test_dispatch_summary_counts(self):
        other = self.store.create_participant("dave", ADMIN)
        self.ext.create_dispatch_reference(other["id"], "watchpat-unit-9",
                                           CLINICIAN)
        self.ext.record_initialization_outcome(
            self.dispatch["id"], "initialized", CLINICIAN)
        summary = self.ext.dispatch_summary(AUDITOR)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["dispatches"], 2)
        self.assertEqual(summary["initialization_outcomes"], 1)
        self.assertEqual(summary["by_latest_outcome"], {"initialized": 1})
        self.assertEqual(summary["without_outcome"], 1)
        scoped = self.ext.dispatch_summary(
            ADMIN, participant_id=self.participant["id"])
        self.assertEqual(scoped["dispatches"], 1)
        self.assertEqual(scoped["without_outcome"], 0)


class TestCollectionReferences(unittest.TestCase):
    """Idx 712: collection references — metadata only, never content."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_extensions()

    def test_create_shape_and_labels(self):
        record = self.ext.record_collection_reference(
            self.participant["id"], "study-ext-42", CLINICIAN,
            record_count=128, program_id=self.program["id"],
            collected_on="2026-06-03")
        self.assertEqual(record["id"], "col-1")
        self.assertEqual(record["study_ref"], "study-ext-42")
        self.assertEqual(record["record_count"], 128)
        self.assertTrue(record["reference_stub"])
        self.assertTrue(record["reference_transport"])
        self.assertFalse(record["content_held_here"])
        self.assertFalse(record["collected_here"])
        self.assertEqual(record["state"], "recorded_reference_only")

    def test_record_count_validation(self):
        for bad in (True, 1.5, -1, "12"):
            with self.assertRaises(ValidationError):
                self.ext.record_collection_reference(
                    self.participant["id"], "study-ext-42", CLINICIAN,
                    record_count=bad)
        record = self.ext.record_collection_reference(
            self.participant["id"], "study-ext-42", CLINICIAN, record_count=0)
        self.assertEqual(record["id"], "col-1")

    def test_review_outcomes_and_derived_view(self):
        collection = self.ext.record_collection_reference(
            self.participant["id"], "study-ext-42", CLINICIAN,
            record_count=128)
        outcome = self.ext.record_review_outcome(
            collection["id"], "reviewed", CLINICIAN, reviewed_on="2026-06-04")
        self.assertEqual(outcome["id"], "rvw-1")
        self.assertEqual(outcome["participant_id"], self.participant["id"])
        self.assertTrue(outcome["reference_stub"])
        self.assertFalse(outcome["decided_here"])
        self.assertFalse(outcome["interpreted_here"])
        view = self.ext.get_collection_reference(collection["id"], CLINICIAN)
        self.assertEqual(view["review_count"], 1)
        self.assertEqual(view["latest_outcome_label"], "reviewed")
        raw = self.ext._collection_references[collection["id"]]
        self.assertNotIn("review_count", raw)
        self.assertNotIn("latest_outcome_label", raw)
        with self.assertRaises(NotFoundError):
            self.ext.record_review_outcome("col-999", "reviewed", CLINICIAN)

    def test_collection_summary_is_sum_of_reports(self):
        first = self.ext.record_collection_reference(
            self.participant["id"], "study-ext-42", CLINICIAN,
            record_count=128)
        self.ext.record_collection_reference(
            self.participant["id"], "study-ext-43", CLINICIAN, record_count=7)
        self.ext.record_review_outcome(first["id"], "reviewed", CLINICIAN)
        self.ext.record_review_outcome(first["id"], "reviewed", CLINICIAN)
        summary = self.ext.collection_summary(AUDITOR)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["collections"], 2)
        self.assertEqual(summary["reported_records_total"], 135)
        self.assertEqual(summary["reviews"], 2)
        self.assertEqual(summary["by_outcome"], {"reviewed": 2})


class TestMemberScopeAndAudit(unittest.TestCase):
    """Member scope mirrors the core store's; audit carries ext_ actions."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_extensions()
        self.other = self.store.create_participant("dave", ADMIN)
        self.own_dispatch = self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN)
        self.other_dispatch = self.ext.create_dispatch_reference(
            self.other["id"], "watchpat-unit-8", CLINICIAN)
        self.own_collection = self.ext.record_collection_reference(
            self.participant["id"], "study-ext-42", CLINICIAN, record_count=3)
        self.ext.record_collection_reference(
            self.other["id"], "study-ext-99", CLINICIAN, record_count=5)

    def test_member_reads_own_only(self):
        own = self.ext.list_dispatch_references(MEMBER)
        self.assertEqual([d["id"] for d in own], [self.own_dispatch["id"]])
        view = self.ext.get_dispatch_reference(self.own_dispatch["id"], MEMBER)
        self.assertEqual(view["id"], self.own_dispatch["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.get_dispatch_reference(self.other_dispatch["id"], MEMBER)
        collections = self.ext.list_collection_references(MEMBER)
        self.assertEqual([c["id"] for c in collections],
                         [self.own_collection["id"]])

    def test_member_denied_summaries(self):
        with self.assertRaises(PermissionDenied):
            self.ext.dispatch_summary(MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.collection_summary(MEMBER)

    def test_audit_actions_present(self):
        self.ext.record_initialization_outcome(
            self.own_dispatch["id"], "initialized", CLINICIAN)
        self.ext.record_review_outcome(
            self.own_collection["id"], "reviewed", CLINICIAN)
        actions = {e["action"] for e in self.store.audit.entries()}
        for expected in ("ext_dispatch_reference_create",
                         "ext_initialization_outcome_record",
                         "ext_collection_reference_record",
                         "ext_review_outcome_record"):
            self.assertIn(expected, actions)


class TestPrivacyDiscipline(unittest.TestCase):
    """The hard privacy rule, pinned over the whole extension surface."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_extensions()
        self.dispatch = self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN,
            program_id=self.program["id"])
        self.ext.record_initialization_outcome(
            self.dispatch["id"], "initialized", CLINICIAN)
        self.collection = self.ext.record_collection_reference(
            self.participant["id"], "study-ext-42", CLINICIAN,
            record_count=128)
        self.ext.record_review_outcome(
            self.collection["id"], "reviewed", CLINICIAN)

    def test_no_forbidden_key_anywhere(self):
        surface = [
            self.ext.get_dispatch_reference(self.dispatch["id"], ADMIN),
            self.ext.list_dispatch_references(ADMIN),
            self.ext.list_initialization_outcomes(ADMIN),
            self.ext.dispatch_summary(ADMIN),
            self.ext.get_collection_reference(self.collection["id"], ADMIN),
            self.ext.list_collection_references(ADMIN),
            self.ext.list_review_outcomes(ADMIN),
            self.ext.collection_summary(ADMIN),
        ]
        for obj in surface:
            self.assertEqual(_scan_forbidden(obj), [], repr(obj))

    def test_smuggled_kwargs_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.create_dispatch_reference(
                self.participant["id"], "watchpat-unit-8", CLINICIAN,
                diagnosis="obstructive sleep apnea")
        with self.assertRaises(TypeError):
            self.ext.record_collection_reference(
                self.participant["id"], "study-ext-43", CLINICIAN,
                results="AHI 12.4")
        with self.assertRaises(TypeError):
            self.ext.record_review_outcome(
                self.collection["id"], "reviewed", CLINICIAN,
                finding="mild apnea")
        self.assertEqual(
            len(self.ext.list_dispatch_references(ADMIN)), 1)
        self.assertEqual(
            len(self.ext.list_collection_references(ADMIN)), 1)

    def test_every_record_is_a_labeled_reference(self):
        records = (
            self.ext.list_dispatch_references(ADMIN)
            + self.ext.list_initialization_outcomes(ADMIN)
            + self.ext.list_collection_references(ADMIN)
            + self.ext.list_review_outcomes(ADMIN))
        self.assertEqual(len(records), 4)
        for record in records:
            self.assertTrue(record["reference_stub"], record["id"])
            self.assertEqual(record["state"], "recorded_reference_only")


class _NoDispatchDeviceGuard(HealthExtensions):
    """Mutant: the dispatch device-uniqueness seam is neutralized.

    Mirrors the canonical seam's removal: dispatch references no
    longer refuse a second reference for the same participant +
    device pair, so one device can be dispatch-referenced to the
    same participant twice.
    """

    def _check_dispatch_device_unique(self, participant_id, device_ref):
        return None


class TestDispatchDeviceUniqueNegativeControl(unittest.TestCase):
    """Negative control for the dispatch device-uniqueness seam.

    The traced claim: a dispatch reference names exactly one
    reported dispatch of a device to a participant, so a second
    dispatch reference for the same participant + ``device_ref``
    pair is refused. For the canonical case the test asserts the
    refusal, that the mutant would NOT refuse (it accepts, leaving
    two dispatch references for one device), and -- via a literal
    assertRaises -- that treating the mutant's outcome as the
    expected outcome fails.
    """

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_extensions()
        self.mutant = _NoDispatchDeviceGuard(self.store)
        # The mutant is the canonical class with only the seam
        # neutralized, so it must operate on the SAME extension
        # tables; otherwise its acceptance would prove nothing
        # about the canonical registry.
        self.mutant._dispatch_references = self.ext._dispatch_references
        self.mutant._initialization_outcomes = \
            self.ext._initialization_outcomes
        self.mutant._counters = self.ext._counters

    def test_duplicate_refused_canonical_but_mutant_accepts(self):
        self.ext.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN)
        # Canonical: the duplicate is refused.
        with self.assertRaises(ValidationError):
            self.ext.create_dispatch_reference(
                self.participant["id"], "watchpat-unit-7", CLINICIAN)
        canonical = self.ext.list_dispatch_references(ADMIN)
        self.assertEqual(len(canonical), 1)
        # Mutant: the same duplicate is accepted -- the seam is the
        # only thing standing between the registry and a double
        # dispatch of one device.
        accepted = self.mutant.create_dispatch_reference(
            self.participant["id"], "watchpat-unit-7", CLINICIAN)
        self.assertEqual(accepted["device_ref"], "watchpat-unit-7")
        mutant_records = [
            d for d in self.mutant.list_dispatch_references(ADMIN)
            if d["device_ref"] == "watchpat-unit-7"]
        self.assertEqual(len(mutant_records), 2)
        # Treating the mutant's outcome (two references) as the
        # canonical expectation must fail.
        with self.assertRaises(AssertionError):
            self.assertEqual(len(canonical), len(mutant_records))

    def test_rbac_gate_companion(self):
        """A member creating a dispatch reference is denied outright."""
        with self.assertRaises(PermissionDenied):
            self.ext.create_dispatch_reference(
                self.participant["id"], "watchpat-unit-7", MEMBER)
        self.assertEqual(self.ext.list_dispatch_references(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
