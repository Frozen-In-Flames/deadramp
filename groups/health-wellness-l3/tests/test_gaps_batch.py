"""Final GAPS batch tests — Singleton 46 (Health & Wellness
L3-adjacent).

Traces to: the 5 open entries of the GAPS.md section "Singleton
46 — Health & Wellness L3-adjacent (1 fork)" (inventory idx
443–447), worked under ``gaps-batch/DECISION.md`` — see
``../BATCH.md`` for the per-entry dispositions. All five entries
are the fork's clinical engines; per the group's UNION-SPEC and
the category's hard privacy rule they may not be built on this
substrate, so every family lands as a labeled reference
implementation (``reference_stub: True``, state
``recorded_reference_only``): records of the external engines'
reported activity against opaque references, with nothing
acquired, rendered, inferred, detected, alerted, or diagnosed
here.

Pins, per family: the exact record shapes and stub labels;
reported values held verbatim and never computed (a burden figure
is stored as reported and never aggregated); derived counts and
latest labels computed at read and never stored. Pins, across
the surface: the hard privacy rule (a recursive forbidden-key
scan over every record, view, and summary; ``TypeError`` on a
smuggled keyword argument; no score-shaped or tier-shaped key
anywhere) and the High apparatus [L3] (extension writes land on
the core's hash-chained audit log and the chain verifies;
extension writes are fail-closed on audit failure; the auditor
role, ``audit_read`` only, is denied every extension read and
write while its core audit duty works; member scope mirrors the
core store's).

Plus the batch's fresh negative control: the stream-device
uniqueness seam ``_check_stream_device_unique`` — the canonical
extension refuses a second stream session for the same
participant + device reference, and a mutant subclass whose seam
never fires accepts it.
"""

import os
import tempfile
import unittest

import health_helpers as H
from health.access import can
from health.audit import AuditLog
from health.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from health.extensions import HealthExtensions

ADMIN = H.ADMIN
CLINICIAN = H.CLINICIAN
MEMBER = H.MEMBER
AUDITOR = H.AUDITOR


def make_ext(audit=None):
    """Fresh core store + program + participant, plus the extension."""
    store, program, participant = H.make_store(audit=audit)
    return store, program, participant, HealthExtensions(store)


def make_other_participant(store):
    return store.create_participant("other-ref", ADMIN)


class TestStreamReference(unittest.TestCase):
    """Idx 443 — EEG acquisition & streaming, reference form."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_ext()
        self.pid = self.participant["id"]

    def test_session_shape_and_labels(self):
        session = self.ext.create_stream_session(self.pid, "device-7",
                                                 CLINICIAN)
        self.assertEqual(session["id"], "sts-1")
        self.assertEqual(session["device_ref"], "device-7")
        self.assertTrue(session["reference_stub"])
        self.assertTrue(session["reference_transport"])
        self.assertFalse(session["signal_held_here"])
        self.assertFalse(session["streamed_here"])
        self.assertEqual(session["state"], "recorded_reference_only")

    def test_duplicate_device_ref_refused_and_no_id_consumed(self):
        self.ext.create_stream_session(self.pid, "device-7", CLINICIAN)
        with self.assertRaises(ValidationError):
            self.ext.create_stream_session(self.pid, "device-7", CLINICIAN)
        second = self.ext.create_stream_session(self.pid, "device-8",
                                                CLINICIAN)
        self.assertEqual(second["id"], "sts-2")

    def test_same_device_ref_other_participant_allowed(self):
        other = make_other_participant(self.store)
        self.ext.create_stream_session(self.pid, "device-7", CLINICIAN)
        session = self.ext.create_stream_session(other["id"], "device-7",
                                                 CLINICIAN)
        self.assertEqual(session["participant_id"], other["id"])

    def test_report_shape_and_count_validation(self):
        session = self.ext.create_stream_session(self.pid, "device-7",
                                                 CLINICIAN)
        report = self.ext.record_stream_report(
            session["id"], "streaming", 1200, CLINICIAN,
            recorded_on="2026-02-01")
        self.assertEqual(report["id"], "srp-1")
        self.assertEqual(report["participant_id"], self.pid)
        self.assertEqual(report["record_count"], 1200)
        self.assertTrue(report["reference_stub"])
        for bad in (True, 1.5, -1, "1200"):
            with self.assertRaises(ValidationError):
                self.ext.record_stream_report(session["id"], "x", bad,
                                              CLINICIAN)
        with self.assertRaises(NotFoundError):
            self.ext.record_stream_report("sts-99", "x", 1, CLINICIAN)

    def test_view_derives_counts_and_latest_label(self):
        session = self.ext.create_stream_session(self.pid, "device-7",
                                                 CLINICIAN)
        empty = self.ext.get_stream_session(session["id"], ADMIN)
        self.assertEqual(empty["report_count"], 0)
        self.assertIsNone(empty["latest_status_label"])
        self.ext.record_stream_report(session["id"], "streaming", 10,
                                      CLINICIAN)
        self.ext.record_stream_report(session["id"], "interrupted", 4,
                                      CLINICIAN)
        view = self.ext.get_stream_session(session["id"], ADMIN)
        self.assertEqual(view["report_count"], 2)
        self.assertEqual(view["latest_status_label"], "interrupted")
        stored = self.ext._stream_sessions[session["id"]]
        self.assertNotIn("report_count", stored)
        self.assertNotIn("latest_status_label", stored)

    def test_unknown_participant_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_stream_session("par-99", "device-7", CLINICIAN)


class TestReviewReference(unittest.TestCase):
    """Idx 444 — waveform review rendering, RE-JUDGED to reference."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_ext()
        self.pid = self.participant["id"]

    def test_session_shape_and_labels(self):
        review = self.ext.record_review_session(self.pid, "signal-3",
                                                CLINICIAN)
        self.assertEqual(review["id"], "rvw-1")
        self.assertTrue(review["reference_stub"])
        self.assertFalse(review["waveform_held_here"])
        self.assertFalse(review["rendered_here"])
        self.assertEqual(review["state"], "recorded_reference_only")
        with self.assertRaises(ValidationError):
            self.ext.record_review_session(self.pid, "signal-3", CLINICIAN)

    def test_outcome_verbatim_and_view(self):
        review = self.ext.record_review_session(self.pid, "signal-3",
                                                CLINICIAN)
        outcome = self.ext.record_review_outcome(
            review["id"], "reviewed — see external system", CLINICIAN,
            "2026-02-02")
        self.assertEqual(outcome["outcome_label"],
                         "reviewed — see external system")
        self.assertFalse(outcome["interpreted_here"])
        self.assertEqual(outcome["participant_id"], self.pid)
        view = self.ext.get_review_session(review["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome_label"],
                         "reviewed — see external system")
        with self.assertRaises(NotFoundError):
            self.ext.record_review_outcome("rvw-99", "x", CLINICIAN,
                                           "2026-02-02")


class TestMonitoringReference(unittest.TestCase):
    """Idx 445 — AI seizure monitoring & Seizure Burden, reference."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_ext()
        self.pid = self.participant["id"]

    def test_profile_shape_and_labels(self):
        profile = self.ext.create_monitoring_profile(self.pid, "model-2",
                                                     CLINICIAN)
        self.assertEqual(profile["id"], "mnp-1")
        self.assertTrue(profile["reference_stub"])
        self.assertFalse(profile["inference_here"])
        self.assertFalse(profile["monitoring_here"])
        self.assertEqual(profile["state"], "recorded_reference_only")

    def test_burden_value_verbatim_never_computed(self):
        profile = self.ext.create_monitoring_profile(self.pid, "model-2",
                                                     CLINICIAN)
        report = self.ext.record_burden_report(profile["id"], 12.5,
                                               CLINICIAN, "2026-02-01")
        self.assertEqual(report["burden_value"], 12.5)
        self.assertFalse(report["computed_here"])
        self.assertFalse(report["quantified_here"])
        self.ext.record_burden_report(profile["id"], 30, CLINICIAN,
                                      "2026-02-03")
        view = self.ext.get_monitoring_profile(profile["id"], ADMIN)
        self.assertEqual(view["report_count"], 2)
        # Latest is a verbatim selection of the most recent report,
        # not an aggregate: 30, not 21.25, not 42.5.
        self.assertEqual(view["latest_reported_value"], 30)

    def test_burden_value_validation(self):
        profile = self.ext.create_monitoring_profile(self.pid, "model-2",
                                                     CLINICIAN)
        for bad in (True, "high", float("nan"), float("inf")):
            with self.assertRaises(ValidationError):
                self.ext.record_burden_report(profile["id"], bad,
                                              CLINICIAN, "2026-02-01")
        with self.assertRaises(NotFoundError):
            self.ext.record_burden_report("mnp-99", 1, CLINICIAN,
                                          "2026-02-01")

    def test_summary_counts_only_no_value_aggregation(self):
        profile = self.ext.create_monitoring_profile(self.pid, "model-2",
                                                     CLINICIAN)
        self.ext.record_burden_report(profile["id"], 12.5, CLINICIAN,
                                      "2026-02-01")
        self.ext.record_burden_report(profile["id"], 30, CLINICIAN,
                                      "2026-02-03")
        summary = self.ext.monitoring_summary(self.pid, ADMIN)
        self.assertEqual(summary, {
            "participant_id": self.pid,
            "method": "deterministic_counts",
            "profiles": 1,
            "burden_reports": 2,
        })


class TestAlertReference(unittest.TestCase):
    """Idx 446 — seizure detection & alerting, reference form."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_ext()
        self.pid = self.participant["id"]

    def test_alert_shape_and_labels(self):
        alert = self.ext.record_alert_reference(
            self.pid, "alert-9", "suspected status epilepticus", CLINICIAN,
            recorded_on="2026-02-01")
        self.assertEqual(alert["id"], "alr-1")
        self.assertEqual(alert["detection_label"],
                         "suspected status epilepticus")
        self.assertTrue(alert["reference_stub"])
        self.assertTrue(alert["reference_transport"])
        self.assertFalse(alert["detected_here"])
        self.assertFalse(alert["alerted_here"])
        self.assertFalse(alert["sent_here"])
        self.assertEqual(alert["state"], "recorded_reference_only")

    def test_outcome_and_view_and_summary(self):
        alert = self.ext.record_alert_reference(self.pid, "alert-9",
                                                "detected", CLINICIAN)
        outcome = self.ext.record_alert_outcome(alert["id"], "acknowledged",
                                                CLINICIAN)
        self.assertEqual(outcome["participant_id"], self.pid)
        self.assertTrue(outcome["reference_stub"])
        view = self.ext.get_alert_reference(alert["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome_label"], "acknowledged")
        summary = self.ext.alert_summary(self.pid, ADMIN)
        self.assertEqual(summary["alerts"], 1)
        self.assertEqual(summary["alert_outcomes"], 1)
        self.assertEqual(summary["method"], "deterministic_counts")
        with self.assertRaises(NotFoundError):
            self.ext.record_alert_outcome("alr-99", "x", CLINICIAN)


class TestDiagnosticReference(unittest.TestCase):
    """Idx 447 — bedside diagnostic support, RE-JUDGED to reference."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_ext()
        self.pid = self.participant["id"]

    def test_session_shape_and_labels(self):
        session = self.ext.record_diagnostic_session(self.pid, "bedside-4",
                                                     CLINICIAN)
        self.assertEqual(session["id"], "dgs-1")
        self.assertTrue(session["reference_stub"])
        self.assertFalse(session["diagnosed_here"])
        self.assertFalse(session["support_rendered_here"])
        self.assertEqual(session["state"], "recorded_reference_only")

    def test_outcome_verbatim_and_view(self):
        session = self.ext.record_diagnostic_session(self.pid, "bedside-4",
                                                     CLINICIAN)
        outcome = self.ext.record_diagnostic_outcome(
            session["id"], "reported by external system", CLINICIAN,
            "2026-02-02")
        self.assertEqual(outcome["outcome_label"],
                         "reported by external system")
        self.assertFalse(outcome["interpreted_here"])
        view = self.ext.get_diagnostic_session(session["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome_label"],
                         "reported by external system")
        with self.assertRaises(NotFoundError):
            self.ext.record_diagnostic_outcome("dgs-99", "x", CLINICIAN,
                                               "2026-02-02")


FORBIDDEN_KEYS = {
    "name", "email", "phone", "dob", "date_of_birth", "diagnosis",
    "diagnoses", "note", "notes", "comment", "insurer", "insurance",
    "member_number", "ssn", "address", "score", "risk_score",
    "severity", "threshold", "finding", "findings", "recommendation",
    "eeg", "eeg_data", "waveform", "waveform_data", "signal",
    "signal_data", "clinical_note",
}


def _scan_keys(obj, path="root"):
    """Yield (path, key) for every dict key in a nested structure."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield path, key
            yield from _scan_keys(value, path + "." + str(key))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            yield from _scan_keys(value, "%s[%d]" % (path, index))


class TestPrivacyScans(unittest.TestCase):
    """The hard privacy rule over the whole extension surface."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_ext()
        self.pid = self.participant["id"]

    def _surface(self):
        ext = self.ext
        session = ext.create_stream_session(self.pid, "device-7", CLINICIAN)
        report = ext.record_stream_report(session["id"], "streaming", 3,
                                          CLINICIAN)
        review = ext.record_review_session(self.pid, "signal-3", CLINICIAN)
        routcome = ext.record_review_outcome(review["id"], "reviewed",
                                             CLINICIAN, "2026-02-02")
        profile = ext.create_monitoring_profile(self.pid, "model-2",
                                                CLINICIAN)
        burden = ext.record_burden_report(profile["id"], 12.5, CLINICIAN,
                                          "2026-02-01")
        alert = ext.record_alert_reference(self.pid, "alert-9", "detected",
                                           CLINICIAN)
        aoutcome = ext.record_alert_outcome(alert["id"], "acknowledged",
                                            CLINICIAN)
        dsession = ext.record_diagnostic_session(self.pid, "bedside-4",
                                                 CLINICIAN)
        doutcome = ext.record_diagnostic_outcome(
            dsession["id"], "reported", CLINICIAN, "2026-02-02")
        return [
            session, report, review, routcome, profile, burden, alert,
            aoutcome, dsession, doutcome,
            ext.get_stream_session(session["id"], ADMIN),
            ext.get_review_session(review["id"], ADMIN),
            ext.get_monitoring_profile(profile["id"], ADMIN),
            ext.get_alert_reference(alert["id"], ADMIN),
            ext.get_diagnostic_session(dsession["id"], ADMIN),
            ext.monitoring_summary(self.pid, ADMIN),
            ext.alert_summary(self.pid, ADMIN),
        ]

    def test_no_forbidden_key_anywhere(self):
        for obj in self._surface():
            for path, key in _scan_keys(obj):
                self.assertNotIn(key, FORBIDDEN_KEYS,
                                 "%s carries forbidden key %r" % (path, key))
                self.assertFalse(str(key).endswith("_score"),
                                 "%s carries score-shaped key %r" % (path, key))

    def test_no_tier_or_baseline_key_anywhere(self):
        for obj in self._surface():
            for path, key in _scan_keys(obj):
                lowered = str(key).lower()
                for fragment in ("tier", "baseline", "cmmc", "fedramp"):
                    self.assertNotIn(fragment, lowered,
                                     "%s carries %r in key %r"
                                     % (path, fragment, key))

    def test_smuggled_keyword_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.create_stream_session(self.pid, "device-7", CLINICIAN,
                                           diagnosis="seizure")
        with self.assertRaises(TypeError):
            self.ext.record_review_session(self.pid, "signal-3", CLINICIAN,
                                           waveform=[1, 2, 3])
        with self.assertRaises(TypeError):
            self.ext.record_alert_reference(self.pid, "alert-9", "detected",
                                            CLINICIAN, patient_name="x")
        with self.assertRaises(TypeError):
            self.ext.record_diagnostic_outcome("dgs-1", "x", CLINICIAN,
                                               "2026-02-02", finding="y")


class TestHighApparatus(unittest.TestCase):
    """[L3] The High apparatus binds the extension surface."""

    def setUp(self):
        self.store, self.program, self.participant, self.ext = make_ext()
        self.pid = self.participant["id"]

    def test_extension_writes_on_hash_chain_and_chain_verifies(self):
        audit = self.store.audit
        session = self.ext.create_stream_session(self.pid, "device-7",
                                                 CLINICIAN)
        self.ext.record_stream_report(session["id"], "streaming", 3,
                                      CLINICIAN)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("ext_stream_session_create", actions)
        self.assertIn("ext_stream_report_record", actions)
        self.assertEqual(audit.verify_chain(), (True, None))

    def test_auditor_denied_extension_but_audit_duty_works(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_stream_session(self.pid, "device-7", AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.list_stream_sessions(AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.monitoring_summary(self.pid, AUDITOR)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_stream_session_create:denied", actions)
        # The auditor's own duty is untouched: it holds audit_read
        # and the chain over core + extension entries verifies.
        self.assertTrue(can(AUDITOR, "audit_read"))
        self.assertEqual(self.store.audit.verify_chain(), (True, None))
        self.assertTrue(self.store.audit.query(action="participant_create"))

    def test_member_scope_and_member_write_denied(self):
        other = make_other_participant(self.store)
        mine = self.ext.create_stream_session(self.pid, "device-7",
                                              CLINICIAN)
        self.ext.create_stream_session(other["id"], "device-8", CLINICIAN)
        own = self.ext.list_stream_sessions(MEMBER)
        self.assertEqual([s["id"] for s in own], [mine["id"]])
        with self.assertRaises(PermissionDenied):
            self.ext.get_stream_session(
                self.ext.list_stream_sessions(ADMIN,
                                              participant_id=other["id"]
                                              )[0]["id"], MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.create_stream_session(self.pid, "device-9", MEMBER)

    def test_extension_write_fail_closed_on_audit_failure(self):
        """AU-5: a broken audit path rolls the extension write back
        in full -- no record, no id consumed, chain intact."""
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(os.path.join(tmp, "audit.jsonl"))
            store, program, participant, ext = make_ext(audit=audit)
            before = audit.entries()
            if os.path.exists(audit.path):
                os.remove(audit.path)
            os.mkdir(audit.path)
            with self.assertRaises(AuditWriteError):
                ext.create_stream_session(participant["id"], "device-7",
                                          CLINICIAN)
            self.assertEqual(audit.entries(), before)
            self.assertEqual(audit.verify_chain(), (True, None))
            store.audit = AuditLog()
            session = ext.create_stream_session(participant["id"],
                                                "device-7", CLINICIAN)
            self.assertEqual(session["id"], "sts-1")


class _NoDeviceGuardExtensions(HealthExtensions):
    """Mutant: the stream-device uniqueness seam never fires."""

    def _check_stream_device_unique(self, participant_id, device_ref):
        return None


class TestStreamDeviceUniqueNegativeControl(unittest.TestCase):
    """Fresh negative control for the new code.

    Canonical expectation: a second stream session for the same
    participant + device reference is refused. The mutant seam
    accepts it, misstating the registry (two session records for
    one reported stream).
    """

    def _fixture(self, ext_cls=HealthExtensions):
        store, program, participant = H.make_store()
        return participant, ext_cls(store)

    def test_canonical_refuses_duplicate(self):
        participant, ext = self._fixture()
        ext.create_stream_session(participant["id"], "device-7", CLINICIAN)
        with self.assertRaises(ValidationError):
            ext.create_stream_session(participant["id"], "device-7",
                                      CLINICIAN)
        self.assertEqual(len(ext.list_stream_sessions(ADMIN)), 1)

    def test_mutant_accepts_duplicate(self):
        participant, ext = self._fixture(_NoDeviceGuardExtensions)
        ext.create_stream_session(participant["id"], "device-7", CLINICIAN)
        ext.create_stream_session(participant["id"], "device-7", CLINICIAN)
        self.assertEqual(len(ext.list_stream_sessions(ADMIN)), 2)

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        participant, ext = self._fixture(_NoDeviceGuardExtensions)
        ext.create_stream_session(participant["id"], "device-7", CLINICIAN)
        ext.create_stream_session(participant["id"], "device-7", CLINICIAN)
        with self.assertRaises(AssertionError):
            self.assertEqual(len(ext.list_stream_sessions(ADMIN)), 1)


if __name__ == "__main__":
    unittest.main()
