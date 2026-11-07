"""Final GAPS batch tests — Singleton 47 (Law Enforcement L1).

Pins the extension surface in ``src/lawenf/extensions.py``
against the group's 5 open Extended entries (see ``../BATCH.md``):

- License plate recognition engine & camera network (idx 448) —
  reference (re-judged from build-extension): job/outcome
  records; nothing is recognized, read, or matched here, and no
  plate text or vehicle identifier exists in any field shape.
- Audio recognition sensors & detection (idx 449) — reference:
  job/outcome records; nothing is detected here.
- Video management & evidence-capture pipeline (idx 450) —
  reference: capture job/outcome records; a captured artifact is
  named by digest + byte count only, nothing is captured or
  stored here.
- Camera / sensor hardware (idx 451) — built: device
  registrations + reported status records; the devices
  themselves are not manufactured or operated here.
- Public-safety collaboration & crime-analysis platform
  (idx 452) — built: share/receipt records (transport labeled,
  nothing transmitted) and analysis/finding records (findings
  reported verbatim, never computed).

Plus the batch's fresh negative control: the latest-label seam
``_latest_label`` — a mutant that reads the earliest record
must misstate every derived "latest" label.
"""

import hashlib
import inspect
import unittest

import lawenf_helpers as helpers
from lawenf.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from lawenf.extensions import LawEnfExtensions

ADMIN = helpers.ADMIN
MEMBER = helpers.MEMBER
VIEWER = helpers.VIEWER
OUTSIDER = helpers.OUTSIDER

DOC_SHA256 = helpers.DOC_SHA256
OTHER_SHA256 = hashlib.sha256(b"captured artifact bytes").hexdigest()


def make_ext():
    """Fresh core store + audit + matter, plus the extension."""
    store, audit, matter = helpers.make_store()
    return store, audit, matter, LawEnfExtensions(store)


def make_document(store, matter_id, ref="DOC-REF-1"):
    return store.register_document(matter_id, ref, DOC_SHA256, 128, MEMBER)


class TestLprReference(unittest.TestCase):
    """Idx 448 — LPR jobs are labeled reference records; no plate
    is read and nothing is matched here."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_job_shape_and_stub_labels(self):
        job = self.ext.record_lpr_job(
            self.mid, "LPR-JOB-1", MEMBER, engine_label="vendor-lpr",
            scope_label="north-gate watch")
        self.assertEqual(job["id"], "lpr-1")
        self.assertTrue(job["reference_stub"])
        self.assertFalse(job["recognized_here"])
        self.assertFalse(job["plates_read_here"])
        self.assertFalse(job["matched_here"])
        self.assertEqual(job["status"], "recorded_reference_only")

    def test_duplicate_ref_rejected_and_no_id_consumed(self):
        self.ext.record_lpr_job(self.mid, "LPR-A", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_lpr_job(self.mid, "LPR-A", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_lpr_job(self.mid, "  ", MEMBER)
        second = self.ext.record_lpr_job(self.mid, "LPR-B", MEMBER)
        self.assertEqual(second["id"], "lpr-2")

    def test_outcome_and_view(self):
        job = self.ext.record_lpr_job(self.mid, "LPR-1", MEMBER)
        out = self.ext.record_lpr_outcome(
            self.mid, job["id"], "completed-elsewhere", MEMBER,
            result_ref="result-7", result_count=3)
        self.assertEqual(out["id"], "lpo-1")
        self.assertTrue(out["reference_stub"])
        self.assertEqual(out["result_count"], 3)
        for bad in (True, 1.5, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_lpr_outcome(
                    self.mid, job["id"], "x", MEMBER, result_count=bad)
        self.ext.record_lpr_outcome(
            self.mid, job["id"], "reviewed-elsewhere", MEMBER)
        view = self.ext.lpr_view(self.mid, job["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome"], "reviewed-elsewhere")
        # The stored job record carries no derived key.
        stored = self.ext.get_lpr_job(self.mid, job["id"], ADMIN)
        self.assertNotIn("outcome_count", stored)
        self.assertNotIn("latest_outcome", stored)

    def test_outcome_for_unknown_job_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_lpr_outcome(self.mid, "lpr-99", "x", MEMBER)


class TestAudioReference(unittest.TestCase):
    """Idx 449 — audio jobs are labeled reference records; nothing
    is detected or recognized here."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_job_shape_and_stub_labels(self):
        job = self.ext.record_audio_job(
            self.mid, "AUD-1", MEMBER, sensor_ref="sensor-ref-4",
            engine_label="vendor-audio")
        self.assertEqual(job["id"], "aud-1")
        self.assertTrue(job["reference_stub"])
        self.assertFalse(job["detected_here"])
        self.assertFalse(job["recognized_here"])
        self.assertEqual(job["status"], "recorded_reference_only")
        self.assertEqual(job["sensor_ref"], "sensor-ref-4")

    def test_outcome_and_view(self):
        job = self.ext.record_audio_job(self.mid, "AUD-1", MEMBER)
        out = self.ext.record_audio_outcome(
            self.mid, job["id"], "event-reported-elsewhere", MEMBER,
            result_ref="clip-ref-2")
        self.assertTrue(out["reference_stub"])
        self.assertEqual(out["result_ref"], "clip-ref-2")
        self.ext.record_audio_outcome(
            self.mid, job["id"], "no-event-reported", MEMBER)
        view = self.ext.audio_view(self.mid, job["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome"], "no-event-reported")


class TestCaptureReference(unittest.TestCase):
    """Idx 450 — capture jobs are labeled reference records; a
    captured artifact is named by digest + byte count only."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_job_shape_and_stub_labels(self):
        job = self.ext.record_capture_job(
            self.mid, "CAP-1", MEMBER, device_ref="device-ref-9",
            format_label="vendor-video")
        self.assertEqual(job["id"], "cap-1")
        self.assertTrue(job["reference_stub"])
        self.assertTrue(job["reference_transport"])
        self.assertFalse(job["captured_here"])
        self.assertFalse(job["stored_here"])
        self.assertFalse(job["content_held"])
        self.assertEqual(job["status"], "recorded_reference_only")

    def test_outcome_digest_discipline_and_view(self):
        job = self.ext.record_capture_job(self.mid, "CAP-1", MEMBER)
        out = self.ext.record_capture_outcome(
            self.mid, job["id"], "stored-elsewhere", MEMBER,
            output_sha256=OTHER_SHA256, size_bytes=4096)
        self.assertEqual(out["output_sha256"], OTHER_SHA256)
        self.assertEqual(out["size_bytes"], 4096)
        self.assertFalse(out["content_held"])
        with self.assertRaises(ValidationError):
            self.ext.record_capture_outcome(
                self.mid, job["id"], "x", MEMBER,
                output_sha256="not-a-digest")
        with self.assertRaises(ValidationError):
            self.ext.record_capture_outcome(
                self.mid, job["id"], "x", MEMBER, size_bytes=1.5)
        self.ext.record_capture_outcome(
            self.mid, job["id"], "retention-applied-elsewhere", MEMBER)
        view = self.ext.capture_view(self.mid, job["id"], ADMIN)
        self.assertEqual(view["outcome_count"], 2)
        self.assertEqual(view["latest_outcome"],
                         "retention-applied-elsewhere")


class TestDevicesBuilt(unittest.TestCase):
    """Idx 451 — the device registry surface; statuses are
    reported, never observed here."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_registration_shape_and_labels(self):
        dev = self.ext.register_device(
            self.mid, "DEVICE-REF-1", "fixed camera", MEMBER,
            site_ref="site-ref-3")
        self.assertEqual(dev["id"], "dev-1")
        self.assertEqual(dev["kind_label"], "fixed camera")
        self.assertFalse(dev["manufactured_here"])
        self.assertFalse(dev["content_held"])
        self.assertNotIn("reference_stub", dev)

    def test_duplicate_ref_rejected_and_no_id_consumed(self):
        self.ext.register_device(self.mid, "DEV-A", "camera", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_device(self.mid, "DEV-A", "camera", MEMBER)
        second = self.ext.register_device(self.mid, "DEV-B", "sensor",
                                          MEMBER)
        self.assertEqual(second["id"], "dev-2")

    def test_status_verbatim_and_view_derives_latest(self):
        dev = self.ext.register_device(self.mid, "DEV-1", "audio sensor",
                                       MEMBER)
        empty = self.ext.device_view(self.mid, dev["id"], ADMIN)
        self.assertEqual(empty["status_count"], 0)
        self.assertIsNone(empty["latest_status_label"])
        st = self.ext.record_device_status(
            self.mid, dev["id"], "Reported Online (vendor feed)", MEMBER)
        self.assertEqual(st["status_label"], "Reported Online (vendor feed)")
        self.ext.record_device_status(
            self.mid, dev["id"], "reported-offline", MEMBER)
        view = self.ext.device_view(self.mid, dev["id"], ADMIN)
        self.assertTrue(view["derived"])
        self.assertEqual(view["status_count"], 2)
        self.assertEqual(view["latest_status_label"], "reported-offline")
        # The stored registration carries no derived key.
        stored = self.ext.get_device(self.mid, dev["id"], ADMIN)
        self.assertNotIn("status_count", stored)
        self.assertNotIn("latest_status_label", stored)

    def test_status_for_unknown_device_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_device_status(self.mid, "dev-99", "x", MEMBER)


class TestCollaborationBuilt(unittest.TestCase):
    """Idx 452 — share records (nothing transmitted) and analysis
    records (findings reported, never computed)."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_share_shape_and_transport_labels(self):
        share = self.ext.record_share(
            self.mid, "SHARE-1", "target-ref-5", "agency-ref-2", MEMBER,
            scope_label="joint watch")
        self.assertEqual(share["id"], "csh-1")
        self.assertTrue(share["reference_transport"])
        self.assertFalse(share["transmitted_here"])
        self.assertFalse(share["shared_here"])
        self.assertFalse(share["content_held"])
        self.assertNotIn("reference_stub", share)

    def test_share_receipts_and_view(self):
        share = self.ext.record_share(
            self.mid, "SHARE-1", "target-ref-5", "agency-ref-2", MEMBER)
        rcpt = self.ext.record_share_receipt(
            self.mid, share["id"], "acknowledged-elsewhere", MEMBER)
        self.assertTrue(rcpt["reference_transport"])
        self.ext.record_share_receipt(
            self.mid, share["id"], "accepted-elsewhere", MEMBER)
        view = self.ext.collaboration_view(self.mid, share["id"], ADMIN)
        self.assertEqual(view["receipt_count"], 2)
        self.assertEqual(view["latest_outcome"], "accepted-elsewhere")

    def test_analysis_shape_and_document_binding(self):
        doc = make_document(self.store, self.mid)
        ana = self.ext.record_analysis(
            self.mid, "ANA-1", MEMBER, method_label="analyst-review",
            document_id=doc["id"])
        self.assertEqual(ana["id"], "anl-1")
        self.assertFalse(ana["analyzed_here"])
        self.assertFalse(ana["patterns_computed_here"])
        self.assertFalse(ana["content_held"])
        with self.assertRaises(NotFoundError):
            self.ext.record_analysis(
                self.mid, "ANA-2", MEMBER, document_id="doc-99")

    def test_analysis_findings_and_view(self):
        ana = self.ext.record_analysis(self.mid, "ANA-1", MEMBER)
        fin = self.ext.record_analysis_finding(
            self.mid, ana["id"], "finding-ref-1", MEMBER,
            reported_label="cluster-noted-by-analyst")
        self.assertEqual(fin["id"], "anf-1")
        self.assertFalse(fin["computed_here"])
        self.assertEqual(fin["reported_label"], "cluster-noted-by-analyst")
        self.ext.record_analysis_finding(
            self.mid, ana["id"], "finding-ref-2", MEMBER,
            reported_label="no-cluster-reported")
        view = self.ext.analysis_view(self.mid, ana["id"], ADMIN)
        self.assertEqual(view["finding_count"], 2)
        self.assertEqual(view["latest_reported_label"],
                         "no-cluster-reported")

    def test_extension_report_counts(self):
        self.ext.record_lpr_job(self.mid, "LPR-1", MEMBER)
        self.ext.register_device(self.mid, "DEV-1", "camera", MEMBER)
        self.ext.record_share(
            self.mid, "SHARE-1", "t", "r", MEMBER)
        report = self.ext.extension_report(self.mid, ADMIN)
        self.assertTrue(report["derived"])
        self.assertEqual(report["counts"]["lpr_job"], 1)
        self.assertEqual(report["counts"]["device_registration"], 1)
        self.assertEqual(report["counts"]["collaboration_share"], 1)
        self.assertEqual(report["counts"]["analysis_finding"], 0)


class TestPrivacyShapePins(unittest.TestCase):
    """The hard privacy rule over the new surface: exact key sets,
    no score-shaped key anywhere, and no signature that could
    accept content, a sensing payload, or identity."""

    BANNED_PARAMS = {
        "content", "body", "text", "plate", "plate_text",
        "plate_number", "vehicle_id", "vehicle_identifier",
        "audio", "audio_content", "video", "video_content",
        "image", "transcript", "query_text", "note_text",
        "prompt", "subject", "subject_name", "person_name",
        "name", "email", "address", "face", "facial",
    }

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]
        self.doc = make_document(self.store, self.mid)

    def test_exact_key_sets(self):
        job = self.ext.record_lpr_job(self.mid, "LPR", MEMBER)
        self.assertEqual(set(job), {
            "id", "matter_id", "job_ref", "engine_label", "scope_label",
            "reference_stub", "recognized_here", "plates_read_here",
            "matched_here", "status", "created_by", "created_utc"})
        out = self.ext.record_lpr_outcome(self.mid, job["id"], "done",
                                          MEMBER)
        self.assertEqual(set(out), {
            "id", "matter_id", "job_id", "outcome_label", "result_ref",
            "result_count", "reference_stub", "created_by", "created_utc"})
        ajob = self.ext.record_audio_job(self.mid, "AUD", MEMBER)
        self.assertEqual(set(ajob), {
            "id", "matter_id", "job_ref", "sensor_ref", "engine_label",
            "reference_stub", "detected_here", "recognized_here",
            "status", "created_by", "created_utc"})
        aout = self.ext.record_audio_outcome(self.mid, ajob["id"], "done",
                                             MEMBER)
        self.assertEqual(set(aout), {
            "id", "matter_id", "job_id", "outcome_label", "result_ref",
            "reference_stub", "created_by", "created_utc"})
        cjob = self.ext.record_capture_job(self.mid, "CAP", MEMBER)
        self.assertEqual(set(cjob), {
            "id", "matter_id", "job_ref", "device_ref", "format_label",
            "reference_stub", "reference_transport", "captured_here",
            "stored_here", "content_held", "status", "created_by",
            "created_utc"})
        cout = self.ext.record_capture_outcome(self.mid, cjob["id"],
                                               "done", MEMBER)
        self.assertEqual(set(cout), {
            "id", "matter_id", "job_id", "outcome_label", "output_sha256",
            "size_bytes", "reference_stub", "reference_transport",
            "content_held", "created_by", "created_utc"})
        dev = self.ext.register_device(self.mid, "DEV", "camera", MEMBER)
        self.assertEqual(set(dev), {
            "id", "matter_id", "device_ref", "kind_label", "site_ref",
            "manufactured_here", "content_held", "created_by",
            "created_utc"})
        dst = self.ext.record_device_status(self.mid, dev["id"], "online",
                                            MEMBER)
        self.assertEqual(set(dst), {
            "id", "matter_id", "device_id", "status_label", "created_by",
            "created_utc"})
        share = self.ext.record_share(self.mid, "SH", "t", "r", MEMBER)
        self.assertEqual(set(share), {
            "id", "matter_id", "share_ref", "target_ref", "recipient_ref",
            "scope_label", "reference_transport", "transmitted_here",
            "shared_here", "content_held", "created_by", "created_utc"})
        rcpt = self.ext.record_share_receipt(self.mid, share["id"], "ok",
                                             MEMBER)
        self.assertEqual(set(rcpt), {
            "id", "matter_id", "share_id", "outcome_label",
            "reference_transport", "created_by", "created_utc"})
        ana = self.ext.record_analysis(self.mid, "ANA", MEMBER)
        self.assertEqual(set(ana), {
            "id", "matter_id", "analysis_ref", "method_label",
            "document_id", "analyzed_here", "patterns_computed_here",
            "content_held", "created_by", "created_utc"})
        fin = self.ext.record_analysis_finding(self.mid, ana["id"], "F",
                                               MEMBER)
        self.assertEqual(set(fin), {
            "id", "matter_id", "analysis_id", "result_ref",
            "reported_label", "computed_here", "created_by",
            "created_utc"})

    def test_no_score_shaped_key_anywhere(self):
        job = self.ext.record_lpr_job(self.mid, "LPR", MEMBER)
        self.ext.record_lpr_outcome(self.mid, job["id"], "done", MEMBER)
        dev = self.ext.register_device(self.mid, "DEV", "camera", MEMBER)
        self.ext.record_device_status(self.mid, dev["id"], "online",
                                      MEMBER)
        ana = self.ext.record_analysis(self.mid, "ANA", MEMBER)
        self.ext.record_analysis_finding(self.mid, ana["id"], "F", MEMBER)
        records = [
            job, dev, ana,
            self.ext.lpr_view(self.mid, job["id"], ADMIN),
            self.ext.device_view(self.mid, dev["id"], ADMIN),
            self.ext.analysis_view(self.mid, ana["id"], ADMIN),
            self.ext.extension_report(self.mid, ADMIN),
        ]

        def scan(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    lowered = str(key).lower()
                    for banned in ("score", "rating", "risk", "rank"):
                        self.assertNotIn(banned, lowered)
                    scan(value)
            elif isinstance(node, (list, tuple)):
                for item in node:
                    scan(item)

        for record in records:
            scan(record)

    def test_no_signature_accepts_content_or_identity(self):
        for name, method in inspect.getmembers(
                LawEnfExtensions, predicate=inspect.isfunction):
            if name.startswith("_") and name != "_latest_label":
                continue
            params = inspect.signature(method).parameters
            for param in params.values():
                self.assertNotEqual(
                    param.kind, inspect.Parameter.VAR_KEYWORD,
                    "%s must not accept **kwargs" % name)
                self.assertNotIn(
                    param.name, self.BANNED_PARAMS,
                    "%s parameter %r could hold content/identity"
                    % (name, param.name))

    def test_smuggled_fields_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_lpr_job(
                self.mid, "LPR2", MEMBER, plate_text="ABC-1234")
        with self.assertRaises(TypeError):
            self.ext.record_audio_job(
                self.mid, "AUD2", MEMBER, audio=b"sound bytes")
        with self.assertRaises(TypeError):
            self.ext.record_capture_job(
                self.mid, "CAP2", MEMBER, video=b"video bytes")
        with self.assertRaises(TypeError):
            self.ext.register_device(
                self.mid, "DEV2", "camera", MEMBER,
                subject_name="a person")
        with self.assertRaises(TypeError):
            self.ext.record_share(
                self.mid, "SH2", "t", "r", MEMBER, content="evidence")
        with self.assertRaises(TypeError):
            self.ext.record_analysis(
                self.mid, "ANA2", MEMBER, prompt="predict recidivism")


class TestAccessAndBoundaries(unittest.TestCase):
    """Both founding boundaries bind the new surface."""

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_lpr_job(self.mid, "LPR", VIEWER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_lpr_job:denied", actions)

    def test_outsider_denied_by_membership(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_device(self.mid, "DEV", "camera", OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.list_devices(self.mid, OUTSIDER)

    def test_closed_matter_rejects_extension_writes(self):
        matter2 = self.store.create_matter("MATTER-REF-CLOSED", MEMBER)
        self.store.close_matter(matter2["id"], MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_device(matter2["id"], "DEV", "camera", MEMBER)

    def test_mutations_audited_and_admin_reads(self):
        dev = self.ext.register_device(self.mid, "DEV", "camera", MEMBER)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_device_register", actions)
        view = self.ext.device_view(self.mid, dev["id"], ADMIN)
        self.assertEqual(view["device_ref"], "DEV")


class _EarliestLabelExtensions(LawEnfExtensions):
    """Mutant: the latest-label seam reads the earliest record."""

    @staticmethod
    def _latest_label(records, key):
        return records[0][key] if records else None


class TestLatestLabelNegativeControl(unittest.TestCase):
    """Fresh negative control for the latest-label seam.

    Canonical expectation: a derived view's "latest" label is the
    most recently recorded one. The mutant seam reads the earliest
    record and must misstate it.
    """

    def setUp(self):
        self.store, self.audit, self.matter, self.ext = make_ext()
        self.mid = self.matter["id"]
        self.mutant = _EarliestLabelExtensions(self.store)
        dev = self.ext.register_device(self.mid, "DEV", "camera", MEMBER)
        self.device_id = dev["id"]
        self.ext.record_device_status(
            self.mid, self.device_id, "reported-online", MEMBER)
        self.ext.record_device_status(
            self.mid, self.device_id, "reported-offline", MEMBER)
        # The mutant shares the store but not the records; rebuild
        # the same stream on the mutant for a fair comparison.
        mdev = self.mutant.register_device(self.mid, "DEV", "camera",
                                           MEMBER)
        self.mdevice_id = mdev["id"]
        self.mutant.record_device_status(
            self.mid, self.mdevice_id, "reported-online", MEMBER)
        self.mutant.record_device_status(
            self.mid, self.mdevice_id, "reported-offline", MEMBER)

    def test_canonical_latest_is_most_recent(self):
        view = self.ext.device_view(self.mid, self.device_id, ADMIN)
        self.assertEqual(view["latest_status_label"], "reported-offline")
        self.assertEqual(view["status_count"], 2)

    def test_mutant_reports_earliest(self):
        view = self.mutant.device_view(self.mid, self.mdevice_id, ADMIN)
        self.assertEqual(view["latest_status_label"], "reported-online")

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(
                self.mutant.device_view(self.mid, self.mdevice_id, ADMIN)
                ["latest_status_label"],
                "reported-offline")


if __name__ == "__main__":
    unittest.main()
