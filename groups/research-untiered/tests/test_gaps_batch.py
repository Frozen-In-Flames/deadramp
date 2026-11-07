"""Final GAPS batch tests — Untiered Set 9, Research (tier null).

Pins the extension surface in ``src/research/extensions.py`` per
GAPS.md section entry (inventory idx 828–838; see ``../BATCH.md``
for the per-entry disposition), the founding privacy discipline
(no record shape can hold subject data — every entity shape is
pinned to its exact key set, and an unexpected keyword argument
raises ``TypeError``), and tier null on the extension surface (a
recursive scan finds no tier-, baseline-, or score-shaped key on
any extension record or view).

The batch's fresh negative control lives here:
``TestConsentDerivationNegativeControl`` mutates the extension's
single consent-derivation seam (``_current_consent_label``) to
read the EARLIEST recorded state instead of the latest, and pins
that the canonical expectations reject the mutant's outcomes.
"""

import unittest

from research.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from research.extensions import ResearchExtensions

from research_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    STAFF,
    VIEWER,
    make_store,
)

FORBIDDEN_KEY_FRAGMENTS = ("tier", "baseline", "cmmc", "fedramp",
                           "score", "rank")


def make_extensions():
    """Fresh store + canonical commons + the extension surface."""
    store, commons, _org = make_store()
    return ResearchExtensions(store), store, commons


def _scan_keys(value, path="root"):
    """Yield (path, key) for every dict key in a nested structure."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, key
            yield from _scan_keys(item, path + "." + str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _scan_keys(item, "%s[%d]" % (path, index))


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.ext, self.store, self.commons = make_extensions()
        self.cid = self.commons["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]


class TestIntelligenceItems(BatchFixture):
    """Idx 828 — market & policy intelligence platform (built)."""

    def test_record_and_summary(self):
        item = self.ext.record_intelligence_item(
            MEMBER, self.cid, "legislation", "BILL-2026-114",
            "congressional record feed", "detail:opaque-1")
        self.assertEqual(item["id"], "int-1")
        self.assertIs(item["gathered_here"], False)
        self.ext.record_intelligence_item(
            MEMBER, self.cid, "hearing", "HEARING-9",
            "committee calendar", "detail:opaque-2")
        self.ext.record_intelligence_item(
            STAFF, self.cid, "legislation", "BILL-2026-200",
            "congressional record feed", "detail:opaque-3")
        summary = self.ext.intelligence_summary(MEMBER, self.cid)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["by_kind"],
                         {"legislation": 2, "hearing": 1})
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertIs(summary["gathered_here"], False)

    def test_bad_kind_rejected_and_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.record_intelligence_item(
                MEMBER, self.cid, "rumor", "X-1", "feed", "detail:x")
        item = self.ext.record_intelligence_item(
            MEMBER, self.cid, "policy_item", "POL-1", "feed", "detail:y")
        self.assertEqual(item["id"], "int-1")

    def test_shape_pinned(self):
        item = self.ext.record_intelligence_item(
            MEMBER, self.cid, "directory_entry", "PERSON-REF-1",
            "directory export", "detail:z")
        self.assertEqual(
            set(item.keys()),
            {"id", "commons_id", "kind", "topic_ref", "source_label",
             "detail_ref", "gathered_here", "created_by", "created_utc"})


class TestAwards(BatchFixture):
    """Idx 829 — contract award & subaward analysis (built)."""

    def _prime(self):
        return self.ext.record_award(
            MEMBER, self.cid, "AWARD-1", "ORG-A", "prime", 1_000_000)

    def test_analysis_is_deterministic_sums(self):
        prime = self._prime()
        self.ext.record_award(
            MEMBER, self.cid, "SUB-1", "ORG-B", "subaward", 250_000,
            parent_award_id=prime["id"])
        self.ext.record_award(
            MEMBER, self.cid, "SUB-2", "ORG-C", "subaward", 150_000,
            parent_award_id=prime["id"])
        analysis = self.ext.award_analysis(MEMBER, self.cid)
        self.assertEqual(analysis["award_count"], 3)
        self.assertEqual(analysis["prime_count"], 1)
        self.assertEqual(analysis["subaward_count"], 2)
        self.assertEqual(analysis["total_cents"], 1_400_000)
        self.assertEqual(analysis["prime_cents"], 1_000_000)
        self.assertEqual(analysis["subaward_cents"], 400_000)
        self.assertEqual(analysis["method"], "deterministic_sums")
        subs = self.ext.list_subawards(MEMBER, prime["id"])
        self.assertEqual([s["award_ref"] for s in subs], ["SUB-1", "SUB-2"])

    def test_float_and_bool_amounts_rejected(self):
        for bad in (10.5, True, "100"):
            with self.assertRaises(ValidationError):
                self.ext.record_award(
                    MEMBER, self.cid, "AWARD-X", "ORG-A", "prime", bad)
        award = self._prime()
        self.assertEqual(award["id"], "awd-1")

    def test_subaward_parent_rules(self):
        prime = self._prime()
        with self.assertRaises(ValidationError):
            self.ext.record_award(
                MEMBER, self.cid, "SUB-X", "ORG-B", "prime", 5,
                parent_award_id=prime["id"])
        sub = self.ext.record_award(
            MEMBER, self.cid, "SUB-1", "ORG-B", "subaward", 5,
            parent_award_id=prime["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_award(
                MEMBER, self.cid, "SUB-2", "ORG-C", "subaward", 5,
                parent_award_id=sub["id"])

    def test_duplicate_award_ref_rejected(self):
        self._prime()
        with self.assertRaises(ValidationError):
            self._prime()


class TestRelationshipGraph(BatchFixture):
    """Idx 830 — entity / relationship-graph analytics (built)."""

    def _entities(self):
        a = self.ext.register_entity(MEMBER, self.cid, "ENT-A",
                                     "organization")
        b = self.ext.register_entity(MEMBER, self.cid, "ENT-B", "program")
        c = self.ext.register_entity(MEMBER, self.cid, "ENT-C", "person")
        return a, b, c

    def test_degrees_derived_at_read(self):
        a, b, c = self._entities()
        self.ext.record_relationship(MEMBER, self.cid, a["id"], b["id"],
                                     "funds")
        self.ext.record_relationship(MEMBER, self.cid, a["id"], c["id"],
                                     "funds")
        self.ext.record_relationship(MEMBER, self.cid, c["id"], b["id"],
                                     "reports_to")
        view = self.ext.entity_view(MEMBER, b["id"])
        self.assertEqual(view["in_degree"], 2)
        self.assertEqual(view["out_degree"], 0)
        self.assertEqual(view["total_degree"], 2)
        self.assertIs(view["inference_here"], False)
        stored = self.ext._entities[b["id"]]
        self.assertNotIn("in_degree", stored)
        self.assertNotIn("total_degree", stored)
        neighbors = self.ext.list_neighbors(MEMBER, a["id"])
        self.assertEqual(neighbors["outgoing"], [b["id"], c["id"]])
        self.assertEqual(neighbors["incoming"], [])

    def test_relationship_counts_by_label(self):
        a, b, c = self._entities()
        self.ext.record_relationship(MEMBER, self.cid, a["id"], b["id"],
                                     "funds")
        self.ext.record_relationship(MEMBER, self.cid, a["id"], c["id"],
                                     "funds")
        self.ext.record_relationship(MEMBER, self.cid, c["id"], b["id"],
                                     "reports_to")
        counts = self.ext.relationship_counts(MEMBER, self.cid)
        self.assertEqual(counts["edge_count"], 3)
        self.assertEqual(counts["entity_count"], 3)
        self.assertEqual(counts["by_label"],
                         {"funds": 2, "reports_to": 1})

    def test_self_loop_and_duplicate_edge_rejected(self):
        a, b, _c = self._entities()
        with self.assertRaises(ValidationError):
            self.ext.record_relationship(MEMBER, self.cid, a["id"],
                                         a["id"], "funds")
        self.ext.record_relationship(MEMBER, self.cid, a["id"], b["id"],
                                     "funds")
        with self.assertRaises(ValidationError):
            self.ext.record_relationship(MEMBER, self.cid, a["id"],
                                         b["id"], "funds")

    def test_duplicate_entity_ref_rejected(self):
        self._entities()
        with self.assertRaises(ValidationError):
            self.ext.register_entity(MEMBER, self.cid, "ENT-A", "place")


class TestSavedSearchReference(BatchFixture):
    """Idx 831 — saved-search, alerting & entity-tracking (reference)."""

    def test_stub_labels_pinned(self):
        record = self.ext.record_saved_search(
            MEMBER, self.cid, "SEARCH-REF-1", "award records")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["executed_here"], False)
        self.assertIs(record["alerts_sent_here"], False)

    def test_tracking_reference_labels(self):
        entity = self.ext.register_entity(MEMBER, self.cid, "ENT-A",
                                          "organization")
        record = self.ext.record_entity_tracking(
            MEMBER, self.cid, entity["id"], "watch: quarterly")
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["tracking_active_here"], False)
        self.assertEqual(record["state"], "recorded_reference_only")


class TestEdc(BatchFixture):
    """Idx 832 — clinical-trial EDC (built)."""

    def _form(self):
        return self.ext.define_capture_form(
            MEMBER, self.cid, "FORM-AE", "Adverse events",
            ["field:visit_date", "field:event_code"])

    def test_form_shape_and_derived_count(self):
        form = self._form()
        self.assertEqual(
            set(form.keys()),
            {"id", "commons_id", "form_ref", "title", "field_refs",
             "captured_values_held_here", "created_by", "created_utc"})
        self.assertNotIn("field_count", form)
        view = self.ext.form_view(MEMBER, form["id"])
        self.assertEqual(view["field_count"], 2)
        self.assertIs(view["captured_values_held_here"], False)

    def test_duplicate_fields_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.define_capture_form(
                MEMBER, self.cid, "FORM-X", "Bad",
                ["field:a", "field:a"])

    def test_submission_holds_counts_only(self):
        form = self._form()
        sub = self.ext.record_submission(
            MEMBER, self.cid, form["id"], "SITE-7", 12,
            queries_reported=1, subject_ref="PART-REF-9")
        self.assertEqual(
            set(sub.keys()),
            {"id", "commons_id", "form_id", "site_ref", "subject_ref",
             "recorded_status", "fields_reported", "queries_reported",
             "captured_values_held_here", "created_by", "created_utc"})
        self.assertEqual(sub["recorded_status"], "reported_submitted")
        self.assertIs(sub["captured_values_held_here"], False)

    def test_submission_validation(self):
        form = self._form()
        with self.assertRaises(ValidationError):
            self.ext.record_submission(
                MEMBER, self.cid, form["id"], "SITE-7", -1)
        with self.assertRaises(ValidationError):
            self.ext.record_submission(
                MEMBER, self.cid, form["id"], "SITE-7", 1.5)
        with self.assertRaises(ValidationError):
            self.ext.record_submission(
                MEMBER, self.cid, form["id"], "SITE-7", 3,
                recorded_status="verified")


class TestEConsentEcoa(BatchFixture):
    """Idx 833 — eConsent & eCOA (built)."""

    def _instrument(self):
        return self.ext.define_consent_instrument(
            MEMBER, self.cid, "CONSENT-MAIN", "v3")

    def test_instrument_labels(self):
        inst = self._instrument()
        self.assertIs(inst["signature_possible_here"], False)
        self.assertIs(inst["consent_effected_here"], False)

    def test_current_state_is_latest_recorded(self):
        inst = self._instrument()
        self.ext.record_consent_state(
            MEMBER, self.cid, inst["id"], "PART-1", "reported_pending")
        self.ext.record_consent_state(
            STAFF, self.cid, inst["id"], "PART-1", "reported_consented")
        view = self.ext.consent_current_state(MEMBER, inst["id"], "PART-1")
        self.assertEqual(view["current_state"], "reported_consented")
        self.assertEqual(view["state_record_count"], 2)
        self.assertIs(view["derived"], True)
        for record in self.ext._consent_states.values():
            self.assertNotIn("current_state", record)

    def test_unknown_participant_state_is_not_found(self):
        inst = self._instrument()
        with self.assertRaises(NotFoundError):
            self.ext.consent_current_state(MEMBER, inst["id"], "PART-404")

    def test_bad_state_label_rejected_and_consumes_no_id(self):
        inst = self._instrument()
        with self.assertRaises(ValidationError):
            self.ext.record_consent_state(
                MEMBER, self.cid, inst["id"], "PART-1", "signed")
        record = self.ext.record_consent_state(
            MEMBER, self.cid, inst["id"], "PART-1", "reported_pending")
        self.assertEqual(record["id"], "cns-1")
        self.assertIs(record["signature_held_here"], False)

    def test_outcome_response_counts_only(self):
        inst = self.ext.define_outcome_instrument(
            MEMBER, self.cid, "QOL-1", "questionnaire")
        record = self.ext.record_outcome_response_count(
            MEMBER, self.cid, inst["id"], "PART-1", 7)
        self.assertEqual(
            set(record.keys()),
            {"id", "commons_id", "instrument_id", "participant_ref",
             "responses_reported", "response_content_held_here",
             "created_by", "created_utc"})
        self.assertIs(record["response_content_held_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_outcome_response_count(
                MEMBER, self.cid, inst["id"], "PART-1", True)


class TestClinicalSummary(BatchFixture):
    """Idx 834 — clinical-trial reporting & analytics (built)."""

    def test_summary_counts(self):
        form = self.ext.define_capture_form(
            MEMBER, self.cid, "FORM-AE", "Adverse events", ["field:a"])
        self.ext.record_submission(
            MEMBER, self.cid, form["id"], "SITE-1", 10, queries_reported=2)
        self.ext.record_submission(
            MEMBER, self.cid, form["id"], "SITE-2", 4,
            recorded_status="reported_partial")
        inst = self.ext.define_consent_instrument(
            MEMBER, self.cid, "CONSENT-MAIN", "v3")
        self.ext.record_consent_state(
            MEMBER, self.cid, inst["id"], "PART-1", "reported_pending")
        self.ext.record_consent_state(
            MEMBER, self.cid, inst["id"], "PART-1", "reported_consented")
        self.ext.record_consent_state(
            MEMBER, self.cid, inst["id"], "PART-2", "reported_declined")
        outcome = self.ext.define_outcome_instrument(
            MEMBER, self.cid, "QOL-1", "diary")
        self.ext.record_outcome_response_count(
            MEMBER, self.cid, outcome["id"], "PART-1", 5)
        summary = self.ext.clinical_summary(MEMBER, self.cid)
        self.assertEqual(summary["capture_forms"], 1)
        self.assertEqual(summary["submissions"], 2)
        self.assertEqual(
            summary["submissions_by_recorded_status"],
            {"reported_submitted": 1, "reported_partial": 1})
        self.assertEqual(summary["fields_reported_total"], 14)
        self.assertEqual(summary["queries_reported_total"], 2)
        self.assertEqual(summary["consent_current_states"],
                         {"reported_consented": 1, "reported_declined": 1})
        self.assertEqual(summary["outcome_responses_reported_total"], 5)
        self.assertEqual(summary["method"], "deterministic_counts")


class TestIdentityResolution(BatchFixture):
    """Idx 835 — identity resolution & background investigation (built)."""

    def test_linkage_pair_is_reported_never_computed(self):
        pair = self.ext.record_linkage_pair(
            MEMBER, self.cid, "REF-LEFT", "REF-RIGHT",
            "reported_token_match", "vendor linkage export")
        self.assertIs(pair["match_computed_here"], False)
        self.assertIs(pair["identity_verified_here"], False)
        counts = self.ext.linkage_counts(MEMBER, self.cid)
        self.assertEqual(counts["pair_count"], 1)
        self.assertEqual(counts["by_method"], {"reported_token_match": 1})

    def test_linkage_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.record_linkage_pair(
                MEMBER, self.cid, "SAME", "SAME", "reported_token_match",
                "export")
        with self.assertRaises(ValidationError):
            self.ext.record_linkage_pair(
                MEMBER, self.cid, "A", "B", "computed_match", "export")
        pair = self.ext.record_linkage_pair(
            MEMBER, self.cid, "A", "B", "reported_key_match", "export")
        self.assertEqual(pair["id"], "lnk-1")

    def test_investigation_case_lifecycle(self):
        case = self.ext.open_investigation_case(
            MEMBER, self.cid, "CASE-1", "SUBJECT-REF-1")
        self.assertIs(case["searched_here"], False)
        self.assertIs(case["verified_here"], False)
        finding = self.ext.record_investigation_finding(
            STAFF, case["id"], "credential reported active")
        self.assertEqual(finding["finding_label"],
                         "credential reported active")
        self.assertIs(finding["verified_here"], False)
        closed = self.ext.close_investigation_case(
            ADMIN, case["id"], "reported_complete")
        self.assertEqual(closed["state"], "closed")
        self.assertEqual(closed["outcome_label"], "reported_complete")
        view = self.ext.investigation_case_view(MEMBER, case["id"])
        self.assertEqual(view["finding_count"], 1)
        with self.assertRaises(ValidationError):
            self.ext.record_investigation_finding(
                STAFF, case["id"], "late finding")


class TestMonitoringReference(BatchFixture):
    """Idx 836 — ongoing identity monitoring (reference)."""

    def test_stub_labels_pinned(self):
        record = self.ext.record_monitoring_reference(
            MEMBER, self.cid, "SUBJECT-REF-1", "monitoring bureau feed")
        self.assertIs(record["reference_stub"], True)
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIs(record["monitoring_active_here"], False)
        self.assertIs(record["alerts_sent_here"], False)


class TestSupplier(BatchFixture):
    """Idx 837 (reference) and 838 (built) — supplier discovery
    & intelligence."""

    def test_discovery_reference_labels(self):
        record = self.ext.record_discovery_reference(
            MEMBER, self.cid, "INQUIRY-1", "additive manufacturing")
        self.assertIs(record["reference_stub"], True)
        self.assertIs(record["discovery_performed_here"], False)
        self.assertIs(record["searched_here"], False)

    def test_capability_counts_and_lookup(self):
        self.ext.record_supplier_profile(
            MEMBER, self.cid, "SUP-1", ["3d_printing", "cnc"], "profile db")
        self.ext.record_supplier_profile(
            MEMBER, self.cid, "SUP-2", ["cnc"], "profile db")
        counts = self.ext.supplier_capability_counts(MEMBER, self.cid)
        self.assertEqual(counts["supplier_count"], 2)
        self.assertEqual(counts["by_capability"],
                         {"3d_printing": 1, "cnc": 2})
        found = self.ext.suppliers_with_capability(
            MEMBER, self.cid, "3d_printing")
        self.assertEqual(found["supplier_refs"], ["SUP-1"])
        self.assertEqual(found["method"], "recorded_label_lookup")
        self.assertIs(found["evaluated_here"], False)

    def test_duplicate_supplier_rejected(self):
        self.ext.record_supplier_profile(
            MEMBER, self.cid, "SUP-1", ["cnc"], "profile db")
        with self.assertRaises(ValidationError):
            self.ext.record_supplier_profile(
                MEMBER, self.cid, "SUP-1", ["laser"], "profile db")


class TestSurfacePins(BatchFixture):
    """Cross-cutting pins: shapes, tier null, RBAC, commons scope."""

    def _one_of_each(self):
        ext, cid = self.ext, self.cid
        records = {}
        records["intelligence"] = ext.record_intelligence_item(
            MEMBER, cid, "policy_item", "POL-1", "feed", "detail:1")
        prime = ext.record_award(MEMBER, cid, "AWARD-1", "ORG-A",
                                 "prime", 100)
        records["award"] = prime
        entity = ext.register_entity(MEMBER, cid, "ENT-A", "organization")
        other = ext.register_entity(MEMBER, cid, "ENT-B", "program")
        records["entity"] = entity
        records["relationship"] = ext.record_relationship(
            MEMBER, cid, entity["id"], other["id"], "funds")
        records["saved_search"] = ext.record_saved_search(
            MEMBER, cid, "SEARCH-1", "awards")
        records["tracking"] = ext.record_entity_tracking(
            MEMBER, cid, entity["id"], "watch")
        form = ext.define_capture_form(MEMBER, cid, "FORM-1", "Form",
                                       ["field:a"])
        records["form"] = form
        records["submission"] = ext.record_submission(
            MEMBER, cid, form["id"], "SITE-1", 3)
        consent = ext.define_consent_instrument(MEMBER, cid, "CONSENT-1",
                                                "v1")
        records["consent_instrument"] = consent
        records["consent_state"] = ext.record_consent_state(
            MEMBER, cid, consent["id"], "PART-1", "reported_consented")
        outcome = ext.define_outcome_instrument(MEMBER, cid, "QOL-1",
                                                "diary")
        records["outcome_instrument"] = outcome
        records["outcome_response"] = ext.record_outcome_response_count(
            MEMBER, cid, outcome["id"], "PART-1", 2)
        records["linkage"] = ext.record_linkage_pair(
            MEMBER, cid, "L-1", "R-1", "reported_token_match", "export")
        case = ext.open_investigation_case(MEMBER, cid, "CASE-1",
                                           "SUBJECT-1")
        records["case"] = case
        records["finding"] = ext.record_investigation_finding(
            STAFF, case["id"], "label as reported")
        records["monitoring"] = ext.record_monitoring_reference(
            MEMBER, cid, "SUBJECT-1", "feed")
        records["discovery"] = ext.record_discovery_reference(
            MEMBER, cid, "INQ-1", "scope")
        records["supplier"] = ext.record_supplier_profile(
            MEMBER, cid, "SUP-1", ["cnc"], "db")
        views = [
            ext.intelligence_summary(MEMBER, cid),
            ext.award_analysis(MEMBER, cid),
            ext.entity_view(MEMBER, entity["id"]),
            ext.relationship_counts(MEMBER, cid),
            ext.list_neighbors(MEMBER, entity["id"]),
            ext.form_view(MEMBER, form["id"]),
            ext.consent_current_state(MEMBER, consent["id"], "PART-1"),
            ext.clinical_summary(MEMBER, cid),
            ext.linkage_counts(MEMBER, cid),
            ext.investigation_case_view(MEMBER, case["id"]),
            ext.supplier_capability_counts(MEMBER, cid),
            ext.suppliers_with_capability(MEMBER, cid, "cnc"),
        ]
        return records, views

    def test_no_tier_or_score_shaped_key_anywhere(self):
        records, views = self._one_of_each()
        for structure in list(records.values()) + views:
            for path, key in _scan_keys(structure):
                for fragment in FORBIDDEN_KEY_FRAGMENTS:
                    self.assertNotIn(
                        fragment, key.lower(),
                        "%s key %r at %s carries forbidden fragment %r"
                        % (type(structure), key, path, fragment))

    def test_unexpected_keyword_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_intelligence_item(
                MEMBER, self.cid, "policy_item", "POL-1", "feed",
                "detail:1", diagnosis="smuggled")
        with self.assertRaises(TypeError):
            self.ext.record_consent_state(
                MEMBER, self.cid, "cin-1", "PART-1",
                "reported_consented", signature=b"bytes")
        with self.assertRaises(TypeError):
            self.ext.record_linkage_pair(
                MEMBER, self.cid, "A", "B", "reported_key_match",
                "export", ssn="000-00-0000")

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_intelligence_item(
                VIEWER, self.cid, "policy_item", "POL-1", "feed",
                "detail:1")
        self.assertIn("ext_intelligence_record:denied",
                      self.audit_actions())

    def test_outsider_denied_by_commons_boundary(self):
        with self.assertRaises(PermissionDenied):
            self.ext.list_intelligence_items(OUTSIDER, self.cid)
        with self.assertRaises(PermissionDenied):
            self.ext.record_award(OUTSIDER, self.cid, "AWARD-1",
                                  "ORG-A", "prime", 100)

    def test_no_record_carries_a_status_on_consent_states(self):
        inst = self.ext.define_consent_instrument(
            MEMBER, self.cid, "CONSENT-1", "v1")
        self.ext.record_consent_state(
            MEMBER, self.cid, inst["id"], "PART-1", "reported_pending")
        for record in self.ext._consent_states.values():
            self.assertEqual(
                set(record.keys()),
                {"id", "commons_id", "instrument_id", "participant_ref",
                 "state_label", "signature_held_here",
                 "consent_effected_here", "created_by", "created_utc"})


class MutantConsentExtensions(ResearchExtensions):
    """The negative control's mutant: current consent state reads
    the EARLIEST recorded state instead of the latest."""

    def _current_consent_label(self, history):
        return history[0]["state_label"]


class TestConsentDerivationNegativeControl(unittest.TestCase):
    """Fresh mutation-verified negative control (batch).

    Canonical expectation: with states [reported_pending,
    reported_consented] recorded in that order, the derived
    current state is the LATEST label, ``reported_consented`` --
    in the consent view and in the clinical summary's consent
    counts. The mutant (earliest-label derivation) must NOT
    produce that outcome, and treating the mutant's outcome as
    the expected outcome must fail.
    """

    def _build(self, ext_class):
        store, commons, _org = make_store()
        ext = ext_class(store)
        inst = ext.define_consent_instrument(
            MEMBER, commons["id"], "CONSENT-MAIN", "v3")
        ext.record_consent_state(
            MEMBER, commons["id"], inst["id"], "PART-1",
            "reported_pending")
        ext.record_consent_state(
            MEMBER, commons["id"], inst["id"], "PART-1",
            "reported_consented")
        return ext, commons, inst

    def test_current_state_is_latest_canonical(self):
        ext, commons, inst = self._build(ResearchExtensions)
        view = ext.consent_current_state(MEMBER, inst["id"], "PART-1")
        self.assertEqual(view["current_state"], "reported_consented")

    def test_mutant_reads_earliest_not_latest(self):
        ext, commons, inst = self._build(MutantConsentExtensions)
        view = ext.consent_current_state(MEMBER, inst["id"], "PART-1")
        self.assertEqual(view["current_state"], "reported_pending")

    def test_canonical_expectation_rejects_mutant(self):
        ext, commons, inst = self._build(MutantConsentExtensions)
        view = ext.consent_current_state(MEMBER, inst["id"], "PART-1")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_state"], "reported_consented")

    def test_mutant_changes_clinical_summary_counts(self):
        canonical, commons, _inst = self._build(ResearchExtensions)
        mutant, _commons2, _inst2 = self._build(MutantConsentExtensions)
        self.assertEqual(
            canonical.clinical_summary(MEMBER, commons["id"])
            ["consent_current_states"],
            {"reported_consented": 1})
        self.assertEqual(
            mutant.clinical_summary(MEMBER, commons["id"])
            ["consent_current_states"],
            {"reported_pending": 1})


if __name__ == "__main__":
    unittest.main()
