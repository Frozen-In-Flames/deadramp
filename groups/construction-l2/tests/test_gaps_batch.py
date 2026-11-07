"""Final GAPS batch — Construction L2 extension surface.

Pins the records forms built for the 9 open entries of the
"Group 19 — Construction L2 (4 forks)" section of GAPS.md (see
BATCH.md in the group directory): cost estimating, GPS / field
collection, prevailing wage, dispatch routing (built), and the
five labeled reference stubs (telematics, contract lifecycle,
e-signature, AI/ML, workflow automation).

The founding discipline is pinned throughout: nothing here
senses, monitors, signs, infers, or executes — every record
carries its ``*_here: False`` label, outcomes and figures are
stored exactly as reported, computed values exist only in read
views, and the core records underneath are byte-identical after
every extension operation.
"""

import unittest
from fractions import Fraction

from construct.errors import NotFoundError, PermissionDenied, ValidationError
from construct.extensions import ConstructExtensions, _compute_wage_amounts

from construct_helpers import ADMIN, OPERATOR, VIEWER, make_store


def mutant_wage_amounts(base_rate, fringe_rate, minutes):
    """The wage mutant: computes the base and waves the fringe
    through as zero, so the gross is understated by exactly the
    fringe amount."""
    base = Fraction(base_rate * minutes, 60)
    return base, Fraction(0), base


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


def _has_float(obj):
    if isinstance(obj, float):
        return True
    if isinstance(obj, dict):
        return any(_has_float(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_float(v) for v in obj)
    return False


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.project, self.prime, self.sub = make_store()
        self.audit = self.store.audit
        self.ext = ConstructExtensions(self.store)
        self.pid = self.project["id"]

    def make_contract(self):
        return self.store.create_contract(
            ADMIN, "Main Contract", self.pid, org_id=self.prime["id"],
            value_cents=1000000)

    def make_document(self):
        return self.store.create_document(
            ADMIN, "Spec Sheet", project_id=self.pid, doc_type="specification")

    def make_dispatch(self):
        return self.store.create_dispatch(
            ADMIN, self.pid, "Deliver forms", org_id=self.prime["id"])

    def make_rate_table(self, base=3000, fringe=500):
        return self.ext.create_rate_table(
            ADMIN, "TX-Davis-Bacon", "electrician", base, fringe,
            effective_label="2026 schedule")

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]


class TestCostEstimating(BatchFixture):
    """Entry 204: cost estimating engines & proprietary cost
    data — built as estimate records with totals derived at
    read; cost data held as a source reference only."""

    def test_estimate_shape_and_labels(self):
        est = self.ext.create_estimate(
            OPERATOR, self.pid, "Annex estimate",
            cost_data_source_ref="RSMeans-2026-Q1")
        self.assertEqual(est["id"], "est-1")
        self.assertEqual(
            set(est.keys()),
            {"id", "project_id", "title", "cost_data_source_ref",
             "data_held_here", "created_by", "created_utc"})
        self.assertIs(est["data_held_here"], False)
        self.assertIn("ext_estimate_create", self.audit_actions())

    def test_totals_derived_at_read_never_stored(self):
        est = self.ext.create_estimate(ADMIN, self.pid, "Estimate")
        line_a = self.ext.add_estimate_line(
            ADMIN, est["id"], "conduit", 3, 250)
        self.ext.add_estimate_line(ADMIN, est["id"], "labor", 2, 1000)
        # Stored line carries no total key.
        self.assertEqual(
            set(line_a.keys()),
            {"id", "estimate_id", "description", "quantity",
             "unit_price_cents", "created_by", "created_utc"})
        self.assertNotIn("total_cents",
                         self.ext.get_estimate(ADMIN, est["id"]))
        view = self.ext.estimate_view(ADMIN, est["id"])
        self.assertEqual(view["lines"][0]["line_total_cents"], 750)
        self.assertEqual(view["lines"][1]["line_total_cents"], 2000)
        self.assertEqual(view["total_cents"], 2750)
        self.assertEqual(view["line_count"], 2)
        # Estimates create no core cost entries.
        self.assertEqual(self.store.list_cost_entries(ADMIN), [])

    def test_money_and_quantity_rules(self):
        est = self.ext.create_estimate(ADMIN, self.pid, "Estimate")
        with self.assertRaises(ValidationError):
            self.ext.add_estimate_line(ADMIN, est["id"], "x", 1, 10.5)
        with self.assertRaises(ValidationError):
            self.ext.add_estimate_line(ADMIN, est["id"], "x", 1, True)
        with self.assertRaises(ValidationError):
            self.ext.add_estimate_line(ADMIN, est["id"], "x", 0, 100)
        with self.assertRaises(ValidationError):
            self.ext.add_estimate_line(ADMIN, est["id"], "x", 1, -5)
        # Failures consumed no ids.
        line = self.ext.add_estimate_line(ADMIN, est["id"], "ok", 1, 100)
        self.assertEqual(line["id"], "estl-1")

    def test_unknown_project_and_estimate(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_estimate(ADMIN, "prj-99", "Nope")
        with self.assertRaises(NotFoundError):
            self.ext.add_estimate_line(ADMIN, "est-99", "x", 1, 100)


class TestFieldReports(BatchFixture):
    """Entry 205: GPS / location tracking & field collection —
    built as field-report records holding reported labels
    verbatim; nothing is sensed or tracked."""

    def test_report_shape_labels_and_verbatim_position(self):
        report = self.ext.record_field_report(
            OPERATOR, self.pid, "GRID 44.02 / -91.10 as reported",
            "form F-7 submitted", worker_ref="W-EXT-1",
            reported_at="2026-10-01T08:30:00Z")
        self.assertEqual(report["id"], "fld-1")
        self.assertEqual(
            set(report.keys()),
            {"id", "project_id", "dispatch_id", "worker_ref", "form_ref",
             "reported_position_label", "observation_label", "reported_at",
             "tracked_here", "collected_here", "created_by", "created_utc"})
        self.assertEqual(report["reported_position_label"],
                         "GRID 44.02 / -91.10 as reported")
        self.assertIs(report["tracked_here"], False)
        self.assertIs(report["collected_here"], False)

    def test_reports_are_standalone_no_tracking_state(self):
        self.ext.record_field_report(ADMIN, self.pid, "P-1", "obs-1")
        self.ext.record_field_report(ADMIN, self.pid, "P-2", "obs-2")
        reports = self.ext.list_field_reports(ADMIN, self.pid)
        self.assertEqual(len(reports), 2)
        for report in reports:
            self.assertNotIn("track", _all_keys(report) - {"tracked_here"})
            self.assertNotIn("trail", _all_keys(report))
            self.assertNotIn("history", _all_keys(report))

    def test_dispatch_link_must_match_project(self):
        dispatch = self.make_dispatch()
        other = self.store.create_project("Other Project", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_field_report(
                ADMIN, other["id"], "P", "obs", dispatch_id=dispatch["id"])
        report = self.ext.record_field_report(
            ADMIN, self.pid, "P", "obs", dispatch_id=dispatch["id"])
        self.assertEqual(report["dispatch_id"], dispatch["id"])


class TestPrevailingWage(BatchFixture):
    """Entry 211: prevailing-wage determination depth — built:
    rate tables as data, wage lines as recorded inputs, amounts
    derived exactly at read, certified-payroll reports derived,
    e-filing as a labeled reference."""

    def test_rate_table_shape(self):
        table = self.make_rate_table()
        self.assertEqual(table["id"], "rate-1")
        self.assertEqual(
            set(table.keys()),
            {"id", "jurisdiction_label", "trade_label",
             "base_rate_cents_per_hour", "fringe_rate_cents_per_hour",
             "effective_label", "created_by", "created_utc"})

    def test_wage_amounts_derived_exact_never_stored(self):
        table = self.make_rate_table()
        line = self.ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 480,
            "2026-W40")
        self.assertEqual(
            set(line.keys()),
            {"id", "project_id", "org_id", "worker_ref", "rate_table_id",
             "minutes", "period_label", "created_by", "created_utc"})
        view = self.ext.wage_line_view(ADMIN, line["id"])
        self.assertEqual(view["base_cents"], 24000)
        self.assertEqual(view["fringe_cents"], 4000)
        self.assertEqual(view["gross_cents"], 28000)

    def test_fractional_amounts_rendered_exactly(self):
        table = self.make_rate_table(base=1001, fringe=0)
        line = self.ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 7,
            "2026-W40")
        view = self.ext.wage_line_view(ADMIN, line["id"])
        self.assertEqual(view["base_cents"], "7007/60")
        self.assertEqual(view["fringe_cents"], 0)
        self.assertEqual(view["gross_cents"], "7007/60")
        base, fringe, gross = _compute_wage_amounts(1001, 0, 7)
        self.assertEqual(base, Fraction(7007, 60))
        self.assertEqual(gross, base + fringe)

    def test_certified_payroll_report_totals_derived(self):
        table = self.make_rate_table()
        line_a = self.ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 480,
            "2026-W40")
        line_b = self.ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-2", table["id"], 240,
            "2026-W40")
        report = self.ext.generate_certified_payroll_report(
            ADMIN, self.pid, self.sub["id"], "2026-W40",
            [line_a["id"], line_b["id"]])
        self.assertEqual(report["id"], "cpr-1")
        self.assertEqual(
            set(report.keys()),
            {"id", "project_id", "org_id", "period_label", "line_ids",
             "created_by", "created_utc"})
        view = self.ext.certified_payroll_view(ADMIN, report["id"])
        self.assertEqual(view["total_base_cents"], 36000)
        self.assertEqual(view["total_fringe_cents"], 6000)
        self.assertEqual(view["total_gross_cents"], 42000)
        self.assertEqual(view["line_count"], 2)
        self.assertEqual(view["worker_count"], 2)
        # The report created no core payroll record.
        self.assertEqual(self.store.list_payrolls(ADMIN), [])

    def test_report_rejects_foreign_lines(self):
        table = self.make_rate_table()
        line = self.ext.record_wage_line(
            ADMIN, self.pid, self.prime["id"], "W-9", table["id"], 60,
            "2026-W40")
        with self.assertRaises(ValidationError):
            self.ext.generate_certified_payroll_report(
                ADMIN, self.pid, self.sub["id"], "2026-W40", [line["id"]])

    def test_efiling_is_labeled_reference(self):
        table = self.make_rate_table()
        line = self.ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 60,
            "2026-W40")
        report = self.ext.generate_certified_payroll_report(
            ADMIN, self.pid, self.sub["id"], "2026-W40", [line["id"]])
        filing = self.ext.record_efiling(
            ADMIN, report["id"], "AGENCY-RECEIPT-1")
        self.assertEqual(
            set(filing.keys()),
            {"id", "report_id", "filing_ref", "reference_stub",
             "filed_here", "state", "created_by", "created_utc"})
        self.assertIs(filing["reference_stub"], True)
        self.assertIs(filing["filed_here"], False)
        self.assertEqual(filing["state"], "recorded_reference_only")

    def test_rate_and_minutes_rules(self):
        with self.assertRaises(ValidationError):
            self.ext.create_rate_table(ADMIN, "J", "T", 0, 100)
        with self.assertRaises(ValidationError):
            self.ext.create_rate_table(ADMIN, "J", "T", 100.5, 100)
        with self.assertRaises(ValidationError):
            self.ext.create_rate_table(ADMIN, "J", "T", 100, -1)
        table = self.make_rate_table()
        with self.assertRaises(ValidationError):
            self.ext.record_wage_line(
                ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 0,
                "2026-W40")
        with self.assertRaises(NotFoundError):
            self.ext.record_wage_line(
                ADMIN, self.pid, self.sub["id"], "W-1", "rate-99", 60,
                "2026-W40")


class TestWageSeamNegativeControl(BatchFixture):
    """Fresh negative control for the new code: the prevailing-
    wage seam :func:`_compute_wage_amounts`. The canonical claim
    is that fringe is computed from the recorded fringe rate
    and included in the gross. The mutant drops the fringe;
    treating its outcome as the expectation must fail."""

    def test_fringe_canonical_but_mutant_not(self):
        base, fringe, gross = _compute_wage_amounts(3000, 500, 480)
        self.assertEqual((base, fringe, gross),
                         (Fraction(24000), Fraction(4000), Fraction(28000)))
        m_base, m_fringe, m_gross = mutant_wage_amounts(3000, 500, 480)
        self.assertNotEqual((m_base, m_fringe, m_gross),
                            (Fraction(24000), Fraction(4000), Fraction(28000)))
        with self.assertRaises(AssertionError):
            self.assertEqual(m_gross, Fraction(28000))

    def test_view_uses_the_seam(self):
        table = self.make_rate_table()
        line = self.ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 480,
            "2026-W40")
        view = self.ext.wage_line_view(ADMIN, line["id"])
        self.assertEqual(view["fringe_cents"], 4000)
        self.assertEqual(view["gross_cents"], 28000)
        # The mutant's gross would fail this expectation.
        _, _, m_gross = mutant_wage_amounts(3000, 500, 480)
        self.assertNotEqual(view["gross_cents"], m_gross)


class TestDispatchRouting(BatchFixture):
    """Entry 212: dispatch routing & optimization — built as
    route records held as data plus verbatim reported outcomes;
    no optimizer runs."""

    def test_route_shape_order_and_core_untouched(self):
        dispatch = self.make_dispatch()
        before = self.store.get_dispatch(dispatch["id"], ADMIN)
        route = self.ext.create_route_plan(
            OPERATOR, dispatch["id"], ["Depot", "Site B", "Site A"])
        self.assertEqual(route["id"], "rte-1")
        self.assertEqual(
            set(route.keys()),
            {"id", "dispatch_id", "project_id", "stops",
             "optimized_here", "created_by", "created_utc"})
        # The recorded order is the caller's order, verbatim —
        # not a computed (e.g. sorted) order.
        self.assertEqual(route["stops"], ["Depot", "Site B", "Site A"])
        self.assertIs(route["optimized_here"], False)
        self.assertEqual(
            self.store.get_dispatch(dispatch["id"], ADMIN), before)

    def test_route_outcomes_verbatim(self):
        dispatch = self.make_dispatch()
        route = self.ext.create_route_plan(ADMIN, dispatch["id"], ["A"])
        outcome = self.ext.record_route_outcome(
            ADMIN, route["id"], "reported_delayed")
        self.assertIs(outcome["optimized_here"], False)
        view = self.ext.route_view(ADMIN, route["id"])
        self.assertEqual(len(view["outcomes"]), 1)
        self.assertEqual(view["dispatch"]["id"], dispatch["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_route_outcome(ADMIN, route["id"], "optimized")


class TestTelematicsStub(BatchFixture):
    """Entry 206: fleet & vehicle telematics — labeled
    reference; driver scores are reported labels only."""

    def test_vehicle_and_report_shapes(self):
        vehicle = self.ext.register_vehicle(
            OPERATOR, self.pid, "VIN-REF-7")
        self.assertEqual(
            set(vehicle.keys()),
            {"id", "project_id", "vehicle_ref", "reference_stub",
             "monitored_here", "state", "created_by", "created_utc"})
        self.assertIs(vehicle["reference_stub"], True)
        self.assertIs(vehicle["monitored_here"], False)
        report = self.ext.record_telematics_report(
            ADMIN, vehicle["id"], "reported_idling",
            reported_driver_score_label="watch")
        self.assertEqual(
            set(report.keys()),
            {"id", "vehicle_id", "project_id", "report_label",
             "reported_driver_score_label", "reference_stub",
             "monitored_here", "state", "created_by", "created_utc"})
        self.assertEqual(report["reported_driver_score_label"], "watch")

    def test_no_computed_score_anywhere(self):
        vehicle = self.ext.register_vehicle(ADMIN, self.pid, "VIN-REF-7")
        report = self.ext.record_telematics_report(
            ADMIN, vehicle["id"], "reported_speeding",
            reported_driver_score_label="good")
        score_keys = {k for k in _all_keys(report) if "score" in k}
        self.assertEqual(score_keys, {"reported_driver_score_label"})
        self.assertIsInstance(report["reported_driver_score_label"], str)
        with self.assertRaises(ValidationError):
            self.ext.record_telematics_report(
                ADMIN, vehicle["id"], "reported_flying")


class TestContractLifecycleStub(BatchFixture):
    """Entry 207: CLM workflow engines, template & clause
    libraries, playbooks with redlining — labeled reference:
    metadata records plus reported outcomes."""

    def test_template_clause_playbook_metadata_only(self):
        template = self.ext.create_template_record(
            ADMIN, "MSA Template", "TPL-REF-1")
        clause = self.ext.create_clause_record(
            ADMIN, "indemnity-standard", template_id=template["id"])
        playbook = self.ext.create_playbook_record(
            ADMIN, "Standard Playbook", "PBK-REF-1")
        for record in (template, clause, playbook):
            self.assertIs(record["reference_stub"], True)
            self.assertEqual(record["state"], "recorded_reference_only")
            self.assertNotIn("content", _all_keys(record))
            self.assertNotIn("text", _all_keys(record))

    def test_negotiation_outcome_verbatim_core_untouched(self):
        contract = self.make_contract()
        before = self.store.get_contract(contract["id"], ADMIN,
                                         now="2026-06-01T00:00:00Z")
        playbook = self.ext.create_playbook_record(
            ADMIN, "Standard Playbook", "PBK-REF-1")
        outcome = self.ext.record_negotiation_outcome(
            ADMIN, contract["id"], "reported_countered",
            playbook_id=playbook["id"])
        self.assertIs(outcome["redlined_here"], False)
        self.assertIs(outcome["reference_stub"], True)
        after = self.store.get_contract(contract["id"], ADMIN,
                                        now="2026-06-01T00:00:00Z")
        self.assertEqual(before, after)


class TestESignatureStub(BatchFixture):
    """Entry 208: e-signature execution — labeled reference in
    the house form; no signature value exists."""

    def test_request_and_outcome_shapes(self):
        contract = self.make_contract()
        request = self.ext.record_signature_request(
            ADMIN, "SIGNER-REF-1", contract_id=contract["id"])
        self.assertEqual(
            set(request.keys()),
            {"id", "contract_id", "document_id", "signer_ref",
             "reference_stub", "signed_here", "state", "created_by",
             "created_utc"})
        self.assertIs(request["signed_here"], False)
        outcome = self.ext.record_signature_outcome(
            ADMIN, request["id"], "reported_signed")
        self.assertIs(outcome["signed_here"], False)
        for record in (request, outcome):
            self.assertNotIn("signature_value", _all_keys(record))
            self.assertNotIn("signature_data", _all_keys(record))

    def test_exactly_one_target_required(self):
        contract = self.make_contract()
        document = self.make_document()
        with self.assertRaises(ValidationError):
            self.ext.record_signature_request(ADMIN, "S-1")
        with self.assertRaises(ValidationError):
            self.ext.record_signature_request(
                ADMIN, "S-1", contract_id=contract["id"],
                document_id=document["id"])
        request = self.ext.record_signature_request(
            ADMIN, "S-1", document_id=document["id"])
        self.assertEqual(request["document_id"], document["id"])


class TestAiStub(BatchFixture):
    """Entry 209: AI/ML models (extraction & negotiation
    assistance) — labeled reference; results are opaque refs."""

    def test_extraction_result_opaque_ref_only(self):
        document = self.make_document()
        record = self.ext.record_extraction_result(
            ADMIN, document["id"], "extractor-v1", "RESULT-REF-1")
        self.assertEqual(
            set(record.keys()),
            {"id", "document_id", "model_label", "result_ref",
             "reference_stub", "inference_here", "state", "created_by",
             "created_utc"})
        self.assertIs(record["inference_here"], False)
        self.assertNotIn("extracted_text", _all_keys(record))

    def test_negotiation_assistance_opaque_ref_only(self):
        contract = self.make_contract()
        record = self.ext.record_negotiation_assistance(
            ADMIN, contract["id"], "negotiator-v1", "RESULT-REF-2")
        self.assertIs(record["inference_here"], False)
        self.assertIs(record["reference_stub"], True)
        self.assertNotIn("advice", _all_keys(record))
        self.assertNotIn("extracted_text", _all_keys(record))


class TestWorkflowStub(BatchFixture):
    """Entry 210: workflow / process automation engines —
    labeled reference: definitions held as data; the registry
    never executes."""

    def test_definition_held_as_data_never_executed(self):
        definition = self.ext.create_workflow_definition(
            OPERATOR, "Submittal flow",
            ["draft", "submitted", "under_review", "approved"])
        self.assertEqual(
            set(definition.keys()),
            {"id", "label", "steps", "reference_stub", "executed_here",
             "state", "created_by", "created_utc"})
        self.assertEqual(definition["steps"],
                         ["draft", "submitted", "under_review", "approved"])
        self.assertIs(definition["executed_here"], False)
        self.assertFalse(hasattr(self.ext, "run_workflow"))
        self.assertFalse(hasattr(self.ext, "execute_workflow"))
        outcome = self.ext.record_workflow_outcome(
            ADMIN, definition["id"], "reported_completed")
        self.assertIs(outcome["executed_here"], False)
        # Recording an outcome changed no definition.
        self.assertEqual(
            self.ext.get_workflow_definition(ADMIN, definition["id"]),
            definition)


class TestGuardsAndDiscipline(BatchFixture):
    """Cross-cutting: RBAC denial is audited and consumes no
    id; unexpected fields cannot be smuggled in; no stored
    extension record holds a float."""

    def test_viewer_write_denied_audited_no_id_consumed(self):
        store, project, prime, sub = make_store()
        ext = ConstructExtensions(store)
        with self.assertRaises(PermissionDenied):
            ext.create_estimate(VIEWER, project["id"], "Nope")
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("ext_estimate_create:denied", actions)
        est = ext.create_estimate(ADMIN, project["id"], "Fine")
        self.assertEqual(est["id"], "est-1")

    def test_viewer_reads_allowed(self):
        est = self.ext.create_estimate(ADMIN, self.pid, "Readable")
        self.assertEqual(
            self.ext.get_estimate(VIEWER, est["id"])["id"], est["id"])

    def test_unexpected_kwarg_raises_typeerror(self):
        with self.assertRaises(TypeError):
            self.ext.create_estimate(
                ADMIN, self.pid, "T", smuggled_field="x")
        with self.assertRaises(TypeError):
            self.ext.record_telematics_report(
                ADMIN, "veh-1", "reported_ok", computed_score=42)

    def test_no_floats_and_stub_labels_across_surface(self):
        table = self.make_rate_table()
        line = self.ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 60,
            "2026-W40")
        vehicle = self.ext.register_vehicle(ADMIN, self.pid, "VIN-1")
        records = [
            self.ext.create_estimate(ADMIN, self.pid, "E"),
            self.ext.record_field_report(ADMIN, self.pid, "P", "obs"),
            table, line, vehicle,
            self.ext.record_telematics_report(
                ADMIN, vehicle["id"], "reported_ok"),
            self.ext.create_template_record(ADMIN, "T", "REF-1"),
            self.ext.create_workflow_definition(ADMIN, "W", ["a", "b"]),
        ]
        for record in records:
            self.assertFalse(_has_float(record), record["id"])
        stub_records = [r for r in records
                        if r["id"].startswith(("veh-", "tel-", "tpl-", "wfd-"))]
        for record in stub_records:
            self.assertIs(record["reference_stub"], True)
            self.assertEqual(record["state"], "recorded_reference_only")


if __name__ == "__main__":
    unittest.main()
