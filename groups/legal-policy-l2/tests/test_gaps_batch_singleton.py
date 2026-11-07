"""Final GAPS batch tests — Legal & Policy L2 founding singleton.

Pins the extension surface in ``src/legalpol/singleton_extensions.py``
per GAPS.md section "Singleton 49 -- Legal & Policy L2 (1 fork, new
category)" (inventory idx 485-490 and 492; idx 491 and 493 were
already closed ``re-scoped``; see ``../BATCH-SINGLETON49.md`` for the
per-entry disposition), and the founding privacy discipline: no
record shape can hold document content, corpus content, generated
text, a prompt, a model completion, or query text — every entity
shape is pinned to its exact key set, and an unexpected keyword
argument raises ``TypeError``.

The batch's fresh negative control lives here:
``TestCurationDerivationNegativeControl`` mutates the extension's
single curation-derivation seam (``_current_curation_label``) to
read the EARLIEST recorded event instead of the latest, and pins
that the canonical expectations reject the mutant's outcomes.
"""

import unittest

from legalpol.errors import (
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from legalpol.singleton_extensions import LegalPolSingletonExtensions

from legalpol_helpers import (
    ADMIN,
    DOC_SHA256,
    MEMBER,
    OUTSIDER,
    QUERY_SHA256,
    SHA256_A,
    VIEWER,
    make_session,
    make_store,
    make_workspace,
)

FORBIDDEN_KEY_FRAGMENTS = (
    "signature", "query", "summary", "score", "extracted_text",
    "content_text", "document_content", "raw_content",
    "document_text", "generated_text", "prompt_text",
    "completion_text", "corpus_text", "source_text",
)


def make_singleton():
    """Fresh store + canonical agency/workspace + extension surface."""
    store, audit, agency = make_store()
    workspace = make_workspace(store, agency)
    return LegalPolSingletonExtensions(store), store, audit, agency, workspace


def make_source(store, source_ref="LIB-REF-001", kind="statute"):
    return store.register_library_source(
        source_ref, kind, ADMIN, title="United States Code")


def make_document(store, agency, workspace, doc_ref="DOC-REF-001",
                  kind="generated"):
    return store.register_document(
        agency["id"], workspace["id"], doc_ref, DOC_SHA256, 128, MEMBER,
        kind=kind)


def _scan_keys(value, path="root"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, key
            yield from _scan_keys(item, path + "." + str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _scan_keys(item, "%s[%d]" % (path, index))


class TestCorpusContent(unittest.TestCase):
    """Idx 486 (built): corpus content as a registry over core
    library sources — extent as reported, curation events, license
    records; the content itself is never held."""

    def setUp(self):
        self.ext, self.store, self.audit, self.agency, self.ws = \
            make_singleton()
        self.source = make_source(self.store)

    def test_content_record_shape_and_flags(self):
        record = self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-001", 1204,
            content_sha256=SHA256_A)
        self.assertEqual(
            set(record),
            {"id", "source_id", "content_ref", "reported_item_count",
             "content_sha256", "content_held_here", "curated_here",
             "licensed_here", "created_by", "created_utc"})
        self.assertEqual(record["id"], "cor-1")
        self.assertEqual(record["reported_item_count"], 1204)
        self.assertIs(record["content_held_here"], False)
        self.assertIs(record["curated_here"], False)
        self.assertIs(record["licensed_here"], False)

    def test_digest_and_count_discipline(self):
        with self.assertRaises(ValidationError):
            self.ext.register_corpus_content(
                ADMIN, self.source["id"], "COR-REF-001", 10,
                content_sha256="not-a-digest")
        with self.assertRaises(ValidationError):
            self.ext.register_corpus_content(
                ADMIN, self.source["id"], "COR-REF-001", True)
        with self.assertRaises(ValidationError):
            self.ext.register_corpus_content(
                ADMIN, self.source["id"], "COR-REF-001", 2.5)
        with self.assertRaises(NotFoundError):
            self.ext.register_corpus_content(
                ADMIN, "lib-999", "COR-REF-001", 10)

    def test_duplicate_ref_rejected_and_no_id_consumed(self):
        first = self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-001", 10)
        with self.assertRaises(ValidationError):
            self.ext.register_corpus_content(
                ADMIN, self.source["id"], "COR-REF-001", 20)
        second = self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-002", 20)
        self.assertEqual(first["id"], "cor-1")
        self.assertEqual(second["id"], "cor-2")

    def test_stored_record_carries_no_derived_state(self):
        record = self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-001", 10)
        self.ext.record_curation_event(
            ADMIN, record["id"], "CEV-REF-001", "reported_added")
        stored = self.ext.get_corpus_content(ADMIN, record["id"])
        self.assertNotIn("current_curation_state", stored)
        self.assertNotIn("is_withdrawn", stored)

    def test_view_derives_latest_state_and_counts(self):
        record = self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-001", 10)
        self.ext.record_curation_event(
            ADMIN, record["id"], "CEV-REF-001", "reported_added")
        self.ext.record_curation_event(
            ADMIN, record["id"], "CEV-REF-002", "reported_withdrawn")
        self.ext.record_corpus_license(
            ADMIN, record["id"], "LIC-REF-001", "LICENSOR-REF-001",
            "public domain")
        view = self.ext.corpus_content_view(ADMIN, record["id"])
        self.assertEqual(view["current_curation_state"],
                         "reported_withdrawn")
        self.assertIs(view["is_withdrawn"], True)
        self.assertEqual(view["curation_event_count"], 2)
        self.assertEqual(view["license_count"], 1)

    def test_view_without_events_is_recorded(self):
        record = self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-001", 10)
        view = self.ext.corpus_content_view(ADMIN, record["id"])
        self.assertEqual(view["current_curation_state"], "recorded")
        self.assertIs(view["is_withdrawn"], False)
        self.assertEqual(view["license_count"], 0)

    def test_event_and_license_shapes(self):
        record = self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-001", 10)
        event = self.ext.record_curation_event(
            ADMIN, record["id"], "CEV-REF-001", "reported_added")
        self.assertEqual(
            set(event),
            {"id", "content_id", "event_ref", "event_label",
             "curated_here", "created_by", "created_utc"})
        self.assertIs(event["curated_here"], False)
        license_record = self.ext.record_corpus_license(
            ADMIN, record["id"], "LIC-REF-001", "LICENSOR-REF-001",
            "public domain")
        self.assertEqual(
            set(license_record),
            {"id", "content_id", "license_ref", "licensor_ref",
             "license_label", "licensed_here", "created_by",
             "created_utc"})
        self.assertIs(license_record["licensed_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_curation_event(
                ADMIN, record["id"], "CEV-REF-002", "reported_deleted")

    def test_corpus_summary_counts(self):
        record = self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-001", 10)
        self.ext.record_curation_event(
            ADMIN, record["id"], "CEV-REF-001", "reported_added")
        self.ext.record_curation_event(
            ADMIN, record["id"], "CEV-REF-002", "reported_updated")
        self.ext.record_corpus_license(
            ADMIN, record["id"], "LIC-REF-001", "LICENSOR-REF-001",
            "public domain")
        summary = self.ext.corpus_summary(ADMIN)
        self.assertEqual(summary["library_source_count"], 1)
        self.assertEqual(summary["content_record_count"], 1)
        self.assertEqual(summary["sources_with_content"], 1)
        self.assertEqual(summary["curation_event_count"], 2)
        self.assertEqual(
            summary["curation_events_by_label"],
            {"reported_added": 1, "reported_updated": 1})
        self.assertEqual(summary["license_count"], 1)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertIs(summary["content_held_here"], False)


class MutantCurationExtensions(LegalPolSingletonExtensions):
    """The negative-control mutant: the curation seam reads the
    EARLIEST recorded event instead of the latest."""

    @staticmethod
    def _current_curation_label(events):
        if not events:
            return "recorded"
        return events[0]["event_label"]


class TestCurationDerivationNegativeControl(unittest.TestCase):
    """Fresh negative control: a corpus content record's current
    curation state is the LATEST recorded event label."""

    def _build(self, ext_class):
        store, audit, agency = make_store()
        ext = ext_class(store)
        source = make_source(store)
        record = ext.register_corpus_content(
            ADMIN, source["id"], "COR-REF-001", 10)
        ext.record_curation_event(
            ADMIN, record["id"], "CEV-REF-001", "reported_added")
        ext.record_curation_event(
            ADMIN, record["id"], "CEV-REF-002", "reported_withdrawn")
        return ext, record

    def test_current_state_is_latest_canonical(self):
        ext, record = self._build(LegalPolSingletonExtensions)
        view = ext.corpus_content_view(ADMIN, record["id"])
        self.assertEqual(view["current_curation_state"],
                         "reported_withdrawn")
        self.assertIs(view["is_withdrawn"], True)

    def test_mutant_reads_earliest(self):
        ext, record = self._build(MutantCurationExtensions)
        view = ext.corpus_content_view(ADMIN, record["id"])
        self.assertEqual(view["current_curation_state"], "reported_added")
        self.assertIs(view["is_withdrawn"], False)

    def test_canonical_expectation_rejects_mutant(self):
        canonical, record = self._build(LegalPolSingletonExtensions)
        mutant, mutant_record = self._build(MutantCurationExtensions)
        canonical_view = canonical.corpus_content_view(ADMIN, record["id"])
        mutant_view = mutant.corpus_content_view(ADMIN, mutant_record["id"])
        with self.assertRaises(AssertionError):
            self.assertEqual(canonical_view["current_curation_state"],
                             mutant_view["current_curation_state"])
        with self.assertRaises(AssertionError):
            self.assertEqual(canonical_view["is_withdrawn"],
                             mutant_view["is_withdrawn"])


class TestAgentRuntime(unittest.TestCase):
    """Idx 485 (reference): agent runs as request + reported
    outcome records; model bridges as definition records."""

    def setUp(self):
        self.ext, self.store, self.audit, self.agency, self.ws = \
            make_singleton()
        self.session = make_session(self.store, self.agency, self.ws)

    def test_run_record_is_labeled_reference(self):
        run = self.ext.record_agent_run(
            MEMBER, self.agency["id"], self.ws["id"], self.session["id"],
            "RUN-REF-001", task_label="summarize the docket")
        self.assertEqual(
            set(run),
            {"id", "agency_id", "workspace_id", "session_id", "run_ref",
             "task_label", "reference_stub", "state", "inference_here",
             "orchestrated_here", "retrieved_here", "created_by",
             "created_utc"})
        self.assertIs(run["reference_stub"], True)
        self.assertEqual(run["state"], "recorded_reference_only")
        self.assertIs(run["inference_here"], False)
        self.assertIs(run["orchestrated_here"], False)
        self.assertIs(run["retrieved_here"], False)

    def test_outcome_records_and_view(self):
        run = self.ext.record_agent_run(
            MEMBER, self.agency["id"], self.ws["id"], self.session["id"],
            "RUN-REF-001")
        outcome = self.ext.record_agent_run_outcome(
            MEMBER, self.agency["id"], run["id"], "ARO-REF-001",
            result_ref="RESULT-REF-001", reported_label="reported_completed")
        self.assertEqual(
            set(outcome),
            {"id", "agency_id", "run_id", "outcome_ref", "result_ref",
             "reported_label", "reference_stub", "inference_here",
             "created_by", "created_utc"})
        view = self.ext.agent_run_view(MEMBER, self.agency["id"], run["id"])
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_reported_label"],
                         "reported_completed")

    def test_session_must_be_in_workspace(self):
        other = make_workspace(
            self.store, self.agency, workspace_ref="WSP-REF-002")
        with self.assertRaises(NotFoundError):
            self.ext.record_agent_run(
                MEMBER, self.agency["id"], other["id"], self.session["id"],
                "RUN-REF-001")

    def test_model_bridge_definition(self):
        bridge = self.ext.define_model_bridge(
            MEMBER, self.agency["id"], "BRG-REF-001", "model transport")
        self.assertEqual(
            set(bridge),
            {"id", "agency_id", "bridge_ref", "endpoint_label",
             "reference_stub", "reference_transport", "state",
             "transported_here", "created_by", "created_utc"})
        self.assertIs(bridge["reference_transport"], True)
        self.assertIs(bridge["transported_here"], False)


class TestSearchEngines(unittest.TestCase):
    """Idx 487 (reference): engine definitions + reported run
    records bound to core saved searches; no query can exist."""

    def setUp(self):
        self.ext, self.store, self.audit, self.agency, self.ws = \
            make_singleton()

    def test_engine_definition_is_labeled_reference(self):
        engine = self.ext.define_search_engine(
            MEMBER, self.agency["id"], "ENG-REF-001", "semantic")
        self.assertEqual(
            set(engine),
            {"id", "agency_id", "engine_ref", "engine_kind",
             "reference_stub", "state", "indexed_here", "ranked_here",
             "searched_here", "created_by", "created_utc"})
        self.assertIs(engine["reference_stub"], True)
        self.assertIs(engine["indexed_here"], False)
        self.assertIs(engine["ranked_here"], False)
        self.assertIs(engine["searched_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.define_search_engine(
                MEMBER, self.agency["id"], "ENG-REF-002", "boolean")

    def test_run_record_bound_to_core_saved_search(self):
        engine = self.ext.define_search_engine(
            MEMBER, self.agency["id"], "ENG-REF-001", "full_text")
        saved = self.store.save_search(
            self.agency["id"], "SEA-REF-001", QUERY_SHA256, 7, MEMBER)
        run = self.ext.record_search_engine_run(
            MEMBER, self.agency["id"], engine["id"], "SRN-REF-001", 7,
            search_id=saved["id"])
        self.assertEqual(
            set(run),
            {"id", "agency_id", "engine_id", "search_id", "run_ref",
             "reported_result_count", "reference_stub", "searched_here",
             "ranked_here", "created_by", "created_utc"})
        self.assertEqual(run["search_id"], saved["id"])
        self.assertEqual(run["reported_result_count"], 7)
        with self.assertRaises(NotFoundError):
            self.ext.record_search_engine_run(
                MEMBER, self.agency["id"], engine["id"], "SRN-REF-002", 0,
                search_id="sea-999")


class TestSandboxRuntime(unittest.TestCase):
    """Idx 488 (built): provisioning requests + reported outcomes
    over core sandbox sessions; the runtime itself is not here."""

    def setUp(self):
        self.ext, self.store, self.audit, self.agency, self.ws = \
            make_singleton()
        self.sandbox = make_session(
            self.store, self.agency, self.ws, session_ref="SES-SBX-001",
            sandbox=True)
        self.plain = make_session(
            self.store, self.agency, self.ws, session_ref="SES-REF-002")

    def test_request_and_outcome_shapes(self):
        request = self.ext.request_sandbox_provisioning(
            MEMBER, self.agency["id"], self.sandbox["id"], "SBP-REF-001")
        self.assertEqual(
            set(request),
            {"id", "agency_id", "workspace_id", "session_id",
             "request_ref", "provisioned_here", "runtime_here",
             "created_by", "created_utc"})
        self.assertIs(request["provisioned_here"], False)
        self.assertIs(request["runtime_here"], False)
        outcome = self.ext.record_sandbox_outcome(
            MEMBER, self.agency["id"], request["id"],
            "reported_provisioned")
        self.assertEqual(
            set(outcome),
            {"id", "agency_id", "request_id", "outcome_label",
             "provisioned_here", "runtime_here", "created_by",
             "created_utc"})

    def test_non_sandbox_session_refused(self):
        with self.assertRaises(ValidationError):
            self.ext.request_sandbox_provisioning(
                MEMBER, self.agency["id"], self.plain["id"], "SBP-REF-001")

    def test_view_derives_outcome_and_core_consumption(self):
        request = self.ext.request_sandbox_provisioning(
            MEMBER, self.agency["id"], self.sandbox["id"], "SBP-REF-001")
        self.ext.record_sandbox_outcome(
            MEMBER, self.agency["id"], request["id"],
            "reported_provisioned")
        view = self.ext.sandbox_runtime_view(
            MEMBER, self.agency["id"], request["id"])
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome_label"],
                         "reported_provisioned")
        self.assertEqual(view["session_status"], "active")
        self.assertIs(view["sandbox_consumed"], False)
        self.store.record_execution(
            self.agency["id"], self.sandbox["id"], "EXE-REF-001", MEMBER)
        view = self.ext.sandbox_runtime_view(
            MEMBER, self.agency["id"], request["id"])
        self.assertIs(view["sandbox_consumed"], True)


class TestExecutionEngine(unittest.TestCase):
    """Idx 489 (built): jobs over core execution records +
    reported outcomes; nothing is executed here."""

    def setUp(self):
        self.ext, self.store, self.audit, self.agency, self.ws = \
            make_singleton()
        self.session = make_session(self.store, self.agency, self.ws)
        self.execution = self.store.record_execution(
            self.agency["id"], self.session["id"], "EXE-REF-001", MEMBER)

    def test_job_and_outcome_shapes_and_view(self):
        job = self.ext.record_execution_job(
            MEMBER, self.agency["id"], self.session["id"],
            self.execution["id"], "JOB-REF-001")
        self.assertEqual(
            set(job),
            {"id", "agency_id", "session_id", "execution_id",
             "execution_kind", "job_ref", "executed_here", "created_by",
             "created_utc"})
        self.assertIs(job["executed_here"], False)
        outcome = self.ext.record_execution_outcome(
            MEMBER, self.agency["id"], job["id"], "reported_completed",
            reported_exit_code=0)
        self.assertEqual(
            set(outcome),
            {"id", "agency_id", "job_id", "outcome_label",
             "reported_exit_code", "executed_here", "created_by",
             "created_utc"})
        view = self.ext.execution_job_view(
            MEMBER, self.agency["id"], job["id"])
        self.assertEqual(view["outcome_count"], 1)
        self.assertEqual(view["latest_outcome_label"],
                         "reported_completed")
        self.assertEqual(view["latest_reported_exit_code"], 0)

    def test_exit_code_discipline(self):
        job = self.ext.record_execution_job(
            MEMBER, self.agency["id"], self.session["id"],
            self.execution["id"], "JOB-REF-001")
        outcome = self.ext.record_execution_outcome(
            MEMBER, self.agency["id"], job["id"], "reported_failed",
            reported_exit_code=-1)
        self.assertEqual(outcome["reported_exit_code"], -1)
        with self.assertRaises(ValidationError):
            self.ext.record_execution_outcome(
                MEMBER, self.agency["id"], job["id"], "reported_failed",
                reported_exit_code=True)
        with self.assertRaises(ValidationError):
            self.ext.record_execution_outcome(
                MEMBER, self.agency["id"], job["id"], "reported_failed",
                reported_exit_code=1.5)

    def test_unknown_execution_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_execution_job(
                MEMBER, self.agency["id"], self.session["id"], "exe-999",
                "JOB-REF-001")


class TestDocumentGeneration(unittest.TestCase):
    """Idx 490 (reference): generation requests + reported outputs
    held as core document references; no generated text exists."""

    def setUp(self):
        self.ext, self.store, self.audit, self.agency, self.ws = \
            make_singleton()

    def test_request_is_labeled_reference(self):
        request = self.ext.record_generation_request(
            MEMBER, self.agency["id"], self.ws["id"], "GNR-REF-001",
            purpose_label="draft guidance")
        self.assertEqual(
            set(request),
            {"id", "agency_id", "workspace_id", "session_id",
             "request_ref", "purpose_label", "reference_stub", "state",
             "generated_here", "drafted_here", "created_by",
             "created_utc"})
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["generated_here"], False)
        self.assertIs(request["drafted_here"], False)

    def test_output_is_a_core_document_reference(self):
        request = self.ext.record_generation_request(
            MEMBER, self.agency["id"], self.ws["id"], "GNR-REF-001")
        document = make_document(self.store, self.agency, self.ws)
        output = self.ext.record_generation_output(
            MEMBER, self.agency["id"], request["id"], document["id"])
        self.assertEqual(
            set(output),
            {"id", "agency_id", "request_id", "document_id",
             "reference_stub", "generated_here", "created_by",
             "created_utc"})
        view = self.ext.generation_request_view(
            MEMBER, self.agency["id"], request["id"])
        self.assertEqual(view["output_count"], 1)
        self.assertEqual(view["output_document_ids"], [document["id"]])
        with self.assertRaises(ValidationError):
            self.ext.record_generation_output(
                MEMBER, self.agency["id"], request["id"], document["id"])

    def test_output_document_must_be_in_request_workspace(self):
        request = self.ext.record_generation_request(
            MEMBER, self.agency["id"], self.ws["id"], "GNR-REF-001")
        other = make_workspace(
            self.store, self.agency, workspace_ref="WSP-REF-002")
        foreign = make_document(
            self.store, self.agency, other, doc_ref="DOC-REF-002")
        with self.assertRaises(NotFoundError):
            self.ext.record_generation_output(
                MEMBER, self.agency["id"], request["id"], foreign["id"])


class TestSecurityMonitoring(unittest.TestCase):
    """Idx 492 (reference): feed definitions + reported
    observations; nothing is monitored or scanned here."""

    def setUp(self):
        self.ext, self.store, self.audit, self.agency, self.ws = \
            make_singleton()

    def test_feed_is_labeled_reference_transport(self):
        feed = self.ext.define_monitoring_feed(
            MEMBER, self.agency["id"], "FED-REF-001", "platform scanner")
        self.assertEqual(
            set(feed),
            {"id", "agency_id", "feed_ref", "source_label",
             "reference_stub", "reference_transport", "state",
             "monitored_here", "scanned_here", "created_by",
             "created_utc"})
        self.assertIs(feed["reference_transport"], True)
        self.assertIs(feed["monitored_here"], False)
        self.assertIs(feed["scanned_here"], False)

    def test_observations_and_derived_counts(self):
        feed = self.ext.define_monitoring_feed(
            MEMBER, self.agency["id"], "FED-REF-001", "platform scanner")
        observation = self.ext.record_monitoring_observation(
            MEMBER, self.agency["id"], feed["id"], "OBS-REF-001",
            "reported vulnerability", "high")
        self.assertEqual(
            set(observation),
            {"id", "agency_id", "feed_id", "observation_ref",
             "observation_label", "severity_label", "reference_stub",
             "monitored_here", "created_by", "created_utc"})
        self.ext.record_monitoring_observation(
            MEMBER, self.agency["id"], feed["id"], "OBS-REF-002",
            "reported configuration drift", "low")
        view = self.ext.monitoring_feed_view(
            MEMBER, self.agency["id"], feed["id"])
        self.assertEqual(view["observation_count"], 2)
        self.assertEqual(view["observations_by_severity"],
                         {"high": 1, "low": 1})


class TestCrossCuttingGuards(unittest.TestCase):
    """The founding discipline across the whole new surface: RBAC
    and the membership boundary, TypeError on content-shaped
    kwargs, the recursive forbidden-key scan, and audit."""

    def setUp(self):
        self.ext, self.store, self.audit, self.agency, self.ws = \
            make_singleton()
        self.source = make_source(self.store)
        self.session = make_session(self.store, self.agency, self.ws)

    def test_viewer_writes_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_corpus_content(
                VIEWER, self.source["id"], "COR-REF-001", 10)
        with self.assertRaises(PermissionDenied):
            self.ext.record_agent_run(
                VIEWER, self.agency["id"], self.ws["id"],
                self.session["id"], "RUN-REF-001")
        denied = [e["action"] for e in self.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertIn("ext_corpus_content:denied", denied)
        self.assertIn("ext_agent_run:denied", denied)

    def test_outsider_denied_at_membership_boundary(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_agent_run(
                OUTSIDER, self.agency["id"], self.ws["id"],
                self.session["id"], "RUN-REF-001")

    def test_content_shaped_kwargs_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.record_agent_run(
                MEMBER, self.agency["id"], self.ws["id"],
                self.session["id"], "RUN-REF-001", prompt="write a memo")
        with self.assertRaises(TypeError):
            self.ext.register_corpus_content(
                ADMIN, self.source["id"], "COR-REF-001", 10,
                content="the statutes themselves")
        engine = self.ext.define_search_engine(
            MEMBER, self.agency["id"], "ENG-REF-001", "semantic")
        with self.assertRaises(TypeError):
            self.ext.record_search_engine_run(
                MEMBER, self.agency["id"], engine["id"], "SRN-REF-001",
                3, query_text="administrative procedure")
        with self.assertRaises(TypeError):
            self.ext.record_generation_request(
                MEMBER, self.agency["id"], self.ws["id"], "GNR-REF-001",
                document_text="draft text")

    def test_extension_writes_are_audited(self):
        self.ext.register_corpus_content(
            ADMIN, self.source["id"], "COR-REF-001", 10)
        self.ext.define_monitoring_feed(
            MEMBER, self.agency["id"], "FED-REF-001", "platform scanner")
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_corpus_content", actions)
        self.assertIn("ext_monitoring_feed", actions)

    def test_no_forbidden_key_anywhere_on_the_surface(self):
        ext, store, audit, agency, ws = make_singleton()
        source = make_source(store)
        session = make_session(store, agency, ws)
        sandbox = make_session(
            store, agency, ws, session_ref="SES-SBX-001", sandbox=True)
        execution = store.record_execution(
            agency["id"], session["id"], "EXE-REF-001", MEMBER)
        saved = store.save_search(
            agency["id"], "SEA-REF-001", QUERY_SHA256, 7, MEMBER)
        document = make_document(store, agency, ws)
        records = []
        content = ext.register_corpus_content(
            ADMIN, source["id"], "COR-REF-001", 10,
            content_sha256=SHA256_A)
        records.append(content)
        records.append(ext.record_curation_event(
            ADMIN, content["id"], "CEV-REF-001", "reported_added"))
        records.append(ext.record_corpus_license(
            ADMIN, content["id"], "LIC-REF-001", "LICENSOR-REF-001",
            "public domain"))
        records.append(ext.corpus_content_view(ADMIN, content["id"]))
        records.append(ext.corpus_summary(ADMIN))
        run = ext.record_agent_run(
            MEMBER, agency["id"], ws["id"], session["id"], "RUN-REF-001")
        records.append(run)
        records.append(ext.record_agent_run_outcome(
            MEMBER, agency["id"], run["id"], "ARO-REF-001",
            result_ref="RESULT-REF-001"))
        records.append(ext.agent_run_view(MEMBER, agency["id"], run["id"]))
        records.append(ext.define_model_bridge(
            MEMBER, agency["id"], "BRG-REF-001", "model transport"))
        engine = ext.define_search_engine(
            MEMBER, agency["id"], "ENG-REF-001", "hybrid")
        records.append(engine)
        records.append(ext.record_search_engine_run(
            MEMBER, agency["id"], engine["id"], "SRN-REF-001", 7,
            search_id=saved["id"]))
        request = ext.request_sandbox_provisioning(
            MEMBER, agency["id"], sandbox["id"], "SBP-REF-001")
        records.append(request)
        records.append(ext.record_sandbox_outcome(
            MEMBER, agency["id"], request["id"], "reported_provisioned"))
        records.append(ext.sandbox_runtime_view(
            MEMBER, agency["id"], request["id"]))
        job = ext.record_execution_job(
            MEMBER, agency["id"], session["id"], execution["id"],
            "JOB-REF-001")
        records.append(job)
        records.append(ext.record_execution_outcome(
            MEMBER, agency["id"], job["id"], "reported_completed",
            reported_exit_code=0))
        records.append(ext.execution_job_view(
            MEMBER, agency["id"], job["id"]))
        generation = ext.record_generation_request(
            MEMBER, agency["id"], ws["id"], "GNR-REF-001")
        records.append(generation)
        records.append(ext.record_generation_output(
            MEMBER, agency["id"], generation["id"], document["id"]))
        records.append(ext.generation_request_view(
            MEMBER, agency["id"], generation["id"]))
        feed = ext.define_monitoring_feed(
            MEMBER, agency["id"], "FED-REF-001", "platform scanner")
        records.append(feed)
        records.append(ext.record_monitoring_observation(
            MEMBER, agency["id"], feed["id"], "OBS-REF-001",
            "reported vulnerability", "high"))
        records.append(ext.monitoring_feed_view(
            MEMBER, agency["id"], feed["id"]))
        self.assertEqual(len(records), 23)
        for record in records:
            for path, key in _scan_keys(record):
                for fragment in FORBIDDEN_KEY_FRAGMENTS:
                    self.assertNotIn(
                        fragment, key,
                        "forbidden key fragment %r at %s: %r"
                        % (fragment, path, key))


if __name__ == "__main__":
    unittest.main()
