"""Final GAPS batch tests — Research L1 singleton (Remainder
Singleton 63).

Pins the extension surface in ``src/research/extensions.py`` per
GAPS.md section entry (inventory idx 714–724; see ``../BATCH.md``
for the per-entry disposition), the founding privacy discipline
(no record shape can hold a study's content — no title or
abstract text, no protocol prose, no extracted value, no result,
no score; every entity shape is pinned to its exact key set, and
an unexpected keyword argument raises ``TypeError``), and the
human-in-the-loop pin: recording a suggestion or a human decision
leaves the screening record it concerns byte-identical.

The batch's fresh negative control lives here:
``TestProtocolCurrencyNegativeControl`` mutates the extension's
single protocol-currency seam (``_current_protocol_record``) to
read the EARLIEST version instead of the latest, and pins that
the canonical expectations reject the mutant's outcomes.
"""

import copy
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

# Key fragments no extension record or view may carry: they are
# the shapes of fields that could hold a score or study content.
# ("title_abstract" is a stage LABEL used as a count key in
# summaries, not a content field, so the abstract fragment is the
# field-shaped "abstract_text".)
FORBIDDEN_KEY_FRAGMENTS = ("score", "rank", "payload",
                           "abstract_text", "content", "effect_size",
                           "p_value", "extracted_data", "study_title",
                           "result_text")


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

    def make_program(self, ref="REVIEWS-2026"):
        return self.ext.create_review_program(
            MEMBER, self.cid, ref, "Systematic review program")

    def make_protocol(self, program, ref="PROTO-1",
                      criteria=("CRIT-1", "CRIT-2")):
        return self.ext.create_protocol(
            MEMBER, program["id"], ref, list(criteria))


class TestPrograms(BatchFixture):
    """Idx 722 — project / team / role administration (built)."""

    def test_create_members_and_summary(self):
        program = self.make_program()
        self.assertEqual(program["id"], "prg-1")
        self.ext.add_program_member(MEMBER, program["id"], "REVIEWER-1",
                                    "lead_reviewer")
        self.ext.add_program_member(STAFF, program["id"], "REVIEWER-2",
                                    "screener")
        self.ext.add_program_member(MEMBER, program["id"], "REVIEWER-1",
                                    "extractor")
        members = self.ext.list_program_members(MEMBER, program["id"])
        self.assertEqual(len(members), 3)
        summary = self.ext.program_summary(MEMBER, program["id"])
        self.assertEqual(summary["members"], 3)
        self.assertEqual(summary["members_by_role"],
                         {"lead_reviewer": 1, "screener": 1,
                          "extractor": 1})
        self.assertEqual(summary["protocols"], 0)
        self.assertEqual(summary["method"], "deterministic_counts")

    def test_duplicate_membership_refused(self):
        program = self.make_program()
        self.ext.add_program_member(MEMBER, program["id"], "REVIEWER-1",
                                    "screener")
        with self.assertRaises(ValidationError):
            self.ext.add_program_member(MEMBER, program["id"],
                                        "REVIEWER-1", "screener")

    def test_program_ref_unique_and_no_id_consumed(self):
        self.make_program()
        with self.assertRaises(ValidationError):
            self.make_program()
        second = self.make_program("REVIEWS-2027")
        self.assertEqual(second["id"], "prg-2")

    def test_shape_pinned(self):
        program = self.make_program()
        self.assertEqual(
            set(program.keys()),
            {"id", "commons_id", "program_ref", "label", "created_by",
             "created_utc"})
        member = self.ext.add_program_member(
            MEMBER, program["id"], "REVIEWER-1", "screener")
        self.assertEqual(
            set(member.keys()),
            {"id", "commons_id", "program_id", "member_ref",
             "role_label", "created_by", "created_utc"})

    def test_member_takes_no_identity_fields(self):
        program = self.make_program()
        with self.assertRaises(TypeError):
            self.ext.add_program_member(
                MEMBER, program["id"], "REVIEWER-1", "screener",
                email="someone@example.org")


class TestProtocols(BatchFixture):
    """Idx 719 — review protocol creation (built)."""

    def test_create_shape_and_view(self):
        program = self.make_program()
        protocol = self.make_protocol(program)
        self.assertEqual(protocol["id"], "pro-1")
        self.assertEqual(protocol["version"], 1)
        self.assertIs(protocol["protocol_text_held_here"], False)
        self.assertEqual(
            set(protocol.keys()),
            {"id", "commons_id", "program_id", "protocol_ref",
             "version", "criteria_refs", "protocol_text_held_here",
             "created_by", "created_utc"})
        view = self.ext.protocol_view(MEMBER, protocol["id"])
        self.assertEqual(view["criterion_count"], 2)
        self.assertEqual(view["latest_version"], 1)
        self.assertIs(view["is_latest"], True)
        stored = self.ext._protocols[protocol["id"]]
        self.assertNotIn("latest_version", stored)
        self.assertNotIn("is_latest", stored)

    def test_criteria_validated(self):
        program = self.make_program()
        with self.assertRaises(ValidationError):
            self.ext.create_protocol(MEMBER, program["id"], "P-1",
                                     ["CRIT-1", "CRIT-1"])
        with self.assertRaises(ValidationError):
            self.ext.create_protocol(MEMBER, program["id"], "P-1", [])
        protocol = self.make_protocol(program)
        self.assertEqual(protocol["id"], "pro-1")

    def test_revise_appends_and_create_refused_for_existing_ref(self):
        program = self.make_program()
        v1 = self.make_protocol(program)
        v2 = self.ext.revise_protocol(MEMBER, v1["id"],
                                      ["CRIT-1", "CRIT-2", "CRIT-3"])
        self.assertEqual(v2["version"], 2)
        self.assertEqual(v2["criteria_refs"],
                         ["CRIT-1", "CRIT-2", "CRIT-3"])
        original = self.ext.get_protocol(MEMBER, v1["id"])
        self.assertEqual(original["criteria_refs"], ["CRIT-1", "CRIT-2"])
        with self.assertRaises(ValidationError):
            self.make_protocol(program)
        listed = self.ext.list_protocols(MEMBER, self.cid)
        self.assertEqual([p["version"] for p in listed], [1, 2])

    def test_current_protocol_is_latest_version(self):
        program = self.make_program()
        v1 = self.make_protocol(program)
        self.ext.revise_protocol(MEMBER, v1["id"], ["CRIT-9"])
        current = self.ext.current_protocol(MEMBER, self.cid, "PROTO-1")
        self.assertEqual(current["version"], 2)
        self.assertEqual(current["criteria_refs"], ["CRIT-9"])
        self.assertIs(current["is_latest"], True)

    def test_protocol_view_derived_currency(self):
        program = self.make_program()
        v1 = self.make_protocol(program)
        v2 = self.ext.revise_protocol(MEMBER, v1["id"], ["CRIT-9"])
        view1 = self.ext.protocol_view(MEMBER, v1["id"])
        self.assertEqual(view1["latest_version"], 2)
        self.assertIs(view1["is_latest"], False)
        view2 = self.ext.protocol_view(MEMBER, v2["id"])
        self.assertIs(view2["is_latest"], True)


class TestScreening(BatchFixture):
    """Idx 716 — title/abstract & full-text screening pipeline
    (built)."""

    def setUp(self):
        super().setUp()
        self.program = self.make_program()
        self.protocol = self.make_protocol(self.program)

    def _record(self, study="STUDY-1", stage="title_abstract",
                label="reported_include", reviewer="REVIEWER-1",
                protocol=None):
        return self.ext.record_screening_decision(
            MEMBER, self.program["id"],
            (protocol or self.protocol)["id"], study, stage, label,
            reviewer)

    def test_record_and_summary(self):
        first = self._record()
        self.assertEqual(first["id"], "scr-1")
        self.assertIs(first["screened_by_engine"], False)
        self.assertEqual(
            set(first.keys()),
            {"id", "commons_id", "program_id", "protocol_id",
             "study_ref", "stage", "decision_label", "reviewer_ref",
             "screened_by_engine", "created_by", "created_utc"})
        self._record(label="reported_exclude", reviewer="REVIEWER-2")
        self._record(study="STUDY-2", stage="full_text")
        summary = self.ext.screening_summary(MEMBER, self.program["id"])
        self.assertEqual(summary["records"], 3)
        self.assertEqual(summary["studies"], 2)
        self.assertEqual(
            summary["by_stage"],
            {"title_abstract": {"reported_include": 1,
                                "reported_exclude": 1},
             "full_text": {"reported_include": 1}})
        self.assertIs(summary["advanced_automatically_here"], False)

    def test_duplicate_reviewer_decision_refused_no_id(self):
        self._record()
        with self.assertRaises(ValidationError):
            self._record(label="reported_exclude")
        second = self._record(reviewer="REVIEWER-2")
        self.assertEqual(second["id"], "scr-2")

    def test_stage_and_label_validated(self):
        with self.assertRaises(ValidationError):
            self._record(stage="abstract_only")
        with self.assertRaises(ValidationError):
            self._record(label="include")

    def test_full_text_needs_no_title_abstract_record(self):
        # The pipeline moves nothing automatically: stages are
        # independent records a human workflow drives.
        record = self._record(stage="full_text")
        self.assertEqual(record["stage"], "full_text")

    def test_protocol_of_other_program_refused(self):
        other = self.make_program("REVIEWS-2027")
        foreign = self.make_protocol(other, ref="PROTO-OTHER")
        with self.assertRaises(ValidationError):
            self._record(protocol=foreign)

    def test_screening_against_current_version_accepted(self):
        v2 = self.ext.revise_protocol(MEMBER, self.protocol["id"],
                                      ["CRIT-1", "CRIT-2", "CRIT-3"])
        record = self._record(protocol=v2)
        self.assertEqual(record["protocol_id"], v2["id"])

    def test_screening_against_superseded_version_refused(self):
        self.ext.revise_protocol(MEMBER, self.protocol["id"], ["CRIT-9"])
        with self.assertRaises(ValidationError):
            self._record()


class TestExtraction(BatchFixture):
    """Idx 717 — data extraction from studies (built)."""

    def setUp(self):
        super().setUp()
        self.program = self.make_program()
        self.form = self.ext.define_extraction_form(
            MEMBER, self.program["id"], "FORM-1",
            ["FIELD-A", "FIELD-B", "FIELD-C"])

    def test_form_view_derives_field_count(self):
        self.assertEqual(self.form["id"], "exf-1")
        self.assertIs(self.form["values_held_here"], False)
        view = self.ext.extraction_form_view(MEMBER, self.form["id"])
        self.assertEqual(view["field_count"], 3)
        self.assertNotIn("field_count", self.ext._extraction_forms["exf-1"])

    def test_record_and_summary(self):
        record = self.ext.record_extraction(
            MEMBER, self.form["id"], "STUDY-1", ["FIELD-A", "FIELD-B"],
            "reported_in_progress", "EXTRACTOR-1")
        self.assertEqual(record["id"], "exr-1")
        self.assertIs(record["values_held_here"], False)
        self.assertEqual(
            set(record.keys()),
            {"id", "commons_id", "program_id", "form_id", "study_ref",
             "field_refs", "state_label", "extractor_ref",
             "values_held_here", "created_by", "created_utc"})
        self.ext.record_extraction(
            MEMBER, self.form["id"], "STUDY-1",
            ["FIELD-A", "FIELD-B", "FIELD-C"], "reported_complete",
            "EXTRACTOR-1")
        summary = self.ext.extraction_summary(MEMBER, self.program["id"])
        self.assertEqual(summary["records"], 2)
        self.assertEqual(summary["fields_addressed"], 5)
        self.assertEqual(summary["by_state"],
                         {"reported_in_progress": 1,
                          "reported_complete": 1})

    def test_unknown_field_and_bad_state_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.record_extraction(
                MEMBER, self.form["id"], "STUDY-1", ["FIELD-Z"],
                "reported_in_progress", "EXTRACTOR-1")
        with self.assertRaises(ValidationError):
            self.ext.record_extraction(
                MEMBER, self.form["id"], "STUDY-1", [],
                "extracted", "EXTRACTOR-1")

    def test_no_value_can_be_supplied(self):
        with self.assertRaises(TypeError):
            self.ext.record_extraction(
                MEMBER, self.form["id"], "STUDY-1", ["FIELD-A"],
                "reported_in_progress", "EXTRACTOR-1", value="42")
        with self.assertRaises(TypeError):
            self.ext.define_extraction_form(
                MEMBER, self.program["id"], "FORM-2", ["FIELD-A"],
                field_values=["x"])


class TestExportManifests(BatchFixture):
    """Idx 720 — meta-analysis export (built)."""

    def setUp(self):
        super().setUp()
        self.program = self.make_program()
        self.protocol = self.make_protocol(self.program)
        pid, proto = self.program["id"], self.protocol["id"]
        self.ext.record_screening_decision(
            MEMBER, pid, proto, "STUDY-1", "title_abstract",
            "reported_include", "REVIEWER-1")
        self.ext.record_screening_decision(
            MEMBER, pid, proto, "STUDY-1", "full_text",
            "reported_include", "REVIEWER-1")
        self.ext.record_screening_decision(
            MEMBER, pid, proto, "STUDY-2", "title_abstract",
            "reported_include", "REVIEWER-1")
        self.ext.record_screening_decision(
            MEMBER, pid, proto, "STUDY-2", "full_text",
            "reported_exclude", "REVIEWER-1")
        form = self.ext.define_extraction_form(
            MEMBER, pid, "FORM-1", ["FIELD-A", "FIELD-B"])
        self.ext.record_extraction(
            MEMBER, form["id"], "STUDY-1", ["FIELD-A", "FIELD-B"],
            "reported_complete", "EXTRACTOR-1")

    def test_manifest_view_counts(self):
        manifest = self.ext.create_export_manifest(
            MEMBER, self.program["id"], "EXPORT-1")
        self.assertEqual(manifest["id"], "exp-1")
        self.assertIs(manifest["reference_transport"], True)
        self.assertIs(manifest["exported_here"], False)
        self.assertIs(manifest["statistics_computed_here"], False)
        self.assertEqual(
            set(manifest.keys()),
            {"id", "commons_id", "program_id", "manifest_ref",
             "reference_transport", "exported_here",
             "statistics_computed_here", "created_by", "created_utc"})
        view = self.ext.export_manifest_view(MEMBER, manifest["id"])
        self.assertEqual(view["screening_records"], 4)
        self.assertEqual(view["studies_screened"], 2)
        # Only a full-text include counts; title/abstract includes
        # and full-text excludes do not.
        self.assertEqual(view["studies_with_full_text_include"], 1)
        self.assertEqual(view["extraction_records"], 1)
        self.assertEqual(view["fields_addressed"], 2)
        self.assertEqual(view["method"], "deterministic_counts")


class TestDictionaries(BatchFixture):
    """Idx 721 — shared dictionary management (built)."""

    def test_terms_revisions_and_summary(self):
        dictionary = self.ext.create_dictionary(
            MEMBER, self.cid, "DICT-1", "Review terminology")
        self.assertEqual(dictionary["id"], "dic-1")
        term = self.ext.add_term(MEMBER, dictionary["id"], "TERM-LIVING",
                                 "DEF-REF-1")
        self.assertEqual(term["revision"], 1)
        self.assertIs(term["definition_text_held_here"], False)
        revised = self.ext.revise_term(MEMBER, term["id"], "DEF-REF-2")
        self.assertEqual(revised["revision"], 2)
        with self.assertRaises(ValidationError):
            self.ext.add_term(MEMBER, dictionary["id"], "TERM-LIVING",
                              "DEF-REF-3")
        view_old = self.ext.term_view(MEMBER, term["id"])
        self.assertEqual(view_old["latest_revision"], 2)
        self.assertIs(view_old["is_latest"], False)
        view_new = self.ext.term_view(MEMBER, revised["id"])
        self.assertIs(view_new["is_latest"], True)
        current = self.ext.list_terms(MEMBER, dictionary["id"],
                                      current_only=True)
        self.assertEqual([t["id"] for t in current], [revised["id"]])
        summary = self.ext.dictionary_summary(MEMBER, dictionary["id"])
        self.assertEqual(summary["terms"], 1)
        self.assertEqual(summary["revisions"], 2)


class TestSuggestions(BatchFixture):
    """Idx 724 — human-in-the-loop AI suggestion surface (built)."""

    def setUp(self):
        super().setUp()
        self.program = self.make_program()
        self.protocol = self.make_protocol(self.program)
        self.screening = self.ext.record_screening_decision(
            MEMBER, self.program["id"], self.protocol["id"], "STUDY-1",
            "title_abstract", "reported_undecided", "REVIEWER-1")

    def test_suggestion_never_changes_screening_record(self):
        before_internal = copy.deepcopy(
            self.ext._screening_records[self.screening["id"]])
        before_view = self.ext.get_screening_record(
            MEMBER, self.screening["id"])
        suggestion = self.ext.record_suggestion(
            MEMBER, self.program["id"], "STUDY-1",
            "reported_suggest_include", "laser-engine report",
            screening_record_id=self.screening["id"])
        self.ext.record_human_decision(
            STAFF, suggestion["id"], "reported_rejected", "REVIEWER-1")
        after_internal = self.ext._screening_records[self.screening["id"]]
        after_view = self.ext.get_screening_record(
            MEMBER, self.screening["id"])
        self.assertEqual(before_internal, after_internal)
        self.assertEqual(before_view, after_view)

    def test_current_decision_derived_at_read(self):
        suggestion = self.ext.record_suggestion(
            MEMBER, self.program["id"], "STUDY-1",
            "reported_suggest_exclude", "laser-engine report")
        self.assertIs(suggestion["generated_here"], False)
        view = self.ext.suggestion_view(MEMBER, suggestion["id"])
        self.assertEqual(view["current_decision"], "undecided")
        self.assertEqual(view["decision_count"], 0)
        self.ext.record_human_decision(
            STAFF, suggestion["id"], "reported_rejected", "REVIEWER-1")
        self.ext.record_human_decision(
            STAFF, suggestion["id"], "reported_accepted", "REVIEWER-2")
        view = self.ext.suggestion_view(MEMBER, suggestion["id"])
        self.assertEqual(view["current_decision"], "reported_accepted")
        self.assertEqual(view["decision_count"], 2)
        stored = self.ext._suggestions[suggestion["id"]]
        self.assertNotIn("current_decision", stored)
        self.assertNotIn("decision_count", stored)
        summary = self.ext.suggestion_summary(MEMBER, self.program["id"])
        self.assertEqual(summary["by_current_decision"],
                         {"reported_accepted": 1})

    def test_labels_validated(self):
        with self.assertRaises(ValidationError):
            self.ext.record_suggestion(
                MEMBER, self.program["id"], "STUDY-1", "include",
                "laser-engine report")
        suggestion = self.ext.record_suggestion(
            MEMBER, self.program["id"], "STUDY-1",
            "reported_suggest_review", "laser-engine report")
        with self.assertRaises(ValidationError):
            self.ext.record_human_decision(
                STAFF, suggestion["id"], "accepted", "REVIEWER-1")

    def test_decision_requires_decide_permission(self):
        suggestion = self.ext.record_suggestion(
            MEMBER, self.program["id"], "STUDY-1",
            "reported_suggest_review", "laser-engine report")
        with self.assertRaises(PermissionDenied):
            self.ext.record_human_decision(
                VIEWER, suggestion["id"], "reported_accepted",
                "REVIEWER-1")
        self.assertIn("ext_human_decision_record:denied",
                      self.audit_actions())

    def test_no_generated_text_can_be_supplied(self):
        with self.assertRaises(TypeError):
            self.ext.record_suggestion(
                MEMBER, self.program["id"], "STUDY-1",
                "reported_suggest_include", "laser-engine report",
                generated_text="the engine says include it")


class TestAutomationStub(BatchFixture):
    """Idx 714 — systematic review automation engine (reference)."""

    def test_reference_labels_and_events(self):
        program = self.make_program()
        reference = self.ext.record_automation_reference(
            MEMBER, program["id"], "AUTO-1", "vendor status page")
        self.assertEqual(reference["id"], "aut-1")
        self.assertIs(reference["reference_stub"], True)
        self.assertEqual(reference["state"], "recorded_reference_only")
        self.assertIs(reference["automation_active_here"], False)
        self.assertIs(reference["reviews_updated_here"], False)
        event = self.ext.record_automation_event(
            MEMBER, reference["id"], "reported_new_evidence")
        self.assertIs(event["reference_stub"], True)
        self.assertIs(event["applied_here"], False)
        events = self.ext.list_automation_events(MEMBER, reference["id"])
        self.assertEqual([e["id"] for e in events], [event["id"]])

    def test_stub_changes_no_built_records(self):
        program = self.make_program()
        protocol = self.make_protocol(program)
        self.ext.record_screening_decision(
            MEMBER, program["id"], protocol["id"], "STUDY-1",
            "title_abstract", "reported_include", "REVIEWER-1")
        before = self.ext.screening_summary(MEMBER, program["id"])
        reference = self.ext.record_automation_reference(
            MEMBER, program["id"], "AUTO-1", "vendor status page")
        self.ext.record_automation_event(
            MEMBER, reference["id"], "reported_new_evidence")
        after = self.ext.screening_summary(MEMBER, program["id"])
        self.assertEqual(before, after)


class TestSearchStrategyStub(BatchFixture):
    """Idx 715 — literature search-strategy execution (reference)."""

    def test_reference_labels_and_execution(self):
        program = self.make_program()
        strategy = self.ext.record_search_strategy(
            MEMBER, program["id"], "STRAT-1", "QUERY-REF-1",
            ["SRC-1", "SRC-2"])
        self.assertEqual(strategy["id"], "sst-1")
        self.assertIs(strategy["reference_stub"], True)
        self.assertIs(strategy["executed_here"], False)
        self.assertIs(strategy["strategy_text_held_here"], False)
        run = self.ext.record_strategy_execution(
            MEMBER, strategy["id"], "run-2026-06", 412)
        self.assertEqual(run["results_reported"], 412)
        self.assertIs(run["executed_here"], False)
        self.assertIs(run["searched_here"], False)
        runs = self.ext.list_strategy_executions(MEMBER, strategy["id"])
        self.assertEqual(len(runs), 1)

    def test_reported_count_validated(self):
        program = self.make_program()
        strategy = self.ext.record_search_strategy(
            MEMBER, program["id"], "STRAT-1", "QUERY-REF-1", ["SRC-1"])
        with self.assertRaises(ValidationError):
            self.ext.record_strategy_execution(
                MEMBER, strategy["id"], "run-x", -1)
        with self.assertRaises(ValidationError):
            self.ext.record_strategy_execution(
                MEMBER, strategy["id"], "run-x", 1.5)


class TestQualityStub(BatchFixture):
    """Idx 718 — quality assessment & regulator verification
    support (reference)."""

    def test_criteria_outcome_verification(self):
        program = self.make_program()
        criteria = self.ext.record_quality_criteria(
            MEMBER, program["id"], "QA-SET-1", ["CRIT-1", "CRIT-2"])
        self.assertIs(criteria["reference_stub"], True)
        self.assertIs(criteria["assessed_here"], False)
        outcome = self.ext.record_quality_outcome(
            MEMBER, criteria["id"], "REVIEW-REF-1", "reported_meets",
            "ASSESSOR-1")
        self.assertIs(outcome["assessed_here"], False)
        self.assertIs(outcome["verified_here"], False)
        verification = self.ext.record_quality_verification(
            MEMBER, outcome["id"], "reported_verified", "REGULATOR-1")
        self.assertIs(verification["reference_stub"], True)
        self.assertIs(verification["verified_here"], False)
        summary = self.ext.quality_summary(MEMBER, program["id"])
        self.assertEqual(summary["criteria_sets"], 1)
        self.assertEqual(summary["outcomes_by_label"],
                         {"reported_meets": 1})
        self.assertEqual(summary["verifications"], 1)
        self.assertIs(summary["assessed_here"], False)

    def test_outcome_label_validated(self):
        program = self.make_program()
        criteria = self.ext.record_quality_criteria(
            MEMBER, program["id"], "QA-SET-1", ["CRIT-1"])
        with self.assertRaises(ValidationError):
            self.ext.record_quality_outcome(
                MEMBER, criteria["id"], "REVIEW-REF-1", "passed",
                "ASSESSOR-1")


class TestWorkflowStub(BatchFixture):
    """Idx 723 — customizable review workflows (reference)."""

    def test_definition_and_run_labels(self):
        program = self.make_program()
        workflow = self.ext.record_workflow_definition(
            MEMBER, program["id"], "WF-1", ["STEP-SCREEN", "STEP-EXTRACT"])
        self.assertEqual(workflow["id"], "wfd-1")
        self.assertIs(workflow["reference_stub"], True)
        self.assertIs(workflow["executed_here"], False)
        before = copy.deepcopy(self.ext._workflow_definitions["wfd-1"])
        run = self.ext.record_workflow_run(MEMBER, workflow["id"],
                                           "run-2026-06")
        self.assertIs(run["executed_here"], False)
        self.assertEqual(self.ext._workflow_definitions["wfd-1"], before)
        runs = self.ext.list_workflow_runs(MEMBER, workflow["id"])
        self.assertEqual(len(runs), 1)

    def test_duplicate_steps_refused(self):
        program = self.make_program()
        with self.assertRaises(ValidationError):
            self.ext.record_workflow_definition(
                MEMBER, program["id"], "WF-1", ["STEP-A", "STEP-A"])


class TestCrossCutting(BatchFixture):
    """Discipline pins across the whole extension surface."""

    def _one_of_each(self):
        program = self.make_program()
        protocol = self.make_protocol(program)
        screening = self.ext.record_screening_decision(
            MEMBER, program["id"], protocol["id"], "STUDY-1",
            "title_abstract", "reported_include", "REVIEWER-1")
        form = self.ext.define_extraction_form(
            MEMBER, program["id"], "FORM-1", ["FIELD-A"])
        extraction = self.ext.record_extraction(
            MEMBER, form["id"], "STUDY-1", ["FIELD-A"],
            "reported_complete", "EXTRACTOR-1")
        manifest = self.ext.create_export_manifest(
            MEMBER, program["id"], "EXPORT-1")
        dictionary = self.ext.create_dictionary(
            MEMBER, self.cid, "DICT-1", "Terms")
        term = self.ext.add_term(MEMBER, dictionary["id"], "TERM-1",
                                 "DEF-REF-1")
        suggestion = self.ext.record_suggestion(
            MEMBER, program["id"], "STUDY-1",
            "reported_suggest_include", "engine report",
            screening_record_id=screening["id"])
        decision = self.ext.record_human_decision(
            STAFF, suggestion["id"], "reported_accepted", "REVIEWER-1")
        automation = self.ext.record_automation_reference(
            MEMBER, program["id"], "AUTO-1", "status page")
        strategy = self.ext.record_search_strategy(
            MEMBER, program["id"], "STRAT-1", "QUERY-1", ["SRC-1"])
        criteria = self.ext.record_quality_criteria(
            MEMBER, program["id"], "QA-1", ["CRIT-1"])
        outcome = self.ext.record_quality_outcome(
            MEMBER, criteria["id"], "REVIEW-1", "reported_meets",
            "ASSESSOR-1")
        workflow = self.ext.record_workflow_definition(
            MEMBER, program["id"], "WF-1", ["STEP-A"])
        records = {
            "program": program, "protocol": protocol,
            "screening": screening, "form": form,
            "extraction": extraction, "manifest": manifest,
            "dictionary": dictionary, "term": term,
            "suggestion": suggestion, "decision": decision,
            "automation": automation, "strategy": strategy,
            "criteria": criteria, "outcome": outcome,
            "workflow": workflow,
        }
        views = [
            self.ext.protocol_view(MEMBER, protocol["id"]),
            self.ext.extraction_form_view(MEMBER, form["id"]),
            self.ext.export_manifest_view(MEMBER, manifest["id"]),
            self.ext.term_view(MEMBER, term["id"]),
            self.ext.suggestion_view(MEMBER, suggestion["id"]),
            self.ext.screening_summary(MEMBER, program["id"]),
            self.ext.extraction_summary(MEMBER, program["id"]),
            self.ext.suggestion_summary(MEMBER, program["id"]),
            self.ext.program_summary(MEMBER, program["id"]),
        ]
        return records, views

    def test_no_content_or_score_shaped_key_anywhere(self):
        records, views = self._one_of_each()
        for structure in list(records.values()) + views:
            for path, key in _scan_keys(structure):
                for fragment in FORBIDDEN_KEY_FRAGMENTS:
                    self.assertNotIn(
                        fragment, key.lower(),
                        "%s key %r at %s carries forbidden fragment %r"
                        % (type(structure), key, path, fragment))

    def test_unexpected_keyword_raises_type_error(self):
        program = self.make_program()
        protocol = self.make_protocol(program)
        with self.assertRaises(TypeError):
            self.ext.record_screening_decision(
                MEMBER, program["id"], protocol["id"], "STUDY-1",
                "title_abstract", "reported_include", "REVIEWER-1",
                study_title="A Randomized Trial of Something")
        with self.assertRaises(TypeError):
            self.ext.create_protocol(
                MEMBER, program["id"], "PROTO-2", ["CRIT-1"],
                text="inclusion: adults; exclusion: children")

    def test_viewer_write_denied_and_audited(self):
        program = self.make_program()
        protocol = self.make_protocol(program)
        with self.assertRaises(PermissionDenied):
            self.ext.record_screening_decision(
                VIEWER, program["id"], protocol["id"], "STUDY-1",
                "title_abstract", "reported_include", "REVIEWER-1")
        self.assertIn("ext_screening_record:denied", self.audit_actions())

    def test_outsider_denied_by_commons_boundary(self):
        program = self.make_program()
        with self.assertRaises(PermissionDenied):
            self.ext.list_review_programs(OUTSIDER, self.cid)
        with self.assertRaises(PermissionDenied):
            self.ext.create_review_program(
                OUTSIDER, self.cid, "REVIEWS-X", "Other program")

    def test_missing_program_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_protocol(MEMBER, "prg-99", "P-1", ["CRIT-1"])


class MutantProtocolExtensions(ResearchExtensions):
    """The negative control's mutant: protocol currency reads the
    EARLIEST recorded version instead of the latest."""

    def _current_protocol_record(self, versions):
        return versions[0]


class TestProtocolCurrencyNegativeControl(unittest.TestCase):
    """Fresh mutation-verified negative control (batch).

    Canonical expectation: with versions [1, 2] recorded in that
    order, the current protocol is version 2 — the current view
    shows version 2's criteria, and screening binds to version 2
    (accepted) while version 1 is refused as superseded. The
    mutant (earliest-version currency) must NOT produce those
    outcomes, and treating the mutant's outcomes as the expected
    outcomes must fail.
    """

    def _build(self, ext_class):
        store, commons, _org = make_store()
        ext = ext_class(store)
        program = ext.create_review_program(
            MEMBER, commons["id"], "REVIEWS-2026", "Review program")
        v1 = ext.create_protocol(MEMBER, program["id"], "PROTO-1",
                                 ["CRIT-1"])
        v2 = ext.revise_protocol(MEMBER, v1["id"], ["CRIT-1", "CRIT-2"])
        return ext, commons, program, v1, v2

    def test_canonical_current_is_latest(self):
        ext, commons, _program, _v1, _v2 = self._build(ResearchExtensions)
        current = ext.current_protocol(MEMBER, commons["id"], "PROTO-1")
        self.assertEqual(current["version"], 2)
        self.assertEqual(current["criteria_refs"], ["CRIT-1", "CRIT-2"])

    def test_mutant_current_is_earliest(self):
        ext, commons, _program, _v1, _v2 = \
            self._build(MutantProtocolExtensions)
        current = ext.current_protocol(MEMBER, commons["id"], "PROTO-1")
        self.assertEqual(current["version"], 1)

    def test_canonical_expectation_rejects_mutant(self):
        ext, commons, _program, _v1, _v2 = \
            self._build(MutantProtocolExtensions)
        current = ext.current_protocol(MEMBER, commons["id"], "PROTO-1")
        with self.assertRaises(AssertionError):
            self.assertEqual(current["version"], 2)

    def test_canonical_screening_binds_to_latest(self):
        ext, _commons, program, v1, v2 = self._build(ResearchExtensions)
        record = ext.record_screening_decision(
            MEMBER, program["id"], v2["id"], "STUDY-1",
            "title_abstract", "reported_include", "REVIEWER-1")
        self.assertEqual(record["protocol_id"], v2["id"])
        with self.assertRaises(ValidationError):
            ext.record_screening_decision(
                MEMBER, program["id"], v1["id"], "STUDY-2",
                "title_abstract", "reported_include", "REVIEWER-1")

    def test_mutant_screening_binds_to_earliest(self):
        ext, _commons, program, v1, v2 = \
            self._build(MutantProtocolExtensions)
        with self.assertRaises(ValidationError):
            ext.record_screening_decision(
                MEMBER, program["id"], v2["id"], "STUDY-1",
                "title_abstract", "reported_include", "REVIEWER-1")
        record = ext.record_screening_decision(
            MEMBER, program["id"], v1["id"], "STUDY-1",
            "title_abstract", "reported_include", "REVIEWER-1")
        self.assertEqual(record["protocol_id"], v1["id"])


if __name__ == "__main__":
    unittest.main()
