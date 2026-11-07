"""Final GAPS batch — Untiered Set 14 (CMS) extension surface.

Pins the records-form implementations and labeled reference
implementations in ``cms.extensions`` for the twelve open entries
of the GAPS.md section "Untiered Set 14 — Content Management
System (CMS) (2 forks, tier null)":

- build-extension: template/fragment definition records
  (rendering & templating), personalization segments / subject
  attributes / rules with read-time derived matching, versioning
  depth (revision chains, comparison records, asset version
  groups), low-code application/form definition records, and
  locale records with derived multi-site counts;
- stub-engine: labeled reference records for enterprise search
  indexing, editorial workflow engines, document generation,
  identity federation/SSO, headless delivery, CDN/runtime
  serving, and platform hosting.

Also pins the set's tier discipline over the extension surface:
no record or view carries a tier, baseline, impact-level, or
score-shaped key (recursive scan), and the batch's fresh
negative control for the personalization matching seam
``cms.extensions._condition_holds``.
"""

import unittest

import cms.extensions as extensions_module
from cms.errors import NotFoundError, PermissionDenied, ValidationError
from cms.extensions import CmsExtensions

from cms_helpers import (
    ADMIN, PUBLISHER, EDITOR, AUTHOR, VIEWER, make_item, make_store,
)


def make_extensions():
    """Fresh core store (canonical site/section) + extension register."""
    store, site, section = make_store()
    return CmsExtensions(store), store, site, section


FORBIDDEN_KEY_PARTS = ("score", "tier", "baseline", "rating", "grade", "rank")
FORBIDDEN_KEYS = {"cmmc_tier", "fedramp_impact_level", "impact_level"}


def assert_no_forbidden_keys(case, node, path="root"):
    """Recursively assert no tier/baseline/score-shaped key exists."""
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            case.assertNotIn(key, FORBIDDEN_KEYS,
                             "forbidden key %r at %s" % (key, path))
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(
                    part, lowered,
                    "key %r at %s contains forbidden part %r" % (key, path, part))
            assert_no_forbidden_keys(case, value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            assert_no_forbidden_keys(case, value, "%s[%d]" % (path, index))


class TestTemplates(unittest.TestCase):
    """Gap: rendering & templating engines and visual/WYSIWYG editors."""

    def test_template_record_shape_and_derived_placeholders(self):
        ext, store, site, section = make_extensions()
        record = ext.create_template(
            PUBLISHER, "Landing", "Hello {{ visitor_name }}, see {{offer}}")
        self.assertEqual(record["id"], "tpl-1")
        self.assertEqual(record["kind"], "template")
        self.assertEqual(record["version"], 1)
        self.assertIs(record["rendered_here"], False)
        # Placeholder names are derived from the held body at read.
        self.assertEqual(record["placeholder_names"],
                         ["offer", "visitor_name"])
        self.assertNotIn("placeholder_names",
                         ext._templates["tpl-1"])

    def test_fragment_kind_and_update_versioning(self):
        ext, store, site, section = make_extensions()
        record = ext.create_template(PUBLISHER, "Card",
                                     "<div>{{title}}</div>",
                                     kind="fragment")
        updated = ext.update_template(PUBLISHER, record["id"],
                                      "<div>{{title}} {{cta}}</div>")
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["version_count"], 2)
        self.assertEqual(updated["placeholder_names"], ["cta", "title"])
        self.assertEqual(len(updated["history"]), 1)
        self.assertEqual(updated["history"][0]["body"], "<div>{{title}}</div>")
        self.assertIs(updated["rendered_here"], False)

    def test_template_write_denied_for_viewer_and_no_id_consumed(self):
        ext, store, site, section = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.create_template(VIEWER, "Nope", "body")
        with self.assertRaises(ValidationError):
            ext.create_template(PUBLISHER, "Bad", "body", kind="widget")
        record = ext.create_template(PUBLISHER, "Ok", "body")
        self.assertEqual(record["id"], "tpl-1")

    def test_template_audit_actions(self):
        ext, store, site, section = make_extensions()
        ext.create_template(PUBLISHER, "Landing", "body")
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("ext_template_create", actions)


class TestPersonalization(unittest.TestCase):
    """Gap: personalization / experience optimization."""

    def _segment_and_subjects(self, ext):
        segment = ext.create_segment(
            EDITOR, "Returning staff",
            [{"key": "cohort", "op": "equals", "value": "staff"},
             {"key": "region", "op": "present"}])
        ext.record_subject_attributes(
            EDITOR, "subj-ref-a", {"cohort": "staff", "region": "north"})
        ext.record_subject_attributes(
            EDITOR, "subj-ref-b", {"cohort": "public", "region": "north"})
        ext.record_subject_attributes(
            EDITOR, "subj-ref-c", {"cohort": "staff"})
        return segment

    def test_match_derived_at_read(self):
        ext, store, site, section = make_extensions()
        segment = self._segment_and_subjects(ext)
        match_a = ext.segment_match(segment["id"], "subj-ref-a", EDITOR)
        self.assertTrue(match_a["matched"])
        self.assertEqual(match_a["matched_conditions"], 2)
        self.assertEqual(match_a["total_conditions"], 2)
        self.assertIs(match_a["served_here"], False)
        match_b = ext.segment_match(segment["id"], "subj-ref-b", EDITOR)
        self.assertFalse(match_b["matched"])
        self.assertEqual(match_b["matched_conditions"], 1)
        match_c = ext.segment_match(segment["id"], "subj-ref-c", EDITOR)
        self.assertFalse(match_c["matched"])
        self.assertEqual(match_c["matched_conditions"], 1)

    def test_match_counts_derived(self):
        ext, store, site, section = make_extensions()
        segment = self._segment_and_subjects(ext)
        counts = ext.segment_match_counts(segment["id"], EDITOR)
        self.assertEqual(counts["subjects_recorded"], 3)
        self.assertEqual(counts["subjects_matching"], 1)
        self.assertIs(counts["optimized_here"], False)

    def test_rule_view_derives_and_serves_nothing(self):
        ext, store, site, section = make_extensions()
        segment = self._segment_and_subjects(ext)
        rule = ext.create_rule(EDITOR, "Staff banner", segment["id"], "ci-1")
        view_a = ext.rule_view(rule["id"], "subj-ref-a", EDITOR)
        self.assertTrue(view_a["segment_matched"])
        self.assertIs(view_a["served_here"], False)
        self.assertIs(view_a["optimized_here"], False)
        view_b = ext.rule_view(rule["id"], "subj-ref-b", EDITOR)
        self.assertFalse(view_b["segment_matched"])

    def test_subject_rerecord_replaces_attributes_keeps_id(self):
        ext, store, site, section = make_extensions()
        first = ext.record_subject_attributes(EDITOR, "s-1", {"a": "1"})
        second = ext.record_subject_attributes(EDITOR, "s-1", {"a": "2"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["attributes"], {"a": "2"})

    def test_unknown_subject_and_bad_conditions(self):
        ext, store, site, section = make_extensions()
        segment = ext.create_segment(EDITOR, "S",
                                     [{"key": "k", "op": "present"}])
        with self.assertRaises(NotFoundError):
            ext.segment_match(segment["id"], "nobody", EDITOR)
        with self.assertRaises(ValidationError):
            ext.create_segment(EDITOR, "Bad", [{"key": "k", "op": "near"}])
        with self.assertRaises(ValidationError):
            ext.create_segment(EDITOR, "Bad", [])
        nxt = ext.create_segment(EDITOR, "Next",
                                 [{"key": "k", "op": "present"}])
        self.assertEqual(nxt["id"], "seg-2")


class TestVersioningDepth(unittest.TestCase):
    """Gap: document & media versioning depth."""

    def test_item_version_chain_derived_from_core_revisions(self):
        ext, store, site, section = make_extensions()
        item = make_item(store, site)
        store.update_item(EDITOR, item["id"], body="Second body")
        store.update_item(EDITOR, item["id"], body="Third body")
        chain = ext.item_version_chain(item["id"], EDITOR)
        self.assertEqual(chain["chain_length"], 3)
        self.assertEqual(chain["current_revision"], 3)
        self.assertEqual([c["revision"] for c in chain["chain"]], [1, 2, 3])

    def test_comparison_record_labels_verbatim_no_diff(self):
        ext, store, site, section = make_extensions()
        item = make_item(store, site)
        store.update_item(EDITOR, item["id"], body="Second body")
        record = ext.record_comparison(
            EDITOR, item["id"], 1, 2, "legal review: wording tightened")
        self.assertEqual(record["id"], "cmp-1")
        self.assertEqual(record["label"], "legal review: wording tightened")
        self.assertIs(record["diff_computed_here"], False)
        with self.assertRaises(ValidationError):
            ext.record_comparison(EDITOR, item["id"], 1, 9, "nope")
        nxt = ext.record_comparison(EDITOR, item["id"], 2, 1, "back-check")
        self.assertEqual(nxt["id"], "cmp-2")

    def test_asset_version_group(self):
        ext, store, site, section = make_extensions()
        asset = store.register_asset(EDITOR, site["id"], "guide.pdf",
                                     "document", 1200, data=b"guide")
        group = ext.create_asset_version_group(EDITOR, "Guide versions")
        self.assertEqual(group["member_count"], 0)
        updated = ext.add_asset_version(EDITOR, group["id"], asset["id"],
                                        "2026.1")
        self.assertEqual(updated["member_count"], 1)
        self.assertEqual(updated["version_labels"], ["2026.1"])
        with self.assertRaises(ValidationError):
            ext.add_asset_version(EDITOR, group["id"], asset["id"], "2026.2")
        with self.assertRaises(NotFoundError):
            ext.add_asset_version(EDITOR, group["id"], "asset-99", "x")


class TestLowCodeDefinitions(unittest.TestCase):
    """Gap: low-code application builders & form engines."""

    def test_definition_records_held_as_data(self):
        ext, store, site, section = make_extensions()
        definition = {"fields": [{"name": "email", "kind": "text"}]}
        record = ext.create_definition(PUBLISHER, "form", "Intake",
                                       definition)
        self.assertEqual(record["id"], "def-1")
        self.assertIs(record["executed_here"], False)
        self.assertIs(record["rendered_here"], False)
        # The caller's dict is deep-copied: later mutation changes nothing.
        definition["fields"].append({"name": "extra", "kind": "text"})
        stored = ext.get_definition(record["id"], PUBLISHER)
        self.assertEqual(len(stored["definition"]["fields"]), 1)

    def test_definition_update_versions(self):
        ext, store, site, section = make_extensions()
        record = ext.create_definition(PUBLISHER, "application", "Portal",
                                       {"pages": ["home"]})
        updated = ext.update_definition(PUBLISHER, record["id"],
                                        {"pages": ["home", "about"]})
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["history"][0]["definition"],
                         {"pages": ["home"]})
        with self.assertRaises(ValidationError):
            ext.create_definition(PUBLISHER, "form", "Bad", ["not-a-dict"])


class TestMultiSiteLocales(unittest.TestCase):
    """Gap: multi-site & multilingual site operations depth."""

    def test_locale_records_and_linkage(self):
        ext, store, site, section = make_extensions()
        locale = ext.create_locale(PUBLISHER, site["id"], "es", "Espanol")
        self.assertEqual(locale["linked_item_count"], 0)
        item = make_item(store, site)
        linked = ext.link_item_to_locale(PUBLISHER, locale["id"], item["id"])
        self.assertEqual(linked["linked_item_count"], 1)
        with self.assertRaises(ValidationError):
            ext.link_item_to_locale(PUBLISHER, locale["id"], item["id"])
        with self.assertRaises(ValidationError):
            ext.create_locale(PUBLISHER, site["id"], "es", "duplicate")

    def test_link_rejects_item_from_another_site(self):
        ext, store, site, section = make_extensions()
        other = store.create_site(PUBLISHER, "Other", "other-site")
        foreign = make_item(store, other, slug="foreign")
        locale = ext.create_locale(PUBLISHER, site["id"], "fr")
        with self.assertRaises(ValidationError):
            ext.link_item_to_locale(PUBLISHER, locale["id"], foreign["id"])

    def test_summaries_derived(self):
        ext, store, site, section = make_extensions()
        item = make_item(store, site)
        locale = ext.create_locale(PUBLISHER, site["id"], "es")
        ext.link_item_to_locale(PUBLISHER, locale["id"], item["id"])
        summary = ext.site_locale_summary(site["id"], PUBLISHER)
        self.assertEqual(summary["locale_count"], 1)
        self.assertEqual(summary["locales"], ["es"])
        self.assertEqual(summary["linked_item_count"], 1)
        self.assertEqual(summary["site_item_count"], 1)
        multi = ext.multi_site_summary(PUBLISHER)
        self.assertEqual(multi["site_count"], 1)
        self.assertEqual(multi["sites"][0]["section_count"], 1)
        self.assertEqual(multi["sites"][0]["locale_count"], 1)


class TestReferenceStubs(unittest.TestCase):
    """The seven stub-engine entries, as labeled reference records."""

    def test_search_index_reference_and_reported_run(self):
        ext, store, site, section = make_extensions()
        ref = ext.register_search_index_reference(PUBLISHER, "Enterprise "
                                                  "Search", "all-sites")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["indexing_performed_here"], False)
        updated = ext.record_index_run_reference(PUBLISHER, ref["id"], 431)
        self.assertEqual(updated["runs"][0]["documents_reported"], 431)
        with self.assertRaises(ValidationError):
            ext.record_index_run_reference(PUBLISHER, ref["id"], -1)
        # The core search is untouched: still literal substring search.
        results = store.search(EDITOR, "Main")
        self.assertEqual(set(results.keys()),
                         {"items", "assets", "sites", "tags"})

    def test_workflow_engine_reference_changes_no_core_item(self):
        ext, store, site, section = make_extensions()
        item = make_item(store, site)
        before = store.get_item(item["id"], EDITOR)
        ref = ext.register_workflow_engine_reference(
            PUBLISHER, "Parallel review engine",
            {"steps": ["legal", "comms"], "parallel": True})
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["executed_here"], False)
        after = store.get_item(item["id"], EDITOR)
        self.assertEqual(before["status"], after["status"])
        self.assertEqual(after["status"], "draft")

    def test_document_generation_reference(self):
        ext, store, site, section = make_extensions()
        ref = ext.register_document_generation_reference(
            PUBLISHER, "Drawloop DocGen", "crm-records")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["generated_here"], False)
        updated = ext.record_generation_reference(PUBLISHER, ref["id"],
                                                  "pkg-2026-011")
        self.assertEqual(updated["packages"][0]["package_ref"], "pkg-2026-011")

    def test_identity_hook_is_not_an_idp(self):
        ext, store, site, section = make_extensions()
        ref = ext.register_identity_hook(PUBLISHER, "SSO hook", "SAML 2.0")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["hook_only"], True)
        self.assertIs(ref["identity_provider"], False)
        self.assertEqual(ref["protocol_label"], "SAML 2.0")

    def test_headless_delivery_receipts_are_reference_transport(self):
        ext, store, site, section = make_extensions()
        ref = ext.register_headless_delivery_reference(PUBLISHER, "Headless "
                                                       "API delivery")
        self.assertIs(ref["reference_transport"], True)
        self.assertIs(ref["delivered_here"], False)
        updated = ext.record_delivery_receipt(PUBLISHER, ref["id"],
                                              "channel-web")
        receipt = updated["receipts"][0]
        self.assertIs(receipt["reference_transport"], True)
        self.assertEqual(receipt["channel_ref"], "channel-web")

    def test_cdn_and_hosting_references(self):
        ext, store, site, section = make_extensions()
        cdn = ext.register_cdn_reference(PUBLISHER, "Delivery network")
        self.assertIs(cdn["reference_stub"], True)
        self.assertIs(cdn["served_here"], False)
        hosting = ext.register_hosting_reference(
            PUBLISHER, "Managed hosting", "vendor cloud platform")
        self.assertIs(hosting["reference_stub"], True)
        self.assertIs(hosting["hosted_here"], False)
        self.assertEqual(hosting["substrate_label"], "vendor cloud platform")
        families = {r["family"] for r in ext.list_references(actor=PUBLISHER)}
        self.assertEqual(families, {"cdn_delivery", "platform_hosting"})


class TestTierNullSurface(unittest.TestCase):
    """Tier stays null over the whole extension surface (recursive scan)."""

    def test_no_tier_baseline_or_score_keys_anywhere(self):
        ext, store, site, section = make_extensions()
        ext.create_template(PUBLISHER, "Landing", "Hi {{name}}")
        segment = ext.create_segment(EDITOR, "Staff",
                                     [{"key": "cohort", "op": "equals",
                                       "value": "staff"}])
        ext.record_subject_attributes(EDITOR, "s-1", {"cohort": "staff"})
        rule = ext.create_rule(EDITOR, "Banner", segment["id"], "ci-1")
        item = make_item(store, site)
        store.update_item(EDITOR, item["id"], body="v2")
        ext.record_comparison(EDITOR, item["id"], 1, 2, "checked")
        asset = store.register_asset(EDITOR, site["id"], "a.pdf",
                                     "document", 10, data=b"a")
        group = ext.create_asset_version_group(EDITOR, "G")
        ext.add_asset_version(EDITOR, group["id"], asset["id"], "1.0")
        ext.create_definition(PUBLISHER, "form", "F", {"fields": []})
        locale = ext.create_locale(PUBLISHER, site["id"], "es")
        ext.link_item_to_locale(PUBLISHER, locale["id"], item["id"])
        ext.register_search_index_reference(PUBLISHER, "Idx", "all")
        ext.register_workflow_engine_reference(PUBLISHER, "WF", {})
        ext.register_document_generation_reference(PUBLISHER, "DG", "crm")
        ext.register_identity_hook(PUBLISHER, "SSO", "OIDC")
        ext.register_headless_delivery_reference(PUBLISHER, "HD")
        ext.register_cdn_reference(PUBLISHER, "CDN")
        ext.register_hosting_reference(PUBLISHER, "Host", "vendor cloud")
        surface = [
            ext.list_templates(actor=ADMIN),
            ext.list_segments(actor=ADMIN),
            ext.segment_match(segment["id"], "s-1", ADMIN),
            ext.segment_match_counts(segment["id"], ADMIN),
            ext.rule_view(rule["id"], "s-1", ADMIN),
            ext.item_version_chain(item["id"], ADMIN),
            ext.list_comparisons(actor=ADMIN),
            ext.list_asset_version_groups(actor=ADMIN),
            ext.list_definitions(actor=ADMIN),
            ext.list_locales(actor=ADMIN),
            ext.site_locale_summary(site["id"], ADMIN),
            ext.multi_site_summary(ADMIN),
            ext.list_references(actor=ADMIN),
        ]
        for node in surface:
            assert_no_forbidden_keys(self, node)


class TestConditionNegativeControl(unittest.TestCase):
    """Fresh negative control: the personalization matching seam.

    The traced claim: a subject matches a segment only when every
    recorded condition holds against the subject's recorded
    attributes (``cms.extensions._condition_holds`` is the single
    derivation seam). The mutant waves every condition through.
    For the canonical case (an ``equals`` condition the subject
    fails) the test asserts the canonical expectation (no match),
    that the mutant would NOT produce it (it matches), and that
    treating the mutant's outcome as the expected outcome fails.
    """

    def _fixture(self):
        ext, store, site, section = make_extensions()
        segment = ext.create_segment(
            EDITOR, "Staff only",
            [{"key": "cohort", "op": "equals", "value": "staff"}])
        ext.record_subject_attributes(EDITOR, "subj-x", {"cohort": "public"})
        return ext, segment

    def test_equals_condition_canonical_but_mutant_not(self):
        ext, segment = self._fixture()
        canonical = ext.segment_match(segment["id"], "subj-x", EDITOR)
        self.assertFalse(canonical["matched"])
        self.assertEqual(canonical["matched_conditions"], 0)

        original = extensions_module._condition_holds
        extensions_module._condition_holds = lambda cond, attrs: True
        try:
            mutant = ext.segment_match(segment["id"], "subj-x", EDITOR)
        finally:
            extensions_module._condition_holds = original
        self.assertTrue(mutant["matched"])
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant["matched"], canonical["matched"])
        # Restored seam: canonical result again.
        restored = ext.segment_match(segment["id"], "subj-x", EDITOR)
        self.assertFalse(restored["matched"])

    def test_counts_canonical_but_mutant_not(self):
        ext, segment = self._fixture()
        canonical = ext.segment_match_counts(segment["id"], EDITOR)
        self.assertEqual(canonical["subjects_matching"], 0)
        original = extensions_module._condition_holds
        extensions_module._condition_holds = lambda cond, attrs: True
        try:
            mutant = ext.segment_match_counts(segment["id"], EDITOR)
        finally:
            extensions_module._condition_holds = original
        self.assertEqual(mutant["subjects_matching"], 1)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant["subjects_matching"],
                             canonical["subjects_matching"])


if __name__ == "__main__":
    unittest.main()
