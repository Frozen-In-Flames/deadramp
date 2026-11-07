"""Final GAPS batch — Energy Management L1 extension surface.

Pins the records forms built for the 10 open entries of the
"Remainder Singleton 57 — Energy Management L1" section of
GAPS.md (see BATCH.md in the group directory): auction execution
runs, alert delivery, market intelligence, the advisory
practice, chart/dashboard definitions, supply contracts,
settlement, and the three labeled reference stubs (price
triggers, identity, data integrations).

The founding discipline is pinned throughout: nothing here
conducts, evaluates, delivers, produces, performs, renders,
executes, or pays — every record carries its ``*_here: False``
label, outcomes and figures are stored exactly as reported, and
the core records underneath are byte-identical after every
extension operation.
"""

import unittest

from energy.errors import NotFoundError, PermissionDenied, ValidationError
from energy.extensions import EnergyExtensions, _check_settlement_cap

from energy_helpers import (ADMIN, AFTER, IN_WINDOW, IN_WINDOW_LATE, MEMBER,
                            VIEWER, make_customer, make_open_auction,
                            make_providers, make_store)

TERM_START = "2024-01-01"
TERM_END = "2024-12-31"
BEFORE_TERM = "2023-06-01T00:00:00+00:00"
IN_TERM = "2024-06-01T00:00:00+00:00"
AFTER_TERM = "2025-06-01T00:00:00+00:00"


def mutant_cap(contract_value_cents, committed_cents, amount_cents):
    """The cap mutant: sums nothing, compares nothing, waves
    every request through as within cap."""
    return "within cap"


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.ext = EnergyExtensions(self.store)
        self.customer = make_customer(self.store)
        self.provider_a, self.provider_b = make_providers(self.store)
        self.auction = make_open_auction(self.store, self.customer)
        self.bid_a = self.store.record_bid(
            ADMIN, self.auction["id"], self.provider_a["id"], 500,
            at=IN_WINDOW)
        self.bid_b = self.store.record_bid(
            ADMIN, self.auction["id"], self.provider_b["id"], 450,
            at=IN_WINDOW_LATE)

    def make_contract(self, quantity=100, price=500):
        return self.ext.create_contract(
            ADMIN, self.customer["id"], self.provider_a["id"],
            "electricity", "ERCOT-North", quantity, price,
            TERM_START, TERM_END, auction_id=self.auction["id"])

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]


class TestAuctionExecution(BatchFixture):
    """Entry 691: reverse auction execution engine — built as
    session/run records with verbatim reported outcomes."""

    def test_run_record_shape_and_labels(self):
        run = self.ext.record_auction_run(
            MEMBER, self.auction["id"], "SESSION-1")
        self.assertEqual(run["id"], "arun-1")
        self.assertEqual(
            set(run.keys()),
            {"id", "auction_id", "session_ref", "conducted_here",
             "created_by", "created_utc"})
        self.assertIs(run["conducted_here"], False)
        self.assertIn("ext_auction_run_create", self.audit_actions())

    def test_report_verbatim_and_core_outcome_untouched(self):
        outcome_before = self.store.auction_outcome(
            ADMIN, self.auction["id"], now=AFTER)
        view_before = self.store.get_auction(
            ADMIN, self.auction["id"], now=AFTER)
        run = self.ext.record_auction_run(
            ADMIN, self.auction["id"], "SESSION-1")
        report = self.ext.record_auction_run_report(
            ADMIN, run["id"], "reported_cleared",
            reported_winner_ref="EXT-BID-999")
        self.assertIs(report["conducted_here"], False)
        self.assertEqual(report["reported_winner_ref"], "EXT-BID-999")
        # The core outcome is the core's derivation from its bid
        # records, before and after: the run's reported winner
        # reference changes nothing.
        self.assertEqual(
            self.store.auction_outcome(ADMIN, self.auction["id"], now=AFTER),
            outcome_before)
        self.assertEqual(
            self.store.get_auction(ADMIN, self.auction["id"], now=AFTER),
            view_before)
        view = self.ext.auction_execution_view(ADMIN, run["id"], now=AFTER)
        self.assertEqual(view["core_outcome"], outcome_before)
        self.assertEqual(view["core_outcome"]["winning_bid_id"],
                         self.bid_b["id"])
        self.assertEqual(
            view["core_outcome"]["lowest_price_cents_per_unit"], 450)
        self.assertEqual(len(view["reports"]), 1)

    def test_duplicate_session_ref_refused_and_no_id_consumed(self):
        self.ext.record_auction_run(ADMIN, self.auction["id"], "SESSION-1")
        with self.assertRaises(ValidationError):
            self.ext.record_auction_run(
                ADMIN, self.auction["id"], "SESSION-1")
        run = self.ext.record_auction_run(
            ADMIN, self.auction["id"], "SESSION-2")
        self.assertEqual(run["id"], "arun-2")

    def test_unknown_auction_and_label(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_auction_run(ADMIN, "auc-99", "SESSION-1")
        run = self.ext.record_auction_run(
            ADMIN, self.auction["id"], "SESSION-1")
        with self.assertRaises(ValidationError):
            self.ext.record_auction_run_report(ADMIN, run["id"], "cleared")
        with self.assertRaises(NotFoundError):
            self.ext.record_auction_run_report(
                ADMIN, "arun-99", "reported_cleared")

    def test_viewer_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_auction_run(
                VIEWER, self.auction["id"], "SESSION-1")
        self.assertIn("ext_auction_run_create:denied", self.audit_actions())
        self.assertEqual(self.ext.list_auction_runs(ADMIN), [])


class TestDeliveryTransport(BatchFixture):
    """Entry 693: alert & notification delivery transport —
    built as reference-transport records with verbatim reports."""

    def setUp(self):
        super().setUp()
        self.subscription = self.store.create_subscription(
            ADMIN, self.customer["id"], "price_change",
            threshold_cents_per_unit=400)
        self.alert = self.store.record_alert(
            ADMIN, self.customer["id"], "price_change", "Price moved",
            subscription_id=self.subscription["id"])

    def test_delivery_shape_and_labels(self):
        delivery = self.ext.record_delivery(
            MEMBER, self.alert["id"], "portal-inbox")
        self.assertEqual(delivery["id"], "dmsg-1")
        self.assertEqual(
            set(delivery.keys()),
            {"id", "alert_id", "customer_id", "channel_ref",
             "reference_transport", "delivered_here", "created_by",
             "created_utc"})
        self.assertEqual(delivery["customer_id"], self.customer["id"])
        self.assertIs(delivery["reference_transport"], True)
        self.assertIs(delivery["delivered_here"], False)

    def test_current_state_derived_latest_report_wins(self):
        delivery = self.ext.record_delivery(
            ADMIN, self.alert["id"], "portal-inbox")
        stored = self.ext.get_delivery(ADMIN, delivery["id"])
        self.assertNotIn("current_state", stored)
        view = self.ext.delivery_view(ADMIN, delivery["id"])
        self.assertEqual(view["current_state"], "recorded")
        self.assertEqual(view["report_count"], 0)
        self.ext.record_delivery_report(
            ADMIN, delivery["id"], "reported_delivered")
        view = self.ext.delivery_view(ADMIN, delivery["id"])
        self.assertEqual(view["current_state"], "reported_delivered")
        self.ext.record_delivery_report(
            ADMIN, delivery["id"], "reported_bounced")
        view = self.ext.delivery_view(ADMIN, delivery["id"])
        self.assertEqual(view["current_state"], "reported_bounced")
        self.assertEqual(view["report_count"], 2)
        self.assertNotIn("current_state",
                         self.ext.get_delivery(ADMIN, delivery["id"]))

    def test_unknown_alert_label_and_core_alerts_unchanged(self):
        before = self.store.list_alerts(ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_delivery(ADMIN, "alrt-99", "portal-inbox")
        delivery = self.ext.record_delivery(
            ADMIN, self.alert["id"], "portal-inbox")
        with self.assertRaises(ValidationError):
            self.ext.record_delivery_report(ADMIN, delivery["id"], "sent")
        self.ext.record_delivery_report(
            ADMIN, delivery["id"], "reported_delivered")
        self.assertEqual(self.store.list_alerts(ADMIN), before)


class TestMarketIntelligence(BatchFixture):
    """Entry 694: market intelligence engine — built as analysis
    records holding conclusions exactly as reported. Market-
    update notifications stay booked once, under the core alert
    records; this surface creates none."""

    FIGURES = [{"label": "ERCOT North hub, $/MWh", "value_text": "42.50"},
               {"label": "forward curve slope", "value_text": "-3"}]

    def test_analysis_shape_and_figures_verbatim(self):
        analysis = self.ext.record_analysis(
            MEMBER, self.customer["id"], "TOPIC-ERCOT-Q3",
            "desk-analyst-7", "rising", self.FIGURES)
        self.assertEqual(analysis["id"], "mint-1")
        self.assertEqual(
            set(analysis.keys()),
            {"id", "customer_id", "engagement_id", "topic_ref",
             "analyst_label", "outlook_label", "figures",
             "produced_here", "created_by", "created_utc"})
        self.assertIs(analysis["produced_here"], False)
        self.assertEqual(analysis["figures"], self.FIGURES)
        self.assertIsNone(analysis["engagement_id"])

    def test_figures_must_be_reported_text(self):
        for bad in (42.5, 42, True, "soon", ""):
            figures = [{"label": "x", "value_text": bad}]
            with self.assertRaises(ValidationError):
                self.ext.record_analysis(
                    ADMIN, self.customer["id"], "T-1", "a", "rising",
                    figures)
        with self.assertRaises(ValidationError):
            self.ext.record_analysis(
                ADMIN, self.customer["id"], "T-1", "a", "rising",
                [{"label": "x", "value_text": "1.0", "extra": "y"}])
        with self.assertRaises(ValidationError):
            self.ext.record_analysis(
                ADMIN, self.customer["id"], "T-1", "a", "rising", [])
        self.assertEqual(self.ext.list_analyses(ADMIN), [])

    def test_engagement_binding_checked(self):
        budgeting = self.store.create_engagement(
            ADMIN, self.customer["id"], "budgeting", "Budget review")
        with self.assertRaises(ValidationError):
            self.ext.record_analysis(
                ADMIN, self.customer["id"], "T-1", "a", "rising",
                self.FIGURES, engagement_id=budgeting["id"])
        intel = self.store.create_engagement(
            ADMIN, self.customer["id"], "market_intelligence",
            "Market watch")
        analysis = self.ext.record_analysis(
            ADMIN, self.customer["id"], "T-1", "a", "falling",
            self.FIGURES, engagement_id=intel["id"])
        self.assertEqual(analysis["engagement_id"], intel["id"])

    def test_no_notification_created_and_summary_counts(self):
        self.assertEqual(self.store.list_alerts(ADMIN), [])
        self.ext.record_analysis(
            ADMIN, self.customer["id"], "T-1", "a", "rising", self.FIGURES)
        self.ext.record_analysis(
            ADMIN, self.customer["id"], "T-2", "a", "falling", self.FIGURES)
        self.assertEqual(self.store.list_alerts(ADMIN), [])
        self.assertEqual(
            self.ext.market_intelligence_summary(ADMIN),
            {"analyses": 2,
             "analyses_by_outlook": {"rising": 1, "falling": 1,
                                     "stable": 0}})


class TestAdvisoryPractice(BatchFixture):
    """Entry 695: advisory practice itself — built as session
    records over core engagements with verbatim reported
    recommendations. The fork's people perform the practice."""

    def setUp(self):
        super().setUp()
        self.engagement = self.store.create_engagement(
            ADMIN, self.customer["id"], "budgeting",
            "Quarterly budget review")

    def test_session_and_recommendation_shapes(self):
        session = self.ext.record_advisory_session(
            MEMBER, self.engagement["id"], "CALL-2024-06-12")
        self.assertEqual(session["id"], "ases-1")
        self.assertIs(session["performed_here"], False)
        recommendation = self.ext.record_recommendation(
            MEMBER, session["id"], "lock 60% of Q3 volume at or under cap")
        self.assertEqual(recommendation["id"], "arec-1")
        self.assertEqual(recommendation["recommendation_label"],
                         "lock 60% of Q3 volume at or under cap")
        self.assertIs(recommendation["performed_here"], False)

    def test_core_engagement_byte_identical(self):
        before = self.store.get_engagement(ADMIN, self.engagement["id"])
        session = self.ext.record_advisory_session(
            ADMIN, self.engagement["id"], "CALL-1")
        self.ext.record_recommendation(ADMIN, session["id"], "hold")
        after = self.store.get_engagement(ADMIN, self.engagement["id"])
        self.assertEqual(after, before)
        self.assertEqual(after["status"], "open")

    def test_unknown_engagement_and_duplicate_session_ref(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_advisory_session(ADMIN, "eng-99", "CALL-1")
        self.ext.record_advisory_session(
            ADMIN, self.engagement["id"], "CALL-1")
        with self.assertRaises(ValidationError):
            self.ext.record_advisory_session(
                ADMIN, self.engagement["id"], "CALL-1")
        with self.assertRaises(NotFoundError):
            self.ext.record_recommendation(ADMIN, "ases-99", "hold")


class TestChartsDashboards(BatchFixture):
    """Entry 696: price chart rendering & dashboards — built as
    chart definition records plus dashboard configurations.
    Nothing is drawn."""

    def setUp(self):
        super().setUp()
        self.store.record_observation(
            ADMIN, "ERCOT-North", "electricity", 500,
            observed_at="2024-06-01T00:00:00+00:00")
        self.store.record_observation(
            ADMIN, "ERCOT-North", "electricity", 475,
            observed_at="2024-06-03T00:00:00+00:00")

    def test_chart_requires_a_recorded_series(self):
        with self.assertRaises(ValidationError):
            self.ext.create_chart_definition(
                ADMIN, "NOWHERE", "natural_gas", "line")
        chart = self.ext.create_chart_definition(
            MEMBER, "ERCOT-North", "electricity", "line")
        self.assertEqual(chart["id"], "chrt-1")
        self.assertIs(chart["rendered_here"], False)

    def test_chart_view_derives_series_facts(self):
        chart = self.ext.create_chart_definition(
            ADMIN, "ERCOT-North", "electricity", "bar")
        stored = self.ext.get_chart(ADMIN, chart["id"])
        self.assertNotIn("observation_count", stored)
        self.assertNotIn("latest_price_cents_per_unit", stored)
        view = self.ext.chart_view(ADMIN, chart["id"])
        self.assertEqual(view["observation_count"], 2)
        self.assertEqual(view["latest_price_cents_per_unit"], 475)
        self.assertEqual(view["latest_observed_at"],
                         "2024-06-03T00:00:00+00:00")
        with self.assertRaises(ValidationError):
            self.ext.create_chart_definition(
                ADMIN, "ERCOT-North", "electricity", "pie")

    def test_dashboard_config_validates_references(self):
        chart = self.ext.create_chart_definition(
            ADMIN, "ERCOT-North", "electricity", "area")
        dashboard = self.ext.create_dashboard_config(
            ADMIN, "Procurement board", [chart["id"]])
        self.assertEqual(dashboard["id"], "dash-1")
        self.assertEqual(dashboard["chart_ids"], [chart["id"]])
        self.assertIs(dashboard["rendered_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.create_dashboard_config(ADMIN, "Bad", ["chrt-99"])
        with self.assertRaises(ValidationError):
            self.ext.create_dashboard_config(
                ADMIN, "Dup", [chart["id"], chart["id"]])


class TestSupplyContracts(BatchFixture):
    """Entry 697: supply contract lifecycle & execution — built
    as contract records whose value and lifecycle state derive
    at read. Execution happens on the parties' own systems."""

    def test_contract_shape_no_value_no_state_stored(self):
        contract = self.make_contract()
        self.assertEqual(contract["id"], "ctr-1")
        self.assertEqual(
            set(contract.keys()),
            {"id", "customer_id", "provider_id", "auction_id",
             "commodity", "region", "quantity_units",
             "price_cents_per_unit", "term_start", "term_end",
             "executed_here", "created_by", "created_utc"})
        self.assertIs(contract["executed_here"], False)
        stored = self.ext.get_contract(ADMIN, contract["id"])
        self.assertNotIn("value_cents", stored)
        self.assertNotIn("lifecycle_state", stored)

    def test_view_derives_value_and_window_state(self):
        contract = self.make_contract()
        self.assertEqual(
            self.ext.contract_view(ADMIN, contract["id"], now=BEFORE_TERM)
            ["value_cents"], 50000)
        self.assertEqual(
            self.ext.contract_view(ADMIN, contract["id"], now=BEFORE_TERM)
            ["lifecycle_state"], "pending")
        self.assertEqual(
            self.ext.contract_view(ADMIN, contract["id"], now=IN_TERM)
            ["lifecycle_state"], "active")
        self.assertEqual(
            self.ext.contract_view(ADMIN, contract["id"], now=AFTER_TERM)
            ["lifecycle_state"], "expired")

    def test_recorded_termination_overrides_window(self):
        contract = self.make_contract()
        event = self.ext.record_contract_event(
            ADMIN, contract["id"], "recorded_terminated")
        self.assertEqual(event["id"], "cevt-1")
        self.assertIs(event["executed_here"], False)
        view = self.ext.contract_view(ADMIN, contract["id"], now=IN_TERM)
        self.assertEqual(view["lifecycle_state"], "terminated")
        self.assertEqual(len(view["events"]), 1)
        with self.assertRaises(ValidationError):
            self.ext.record_contract_event(
                ADMIN, contract["id"], "terminated")

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_contract(
                ADMIN, self.customer["id"], self.provider_a["id"],
                "electricity", "ERCOT-North", 100, 10.5,
                TERM_START, TERM_END)
        with self.assertRaises(ValidationError):
            self.ext.create_contract(
                ADMIN, self.customer["id"], self.provider_a["id"],
                "electricity", "ERCOT-North", 100, True,
                TERM_START, TERM_END)
        with self.assertRaises(ValidationError):
            self.ext.create_contract(
                ADMIN, self.customer["id"], self.provider_a["id"],
                "electricity", "ERCOT-North", 100, 500,
                TERM_END, TERM_START)
        with self.assertRaises(NotFoundError):
            self.ext.create_contract(
                ADMIN, self.customer["id"], "prov-99",
                "electricity", "ERCOT-North", 100, 500,
                TERM_START, TERM_END)
        self.assertEqual(self.ext.list_contracts(ADMIN), [])


class TestSettlements(BatchFixture):
    """Entry 698: payment / settlement execution — built as
    settlement-request records plus verbatim outcome reports,
    capped by the linked contract's recorded amount. No money
    moves here."""

    def setUp(self):
        super().setUp()
        self.contract = self.make_contract()  # value 50,000 cents

    def test_request_shape_and_labels(self):
        settlement = self.ext.request_settlement(
            MEMBER, self.contract["id"], 30000)
        self.assertEqual(settlement["id"], "stl-1")
        self.assertEqual(
            set(settlement.keys()),
            {"id", "contract_id", "amount_cents", "paid_here",
             "created_by", "created_utc"})
        self.assertIs(settlement["paid_here"], False)
        report = self.ext.record_settlement_report(
            MEMBER, settlement["id"], "reported_paid")
        self.assertEqual(report["id"], "srpt-1")
        self.assertIs(report["paid_here"], False)

    def test_requests_capped_at_contract_value(self):
        self.ext.request_settlement(ADMIN, self.contract["id"], 30000)
        with self.assertRaises(ValidationError):
            self.ext.request_settlement(ADMIN, self.contract["id"], 20001)
        second = self.ext.request_settlement(
            ADMIN, self.contract["id"], 20000)
        self.assertEqual(second["id"], "stl-2")
        self.assertEqual(
            self.ext.settlement_summary(ADMIN, self.contract["id"]),
            {"contract_id": self.contract["id"], "value_cents": 50000,
             "committed_cents": 50000, "remaining_cents": 0,
             "request_count": 2, "report_count": 0})

    def test_non_integer_amounts_refused(self):
        for bad in (10.5, 100.0, True, "100", 0, -5):
            with self.assertRaises(ValidationError):
                self.ext.request_settlement(
                    ADMIN, self.contract["id"], bad)
        self.assertEqual(self.ext.list_settlements(ADMIN), [])

    def test_paid_report_keeps_the_commitment(self):
        settlement = self.ext.request_settlement(
            ADMIN, self.contract["id"], 30000)
        self.ext.record_settlement_report(
            ADMIN, settlement["id"], "reported_paid")
        with self.assertRaises(ValidationError):
            self.ext.request_settlement(ADMIN, self.contract["id"], 20001)
        self.assertEqual(
            self.ext.settlement_summary(ADMIN, self.contract["id"])
            ["committed_cents"], 30000)

    def test_failed_report_releases_the_amount(self):
        settlement = self.ext.request_settlement(
            ADMIN, self.contract["id"], 30000)
        self.ext.record_settlement_report(
            ADMIN, settlement["id"], "reported_failed")
        released = self.ext.request_settlement(
            ADMIN, self.contract["id"], 50000)
        self.assertEqual(released["id"], "stl-2")
        self.assertEqual(
            self.ext.settlement_summary(ADMIN, self.contract["id"])
            ["committed_cents"], 50000)

    def test_unknown_records(self):
        with self.assertRaises(NotFoundError):
            self.ext.request_settlement(ADMIN, "ctr-99", 100)
        settlement = self.ext.request_settlement(
            ADMIN, self.contract["id"], 100)
        with self.assertRaises(NotFoundError):
            self.ext.record_settlement_report(
                ADMIN, "stl-99", "reported_paid")
        with self.assertRaises(ValidationError):
            self.ext.record_settlement_report(
                ADMIN, settlement["id"], "paid")

    def test_core_and_contract_records_untouched(self):
        contract_before = self.ext.get_contract(ADMIN, self.contract["id"])
        outcome_before = self.store.auction_outcome(
            ADMIN, self.auction["id"], now=AFTER)
        settlement = self.ext.request_settlement(
            ADMIN, self.contract["id"], 30000)
        self.ext.record_settlement_report(
            ADMIN, settlement["id"], "reported_paid")
        self.assertEqual(
            self.ext.get_contract(ADMIN, self.contract["id"]),
            contract_before)
        self.assertEqual(
            self.store.auction_outcome(ADMIN, self.auction["id"], now=AFTER),
            outcome_before)


class TestSettlementCapNegativeControl(BatchFixture):
    """Fresh negative control for the batch: the settlement cap
    seam ``_check_settlement_cap`` in ``energy/extensions.py``.

    Traced claim: **the settlement cap is the SI-10 integrity
    boundary of settlement on a supply contract** — outstanding
    requested amounts for a contract never exceed the contract's
    recorded amount (quantity x price per unit, derived at
    read). Each canonical case asserts (1) the real
    implementation raises ValidationError and stores nothing /
    consumes no id, (2) the mutant gate would NOT raise, and
    (3) treating the mutant's outcome as expected fails.
    """

    def setUp(self):
        super().setUp()
        self.contract = self.make_contract()  # value 50,000 cents

    def _assert_mutant_rejected(self, mutant_outcome):
        self.assertNotEqual(mutant_outcome, "rejected")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, "rejected")

    def test_single_request_one_cent_over_value(self):
        with self.assertRaises(ValidationError):
            _check_settlement_cap(50000, 0, 50001)
        with self.assertRaises(ValidationError):
            self.ext.request_settlement(ADMIN, self.contract["id"], 50001)
        self.assertEqual(self.ext.list_settlements(ADMIN), [])
        mutant_outcome = mutant_cap(50000, 0, 50001)
        self.assertEqual(mutant_outcome, "within cap")
        self._assert_mutant_rejected(mutant_outcome)
        good = self.ext.request_settlement(ADMIN, self.contract["id"], 5000)
        self.assertEqual(good["id"], "stl-1")

    def test_two_requests_each_within_value_whose_sum_exceeds_it(self):
        first = self.ext.request_settlement(
            ADMIN, self.contract["id"], 30000)
        self.assertEqual(first["id"], "stl-1")
        with self.assertRaises(ValidationError):
            _check_settlement_cap(50000, 30000, 20001)
        with self.assertRaises(ValidationError):
            self.ext.request_settlement(ADMIN, self.contract["id"], 20001)
        self.assertEqual(len(self.ext.list_settlements(ADMIN)), 1)
        mutant_outcome = mutant_cap(50000, 30000, 20001)
        self.assertEqual(mutant_outcome, "within cap")
        self._assert_mutant_rejected(mutant_outcome)
        second = self.ext.request_settlement(
            ADMIN, self.contract["id"], 20000)
        self.assertEqual(second["id"], "stl-2")


class TestPriceTriggers(BatchFixture):
    """Entry 692 (stub): price-trigger evaluation engine —
    shipped as a labeled reference implementation: definitions
    as data plus verbatim reported evaluations. Alert records
    stay Core."""

    def setUp(self):
        super().setUp()
        self.subscription = self.store.create_subscription(
            ADMIN, self.customer["id"], "price_change",
            threshold_cents_per_unit=400)

    def test_definition_shape_and_labels(self):
        definition = self.ext.record_trigger_definition(
            MEMBER, self.subscription["id"], "crosses_below")
        self.assertEqual(definition["id"], "trgd-1")
        self.assertEqual(
            set(definition.keys()),
            {"id", "subscription_id", "condition_label",
             "reference_stub", "evaluated_here", "state",
             "created_by", "created_utc"})
        self.assertIs(definition["reference_stub"], True)
        self.assertIs(definition["evaluated_here"], False)
        self.assertEqual(definition["state"], "recorded_reference_only")

    def test_reported_firing_creates_no_alert(self):
        definition = self.ext.record_trigger_definition(
            ADMIN, self.subscription["id"], "crosses_below")
        self.assertEqual(self.store.list_alerts(ADMIN), [])
        evaluation = self.ext.record_trigger_evaluation(
            ADMIN, definition["id"], "reported_fired")
        self.assertEqual(evaluation["id"], "trge-1")
        self.assertIs(evaluation["reference_stub"], True)
        self.assertIs(evaluation["evaluated_here"], False)
        self.assertEqual(self.store.list_alerts(ADMIN), [])

    def test_unknown_subscription_condition_and_definition(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_trigger_definition(
                ADMIN, "sub-99", "crosses_below")
        with self.assertRaises(ValidationError):
            self.ext.record_trigger_definition(
                ADMIN, self.subscription["id"], "crosses")
        definition = self.ext.record_trigger_definition(
            ADMIN, self.subscription["id"], "crosses_above")
        with self.assertRaises(NotFoundError):
            self.ext.record_trigger_evaluation(
                ADMIN, "trgd-99", "reported_fired")
        with self.assertRaises(ValidationError):
            self.ext.record_trigger_evaluation(
                ADMIN, definition["id"], "fired")


class TestIdentityReference(BatchFixture):
    """Entry 699 (stub): identity provider — shipped as a
    labeled reference implementation per PLATFORM-LAYER.md
    decision 1. IA-2 stays with the embedding organization."""

    def test_reference_shape_and_labels(self):
        reference = self.ext.record_identity_reference(
            ADMIN, "IDP-EXTERNAL-1", "Organization IdP (records label)")
        self.assertEqual(reference["id"], "idr-1")
        self.assertEqual(
            set(reference.keys()),
            {"id", "provider_ref", "provider_label", "reference_stub",
             "identity_provider", "state", "created_by", "created_utc"})
        self.assertIs(reference["reference_stub"], True)
        self.assertIs(reference["identity_provider"], False)
        self.assertEqual(reference["state"], "recorded_reference_only")

    def test_duplicate_provider_ref_refused(self):
        self.ext.record_identity_reference(ADMIN, "IDP-1", "One")
        with self.assertRaises(ValidationError):
            self.ext.record_identity_reference(ADMIN, "IDP-1", "Again")
        second = self.ext.record_identity_reference(ADMIN, "IDP-2", "Two")
        self.assertEqual(second["id"], "idr-2")


class TestDataIntegrations(BatchFixture):
    """Entry 700 (stub): energy data integrations — shipped as
    a labeled reference implementation: feed records plus sync
    receipts holding counts exactly as reported. No feed data
    is held in any shape."""

    def test_feed_and_receipt_shapes(self):
        feed = self.ext.record_feed(MEMBER, "FEED-METER-7", "meter")
        self.assertEqual(feed["id"], "feed-1")
        self.assertEqual(
            set(feed.keys()),
            {"id", "feed_ref", "feed_kind", "reference_stub",
             "reference_transport", "state", "created_by",
             "created_utc"})
        self.assertIs(feed["reference_stub"], True)
        self.assertIs(feed["reference_transport"], True)
        receipt = self.ext.record_feed_receipt(ADMIN, feed["id"], 1200)
        self.assertEqual(receipt["id"], "frcp-1")
        self.assertEqual(
            set(receipt.keys()),
            {"id", "feed_id", "records_reported", "reference_stub",
             "reference_transport", "data_held_here", "state",
             "created_by", "created_utc"})
        self.assertEqual(receipt["records_reported"], 1200)
        self.assertIs(receipt["data_held_here"], False)

    def test_counts_must_be_reported_integers(self):
        feed = self.ext.record_feed(ADMIN, "FEED-PRICE-1", "market_price")
        for bad in (12.5, True, "1200", -1):
            with self.assertRaises(ValidationError):
                self.ext.record_feed_receipt(ADMIN, feed["id"], bad)
        with self.assertRaises(NotFoundError):
            self.ext.record_feed_receipt(ADMIN, "feed-99", 10)
        with self.assertRaises(ValidationError):
            self.ext.record_feed(ADMIN, "FEED-PRICE-1", "supplier")
        with self.assertRaises(ValidationError):
            self.ext.record_feed(ADMIN, "FEED-X", "weather")


FORBIDDEN_KEY_PARTS = ("score", "rating", "rank", "leaderboard",
                       "password", "secret", "credential", "payload",
                       "meter_reading", "account_number", "ssn")


def _scan_keys(value, path="root"):
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                if part in lowered:
                    raise AssertionError(
                        "forbidden key %r at %s" % (key, path))
            _scan_keys(item, "%s.%s" % (path, key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_keys(item, "%s[%d]" % (path, index))


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins: no shape anywhere on the extension
    surface can hold a score, a credential, or feed data; the
    method signatures admit no unlisted field; the summary is
    counts only."""

    def _build_one_of_everything(self):
        run = self.ext.record_auction_run(
            ADMIN, self.auction["id"], "SESSION-1")
        self.ext.record_auction_run_report(
            ADMIN, run["id"], "reported_cleared",
            reported_winner_ref="EXT-BID-2")
        subscription = self.store.create_subscription(
            ADMIN, self.customer["id"], "price_change",
            threshold_cents_per_unit=400)
        alert = self.store.record_alert(
            ADMIN, self.customer["id"], "price_change", "Price moved",
            subscription_id=subscription["id"])
        delivery = self.ext.record_delivery(ADMIN, alert["id"], "portal")
        self.ext.record_delivery_report(
            ADMIN, delivery["id"], "reported_delivered")
        self.ext.record_analysis(
            ADMIN, self.customer["id"], "T-1", "desk", "stable",
            [{"label": "hub", "value_text": "41.75"}])
        engagement = self.store.create_engagement(
            ADMIN, self.customer["id"], "risk_management", "Hedge review")
        session = self.ext.record_advisory_session(
            ADMIN, engagement["id"], "CALL-1")
        self.ext.record_recommendation(ADMIN, session["id"], "hedge 40%")
        self.store.record_observation(
            ADMIN, "ERCOT-North", "electricity", 480,
            observed_at="2024-06-02T00:00:00+00:00")
        chart = self.ext.create_chart_definition(
            ADMIN, "ERCOT-North", "electricity", "line")
        self.ext.create_dashboard_config(ADMIN, "Board", [chart["id"]])
        contract = self.make_contract()
        self.ext.record_contract_event(
            ADMIN, contract["id"], "recorded_amended")
        settlement = self.ext.request_settlement(
            ADMIN, contract["id"], 10000)
        self.ext.record_settlement_report(
            ADMIN, settlement["id"], "reported_partial")
        definition = self.ext.record_trigger_definition(
            ADMIN, subscription["id"], "crosses_below")
        self.ext.record_trigger_evaluation(
            ADMIN, definition["id"], "reported_not_fired")
        self.ext.record_identity_reference(ADMIN, "IDP-1", "Org IdP")
        feed = self.ext.record_feed(ADMIN, "FEED-1", "supplier")
        self.ext.record_feed_receipt(ADMIN, feed["id"], 33)
        return run, delivery, chart, contract

    def test_no_forbidden_key_anywhere(self):
        run, delivery, chart, contract = self._build_one_of_everything()
        surfaces = [
            self.ext.list_auction_runs(ADMIN),
            self.ext.list_auction_run_reports(ADMIN),
            self.ext.auction_execution_view(ADMIN, run["id"], now=AFTER),
            self.ext.list_deliveries(ADMIN),
            self.ext.list_delivery_reports(ADMIN),
            self.ext.delivery_view(ADMIN, delivery["id"]),
            self.ext.list_analyses(ADMIN),
            self.ext.market_intelligence_summary(ADMIN),
            self.ext.list_advisory_sessions(ADMIN),
            self.ext.list_recommendations(ADMIN),
            self.ext.list_charts(ADMIN),
            self.ext.list_dashboards(ADMIN),
            self.ext.chart_view(ADMIN, chart["id"]),
            self.ext.list_contracts(ADMIN),
            self.ext.list_contract_events(ADMIN),
            self.ext.contract_view(ADMIN, contract["id"], now=IN_TERM),
            self.ext.list_settlements(ADMIN),
            self.ext.list_settlement_reports(ADMIN),
            self.ext.settlement_summary(ADMIN, contract["id"]),
            self.ext.list_trigger_definitions(ADMIN),
            self.ext.list_trigger_evaluations(ADMIN),
            self.ext.list_identity_references(ADMIN),
            self.ext.list_feeds(ADMIN),
            self.ext.list_feed_receipts(ADMIN),
            self.ext.extensions_summary(ADMIN),
        ]
        for surface in surfaces:
            _scan_keys(surface)

    def test_unexpected_keyword_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_identity_reference(
                ADMIN, "IDP-9", "x", payload="smuggled")
        with self.assertRaises(TypeError):
            self.ext.record_feed(ADMIN, "FEED-9", "meter", data=[])
        with self.assertRaises(TypeError):
            self.ext.record_analysis(
                ADMIN, self.customer["id"], "T-1", "a", "rising",
                [{"label": "x", "value_text": "1"}], analysis_text="buy")
        self.assertEqual(self.ext.list_identity_references(ADMIN), [])
        self.assertEqual(self.ext.list_feeds(ADMIN), [])

    def test_extensions_summary_counts(self):
        self._build_one_of_everything()
        self.assertEqual(
            self.ext.extensions_summary(ADMIN),
            {"auction_runs": 1, "auction_run_reports": 1,
             "deliveries": 1, "delivery_reports": 1, "analyses": 1,
             "advisory_sessions": 1, "recommendations": 1, "charts": 1,
             "dashboards": 1, "contracts": 1, "contract_events": 1,
             "settlements": 1, "settlement_reports": 1,
             "trigger_definitions": 1, "trigger_evaluations": 1,
             "identity_references": 1, "feeds": 1, "feed_receipts": 1})


if __name__ == "__main__":
    unittest.main()
