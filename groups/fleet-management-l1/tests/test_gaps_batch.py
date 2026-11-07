"""Final GAPS batch tests — Fleet Management L1 (Group 32).

Pins the extension surface in ``fleet.extensions`` per GAPS.md
entry (see ``BATCH.md`` in the group directory):

- Live telematics & GPS streaming (reference): stream records +
  caller-reported position/status records, exact key sets,
  ``tracked_here`` / ``sensed_here`` False, no track structure.
- Dispatch routing & optimization (built, records form):
  route plans as data (``optimized_here`` False), dispatch
  assignments over core reservations (``dispatched_here`` /
  ``controlled_here`` False), reported outcomes verbatim.
- ELD / hours-of-service integrations (reference): device
  bindings + reported HOS figures/labels, ``evaluated_here``
  False.
- Demand & capacity forecasting engine (built): reported
  inputs verbatim; demand/capacity totals and ratio derived at
  read, exact, never projected — plus the batch's fresh
  mutation-verified negative control on the derivation seam
  ``_recorded_demand_totals``.
- EV charging station communication & session control
  (reference components over core sessions): control requests
  labeled ``reference_stub`` with ``communicated_here`` /
  ``controlled_here`` False, pinned to leave the core session
  record untouched.
- Payment processing (built): integer-cent payment records
  bound to core sessions, opaque payment refs, exact key set,
  totals derived at read.
- Analytics & utilization-optimization engines (built):
  report-run records pinned to exactly four keys (no figures
  stored); views derive counts/sums/shares at read, tracking
  registry state; a recursive scan pins that no score-shaped
  key exists anywhere on the extension surface.
- Hosted platform operations (reference): reported status
  records, ``operated_here`` / ``hosted_here`` False, counts
  derived at read.

Cross-cutting: unexpected keyword arguments raise
``TypeError`` (no field can be smuggled into a record), viewer
writes are denied and audited, and float/bool figures are
rejected at the boundary.
"""

import unittest

from fleet_helpers import ADMIN, MANAGER, VIEWER, make_store

from fleet.errors import NotFoundError, PermissionDenied, ValidationError
from fleet.extensions import FleetExtensions, _recorded_demand_totals

FORBIDDEN_KEY_PARTS = (
    "score", "rating", "rank", "grade", "index",
    "latitude", "longitude", "coordinate",
)


def _scan_no_forbidden(value, path="root"):
    """Recursively assert no score/rank/coordinate-shaped key."""
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                # "index" is allowed only as part of no key at all;
                # plain substring pinning is deliberate here.
                assert part not in lowered, (path, key)
            _scan_no_forbidden(item, "%s.%s" % (path, key))
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _scan_no_forbidden(item, "%s[%d]" % (path, i))


class BatchCase(unittest.TestCase):
    def setUp(self):
        self.store, self.vehicle, self.operator = make_store()
        self.ext = FleetExtensions(self.store)

    def make_reservation(self):
        return self.store.create_reservation(
            self.vehicle["id"], "OP-REF-001", "2026-11-01",
            "2026-11-03", MANAGER)

    def make_session(self):
        return self.store.create_charging_session(
            "STN-REF-1", "OP-REF-001", MANAGER, watt_hours=500)

    def record(self, kind, units, subject="Depot A", period="2026-W45"):
        return self.ext.record_forecast_input(
            MANAGER, subject, kind, period, units)


class TestTelematicsReference(BatchCase):
    def test_stream_record_exact_keys_and_labels(self):
        stream = self.ext.create_telematics_stream(
            MANAGER, self.vehicle["id"], "gps_stream", "STREAM-REF-1")
        self.assertEqual(stream["id"], "tlm-1")
        self.assertEqual(set(stream), {
            "id", "vehicle_id", "kind", "source_ref",
            "reference_stub", "state", "streamed_here",
            "created_by", "created_utc",
        })
        self.assertIs(stream["reference_stub"], True)
        self.assertEqual(stream["state"], "recorded_reference_only")
        self.assertIs(stream["streamed_here"], False)

    def test_report_holds_labels_verbatim_not_tracked(self):
        stream = self.ext.create_telematics_stream(
            MANAGER, self.vehicle["id"], "telematics_feed", "FEED-1")
        report = self.ext.record_telematics_report(
            MANAGER, stream["id"], "position_report", "Depot North",
            status_label="en route")
        self.assertEqual(report["position_label"], "Depot North")
        self.assertEqual(report["status_label"], "en route")
        self.assertIs(report["tracked_here"], False)
        self.assertIs(report["sensed_here"], False)
        # No track/trail/history structure exists on the record.
        self.assertEqual(set(report), {
            "id", "stream_id", "kind", "position_label",
            "status_label", "tracked_here", "sensed_here",
            "reference_stub", "state", "created_by", "created_utc",
        })

    def test_view_derives_report_count(self):
        stream = self.ext.create_telematics_stream(
            MANAGER, self.vehicle["id"], "status_feed", "FEED-2")
        self.assertEqual(
            self.ext.telematics_stream_view(MANAGER, stream["id"])
            ["report_count"], 0)
        self.ext.record_telematics_report(
            MANAGER, stream["id"], "status_report", "Yard")
        self.ext.record_telematics_report(
            MANAGER, stream["id"], "status_report", "Gate")
        view = self.ext.telematics_stream_view(MANAGER, stream["id"])
        self.assertEqual(view["report_count"], 2)
        self.assertNotIn("report_count", stream)

    def test_unknown_vehicle_and_bad_kind_rejected_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_telematics_stream(
                MANAGER, "veh-99", "gps_stream", "S-1")
        with self.assertRaises(ValidationError):
            self.ext.create_telematics_stream(
                MANAGER, self.vehicle["id"], "lidar", "S-1")
        stream = self.ext.create_telematics_stream(
            MANAGER, self.vehicle["id"], "gps_stream", "S-1")
        self.assertEqual(stream["id"], "tlm-1")

    def test_coordinate_kwarg_smuggling_rejected(self):
        stream = self.ext.create_telematics_stream(
            MANAGER, self.vehicle["id"], "gps_stream", "S-1")
        with self.assertRaises(TypeError):
            self.ext.record_telematics_report(
                MANAGER, stream["id"], "position_report", "Yard",
                latitude=32.9)


class TestDispatchRecords(BatchCase):
    def test_route_plan_holds_steps_verbatim_not_optimized(self):
        plan = self.ext.create_route_plan(
            MANAGER, "Morning loop", "planned_route",
            step_labels=("Depot", "Site A", "Depot"))
        self.assertEqual(plan["step_labels"], ["Depot", "Site A", "Depot"])
        self.assertIs(plan["optimized_here"], False)
        self.assertEqual(set(plan), {
            "id", "label", "kind", "step_labels", "optimized_here",
            "created_by", "created_utc",
        })

    def test_assignment_records_decision_controls_nothing(self):
        reservation = self.make_reservation()
        plan = self.ext.create_route_plan(
            MANAGER, "Loop", "reported_route", step_labels=("A",))
        assignment = self.ext.create_dispatch_assignment(
            MANAGER, reservation["id"], "OP-REF-001",
            route_plan_id=plan["id"])
        self.assertIs(assignment["dispatched_here"], False)
        self.assertIs(assignment["controlled_here"], False)
        # The core reservation is untouched by the assignment.
        self.assertEqual(
            self.store.get_reservation(reservation["id"])["status"],
            "reserved")
        view = self.ext.route_plan_view(MANAGER, plan["id"])
        self.assertEqual(view["assignment_count"], 1)

    def test_outcome_label_verbatim_and_validated(self):
        reservation = self.make_reservation()
        assignment = self.ext.create_dispatch_assignment(
            MANAGER, reservation["id"], "OP-REF-001")
        outcome = self.ext.record_dispatch_outcome(
            MANAGER, assignment["id"], "reported_completed")
        self.assertEqual(outcome["outcome_label"], "reported_completed")
        with self.assertRaises(ValidationError):
            self.ext.record_dispatch_outcome(
                MANAGER, assignment["id"], "completed")

    def test_unknown_reservation_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_dispatch_assignment(
                MANAGER, "res-99", "OP-REF-001")


class TestEldReference(BatchCase):
    def test_binding_and_hos_records(self):
        binding = self.ext.create_eld_binding(
            MANAGER, self.operator["id"], "eld", "DEV-REF-1")
        self.assertIs(binding["reference_stub"], True)
        self.assertIs(binding["connected_here"], False)
        hos = self.ext.record_hours_of_service(
            MANAGER, binding["id"], 420, 600, "reported_compliant")
        self.assertEqual(hos["reported_driving_minutes"], 420)
        self.assertEqual(hos["compliance_label"], "reported_compliant")
        self.assertIs(hos["evaluated_here"], False)

    def test_hos_label_is_verbatim_never_evaluated(self):
        binding = self.ext.create_eld_binding(
            MANAGER, self.operator["id"], "eld", "DEV-REF-2")
        # Figures that would breach any real limit still record the
        # REPORTED label only; nothing here evaluates them.
        hos = self.ext.record_hours_of_service(
            MANAGER, binding["id"], 5000, 6000, "reported_compliant")
        self.assertEqual(hos["compliance_label"], "reported_compliant")
        with self.assertRaises(ValidationError):
            self.ext.record_hours_of_service(
                MANAGER, binding["id"], -1, 0, "reported_compliant")
        with self.assertRaises(ValidationError):
            self.ext.record_hours_of_service(
                MANAGER, binding["id"], 1.5, 0, "reported_compliant")


class TestForecastDerivation(BatchCase):
    def test_inputs_stored_verbatim(self):
        record = self.record("demand", 7)
        self.assertEqual(set(record), {
            "id", "subject_label", "kind", "period_label",
            "reported_units", "created_by", "created_utc",
        })
        self.assertEqual(record["reported_units"], 7)

    def test_view_derives_recorded_totals_exactly(self):
        self.record("demand", 10)
        self.record("demand", 5, period="2026-W46")
        self.record("capacity", 12)
        self.record("capacity", 8, period="2026-W46")
        self.record("demand", 99, subject="Other Depot")
        view = self.ext.forecast_view(MANAGER, "Depot A")
        self.assertEqual(view["recorded_demand"], 15)
        self.assertEqual(view["recorded_capacity"], 20)
        self.assertEqual(view["recorded_balance"], -5)
        self.assertEqual(view["demand_to_capacity"], "3/4")
        self.assertEqual(view["input_count"], 4)
        self.assertIs(view["projected_here"], False)
        self.assertIs(view["modeled_here"], False)

    def test_ratio_whole_renders_int_and_empty_capacity_none(self):
        self.record("demand", 20, subject="Whole")
        self.record("capacity", 10, subject="Whole")
        self.assertEqual(
            self.ext.forecast_view(MANAGER, "Whole")
            ["demand_to_capacity"], 2)
        self.record("demand", 3, subject="NoCap")
        view = self.ext.forecast_view(MANAGER, "NoCap")
        self.assertIsNone(view["demand_to_capacity"])
        self.assertEqual(view["recorded_capacity"], 0)

    def test_float_and_bool_units_rejected(self):
        with self.assertRaises(ValidationError):
            self.record("demand", 2.5)
        with self.assertRaises(ValidationError):
            self.record("demand", True)


class TestDemandTotalsNegativeControl(BatchCase):
    """The batch's fresh negative control: the derivation seam
    ``_recorded_demand_totals``.

    Canonical expectation: demand inputs total into the demand
    total and capacity inputs into the capacity total. A mutant
    that swaps the two kinds must NOT produce the canonical
    totals, and treating the mutant's output as the expectation
    must fail.
    """

    INPUTS = [
        {"kind": "demand", "reported_units": 10},
        {"kind": "demand", "reported_units": 5},
        {"kind": "capacity", "reported_units": 20},
    ]

    @staticmethod
    def _mutant_totals(inputs):
        total_demand = sum(r["reported_units"] for r in inputs
                           if r["kind"] == "capacity")
        total_capacity = sum(r["reported_units"] for r in inputs
                             if r["kind"] == "demand")
        return total_demand, total_capacity

    def test_canonical_but_mutant_swaps(self):
        canonical = _recorded_demand_totals(self.INPUTS)
        self.assertEqual(canonical, (15, 20))
        mutant = self._mutant_totals(self.INPUTS)
        self.assertEqual(mutant, (20, 15))
        self.assertNotEqual(mutant, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, (15, 20))

    def test_view_uses_the_seam(self):
        self.record("demand", 10)
        self.record("capacity", 20)
        view = self.ext.forecast_view(MANAGER, "Depot A")
        self.assertEqual(
            (view["recorded_demand"], view["recorded_capacity"]),
            _recorded_demand_totals(
                [r for r in self.ext._forecast_inputs.values()]))


class TestSessionControlReference(BatchCase):
    def test_control_request_labeled_and_core_untouched(self):
        session = self.make_session()
        before = self.store.get_charging_session(session["id"])
        control = self.ext.record_session_control(
            MANAGER, session["id"], "set_limit",
            requested_limit_watt_hours=1000)
        self.assertIs(control["reference_stub"], True)
        self.assertEqual(control["state"], "recorded_reference_only")
        self.assertIs(control["communicated_here"], False)
        self.assertIs(control["controlled_here"], False)
        after = self.store.get_charging_session(session["id"])
        self.assertEqual(before, after)

    def test_outcome_recorded_verbatim_and_counted(self):
        session = self.make_session()
        control = self.ext.record_session_control(
            MANAGER, session["id"], "start_session")
        outcome = self.ext.record_session_control_outcome(
            MANAGER, control["id"], "reported_accepted")
        self.assertEqual(outcome["outcome_label"], "reported_accepted")
        view = self.ext.session_control_view(MANAGER, control["id"])
        self.assertEqual(view["outcome_count"], 1)
        with self.assertRaises(ValidationError):
            self.ext.record_session_control_outcome(
                MANAGER, control["id"], "accepted")


class TestPayments(BatchCase):
    def test_payment_record_exact_keys_integer_cents(self):
        session = self.make_session()
        payment = self.ext.record_payment(
            MANAGER, session["id"], "capture", 1250, "PAY-REF-1",
            "reported_captured")
        self.assertEqual(set(payment), {
            "id", "session_id", "kind", "amount_cents",
            "payment_ref", "outcome_label", "moved_here",
            "settled_here", "created_by", "created_utc",
        })
        self.assertIs(payment["moved_here"], False)
        self.assertIs(payment["settled_here"], False)

    def test_float_amount_and_card_kwarg_rejected(self):
        session = self.make_session()
        with self.assertRaises(ValidationError):
            self.ext.record_payment(
                MANAGER, session["id"], "capture", 12.5, "PAY-REF-1",
                "reported_captured")
        with self.assertRaises(TypeError):
            self.ext.record_payment(
                MANAGER, session["id"], "capture", 100, "PAY-REF-1",
                "reported_captured", card_number="4111111111111111")

    def test_totals_derived_at_read_by_outcome(self):
        session = self.make_session()
        view = self.ext.session_payments_view(MANAGER, session["id"])
        self.assertEqual(view["total_cents"], 0)
        self.ext.record_payment(
            MANAGER, session["id"], "capture", 1000, "P-1",
            "reported_captured")
        self.ext.record_payment(
            MANAGER, session["id"], "refund", 250, "P-2",
            "reported_refunded")
        view = self.ext.session_payments_view(MANAGER, session["id"])
        self.assertEqual(view["payment_count"], 2)
        self.assertEqual(view["total_cents"], 1250)
        self.assertEqual(view["cents_by_outcome"],
                         {"reported_captured": 1000,
                          "reported_refunded": 250})


class TestAnalytics(BatchCase):
    def test_run_record_stores_no_figures(self):
        run = self.ext.record_report_run(MANAGER, "Weekly utilization")
        self.assertEqual(set(run),
                         {"id", "label", "created_by", "created_utc"})

    def test_view_derives_from_registry_and_tracks_state(self):
        run = self.ext.record_report_run(MANAGER, "Weekly utilization")
        view = self.ext.analytics_view(MANAGER, run["id"])
        self.assertEqual(view["counts"]["vehicles"], 1)
        self.assertIsNone(view["latest_odometer"])
        self.assertIsNone(view["maintenance_completed_share"])
        self.store.record_usage(self.vehicle["id"], 12000, MANAGER)
        maintenance = self.store.create_maintenance(
            self.vehicle["id"], "inspection", "2026-11-05", MANAGER)
        self.store.complete_maintenance(
            maintenance["id"], MANAGER, completed_date="2026-11-04")
        self.store.create_maintenance(
            self.vehicle["id"], "maintenance", "2026-12-01", MANAGER)
        session = self.make_session()
        self.store.close_charging_session(session["id"], MANAGER)
        view = self.ext.analytics_view(MANAGER, run["id"])
        self.assertEqual(view["latest_odometer"], 12000)
        self.assertEqual(view["maintenance_completed_share"], "1/2")
        self.assertEqual(view["charging_closed_share"], 1)
        self.assertEqual(view["total_watt_hours"], 500)
        self.assertIs(view["optimized_here"], False)

    def test_no_score_shaped_key_anywhere(self):
        run = self.ext.record_report_run(MANAGER, "Scan")
        stream = self.ext.create_telematics_stream(
            MANAGER, self.vehicle["id"], "gps_stream", "S-1")
        report = self.ext.record_telematics_report(
            MANAGER, stream["id"], "position_report", "Yard")
        forecast = self.ext.record_forecast_input(
            MANAGER, "Depot A", "demand", "2026-W45", 3)
        session = self.make_session()
        payment = self.ext.record_payment(
            MANAGER, session["id"], "capture", 100, "P-1",
            "reported_captured")
        for surface in (
                stream, report, forecast, payment,
                self.ext.forecast_view(MANAGER, "Depot A"),
                self.ext.analytics_view(MANAGER, run["id"]),
                self.ext.session_payments_view(MANAGER, session["id"]),
                self.ext.platform_operations_view(MANAGER)):
            _scan_no_forbidden(surface)

    def test_optimization_request_is_reference_only(self):
        request = self.ext.record_optimization_request(
            MANAGER, "Depot A utilization")
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["optimized_here"], False)


class TestPlatformOperationsReference(BatchCase):
    def test_operation_record_and_counts_view(self):
        record = self.ext.record_platform_operation(
            MANAGER, "incident", "reported_degraded",
            detail_ref="OPS-REF-1")
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["operated_here"], False)
        self.assertIs(record["hosted_here"], False)
        self.ext.record_platform_operation(
            MANAGER, "incident", "reported_resolved")
        view = self.ext.platform_operations_view(MANAGER)
        self.assertEqual(view["operation_count"], 2)
        self.assertEqual(view["counts_by_kind"], {"incident": 2})
        self.assertEqual(view["counts_by_status"],
                         {"reported_degraded": 1,
                          "reported_resolved": 1})


class TestCrossCutting(BatchCase):
    def test_viewer_write_denied_and_audited(self):
        entries_before = len(self.store.audit.entries())
        with self.assertRaises(PermissionDenied):
            self.ext.create_route_plan(VIEWER, "Nope", "planned_route")
        entries = self.store.audit.entries()
        self.assertEqual(len(entries), entries_before + 1)
        self.assertTrue(
            entries[-1]["action"].endswith(":denied"))
        # The denied attempt consumed no id.
        plan = self.ext.create_route_plan(
            MANAGER, "Ok", "planned_route")
        self.assertEqual(plan["id"], "rtp-1")

    def test_no_actor_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_report_run(None, "Nope")

    def test_audit_records_extension_mutations(self):
        self.ext.create_route_plan(MANAGER, "Audited", "planned_route")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_route_plan_create", actions)


if __name__ == "__main__":
    unittest.main()
