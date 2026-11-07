"""Final GAPS batch — Group 20 (CMS L2) extension surface.

Traces to: the ten open Extended families in ``../UNION-SPEC.md``
("Gaps — specified, not implemented") as closed by
``../src/cms/extensions.py`` under the ratified batch triage
(``../../gaps-batch/DECISION.md``) — see ``../BATCH.md`` for the
per-entry dispositions. Build-extension entries are pinned in
their records forms (definition records, reported counts,
derived-at-read state, decisions under separation of duties);
stub-engine entries are pinned as labeled reference
implementations (``reference_stub: True`` plus each family's
not-here flag False). The batch's fresh negative control is the
case-decision separation-of-duties seam (last test class).
"""

import unittest

from cms.audit import AuditLog
from cms.errors import NotFoundError, PermissionDenied, ValidationError
from cms.extensions import CmsExtensions

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER
from cms_helpers import make_item, make_store


class BatchFixture(unittest.TestCase):
    """Fresh store + canonical site/section + extension register."""

    def setUp(self):
        self.audit = AuditLog()
        self.store, self.site, self.section = make_store(audit=self.audit)
        self.ext = CmsExtensions(self.store)

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]


class TestTemplates(BatchFixture):
    """Rendering & templating (build): definition records, never rendered."""

    def test_template_shape_labels_and_derived_placeholders(self):
        view = self.ext.create_template(
            PUBLISHER, "Landing", "Hello {{ name }}, see {{ title }}")
        self.assertEqual(view["id"], "tpl-1")
        self.assertIs(view["rendered_here"], False)
        self.assertEqual(view["placeholder_names"], ["name", "title"])
        self.assertEqual(view["version_count"], 1)
        stored = self.ext._templates["tpl-1"]
        self.assertEqual(
            set(stored.keys()),
            {"id", "name", "kind", "body", "version", "history",
             "rendered_here", "created_by", "created_utc", "updated_utc"})
        self.assertNotIn("placeholder_names", stored)

    def test_template_update_versions_prior_body(self):
        self.ext.create_template(PUBLISHER, "T", "one {{ a }}")
        view = self.ext.update_template(PUBLISHER, "tpl-1", "two {{ b }}")
        self.assertEqual(view["version"], 2)
        self.assertEqual(view["placeholder_names"], ["b"])
        self.assertEqual(view["history"][0]["body"], "one {{ a }}")

    def test_template_validation_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.create_template(PUBLISHER, "T", "x", kind="widget")
        with self.assertRaises(ValidationError):
            self.ext.create_template(PUBLISHER, "  ", "x")
        view = self.ext.create_template(PUBLISHER, "T", "x")
        self.assertEqual(view["id"], "tpl-1")

    def test_template_write_denied_for_editor(self):
        # editor holds no type_write in the founding matrix
        with self.assertRaises(PermissionDenied):
            self.ext.create_template(EDITOR, "T", "x")
        self.assertIn("ext_template_create:denied", self.audit_actions())


class TestEditorConfigs(BatchFixture):
    """WYSIWYG editors (build): configuration records as data."""

    def test_editor_config_shape_and_deep_copy(self):
        settings = {"toolbar": ["bold"]}
        record = self.ext.create_editor_config(
            ADMIN, "Rich text", "wysiwyg", settings)
        self.assertEqual(record["id"], "edc-1")
        self.assertIs(record["rendered_here"], False)
        settings["toolbar"].append("italic")
        again = self.ext.get_editor_config("edc-1", actor=ADMIN)
        self.assertEqual(again["settings"], {"toolbar": ["bold"]})

    def test_editor_config_update_versions(self):
        self.ext.create_editor_config(ADMIN, "E", "wysiwyg", {"a": 1})
        updated = self.ext.update_editor_config(ADMIN, "edc-1", {"a": 2})
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["history"][0]["settings"], {"a": 1})


class TestIngestion(BatchFixture):
    """Bulk ingestion & index-in-place (build): reported counts, no content."""

    def test_ingestion_batch_exact_shape(self):
        record = self.ext.create_ingestion_batch(
            EDITOR, "Nightly load", "repo-main", 1200, ["sha256:abc"])
        self.assertEqual(
            set(record.keys()),
            {"id", "name", "source_ref", "documents_reported",
             "checksum_refs", "content_held", "created_by", "created_utc"})
        self.assertIs(record["content_held"], False)
        self.assertEqual(record["documents_reported"], 1200)

    def test_ingestion_count_validation_consumes_no_id(self):
        for bad in (True, -1, 2.5, "12"):
            with self.assertRaises(ValidationError):
                self.ext.create_ingestion_batch(EDITOR, "B", "src", bad)
        record = self.ext.create_ingestion_batch(EDITOR, "B", "src", 3)
        self.assertEqual(record["id"], "ing-1")

    def test_index_declaration_and_derived_summary(self):
        self.ext.create_ingestion_batch(EDITOR, "B1", "src", 10)
        self.ext.create_ingestion_batch(EDITOR, "B2", "src", 5, ["r1", "r2"])
        decl = self.ext.create_index_declaration(
            EDITOR, "In place", "repo-main", ["title", "body"])
        self.assertIs(decl["indexing_performed_here"], False)
        summary = self.ext.ingestion_summary(actor=ADMIN)
        self.assertEqual(summary["batch_count"], 2)
        self.assertEqual(summary["documents_reported_total"], 15)
        self.assertEqual(summary["checksum_ref_count"], 2)
        self.assertEqual(summary["index_declaration_count"], 1)
        self.assertIs(summary["content_held"], False)


class TestLoans(BatchFixture):
    """Library ILS circulation (build): recorded states, derived current."""

    def test_loan_current_state_derived_not_stored(self):
        view = self.ext.record_loan(EDITOR, "patron-7", "item-9")
        self.assertEqual(view["current_state"], "checked_out")
        self.assertEqual(view["event_count"], 1)
        stored = self.ext._loans["loan-1"]
        self.assertEqual(
            set(stored.keys()),
            {"id", "patron_ref", "item_ref", "events",
             "created_by", "created_utc"})
        self.assertNotIn("current_state", stored)

    def test_loan_events_advance_derived_state(self):
        self.ext.record_loan(EDITOR, "patron-7", "item-9")
        self.ext.record_loan_event(EDITOR, "loan-1", "renewed")
        view = self.ext.record_loan_event(EDITOR, "loan-1", "checked_in")
        self.assertEqual(view["current_state"], "checked_in")
        self.assertEqual(view["event_count"], 3)

    def test_loan_validation_and_unknown(self):
        with self.assertRaises(ValidationError):
            self.ext.record_loan(EDITOR, " ", "item-9")
        with self.assertRaises(NotFoundError):
            self.ext.record_loan_event(EDITOR, "loan-99", "renewed")


class TestCatalogRecords(BatchFixture):
    """MARC21 cataloging depth (build): field records held as data."""

    def test_catalog_fields_held_as_data_deep_copied(self):
        fields = [{"tag": "245", "value": "Some title"},
                  {"tag": "020", "value": "123"}]
        record = self.ext.create_catalog_record(EDITOR, "item-9", fields)
        self.assertIs(record["discovery_engine_here"], False)
        fields.append({"tag": "999", "value": "mutated"})
        again = self.ext.get_catalog_record("cat-1", actor=EDITOR)
        self.assertEqual(len(again["fields"]), 2)

    def test_catalog_field_shape_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_catalog_record(EDITOR, "i", [{"tag": "245"}])
        with self.assertRaises(ValidationError):
            self.ext.create_catalog_record(
                EDITOR, "i", [{"tag": "245", "value": "x", "extra": 1}])
        with self.assertRaises(ValidationError):
            self.ext.create_catalog_record(EDITOR, "i", [])

    def test_discovery_remains_core_literal_search(self):
        make_item(self.store, self.site)
        result = self.store.search(AUTHOR, "hello")
        self.assertEqual(len(result["items"]), 1)
        # literal, not an indexing engine: regex metacharacters are text
        result = self.store.search(AUTHOR, "h.llo")
        self.assertEqual(result["items"], [])
        # catalog field values are data, never parsed into discovery
        self.ext.create_catalog_record(
            EDITOR, "item-9", [{"tag": "245", "value": "Zebra title"}])
        result = self.store.search(AUTHOR, "zebra")
        self.assertEqual(result["items"], [])


class TestAcquisitions(BatchFixture):
    """EDI acquisitions (build): integer-cent order data, never sent."""

    def test_acquisition_order_exact_shape(self):
        record = self.ext.create_acquisition_order(
            EDITOR, "supplier-3", "item-9", 259900)
        self.assertEqual(
            set(record.keys()),
            {"id", "supplier_ref", "item_ref", "amount_cents",
             "state_label", "transmitted_here", "created_by", "created_utc"})
        self.assertIs(record["transmitted_here"], False)
        self.assertEqual(record["amount_cents"], 259900)

    def test_acquisition_money_validation_consumes_no_id(self):
        for bad in (10.5, True, -5, "100"):
            with self.assertRaises(ValidationError):
                self.ext.create_acquisition_order(EDITOR, "s", "i", bad)
        record = self.ext.create_acquisition_order(EDITOR, "s", "i", 100)
        self.assertEqual(record["id"], "acq-1")


class TestCases(BatchFixture):
    """BPM / case management (build): records only, no content field."""

    def test_case_record_exact_keys_no_content_field(self):
        view = self.ext.open_case(EDITOR, "EEO-2026-014", "subj-88", "eeo")
        stored = self.ext._cases["case-1"]
        self.assertEqual(
            set(stored.keys()),
            {"id", "case_ref", "subject_ref", "case_type", "opened_by",
             "created_utc", "events"})
        for forbidden in ("body", "content", "notes", "narrative",
                          "description", "evidence", "evidence_text",
                          "complaint", "details"):
            self.assertNotIn(forbidden, stored)
        self.assertEqual(view["current_state"], "opened")
        self.assertNotIn("current_state", stored)

    def test_case_events_and_decision_flow(self):
        self.ext.open_case(EDITOR, "IG-7", "subj-1", "ig_casework")
        view = self.ext.record_case_event(EDITOR, "case-1", "under_review")
        self.assertEqual(view["current_state"], "under_review")
        decision = self.ext.record_case_decision(
            PUBLISHER, "case-1", "closed_no_action")
        self.assertIs(decision["adjudicated_here"], False)
        view = self.ext.case_view("case-1", actor=EDITOR)
        self.assertEqual(view["decision_count"], 1)

    def test_case_type_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.open_case(EDITOR, "X-1", "subj-1", "criminal")


class MutantExtensions(CmsExtensions):
    """Negative-control mutant: the decider guard waves through."""

    def _check_decider_not_opener(self, case, actor):
        return None


class TestDeciderNotOpenerNegativeControl(BatchFixture):
    """Fresh negative control: decider is never the case's opener.

    Traced claim (BPM / case-management family; control family
    AC-5, separation of duties): a case's decision is recorded
    only by someone other than the user who opened the case.
    Three legs, mirroring the core negative control's form: the
    canonical expectation holds on the real implementation, the
    mutant would NOT produce it, and treating the mutant's
    outcome as the expectation fails.
    """

    def test_opener_decision_denied_canonical_but_mutant_allows(self):
        case = self.ext.open_case(EDITOR, "EEO-1", "subj-9", "eeo")
        with self.assertRaises(PermissionDenied):
            self.ext.record_case_decision(EDITOR, case["id"], "sustained")
        # the denial consumed no decision id and recorded nothing
        self.assertEqual(self.ext.list_case_decisions(actor=ADMIN), [])
        decision = self.ext.record_case_decision(
            PUBLISHER, case["id"], "sustained")
        self.assertEqual(decision["id"], "dec-1")
        mutant = MutantExtensions(self.store)
        mcase = mutant.open_case(EDITOR, "EEO-2", "subj-9", "eeo")
        allowed = mutant.record_case_decision(EDITOR, mcase["id"], "x")
        self.assertEqual(allowed["decided_by"], "carol")

    def test_mutant_outcome_as_expectation_fails(self):
        mutant = MutantExtensions(self.store)
        mcase = mutant.open_case(EDITOR, "EEO-3", "subj-9", "eeo")
        with self.assertRaises(AssertionError):
            with self.assertRaises(PermissionDenied):
                mutant.record_case_decision(EDITOR, mcase["id"], "x")

    def test_denial_is_audited(self):
        case = self.ext.open_case(EDITOR, "EEO-4", "subj-9", "eeo")
        with self.assertRaises(PermissionDenied):
            self.ext.record_case_decision(EDITOR, case["id"], "x")
        self.assertIn("ext_case_decision:denied", self.audit_actions())


class TestPersonalization(BatchFixture):
    """Personalization (build): derived matching, no optimization."""

    def _segment_and_subjects(self):
        segment = self.ext.create_segment(EDITOR, "EU gold", [
            {"key": "region", "op": "equals", "value": "eu"},
            {"key": "tier", "op": "present"},
        ])
        self.ext.record_subject_attributes(
            EDITOR, "subj-a", {"region": "eu", "tier": "gold"})
        self.ext.record_subject_attributes(
            EDITOR, "subj-b", {"region": "us", "tier": "gold"})
        return segment

    def test_segment_match_derivation(self):
        segment = self._segment_and_subjects()
        match = self.ext.segment_match(segment["id"], "subj-a", actor=EDITOR)
        self.assertIs(match["matched"], True)
        self.assertEqual(match["matched_conditions"], 2)
        match = self.ext.segment_match(segment["id"], "subj-b", actor=EDITOR)
        self.assertIs(match["matched"], False)
        self.assertEqual(match["matched_conditions"], 1)
        self.assertIs(match["served_here"], False)

    def test_match_counts_carry_no_optimization(self):
        segment = self._segment_and_subjects()
        counts = self.ext.segment_match_counts(segment["id"], actor=EDITOR)
        self.assertEqual(counts["subjects_recorded"], 2)
        self.assertEqual(counts["subjects_matching"], 1)
        self.assertIs(counts["optimized_here"], False)

    def test_rule_view_serves_nothing(self):
        segment = self._segment_and_subjects()
        rule = self.ext.create_rule(EDITOR, "R1", segment["id"], "ci-1")
        view = self.ext.rule_view(rule["id"], "subj-a", actor=EDITOR)
        self.assertIs(view["segment_matched"], True)
        self.assertIs(view["served_here"], False)
        self.assertIs(view["optimized_here"], False)

    def test_condition_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_segment(
                EDITOR, "S", [{"key": "k", "op": "contains", "value": "v"}])
        with self.assertRaises(ValidationError):
            self.ext.create_segment(
                EDITOR, "S", [{"key": "k", "op": "equals", "value": True}])


class TestReferences(BatchFixture):
    """Stub engines: labeled reference implementations, never execution."""

    def test_search_index_reference_and_reported_run(self):
        ref = self.ext.register_search_index_reference(
            PUBLISHER, "Knowvation index", "repo-main")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["indexing_performed_here"], False)
        updated = self.ext.record_index_run_reference(PUBLISHER, ref["id"], 4321)
        self.assertEqual(updated["runs"][0]["documents_reported"], 4321)

    def test_workflow_reference_changes_no_core_item(self):
        item = make_item(self.store, self.site)
        ref = self.ext.register_workflow_engine_reference(
            PUBLISHER, "Parallel review", {"steps": ["parallel_review"]})
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["executed_here"], False)
        after = self.store.get_item(item["id"], actor=ADMIN)
        self.assertEqual(after["status"], "draft")

    def test_cdn_reference_and_transport_receipt(self):
        ref = self.ext.register_cdn_reference(PUBLISHER, "Edge network")
        self.assertIs(ref["served_here"], False)
        self.assertIs(ref["reference_transport"], True)
        updated = self.ext.record_cdn_receipt(PUBLISHER, ref["id"], "edge-1")
        self.assertIs(updated["receipts"][0]["reference_transport"], True)

    def test_engagement_reference_and_reported_receipt(self):
        ref = self.ext.register_engagement_reference(
            PUBLISHER, "DHRP engagement", "study-9")
        self.assertIs(ref["engaged_here"], False)
        updated = self.ext.record_engagement_receipt(
            PUBLISHER, ref["id"], "portal", 57)
        self.assertEqual(updated["receipts"][0]["participants_reported"], 57)
        with self.assertRaises(ValidationError):
            self.ext.record_engagement_receipt(
                PUBLISHER, ref["id"], "portal", -1)

    def test_hosting_reference_labels_and_role_gate(self):
        ref = self.ext.register_hosting_reference(
            PUBLISHER, "Acquia hosting", "Vendor PaaS runtime")
        self.assertIs(ref["hosted_here"], False)
        self.assertEqual(ref["substrate_label"], "Vendor PaaS runtime")
        with self.assertRaises(PermissionDenied):
            self.ext.register_hosting_reference(EDITOR, "H", "x")

    def test_reference_family_filter_and_wrong_family_run(self):
        cdn = self.ext.register_cdn_reference(PUBLISHER, "Edge")
        self.ext.register_hosting_reference(PUBLISHER, "H", "sub")
        only_cdn = self.ext.list_references(family="cdn_delivery", actor=ADMIN)
        self.assertEqual([r["id"] for r in only_cdn], [cdn["id"]])
        with self.assertRaises(NotFoundError):
            self.ext.record_index_run_reference(PUBLISHER, cdn["id"], 10)


class TestCrossCutting(BatchFixture):
    """House rules across the whole extension surface."""

    def test_denied_write_audited_and_changes_nothing(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_template(VIEWER, "T", "x")
        self.assertEqual(self.ext._templates, {})
        self.assertIn("ext_template_create:denied", self.audit_actions())

    def test_missing_actor_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_template(None, "T", "x")
        with self.assertRaises(PermissionDenied):
            self.ext.open_case(None, "C-1", "subj-1", "eeo")


if __name__ == "__main__":
    unittest.main()
