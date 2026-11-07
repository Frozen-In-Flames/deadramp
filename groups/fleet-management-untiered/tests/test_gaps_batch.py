"""Final GAPS batch tests — Fleet Management untiered set
(Untiered Set 15), 7 open entries.

Traces to: GAPS.md section "Untiered Set 15 — Fleet Management
(2 forks, tier null)", entries idx 875–881 in
gaps-batch/inventory.json, closed per gaps-batch/DECISION.md
(ratified 2026-11-07):

- Live telematics & GPS streaming — reference
- Integration engines & external connectors — reference
- Video-based safety & dash-camera analytics engines — reference
- IoT device telemetry ingestion & equipment/environmental
  monitoring engines — reference
- Alerting & notification engines — built (records form)
- Driver workflow & compliance applications — reference
- Dashboarding front-ends beyond registry reporting — built
  (definitions + read-time derivation)

Pins, per entry: the exact record key sets; the stub labels
(``reference_stub: True`` and the ``*_here: False`` flags on the
records themselves); reported figures and labels stored
verbatim; derivations at read (report/outcome/event/observation
counts, alert counts, dashboard panel figures) with stored
records carrying no derived figure; ``TypeError`` on smuggled
keyword arguments — including any coordinate kwarg (no
coordinate field can exist); and the category's inverse
invariant: no charge-control surface exists on the extension
(no method can command a charging session).

Cross-cutting pins: a recursive scan asserting no
tier/baseline/impact/CMMC-shaped key exists anywhere on the
extension surface (tier-null discipline) and no
score/rating/rank/grade/index or coordinate-shaped key exists;
viewer writes are denied and audited with ``:denied`` and
consume no id; and the fresh negative control for the
dashboard derivation seam ``_maintenance_completed_share``.
"""

import unittest
from fractions import Fraction

from fleet_helpers import ADMIN, MANAGER, VIEWER, make_store

from fleet.errors import NotFoundError, PermissionDenied, ValidationError
from fleet.extensions import (
    FleetUntieredExtensions, _maintenance_completed_share,
)

FORBIDDEN_KEY_PARTS = (
    "score", "rating", "rank", "grade", "index",
    "latitude", "longitude", "coordinate",
)
TIER_KEY_PARTS = (
    "tier", "cmmc", "baseline", "impact", "fedramp",
)


def _scan_keys(value, parts, path="root"):
    """Recursively assert no key contains any of ``parts``."""
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            for part in parts:
                assert part not in lowered, (path, key)
            _scan_keys(item, parts, "%s.%s" % (path, key))
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _scan_keys(item, parts, "%s[%d]" % (path, i))


class BatchCase(unittest.TestCase):
    def setUp(self):
        self.store, self.vehicle, self.operator = make_store()
        self.ext = FleetUntieredExtensions(self.store)

    def make_stream(self):
        return self.ext.create_telematics_stream(
            MANAGER, self.vehicle["id"], "gps_stream", "STREAM-REF-1")

    def make_rule(self):
        return self.ext.create_alert_rule(
            MANAGER, "Depot door rule", "door reported open")

    def make_alert(self):
        rule = self.make_rule()
        return self.ext.record_alert(
            MANAGER, rule["id"], "DEPOT-A", "reported_warning")


class TestTelematicsReference(BatchCase):
    def test_stream_record_exact_keys_and_labels(self):
        stream = self.make_stream()
        self.assertEqual(
            set(stream),
            {"id", "vehicle_id", "kind", "source_ref",
             "reference_stub", "state", "streamed_here",
             "created_by", "created_utc"})
        self.assertEqual(stream["id"], "tlm-1")
        self.assertIs(stream["reference_stub"], True)
        self.assertEqual(stream["state"], "recorded_reference_only")
        self.assertIs(stream["streamed_here"], False)

    def test_report_verbatim_and_standalone(self):
        stream = self.make_stream()
        report = self.ext.record_telematics_report(
            MANAGER, stream["id"], "position_report",
            "Depot A, bay 3", "reported_moving")
        self.assertEqual(
            set(report),
            {"id", "stream_id", "kind", "position_label",
             "status_label", "tracked_here", "sensed_here",
             "reference_stub", "state", "created_by", "created_utc"})
        self.assertEqual(report["position_label"], "Depot A, bay 3")
        self.assertIs(report["tracked_here"], False)
        self.assertIs(report["sensed_here"], False)

    def test_no_coordinate_kwarg_can_exist(self):
        stream = self.make_stream()
        with self.assertRaises(TypeError):
            self.ext.record_telematics_report(
                MANAGER, stream["id"], "position_report",
                "somewhere", latitude=32.9)
        with self.assertRaises(TypeError):
            self.ext.record_telematics_report(
                MANAGER, stream["id"], "position_report",
                "somewhere", longitude=-96.9)

    def test_view_derives_report_count(self):
        stream = self.make_stream()
        stored = self.ext.telematics_stream_view(MANAGER, stream["id"])
        self.assertEqual(stored["report_count"], 0)
        self.ext.record_telematics_report(
            MANAGER, stream["id"], "status_report", "Depot A")
        self.ext.record_telematics_report(
            MANAGER, stream["id"], "status_report", "Depot B")
        view = self.ext.telematics_stream_view(MANAGER, stream["id"])
        self.assertEqual(view["report_count"], 2)

    def test_unknown_vehicle_and_kind_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_telematics_stream(
                MANAGER, "veh-99", "gps_stream", "X")
        with self.assertRaises(ValidationError):
            self.ext.create_telematics_stream(
                MANAGER, self.vehicle["id"], "lidar", "X")


class TestConnectorsReference(BatchCase):
    def test_connector_record_exact_keys_and_labels(self):
        conn = self.ext.create_connector(
            MANAGER, "Maintenance system", "outbound", "ENDPOINT-REF-1")
        self.assertEqual(
            set(conn),
            {"id", "system_label", "direction_label", "endpoint_ref",
             "reference_stub", "state", "connected_here",
             "invoked_here", "created_by", "created_utc"})
        self.assertEqual(conn["id"], "con-1")
        self.assertIs(conn["reference_stub"], True)
        self.assertIs(conn["connected_here"], False)
        self.assertIs(conn["invoked_here"], False)

    def test_outcome_verbatim_and_count_derived(self):
        conn = self.ext.create_connector(
            MANAGER, "Billing system", "bidirectional", "EP-2")
        outcome = self.ext.record_connector_outcome(
            MANAGER, conn["id"], "reported_partial")
        self.assertEqual(outcome["outcome_label"], "reported_partial")
        self.assertIs(outcome["reference_stub"], True)
        self.ext.record_connector_outcome(
            MANAGER, conn["id"], "reported_succeeded")
        view = self.ext.connector_view(MANAGER, conn["id"])
        self.assertEqual(view["outcome_count"], 2)
        with self.assertRaises(ValidationError):
            self.ext.record_connector_outcome(
                MANAGER, conn["id"], "reported_lost")


class TestVideoSafetyReference(BatchCase):
    def test_binding_and_event_shapes(self):
        binding = self.ext.create_camera_binding(
            MANAGER, self.vehicle["id"], "dash_camera", "CAM-REF-1")
        self.assertIs(binding["footage_held_here"], False)
        self.assertIs(binding["connected_here"], False)
        event = self.ext.record_video_event(
            MANAGER, binding["id"], "reported_hard_brake",
            "reported_high")
        self.assertEqual(
            set(event),
            {"id", "binding_id", "event_kind", "severity_label",
             "analyzed_here", "detected_here", "footage_held_here",
             "reference_stub", "state", "created_by", "created_utc"})
        self.assertIs(event["analyzed_here"], False)
        view = self.ext.camera_binding_view(MANAGER, binding["id"])
        self.assertEqual(view["event_count"], 1)

    def test_no_footage_kwarg_can_exist(self):
        binding = self.ext.create_camera_binding(
            MANAGER, self.vehicle["id"], "dash_camera", "CAM-REF-1")
        with self.assertRaises(TypeError):
            self.ext.record_video_event(
                MANAGER, binding["id"], "reported_collision",
                "reported_critical", footage="frame-data")


class TestIotReference(BatchCase):
    def test_device_and_observation_shapes(self):
        device = self.ext.create_iot_device(
            MANAGER, "environmental_sensor", "SENSOR-REF-1",
            "Depot A air quality")
        self.assertIs(device["ingested_here"], False)
        self.assertIs(device["connected_here"], False)
        obs = self.ext.record_iot_observation(
            MANAGER, device["id"], "temperature", "reported 21C")
        self.assertEqual(obs["reported_value_label"], "reported 21C")
        self.assertIs(obs["sensed_here"], False)
        self.assertIs(obs["ingested_here"], False)
        view = self.ext.iot_device_view(MANAGER, device["id"])
        self.assertEqual(view["observation_count"], 1)

    def test_unknown_device_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_iot_observation(
                MANAGER, "iot-99", "temperature", "reported 21C")


class TestAlertingBuilt(BatchCase):
    def test_rule_is_data_never_evaluated(self):
        rule = self.make_rule()
        self.assertEqual(
            set(rule),
            {"id", "label", "condition_label", "evaluated_here",
             "created_by", "created_utc"})
        self.assertIs(rule["evaluated_here"], False)

    def test_alert_recorded_not_detected(self):
        alert = self.make_alert()
        self.assertIs(alert["detected_here"], False)
        self.assertEqual(alert["severity_label"], "reported_warning")

    def test_notification_is_delivery_attempt_record(self):
        alert = self.make_alert()
        note = self.ext.record_notification(
            MANAGER, alert["id"], "email", "RECIP-REF-1",
            "reported_delivered")
        self.assertEqual(
            set(note),
            {"id", "alert_id", "channel_kind", "recipient_ref",
             "outcome_label", "reference_transport", "delivered_here",
             "created_by", "created_utc"})
        self.assertIs(note["reference_transport"], True)
        self.assertIs(note["delivered_here"], False)
        with self.assertRaises(TypeError):
            self.ext.record_notification(
                MANAGER, alert["id"], "email", "RECIP-REF-1",
                "reported_delivered", message="hello")

    def test_alerts_view_counts_derived(self):
        alert = self.make_alert()
        self.ext.record_notification(
            MANAGER, alert["id"], "sms", "RECIP-REF-2",
            "reported_failed")
        view = self.ext.alerts_view(MANAGER)
        self.assertEqual(view["rule_count"], 1)
        self.assertEqual(view["alert_count"], 1)
        self.assertEqual(view["alerts_by_severity"],
                         {"reported_warning": 1})
        self.assertEqual(view["notifications_by_outcome"],
                         {"reported_failed": 1})
        self.assertIs(view["delivered_here"], False)


class TestDriverWorkflowReference(BatchCase):
    def test_task_and_compliance_shapes(self):
        task = self.ext.create_workflow_task(
            MANAGER, self.operator["id"], "Pre-trip inspection",
            "reported_completed")
        self.assertEqual(
            set(task),
            {"id", "operator_id", "task_label", "status_label",
             "reference_stub", "state", "executed_here",
             "created_by", "created_utc"})
        self.assertIs(task["executed_here"], False)
        record = self.ext.record_compliance_application(
            MANAGER, "Hours-of-service application",
            "reported_compliant")
        self.assertIs(record["evaluated_here"], False)
        self.assertIs(record["reference_stub"], True)
        view = self.ext.workflow_view(MANAGER, self.operator["id"])
        self.assertEqual(view["task_count"], 1)
        self.assertEqual(view["tasks_by_status"],
                         {"reported_completed": 1})


class TestDashboardingBuilt(BatchCase):
    def _seed_registry(self):
        # Two completed maintenance records and one past-due
        # uncompleted (derived overdue) -> completed share 2/3.
        m1 = self.store.create_maintenance(
            self.vehicle["id"], "inspection", "2026-01-10", MANAGER)
        m2 = self.store.create_maintenance(
            self.vehicle["id"], "inspection", "2026-01-12", MANAGER)
        self.store.create_maintenance(
            self.vehicle["id"], "inspection", "2026-01-15", MANAGER)
        self.store.complete_maintenance(m1["id"], MANAGER, "2026-01-09")
        self.store.complete_maintenance(m2["id"], MANAGER, "2026-01-11")
        self.store.record_usage(self.vehicle["id"], 12000, MANAGER)
        session = self.store.create_charging_session(
            "STN-REF-1", "OP-REF-001", MANAGER, watt_hours=500)
        self.store.close_charging_session(
            session["id"], MANAGER, watt_hours=22500)

    def test_dashboard_record_is_definition_only(self):
        dash = self.ext.create_dashboard(
            MANAGER, "Ops board", ["record_counts", "charging_energy"])
        self.assertEqual(
            set(dash),
            {"id", "label", "panel_kinds", "rendered_here",
             "created_by", "created_utc"})
        self.assertIs(dash["rendered_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.create_dashboard(MANAGER, "Bad", ["pie_chart"])

    def test_view_derives_figures_at_read(self):
        dash = self.ext.create_dashboard(
            MANAGER, "Ops board",
            ["record_counts", "charging_energy",
             "maintenance_completed_share", "latest_odometer"])
        self._seed_registry()
        view = self.ext.dashboard_view(MANAGER, dash["id"])
        self.assertIs(view["rendered_here"], False)
        self.assertEqual(view["panels"]["record_counts"]["vehicles"], 1)
        self.assertEqual(
            view["panels"]["charging_energy"]["total_watt_hours"], 22500)
        self.assertEqual(
            view["panels"]["maintenance_completed_share"], "2/3")
        self.assertEqual(view["panels"]["latest_odometer"], 12000)

    def test_view_tracks_later_registry_state(self):
        dash = self.ext.create_dashboard(
            MANAGER, "Ops board", ["record_counts"])
        self.store.create_vehicle("Pool Sedan 2", "sedan", ADMIN)
        view = self.ext.dashboard_view(MANAGER, dash["id"])
        self.assertEqual(view["panels"]["record_counts"]["vehicles"], 2)

    def test_empty_share_is_none(self):
        dash = self.ext.create_dashboard(
            MANAGER, "Empty board", ["maintenance_completed_share"])
        view = self.ext.dashboard_view(MANAGER, dash["id"])
        self.assertIsNone(view["panels"]["maintenance_completed_share"])


class TestCompletedShareNegativeControl(BatchCase):
    """Fresh negative control for the seam
    ``_maintenance_completed_share``: the traced claim is that
    the dashboard's maintenance panel is the share of records
    whose CORE-derived status is ``completed``."""

    def _views(self):
        self.store.create_maintenance(
            self.vehicle["id"], "inspection", "2026-01-10", MANAGER)
        m2 = self.store.create_maintenance(
            self.vehicle["id"], "inspection", "2026-01-12", MANAGER)
        m3 = self.store.create_maintenance(
            self.vehicle["id"], "inspection", "2026-01-15", MANAGER)
        self.store.complete_maintenance(m2["id"], MANAGER, "2026-01-11")
        self.store.complete_maintenance(m3["id"], MANAGER, "2026-01-14")
        return self.store.list_maintenance(actor=MANAGER)

    def test_canonical_share_exact(self):
        views = self._views()
        self.assertEqual(
            _maintenance_completed_share(views), Fraction(2, 3))

    def test_overdue_counting_mutant_is_rejected(self):
        views = self._views()
        canonical = _maintenance_completed_share(views)

        def mutant(vs):
            if not vs:
                return None
            return Fraction(
                sum(1 for v in vs
                    if v["derived_status"] == "overdue"), len(vs))

        self.assertEqual(mutant(views), Fraction(1, 3))
        self.assertNotEqual(mutant(views), canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant(views), Fraction(2, 3))


class TestCrossCutting(BatchCase):
    def _exercise_surface(self):
        stream = self.make_stream()
        self.ext.record_telematics_report(
            MANAGER, stream["id"], "status_report", "Depot A")
        conn = self.ext.create_connector(
            MANAGER, "Maintenance system", "outbound", "EP-1")
        self.ext.record_connector_outcome(
            MANAGER, conn["id"], "reported_succeeded")
        binding = self.ext.create_camera_binding(
            MANAGER, self.vehicle["id"], "dash_camera", "CAM-1")
        self.ext.record_video_event(
            MANAGER, binding["id"], "reported_speeding", "reported_low")
        device = self.ext.create_iot_device(
            MANAGER, "vehicle_gateway", "GW-1", "Pool Sedan 1")
        self.ext.record_iot_observation(
            MANAGER, device["id"], "odometer", "reported 12000")
        alert = self.make_alert()
        self.ext.record_notification(
            MANAGER, alert["id"], "push", "RECIP-1", "reported_pending")
        self.ext.create_workflow_task(
            MANAGER, self.operator["id"], "Fuel stop",
            "reported_assigned")
        self.ext.record_compliance_application(
            MANAGER, "ELD application", "reported_pending_review")
        dash = self.ext.create_dashboard(
            MANAGER, "Board", ["record_counts"])
        return {
            "stream_view": self.ext.telematics_stream_view(
                MANAGER, stream["id"]),
            "connector_view": self.ext.connector_view(MANAGER, conn["id"]),
            "binding_view": self.ext.camera_binding_view(
                MANAGER, binding["id"]),
            "device_view": self.ext.iot_device_view(MANAGER, device["id"]),
            "alerts_view": self.ext.alerts_view(MANAGER),
            "workflow_view": self.ext.workflow_view(
                MANAGER, self.operator["id"]),
            "dashboard_view": self.ext.dashboard_view(MANAGER, dash["id"]),
        }

    def test_tier_null_scan_over_surface(self):
        surface = self._exercise_surface()
        _scan_keys(surface, TIER_KEY_PARTS)

    def test_no_score_or_coordinate_keys_anywhere(self):
        surface = self._exercise_surface()
        _scan_keys(surface, FORBIDDEN_KEY_PARTS)

    def test_no_charge_control_surface_exists(self):
        # The category's inverse invariant: nothing on this
        # surface can command a charging session.
        surface_names = [n for n in dir(self.ext)
                         if not n.startswith("_")]
        for name in surface_names:
            lowered = name.lower()
            self.assertNotIn("charge", lowered)
            self.assertNotIn("command", lowered)
            self.assertNotIn("control_session", lowered)

    def test_viewer_write_denied_and_audited(self):
        entries_before = len(self.store.audit.entries())
        with self.assertRaises(PermissionDenied):
            self.ext.create_alert_rule(VIEWER, "Nope", "nothing")
        entries = self.store.audit.entries()
        self.assertEqual(len(entries), entries_before + 1)
        self.assertTrue(entries[-1]["action"].endswith(":denied"))
        rule = self.make_rule()
        self.assertEqual(rule["id"], "alr-1")

    def test_no_actor_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_dashboard(None, "Nope", ["record_counts"])

    def test_audit_records_extension_mutations(self):
        self.make_rule()
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_alert_rule_create", actions)


if __name__ == "__main__":
    unittest.main()
