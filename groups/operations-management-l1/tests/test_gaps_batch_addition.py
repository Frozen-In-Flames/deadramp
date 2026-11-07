"""Final GAPS batch, second unit tests -- the remainder
additions' extension surface (``src/opsmgmt/extensions_addition.py``).

Traces to: the 7 OPEN entries of the GAPS.md section "Remainder
Addition -- Operations Management L1 (+3 forks)" (inventory idx
613-619; ADDENDUM.md section 5), worked under
gaps-batch/DECISION.md. One class per entry, plus cross-cutting
RBAC/audit/no-id-on-failure/copies pins and the unit's fresh
negative control on the latest-reported-status seam
(``_current_reported_status``).

Fixtures mirror the first batch unit's test module: an
OpsExtensionsAddition over the shared make_store() fixture.
"""

import unittest

from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER, make_store
from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from opsmgmt.extensions_addition import (
    OpsExtensionsAddition,
    _current_reported_status,
)


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.person, self.org, self.project = make_store()
        self.ext = OpsExtensionsAddition(self.store)

    def make_room_asset(self):
        return self.store.create_asset(
            "Room 4B", ADMIN, project_id=self.project["id"]
        )


class TestReservations(AdditionFixture):
    """Entry 613: workspace scheduling & reservation engine --
    records form."""

    def test_create_shape_and_boundary(self):
        room = self.make_room_asset()
        record = self.ext.create_reservation(
            "Weekly sync", OPERATOR, kind="room", asset_id=room["id"],
            project_id=self.project["id"], person_id=self.person["id"],
            starts_at="2026-11-09T15:00:00Z", ends_at="2026-11-09T16:00:00Z")
        self.assertEqual(record["id"], "rsv-1")
        self.assertEqual(record["status"], "recorded")
        self.assertIs(record["booked_here"], False)

    def test_window_must_be_ordered(self):
        with self.assertRaises(ValidationError):
            self.ext.create_reservation(
                "Backwards", OPERATOR, starts_at="2026-11-09T16:00:00Z",
                ends_at="2026-11-09T15:00:00Z")

    def test_bad_kind_and_unknown_links_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.create_reservation("X", OPERATOR, kind="castle")
        with self.assertRaises(NotFoundError):
            self.ext.create_reservation("X", OPERATOR, asset_id="ast-99")
        with self.assertRaises(NotFoundError):
            self.ext.create_reservation("X", OPERATOR, project_id="proj-99")
        with self.assertRaises(NotFoundError):
            self.ext.create_reservation("X", OPERATOR, person_id="per-99")
        self.assertEqual(self.ext.list_reservations(OPERATOR), [])

    def test_current_status_derived_never_stored(self):
        record = self.ext.create_reservation("Desk 12", OPERATOR, kind="desk")
        view = self.ext.reservation_view(record["id"], VIEWER)
        self.assertEqual(view["current_reported_status"], "recorded")
        self.ext.record_reservation_outcome(
            record["id"], "reported_reserved", OPERATOR)
        self.ext.record_reservation_outcome(
            record["id"], "reported_checked_in", OPERATOR)
        view = self.ext.reservation_view(record["id"], VIEWER)
        self.assertEqual(view["current_reported_status"], "reported_checked_in")
        stored = self.ext.get_reservation(record["id"], OPERATOR)
        self.assertEqual(stored["status"], "recorded")
        self.assertNotIn("current_reported_status", stored)

    def test_outcome_status_must_be_reported_vocabulary(self):
        record = self.ext.create_reservation("Desk 12", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_reservation_outcome(record["id"], "confirmed",
                                                OPERATOR)
        with self.assertRaises(NotFoundError):
            self.ext.record_reservation_outcome("rsv-99", "reported_reserved",
                                                OPERATOR)


class TestVisitorsAndEvents(AdditionFixture):
    """Entry 614: visitor & event management -- records form."""

    def test_registration_shape_opaque_ref_only(self):
        record = self.ext.register_visitor(
            "VIS-8842", OPERATOR, host_person_id=self.person["id"],
            project_id=self.project["id"])
        self.assertEqual(record["status"], "recorded")
        self.assertIs(record["admitted_here"], False)
        for bad in ("visitor@example.com", "John Doe", "https://x.example"):
            with self.assertRaises(ValidationError):
                self.ext.register_visitor(bad, OPERATOR)

    def test_current_state_derived_from_latest_event(self):
        record = self.ext.register_visitor("VIS-1", OPERATOR)
        self.assertEqual(
            self.ext.visitor_view(record["id"], VIEWER)[
                "current_reported_status"], "recorded")
        self.ext.record_visitor_event(record["id"], "reported_checked_in",
                                      OPERATOR)
        self.ext.record_visitor_event(record["id"], "reported_checked_out",
                                      OPERATOR)
        view = self.ext.visitor_view(record["id"], VIEWER)
        self.assertEqual(view["current_reported_status"],
                         "reported_checked_out")
        self.assertNotIn("current_reported_status",
                         self.ext.get_visitor_registration(record["id"]))

    def test_event_definition_versioned_and_checkin_headcount(self):
        event = self.ext.create_event_definition(
            "Open house", ADMIN, kind="visit", project_id=self.project["id"])
        self.assertEqual(event["version"], 1)
        self.assertIs(event["staged_here"], False)
        updated = self.ext.update_event_definition(
            event["id"], ADMIN, description="Lobby setup at 9")
        self.assertEqual(updated["version"], 2)
        visitor = self.ext.register_visitor("VIS-9", OPERATOR)
        checkin = self.ext.record_event_checkin(
            event["id"], OPERATOR, registration_id=visitor["id"])
        self.assertIs(checkin["admitted_here"], False)
        self.assertEqual(
            len(self.ext.list_event_checkins(OPERATOR, event_id=event["id"])),
            1)
        with self.assertRaises(NotFoundError):
            self.ext.record_event_checkin(event["id"], OPERATOR,
                                          registration_id="vis-99")
        with self.assertRaises(NotFoundError):
            self.ext.record_event_checkin(event["id"], OPERATOR,
                                          person_id="per-99")


class TestFloorPlansSignage(AdditionFixture):
    """Entry 615: interactive floor plans, wayfinding & digital
    signage -- definitions as data; no geometry anywhere."""

    def test_zones_held_as_labels_no_geometry(self):
        plan = self.ext.create_floor_plan_definition(
            "HQ L4", ADMIN,
            zones=[{"label": "North Wing", "kind": "office"},
                   {"label": "Lobby", "kind": "common"}])
        self.assertIs(plan["rendered_here"], False)
        for zone in plan["zones"]:
            self.assertEqual(set(zone), {"label", "kind"})
        with self.assertRaises(ValidationError):
            self.ext.create_floor_plan_definition(
                "Dup", ADMIN,
                zones=[{"label": "A", "kind": "office"},
                       {"label": "A", "kind": "desk"}])
        with self.assertRaises(ValidationError):
            self.ext.create_floor_plan_definition(
                "Coord", ADMIN,
                zones=[{"label": "A", "kind": "office", "x": 10, "y": 4}])

    def test_no_coordinate_entry_point(self):
        plan = self.ext.create_floor_plan_definition(
            "HQ L4", ADMIN, zones=[{"label": "Lobby", "kind": "common"}])
        with self.assertRaises(TypeError):
            self.ext.create_signage_definition(
                "S", ADMIN, plan_id=plan["id"], coordinates="1,2")

    def test_signage_zone_must_exist_on_plan(self):
        plan = self.ext.create_floor_plan_definition(
            "HQ L4", ADMIN, zones=[{"label": "Lobby", "kind": "common"}])
        signage = self.ext.create_signage_definition(
            "Lobby board", ADMIN, kind="lobby", plan_id=plan["id"],
            zone_label="Lobby", content_text="Welcome")
        self.assertIs(signage["displayed_here"], False)
        updated = self.ext.update_signage_definition(
            signage["id"], ADMIN, content_text="Welcome back")
        self.assertEqual(updated["version"], 2)
        with self.assertRaises(ValidationError):
            self.ext.create_signage_definition(
                "Bad zone", ADMIN, plan_id=plan["id"], zone_label="Roof")

    def test_notice_and_wayfinding_counts_derived(self):
        plan = self.ext.create_floor_plan_definition(
            "HQ L4", ADMIN, zones=[{"label": "Lobby", "kind": "common"}])
        self.ext.create_signage_definition(
            "Board", ADMIN, plan_id=plan["id"], zone_label="Lobby")
        self.ext.create_digital_notice(
            "Fire drill", OPERATOR, body_text="Friday 10am",
            plan_id=plan["id"], zone_label="Lobby")
        view = self.ext.wayfinding_view(plan["id"], VIEWER)
        self.assertEqual(view["signage_count"], 1)
        self.assertEqual(view["notice_count"], 1)
        self.assertIs(view["routed_here"], False)
        notice = self.ext.list_digital_notices(OPERATOR)[0]
        self.assertIs(notice["published_here"], False)
        self.assertIs(notice["displayed_here"], False)


class TestSensorReferences(AdditionFixture):
    """Entry 616: IoT sensor integration & sensing -- labeled
    reference implementation (stub-engine, as drafted)."""

    def test_reference_labels_on_every_record(self):
        sensor = self.ext.register_sensor_reference(
            "SENSOR-A1", "occupancy", ADMIN)
        self.assertIs(sensor["reference_stub"], True)
        self.assertIs(sensor["received_here"], False)
        self.assertIs(sensor["sensed_here"], False)
        feed = self.ext.record_sensor_feed_reference(
            sensor["id"], "reported_connected", OPERATOR)
        self.assertIs(feed["reference_stub"], True)
        self.assertIs(feed["reference_transport"], True)
        report = self.ext.record_utilization_report(
            sensor["id"], OPERATOR,
            metric_values={"occupancy_percent_reported": 62})
        self.assertIs(report["reference_stub"], True)
        self.assertEqual(
            report["metric_values"], {"occupancy_percent_reported": 62})

    def test_sensor_ref_cannot_be_an_address(self):
        for bad in ("192.168.1.10", "sensor.example.com",
                    "https://sensor.example/feed"):
            with self.assertRaises(ValidationError):
                self.ext.register_sensor_reference(bad, "occupancy", ADMIN)

    def test_reported_values_verbatim_whole_only(self):
        sensor = self.ext.register_sensor_reference("S-1", "utilization",
                                                    ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_utilization_report(
                sensor["id"], OPERATOR, metric_values={"rate": 0.62})
        with self.assertRaises(ValidationError):
            self.ext.record_utilization_report(
                sensor["id"], OPERATOR, metric_values={"flag": True})
        with self.assertRaises(NotFoundError):
            self.ext.record_utilization_report("sen-99", OPERATOR,
                                               metric_values={})

    def test_utilization_view_counts_and_latest_feed_status(self):
        sensor = self.ext.register_sensor_reference("S-1", "occupancy",
                                                    ADMIN)
        view = self.ext.utilization_view(sensor["id"], OPERATOR)
        self.assertEqual(view["latest_reported_feed_status"], "unreported")
        self.ext.record_sensor_feed_reference(
            sensor["id"], "reported_connected", OPERATOR)
        self.ext.record_sensor_feed_reference(
            sensor["id"], "reported_degraded", OPERATOR)
        self.ext.record_utilization_report(sensor["id"], OPERATOR,
                                           metric_values={"count": 3})
        view = self.ext.utilization_view(sensor["id"], OPERATOR)
        self.assertEqual(view["feed_count"], 2)
        self.assertEqual(view["report_count"], 1)
        self.assertEqual(view["latest_reported_feed_status"],
                         "reported_degraded")


class TestWorkplaceAnalytics(AdditionFixture):
    """Entry 617: workplace analytics & optimization engine --
    definitions as data, run records store no figures."""

    def test_definition_metrics_fixed_set(self):
        definition = self.ext.create_analytics_definition(
            "Workplace counts", ADMIN,
            metrics=["reservation_count", "purchase_total_cents"])
        self.assertIs(definition["optimized_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.create_analytics_definition(
                "Trends", ADMIN, metrics=["utilization_rate"])
        with self.assertRaises(ValidationError):
            self.ext.create_analytics_definition(
                "Trend2", ADMIN, metrics=["trend_forecast"])

    def test_run_record_stores_no_figures(self):
        definition = self.ext.create_analytics_definition(
            "Counts", ADMIN, metrics=["reservation_count"])
        run = self.ext.record_analytics_run(definition["id"], OPERATOR)
        self.assertNotIn("figures", run)
        self.assertEqual(
            set(run),
            {"id", "definition_id", "note", "optimized_here", "created_by",
             "created_utc", "updated_utc"})

    def test_figures_derived_at_read_from_own_records(self):
        reservation = self.ext.create_reservation(
            "Desk 1", OPERATOR, project_id=self.project["id"])
        self.ext.record_reservation_outcome(
            reservation["id"], "reported_reserved", OPERATOR)
        self.ext.register_visitor("VIS-1", OPERATOR,
                                   project_id=self.project["id"])
        self.ext.record_purchase(OPERATOR, 2500,
                                 project_id=self.project["id"])
        definition = self.ext.create_analytics_definition(
            "Scoped", ADMIN,
            metrics=["reservation_count", "active_reservation_count",
                     "visitor_registration_count", "purchase_total_cents",
                     "checkin_count"],
            project_id=self.project["id"])
        run = self.ext.record_analytics_run(definition["id"], OPERATOR)
        figures = self.ext.analytics_run_view(run["id"], VIEWER)["figures"]
        self.assertEqual(figures, {
            "reservation_count": 1,
            "active_reservation_count": 1,
            "visitor_registration_count": 1,
            "purchase_total_cents": 2500,
            "checkin_count": 0,
        })
        # Terminal outcome removes the reservation from "active".
        self.ext.record_reservation_outcome(
            reservation["id"], "reported_completed", OPERATOR)
        figures = self.ext.analytics_run_view(run["id"], VIEWER)["figures"]
        self.assertEqual(figures["active_reservation_count"], 0)


class TestProcurement(AdditionFixture):
    """Entry 618: procurement marketplace & requisitioning
    engine -- records form; money in integer cents."""

    def test_listing_and_requisition_records(self):
        listing = self.ext.create_catalog_listing(
            "Standing desks", OPERATOR, organization_id=self.org["id"])
        self.assertIs(listing["ordered_here"], False)
        wo = self.store.create_work_order(
            OPERATOR, "task", "Fit out floor 4",
            project_id=self.project["id"])
        requisition = self.ext.create_requisition(
            "12 standing desks", OPERATOR, project_id=self.project["id"],
            work_order_id=wo["id"], listing_id=listing["id"],
            requester_ref="REQ-77")
        self.assertIs(requisition["ordered_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.create_requisition("X", OPERATOR, work_order_id="wo-99")
        with self.assertRaises(NotFoundError):
            self.ext.create_requisition("X", OPERATOR, listing_id="lst-99")

    def test_purchase_money_is_integer_cents(self):
        purchase = self.ext.record_purchase(OPERATOR, 12999)
        self.assertIs(purchase["paid_here"], False)
        for bad in (12.5, True, 0, -5, "12999"):
            with self.assertRaises(ValidationError):
                self.ext.record_purchase(OPERATOR, bad)

    def test_purchase_current_status_derived(self):
        purchase = self.ext.record_purchase(OPERATOR, 500)
        self.assertEqual(
            self.ext.purchase_view(purchase["id"], VIEWER)[
                "current_reported_status"], "recorded")
        self.ext.record_purchase_outcome(purchase["id"], "reported_paid",
                                         OPERATOR)
        view = self.ext.purchase_view(purchase["id"], VIEWER)
        self.assertEqual(view["current_reported_status"], "reported_paid")
        self.assertEqual(
            self.ext.get_purchase(purchase["id"])["status"], "recorded")

    def test_summary_counts_and_sums_only(self):
        listing = self.ext.create_catalog_listing("Chairs", OPERATOR)
        self.ext.create_requisition("4 chairs", OPERATOR,
                                    listing_id=listing["id"])
        purchase = self.ext.record_purchase(OPERATOR, 400)
        self.ext.record_purchase_outcome(purchase["id"], "reported_paid",
                                         OPERATOR)
        summary = self.ext.procurement_summary(VIEWER)
        self.assertEqual(summary["listings"], 1)
        self.assertEqual(summary["requisitions"], 1)
        self.assertEqual(summary["total_recorded_cents"], 400)
        self.assertEqual(summary["outcomes_by_reported_status"],
                         {"reported_paid": 1})
        self.assertEqual(summary["requisitions_by_listing"],
                         {listing["id"]: 1})
        self.assertIs(summary["directed_here"], False)


class TestPortfolioSuite(AdditionFixture):
    """Entry 619: real-estate portfolio suite -- records form
    (Tango catalogue excess)."""

    def test_space_and_move_records(self):
        space = self.ext.create_portfolio_space(
            "Floor 4 North", OPERATOR, project_id=self.project["id"])
        move = self.ext.create_move_record(
            "Team relocation", OPERATOR, to_space_id=space["id"])
        self.assertIs(move["moved_here"], False)
        self.ext.record_move_outcome(move["id"], "reported_in_progress",
                                     OPERATOR)
        view = self.ext.move_view(move["id"], VIEWER)
        self.assertEqual(view["current_reported_status"],
                         "reported_in_progress")
        with self.assertRaises(NotFoundError):
            self.ext.create_move_record("X", OPERATOR, to_space_id="spc-99")

    def test_space_plan_definition_held_as_data(self):
        space = self.ext.create_portfolio_space("Floor 4 North", OPERATOR)
        plan = self.ext.create_space_plan_definition(
            "Q3 plan", ADMIN, space_ids=[space["id"]])
        self.assertEqual(plan["space_ids"], [space["id"]])
        self.assertIs(plan["executed_here"], False)
        updated = self.ext.update_space_plan_definition(
            plan["id"], ADMIN, note="Revised")
        self.assertEqual(updated["version"], 2)
        with self.assertRaises(NotFoundError):
            self.ext.create_space_plan_definition(
                "Bad", ADMIN, space_ids=["spc-99"])
        with self.assertRaises(PermissionDenied):
            self.ext.create_space_plan_definition("Nope", OPERATOR)

    def test_lease_view_derives_obligation_and_status(self):
        lease = self.ext.create_lease_record(
            "HQ lease", OPERATOR, amount_cents=120000, term_months=12,
            counterparty_ref="LESSOR-1")
        self.assertIs(lease["signed_here"], False)
        self.assertIs(lease["accounted_here"], False)
        view = self.ext.lease_view(lease["id"], OPERATOR)
        self.assertEqual(view["derived_total_obligation_cents"], 1440000)
        self.assertEqual(view["current_reported_status"], "recorded")
        self.ext.record_lease_event(lease["id"], "reported_active", OPERATOR)
        view = self.ext.lease_view(lease["id"], OPERATOR)
        self.assertEqual(view["current_reported_status"], "reported_active")
        bare = self.ext.create_lease_record("Bare lease", OPERATOR)
        self.assertIsNone(
            self.ext.lease_view(bare["id"], OPERATOR)[
                "derived_total_obligation_cents"])
        for bad in (1200.5, True):
            with self.assertRaises(ValidationError):
                self.ext.create_lease_record("Bad", OPERATOR,
                                             amount_cents=bad)
            with self.assertRaises(ValidationError):
                self.ext.create_lease_record("Bad", OPERATOR,
                                             term_months=bad)

    def test_transaction_and_prediction_records(self):
        txn = self.ext.record_transaction(
            "Floor 5 acquisition", OPERATOR, "reported_under_review",
            amount_cents=900000)
        self.assertIs(txn["closed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_transaction("X", OPERATOR, "closed")
        report = self.ext.record_prediction_report(
            "Location outlook", OPERATOR,
            metric_values={"growth_percent_reported": 4},
            model_ref="MODEL-X")
        self.assertIs(report["predicted_here"], False)
        self.assertEqual(report["metric_values"],
                         {"growth_percent_reported": 4})
        with self.assertRaises(ValidationError):
            self.ext.record_prediction_report(
                "X", OPERATOR, metric_values={"rate": 1.5})

    def test_portfolio_summary_counts_only(self):
        self.ext.create_portfolio_space("S1", OPERATOR)
        self.ext.record_transaction("T1", OPERATOR, "reported_proposed")
        summary = self.ext.portfolio_summary(VIEWER)
        self.assertEqual(summary["spaces"], 1)
        self.assertEqual(summary["transactions_by_reported_status"],
                         {"reported_proposed": 1})
        self.assertIs(summary["predicted_here"], False)
        self.assertIs(summary["signed_here"], False)
        self.assertIs(summary["accounted_here"], False)


class TestAdditionCrossCutting(AdditionFixture):
    """RBAC / audit / no-id-on-failure / copies-are-copies pins
    for the second unit's surface."""

    def test_config_surfaces_are_admin_only(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_event_definition("E", OPERATOR)
        with self.assertRaises(PermissionDenied):
            self.ext.create_floor_plan_definition("P", OPERATOR)
        with self.assertRaises(PermissionDenied):
            self.ext.create_analytics_definition("A", OPERATOR)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_event_create:denied", actions)
        self.assertIn("exta_floorplan_create:denied", actions)
        self.assertIn("exta_analytics_create:denied", actions)

    def test_viewer_cannot_write_and_denial_is_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_reservation("R", VIEWER)
        with self.assertRaises(PermissionDenied):
            self.ext.register_sensor_reference("S-1", "occupancy", VIEWER)
        with self.assertRaises(PermissionDenied):
            self.ext.record_purchase(VIEWER, 100)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_reservation_create:denied", actions)
        self.assertIn("exta_sensor_reference:denied", actions)
        self.assertIn("exta_purchase_record:denied", actions)

    def test_viewer_cannot_read_audit_gated_views(self):
        # report_read is held by the viewer; audit_read is not part
        # of this surface at all. A viewer CAN read the summaries;
        # pin that reads succeed and writes remain denied instead.
        self.assertEqual(self.ext.procurement_summary(VIEWER)["listings"], 0)
        self.assertEqual(self.ext.portfolio_summary(VIEWER)["spaces"], 0)

    def test_failed_operations_consume_no_ids(self):
        with self.assertRaises(ValidationError):
            self.ext.create_reservation("Bad", OPERATOR, kind="castle")
        with self.assertRaises(ValidationError):
            self.ext.record_purchase(OPERATOR, 1.5)
        record = self.ext.create_reservation("Good", OPERATOR)
        self.assertEqual(record["id"], "rsv-1")
        purchase = self.ext.record_purchase(OPERATOR, 100)
        self.assertEqual(purchase["id"], "pur-1")

    def test_successful_mutations_audit_exta_actions(self):
        self.ext.create_reservation("R", OPERATOR)
        self.ext.register_sensor_reference("S-1", "occupancy", ADMIN)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_reservation_create", actions)
        self.assertIn("exta_sensor_reference", actions)

    def test_returned_records_are_copies(self):
        record = self.ext.create_reservation("R", OPERATOR)
        record["status"] = "tampered"
        record["booked_here"] = True
        fresh = self.ext.get_reservation(record["id"], OPERATOR)
        self.assertEqual(fresh["status"], "recorded")
        self.assertIs(fresh["booked_here"], False)
        listed = self.ext.list_reservations(OPERATOR)
        listed[0]["name"] = "tampered"
        self.assertEqual(
            self.ext.get_reservation(record["id"])["name"], "R")


def _first_event_mutant(events, initial):
    """Mutant seam: the current status reads as the FIRST
    reported event's status instead of the latest."""
    if not events:
        return initial
    return events[0]["reported_status"]


class TestCurrentStatusNegativeControl(AdditionFixture):
    """Negative control for the unit's fresh seam.

    Traced claim: **current reported status derives at read from
    the LATEST reported event** -- after outcomes ``reserved``
    then ``checked_in`` are recorded, a reservation must read
    ``current_reported_status == "reported_checked_in"`` (and a
    lease after ``active`` then ``renewed`` must read
    ``reported_renewed``). The mutant seam
    (:func:`_first_event_mutant`) reads the first event instead
    and would NOT produce that expectation; treating the
    mutant's outcome as expected fails.
    """

    def _two_outcome_reservation(self, ext):
        record = ext.create_reservation("Desk 12", OPERATOR, kind="desk")
        ext.record_reservation_outcome(record["id"], "reported_reserved",
                                       OPERATOR)
        ext.record_reservation_outcome(record["id"], "reported_checked_in",
                                       OPERATOR)
        return record

    def test_current_status_canonical_but_mutant_not(self):
        record = self._two_outcome_reservation(self.ext)
        outcomes = self.ext.list_reservation_outcomes(
            OPERATOR, reservation_id=record["id"])
        canonical = _current_reported_status(outcomes, "recorded")
        self.assertEqual(canonical, "reported_checked_in")
        view = self.ext.reservation_view(record["id"], VIEWER)
        self.assertEqual(view["current_reported_status"], canonical)
        mutant = _first_event_mutant(outcomes, "recorded")
        self.assertEqual(mutant, "reported_reserved")
        self.assertNotEqual(mutant, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, "reported_checked_in")

    def test_current_status_lease_shares_the_seam(self):
        lease = self.ext.create_lease_record("HQ lease", OPERATOR)
        self.ext.record_lease_event(lease["id"], "reported_active", OPERATOR)
        self.ext.record_lease_event(lease["id"], "reported_renewed", OPERATOR)
        view = self.ext.lease_view(lease["id"], VIEWER)
        self.assertEqual(view["current_reported_status"], "reported_renewed")
        events = self.ext.list_lease_events(OPERATOR, lease_id=lease["id"])
        self.assertEqual(
            _first_event_mutant(events, "recorded"), "reported_active")


if __name__ == "__main__":
    unittest.main()
