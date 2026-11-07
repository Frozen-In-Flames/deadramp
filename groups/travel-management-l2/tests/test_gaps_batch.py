"""Final GAPS batch tests — Travel Management L2 (Singleton 55).

Pins the extension surface in ``travel.extensions`` for the 8
open entries of the section: booking requests and verbatim
outcome reports, reservation-integration reference records,
disbursement requests under the disbursement cap, receipt
registrations and extraction reports, connector reference
records, delivery-attempt records, report definitions and
figure-free run records, and identity-provider reference
records — plus the cross-cutting disciplines (exact record
shapes, honesty labels, TypeError signature pins, no score key
anywhere, denied attempts audited, failed operations consuming
no ids) and the fresh mutation-verified negative control for
the disbursement cap.
"""

import unittest

from travel.errors import NotFoundError, PermissionDenied, ValidationError
from travel.extensions import TravelExtensions

from travel_helpers import (
    ADMIN,
    DECIDER,
    MEMBER,
    OUTSIDER,
    VIEWER,
    make_approved_authorization,
    make_approved_report,
    make_report_with_items,
    make_store,
    make_traveler,
)

DIGEST = "a" * 64


def _all_keys(value):
    """Every dict key in a nested structure, recursively."""
    keys = set()
    if isinstance(value, dict):
        for key, sub in value.items():
            keys.add(key)
            keys |= _all_keys(sub)
    elif isinstance(value, (list, tuple)):
        for sub in value:
            keys |= _all_keys(sub)
    return keys


class ExtensionsTestCase(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()
        self.ext = TravelExtensions(self.store)
        self.traveler = make_traveler(self.store, self.org)
        self.auth = make_approved_authorization(
            self.store, self.org, self.traveler)

    def make_notification(self):
        return self.store.create_notification(
            MEMBER, self.org["id"], "reminder", "TRV-100",
            target_kind="authorization", target_id=self.auth["id"])


class TestBookingRequests(ExtensionsTestCase):
    """Entry 531 — travel booking & reservation engine (built)."""

    def test_request_record_shape_and_labels(self):
        request = self.ext.create_booking_request(
            MEMBER, self.auth["id"], "air", "Carrier A", 220_000)
        self.assertEqual(set(request), {
            "id", "org_id", "authorization_id", "traveler_id",
            "segment_kind", "provider_label", "fare_cents",
            "booked_here", "ticketed_here", "state",
            "created_by", "created_utc",
        })
        self.assertEqual(request["id"], "bkr-1")
        self.assertEqual(request["org_id"], self.org["id"])
        self.assertEqual(request["traveler_id"], self.traveler["id"])
        self.assertIs(request["booked_here"], False)
        self.assertIs(request["ticketed_here"], False)
        self.assertEqual(request["state"], "recorded_request_only")

    def test_report_outcome_verbatim_and_current_outcome_derived(self):
        request = self.ext.create_booking_request(
            MEMBER, self.auth["id"], "lodging", "Hotel B", 90_000)
        view = self.ext.booking_view(MEMBER, request["id"])
        self.assertIsNone(view["current_outcome"])
        self.ext.record_booking_report(
            MEMBER, request["id"], "reported_waitlisted")
        report = self.ext.record_booking_report(
            MEMBER, request["id"], "reported_booked",
            reported_reference="CONF-778")
        self.assertEqual(set(report), {
            "id", "request_id", "outcome_label", "reported_reference",
            "booked_here", "ticketed_here", "created_by", "created_utc",
        })
        self.assertEqual(report["reported_reference"], "CONF-778")
        view = self.ext.booking_view(MEMBER, request["id"])
        self.assertEqual(view["current_outcome"], "reported_booked")
        # The stored request record carries no derived key.
        stored = self.ext.get_booking_request(MEMBER, request["id"])
        self.assertNotIn("current_outcome", stored)

    def test_reports_leave_core_authorization_byte_identical(self):
        before = self.store.get_authorization(
            MEMBER, self.auth["id"], as_of="2026-06-01")
        request = self.ext.create_booking_request(
            MEMBER, self.auth["id"], "air", "Carrier A", 220_000)
        self.ext.record_booking_report(
            MEMBER, request["id"], "reported_ticketed",
            reported_reference="TKT-1")
        after = self.store.get_authorization(
            MEMBER, self.auth["id"], as_of="2026-06-01")
        self.assertEqual(before, after)

    def test_validation_and_no_id_on_failure(self):
        with self.assertRaises(ValidationError):
            self.ext.create_booking_request(
                MEMBER, self.auth["id"], "air", "Carrier A", 10.5)
        with self.assertRaises(ValidationError):
            self.ext.create_booking_request(
                MEMBER, self.auth["id"], "rocket", "Carrier A", 100)
        with self.assertRaises(NotFoundError):
            self.ext.create_booking_request(
                MEMBER, "auth-999", "air", "Carrier A", 100)
        request = self.ext.create_booking_request(
            MEMBER, self.auth["id"], "air", "Carrier A", 100)
        self.assertEqual(request["id"], "bkr-1")

    def test_unknown_outcome_label_rejected(self):
        request = self.ext.create_booking_request(
            MEMBER, self.auth["id"], "air", "Carrier A", 100)
        with self.assertRaises(ValidationError):
            self.ext.record_booking_report(
                MEMBER, request["id"], "definitely_booked")


class TestReservationIntegrations(ExtensionsTestCase):
    """Entry 532 — carrier, hotel & GDS integrations (reference)."""

    def test_integration_record_shape_and_labels(self):
        integration = self.ext.record_reservation_integration(
            MEMBER, self.org["id"], "GDS-AMADEUS", "gds", "Amadeus GDS")
        self.assertEqual(set(integration), {
            "id", "org_id", "system_ref", "system_kind",
            "provider_label", "reference_stub", "reference_transport",
            "connected_here", "transmitted_here", "state",
            "created_by", "created_utc",
        })
        self.assertIs(integration["reference_stub"], True)
        self.assertIs(integration["reference_transport"], True)
        self.assertIs(integration["connected_here"], False)
        self.assertIs(integration["transmitted_here"], False)
        self.assertEqual(integration["state"], "recorded_reference_only")

    def test_receipts_and_derived_view(self):
        integration = self.ext.record_reservation_integration(
            MEMBER, self.org["id"], "CRS-1", "carrier", "Carrier CRS")
        receipt = self.ext.record_reservation_receipt(
            MEMBER, integration["id"], "reported_confirmed", 14)
        self.assertEqual(set(receipt), {
            "id", "integration_id", "outcome_label", "reported_count",
            "reference_stub", "reference_transport", "transmitted_here",
            "created_by", "created_utc",
        })
        self.ext.record_reservation_receipt(
            MEMBER, integration["id"], "reported_pending", 3)
        view = self.ext.reservation_integration_view(
            MEMBER, integration["id"])
        self.assertEqual(view["receipt_count"], 2)
        self.assertEqual(view["reported_total"], 17)

    def test_duplicate_system_ref_rejected_per_org(self):
        self.ext.record_reservation_integration(
            MEMBER, self.org["id"], "GDS-1", "gds", "GDS")
        with self.assertRaises(ValidationError):
            self.ext.record_reservation_integration(
                MEMBER, self.org["id"], "GDS-1", "gds", "GDS again")

    def test_outsider_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_reservation_integration(
                OUTSIDER, self.org["id"], "GDS-1", "gds", "GDS")
        with self.assertRaises(PermissionDenied):
            self.ext.list_reservation_integrations(
                OUTSIDER, self.org["id"])


class TestDisbursements(ExtensionsTestCase):
    """Entry 533 — payment & disbursement execution (built)."""

    def setUp(self):
        super().setUp()
        # Approved report, total 150_000 (lodging 120_000 + meals 30_000).
        self.report = make_approved_report(self.store, self.auth)

    def test_request_record_shape_and_labels(self):
        request = self.ext.request_disbursement(
            MEMBER, self.report["id"], 50_000)
        self.assertEqual(set(request), {
            "id", "org_id", "report_id", "amount_cents", "paid_here",
            "disbursed_here", "moved_here", "state", "created_by",
            "created_utc",
        })
        self.assertIs(request["paid_here"], False)
        self.assertIs(request["disbursed_here"], False)
        self.assertIs(request["moved_here"], False)
        self.assertEqual(request["state"], "recorded_request_only")

    def test_request_over_report_total_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement(
                MEMBER, self.report["id"], 150_001)

    def test_cap_allows_exact_total_then_rejects_one_cent_more(self):
        self.ext.request_disbursement(MEMBER, self.report["id"], 150_000)
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement(MEMBER, self.report["id"], 1)

    def test_failed_report_releases_commitment(self):
        first = self.ext.request_disbursement(
            MEMBER, self.report["id"], 100_000)
        self.ext.record_disbursement_report(
            MEMBER, first["id"], "reported_failed")
        second = self.ext.request_disbursement(
            MEMBER, self.report["id"], 150_000)
        summary = self.ext.report_disbursement_summary(
            MEMBER, self.report["id"])
        self.assertEqual(summary["requested_cents"], 250_000)
        self.assertEqual(summary["committed_cents"], 150_000)
        self.assertEqual(summary["request_count"], 2)
        self.assertEqual(second["amount_cents"], 150_000)

    def test_outcome_report_verbatim_and_view_derivation(self):
        request = self.ext.request_disbursement(
            MEMBER, self.report["id"], 40_000)
        report = self.ext.record_disbursement_report(
            MEMBER, request["id"], "reported_paid")
        self.assertEqual(set(report), {
            "id", "request_id", "outcome_label", "paid_here",
            "disbursed_here", "created_by", "created_utc",
        })
        view = self.ext.disbursement_view(MEMBER, request["id"])
        self.assertEqual(view["current_outcome"], "reported_paid")
        stored = self.ext.list_disbursement_requests(
            MEMBER, self.report["id"])[0]
        self.assertNotIn("current_outcome", stored)

    def test_requires_approved_report(self):
        draft = make_report_with_items(self.store, self.auth)
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement(MEMBER, draft["id"], 100)

    def test_float_amount_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement(
                MEMBER, self.report["id"], 10.0)
        request = self.ext.request_disbursement(
            MEMBER, self.report["id"], 100)
        self.assertEqual(request["id"], "dis-1")


class _NoCapExtensions(TravelExtensions):
    """Mutant: the disbursement cap seam waves everything through."""

    def _check_disbursement_cap(self, report_total_cents, committed_cents,
                                amount_cents):
        return True


class TestDisbursementCapNegativeControl(ExtensionsTestCase):
    """Fresh negative control: the disbursement cap seam is what
    keeps cumulative outstanding requests at or under the core
    expense report's derived total."""

    def setUp(self):
        super().setUp()
        self.report = make_approved_report(self.store, self.auth)

    def _over_cap(self, ext):
        ext.request_disbursement(MEMBER, self.report["id"], 100_000)
        return ext.request_disbursement(MEMBER, self.report["id"], 60_000)

    def test_canonical_store_rejects_over_cap(self):
        with self.assertRaises(ValidationError):
            self._over_cap(self.ext)
        summary = self.ext.report_disbursement_summary(
            MEMBER, self.report["id"])
        self.assertEqual(summary["committed_cents"], 100_000)

    def test_mutant_accepts_and_committed_exceeds_total(self):
        mutant = _NoCapExtensions(self.store)
        request = self._over_cap(mutant)
        self.assertEqual(request["amount_cents"], 60_000)
        summary = mutant.report_disbursement_summary(
            MEMBER, self.report["id"])
        self.assertEqual(summary["committed_cents"], 160_000)
        self.assertGreater(summary["committed_cents"],
                           summary["report_total_cents"])

    def test_mutant_as_expectation_fails(self):
        mutant = _NoCapExtensions(self.store)
        with self.assertRaises(AssertionError):
            with self.assertRaises(ValidationError):
                self._over_cap(mutant)


class TestReceipts(ExtensionsTestCase):
    """Entry 534 — receipt capture & imaging / OCR (built)."""

    def setUp(self):
        super().setUp()
        self.draft = make_report_with_items(self.store, self.auth)
        self.items = self.store.list_expense_items(
            MEMBER, self.draft["id"])

    def test_receipt_record_shape_and_labels(self):
        receipt = self.ext.register_receipt(
            MEMBER, self.draft["id"], self.items[0]["id"], "RCPT-9",
            sha256_digest=DIGEST)
        self.assertEqual(set(receipt), {
            "id", "org_id", "report_id", "item_id", "receipt_ref",
            "sha256_digest", "content_held_here", "imaged_here",
            "ocr_performed_here", "created_by", "created_utc",
        })
        self.assertIs(receipt["content_held_here"], False)
        self.assertIs(receipt["imaged_here"], False)
        self.assertIs(receipt["ocr_performed_here"], False)
        self.assertEqual(receipt["sha256_digest"], DIGEST)

    def test_bad_digest_and_unknown_item_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_receipt(
                MEMBER, self.draft["id"], self.items[0]["id"], "R-1",
                sha256_digest="not-a-digest")
        with self.assertRaises(NotFoundError):
            self.ext.register_receipt(
                MEMBER, self.draft["id"], "itm-999", "R-1")

    def test_extraction_report_verbatim_and_core_item_unchanged(self):
        item_before = dict(self.items[0])
        receipt = self.ext.register_receipt(
            MEMBER, self.draft["id"], self.items[0]["id"], "RCPT-9")
        report = self.ext.record_receipt_extraction_report(
            MEMBER, receipt["id"], "reported_extracted",
            extracted_total_cents=120_000)
        self.assertEqual(set(report), {
            "id", "receipt_id", "outcome_label",
            "extracted_total_cents", "extracted_here",
            "ocr_performed_here", "created_by", "created_utc",
        })
        self.assertEqual(report["extracted_total_cents"], 120_000)
        self.assertIs(report["extracted_here"], False)
        view = self.ext.receipt_view(MEMBER, receipt["id"])
        self.assertEqual(view["current_outcome"], "reported_extracted")
        item_after = self.store.list_expense_items(
            MEMBER, self.draft["id"])[0]
        self.assertEqual(item_before, item_after)


class TestConnectorReferences(ExtensionsTestCase):
    """Entry 535 — integration connector engines (reference)."""

    def setUp(self):
        super().setUp()
        self.integration = self.store.register_integration(
            MEMBER, self.org["id"], "GDS link", "api", "Amadeus")

    def test_connector_record_shape_and_labels(self):
        reference = self.ext.record_connector_reference(
            MEMBER, self.org["id"], self.integration["id"], "GDS engine")
        self.assertEqual(set(reference), {
            "id", "org_id", "integration_id", "engine_label",
            "reference_stub", "reference_transport", "executed_here",
            "connected_here", "state", "created_by", "created_utc",
        })
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["executed_here"], False)
        self.assertIs(reference["connected_here"], False)
        self.assertEqual(reference["state"], "recorded_reference_only")

    def test_run_report_counts_as_reported(self):
        reference = self.ext.record_connector_reference(
            MEMBER, self.org["id"], self.integration["id"], "GDS engine")
        report = self.ext.record_connector_run_report(
            MEMBER, reference["id"], "reported_synced", 42)
        self.assertEqual(set(report), {
            "id", "connector_id", "outcome_label", "reported_records",
            "reference_stub", "reference_transport", "executed_here",
            "created_by", "created_utc",
        })
        self.assertEqual(report["reported_records"], 42)

    def test_unknown_integration_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_connector_reference(
                MEMBER, self.org["id"], "int-999", "engine")


class TestDeliveryTransport(ExtensionsTestCase):
    """Entry 536 — notification delivery transport (built)."""

    def test_attempt_record_shape_and_labels(self):
        note = self.make_notification()
        attempt = self.ext.record_delivery_attempt(
            MEMBER, self.org["id"], note["id"], "email")
        self.assertEqual(set(attempt), {
            "id", "org_id", "notification_id", "channel",
            "reference_transport", "delivered_here",
            "transmitted_here", "state", "created_by", "created_utc",
        })
        self.assertIs(attempt["reference_transport"], True)
        self.assertIs(attempt["delivered_here"], False)
        self.assertIs(attempt["transmitted_here"], False)

    def test_report_and_derived_current_outcome(self):
        note = self.make_notification()
        attempt = self.ext.record_delivery_attempt(
            MEMBER, self.org["id"], note["id"], "sms")
        report = self.ext.record_delivery_report(
            MEMBER, attempt["id"], "reported_bounced")
        self.assertEqual(set(report), {
            "id", "attempt_id", "outcome_label", "reference_transport",
            "delivered_here", "created_by", "created_utc",
        })
        self.ext.record_delivery_report(
            MEMBER, attempt["id"], "reported_delivered")
        view = self.ext.delivery_view(MEMBER, attempt["id"])
        self.assertEqual(view["current_outcome"], "reported_delivered")
        # The core notification record is untouched by the transport.
        core_notes = self.store.list_notifications(MEMBER, self.org["id"])
        self.assertEqual(core_notes[0], note)

    def test_unknown_notification_and_channel_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_delivery_attempt(
                MEMBER, self.org["id"], "ntf-999", "email")
        note = self.make_notification()
        with self.assertRaises(ValidationError):
            self.ext.record_delivery_attempt(
                MEMBER, self.org["id"], note["id"], "telepathy")


class TestReportGeneration(ExtensionsTestCase):
    """Entry 537 — report generation engine & dashboards (built)."""

    def test_definition_held_as_data(self):
        definition = self.ext.register_report_definition(
            MEMBER, self.org["id"], "Monthly travel",
            "counts by status; sums by organization")
        self.assertEqual(set(definition), {
            "id", "org_id", "name", "definition_text",
            "generated_here", "rendered_here", "created_by",
            "created_utc",
        })
        self.assertEqual(definition["definition_text"],
                         "counts by status; sums by organization")
        self.assertIs(definition["generated_here"], False)
        self.assertIs(definition["rendered_here"], False)

    def test_run_record_stores_no_figures_and_view_derives(self):
        definition = self.ext.register_report_definition(
            MEMBER, self.org["id"], "Monthly travel", "summary figures")
        run = self.ext.record_report_run(
            MEMBER, definition["id"], "reported_generated")
        self.assertEqual(set(run), {
            "id", "definition_id", "outcome_label", "created_by",
            "created_utc",
        })
        view = self.ext.report_run_view(MEMBER, run["id"])
        self.assertEqual(view["figures"]["travelers"], 1)
        # Figures track registry state: a new core traveler moves them.
        self.store.create_traveler(
            MEMBER, self.org["id"], "TRV-200", "Traveler Two")
        view = self.ext.report_run_view(MEMBER, run["id"])
        self.assertEqual(view["figures"]["travelers"], 2)

    def test_dashboard_configuration_and_derived_figures(self):
        dashboard = self.ext.register_dashboard(
            MEMBER, self.org["id"], "Ops board", "summary widgets")
        self.assertEqual(set(dashboard), {
            "id", "org_id", "name", "definition_text", "rendered_here",
            "created_by", "created_utc",
        })
        self.assertIs(dashboard["rendered_here"], False)
        view = self.ext.dashboard_view(MEMBER, dashboard["id"])
        self.assertEqual(view["figures"]["org_id"], self.org["id"])


class TestIdentityReference(ExtensionsTestCase):
    """Entry 538 — identity provider / identity management (reference)."""

    def test_reference_record_shape_and_labels(self):
        reference = self.ext.record_identity_reference(
            MEMBER, self.org["id"], "IDP-ENTRA", "Agency Entra ID")
        self.assertEqual(set(reference), {
            "id", "org_id", "provider_ref", "provider_label",
            "reference_stub", "identity_provider", "state",
            "created_by", "created_utc",
        })
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["identity_provider"], False)
        self.assertEqual(reference["state"], "recorded_reference_only")

    def test_duplicate_provider_ref_rejected_per_org(self):
        self.ext.record_identity_reference(
            MEMBER, self.org["id"], "IDP-1", "Provider One")
        with self.assertRaises(ValidationError):
            self.ext.record_identity_reference(
                MEMBER, self.org["id"], "IDP-1", "Provider One again")


class TestExtensionDiscipline(ExtensionsTestCase):
    """Cross-cutting disciplines on the whole extension surface."""

    def test_no_score_shaped_key_anywhere(self):
        request = self.ext.create_booking_request(
            MEMBER, self.auth["id"], "air", "Carrier A", 100)
        self.ext.record_booking_report(
            MEMBER, request["id"], "reported_booked")
        report = make_approved_report(self.store, self.auth)
        self.ext.request_disbursement(MEMBER, report["id"], 100)
        definition = self.ext.register_report_definition(
            MEMBER, self.org["id"], "R", "figures")
        run = self.ext.record_report_run(
            MEMBER, definition["id"], "reported_generated")
        views = [
            self.ext.booking_view(MEMBER, request["id"]),
            self.ext.report_disbursement_summary(MEMBER, report["id"]),
            self.ext.report_run_view(MEMBER, run["id"]),
        ]
        for view in views:
            for key in _all_keys(view):
                lowered = key.lower()
                self.assertNotIn("score", lowered)
                self.assertNotIn("rating", lowered)
                self.assertNotIn("rank", lowered)
                self.assertNotIn("grade", lowered)

    def test_smuggled_fields_rejected_by_signature(self):
        with self.assertRaises(TypeError):
            self.ext.create_booking_request(
                MEMBER, self.auth["id"], "air", "Carrier A", 100,
                passenger_name="Real Person")
        draft = make_report_with_items(self.store, self.auth)
        item = self.store.list_expense_items(MEMBER, draft["id"])[0]
        with self.assertRaises(TypeError):
            self.ext.register_receipt(
                MEMBER, draft["id"], item["id"], "R-1",
                image_bytes=b"\x89PNG")
        with self.assertRaises(TypeError):
            self.ext.record_identity_reference(
                MEMBER, self.org["id"], "IDP-1", "Provider",
                password="secret")
        note = self.make_notification()
        with self.assertRaises(TypeError):
            self.ext.record_delivery_attempt(
                MEMBER, self.org["id"], note["id"], "email",
                message_body="hello")

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_booking_request(
                VIEWER, self.auth["id"], "air", "Carrier A", 100)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_booking_request_create:denied", actions)

    def test_successful_mutations_audited_with_ext_prefix(self):
        self.ext.create_booking_request(
            MEMBER, self.auth["id"], "air", "Carrier A", 100)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_booking_request_create", actions)

    def test_decider_is_a_member_and_can_use_surface(self):
        # DECIDER (dana, member) did not create the authorization;
        # the extension surface rides the core role matrix as-is.
        request = self.ext.create_booking_request(
            DECIDER, self.auth["id"], "rail", "Rail B", 5_000)
        self.assertEqual(request["created_by"], "dana")


if __name__ == "__main__":
    unittest.main()
