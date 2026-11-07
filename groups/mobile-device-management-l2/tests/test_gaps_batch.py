"""Final GAPS batch tests — Singleton 50, Mobile Device Management
(MDM) L2.

Pins the extension surface in ``src/mdm/extensions.py``
(``MdmExtensions``, wrapping the core ``MdmStore``): one test
class per open GAPS.md entry for this group (see ``../BATCH.md``
for the per-entry disposition), plus cross-cutting pins — the
founding privacy invariant over the WHOLE extension surface
(no identifier or location key on any stored record), the
stub/reference labels, core-unchanged pins for the reference
surfaces, RBAC denials consuming no id, and ``ext_``-prefixed
audit actions.

The batch's fresh negative control is the device-command
separation-of-duties seam
(``MdmExtensions._check_command_confirmer_not_requester``):
``TestCommandNegativeControl`` pins the canonical expectation,
and the external mutation drill is recorded in
``tests/README.md``.

Fixtures: ``make_store()`` (organization AGENCY-1 by MEMBER/bob,
STAFF/erin a member) from ``mdm_helpers``.
"""

import unittest

from mdm_helpers import (
    ADMIN, MEMBER, OUTSIDER, STAFF, VIEWER,
    make_bill, make_budget, make_contract, make_funded_budget,
    make_inventory, make_store,
)

from mdm.errors import NotFoundError, PermissionDenied, ValidationError
from mdm.extensions import FORBIDDEN_KEYS, MdmExtensions


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


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()
        self.ext = MdmExtensions(self.store)
        self.oid = self.org["id"]


class TestOptimizationRecommendations(BatchFixture):
    """Entry (idx 470): Optimization engine — built as recorded
    recommendation records (the name-only basis is stated in
    BATCH.md); no optimizer runs."""

    def test_record_shape_and_no_computation(self):
        rec = self.ext.create_optimization_recommendation(
            MEMBER, self.oid, "PLAN-VOICE-1", "consolidate",
            "Two voice plans overlap", estimated_saving_cents=12000)
        self.assertEqual(rec["id"], "opt-1")
        self.assertEqual(rec["method"], "recorded_recommendation")
        self.assertIs(rec["computed_here"], False)
        self.assertEqual(rec["estimated_saving_cents"], 12000)

    def test_float_saving_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_optimization_recommendation(
                MEMBER, self.oid, "PLAN-1", "act", "why",
                estimated_saving_cents=10.5)
        rec = self.ext.create_optimization_recommendation(
            MEMBER, self.oid, "PLAN-1", "act", "why")
        self.assertEqual(rec["id"], "opt-1")
        self.assertIsNone(rec["estimated_saving_cents"])

    def test_viewer_cannot_create_and_outsider_cannot_read(self):
        self.store.add_member(ADMIN, self.oid, VIEWER.name)
        with self.assertRaises(PermissionDenied):
            self.ext.create_optimization_recommendation(
                VIEWER, self.oid, "PLAN-1", "act", "why")
        rec = self.ext.create_optimization_recommendation(
            MEMBER, self.oid, "PLAN-1", "act", "why")
        self.assertEqual(
            self.ext.get_optimization_recommendation(VIEWER, rec["id"])["id"],
            rec["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.list_optimization_recommendations(OUTSIDER, self.oid)


class TestWorkflowExecutionReference(BatchFixture):
    """Entry (idx 471): Workflow execution / routing engine —
    reference (stub-engine): execution request records only."""

    def test_reference_record_and_core_unchanged(self):
        workflow = self.store.create_workflow(
            MEMBER, self.oid, "Order intake", ["intake", "review"])
        before = self.store.get_workflow(MEMBER, workflow["id"])
        record = self.ext.record_workflow_execution(MEMBER, workflow["id"])
        self.assertEqual(record["id"], "wex-1")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["status"], "recorded_reference_only")
        self.assertIs(record["executed"], False)
        after = self.store.get_workflow(MEMBER, workflow["id"])
        self.assertEqual(before, after)
        self.assertEqual(self.store.list_orders(MEMBER, self.oid), [])

    def test_unknown_workflow_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_workflow_execution(MEMBER, "wfl-99")


class TestCarrierIntegrationReference(BatchFixture):
    """Entry (idx 472): Carrier & network integration engines —
    reference (stub-engine): connector and event records only."""

    def test_connector_and_event_labels(self):
        connector = self.ext.create_carrier_connector(
            MEMBER, self.oid, "CARRIER-A", "bill_feed")
        self.assertEqual(connector["id"], "int-1")
        self.assertIs(connector["reference_stub"], True)
        self.assertIs(connector["connected_here"], False)
        event = self.ext.record_carrier_event(
            MEMBER, connector["id"], "bill_feed_received", "June feed")
        self.assertEqual(event["id"], "cev-1")
        self.assertIs(event["reference_stub"], True)
        self.assertIs(event["reference_transport"], True)
        self.assertIs(event["executed_here"], False)
        self.assertEqual(event["status"], "recorded_reference_only")

    def test_bad_kind_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_carrier_connector(
                MEMBER, self.oid, "CARRIER-A", "telepathy")
        connector = self.ext.create_carrier_connector(
            MEMBER, self.oid, "CARRIER-A", "order_execution")
        self.assertEqual(connector["id"], "int-1")


class TestReconciliation(BatchFixture):
    """Entry (idx 473): Bill reconciliation engine beyond registry
    validation runs — built as reconciliation case records with
    totals derived at read from the recorded lines."""

    def _case(self):
        contract = make_contract(self.store, self.org)
        bill = make_bill(self.store, self.org, contract)
        return self.ext.create_reconciliation(MEMBER, bill["id"], [
            {"label": "voice", "billed_cents": 50000,
             "expected_cents": 50000, "status": "matched"},
            {"label": "data", "billed_cents": 1200,
             "expected_cents": 1000, "status": "variance"},
        ]), bill

    def test_view_totals_derived_from_recorded_lines(self):
        case, _ = self._case()
        view = self.ext.reconciliation_view(MEMBER, case["id"])
        self.assertEqual(view["line_count"], 2)
        self.assertEqual(view["billed_cents"], 51200)
        self.assertEqual(view["expected_cents"], 51000)
        self.assertEqual(view["variance_cents"], 200)
        self.assertEqual(view["lines_by_status"],
                         {"matched": 1, "variance": 1, "unmatched": 0})
        self.assertTrue(view["derived"])
        self.assertFalse(view["stored"])

    def test_stored_case_carries_no_totals_and_bill_unchanged(self):
        case, bill = self._case()
        self.assertEqual(set(case.keys()),
                         {"id", "org_id", "bill_id", "lines",
                          "created_by", "created_utc"})
        self.assertEqual(self.store.get_bill(MEMBER, bill["id"]), bill)

    def test_bad_line_rejected_whole(self):
        contract = make_contract(self.store, self.org)
        bill = make_bill(self.store, self.org, contract)
        with self.assertRaises(ValidationError):
            self.ext.create_reconciliation(MEMBER, bill["id"], [
                {"label": "x", "billed_cents": 1.5,
                 "expected_cents": 1, "status": "matched"},
            ])
        with self.assertRaises(ValidationError):
            self.ext.create_reconciliation(MEMBER, bill["id"], [
                {"label": "x", "billed_cents": 1,
                 "expected_cents": 1, "status": "close enough"},
            ])
        self.assertEqual(self.ext.list_reconciliations(MEMBER, self.oid), [])


class TestForecasts(BatchFixture):
    """Entry (idx 474): Budget projection / forecasting engine —
    built as verbatim recorded projections; never computed."""

    def test_projection_recorded_verbatim(self):
        budget = make_funded_budget(self.store, self.org)
        forecast = self.ext.create_forecast(
            MEMBER, budget["id"], 400000, 100000, "carrier notice")
        self.assertEqual(forecast["projected_obligated_cents"], 400000)
        self.assertEqual(forecast["projected_spent_cents"], 100000)
        self.assertEqual(forecast["method"], "recorded_verbatim")
        self.assertIs(forecast["computed_here"], False)
        fetched = self.ext.get_forecast(MEMBER, forecast["id"])
        self.assertEqual(fetched["projected_obligated_cents"], 400000)

    def test_view_places_recorded_projection_beside_derived_actuals(self):
        budget = make_funded_budget(self.store, self.org)
        forecast = self.ext.create_forecast(
            MEMBER, budget["id"], 400000, 100000, "carrier notice")
        view = self.ext.forecast_view(MEMBER, forecast["id"])
        self.assertEqual(view["projection_source"], "recorded_verbatim")
        self.assertEqual(view["projected_available_cents"], 500000)
        self.assertEqual(view["obligated_cents"], 300000)
        self.assertEqual(view["spent_cents"], 200000)
        self.assertEqual(view["available_cents"], 500000)
        self.assertEqual(view["actuals_source"], "derived_from_obligations")

    def test_float_projection_rejected(self):
        budget = make_budget(self.store, self.org)
        with self.assertRaises(ValidationError):
            self.ext.create_forecast(MEMBER, budget["id"], 1.5, 0, "x")


class TestAnalytics(BatchFixture):
    """Entry (idx 475): Analytics engine beyond registry summaries
    — built as named deterministic derivations over core records."""

    def test_spending_by_period(self):
        contract = make_contract(self.store, self.org)
        make_bill(self.store, self.org, contract)
        make_bill(self.store, self.org, contract,
                  period="2026-07", stated_cents=7000)
        analytic = self.ext.create_analytic(
            MEMBER, self.oid, "Spend", "spending_by_period")
        view = self.ext.analytic_view(MEMBER, analytic["id"])
        self.assertEqual(view["rows"], [
            {"period": "2026-06", "bills": 1, "stated_cents": 50000},
            {"period": "2026-07", "bills": 1, "stated_cents": 7000},
        ])
        self.assertEqual(view["method"], "deterministic_derivation")
        self.assertFalse(view["stored"])

    def test_recurring_by_kind_excludes_disconnected(self):
        item = make_inventory(self.store, self.org)
        make_inventory(self.store, self.org, ref="SVC-200",
                       service_kind="mobility", label="Field lines",
                       plan_ref="PLAN-MOB-1", monthly_recurring_cents=9000)
        order = self.store.create_order(
            MEMBER, self.oid, "disconnect", "drop it", item["id"])
        self.store.decide_order(STAFF, order["id"], True)
        self.store.fulfill_order(MEMBER, order["id"])
        analytic = self.ext.create_analytic(
            MEMBER, self.oid, "Recurring", "recurring_by_kind")
        view = self.ext.analytic_view(MEMBER, analytic["id"])
        self.assertEqual(view["rows"], [
            {"service_kind": "mobility", "items": 1,
             "monthly_recurring_cents": 9000},
        ])

    def test_open_dispute_exposure(self):
        contract = make_contract(self.store, self.org)
        bill = make_bill(self.store, self.org, contract)
        self.store.create_dispute(MEMBER, bill["id"], 4000, "overcharge")
        analytic = self.ext.create_analytic(
            MEMBER, self.oid, "Exposure", "open_dispute_exposure")
        view = self.ext.analytic_view(MEMBER, analytic["id"])
        self.assertEqual(view["rows"], [
            {"disputes_by_status": {"open": 1}, "open_disputed_cents": 4000},
        ])


class TestReportGeneration(BatchFixture):
    """Entry (idx 476): Report generation engine — built as report
    definitions plus run records holding figures derived at
    generation time (the core validation-run shape)."""

    def test_definition_and_run(self):
        make_inventory(self.store, self.org)
        make_funded_budget(self.store, self.org)
        definition = self.ext.create_report_definition(
            MEMBER, self.oid, "Monthly", ["inventory", "budgets"])
        run = self.ext.generate_report(MEMBER, definition["id"])
        self.assertEqual(run["id"], "rpr-1")
        self.assertEqual(run["figures"]["inventory"]["by_kind"],
                         {"wireline": 1, "mobility": 0, "other": 0})
        self.assertEqual(run["figures"]["budgets"],
                         {"count": 1, "available_cents": 500000})

    def test_run_is_a_snapshot(self):
        make_inventory(self.store, self.org)
        definition = self.ext.create_report_definition(
            MEMBER, self.oid, "Monthly", ["inventory"])
        run = self.ext.generate_report(MEMBER, definition["id"])
        make_inventory(self.store, self.org, ref="SVC-200")
        stored = self.ext.get_report_run(MEMBER, run["id"])
        self.assertEqual(stored["figures"]["inventory"]["by_kind"],
                         {"wireline": 1, "mobility": 0, "other": 0})

    def test_bad_section_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_report_definition(
                MEMBER, self.oid, "Bad", ["secrets"])


class TestAlertDeliveryReference(BatchFixture):
    """Entry (idx 477): Alert delivery transport — reference
    (stub-engine): delivery receipts only; alerts are records."""

    def test_receipt_labels_and_core_alert_unchanged(self):
        alert = self.store.create_alert(
            MEMBER, self.oid, "general", "Budget watch")
        before = dict(alert)
        receipt = self.ext.record_alert_delivery(MEMBER, alert["id"], "email")
        self.assertIs(receipt["reference_stub"], True)
        self.assertIs(receipt["reference_transport"], True)
        self.assertIs(receipt["delivered"], False)
        self.assertEqual(receipt["status"], "recorded_reference_only")
        after = self.store.list_alerts(MEMBER, self.oid)[0]
        self.assertEqual(before, after)

    def test_bad_channel_and_unknown_alert(self):
        alert = self.store.create_alert(MEMBER, self.oid, "general", "Hi")
        with self.assertRaises(ValidationError):
            self.ext.record_alert_delivery(MEMBER, alert["id"], "fax")
        with self.assertRaises(NotFoundError):
            self.ext.record_alert_delivery(MEMBER, "alr-99", "email")


class TestPortalConfiguration(BatchFixture):
    """Entry (idx 478): Web portal / single-pane web application —
    built as page configuration records; nothing rendered/served."""

    def test_page_record_and_duplicate_ref(self):
        page = self.ext.create_portal_page(
            MEMBER, self.oid, "home", "Home", ["inventory", "budgets"])
        self.assertEqual(page["id"], "por-1")
        self.assertIs(page["rendered_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.create_portal_page(
                MEMBER, self.oid, "home", "Again", ["orders"])
        page2 = self.ext.create_portal_page(
            MEMBER, self.oid, "billing", "Billing", ["bills"])
        self.assertEqual(page2["id"], "por-2")

    def test_portal_view_is_configuration_not_a_page(self):
        self.ext.create_portal_page(
            MEMBER, self.oid, "home", "Home", ["inventory"])
        view = self.ext.portal_view(MEMBER, self.oid)
        self.assertIs(view["served_here"], False)
        self.assertEqual(len(view["pages"]), 1)
        self.assertEqual(view["summary"]["inventory_by_state"],
                         {"active": 0, "suspended": 0, "disconnected": 0})


class TestServiceOperations(BatchFixture):
    """Entry (idx 479): Managed Mobility services operations —
    built as operation work records with a recorded lifecycle."""

    def test_lifecycle_and_invalid_jump(self):
        op = self.ext.create_service_operation(
            MEMBER, self.oid, "line_audit", "SVC-100", "Quarterly audit")
        self.assertEqual(op["status"], "open")
        with self.assertRaises(ValidationError):
            self.ext.set_service_operation_status(
                MEMBER, op["id"], "completed")
        op = self.ext.set_service_operation_status(
            MEMBER, op["id"], "in_progress")
        op = self.ext.set_service_operation_status(
            MEMBER, op["id"], "completed")
        self.assertEqual(op["status"], "completed")
        self.assertIsNotNone(op["closed_utc"])

    def test_summary_counts_derived(self):
        self.ext.create_service_operation(
            MEMBER, self.oid, "line_audit", "SVC-100", "a")
        self.ext.create_service_operation(
            MEMBER, self.oid, "rate_review", "SVC-100", "b")
        summary = self.ext.operations_summary(MEMBER, self.oid)
        self.assertEqual(summary["operations_by_kind"]["line_audit"], 1)
        self.assertEqual(summary["operations_by_status"]["open"], 2)
        self.assertFalse(summary["stored"])


class TestEnrollmentReference(BatchFixture):
    """Entry (idx 480): Mobile device enrollment & provisioning
    plane — reference (stub-engine): enrollment records over
    opaque device references only."""

    def test_record_shape_exact_and_labels(self):
        record = self.ext.record_enrollment(
            MEMBER, self.oid, "DEVICE-REF-1", "GSE program")
        self.assertEqual(
            set(record.keys()),
            {"id", "org_id", "device_ref", "program_label",
             "reference_stub", "status", "provisioned_here",
             "created_by", "created_utc"})
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["provisioned_here"], False)
        self.assertEqual(record["status"], "recorded_reference_only")

    def test_enrollment_changes_no_core_record(self):
        summary_before = self.store.organization_summary(MEMBER, self.oid)
        self.ext.record_enrollment(MEMBER, self.oid, "DEVICE-REF-1", "GSE")
        summary_after = self.store.organization_summary(MEMBER, self.oid)
        self.assertEqual(summary_before, summary_after)
        self.assertEqual(self.store.list_inventory(MEMBER, self.oid), [])


class TestDeviceCommands(BatchFixture):
    """Entry (idx 481): Remote wipe / lock / device command plane
    — built in records form: request, separation-of-duties
    confirmation, reported outcome. Nothing is issued to any
    device; ``executed_here`` is False throughout."""

    def test_request_record_shape(self):
        command = self.ext.request_device_command(
            MEMBER, self.oid, "DEVICE-REF-1", "lock", "Lost handset")
        self.assertEqual(
            set(command.keys()),
            {"id", "org_id", "device_ref", "command_kind", "reason",
             "status", "requested_by", "confirmed_by",
             "reported_outcome", "executed_here", "created_by",
             "created_utc"})
        self.assertEqual(command["status"], "requested")
        self.assertIs(command["executed_here"], False)

    def test_full_record_lifecycle(self):
        command = self.ext.request_device_command(
            MEMBER, self.oid, "DEVICE-REF-1", "wipe", "Separated employee")
        with self.assertRaises(ValidationError):
            self.ext.record_command_outcome(
                MEMBER, command["id"], "reported_completed")
        command = self.ext.confirm_device_command(STAFF, command["id"])
        self.assertEqual(command["status"], "confirmed")
        self.assertEqual(command["confirmed_by"], "erin")
        command = self.ext.record_command_outcome(
            MEMBER, command["id"], "reported_completed")
        self.assertEqual(command["status"], "reported_closed")
        self.assertEqual(command["reported_outcome"], "reported_completed")
        self.assertIs(command["executed_here"], False)

    def test_requester_cannot_confirm_own_command(self):
        command = self.ext.request_device_command(
            MEMBER, self.oid, "DEVICE-REF-1", "lock", "Lost handset")
        with self.assertRaises(PermissionDenied):
            self.ext.confirm_device_command(MEMBER, command["id"])
        stored = self.ext.get_device_command(ADMIN, command["id"])
        self.assertEqual(stored["status"], "requested")
        self.assertIsNone(stored["confirmed_by"])

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.request_device_command(
                MEMBER, self.oid, "DEVICE-REF-1", "brick", "no")


class TestCommandNegativeControl(BatchFixture):
    """Fresh negative control for the batch: the command
    separation-of-duties seam is load-bearing.

    Canonical expectation: a command requested by bob can never
    be confirmed by bob. The mutant is an ``MdmExtensions``
    subclass whose ``_check_command_confirmer_not_requester``
    never raises — under it, the same confirmation succeeds, so
    the mutant's outcome must NOT equal the canonical one.
    """

    def test_canonical_expectation(self):
        command = self.ext.request_device_command(
            MEMBER, self.oid, "DEVICE-REF-1", "wipe", "Separated employee")
        with self.assertRaises(PermissionDenied):
            self.ext.confirm_device_command(MEMBER, command["id"])

    def test_mutant_outcome_differs(self):
        class MutantExtensions(MdmExtensions):
            def _check_command_confirmer_not_requester(self, command, actor):
                return None

        mutant = MutantExtensions(self.store)
        command = mutant.request_device_command(
            MEMBER, self.oid, "DEVICE-REF-1", "wipe", "Separated employee")
        confirmed = mutant.confirm_device_command(MEMBER, command["id"])
        self.assertEqual(confirmed["status"], "confirmed")
        with self.assertRaises(AssertionError):
            self.assertEqual(confirmed["status"], "requested")


class TestDevicePolicyCompliance(BatchFixture):
    """Entry (idx 482): Device policy management & compliance
    enforcement — built as policy records and reported check
    results, with compliance state derived at read. Nothing is
    enforced on any device."""

    def _policy(self):
        return self.ext.create_device_policy(
            MEMBER, self.oid, "POL-1", "Baseline",
            ["encryption_required", "os_current"])

    def test_policy_record_and_duplicate_ref(self):
        policy = self._policy()
        self.assertIs(policy["enforced_here"], False)
        with self.assertRaises(ValidationError):
            self._policy()

    def test_compliance_state_derived_from_latest_check(self):
        policy = self._policy()
        view = self.ext.compliance_view(MEMBER, policy["id"], "DEVICE-REF-1")
        self.assertEqual(view["state"], "unknown")
        self.ext.record_compliance_check(
            MEMBER, policy["id"], "DEVICE-REF-1",
            {"encryption_required": "pass", "os_current": "pass"})
        view = self.ext.compliance_view(MEMBER, policy["id"], "DEVICE-REF-1")
        self.assertEqual(view["state"], "compliant")
        self.assertEqual(view["checks"], 1)
        self.ext.record_compliance_check(
            MEMBER, policy["id"], "DEVICE-REF-1",
            {"encryption_required": "pass", "os_current": "fail"})
        view = self.ext.compliance_view(MEMBER, policy["id"], "DEVICE-REF-1")
        self.assertEqual(view["state"], "non_compliant")
        self.assertEqual(view["checks"], 2)
        self.assertIs(view["enforced_here"], False)
        self.assertFalse(view["stored"])

    def test_unknown_requirement_label_rejected(self):
        policy = self._policy()
        with self.assertRaises(ValidationError):
            self.ext.record_compliance_check(
                MEMBER, policy["id"], "DEVICE-REF-1",
                {"jailbreak_free": "pass"})


class TestAppManagement(BatchFixture):
    """Entry (idx 483): Mobile application management — built as
    catalog and distribution records; nothing is delivered."""

    def test_catalog_distribution_and_summary(self):
        app = self.ext.create_app_record(
            MEMBER, self.oid, "APP-MAIL", "Mail client", "4.2")
        self.assertEqual(app["id"], "app-1")
        with self.assertRaises(ValidationError):
            self.ext.create_app_record(
                MEMBER, self.oid, "APP-MAIL", "Again", "4.3")
        dist = self.ext.record_app_distribution(
            MEMBER, app["id"], "DEVICE-REF-1", "managed_catalog")
        self.assertIs(dist["delivered_here"], False)
        self.assertEqual(dist["status"], "recorded")
        self.ext.record_app_distribution(
            MEMBER, app["id"], "DEVICE-REF-2", "managed_catalog")
        summary = self.ext.app_summary(MEMBER, self.oid)
        self.assertEqual(summary["apps"], 1)
        self.assertEqual(summary["distributions"], 2)
        self.assertEqual(summary["devices_with_distributions"], 2)


class TestTrackingRecords(BatchFixture):
    """Entry (idx 484): Device location & tracking services —
    built as tracking-service configuration/status records
    ONLY. No location data exists in this build: the record
    shapes are pinned and hold service-state labels, never a
    place."""

    def test_record_shape_exact_no_location(self):
        record = self.ext.create_tracking_record(
            MEMBER, self.oid, "DEVICE-REF-1", "Fleet tracking service")
        self.assertEqual(
            set(record.keys()),
            {"id", "org_id", "device_ref", "service_label",
             "location_data_held", "created_by", "created_utc"})
        self.assertIs(record["location_data_held"], False)

    def test_current_state_derived_from_reports(self):
        record = self.ext.create_tracking_record(
            MEMBER, self.oid, "DEVICE-REF-1", "Fleet tracking service")
        view = self.ext.tracking_view(MEMBER, record["id"])
        self.assertEqual(view["current_state"], "unreported")
        self.ext.record_tracking_status(MEMBER, record["id"], "active")
        view = self.ext.tracking_view(MEMBER, record["id"])
        self.assertEqual(view["current_state"], "active")
        self.assertEqual(view["reports"], 1)
        self.ext.record_tracking_status(MEMBER, record["id"], "suspended")
        view = self.ext.tracking_view(MEMBER, record["id"])
        self.assertEqual(view["current_state"], "suspended")
        self.assertIs(view["location_data_held"], False)
        # The stored record itself carries no state key: the
        # current state is derived, never stored.
        stored = self.ext.get_tracking_record(MEMBER, record["id"])
        self.assertNotIn("current_state", stored)
        self.assertNotIn("reported_state", stored)

    def test_duplicate_device_and_bad_state_rejected(self):
        self.ext.create_tracking_record(
            MEMBER, self.oid, "DEVICE-REF-1", "Fleet tracking service")
        with self.assertRaises(ValidationError):
            self.ext.create_tracking_record(
                MEMBER, self.oid, "DEVICE-REF-1", "Duplicate")
        record = self.ext.list_tracking_records(MEMBER, self.oid)[0]
        with self.assertRaises(ValidationError):
            self.ext.record_tracking_status(MEMBER, record["id"], "at_home")


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins over the whole extension surface."""

    def _one_of_each(self):
        ext = self.ext
        ext.create_optimization_recommendation(
            MEMBER, self.oid, "PLAN-1", "act", "why")
        workflow = self.store.create_workflow(
            MEMBER, self.oid, "W", ["step"])
        ext.record_workflow_execution(MEMBER, workflow["id"])
        connector = ext.create_carrier_connector(
            MEMBER, self.oid, "CARRIER-A", "bill_feed")
        ext.record_carrier_event(
            MEMBER, connector["id"], "bill_feed_received", "feed")
        contract = make_contract(self.store, self.org)
        bill = make_bill(self.store, self.org, contract)
        ext.create_reconciliation(MEMBER, bill["id"], [
            {"label": "l", "billed_cents": 1, "expected_cents": 1,
             "status": "matched"}])
        budget = make_budget(self.store, self.org)
        ext.create_forecast(MEMBER, budget["id"], 1, 1, "basis")
        ext.create_analytic(MEMBER, self.oid, "A", "spending_by_period")
        definition = ext.create_report_definition(
            MEMBER, self.oid, "R", ["bills"])
        ext.generate_report(MEMBER, definition["id"])
        alert = self.store.create_alert(MEMBER, self.oid, "general", "m")
        ext.record_alert_delivery(MEMBER, alert["id"], "email")
        ext.create_portal_page(MEMBER, self.oid, "home", "Home", ["bills"])
        ext.create_service_operation(MEMBER, self.oid, "other", "S", "d")
        ext.record_enrollment(MEMBER, self.oid, "DEVICE-REF-1", "GSE")
        ext.request_device_command(MEMBER, self.oid, "DEVICE-REF-1",
                                   "lock", "lost")
        policy = ext.create_device_policy(
            MEMBER, self.oid, "POL-1", "P", ["encryption_required"])
        ext.record_compliance_check(MEMBER, policy["id"], "DEVICE-REF-1",
                                    {"encryption_required": "pass"})
        app = ext.create_app_record(MEMBER, self.oid, "APP-1", "App", "1.0")
        ext.record_app_distribution(MEMBER, app["id"], "DEVICE-REF-1", "cat")
        tracking = ext.create_tracking_record(
            MEMBER, self.oid, "DEVICE-REF-1", "svc")
        ext.record_tracking_status(MEMBER, tracking["id"], "active")

    def test_no_identifier_or_location_key_anywhere(self):
        self._one_of_each()
        containers = [value for value in vars(self.ext).values()
                      if isinstance(value, dict)
                      and all(isinstance(v, dict) for v in value.values())]
        self.assertTrue(containers)
        for container in containers:
            for record in container.values():
                bad = _all_keys(record) & FORBIDDEN_KEYS
                self.assertEqual(bad, set(),
                                 "forbidden keys on %r" % (record.get("id"),))

    def test_extension_mutations_audit_with_ext_prefix(self):
        self.ext.create_optimization_recommendation(
            MEMBER, self.oid, "PLAN-1", "act", "why")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_optimization_recommendation_create", actions)

    def test_denied_operation_consumes_no_id(self):
        self.store.add_member(ADMIN, self.oid, VIEWER.name)
        with self.assertRaises(PermissionDenied):
            self.ext.request_device_command(
                VIEWER, self.oid, "DEVICE-REF-1", "lock", "lost")
        command = self.ext.request_device_command(
            MEMBER, self.oid, "DEVICE-REF-1", "lock", "lost")
        self.assertEqual(command["id"], "cmd-1")
