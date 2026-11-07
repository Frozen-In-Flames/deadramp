"""Final GAPS batch tests -- Group 14, Communication L3-adjacent.

Pins the extension surface in ``src/comm/extensions.py`` for the 6
Extended entries of the Group 14 section (inventory idx 163-168).
All six close ``reference``: definitions, profiles, attempts and
reported outcomes, every record labeled ``reference_stub: True``,
with the operating half stated absent on the record. Also pins the
house doctrines on the new surface: derived-never-stored (workflow
current outcome, certificate current event / validity state,
carried payment totals, report summary), RBAC through the core
access module with denied attempts audited ``:denied``, the High
apparatus (auditor holds no extension permission; the hash-chained
audit trail verifies after extension operations), failed
operations consume no ids, and no record shape can hold content,
key material, or media (content-shaped kwargs raise ``TypeError``).

The fresh negative control targets the module seam
``_latest_label``: the current reported label of an append-only
stream is its LATEST record's label.
"""

import inspect
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from comm import extensions as ext_mod  # noqa: E402
from comm.errors import NotFoundError, PermissionDenied, ValidationError  # noqa: E402
from comm.extensions import CommExtensions  # noqa: E402
from comm_helpers import ADMIN, AUDITOR, OPERATOR, VIEWER, make_store  # noqa: E402


def fresh_extensions():
    store, contact, group, channel = make_store()
    return CommExtensions(store), store, contact


class TestWorkflowReference(unittest.TestCase):
    """idx 163 -- workflow / BPM engines (reference)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_extensions()

    def test_definition_shape_and_labels(self):
        rec = self.ext.record_workflow_definition(
            "intake", ["receive", "approve", "dispatch"], OPERATOR)
        self.assertEqual(rec["id"], "wfl-1")
        self.assertEqual(rec["steps"], ["receive", "approve", "dispatch"])
        self.assertIs(rec["reference_stub"], True)
        self.assertIs(rec["definition_only"], True)
        self.assertIs(rec["executed_here"], False)
        self.assertIs(rec["approvals_enforced_here"], False)
        self.assertEqual(rec["created_by"], "bob")

    def test_definition_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.record_workflow_definition("x", [], OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_workflow_definition("x", ["ok", ""], OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_workflow_definition("", ["ok"], OPERATOR)

    def test_current_outcome_derived_from_latest(self):
        w = self.ext.record_workflow_definition("intake", ["receive"], OPERATOR)
        view = self.ext.workflow_view(w["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "unreported")
        self.assertEqual(view["outcome_count"], 0)
        self.ext.record_workflow_outcome(w["id"], "reported_running", OPERATOR)
        self.ext.record_workflow_outcome(w["id"], "reported_completed", OPERATOR)
        view = self.ext.workflow_view(w["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "reported_completed")
        self.assertEqual(view["outcome_count"], 2)
        # Stored definition carries no derived key.
        self.assertNotIn("current_outcome", view["definition"])
        self.assertNotIn("status", view["definition"])

    def test_outcome_unknown_workflow(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_workflow_outcome("wfl-99", "reported_x", OPERATOR)

    def test_registry_never_executes_core_records_unchanged(self):
        before = len(self.store.list_messages(OPERATOR))
        w = self.ext.record_workflow_definition("intake", ["receive"], OPERATOR)
        self.ext.record_workflow_outcome(w["id"], "reported_completed", OPERATOR)
        self.assertEqual(len(self.store.list_messages(OPERATOR)), before)


class TestTransportReference(unittest.TestCase):
    """idx 164 -- E2E transport / fax networks / carrier (reference)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_extensions()

    def test_profile_shape_and_labels(self):
        rec = self.ext.record_transport_profile("fax_network", "gov-fax", OPERATOR)
        self.assertEqual(rec["id"], "trp-1")
        self.assertIs(rec["reference_stub"], True)
        self.assertIs(rec["reference_transport"], True)
        self.assertIs(rec["transmitted_here"], False)
        self.assertIs(rec["cryptography_performed"], False)
        self.assertIs(rec["carrier_connected_here"], False)

    def test_profile_kind_validated(self):
        with self.assertRaises(ValidationError):
            self.ext.record_transport_profile("smoke_signal", "x", OPERATOR)

    def test_attempt_binds_message_and_dispatches_nothing(self):
        profile = self.ext.record_transport_profile("e2e_message_transport", "e2e", OPERATOR)
        msg = self.store.compose_message(
            OPERATOR, subject="Hi", body="Hello",
            contact_ids=[self.contact["id"]], channel_kinds=["email"])
        attempt = self.ext.record_transport_attempt(profile["id"], OPERATOR, message_id=msg["id"])
        self.assertIs(attempt["reference_transport"], True)
        self.assertIs(attempt["delivered_here"], False)
        self.assertIs(attempt["transmitted_here"], False)
        deliveries = self.store.list_deliveries(msg["id"], OPERATOR)
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0]["status"], "queued")
        self.assertIsNone(deliveries[0].get("receipt"))

    def test_attempt_unknown_message(self):
        profile = self.ext.record_transport_profile("fax_network", "f", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_transport_attempt(profile["id"], OPERATOR, message_id="msg-99")

    def test_content_kwargs_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_transport_attempt("trp-1", OPERATOR, body="secret")
        with self.assertRaises(TypeError):
            self.ext.record_transport_profile("fax_network", "f", OPERATOR, content="x")


class TestCertificateReference(unittest.TestCase):
    """idx 165 -- key & certificate lifecycle automation (reference)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_extensions()

    def _cert(self):
        return self.ext.record_certificate(
            "device-ref-1", "Example CA", "2026-01-01T00:00:00+00:00",
            "2027-01-01T00:00:00+00:00", ADMIN)

    def test_certificate_exact_shape_no_key_material(self):
        rec = self._cert()
        self.assertEqual(set(rec.keys()), {
            "id", "subject_ref", "issuer_label", "not_before", "not_after",
            "reference_stub", "key_material_held", "issued_here", "deployed_here",
            "created_by", "created_utc"})
        self.assertIs(rec["key_material_held"], False)
        self.assertIs(rec["issued_here"], False)
        self.assertIs(rec["deployed_here"], False)

    def test_key_material_kwarg_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_certificate(
                "s", "CA", "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00",
                ADMIN, key_material="AAAA")

    def test_certificate_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_certificate(
                "s", "CA", "2026-01-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00", OPERATOR)

    def test_validity_window_validated(self):
        with self.assertRaises(ValidationError):
            self.ext.record_certificate(
                "s", "CA", "2027-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", ADMIN)

    def test_current_event_and_validity_derived_at_read(self):
        cert = self._cert()
        view = self.ext.certificate_view(cert["id"], OPERATOR, at="2026-06-01T00:00:00+00:00")
        self.assertEqual(view["current_event"], "none_reported")
        self.assertEqual(view["validity_state"], "within_validity")
        view = self.ext.certificate_view(cert["id"], OPERATOR, at="2025-06-01T00:00:00+00:00")
        self.assertEqual(view["validity_state"], "not_yet_valid")
        view = self.ext.certificate_view(cert["id"], OPERATOR, at="2028-06-01T00:00:00+00:00")
        self.assertEqual(view["validity_state"], "past_validity")
        self.ext.record_certificate_event(cert["id"], "reported_issued", ADMIN)
        self.ext.record_certificate_event(cert["id"], "reported_revoked", ADMIN)
        view = self.ext.certificate_view(cert["id"], OPERATOR, at="2026-06-01T00:00:00+00:00")
        self.assertEqual(view["current_event"], "reported_revoked")
        self.assertEqual(view["event_count"], 2)
        self.assertNotIn("current_event", view["certificate"])
        self.assertNotIn("validity_state", view["certificate"])

    def test_event_label_validated(self):
        cert = self._cert()
        with self.assertRaises(ValidationError):
            self.ext.record_certificate_event(cert["id"], "issued_for_real", ADMIN)


class TestVoiceReference(unittest.TestCase):
    """idx 166 -- voice / IVR / virtual-agent engines (reference)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_extensions()

    def test_profile_shape_and_labels(self):
        rec = self.ext.record_voice_profile("virtual_agent", "agent", OPERATOR)
        self.assertEqual(rec["id"], "vcp-1")
        self.assertIs(rec["reference_stub"], True)
        self.assertIs(rec["reference_transport"], True)
        self.assertIs(rec["media_here"], False)
        self.assertIs(rec["calls_placed_here"], False)
        self.assertIs(rec["conversation_performed"], False)
        self.assertIs(rec["generated_text_held"], False)

    def test_session_report_binds_contact(self):
        profile = self.ext.record_voice_profile("ivr_engine", "ivr", OPERATOR)
        rep = self.ext.record_voice_session_report(
            profile["id"], "reported_completed", OPERATOR, contact_id=self.contact["id"])
        self.assertEqual(rep["outcome_label"], "reported_completed")
        self.assertIs(rep["media_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.record_voice_session_report(
                profile["id"], "reported_x", OPERATOR, contact_id="ct-99")

    def test_transcript_kwarg_raises_type_error(self):
        profile = self.ext.record_voice_profile("ivr_engine", "ivr", OPERATOR)
        with self.assertRaises(TypeError):
            self.ext.record_voice_session_report(
                profile["id"], "reported_x", OPERATOR, transcript="hello")


class TestDeliveryReference(unittest.TestCase):
    """idx 167 -- workspace streaming / edge / CDN (reference)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_extensions()

    def test_profile_shape_and_labels(self):
        rec = self.ext.record_delivery_profile("workspace_streaming", "ws", OPERATOR)
        self.assertEqual(rec["id"], "dlp-1")
        self.assertIs(rec["reference_stub"], True)
        self.assertIs(rec["streamed_here"], False)
        self.assertIs(rec["hosted_here"], False)
        self.assertIs(rec["delivered_here"], False)
        self.assertIs(rec["content_held"], False)

    def test_current_outcome_derived_from_latest(self):
        profile = self.ext.record_delivery_profile("edge_delivery", "edge", OPERATOR)
        view = self.ext.delivery_view(profile["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "unreported")
        self.ext.record_delivery_report(profile["id"], "reported_warming", OPERATOR)
        self.ext.record_delivery_report(profile["id"], "reported_live", OPERATOR)
        view = self.ext.delivery_view(profile["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "reported_live")
        self.assertEqual(view["report_count"], 2)

    def test_content_kwarg_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_delivery_profile("cdn_platform", "cdn", OPERATOR, payload=b"x")


class TestCarriedBundle(unittest.TestCase):
    """idx 168 -- carried Group 11 bundle (reference)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_extensions()

    def test_reference_record_carries_zero_claims_fact(self):
        rec = self.ext.record_carried_reference("ai_ml_models", "models", OPERATOR)
        self.assertEqual(rec["id"], "crf-1")
        self.assertIs(rec["reference_stub"], True)
        self.assertEqual(rec["claimed_by_descriptions"], 0)
        self.assertIs(rec["implemented_here"], False)

    def test_all_nine_families_accepted_and_unknown_rejected(self):
        for family in ext_mod.CARRIED_FAMILIES:
            rec = self.ext.record_carried_reference(family, family, OPERATOR)
            self.assertEqual(rec["family"], family)
        with self.assertRaises(ValidationError):
            self.ext.record_carried_reference("teleportation", "x", OPERATOR)

    def test_report_outcomes_verbatim_current_derived(self):
        ref = self.ext.record_carried_reference("email_security", "sec", OPERATOR)
        self.ext.record_carried_report(ref["id"], "reported_suspicious", OPERATOR)
        self.ext.record_carried_report(ref["id"], "reported_benign", OPERATOR)
        view = self.ext.carried_view(ref["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "reported_benign")
        self.assertIs(view["reports"][0]["performed_here"], False)

    def test_payment_records_integer_cents_totals_derived(self):
        ref = self.ext.record_carried_reference("payment_processing", "pay", OPERATOR)
        self.ext.record_carried_payment(ref["id"], 1500, "recorded_authorized", OPERATOR)
        self.ext.record_carried_payment(ref["id"], 1500, "recorded_captured", OPERATOR)
        total = self.ext.carried_payment_total(ref["id"], OPERATOR)
        self.assertEqual(total["total_cents"], 3000)
        self.assertEqual(total["payment_count"], 2)
        self.assertEqual(total["by_state"],
                         {"recorded_authorized": 1, "recorded_captured": 1})
        pay = self.ext.record_carried_payment(ref["id"], 0, "recorded_voided", OPERATOR)
        self.assertIs(pay["charged_here"], False)
        self.assertIs(pay["settled_here"], False)

    def test_payment_rejects_floats_bools_negatives_and_wrong_family(self):
        ref = self.ext.record_carried_reference("payment_processing", "pay", OPERATOR)
        other = self.ext.record_carried_reference("email_security", "sec", OPERATOR)
        for bad in (10.5, True, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_carried_payment(ref["id"], bad, "recorded_captured", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_carried_payment(ref["id"], 100, "charged", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_carried_payment(other["id"], 100, "recorded_captured", OPERATOR)
        total = self.ext.carried_payment_total(ref["id"], OPERATOR)
        self.assertEqual(total["payment_count"], 0)

    def test_report_summary_deterministic_counts_track_new_records(self):
        summary = self.ext.extension_report_summary(OPERATOR)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["extensions"]["workflow_definitions"], 0)
        self.ext.record_workflow_definition("w", ["s"], OPERATOR)
        self.store.compose_message(
            OPERATOR, subject="Hi", body="Hello",
            contact_ids=[self.contact["id"]], channel_kinds=["email"])
        summary = self.ext.extension_report_summary(OPERATOR)
        self.assertEqual(summary["extensions"]["workflow_definitions"], 1)
        self.assertEqual(summary["core"]["messages"], 1)
        self.assertEqual(summary["core"]["deliveries_by_status"], {"queued": 1})


class TestExtensionDiscipline(unittest.TestCase):
    """Cross-cutting: RBAC, High apparatus, ids, content ban."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_extensions()

    def test_viewer_write_denied_and_audited(self):
        audit = self.store.audit
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            self.ext.record_workflow_definition("w", ["s"], VIEWER)
        entries = audit.entries()
        self.assertEqual(len(entries), before + 1)
        self.assertEqual(entries[-1]["action"], "ext_message_compose:denied")
        self.assertEqual(entries[-1]["actor"], "carol")

    def test_auditor_has_no_extension_permission(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_workflow_definition("w", ["s"], AUDITOR)
        w = self.ext.record_workflow_definition("w", ["s"], OPERATOR)
        with self.assertRaises(PermissionDenied):
            self.ext.workflow_view(w["id"], AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.extension_report_summary(AUDITOR)

    def test_failed_operation_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.record_transport_profile("bogus_kind", "x", OPERATOR)
        rec = self.ext.record_transport_profile("fax_network", "f", OPERATOR)
        self.assertEqual(rec["id"], "trp-1")

    def test_mutations_audited_with_ext_prefix_and_chain_verifies(self):
        self.ext.record_workflow_definition("w", ["s"], OPERATOR)
        ok, bad = self.store.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(bad)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_workflow_definition_record", actions)

    def test_no_content_shaped_parameter_anywhere(self):
        banned = {"content", "body", "payload", "transcript", "audio",
                  "key_material", "signature_bytes", "media"}
        for name, fn in inspect.getmembers(CommExtensions, predicate=inspect.isfunction):
            if name.startswith("_"):
                continue
            params = set(inspect.signature(fn).parameters)
            self.assertEqual(params & banned, set(),
                             "%s accepts a content-shaped parameter" % name)

    def test_no_actor_is_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_workflow_definition("w", ["s"], None)


def _mutant_latest_label(records, key):
    """Mutant seam: reads the EARLIEST record instead of the latest."""
    if not records:
        return None
    return records[0][key]


class TestNegativeControlLatestLabel(unittest.TestCase):
    """Fresh negative control: the current reported label of an
    append-only stream is its LATEST record's label (the seam
    ``_latest_label`` in ``comm.extensions``)."""

    def setUp(self):
        self.ext, self.store, self.contact = fresh_extensions()
        self.w = self.ext.record_workflow_definition("w", ["s"], OPERATOR)
        self.ext.record_workflow_outcome(self.w["id"], "reported_running", OPERATOR)
        self.ext.record_workflow_outcome(self.w["id"], "reported_completed", OPERATOR)

    def test_canonical_view_uses_latest_outcome(self):
        view = self.ext.workflow_view(self.w["id"], OPERATOR)
        self.assertEqual(view["current_outcome"], "reported_completed")

    def test_mutant_earliest_outcome_differs(self):
        records = [{"outcome_label": "reported_running"},
                   {"outcome_label": "reported_completed"}]
        canonical = ext_mod._latest_label(records, "outcome_label")
        mutant = _mutant_latest_label(records, "outcome_label")
        self.assertEqual(canonical, "reported_completed")
        self.assertEqual(mutant, "reported_running")
        self.assertNotEqual(canonical, mutant)

    def test_canonical_expectation_rejects_mutant_outcome(self):
        view = self.ext.workflow_view(self.w["id"], OPERATOR)
        mutant_value = _mutant_latest_label(view["outcomes"], "outcome_label")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_outcome"], mutant_value)


if __name__ == "__main__":
    unittest.main()
