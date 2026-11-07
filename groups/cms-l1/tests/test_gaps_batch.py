"""Final GAPS batch — Group 24 (CMS L1) extension surface.

Traces to: the eight open entries in ``../UNION-SPEC.md``
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

import hashlib
import unittest

from cms.audit import AuditLog
from cms.errors import NotFoundError, PermissionDenied, ValidationError
from cms.extensions import CmsExtensions

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER
from cms_helpers import make_item, make_store

SHA = "a" * 64


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

    def test_ingestion_job_bound_to_core_item(self):
        item = make_item(self.store, self.site)
        job = self.ext.create_ingestion_job(EDITOR, "Load", item["id"], 42)
        self.assertEqual(job["id"], "ingj-1")
        self.assertEqual(job["item_id"], item["id"])
        self.assertIs(job["executed_here"], False)

    def test_ingestion_job_unknown_item_consumes_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_ingestion_job(EDITOR, "Load", "ci-999", 1)
        item = make_item(self.store, self.site)
        job = self.ext.create_ingestion_job(EDITOR, "Load", item["id"], 1)
        self.assertEqual(job["id"], "ingj-1")

    def test_index_declaration_and_derived_summary(self):
        self.ext.create_ingestion_batch(EDITOR, "B1", "src", 10)
        item = make_item(self.store, self.site)
        self.ext.create_ingestion_job(EDITOR, "J1", item["id"], 7)
        decl = self.ext.create_index_declaration(
            EDITOR, "In place", "repo-main", ["title", "tags"])
        self.assertIs(decl["indexing_performed_here"], False)
        summary = self.ext.ingestion_summary(actor=ADMIN)
        self.assertEqual(summary["batch_count"], 1)
        self.assertEqual(summary["documents_reported_total"], 10)
        self.assertEqual(summary["job_count"], 1)
        self.assertEqual(summary["job_documents_reported_total"], 7)
        self.assertEqual(summary["index_declaration_count"], 1)
        self.assertIs(summary["content_held"], False)


class TestILSLoansCatalogAcquisitions(BatchFixture):
    """Library ILS vertical (build): circulation, cataloging, acquisitions."""

    def test_loan_state_derived_never_stored(self):
        view = self.ext.record_loan(EDITOR, "patron-1", "item-9")
        self.assertEqual(view["id"], "loan-1")
        self.assertEqual(view["current_state"], "checked_out")
        stored = self.ext._loans["loan-1"]
        self.assertNotIn("current_state", stored)
        view = self.ext.record_loan_event(EDITOR, "loan-1", "checked_in")
        self.assertEqual(view["current_state"], "checked_in")
        self.assertEqual(view["event_count"], 2)

    def test_catalog_record_fields_held_as_data(self):
        record = self.ext.create_catalog_record(
            EDITOR, "item-9",
            [{"tag": "245", "value": "A title"}, {"tag": "100", "value": "An author"}])
        self.assertEqual(record["id"], "cat-1")
        self.assertIs(record["discovery_engine_here"], False)
        self.assertEqual(record["fields"][0], {"tag": "245", "value": "A title"})
        with self.assertRaises(ValidationError):
            self.ext.create_catalog_record(
                EDITOR, "item-9", [{"tag": "245", "value": "x", "extra": 1}])
        # catalog field values are not searched by the core search
        result = self.store.search(EDITOR, "A title")
        self.assertEqual(result["items"], [])

    def test_acquisition_order_money_boundary(self):
        order = self.ext.create_acquisition_order(
            EDITOR, "supplier-1", "item-9", 2599)
        self.assertEqual(order["id"], "acq-1")
        self.assertEqual(order["amount_cents"], 2599)
        self.assertIs(order["transmitted_here"], False)
        for bad in (25.99, True, -1):
            with self.assertRaises(ValidationError):
                self.ext.create_acquisition_order(
                    EDITOR, "supplier-1", "item-9", bad)
        order = self.ext.create_acquisition_order(
            EDITOR, "supplier-1", "item-9", 100)
        self.assertEqual(order["id"], "acq-2")


class TestILSSharingCollections(BatchFixture):
    """ILS vertical (build): ILL, collections, knowledgebase, proxying."""

    def test_ill_outcomes_reported_state_derived(self):
        view = self.ext.record_ill_request(
            EDITOR, "patron-1", "item-9", "partner-lib")
        self.assertEqual(view["id"], "ill-1")
        self.assertEqual(view["current_state"], "requested")
        self.assertIs(view["fulfilled_here"], False)
        view = self.ext.record_ill_event(EDITOR, "ill-1", "shipped")
        self.assertEqual(view["current_state"], "shipped")
        self.assertNotIn("current_state", self.ext._ill_requests["ill-1"])

    def test_collection_records_and_derived_summary(self):
        self.ext.create_collection_record(
            EDITOR, "Holdings A", "item-9", "main-stacks")
        self.ext.create_collection_record(
            EDITOR, "Holdings B", "item-10", "main-stacks")
        self.ext.create_collection_record(
            EDITOR, "Holdings C", "item-11", "annex")
        summary = self.ext.collection_summary(actor=ADMIN)
        self.assertEqual(summary["collection_record_count"], 3)
        self.assertEqual(summary["records_by_label"],
                         {"main-stacks": 2, "annex": 1})

    def test_kb_article_revisions_form(self):
        article = self.ext.create_kb_article(EDITOR, "Renewals", "v1 body")
        self.assertEqual(article["id"], "kb-1")
        self.assertIs(article["published_here"], False)
        updated = self.ext.update_kb_article(EDITOR, "kb-1", "v2 body")
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["history"][0]["body"], "v1 body")

    def test_proxy_config_is_configuration_only(self):
        settings = {"hosts": ["db.example"]}
        config = self.ext.create_proxy_config(
            EDITOR, "Main proxy", "db-1", settings)
        self.assertEqual(config["id"], "proxy-1")
        self.assertIs(config["proxied_here"], False)
        settings["hosts"].append("other.example")
        again = self.ext.get_proxy_config("proxy-1", actor=EDITOR)
        self.assertEqual(again["settings"], {"hosts": ["db.example"]})


class TestILSDigitalUnion(BatchFixture):
    """ILS vertical (build): digital collections, union catalog."""

    def test_digital_collection_metadata_plus_digest_only(self):
        view = self.ext.create_digital_collection(
            EDITOR, "Photos", self.site["id"])
        self.assertEqual(view["id"], "dig-1")
        self.assertIs(view["bytes_held"], False)
        self.assertEqual(view["member_count"], 0)
        member = self.ext.add_digital_item(EDITOR, "dig-1", "asset-9", SHA)
        self.assertEqual(member["content_sha256"], SHA)
        self.assertEqual(set(member.keys()),
                         {"asset_ref", "content_sha256",
                          "recorded_by", "recorded_utc"})
        view = self.ext.digital_collection_view("dig-1", actor=EDITOR)
        self.assertEqual(view["member_count"], 1)

    def test_digital_item_digest_and_duplicate_validation(self):
        self.ext.create_digital_collection(EDITOR, "Photos", self.site["id"])
        with self.assertRaises(ValidationError):
            self.ext.add_digital_item(EDITOR, "dig-1", "asset-9", "short")
        self.ext.add_digital_item(EDITOR, "dig-1", "asset-9", SHA)
        with self.assertRaises(ValidationError):
            self.ext.add_digital_item(EDITOR, "dig-1", "asset-9", SHA)

    def test_digital_collection_unknown_site_consumes_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_digital_collection(EDITOR, "X", "site-999")
        view = self.ext.create_digital_collection(
            EDITOR, "Photos", self.site["id"])
        self.assertEqual(view["id"], "dig-1")

    def test_union_holding_network_not_here_state_derived(self):
        view = self.ext.record_union_holding(
            EDITOR, "catalog-9", "library-1")
        self.assertEqual(view["id"], "union-1")
        self.assertIs(view["network_here"], False)
        self.assertEqual(view["current_state"], "held")
        view = self.ext.record_union_event(EDITOR, "union-1", "withdrawn")
        self.assertEqual(view["current_state"], "withdrawn")
        self.assertNotIn("current_state", self.ext._union_holdings["union-1"])


class TestMobile(BatchFixture):
    """Mobile application delivery (build): definitions + reported outcomes."""

    def test_app_definition_holds_no_binary(self):
        app = self.ext.create_app_definition(
            PUBLISHER, "Xplore App", "mobile", site_id=self.site["id"])
        self.assertEqual(app["id"], "app-1")
        self.assertIs(app["binary_held"], False)
        self.assertIs(app["delivered_here"], False)

    def test_app_definition_unknown_site_consumes_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_app_definition(
                PUBLISHER, "X", "mobile", site_id="site-999")
        app = self.ext.create_app_definition(PUBLISHER, "X", "mobile")
        self.assertEqual(app["id"], "app-1")

    def test_release_and_reported_distribution_outcomes(self):
        self.ext.create_app_definition(PUBLISHER, "Xplore App", "mobile")
        release = self.ext.create_app_release(PUBLISHER, "app-1", "1.2.0")
        self.assertEqual(release["id"], "rel-1")
        self.assertIs(release["delivered_here"], False)
        outcome = self.ext.record_distribution_outcome(
            EDITOR, "rel-1", "store-channel", 1500)
        self.assertEqual(outcome["installs_reported"], 1500)
        self.assertIs(outcome["delivered_here"], False)
        summary = self.ext.distribution_summary(actor=ADMIN)
        self.assertEqual(summary["installs_reported_total"], 1500)
        self.assertEqual(summary["release_count"], 1)
        with self.assertRaises(ValidationError):
            self.ext.record_distribution_outcome(
                EDITOR, "rel-1", "store-channel", -3)


class TestAnalytics(BatchFixture):
    """Analytics beyond registry reporting (build): derived figures only."""

    def test_report_definition_dimension_validation(self):
        definition = self.ext.create_report_definition(
            PUBLISHER, "By status", "status")
        self.assertEqual(definition["id"], "rpt-1")
        with self.assertRaises(ValidationError):
            self.ext.create_report_definition(PUBLISHER, "Bad", "nonsense")
        definition = self.ext.create_report_definition(
            PUBLISHER, "By kind", "asset_kind")
        self.assertEqual(definition["id"], "rpt-2")

    def test_run_record_stores_no_figures_view_derives(self):
        self.ext.create_report_definition(PUBLISHER, "By status", "status")
        run = self.ext.record_report_run(PUBLISHER, "rpt-1")
        self.assertEqual(run["id"], "run-1")
        self.assertEqual(set(run.keys()),
                         {"id", "definition_id", "recorded_by", "recorded_utc"})
        self.assertEqual(set(self.ext._report_runs["run-1"].keys()),
                         {"id", "definition_id", "recorded_by", "recorded_utc"})
        view = self.ext.report_run_view("run-1", actor=ADMIN)
        self.assertIs(view["figures_stored"], False)
        self.assertEqual(view["figures"]["draft"], 0)

    def test_run_figures_track_registry_state_at_read(self):
        self.ext.create_report_definition(PUBLISHER, "By status", "status")
        self.ext.record_report_run(PUBLISHER, "rpt-1")
        before = self.ext.report_run_view("run-1", actor=ADMIN)
        self.assertEqual(before["figures"]["draft"], 0)
        make_item(self.store, self.site)
        after = self.ext.report_run_view("run-1", actor=ADMIN)
        self.assertEqual(after["figures"]["draft"], 1)
        # the stored run record itself never gained figures
        self.assertNotIn("figures", self.ext._report_runs["run-1"])


class TestCases(BatchFixture):
    """BPM / case management (build): reference-only keys, derived state."""

    def test_case_record_exact_key_set(self):
        view = self.ext.open_case(EDITOR, "case-ref-1", "subj-1", "general")
        self.assertEqual(view["id"], "case-1")
        stored = self.ext._cases["case-1"]
        self.assertEqual(
            set(stored.keys()),
            {"id", "case_ref", "subject_ref", "case_type", "opened_by",
             "created_utc", "events"})
        self.assertEqual(view["current_state"], "opened")
        self.assertNotIn("current_state", stored)

    def test_case_type_validation_and_event_derivation(self):
        with self.assertRaises(ValidationError):
            self.ext.open_case(EDITOR, "c", "s", "eeo")
        self.ext.open_case(EDITOR, "case-ref-1", "subj-1", "service_request")
        view = self.ext.record_case_event(EDITOR, "case-1", "in_progress")
        self.assertEqual(view["current_state"], "in_progress")
        self.assertEqual(view["event_count"], 2)

    def test_case_decision_record_shape(self):
        self.ext.open_case(EDITOR, "case-ref-1", "subj-1", "general")
        decision = self.ext.record_case_decision(
            PUBLISHER, "case-1", "closed_no_action")
        self.assertEqual(decision["id"], "dec-1")
        self.assertIs(decision["adjudicated_here"], False)
        view = self.ext.case_view("case-1", actor=ADMIN)
        self.assertEqual(view["decision_count"], 1)


class TestParticipation(BatchFixture):
    """Participant engagement (build): participation records, reported outcomes."""

    def test_participation_records_and_derived_summary(self):
        record = self.ext.record_participation(
            EDITOR, "program-1", "participant-1", "completed")
        self.assertEqual(record["id"], "part-1")
        self.assertEqual(record["outcome_label"], "completed")
        self.ext.record_participation(
            EDITOR, "program-1", "participant-2", "completed")
        self.ext.record_participation(
            EDITOR, "program-1", "participant-3", "withdrew")
        self.ext.record_participation(
            EDITOR, "program-2", "participant-4", "completed")
        summary = self.ext.participation_summary("program-1", actor=EDITOR)
        self.assertEqual(summary["participation_count"], 3)
        self.assertEqual(summary["by_outcome"],
                         {"completed": 2, "withdrew": 1})


class TestPersonalization(BatchFixture):
    """Personalization (build): segments, subjects, rules; derived matching."""

    def _segment_and_subjects(self):
        self.ext.create_segment(
            EDITOR, "Members",
            [{"key": "member", "op": "equals", "value": "yes"},
             {"key": "branch", "op": "present"}])
        self.ext.record_subject_attributes(
            EDITOR, "subj-1", {"member": "yes", "branch": "main"})
        self.ext.record_subject_attributes(
            EDITOR, "subj-2", {"member": "no", "branch": "main"})

    def test_segment_match_derived_at_read(self):
        self._segment_and_subjects()
        match = self.ext.segment_match("seg-1", "subj-1", actor=EDITOR)
        self.assertIs(match["matched"], True)
        self.assertEqual(match["matched_conditions"], 2)
        self.assertIs(match["served_here"], False)
        match = self.ext.segment_match("seg-1", "subj-2", actor=EDITOR)
        self.assertIs(match["matched"], False)
        self.assertEqual(match["matched_conditions"], 1)

    def test_segment_match_counts_and_rule_view(self):
        self._segment_and_subjects()
        counts = self.ext.segment_match_counts("seg-1", actor=EDITOR)
        self.assertEqual(counts["subjects_recorded"], 2)
        self.assertEqual(counts["subjects_matching"], 1)
        self.assertIs(counts["optimized_here"], False)
        rule = self.ext.create_rule(EDITOR, "R", "seg-1", "content-9")
        view = self.ext.rule_view(rule["id"], "subj-1", actor=EDITOR)
        self.assertIs(view["segment_matched"], True)
        self.assertIs(view["served_here"], False)
        self.assertIs(view["optimized_here"], False)

    def test_subject_attributes_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.record_subject_attributes(
                EDITOR, "subj-1", {"member": True})
        with self.assertRaises(NotFoundError):
            self.ext.segment_match("seg-1", "subj-9", actor=EDITOR)


class TestStubs(BatchFixture):
    """Stub engines: labeled reference implementations, never execution."""

    def test_cdn_reference_and_receipt(self):
        ref = self.ext.register_cdn_reference(PUBLISHER, "Delivery net")
        self.assertEqual(ref["id"], "ref-1")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["reference_transport"], True)
        self.assertIs(ref["served_here"], False)
        updated = self.ext.record_cdn_receipt(PUBLISHER, "ref-1", "chan-1")
        self.assertEqual(len(updated["receipts"]), 1)
        self.assertIs(updated["receipts"][0]["reference_transport"], True)

    def test_search_index_reference_and_core_search_unchanged(self):
        ref = self.ext.register_search_index_reference(
            PUBLISHER, "Discovery engine", "catalog-scope")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["indexed_here"], False)
        updated = self.ext.record_index_run_reference(
            PUBLISHER, ref["id"], 4200)
        self.assertEqual(updated["runs"][0]["documents_reported"], 4200)
        # the build's search remains the core's literal substring search
        item = make_item(self.store, self.site, title="Catalog Notes")
        result = self.store.search(EDITOR, "catalog")
        self.assertEqual([i["id"] for i in result["items"]], [item["id"]])

    def test_discovery_query_holds_digest_and_refs_only(self):
        record = self.ext.record_discovery_query(
            PUBLISHER, "worldcat libraries", ["res-1", "res-2"])
        self.assertEqual(record["id"], "dqry-1")
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["indexed_here"], False)
        self.assertEqual(
            record["query_sha256"],
            hashlib.sha256("worldcat libraries".encode("utf-8")).hexdigest())
        self.assertEqual(
            set(record.keys()),
            {"id", "query_sha256", "result_refs", "reference_stub",
             "indexed_here", "created_by", "created_utc"})
        self.assertNotIn("worldcat", str(record))

    def test_reference_family_mismatch_rejected(self):
        ref = self.ext.register_cdn_reference(PUBLISHER, "Delivery net")
        with self.assertRaises(NotFoundError):
            self.ext.record_index_run_reference(PUBLISHER, ref["id"], 5)


class TestNegativeControlDeciderNotOpener(BatchFixture):
    """Fresh negative control: the case-decision separation-of-duties seam.

    Traced claim: a case's decision may be recorded only by
    someone other than the user who opened the case (control
    family AC-5, mirroring the group's founding drill on the
    editorial approver guard). The mutant below waves the seam
    through; the canonical expectation must then fail.
    """

    def _open(self, ext):
        return ext.open_case(EDITOR, "case-ref-1", "subj-1", "general")

    def test_opener_cannot_decide_canonical(self):
        self._open(self.ext)
        with self.assertRaises(PermissionDenied):
            self.ext.record_case_decision(EDITOR, "case-1", "closed")
        # the denied decision consumed no id and recorded nothing
        self.assertEqual(self.ext.list_case_decisions(actor=ADMIN), [])
        self.assertIn("ext_case_decision:denied", self.audit_actions())

    def test_denied_decision_consumes_no_id(self):
        self._open(self.ext)
        with self.assertRaises(PermissionDenied):
            self.ext.record_case_decision(EDITOR, "case-1", "closed")
        decision = self.ext.record_case_decision(
            PUBLISHER, "case-1", "closed")
        self.assertEqual(decision["id"], "dec-1")

    def test_mutant_waves_opener_decision_through(self):
        class MutantExtensions(CmsExtensions):
            def _check_decider_not_opener(self, case, actor):
                return None

        mutant = MutantExtensions(self.store)
        self._open(mutant)
        decision = mutant.record_case_decision(EDITOR, "case-1", "closed")
        self.assertEqual(decision["decided_by"], "carol")

    def test_mutant_outcome_as_expectation_fails(self):
        class MutantExtensions(CmsExtensions):
            def _check_decider_not_opener(self, case, actor):
                return None

        mutant = MutantExtensions(self.store)
        self._open(mutant)
        with self.assertRaises(AssertionError):
            # Treating the mutant's wave-through as the expected
            # (denied) outcome must fail: the mutant records it.
            try:
                mutant.record_case_decision(EDITOR, "case-1", "closed")
            except PermissionDenied:
                pass
            else:
                raise AssertionError("mutant waved the decision through")

    def test_different_decider_succeeds_on_real_store(self):
        self._open(self.ext)
        decision = self.ext.record_case_decision(
            PUBLISHER, "case-1", "closed")
        self.assertEqual(decision["decided_by"], "bob")
        self.assertIs(decision["adjudicated_here"], False)


if __name__ == "__main__":
    unittest.main()
