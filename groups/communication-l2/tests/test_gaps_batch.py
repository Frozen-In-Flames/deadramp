"""Final GAPS batch — Group 11 Communication L2 extension tests.

Traces to: GAPS.md Group 11 section (12 entries, idx 113-124),
gaps-batch/DECISION.md, PLATFORM-LAYER.md. Pins the extension surface
per entry, stub labels, derived-never-stored, and the legal-hold
disposition gate (the batch's fresh negative control seam).
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from comm_helpers import ADMIN, OPERATOR, VIEWER, make_store  # noqa: E402
from comm.errors import PermissionDenied, ValidationError  # noqa: E402
from comm.extensions import CommExtensions  # noqa: E402

FORBIDDEN_KEYS = ("latitude", "longitude", "lat", "lon", "coordinate",
                  "geofence", "address_geo", "key_material", "private_key",
                  "signature_bytes", "content", "location")


def make_ext():
    store, contact, group, channel = make_store()
    return CommExtensions(store), store, contact


def scan_keys(obj, found=None):
    if found is None:
        found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            scan_keys(v, found)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            scan_keys(v, found)
    return found


class TestArchivingReference(unittest.TestCase):
    """idx 117 — re-judged to reference: decisions + recorded states."""

    def test_capture_record_metadata_only(self):
        ext, store, contact = make_ext()
        cap = ext.record_capture("msg-ref-1", "email", "sha-ref-1", OPERATOR)
        self.assertEqual(cap["content_held"], False)
        self.assertNotIn("content", scan_keys(cap))
        self.assertTrue(cap["id"].startswith("arc-"))

    def test_disposition_eligibility_window_and_hold_gate(self):
        ext, store, contact = make_ext()
        cap = ext.record_capture("m1", "email", "c1", OPERATOR)
        pol = ext.create_retention_policy("p30", 30, OPERATOR)
        early = datetime.now(timezone.utc) + timedelta(days=10)
        late = datetime.now(timezone.utc) + timedelta(days=40)
        self.assertFalse(ext.disposition_eligibility(cap["id"], pol["id"], now=early)["eligible"])
        self.assertTrue(ext.disposition_eligibility(cap["id"], pol["id"], now=late)["eligible"])
        hold = ext.place_legal_hold(cap["id"], "matter-1", OPERATOR)
        self.assertFalse(ext.disposition_eligibility(cap["id"], pol["id"], now=late)["eligible"])
        ext.release_legal_hold(hold["id"], OPERATOR)
        self.assertTrue(ext.disposition_eligibility(cap["id"], pol["id"], now=late)["eligible"])

    def test_disposition_decision_is_reference_and_deletes_nothing(self):
        ext, store, contact = make_ext()
        cap = ext.record_capture("m1", "email", "c1", OPERATOR)
        pol = ext.create_retention_policy("p0", 0, OPERATOR)
        dec = ext.record_disposition_decision(cap["id"], pol["id"], "approve", OPERATOR)
        self.assertTrue(dec["reference_stub"])
        self.assertFalse(dec["disposition_executed"])
        self.assertTrue(dec["eligible"])
        # Capture record survives untouched.
        self.assertEqual(ext.disposition_eligibility(cap["id"], pol["id"])["capture_id"], cap["id"])

    def test_foia_production_recorded_only(self):
        ext, store, contact = make_ext()
        rec = ext.record_foia_production("case-9", "reported_in_production", OPERATOR)
        self.assertTrue(rec["reference_stub"])
        self.assertFalse(rec["produced_here"])
        self.assertFalse(rec["released_here"])

    def test_viewer_denied_capture(self):
        ext, store, contact = make_ext()
        with self.assertRaises(PermissionDenied):
            ext.record_capture("m1", "email", "c1", VIEWER)


class TestCasework(unittest.TestCase):
    """idx 118 — built."""

    def test_case_lifecycle_and_derived_overdue(self):
        ext, store, contact = make_ext()
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        case = ext.open_case("FOIA-2026-1", "foia", OPERATOR, suspense_at=past)
        self.assertEqual(case["status"], "overdue")
        self.assertNotIn("status", ext._cases[case["id"]])
        ext.record_case_step(case["id"], "acknowledged", OPERATOR)
        closed = ext.close_case(case["id"], OPERATOR)
        self.assertEqual(closed["status"], "closed")

    def test_exchange_receipt_reference_transport(self):
        ext, store, contact = make_ext()
        case = ext.open_case("C-1", "correspondence", OPERATOR)
        x = ext.record_exchange(case["id"], "org-ref-2", "outbound", OPERATOR)
        self.assertTrue(x["reference_transport"])
        self.assertFalse(x["transmitted_here"])


class TestEnvelopeProofing(unittest.TestCase):
    """idx 120 — built in records form."""

    def test_envelope_over_core_message(self):
        ext, store, contact = make_ext()
        msg = store.compose_message(OPERATOR, subject="S", body="B",
                                     contact_ids=[contact["id"]], channel_kinds=["email"])
        env = ext.record_envelope(msg["id"], "reported-aes-gcm", OPERATOR)
        self.assertTrue(env["reference_transport"])
        self.assertFalse(env["cryptography_performed"])
        self.assertFalse(env["transmitted_here"])

    def test_proofing_reported_outcome_never_decision(self):
        ext, store, contact = make_ext()
        case = ext.open_proofing_case("subj-ref-1", "document_check", OPERATOR)
        self.assertIsNone(case["current_outcome"])
        view = ext.record_proofing_outcome(case["id"], "verified_declared", OPERATOR)
        self.assertEqual(view["current_outcome"], "verified_declared")
        self.assertFalse(view["decision_made"])
        self.assertFalse(view["identity_provider"])
        self.assertNotIn("current_outcome", ext._proofing[case["id"]])


class TestTracking(unittest.TestCase):
    """idx 121 — built, MDM form: no location data anywhere."""

    def test_tracking_records_hold_no_location(self):
        ext, store, contact = make_ext()
        svc = ext.create_track_service("svc-ref-1", "fleet", OPERATOR)
        asset = ext.register_tracked_asset(svc["id"], "asset-ref-1", OPERATOR)
        ext.record_track_state(asset["id"], "reported_active", OPERATOR)
        view = ext.tracked_asset_view(asset["id"])
        self.assertEqual(view["current_state"], "reported_active")
        self.assertFalse(view["location_data_held"])
        keys = scan_keys(view) | scan_keys(asset) | scan_keys(svc)
        for bad in FORBIDDEN_KEYS:
            self.assertNotIn(bad, keys)


class TestPermitsSurveysPayments(unittest.TestCase):
    """idx 122 — built."""

    def test_permit_pass_flow_and_derived_status(self):
        ext, store, contact = make_ext()
        p = ext.apply_permit("app-ref-1", "event", OPERATOR)
        self.assertEqual(p["status"], "pending")
        self.assertNotIn("status", ext._permits[p["id"]])
        with self.assertRaises(ValidationError):
            ext.issue_pass(p["id"], OPERATOR)
        ext.decide_permit(p["id"], "approve", OPERATOR)
        pas = ext.issue_pass(p["id"], OPERATOR)
        self.assertTrue(pas["id"].startswith("pass-"))

    def test_survey_tally_derived(self):
        ext, store, contact = make_ext()
        s = ext.create_survey("Sat", ["q1", "q2"], OPERATOR)
        ext.record_survey_response(s["id"], "q1", 5, OPERATOR)
        view = ext.record_survey_response(s["id"], "q1", 4, OPERATOR)
        self.assertEqual(view["response_counts"], {"q1": 2})
        with self.assertRaises(ValidationError):
            ext.record_survey_response(s["id"], "q1", 1.5, OPERATOR)

    def test_payment_record_never_charges_and_totals_derived(self):
        ext, store, contact = make_ext()
        pay = ext.record_payment("payer-1", 2500, "recorded_authorized", OPERATOR)
        self.assertFalse(pay["charged_here"])
        self.assertFalse(pay["settled_here"])
        with self.assertRaises(ValidationError):
            ext.record_payment("payer-1", 10.5, "recorded_authorized", OPERATOR)
        totals = ext.payment_totals()
        self.assertEqual(totals["totals_by_state"], {"recorded_authorized": 2500})


class TestStubs(unittest.TestCase):
    """idx 113, 114, 115, 116, 119, 123, 124 — labeled references."""

    def test_email_security_stub(self):
        ext, store, contact = make_ext()
        prof = ext.register_email_security_profile("gw", OPERATOR)
        self.assertTrue(prof["reference_stub"])
        self.assertFalse(prof["detection_performed"])
        rep = ext.record_detection_report(prof["id"], "reported_suspicious", OPERATOR)
        self.assertTrue(rep["reference_stub"])
        self.assertFalse(rep["executed_here"])

    def test_assistant_stub_holds_no_generated_text(self):
        ext, store, contact = make_ext()
        prof = ext.register_assistant_profile("iva", OPERATOR)
        self.assertFalse(prof["inference_here"])
        self.assertFalse(prof["generated_text_held"])

    def test_telephony_and_video_stubs(self):
        ext, store, contact = make_ext()
        tel = ext.register_telephony_profile("pbx", OPERATOR)
        rep = ext.record_stub_report(tel["id"], "reported_completed", OPERATOR)
        self.assertTrue(rep["reference_transport"])
        self.assertFalse(rep["media_here"])
        vid = ext.register_video_profile("bridge", OPERATOR)
        self.assertEqual(vid["claimed_by_descriptions"], 0)
        self.assertFalse(vid["media_here"])

    def test_certificate_record_shape_no_key_material(self):
        ext, store, contact = make_ext()
        cert = ext.register_certificate_record("subj-1", "ca-label", OPERATOR)
        self.assertFalse(cert["key_material_held"])
        self.assertFalse(cert["issued_here"])
        self.assertNotIn("key_material", scan_keys(cert))
        with self.assertRaises(TypeError):
            ext.register_certificate_record("s", "ca", OPERATOR, key_material="x")

    def test_esignature_request_shape(self):
        ext, store, contact = make_ext()
        req = ext.register_signature_request("doc-1", "signer-1", OPERATOR)
        self.assertTrue(req["reference_stub"])
        self.assertFalse(req["signed_here"])
        self.assertNotIn("signature_bytes", scan_keys(req))
        out = ext.record_signature_outcome(req["id"], "reported_signed", OPERATOR)
        self.assertEqual(out["reported"], "reported_signed")

    def test_workflow_definition_never_executes_and_core_unchanged(self):
        ext, store, contact = make_ext()
        before = store.list_messages(OPERATOR)
        wf = ext.register_workflow_definition("flow", {"steps": ["a"]}, OPERATOR)
        self.assertTrue(wf["reference_stub"])
        self.assertFalse(wf["executed_here"])
        self.assertEqual(store.list_messages(OPERATOR), before)
        summary = ext.report_summary()
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["core_messages"], 0)


class TestLegalHoldGateNegativeControl(unittest.TestCase):
    """Fresh negative control: the legal-hold gate seam.

    Canonical: a capture under an active legal hold is NEVER
    disposition-eligible, even past its retention window. The mutant
    (hold check removed) would report it eligible.
    """

    def test_hold_blocks_eligibility_canonical(self):
        ext, store, contact = make_ext()
        cap = ext.record_capture("m1", "email", "c1", OPERATOR)
        pol = ext.create_retention_policy("p0", 0, OPERATOR)
        ext.place_legal_hold(cap["id"], "matter-1", OPERATOR)
        view = ext.disposition_eligibility(cap["id"], pol["id"])
        self.assertFalse(view["eligible"])
        self.assertEqual(view["active_holds"], 1)

    def test_seam_directly(self):
        from comm.extensions import _check_disposition_eligible
        now = datetime.now(timezone.utc)
        cap = {"created_utc": (now - timedelta(days=40)).isoformat()}
        pol = {"retention_days": 30}
        self.assertTrue(_check_disposition_eligible(cap, pol, False, now))
        self.assertFalse(_check_disposition_eligible(cap, pol, True, now))
        # Treating the hold-ignoring (mutant) outcome as the expected
        # outcome for a held capture must fail:
        with self.assertRaises(AssertionError):
            self.assertEqual(True, _check_disposition_eligible(cap, pol, True, now))


if __name__ == "__main__":
    unittest.main()
