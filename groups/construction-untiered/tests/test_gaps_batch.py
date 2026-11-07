"""Final GAPS batch — Construction untiered-set extension surface.

Pins the records forms built for the 9 open entries of the
"Untiered Set 7 — Construction (6 forks, tier null)" section of
GAPS.md (see BATCH.md in the group directory): commissioning,
cost estimating, AI technical document review, document control
depth, GIS / spatial, permitting, asset management, and
prevailing wage (built), and the one labeled reference stub
(workflow automation).

Two disciplines are pinned throughout. The founding records
discipline: nothing here commissions, estimates over a cost
database, reviews, controls content, senses, issues, assesses,
or executes — every record carries its ``*_here: False`` label,
outcomes and figures are stored exactly as reported, and
computed values exist only in read views. And tier null: every
extension record and derived view is scanned recursively for
tier-shaped keys, floats, and numeric lists — this set asserts
no tier, no baseline, and no equivalence anywhere, including
on the new surface.
"""

import unittest
from fractions import Fraction

from construct.errors import NotFoundError, PermissionDenied, ValidationError
from construct.extensions import (
    ConstructExtensions,
    _compute_wage_amounts,
    _current_permit_state,
)

from construct_helpers import ADMIN, OPERATOR, VIEWER, make_store


def mutant_current_permit_state(states):
    """The permit-state mutant: reads the EARLIEST recorded
    label instead of the latest, resurrecting superseded
    states."""
    if not states:
        return "recorded"
    return states[0]["state_label"]


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


def _walk(obj):
    """Yield (key, value) for every dict entry, recursively."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


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

    def make_document(self):
        return self.store.create_document(
            ADMIN, "Spec Sheet", project_id=self.pid,
            doc_type="specification")

    def make_permit(self):
        return self.ext.create_permit(
            OPERATOR, self.pid, "permit", "Building permit",
            authority_label="City of Dallas",
            application_ref="APP-2026-1")

    def make_rate_table(self, base=3000, fringe=500):
        return self.ext.create_rate_table(
            ADMIN, "TX-Davis-Bacon", "electrician", base, fringe,
            effective_label="2026 schedule")

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]


class TestCommissioning(BatchFixture):
    """Entry: Construction commissioning engine — built as
    plan / checklist-item / reported-outcome / turnover records
    over core projects; systems are verified by others."""

    def test_plan_and_item_shapes(self):
        plan = self.ext.create_commissioning_plan(
            OPERATOR, self.pid, "AHU commissioning",
            system_label="AHU-1")
        self.assertEqual(plan["id"], "cxp-1")
        self.assertEqual(
            set(plan.keys()),
            {"id", "project_id", "title", "system_label", "created_by",
             "created_utc"})
        item = self.ext.add_checklist_item(
            ADMIN, plan["id"], "functional_performance_test",
            "Verify airflow at design point")
        self.assertEqual(
            set(item.keys()),
            {"id", "plan_id", "kind", "label", "created_by", "created_utc"})
        self.assertIn("ext_cx_plan_create", self.audit_actions())

    def test_outcome_verbatim_and_labeled(self):
        plan = self.ext.create_commissioning_plan(ADMIN, self.pid, "Cx")
        item = self.ext.add_checklist_item(
            ADMIN, plan["id"], "issue_observation", "Damper stuck")
        outcome = self.ext.record_checklist_outcome(
            ADMIN, item["id"], "reported_resolved",
            reported_by_ref="CX-AGENT-1")
        self.assertEqual(
            set(outcome.keys()),
            {"id", "item_id", "outcome_label", "reported_by_ref",
             "commissioned_here", "created_by", "created_utc"})
        self.assertIs(outcome["commissioned_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_checklist_outcome(
                ADMIN, item["id"], "commissioned_ok")
        with self.assertRaises(ValidationError):
            self.ext.add_checklist_item(ADMIN, plan["id"], "magic", "x")

    def test_turnover_package_references_core_documents(self):
        plan = self.ext.create_commissioning_plan(ADMIN, self.pid, "Cx")
        document = self.make_document()
        package = self.ext.record_turnover_package(
            ADMIN, plan["id"], "PKG-REF-1", document_ids=[document["id"]])
        self.assertIs(package["assembled_here"], False)
        self.assertEqual(package["document_ids"], [document["id"]])
        with self.assertRaises(NotFoundError):
            self.ext.record_turnover_package(
                ADMIN, plan["id"], "PKG-REF-2", document_ids=["doc-99"])

    def test_plan_view_counts_derived(self):
        plan = self.ext.create_commissioning_plan(ADMIN, self.pid, "Cx")
        item_a = self.ext.add_checklist_item(
            ADMIN, plan["id"], "installation_checklist", "Install unit")
        item_b = self.ext.add_checklist_item(
            ADMIN, plan["id"], "functional_performance_test", "Run test")
        self.ext.record_checklist_outcome(
            ADMIN, item_a["id"], "reported_passed")
        self.ext.record_checklist_outcome(
            ADMIN, item_b["id"], "reported_open")
        self.assertNotIn("item_count",
                         self.ext.get_commissioning_plan(ADMIN, plan["id"]))
        view = self.ext.commissioning_plan_view(ADMIN, plan["id"])
        self.assertEqual(view["item_count"], 2)
        self.assertEqual(view["items_by_kind"],
                         {"installation_checklist": 1,
                          "functional_performance_test": 1})
        self.assertEqual(view["outcomes_by_label"],
                         {"reported_passed": 1, "reported_open": 1})
        self.assertEqual(view["turnover_count"], 0)


class TestCostEstimating(BatchFixture):
    """Entry: Cost estimating engines & benchmark cost data —
    built as estimate records with totals derived at read;
    benchmark data held as a source reference only."""

    def test_estimate_shape_and_labels(self):
        est = self.ext.create_estimate(
            OPERATOR, self.pid, "Annex estimate",
            cost_data_source_ref="BENCH-2026-Q1")
        self.assertEqual(est["id"], "est-1")
        self.assertEqual(
            set(est.keys()),
            {"id", "project_id", "title", "cost_data_source_ref",
             "data_held_here", "created_by", "created_utc"})
        self.assertIs(est["data_held_here"], False)

    def test_totals_derived_at_read_never_stored(self):
        est = self.ext.create_estimate(ADMIN, self.pid, "Estimate")
        line_a = self.ext.add_estimate_line(
            ADMIN, est["id"], "conduit", 3, 250)
        self.ext.add_estimate_line(ADMIN, est["id"], "labor", 2, 1000)
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
        self.assertEqual(self.store.list_cost_entries(ADMIN), [])

    def test_money_and_quantity_rules(self):
        est = self.ext.create_estimate(ADMIN, self.pid, "Estimate")
        with self.assertRaises(ValidationError):
            self.ext.add_estimate_line(ADMIN, est["id"], "x", 1, 10.5)
        with self.assertRaises(ValidationError):
            self.ext.add_estimate_line(ADMIN, est["id"], "x", 1, True)
        with self.assertRaises(ValidationError):
            self.ext.add_estimate_line(ADMIN, est["id"], "x", 0, 100)
        line = self.ext.add_estimate_line(ADMIN, est["id"], "ok", 1, 100)
        self.assertEqual(line["id"], "estl-1")


class TestAiReview(BatchFixture):
    """Entry: AI technical document review, UFGS checking &
    cited question-answering — built as review-request records
    plus result records holding opaque references only; no
    extracted text and no answer text exists."""

    def test_request_and_result_shapes(self):
        document = self.make_document()
        request = self.ext.create_review_request(
            OPERATOR, document["id"], "ufgs_check",
            model_label="specset-review")
        self.assertEqual(request["id"], "air-1")
        self.assertEqual(
            set(request.keys()),
            {"id", "document_id", "kind", "model_label", "question_ref",
             "reviewed_here", "created_by", "created_utc"})
        self.assertIs(request["reviewed_here"], False)
        result = self.ext.record_review_result(
            ADMIN, request["id"], "reported_noncompliant", "RESULT-REF-1")
        self.assertEqual(
            set(result.keys()),
            {"id", "request_id", "outcome_label", "result_ref",
             "answer_ref", "reviewed_here", "checked_here",
             "answered_here", "created_by", "created_utc"})
        self.assertIs(result["checked_here"], False)
        for record in (request, result):
            self.assertNotIn("extracted_text", _all_keys(record))
            self.assertNotIn("answer_text", _all_keys(record))
            self.assertNotIn("findings", _all_keys(record))

    def test_cited_qa_answer_held_as_ref_only(self):
        document = self.make_document()
        request = self.ext.create_review_request(
            ADMIN, document["id"], "cited_question_answering",
            question_ref="QUESTION-REF-9")
        result = self.ext.record_review_result(
            ADMIN, request["id"], "reported_answered", "RESULT-REF-2",
            answer_ref="ANSWER-REF-9")
        self.assertEqual(result["answer_ref"], "ANSWER-REF-9")
        self.assertIs(result["answered_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.create_review_request(
                ADMIN, document["id"], "sentiment_scan")


class TestDocumentControl(BatchFixture):
    """Entry: Document control platform depth — built as
    control + reported approval records over core documents;
    content is never held and approval currency is derived."""

    def test_control_shape_and_unique_per_document(self):
        document = self.make_document()
        control = self.ext.register_document_control(
            OPERATOR, document["id"], "controlled",
            register_ref="REG-1")
        self.assertEqual(control["id"], "dct-1")
        self.assertEqual(
            set(control.keys()),
            {"id", "document_id", "control_label", "register_ref",
             "content_held_here", "created_by", "created_utc"})
        self.assertIs(control["content_held_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_document_control(
                ADMIN, document["id"], "controlled-again")

    def test_current_approval_derived_latest_wins(self):
        document = self.make_document()
        control = self.ext.register_document_control(
            ADMIN, document["id"], "controlled")
        self.assertNotIn(
            "current_approval_label",
            self.ext.get_document_control(ADMIN, control["id"]))
        view = self.ext.document_control_view(ADMIN, control["id"])
        self.assertEqual(view["current_approval_label"], "recorded")
        self.ext.record_document_approval(
            ADMIN, control["id"], "reported_revise_resubmit",
            version_number=1)
        self.ext.record_document_approval(
            ADMIN, control["id"], "reported_approved", version_number=2)
        view = self.ext.document_control_view(ADMIN, control["id"])
        self.assertEqual(view["current_approval_label"],
                         "reported_approved")
        self.assertEqual(view["approval_count"], 2)
        self.assertEqual(view["document"]["id"], document["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_document_approval(
                ADMIN, control["id"], "approved")


class TestGis(BatchFixture):
    """Entry: GIS/spatial platform & asset location tracking —
    built as layer metadata with opaque geometry references
    plus reported location records; nothing is sensed."""

    def test_layer_shape_no_geometry_content(self):
        layer = self.ext.create_gis_layer(
            OPERATOR, self.pid, "Parcels", geometry_ref="GEO-REF-1",
            source_ref="COUNTY-GIS-2026")
        self.assertEqual(layer["id"], "gis-1")
        self.assertEqual(
            set(layer.keys()),
            {"id", "project_id", "label", "geometry_ref", "source_ref",
             "rendered_here", "created_by", "created_utc"})
        self.assertIs(layer["rendered_here"], False)
        self.assertNotIn("geometry", _all_keys(layer) - {"geometry_ref"})
        self.assertNotIn("coordinates", _all_keys(layer))

    def test_location_records_verbatim_standalone(self):
        layer = self.ext.create_gis_layer(ADMIN, self.pid, "Assets")
        record = self.ext.record_asset_location(
            OPERATOR, "ASSET-REF-1", "GRID 44.02 / -91.10 as reported",
            layer_id=layer["id"], project_id=self.pid)
        self.assertEqual(
            set(record.keys()),
            {"id", "asset_ref", "layer_id", "project_id",
             "reported_position_label", "reported_at", "tracked_here",
             "created_by", "created_utc"})
        self.assertIs(record["tracked_here"], False)
        self.assertNotIn("history", _all_keys(record))
        self.assertNotIn("trail", _all_keys(record))

    def test_layer_project_mismatch_rejected(self):
        layer = self.ext.create_gis_layer(ADMIN, self.pid, "Assets")
        other = self.store.create_project("Other Project", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_asset_location(
                ADMIN, "ASSET-REF-2", "P", layer_id=layer["id"],
                project_id=other["id"])


class TestPermitting(BatchFixture):
    """Entry: Permitting, licensing & right-of-way management —
    built as permit records with append-only reported states;
    the current state is derived at read, never stored, and the
    authority issues, not this build."""

    def test_permit_shape_no_stored_state(self):
        permit = self.make_permit()
        self.assertEqual(permit["id"], "prm-1")
        self.assertEqual(
            set(permit.keys()),
            {"id", "project_id", "kind", "title", "authority_label",
             "application_ref", "issued_here", "created_by",
             "created_utc"})
        self.assertIs(permit["issued_here"], False)
        self.assertNotIn("current_state",
                         self.ext.get_permit(ADMIN, permit["id"]))

    def test_current_state_is_latest_recorded_label(self):
        permit = self.make_permit()
        view = self.ext.permit_view(ADMIN, permit["id"])
        self.assertEqual(view["current_state"], "recorded")
        self.ext.record_permit_state(
            ADMIN, permit["id"], "reported_submitted")
        self.ext.record_permit_state(
            ADMIN, permit["id"], "reported_under_review")
        self.ext.record_permit_state(
            ADMIN, permit["id"], "reported_issued")
        view = self.ext.permit_view(ADMIN, permit["id"])
        self.assertEqual(view["current_state"], "reported_issued")
        self.assertEqual(view["state_count"], 3)
        with self.assertRaises(ValidationError):
            self.ext.record_permit_state(
                ADMIN, permit["id"], "issued")
        with self.assertRaises(ValidationError):
            self.ext.create_permit(ADMIN, self.pid, "easement", "X")


class TestPermitStateNegativeControl(BatchFixture):
    """Fresh negative control for the new code: the permit-state
    derivation seam :func:`_current_permit_state`. The canonical
    claim is that a permit's current state is its LATEST
    recorded reported-state label. The mutant reads the earliest
    label; treating its outcome as the expectation must fail."""

    STATES = [{"state_label": "reported_submitted"},
              {"state_label": "reported_under_review"},
              {"state_label": "reported_issued"}]

    def test_latest_canonical_but_mutant_not(self):
        self.assertEqual(_current_permit_state(self.STATES),
                         "reported_issued")
        self.assertEqual(_current_permit_state([]), "recorded")
        mutant = mutant_current_permit_state(self.STATES)
        self.assertNotEqual(mutant, "reported_issued")
        self.assertEqual(mutant, "reported_submitted")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, "reported_issued")

    def test_view_uses_the_seam(self):
        permit = self.make_permit()
        self.ext.record_permit_state(
            ADMIN, permit["id"], "reported_submitted")
        self.ext.record_permit_state(
            ADMIN, permit["id"], "reported_issued")
        view = self.ext.permit_view(ADMIN, permit["id"])
        self.assertEqual(view["current_state"], "reported_issued")
        states = self.ext.list_permit_states(ADMIN, permit["id"])
        self.assertNotEqual(
            view["current_state"],
            mutant_current_permit_state(states))


class TestAssetManagement(BatchFixture):
    """Entry: Asset management platform — built as asset
    records in the set's own records form, reported condition
    assessments (labels verbatim), capital-plan records held
    as data, and derived counts."""

    def test_asset_shape_and_unique_ref(self):
        asset = self.ext.register_asset(
            OPERATOR, "ASSET-REF-1", "hvac", project_id=self.pid,
            org_id=self.prime["id"], location_label="Roof")
        self.assertEqual(asset["id"], "ast-1")
        self.assertEqual(
            set(asset.keys()),
            {"id", "asset_ref", "kind_label", "project_id", "org_id",
             "location_label", "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.register_asset(ADMIN, "ASSET-REF-1", "hvac")

    def test_assessment_is_reported_label_only(self):
        asset = self.ext.register_asset(ADMIN, "ASSET-REF-1", "hvac")
        assessment = self.ext.record_condition_assessment(
            ADMIN, asset["id"], "reported_fair",
            assessed_by_ref="INSPECTOR-7")
        self.assertIs(assessment["assessed_here"], False)
        self.assertEqual(assessment["condition_label"], "reported_fair")
        with self.assertRaises(ValidationError):
            self.ext.record_condition_assessment(
                ADMIN, asset["id"], "fair")

    def test_capital_plan_and_summary_counts_derived(self):
        asset_a = self.ext.register_asset(
            ADMIN, "ASSET-REF-1", "hvac", project_id=self.pid)
        asset_b = self.ext.register_asset(
            ADMIN, "ASSET-REF-2", "elevator", project_id=self.pid)
        self.ext.record_condition_assessment(
            ADMIN, asset_a["id"], "reported_poor")
        self.ext.create_capital_plan(
            ADMIN, asset_a["id"], "replace compressor", "FY2028",
            estimate_ref="est-1")
        summary = self.ext.asset_summary(ADMIN, self.pid)
        self.assertEqual(summary["asset_count"], 2)
        self.assertEqual(summary["assets_by_kind"],
                         {"hvac": 1, "elevator": 1})
        self.assertEqual(summary["assessments_by_condition"],
                         {"reported_poor": 1})
        self.assertEqual(summary["capital_plan_count"], 1)
        plan = self.ext.list_capital_plans(ADMIN, asset_a["id"])[0]
        self.assertIs(plan["executed_here"], False)
        self.assertEqual(asset_b["kind_label"], "elevator")


class TestPrevailingWage(BatchFixture):
    """Entry: Prevailing-wage determination depth — built in
    the founding group's adjudicated form: rate tables as data,
    wage lines as recorded inputs, amounts derived exactly at
    read, certified-payroll reports derived, e-filing as a
    labeled reference. In this set the family is claimed in
    name only; the build is the records/arithmetic surface."""

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
        self.assertEqual(
            set(report.keys()),
            {"id", "project_id", "org_id", "period_label", "line_ids",
             "created_by", "created_utc"})
        view = self.ext.certified_payroll_view(ADMIN, report["id"])
        self.assertEqual(view["total_base_cents"], 36000)
        self.assertEqual(view["total_fringe_cents"], 6000)
        self.assertEqual(view["total_gross_cents"], 42000)
        self.assertEqual(view["worker_count"], 2)
        self.assertEqual(self.store.list_payrolls(ADMIN), [])

    def test_efiling_is_labeled_reference(self):
        table = self.make_rate_table()
        line = self.ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 60,
            "2026-W40")
        report = self.ext.generate_certified_payroll_report(
            ADMIN, self.pid, self.sub["id"], "2026-W40", [line["id"]])
        filing = self.ext.record_efiling(
            ADMIN, report["id"], "AGENCY-RECEIPT-1")
        self.assertIs(filing["reference_stub"], True)
        self.assertIs(filing["filed_here"], False)
        self.assertEqual(filing["state"], "recorded_reference_only")


class TestWorkflowStub(BatchFixture):
    """Entry: Workflow automation engines — labeled reference:
    definitions held as data; the registry never executes."""

    def test_definition_held_as_data_never_executed(self):
        definition = self.ext.create_workflow_definition(
            OPERATOR, "Submittal flow",
            ["draft", "submitted", "under_review", "approved"])
        self.assertEqual(
            set(definition.keys()),
            {"id", "label", "steps", "reference_stub", "executed_here",
             "state", "created_by", "created_utc"})
        self.assertIs(definition["reference_stub"], True)
        self.assertIs(definition["executed_here"], False)
        self.assertEqual(definition["state"], "recorded_reference_only")
        self.assertFalse(hasattr(self.ext, "run_workflow"))
        self.assertFalse(hasattr(self.ext, "execute_workflow"))
        outcome = self.ext.record_workflow_outcome(
            ADMIN, definition["id"], "reported_completed")
        self.assertIs(outcome["reference_stub"], True)
        self.assertIs(outcome["executed_here"], False)
        self.assertEqual(
            self.ext.get_workflow_definition(ADMIN, definition["id"]),
            definition)


class TestGuardsAndDiscipline(BatchFixture):
    """Cross-cutting: RBAC denial is audited and consumes no
    id; unexpected fields cannot be smuggled in."""

    def test_viewer_write_denied_audited_no_id_consumed(self):
        store, project, prime, sub = make_store()
        ext = ConstructExtensions(store)
        with self.assertRaises(PermissionDenied):
            ext.create_permit(VIEWER, project["id"], "permit", "Nope")
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("ext_permit_create:denied", actions)
        permit = ext.create_permit(ADMIN, project["id"], "permit", "Fine")
        self.assertEqual(permit["id"], "prm-1")

    def test_viewer_reads_allowed(self):
        permit = self.make_permit()
        self.assertEqual(
            self.ext.get_permit(VIEWER, permit["id"])["id"], permit["id"])

    def test_unexpected_kwarg_raises_typeerror(self):
        with self.assertRaises(TypeError):
            self.ext.create_estimate(
                ADMIN, self.pid, "T", smuggled_field="x")
        with self.assertRaises(TypeError):
            self.ext.record_review_result(
                ADMIN, "air-1", "reported_answered", "R-1",
                answer_text="the answer")


class TestTierNullAndShapeScan(BatchFixture):
    """Cross-cutting: tier null and shape discipline.

    Every extension record and derived view is scanned
    recursively: no key may name a tier, a baseline, or an
    equivalence; no value may be a float; no list may hold
    numbers. This set asserts no baseline anywhere, and the new
    surface is no exception.
    """

    FORBIDDEN_KEY_PARTS = ("tier", "cmmc", "baseline", "equivalence",
                           "impact_level")

    def _everything(self):
        ext = self.ext
        plan = ext.create_commissioning_plan(
            ADMIN, self.pid, "Cx", system_label="AHU-1")
        item = ext.add_checklist_item(
            ADMIN, plan["id"], "installation_checklist", "Install")
        outcome = ext.record_checklist_outcome(
            ADMIN, item["id"], "reported_passed")
        document = self.make_document()
        turnover = ext.record_turnover_package(
            ADMIN, plan["id"], "PKG-1", document_ids=[document["id"]])
        plan_view = ext.commissioning_plan_view(ADMIN, plan["id"])
        est = ext.create_estimate(
            ADMIN, self.pid, "E", cost_data_source_ref="BENCH-1")
        line = ext.add_estimate_line(ADMIN, est["id"], "conduit", 3, 250)
        est_view = ext.estimate_view(ADMIN, est["id"])
        request = ext.create_review_request(
            ADMIN, document["id"], "cited_question_answering",
            question_ref="Q-1")
        result = ext.record_review_result(
            ADMIN, request["id"], "reported_answered", "R-1",
            answer_ref="A-1")
        control = ext.register_document_control(
            ADMIN, document["id"], "controlled")
        approval = ext.record_document_approval(
            ADMIN, control["id"], "reported_approved", version_number=1)
        control_view = ext.document_control_view(ADMIN, control["id"])
        layer = ext.create_gis_layer(
            ADMIN, self.pid, "Parcels", geometry_ref="GEO-1")
        location = ext.record_asset_location(
            ADMIN, "ASSET-REF-1", "P-1", layer_id=layer["id"],
            project_id=self.pid)
        permit = self.make_permit()
        state = ext.record_permit_state(
            ADMIN, permit["id"], "reported_issued")
        permit_view = ext.permit_view(ADMIN, permit["id"])
        asset = ext.register_asset(
            ADMIN, "ASSET-REF-1", "hvac", project_id=self.pid)
        assessment = ext.record_condition_assessment(
            ADMIN, asset["id"], "reported_fair")
        capital = ext.create_capital_plan(
            ADMIN, asset["id"], "service", "FY2027")
        summary = ext.asset_summary(ADMIN, self.pid)
        table = self.make_rate_table()
        wage = ext.record_wage_line(
            ADMIN, self.pid, self.sub["id"], "W-1", table["id"], 480,
            "2026-W40")
        wage_view = ext.wage_line_view(ADMIN, wage["id"])
        report = ext.generate_certified_payroll_report(
            ADMIN, self.pid, self.sub["id"], "2026-W40", [wage["id"]])
        report_view = ext.certified_payroll_view(ADMIN, report["id"])
        filing = ext.record_efiling(ADMIN, report["id"], "RCPT-1")
        definition = ext.create_workflow_definition(
            ADMIN, "Flow", ["a", "b"])
        wf_outcome = ext.record_workflow_outcome(
            ADMIN, definition["id"], "reported_completed")
        return [plan, item, outcome, turnover, plan_view, est, line,
                est_view, request, result, control, approval,
                control_view, layer, location, permit, state,
                permit_view, asset, assessment, capital, summary,
                table, wage, wage_view, report, report_view, filing,
                definition, wf_outcome]

    def test_no_tier_shaped_key_no_float_no_numeric_list(self):
        for record in self._everything():
            for key, value in _walk(record):
                lowered = key.lower()
                for part in self.FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(
                        part, lowered,
                        "tier-shaped key %r in %r" % (key, record))
                self.assertNotIsInstance(
                    value, float,
                    "float value at %r in %r" % (key, record))
                if isinstance(value, list):
                    for entry in value:
                        self.assertNotIsInstance(
                            entry, (int, float),
                            "numeric list at %r in %r" % (key, record))
            self.assertFalse(_has_float(record), record.get("id"))

    def test_stub_records_carry_their_labels(self):
        records = self._everything()
        by_id = {r["id"]: r for r in records if "id" in r}
        for stub_id in ("efl-1", "wfd-1", "wfo-1"):
            self.assertIs(by_id[stub_id]["reference_stub"], True)
            self.assertEqual(by_id[stub_id]["state"],
                             "recorded_reference_only")

    def test_extension_surface_is_audited(self):
        self.ext.create_permit(ADMIN, self.pid, "permit", "Audited")
        self.assertIn("ext_permit_create", self.audit_actions())


if __name__ == "__main__":
    unittest.main()
