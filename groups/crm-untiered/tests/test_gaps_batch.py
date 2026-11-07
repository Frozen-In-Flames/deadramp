"""Final GAPS batch extension tests -- Untiered Set 23 (CRM).

Traces to: the 4 open Extended entries of this set's GAPS.md
section (inventory idx 943-946) and their dispositions in
``BATCH.md`` -- all four close as labeled reference
implementations; idx 943 and 944 are re-judged from their drafted
build-extension dispositions, with grounds in ``BATCH.md``.
Every test names the entry it pins. The fresh mutation-verified
negative control for the new code is
``TestNegativeControlConnectorRollup`` (the drill record is in
tests/README.md); the group's founding control (breach
derivation) is untouched in test_negative_control.py.

Tier discipline pins: this set is untiered (the sheet's
``cmmc_tier`` is null and its impact level "Unknown", pinned in
test_specs.py); the scans below pin that the extension surface
adds no tier-, baseline-, or score-shaped key anywhere.
"""

import unittest

from crm.audit import AuditLog
from crm.errors import NotFoundError, PermissionDenied, ValidationError
from crm.extensions import CrmExtensions, SCORE_KEYS
from crm_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store

FIXED_NOW = "2030-01-01T00:00:00+00:00"

# Substrings that would make a key tier- or posture-shaped. At
# tier null the extension asserts no baseline, no impact level,
# and no equivalence, so none of these may appear in any key on
# the extension surface.
TIER_KEY_PARTS = ("tier", "baseline", "cmmc", "fedramp", "impact",
                  "equivalence")
PERSONAL_KEYS = frozenset({
    "name", "email", "phone", "ssn", "dob", "address", "salary",
})


def make_ext():
    store, account, contact = make_store()
    return CrmExtensions(store), store, account, contact


def scan_keys(case, value):
    """Recursively assert no score-, tier-, or personal-data key."""
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            case.assertNotIn(lowered, SCORE_KEYS)
            case.assertNotIn(lowered, PERSONAL_KEYS)
            case.assertNotIn("score", lowered)
            for part in TIER_KEY_PARTS:
                case.assertNotIn(part, lowered)
            scan_keys(case, item)
    elif isinstance(value, list):
        for item in value:
            scan_keys(case, item)


class TestProposalGeneration(unittest.TestCase):
    """Idx 943: AI proposal-generation engine (reference form)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_request_record_shape_and_labels(self):
        req = self.ext.register_proposal_request(
            OPERATOR, "proposal-model-1", "Draft the Q3 proposal",
            account_id=self.account["id"])
        self.assertEqual(req["id"], "prop-1")
        self.assertEqual(
            set(req.keys()),
            {"id", "model_ref", "purpose", "account_id", "case_id",
             "reference_stub", "inference_here", "generated_here",
             "state", "created_by", "created_utc"})
        self.assertTrue(req["reference_stub"])
        self.assertFalse(req["inference_here"])
        self.assertFalse(req["generated_here"])
        self.assertEqual(req["state"], "recorded_request_only")

    def test_signature_refuses_generated_content(self):
        # There is no parameter that could carry a prompt, a draft,
        # or generated text into this build.
        with self.assertRaises(TypeError):
            self.ext.register_proposal_request(
                OPERATOR, "m", "p", content="dear reviewer")
        with self.assertRaises(TypeError):
            self.ext.register_proposal_request(
                OPERATOR, "m", "p", prompt="write a proposal")
        with self.assertRaises(TypeError):
            self.ext.record_proposal_report(
                OPERATOR, "prop-1", "done", proposal_text="body")

    def test_request_bindings_must_exist_and_agree(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_proposal_request(
                OPERATOR, "m", "p", account_id="acct-99")
        case = self.store.create_case(
            OPERATOR, "general", "Renewal", account_id=self.account["id"])
        other = self.store.create_account(ADMIN, "ACCT-200")
        with self.assertRaises(ValidationError):
            self.ext.register_proposal_request(
                OPERATOR, "m", "p", account_id=other["id"],
                case_id=case["id"])
        req = self.ext.register_proposal_request(
            OPERATOR, "m", "p", account_id=self.account["id"],
            case_id=case["id"])
        self.assertEqual(req["case_id"], case["id"])

    def test_report_names_proposal_by_reference_only(self):
        req = self.ext.register_proposal_request(OPERATOR, "m", "p")
        rep = self.ext.record_proposal_report(
            OPERATOR, req["id"], "reported_drafted",
            proposal_ref="docstore://proposals/991")
        self.assertEqual(rep["id"], "proprep-1")
        self.assertEqual(
            set(rep.keys()),
            {"id", "request_id", "outcome_label", "proposal_ref",
             "reference_stub", "proposal_held_here", "generated_here",
             "created_by", "created_utc"})
        self.assertEqual(rep["outcome_label"], "reported_drafted")
        self.assertFalse(rep["proposal_held_here"])
        with self.assertRaises(NotFoundError):
            self.ext.record_proposal_report(OPERATOR, "prop-99", "x")

    def test_score_shaped_outcome_label_refused(self):
        req = self.ext.register_proposal_request(OPERATOR, "m", "p")
        with self.assertRaises(ValidationError):
            self.ext.record_proposal_report(OPERATOR, req["id"], "score")

    def test_evaluation_figures_are_reported_verbatim(self):
        ev = self.ext.record_proposal_evaluation(
            OPERATOR, "proposal-model-1", "acceptance_count", 12)
        self.assertEqual(ev["metric_value"], 12)
        self.assertFalse(ev["computed_here"])
        ev2 = self.ext.record_proposal_evaluation(
            OPERATOR, "proposal-model-1", "reviewer_verdict", "usable")
        self.assertEqual(ev2["metric_value"], "usable")
        with self.assertRaises(ValidationError):
            self.ext.record_proposal_evaluation(
                OPERATOR, "m", "rate", 0.5)
        with self.assertRaises(ValidationError):
            self.ext.record_proposal_evaluation(
                OPERATOR, "m", "flag", True)

    def test_surface_creates_no_core_records(self):
        before = self.store.report(ADMIN, now=FIXED_NOW)
        req = self.ext.register_proposal_request(
            OPERATOR, "m", "p", account_id=self.account["id"])
        self.ext.record_proposal_report(OPERATOR, req["id"], "done")
        self.ext.record_proposal_evaluation(OPERATOR, "m", "n", 1)
        after = self.store.report(ADMIN, now=FIXED_NOW)
        self.assertEqual(before, after)

    def test_viewer_cannot_write(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_proposal_request(VIEWER, "m", "p")


class TestPipelineForecasting(unittest.TestCase):
    """Idx 944: Pipeline forecasting engine (reference form)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_request_record_shape_and_labels(self):
        req = self.ext.register_forecast_request(
            OPERATOR, "forecast-engine-1", "PIPE-77",
            account_id=self.account["id"])
        self.assertEqual(req["id"], "fcreq-1")
        self.assertEqual(
            set(req.keys()),
            {"id", "engine_ref", "pipeline_ref", "account_id",
             "reference_stub", "computed_here", "state",
             "created_by", "created_utc"})
        self.assertTrue(req["reference_stub"])
        self.assertFalse(req["computed_here"])
        self.assertEqual(req["state"], "recorded_request_only")

    def test_no_pipeline_record_is_created(self):
        # Opportunities & sales pipeline is a named absence in this
        # set: the surface names a pipeline by opaque reference
        # only, and nothing in it creates a pipeline or opportunity
        # record of any kind.
        self.ext.register_forecast_request(OPERATOR, "e", "PIPE-1")
        kinds = set(self.ext.extension_summary(ADMIN)["by_kind"])
        self.assertEqual(kinds, {"forecast_request"})
        self.assertFalse(hasattr(self.ext, "create_opportunity"))
        self.assertFalse(hasattr(self.ext, "create_pipeline"))
        with self.assertRaises(TypeError):
            self.ext.register_forecast_request(
                OPERATOR, "e", "PIPE-1", figure_value=100)

    def test_report_and_figure_are_reported_data(self):
        req = self.ext.register_forecast_request(OPERATOR, "e", "PIPE-1")
        rep = self.ext.record_forecast_report(
            OPERATOR, req["id"], "reported_ready",
            forecast_ref="fcache://runs/12")
        self.assertFalse(rep["forecast_held_here"])
        self.assertFalse(rep["computed_here"])
        fig = self.ext.record_forecast_figure(
            OPERATOR, req["id"], "next_quarter_cents", 4200000)
        self.assertEqual(fig["figure_value"], 4200000)
        self.assertFalse(fig["computed_here"])
        fig2 = self.ext.record_forecast_figure(
            OPERATOR, req["id"], "engine_note", "seasonal uplift claimed")
        self.assertEqual(fig2["figure_value"], "seasonal uplift claimed")

    def test_figures_reject_floats_and_bools(self):
        req = self.ext.register_forecast_request(OPERATOR, "e", "PIPE-1")
        with self.assertRaises(ValidationError):
            self.ext.record_forecast_figure(OPERATOR, req["id"], "x", 1.5)
        with self.assertRaises(ValidationError):
            self.ext.record_forecast_figure(OPERATOR, req["id"], "x", True)
        with self.assertRaises(NotFoundError):
            self.ext.record_forecast_figure(OPERATOR, "fcreq-99", "x", 1)

    def test_summary_is_counts_only(self):
        req = self.ext.register_forecast_request(OPERATOR, "e", "PIPE-1")
        self.ext.record_forecast_report(OPERATOR, req["id"], "ready")
        self.ext.record_forecast_report(OPERATOR, req["id"], "ready")
        self.ext.record_forecast_figure(OPERATOR, req["id"], "cents", 5)
        summary = self.ext.forecast_summary(ADMIN)
        self.assertEqual(summary["method"], "recorded_forecast_counts")
        self.assertEqual(summary["requests"], 1)
        self.assertEqual(summary["reports"], 2)
        self.assertEqual(summary["figures"], 1)
        self.assertEqual(summary["by_outcome"], {"ready": 2})
        self.assertEqual(summary["by_figure_label"], {"cents": 1})
        # The recorded figure value itself is never summed or
        # projected into the summary.
        scan_keys(self, summary)


class TestDocumentAutomation(unittest.TestCase):
    """Idx 945: Document automation engine (reference form)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def test_template_held_as_data(self):
        tmpl = self.ext.register_document_template(
            ADMIN, "Proposal shell", "TMPL-PROPOSAL",
            definition_text="Dear {name}, ...")
        self.assertEqual(tmpl["id"], "dtmpl-1")
        self.assertEqual(tmpl["definition_text"], "Dear {name}, ...")
        self.assertTrue(tmpl["reference_stub"])
        self.assertFalse(tmpl["rendered_here"])
        self.assertFalse(tmpl["executed_here"])
        with self.assertRaises(ValidationError):
            self.ext.register_document_template(
                ADMIN, "Duplicate", "TMPL-PROPOSAL")

    def test_template_surface_is_admin_only(self):
        # Templates bind configuration: config_write, as in the core.
        with self.assertRaises(PermissionDenied):
            self.ext.register_document_template(OPERATOR, "T", "TMPL-1")
        tmpl = self.ext.register_document_template(ADMIN, "T", "TMPL-1")
        with self.assertRaises(PermissionDenied):
            self.ext.request_document_automation(OPERATOR, tmpl["id"])

    def test_request_snapshots_template_and_holds_parameters_as_data(self):
        tmpl = self.ext.register_document_template(
            ADMIN, "Proposal shell", "TMPL-PROPOSAL")
        req = self.ext.request_document_automation(
            ADMIN, tmpl["id"],
            parameters={"audience": "reviewers", "copies": 2},
            account_id=self.account["id"])
        self.assertEqual(req["id"], "docreq-1")
        self.assertEqual(req["template_ref"], "TMPL-PROPOSAL")
        self.assertEqual(req["parameters"],
                         {"audience": "reviewers", "copies": 2})
        self.assertFalse(req["generated_here"])
        self.assertFalse(req["automated_here"])
        self.assertEqual(req["state"], "recorded_request_only")

    def test_parameters_reject_floats_scores_and_nesting(self):
        tmpl = self.ext.register_document_template(ADMIN, "T", "TMPL-1")
        with self.assertRaises(ValidationError):
            self.ext.request_document_automation(
                ADMIN, tmpl["id"], parameters={"ratio": 0.5})
        with self.assertRaises(ValidationError):
            self.ext.request_document_automation(
                ADMIN, tmpl["id"], parameters={"score": 3})
        with self.assertRaises(ValidationError):
            self.ext.request_document_automation(
                ADMIN, tmpl["id"], parameters={"nested": {"a": 1}})

    def test_report_vocabulary_and_reference_only_document(self):
        tmpl = self.ext.register_document_template(ADMIN, "T", "TMPL-1")
        req = self.ext.request_document_automation(ADMIN, tmpl["id"])
        rep = self.ext.record_document_report(
            ADMIN, req["id"], "reported_completed",
            document_ref="docstore://docs/7")
        self.assertEqual(
            set(rep.keys()),
            {"id", "request_id", "outcome", "document_ref",
             "reference_stub", "document_held_here", "generated_here",
             "created_by", "created_utc"})
        self.assertFalse(rep["document_held_here"])
        with self.assertRaises(ValidationError):
            self.ext.record_document_report(ADMIN, req["id"], "completed")
        with self.assertRaises(TypeError):
            self.ext.record_document_report(
                ADMIN, req["id"], "reported_completed",
                document_text="the generated body")

    def test_request_and_report_leave_bound_case_untouched(self):
        case = self.store.create_case(
            OPERATOR, "request", "Assemble the packet",
            account_id=self.account["id"])
        before = self.store.get_case(case["id"], now=FIXED_NOW)
        tmpl = self.ext.register_document_template(ADMIN, "T", "TMPL-1")
        req = self.ext.request_document_automation(
            ADMIN, tmpl["id"], account_id=self.account["id"],
            case_id=case["id"])
        self.ext.record_document_report(
            ADMIN, req["id"], "reported_completed")
        after = self.store.get_case(case["id"], now=FIXED_NOW)
        self.assertEqual(before, after)


class TestConnectorEngines(unittest.TestCase):
    """Idx 946: Integration connector engines (reference form)."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def _catalog_fixture(self):
        self.ext.record_connector_sync(ADMIN, "ext-crm", "inbound", 3)
        self.ext.record_connector_sync(ADMIN, "ext-crm", "outbound", 2)
        self.ext.record_connector_sync(ADMIN, "ext-crm", "inbound", 4)
        self.ext.record_connector_sync(ADMIN, "ext-erp", "inbound", 7)

    def test_connector_definition_record(self):
        conn = self.ext.register_connector(ADMIN, "ext-crm", label="CRM hub")
        self.assertEqual(conn["id"], "conn-1")
        self.assertEqual(
            set(conn.keys()),
            {"id", "connector_ref", "label", "reference_stub",
             "reference_transport", "connected_here",
             "created_by", "created_utc"})
        self.assertTrue(conn["reference_transport"])
        self.assertFalse(conn["connected_here"])
        with self.assertRaises(ValidationError):
            self.ext.register_connector(ADMIN, "ext-crm")
        with self.assertRaises(PermissionDenied):
            self.ext.register_connector(OPERATOR, "ext-other")

    def test_sync_receipt_labels_and_binding(self):
        sync = self.ext.record_connector_sync(
            ADMIN, "ext-crm", "inbound", 5,
            target_kind="account", target_id=self.account["id"])
        self.assertEqual(sync["id"], "csync-1")
        self.assertTrue(sync["reference_stub"])
        self.assertTrue(sync["reference_transport"])
        self.assertFalse(sync["transmitted_here"])
        self.assertFalse(sync["synced_here"])
        self.assertEqual(sync["records_reported"], 5)

    def test_sync_target_must_exist_and_stays_untouched(self):
        module = self.store.create_module(ADMIN, "M", "cases", "a=b")
        before = self.store.get_module(module["id"])
        self.ext.record_connector_sync(
            ADMIN, "ext-crm", "outbound", 1,
            target_kind="module", target_id=module["id"])
        self.assertEqual(before, self.store.get_module(module["id"]))
        with self.assertRaises(NotFoundError):
            self.ext.record_connector_sync(
                ADMIN, "ext-crm", "inbound", 1,
                target_kind="account", target_id="acct-99")
        with self.assertRaises(ValidationError):
            self.ext.record_connector_sync(
                ADMIN, "ext-crm", "inbound", -1)
        with self.assertRaises(ValidationError):
            self.ext.record_connector_sync(
                ADMIN, "ext-crm", "inbound", 1, target_kind="account")

    def test_catalog_rollup_is_derived(self):
        self._catalog_fixture()
        catalog = self.ext.connector_catalog(ADMIN)
        self.assertEqual(catalog["method"], "recorded_sync_counts")
        self.assertEqual(catalog["total_syncs"], 4)
        self.assertEqual(catalog["total_records_reported"], 16)
        self.assertEqual(
            catalog["connectors"],
            [{"connector_ref": "ext-crm", "syncs": 3,
              "records_reported_total": 9,
              "by_direction": {"inbound": 2, "outbound": 1}},
             {"connector_ref": "ext-erp", "syncs": 1,
              "records_reported_total": 7,
              "by_direction": {"inbound": 1}}])


class TestExtensionInvariants(unittest.TestCase):
    """Cross-cutting pins: audit, rollback, labels, tier null,
    no scores, no personal-data shapes."""

    def setUp(self):
        self.ext, self.store, self.account, self.contact = make_ext()

    def _exercise_all(self):
        req = self.ext.register_proposal_request(
            OPERATOR, "m", "p", account_id=self.account["id"])
        self.ext.record_proposal_report(OPERATOR, req["id"], "done")
        self.ext.record_proposal_evaluation(OPERATOR, "m", "n", 3)
        freq = self.ext.register_forecast_request(
            OPERATOR, "e", "PIPE-1", account_id=self.account["id"])
        self.ext.record_forecast_report(OPERATOR, freq["id"], "ready")
        self.ext.record_forecast_figure(OPERATOR, freq["id"], "cents", 9)
        tmpl = self.ext.register_document_template(ADMIN, "T", "TMPL-1")
        dreq = self.ext.request_document_automation(ADMIN, tmpl["id"])
        self.ext.record_document_report(
            ADMIN, dreq["id"], "reported_noop")
        self.ext.register_connector(ADMIN, "ext-crm")
        self.ext.record_connector_sync(ADMIN, "ext-crm", "inbound", 2)
        return req

    def test_mutations_and_denials_are_audited(self):
        self.ext.register_proposal_request(OPERATOR, "m", "p")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_proposal_request_register", actions)
        with self.assertRaises(PermissionDenied):
            self.ext.register_proposal_request(VIEWER, "m", "p")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_proposal_request_register:denied", actions)

    def test_failed_audit_write_rolls_back(self):
        class FailingAudit:
            def record(self, *args, **kwargs):
                raise RuntimeError("audit unavailable")

        good_audit = self.store.audit
        self.store.audit = FailingAudit()
        try:
            with self.assertRaises(RuntimeError):
                self.ext.register_connector(ADMIN, "ext-crm")
        finally:
            self.store.audit = good_audit
        # Nothing landed and no id was consumed.
        self.assertEqual(self.ext.list_connectors(), [])
        conn = self.ext.register_connector(ADMIN, "ext-crm")
        self.assertEqual(conn["id"], "conn-1")

    def test_every_record_is_a_labeled_reference_record(self):
        self._exercise_all()
        self.assertTrue(self.ext._records)
        for record in self.ext._records.values():
            self.assertTrue(record["reference_stub"], record["id"])

    def test_no_score_tier_or_personal_key_anywhere(self):
        self._exercise_all()
        for record in self.ext._records.values():
            scan_keys(self, record)
        scan_keys(self, self.ext.forecast_summary(ADMIN))
        scan_keys(self, self.ext.connector_catalog(ADMIN))
        scan_keys(self, self.ext.extension_summary(ADMIN))

    def test_extension_summary_counts(self):
        self._exercise_all()
        summary = self.ext.extension_summary(ADMIN)
        self.assertEqual(summary["by_kind"]["proposal_request"], 1)
        self.assertEqual(summary["by_kind"]["forecast_figure"], 1)
        self.assertEqual(summary["by_kind"]["document_template"], 1)
        self.assertEqual(summary["by_kind"]["connector_sync"], 1)
        self.assertEqual(summary["total"], 11)


class MutantCrmExtensions(CrmExtensions):
    """The batch's fresh negative-control mutant.

    Overrides the single derivation point for the connector
    catalog -- ``_sync_rollup`` returns nothing: an implementation
    that never accumulates recorded sync receipts must NOT
    produce the canonical catalog rollup.
    """

    def _sync_rollup(self, syncs):
        return {}


class TestNegativeControlConnectorRollup(unittest.TestCase):
    """Fresh negative control: connector catalog derivation.

    Traced claim: the connector catalog's per-connector rollup is
    DERIVED at read from the recorded sync receipts -- receipt
    counts, sums of the connectors' own reported record counts,
    and counts by direction.
    """

    EXPECTED = [
        {"connector_ref": "ext-crm", "syncs": 3,
         "records_reported_total": 9,
         "by_direction": {"inbound": 2, "outbound": 1}},
        {"connector_ref": "ext-erp", "syncs": 1,
         "records_reported_total": 7,
         "by_direction": {"inbound": 1}},
    ]

    def _fixture(self, ext_cls):
        store = fresh_store(audit=AuditLog())
        ext = ext_cls(store)
        ext.record_connector_sync(ADMIN, "ext-crm", "inbound", 3)
        ext.record_connector_sync(ADMIN, "ext-crm", "outbound", 2)
        ext.record_connector_sync(ADMIN, "ext-crm", "inbound", 4)
        ext.record_connector_sync(ADMIN, "ext-erp", "inbound", 7)
        return ext

    def test_canonical_rollup_but_mutant_does_not(self):
        canonical = self._fixture(CrmExtensions).connector_catalog(ADMIN)
        self.assertEqual(canonical["connectors"], self.EXPECTED)
        mutant = self._fixture(MutantCrmExtensions).connector_catalog(ADMIN)
        self.assertEqual(mutant["connectors"], [])
        self.assertNotEqual(mutant["connectors"], canonical["connectors"])
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant["connectors"], self.EXPECTED)


if __name__ == "__main__":
    unittest.main()
