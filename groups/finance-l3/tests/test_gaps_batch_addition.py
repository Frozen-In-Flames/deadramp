"""Final GAPS batch tests (second unit) — Group 42, Finance
L3-adjacent, remainder-addition section.

Pins the extension surface in ``src/finance/extensions_addition.py``
(``FinanceExtensionsAddition``, wrapping the core ``FinanceStore``):
one test class per open GAPS.md entry of the "Remainder Addition —
Finance L3-adjacent (+1 fork)" section (see ``../BATCH-ADDITION.md``
for the per-entry disposition), plus cross-cutting pins —
``exta_``-prefixed actions and ``:denied`` denials on the core
hash-chained audit log, the separated ``auditor`` role denied every
extension operation while its core audit duty works, stub labels on
every reference record (and their absence on built records), the
integer-cents boundary, currency as a label (consolidation sums per
currency, never across), forecasts recorded verbatim and never
computed, derived-never-stored values, the no-bank-detail /
no-identifier / no-score shape pins, the standing trading &
investment execution absence pin, and this unit's fresh negative
control: the per-currency totals seam ``_totals_by_currency``.

Fixtures: ``make_store()`` (a program owned by MEMBER=bob with
VIEWER=carol added as a member) from ``finance_helpers``;
ADMIN=alice/admin (platform admin, not a program member),
AUDITOR=dana/auditor (audit_read only), OUTSIDER=dave/member
(no fixture program).
"""

import unittest

from finance_helpers import (
    ADMIN,
    AUDITOR,
    MEMBER,
    OUTSIDER,
    PERIOD,
    VIEWER,
    make_employee,
    make_store,
)

from finance.errors import NotFoundError, PermissionDenied, ValidationError
from finance.extensions_addition import (
    FinanceExtensionsAddition,
    _totals_by_currency,
)


def mutant_totals_single_bucket(amounts):
    """The defect under control: every amount is summed under the
    first currency label seen — a cross-currency sum, the one
    figure this surface must never produce."""
    totals = {}
    first = None
    for label, amount in amounts:
        if first is None:
            first = label
        totals[first] = totals.get(first, 0) + amount
    return totals


def all_keys(obj):
    """Every dict key in a record, recursively."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            keys |= all_keys(item)
    return keys


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.ext = FinanceExtensionsAddition(self.store)

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def make_entity(self, ref="entity-us", currency="USD", **kwargs):
        return self.ext.register_cpm_entity(
            self.program_id, ref, currency, MEMBER, **kwargs)

    def make_plan(self, entity_id=None, ref="plan-2026", kind="budgeting",
                  period="2026"):
        if entity_id is None:
            entity_id = self.make_entity()["id"]
        return self.ext.create_cpm_plan(
            self.program_id, entity_id, ref, kind, period, MEMBER)


class TestCpmBuilt(AdditionFixture):
    """Entry (idx 667): Corporate performance management (CPM)
    engine — built in records form: entity structure, plan
    definitions and recorded line values in integer cents,
    consolidation derived at read per currency label, forecast
    figures recorded verbatim and never computed."""

    def test_entity_shape_and_labels(self):
        entity = self.make_entity()
        self.assertEqual(entity["id"], "cent-1")
        self.assertEqual(
            set(entity),
            {
                "id", "program_id", "entity_ref", "currency_label",
                "parent_entity_id", "name_label", "modeled_here",
                "state", "created_by", "created_utc",
            },
        )
        self.assertIs(entity["modeled_here"], False)
        self.assertEqual(entity["state"], "recorded_structure_only")
        self.assertNotIn("reference_stub", entity)

    def test_duplicate_entity_ref_rejected_and_no_id_consumed(self):
        self.make_entity()
        with self.assertRaises(ValidationError):
            self.ext.register_cpm_entity(
                self.program_id, "entity-us", "EUR", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_cpm_entity(
                self.program_id, "  ", "USD", MEMBER)
        second = self.make_entity(ref="entity-eu", currency="EUR")
        self.assertEqual(second["id"], "cent-2")

    def test_parent_binding_and_unknown_parent_rejected(self):
        parent = self.make_entity()
        child = self.make_entity(
            ref="entity-us-west", parent_entity_id=parent["id"])
        self.assertEqual(child["parent_entity_id"], parent["id"])
        with self.assertRaises(NotFoundError):
            self.make_entity(ref="entity-x", parent_entity_id="cent-99")

    def test_plan_shape_currency_inherited_and_duplicate_ref(self):
        entity = self.make_entity(currency="EUR")
        plan = self.make_plan(entity_id=entity["id"])
        self.assertEqual(plan["id"], "cpln-1")
        self.assertEqual(plan["currency_label"], "EUR")
        self.assertEqual(plan["state"], "recorded_definition_only")
        self.assertIs(plan["modeled_here"], False)
        with self.assertRaises(ValidationError):
            self.make_plan(entity_id=entity["id"])
        with self.assertRaises(ValidationError):
            self.ext.create_cpm_plan(
                self.program_id, entity["id"], "plan-x", "forecasting",
                "2026", MEMBER)

    def test_plan_line_cents_boundary_and_signed_lines(self):
        plan = self.make_plan()
        line = self.ext.record_cpm_plan_line(
            self.program_id, plan["id"], "revenue", 500000, MEMBER)
        self.assertEqual(line["id"], "clin-1")
        elim = self.ext.record_cpm_plan_line(
            self.program_id, plan["id"], "elimination", -20000, MEMBER)
        self.assertEqual(elim["amount_cents"], -20000)
        for bad in (True, 1.5, 100.0, "100"):
            with self.assertRaises(ValidationError):
                self.ext.record_cpm_plan_line(
                    self.program_id, plan["id"], "bad", bad, MEMBER)
        third = self.ext.record_cpm_plan_line(
            self.program_id, plan["id"], "opex", 1000, MEMBER)
        self.assertEqual(third["id"], "clin-3")

    def test_plan_view_derives_total_and_plan_record_unchanged(self):
        plan = self.make_plan()
        self.ext.record_cpm_plan_line(
            self.program_id, plan["id"], "revenue", 500000, MEMBER)
        self.ext.record_cpm_plan_line(
            self.program_id, plan["id"], "elimination", -20000, MEMBER)
        view = self.ext.cpm_plan_view(self.program_id, plan["id"], MEMBER)
        self.assertEqual(view["line_count"], 2)
        self.assertEqual(view["plan_total_cents"], 480000)
        self.assertIsInstance(view["plan_total_cents"], int)
        stored = self.ext.list_cpm_plans(self.program_id, MEMBER)[0]
        self.assertNotIn("plan_total_cents", stored)
        self.assertNotIn("line_count", stored)
        self.assertEqual(stored, plan)

    def test_forecast_recorded_verbatim_never_computed(self):
        entity = self.make_entity()
        forecast = self.ext.record_cpm_forecast(
            self.program_id, entity["id"], "2026", 750000, MEMBER,
            basis_label="planning-system-export")
        self.assertEqual(forecast["id"], "cfct-1")
        self.assertEqual(forecast["reported_amount_cents"], 750000)
        self.assertEqual(forecast["currency_label"], "USD")
        self.assertIs(forecast["computed_here"], False)
        self.assertEqual(forecast["state"], "recorded_as_reported")
        with self.assertRaises(ValidationError):
            self.ext.record_cpm_forecast(
                self.program_id, entity["id"], "2026", 1.5, MEMBER)
        second = self.ext.record_cpm_forecast(
            self.program_id, entity["id"], "2027", 800000, MEMBER)
        self.assertEqual(second["id"], "cfct-2")

    def test_consolidation_view_per_currency_never_mixed(self):
        usd = self.make_entity(ref="entity-us", currency="USD")
        eur = self.make_entity(ref="entity-eu", currency="EUR")
        plan_usd = self.make_plan(entity_id=usd["id"], ref="plan-us")
        plan_eur = self.make_plan(entity_id=eur["id"], ref="plan-eu")
        self.ext.record_cpm_plan_line(
            self.program_id, plan_usd["id"], "revenue", 100000, MEMBER)
        self.ext.record_cpm_plan_line(
            self.program_id, plan_usd["id"], "elimination", -5000, MEMBER)
        self.ext.record_cpm_plan_line(
            self.program_id, plan_eur["id"], "revenue", 200000, MEMBER)
        self.ext.record_cpm_forecast(
            self.program_id, usd["id"], "2026", 90000, MEMBER)
        self.ext.record_cpm_forecast(
            self.program_id, eur["id"], "2026", 210000, MEMBER)
        other_period = self.ext.create_cpm_plan(
            self.program_id, usd["id"], "plan-2027", "planning", "2027",
            MEMBER)
        self.ext.record_cpm_plan_line(
            self.program_id, other_period["id"], "revenue", 999999,
            MEMBER)
        view = self.ext.cpm_consolidation_view(
            self.program_id, "2026", MEMBER)
        self.assertEqual(view["plan_count"], 2)
        self.assertEqual(view["forecast_count"], 2)
        self.assertEqual(
            view["plan_totals_by_currency"],
            {"USD": 95000, "EUR": 200000})
        self.assertEqual(
            view["forecast_totals_by_currency"],
            {"USD": 90000, "EUR": 210000})
        self.assertIs(view["computed_here"], False)


class TestConnectorsReference(AdditionFixture):
    """Entry (idx 668): Data integration & connector surface —
    labeled reference implementation: connector definitions and
    sync receipts, every record stub-labeled, nothing imported."""

    def make_connector(self, ref="erp-main", kind="erp_system"):
        return self.ext.register_connector(
            self.program_id, ref, kind, MEMBER)

    def test_connector_shape_and_stub_labels(self):
        connector = self.make_connector()
        self.assertEqual(connector["id"], "conn-1")
        self.assertEqual(
            set(connector),
            {
                "id", "program_id", "connector_ref", "source_kind",
                "label", "reference_stub", "reference_transport",
                "connected_here", "synced_here", "state",
                "created_by", "created_utc",
            },
        )
        self.assertIs(connector["reference_stub"], True)
        self.assertIs(connector["reference_transport"], True)
        self.assertIs(connector["connected_here"], False)
        self.assertIs(connector["synced_here"], False)

    def test_duplicate_ref_and_bad_kind_rejected(self):
        self.make_connector()
        with self.assertRaises(ValidationError):
            self.make_connector()
        with self.assertRaises(ValidationError):
            self.ext.register_connector(
                self.program_id, "conn-x", "carrier_pigeon", MEMBER)
        second = self.make_connector(ref="excel-addin",
                                     kind="office_spreadsheet")
        self.assertEqual(second["id"], "conn-2")

    def test_receipt_shape_counts_validated_and_labels(self):
        connector = self.make_connector()
        receipt = self.ext.record_sync_receipt(
            self.program_id, connector["id"], "inbound",
            "reported_completed", MEMBER, records_reported=500)
        self.assertEqual(receipt["id"], "csyn-1")
        self.assertIs(receipt["reference_stub"], True)
        self.assertIs(receipt["imported_here"], False)
        self.assertEqual(receipt["records_reported"], 500)
        for bad in (True, 1.5, -1):
            with self.assertRaises(ValidationError):
                self.ext.record_sync_receipt(
                    self.program_id, connector["id"], "inbound",
                    "reported_completed", MEMBER, records_reported=bad)
        with self.assertRaises(NotFoundError):
            self.ext.record_sync_receipt(
                self.program_id, "conn-99", "inbound",
                "reported_completed", MEMBER)

    def test_receipt_imports_nothing_into_core(self):
        employee = make_employee(self.store, self.program_id)
        before_participants = self.store.list_participants(
            self.program_id, MEMBER)
        before_accruals = self.store.list_accruals(
            self.program_id, MEMBER)
        before_summary = self.store.program_summary(
            self.program_id, PERIOD, MEMBER)
        connector = self.make_connector()
        self.ext.record_sync_receipt(
            self.program_id, connector["id"], "inbound",
            "reported_completed", MEMBER, records_reported=500)
        self.assertEqual(
            self.store.list_participants(self.program_id, MEMBER),
            before_participants)
        self.assertEqual(
            self.store.list_accruals(self.program_id, MEMBER),
            before_accruals)
        self.assertEqual(
            self.store.program_summary(self.program_id, PERIOD, MEMBER),
            before_summary)
        self.assertEqual(employee["id"], before_participants[0]["id"])

    def test_integration_summary_derived(self):
        connector = self.make_connector()
        self.ext.record_sync_receipt(
            self.program_id, connector["id"], "inbound",
            "reported_completed", MEMBER, records_reported=500)
        self.ext.record_sync_receipt(
            self.program_id, connector["id"], "outbound",
            "reported_partial", MEMBER, records_reported=25)
        self.ext.record_sync_receipt(
            self.program_id, connector["id"], "inbound",
            "reported_completed", MEMBER)
        summary = self.ext.integration_summary(self.program_id, MEMBER)
        self.assertEqual(summary["connectors"], 1)
        self.assertEqual(summary["receipts"], 3)
        self.assertEqual(
            summary["receipts_by_outcome"],
            {"reported_completed": 2, "reported_partial": 1,
             "reported_failed": 0})
        self.assertEqual(summary["total_records_reported"], 525)
        self.assertIs(summary["reference_stub"], True)
        self.assertIs(summary["imported_here"], False)


class TestMarketplaceBuilt(AdditionFixture):
    """Entry (idx 669): Solution marketplace & application
    extensibility — built as catalog records: listings held as
    data and adoption records with reported outcomes; the
    marketplace itself is not operated here."""

    def make_listing(self, ref="sol-close", publisher="platform"):
        return self.ext.register_solution_listing(
            self.program_id, ref, publisher, MEMBER,
            category_label="financial-close", version_label="2.1",
            title_label="Close Manager")

    def test_listing_shape_and_labels(self):
        listing = self.make_listing()
        self.assertEqual(listing["id"], "slst-1")
        self.assertEqual(
            set(listing),
            {
                "id", "program_id", "listing_ref", "publisher_kind",
                "category_label", "version_label", "title_label",
                "distributed_here", "installed_here", "state",
                "created_by", "created_utc",
            },
        )
        self.assertIs(listing["distributed_here"], False)
        self.assertIs(listing["installed_here"], False)
        self.assertEqual(listing["state"], "recorded_listing_only")
        self.assertNotIn("reference_stub", listing)

    def test_duplicate_ref_and_bad_publisher_rejected(self):
        self.make_listing()
        with self.assertRaises(ValidationError):
            self.make_listing()
        with self.assertRaises(ValidationError):
            self.ext.register_solution_listing(
                self.program_id, "sol-x", "anonymous", MEMBER)
        second = self.make_listing(ref="sol-partner",
                                   publisher="third_party")
        self.assertEqual(second["id"], "slst-2")

    def test_adoption_and_report_leave_listing_byte_identical(self):
        listing = self.make_listing()
        adoption = self.ext.record_solution_adoption(
            self.program_id, listing["id"], "deployment-eu-1", MEMBER)
        self.assertEqual(adoption["id"], "sado-1")
        self.assertIs(adoption["installed_here"], False)
        report = self.ext.record_adoption_report(
            self.program_id, adoption["id"], "reported_installed",
            MEMBER)
        self.assertEqual(report["id"], "sadr-1")
        self.assertIs(report["installed_here"], False)
        after = self.ext.get_solution_listing(
            self.program_id, listing["id"], MEMBER)
        self.assertEqual(after, listing)
        with self.assertRaises(NotFoundError):
            self.ext.record_solution_adoption(
                self.program_id, "slst-99", "deployment-x", MEMBER)

    def test_marketplace_summary_derived(self):
        first = self.make_listing()
        self.make_listing(ref="sol-partner", publisher="third_party")
        adoption = self.ext.record_solution_adoption(
            self.program_id, first["id"], "deployment-eu-1", MEMBER)
        self.ext.record_adoption_report(
            self.program_id, adoption["id"], "reported_installed",
            MEMBER)
        self.ext.record_adoption_report(
            self.program_id, adoption["id"], "reported_removed", MEMBER)
        summary = self.ext.marketplace_summary(self.program_id, MEMBER)
        self.assertEqual(summary["listings"], 2)
        self.assertEqual(
            summary["listings_by_publisher_kind"],
            {"platform": 1, "third_party": 1})
        self.assertEqual(summary["adoptions"], 1)
        self.assertEqual(summary["adoption_reports"], 2)
        self.assertEqual(
            summary["adoption_reports_by_outcome"],
            {"reported_installed": 1, "reported_removed": 1,
             "reported_failed": 0})
        self.assertIs(summary["distributed_here"], False)


class TestCrossCutting(AdditionFixture):
    """Cross-cutting pins: RBAC + membership on the addition
    surface, exta_ audit actions with :denied denials,
    platform-admin reach, audit-failure rollback, program
    scoping, the standing named-absence pin, and the recursive
    forbidden-key scan across one record of every kind."""

    def _one_of_every_kind(self):
        entity = self.make_entity()
        plan = self.make_plan(entity_id=entity["id"])
        line = self.ext.record_cpm_plan_line(
            self.program_id, plan["id"], "revenue", 100, MEMBER)
        forecast = self.ext.record_cpm_forecast(
            self.program_id, entity["id"], "2026", 100, MEMBER)
        connector = self.ext.register_connector(
            self.program_id, "erp-main", "erp_system", MEMBER)
        receipt = self.ext.record_sync_receipt(
            self.program_id, connector["id"], "inbound",
            "reported_completed", MEMBER, records_reported=3)
        listing = self.ext.register_solution_listing(
            self.program_id, "sol-close", "platform", MEMBER)
        adoption = self.ext.record_solution_adoption(
            self.program_id, listing["id"], "deployment-1", MEMBER)
        report = self.ext.record_adoption_report(
            self.program_id, adoption["id"], "reported_installed",
            MEMBER)
        return (entity, plan, line, forecast, connector, receipt,
                listing, adoption, report)

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_cpm_entity(
                self.program_id, "entity-x", "USD", VIEWER)
        self.assertIn(
            "exta_cpm_entity_register:denied", self.audit_actions())
        self.assertEqual(
            self.ext.list_cpm_entities(self.program_id, MEMBER), [])

    def test_outsider_denied_by_membership(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_connector(
                self.program_id, "erp-x", "erp_system", OUTSIDER)
        self.assertEqual(
            self.ext.list_connectors(self.program_id, MEMBER), [])

    def test_admin_reaches_program_and_audit_records_exta_actions(self):
        entity = self.ext.register_cpm_entity(
            self.program_id, "entity-admin", "USD", ADMIN)
        self.assertEqual(entity["id"], "cent-1")
        self.assertIn("exta_cpm_entity_register", self.audit_actions())

    def test_auditor_denied_addition_but_audit_duty_works(self):
        """High apparatus (AC-5): the auditor role holds audit_read
        only — every addition write AND read is denied — while its
        core audit duty (trail read, chain verification) works
        unchanged, and the chain verifies after addition
        operations."""
        self.make_entity()
        with self.assertRaises(PermissionDenied):
            self.ext.register_cpm_entity(
                self.program_id, "entity-dana", "USD", AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.list_cpm_entities(self.program_id, AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.cpm_consolidation_view(
                self.program_id, "2026", AUDITOR)
        self.assertIn(
            "exta_cpm_entity_register:denied", self.audit_actions())
        self.assertTrue(len(self.audit.entries()) > 0)
        ok, first_bad = self.audit.verify_chain()
        self.assertEqual((ok, first_bad), (True, None))

    def test_cross_program_records_not_visible(self):
        other = self.store.create_program("other-program", MEMBER)
        entity = self.make_entity()
        with self.assertRaises(NotFoundError):
            self.ext.get_cpm_entity(other["id"], entity["id"], MEMBER)
        self.assertEqual(
            self.ext.list_cpm_entities(other["id"], MEMBER), [])

    def test_audit_failure_rolls_back_record_and_id(self):
        class Boom:
            def record(self, *args, **kwargs):
                raise RuntimeError("audit unavailable")

        real_audit = self.store.audit
        self.store.audit = Boom()
        try:
            with self.assertRaises(RuntimeError):
                self.ext.register_cpm_entity(
                    self.program_id, "entity-boom", "USD", MEMBER)
        finally:
            self.store.audit = real_audit
        self.assertEqual(
            self.ext.list_cpm_entities(self.program_id, MEMBER), [])
        entity = self.make_entity()
        self.assertEqual(entity["id"], "cent-1")

    def test_no_execution_surface_exists(self):
        """The category's standing named absence — trading &
        investment execution — stands on this surface too: no
        order, execution, or payment operation exists on the
        class, and nothing consolidates or forecasts *for* the
        caller (no compute entry point beyond read-time sums
        over recorded values)."""
        for name in ("create_trade_order", "execute_trade",
                     "place_trade", "buy", "sell", "execute_payment",
                     "make_payment", "transfer_funds",
                     "run_consolidation", "compute_forecast",
                     "install_solution", "distribute_solution"):
            self.assertFalse(
                hasattr(FinanceExtensionsAddition, name), name)

    def test_forbidden_keys_absent_across_all_kinds(self):
        """Money and identity discipline, by scan: every money key
        is an integer-cents key (no float amount shape exists),
        and no record carries a bank-detail, identifier, credit,
        or score key; derived views carry no rate / trend /
        average / grand-total key."""
        records = self._one_of_every_kind()
        self.assertEqual(len(records), 9)
        fragments = ("score", "account_number", "routing", "iban",
                     "sort_code", "card_number", "bank", "credit",
                     "ssn", "passport", "license_number")
        for record in records:
            for key in all_keys(record):
                for fragment in fragments:
                    self.assertNotIn(fragment, key.lower())
        views = (
            self.ext.cpm_consolidation_view(
                self.program_id, "2026", MEMBER),
            self.ext.integration_summary(self.program_id, MEMBER),
            self.ext.marketplace_summary(self.program_id, MEMBER),
        )
        exact_banned = {"rate", "trend", "average", "grand_total"}
        for view in views:
            for key in all_keys(view):
                self.assertNotIn(key, exact_banned)
        stub_records = (
            self.ext.list_connectors(self.program_id, MEMBER)
            + self.ext.list_sync_receipts(self.program_id, MEMBER)
        )
        for record in stub_records:
            self.assertIs(record["reference_stub"], True)
            self.assertIs(record["reference_transport"], True)
        built_records = (
            self.ext.list_cpm_entities(self.program_id, MEMBER)
            + self.ext.list_solution_listings(self.program_id, MEMBER)
        )
        for record in built_records:
            self.assertNotIn("reference_stub", record)


class TestTotalsByCurrencyNegativeControl(AdditionFixture):
    """Fresh negative control for the per-currency totals seam.

    Canonical expectation: consolidation sums recorded amounts
    per currency label — USD amounts under USD, EUR amounts
    under EUR, never mixed. The mutant sums everything under
    the first label seen (a cross-currency sum) and must
    misstate every multi-currency case.
    """

    AMOUNTS = [("USD", 100000), ("EUR", 200000), ("USD", -5000),
               ("EUR", 1000)]

    def test_canonical_totals_from_seam(self):
        self.assertEqual(
            _totals_by_currency(self.AMOUNTS),
            {"USD": 95000, "EUR": 201000})

    def test_canonical_totals_match_view(self):
        usd = self.make_entity(ref="entity-us", currency="USD")
        eur = self.make_entity(ref="entity-eu", currency="EUR")
        plan_usd = self.make_plan(entity_id=usd["id"], ref="plan-us")
        plan_eur = self.make_plan(entity_id=eur["id"], ref="plan-eu")
        self.ext.record_cpm_plan_line(
            self.program_id, plan_usd["id"], "revenue", 100000, MEMBER)
        self.ext.record_cpm_plan_line(
            self.program_id, plan_usd["id"], "elimination", -5000,
            MEMBER)
        self.ext.record_cpm_plan_line(
            self.program_id, plan_eur["id"], "revenue", 200000, MEMBER)
        self.ext.record_cpm_plan_line(
            self.program_id, plan_eur["id"], "adjustment", 1000, MEMBER)
        view = self.ext.cpm_consolidation_view(
            self.program_id, "2026", MEMBER)
        self.assertEqual(
            view["plan_totals_by_currency"],
            {"USD": 95000, "EUR": 201000})

    def test_mutant_mixes_currencies(self):
        self.assertEqual(
            mutant_totals_single_bucket(self.AMOUNTS),
            {"USD": 296000})
        self.assertNotEqual(
            mutant_totals_single_bucket(self.AMOUNTS),
            {"USD": 95000, "EUR": 201000})

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant_totals_single_bucket(self.AMOUNTS),
                {"USD": 95000, "EUR": 201000})

    def test_sanity_single_currency_both_agree(self):
        amounts = [("USD", 100), ("USD", 50)]
        self.assertEqual(_totals_by_currency(amounts), {"USD": 150})
        self.assertEqual(
            mutant_totals_single_bucket(amounts), {"USD": 150})


if __name__ == "__main__":
    unittest.main()
