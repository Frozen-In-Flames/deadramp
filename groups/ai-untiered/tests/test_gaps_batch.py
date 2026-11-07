"""Tests for the Final GAPS batch extension module.

Covers ``aigateway.extensions.AIGatewayExtensions``: the 8 open
Extended entries of the Artificial Intelligence (AI) untiered set
-- 2 built (serving configuration records over the core model
registry; benchmark records over the core evaluation harness)
and 6 shipped as labeled reference implementations, two of them
re-judged (document understanding; knowledge-base / retrieval).

The module's honesty pins are the point of this suite: exact
record key sets, the reference_stub label on every reference
record, TypeError on every content-shaped argument, the registry
never executing (core request/session state unchanged), the
benchmark surface scoring nothing of its own, tier-null
recursion over every extension record and view, and the fresh
serving-gate negative control (three legs, in-suite; the live
mutation drill is recorded in tests/README.md).
"""

import unittest

from aigateway.errors import NotFoundError, PermissionDenied, ValidationError
from aigateway.extensions import AIGatewayExtensions
from aigateway_helpers import ADMIN, MEMBER, OTHER_MEMBER, VIEWER, make_store

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64

# The exact case set every benchmark test runs against the core's
# echo responder: pass, fail, pass under the core's own scoring.
CASES = [
    {"prompt": "alpha", "match": "exact", "expected": "alpha"},
    {"prompt": "beta", "match": "exact", "expected": "gamma"},
    {"prompt": "Key Word", "match": "contains", "expected": "word"},
]


def make_extensions():
    store, audit, model = make_store()
    return AIGatewayExtensions(store), store, audit, model


def make_dataset(store, name="refset"):
    return store.create_eval_dataset(name, CASES, ADMIN)


def deprecated_model(store, name="oldmodel"):
    model = store.register_model(name, "echo", ADMIN, version=1)
    store.set_model_status(name, 1, "deprecated", ADMIN)
    return model


class TestServingEndpoints(unittest.TestCase):
    def test_endpoint_record_shape(self):
        ext, _store, _audit, _model = make_extensions()
        endpoint = ext.register_serving_endpoint(
            "echoer", MEMBER, replicas_reported=2, region_label="ref-region")
        self.assertEqual(endpoint["id"], "sep-1")
        self.assertEqual(
            set(endpoint.keys()),
            {"id", "model", "model_version", "replicas_reported",
             "region_label", "provisioned_here", "autoscaled_here", "state",
             "created_by", "created_utc"})
        self.assertEqual(endpoint["model"], "echoer")
        self.assertEqual(endpoint["model_version"], 1)
        self.assertEqual(endpoint["replicas_reported"], 2)
        self.assertEqual(endpoint["region_label"], "ref-region")
        self.assertFalse(endpoint["provisioned_here"])
        self.assertFalse(endpoint["autoscaled_here"])
        self.assertEqual(endpoint["state"], "recorded_configuration")
        # A built configuration record is not a stub: no label.
        self.assertNotIn("reference_stub", endpoint)

    def test_endpoint_resolves_highest_version(self):
        ext, store, _audit, _model = make_extensions()
        store.register_model("echoer", "echo", ADMIN, version=2)
        endpoint = ext.register_serving_endpoint("echoer", MEMBER)
        self.assertEqual(endpoint["model_version"], 2)

    def test_endpoint_for_unknown_model_refused(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(NotFoundError):
            ext.register_serving_endpoint("ghost", MEMBER)
        self.assertEqual(ext.list_serving_endpoints(), [])

    def test_endpoint_for_deprecated_model_refused_and_no_id_consumed(self):
        ext, store, _audit, _model = make_extensions()
        deprecated_model(store)
        with self.assertRaises(ValidationError):
            ext.register_serving_endpoint("oldmodel", MEMBER)
        endpoint = ext.register_serving_endpoint("echoer", MEMBER)
        self.assertEqual(endpoint["id"], "sep-1")

    def test_endpoint_validation(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(ValidationError):
            ext.register_serving_endpoint("  ", MEMBER)
        with self.assertRaises(ValidationError):
            ext.register_serving_endpoint("echoer", MEMBER,
                                          replicas_reported=-1)
        with self.assertRaises(ValidationError):
            ext.register_serving_endpoint("echoer", MEMBER,
                                          replicas_reported=True)
        with self.assertRaises(ValidationError):
            ext.register_serving_endpoint("echoer", MEMBER, region_label=7)

    def test_serving_events_and_summary_derived(self):
        ext, _store, _audit, _model = make_extensions()
        first = ext.register_serving_endpoint(
            "echoer", MEMBER, replicas_reported=2)
        second = ext.register_serving_endpoint(
            "echoer", MEMBER, version=1, replicas_reported=3)
        event = ext.record_serving_event(first["id"], "deployment_reported",
                                         MEMBER)
        self.assertEqual(
            set(event.keys()),
            {"id", "endpoint_id", "event_label", "reported", "enacted_here",
             "created_by", "created_utc"})
        self.assertTrue(event["reported"])
        self.assertFalse(event["enacted_here"])
        summary = ext.serving_summary(MEMBER)
        self.assertEqual(
            summary,
            {"endpoints": 2, "events": 1, "replicas_reported_total": 5,
             "models": ["echoer"], "derived": True})
        # The stored endpoint records carry no derived key.
        for record in ext.list_serving_endpoints():
            self.assertNotIn("replicas_reported_total", record)
            self.assertNotIn("derived", record)
        with self.assertRaises(NotFoundError):
            ext.record_serving_event("sep-99", "x", MEMBER)

    def test_serving_denied_for_viewer_and_audited(self):
        ext, _store, audit, _model = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.register_serving_endpoint("echoer", VIEWER)
        denied = [e for e in audit.entries()
                  if e["action"] == "ext_serving_endpoint_register:denied"]
        self.assertEqual(len(denied), 1)


class TestBenchmarks(unittest.TestCase):
    def _benchmark(self, ext, store, name="bench-1"):
        dataset = make_dataset(store)
        return ext.define_benchmark(name, dataset["id"], "echoer", MEMBER)

    def test_benchmark_record_shape(self):
        ext, store, _audit, _model = make_extensions()
        benchmark = self._benchmark(ext, store)
        self.assertEqual(benchmark["id"], "bmk-1")
        self.assertEqual(
            set(benchmark.keys()),
            {"id", "name", "dataset_id", "model", "model_version", "scoring",
             "external_models_evaluated", "created_by", "created_utc"})
        self.assertEqual(benchmark["scoring"], "core_eval_harness")
        self.assertFalse(benchmark["external_models_evaluated"])

    def test_benchmark_requires_existing_dataset_and_model(self):
        ext, store, _audit, _model = make_extensions()
        with self.assertRaises(NotFoundError):
            ext.define_benchmark("b", "evd-99", "echoer", MEMBER)
        dataset = make_dataset(store)
        with self.assertRaises(NotFoundError):
            ext.define_benchmark("b", dataset["id"], "ghost", MEMBER)
        self.assertEqual(ext.list_benchmarks(), [])

    def test_run_benchmark_uses_core_harness_and_links(self):
        ext, store, _audit, _model = make_extensions()
        benchmark = self._benchmark(ext, store)
        run = ext.run_benchmark(benchmark["id"], MEMBER)
        # The run is the core's own run record, scored by the core.
        self.assertTrue(run["id"].startswith("evr-"))
        self.assertEqual(run["total"], 3)
        self.assertEqual(run["passed"], 2)
        links = ext.list_benchmark_runs(benchmark["id"])
        self.assertEqual(len(links), 1)
        link = links[0]
        self.assertEqual(
            set(link.keys()),
            {"id", "benchmark_id", "eval_run_id", "dataset_id", "model",
             "model_version", "created_by", "created_utc"})
        self.assertEqual(link["eval_run_id"], run["id"])
        # The link stores no score: scoring lives in the core run.
        self.assertNotIn("score", link)
        self.assertNotIn("passed", link)

    def test_benchmark_view_derives_totals_from_core_runs(self):
        ext, store, _audit, _model = make_extensions()
        benchmark = self._benchmark(ext, store)
        ext.run_benchmark(benchmark["id"], MEMBER)
        ext.run_benchmark(benchmark["id"], MEMBER)
        view = ext.benchmark_view(benchmark["id"], MEMBER)
        self.assertTrue(view["derived"])
        self.assertEqual(view["run_count"], 2)
        self.assertEqual(view["total_cases"], 6)
        self.assertEqual(view["total_passed"], 4)
        self.assertEqual(len(view["runs"]), 2)
        # The stored definition record carries no derived totals.
        stored = ext.get_benchmark(benchmark["id"])
        self.assertNotIn("total_cases", stored)
        self.assertNotIn("run_count", stored)

    def test_benchmark_view_inherits_core_run_ownership(self):
        ext, store, _audit, _model = make_extensions()
        benchmark = self._benchmark(ext, store)
        ext.run_benchmark(benchmark["id"], MEMBER)
        # The core refuses another member's run; the view inherits it.
        with self.assertRaises(PermissionDenied):
            ext.benchmark_view(benchmark["id"], OTHER_MEMBER)
        # The platform admin can read any run through the view.
        view = ext.benchmark_view(benchmark["id"], ADMIN)
        self.assertEqual(view["run_count"], 1)

    def test_deprecated_model_run_refused_and_no_link_consumed(self):
        ext, store, _audit, _model = make_extensions()
        deprecated_model(store)
        dataset = make_dataset(store)
        benchmark = ext.define_benchmark(
            "old-bench", dataset["id"], "oldmodel", MEMBER)
        with self.assertRaises(ValidationError):
            ext.run_benchmark(benchmark["id"], MEMBER)
        good = self._benchmark(ext, store, name="good-bench")
        ext.run_benchmark(good["id"], MEMBER)
        links = ext.list_benchmark_runs(good["id"])
        self.assertEqual(links[0]["id"], "bmr-1")
        self.assertEqual(ext.benchmark_view(benchmark["id"], MEMBER)
                         ["run_count"], 0)

    def test_benchmark_denied_for_viewer_and_audited(self):
        ext, store, audit, _model = make_extensions()
        dataset = make_dataset(store)
        with self.assertRaises(PermissionDenied):
            ext.define_benchmark("b", dataset["id"], "echoer", VIEWER)
        denied = [e for e in audit.entries()
                  if e["action"] == "ext_benchmark_define:denied"]
        self.assertEqual(len(denied), 1)


class TestInferenceReference(unittest.TestCase):
    def test_request_and_outcome_shapes_and_labels(self):
        ext, _store, _audit, _model = make_extensions()
        request = ext.register_inference_request(
            "echoer", MEMBER, prompt_digest=DIGEST_A)
        self.assertEqual(
            set(request.keys()),
            {"id", "model", "model_version", "prompt_digest",
             "reference_stub", "inference_here", "executed_here", "state",
             "created_by", "created_utc"})
        self.assertTrue(request["reference_stub"])
        self.assertFalse(request["inference_here"])
        self.assertFalse(request["executed_here"])
        outcome = ext.record_inference_outcome(
            request["id"], "reported_complete", MEMBER, output_ref="out-1")
        self.assertEqual(
            set(outcome.keys()),
            {"id", "request_id", "outcome_label", "output_ref",
             "reference_stub", "result_held_here", "created_by",
             "created_utc"})
        self.assertTrue(outcome["reference_stub"])
        self.assertFalse(outcome["result_held_here"])

    def test_request_requires_registered_model(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(NotFoundError):
            ext.register_inference_request("ghost", MEMBER)

    def test_bad_digest_refused(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(ValidationError):
            ext.register_inference_request("echoer", MEMBER,
                                           prompt_digest="not-a-digest")
        with self.assertRaises(ValidationError):
            ext.register_inference_request("echoer", MEMBER,
                                           prompt_digest="A" * 64)

    def test_content_arguments_raise_typeerror(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(TypeError):
            ext.register_inference_request(
                "echoer", MEMBER, **{"prompt": "hello"})
        request = ext.register_inference_request("echoer", MEMBER)
        with self.assertRaises(TypeError):
            ext.record_inference_outcome(
                request["id"], "x", MEMBER, **{"output": "text"})

    def test_inference_request_invokes_nothing(self):
        ext, store, _audit, _model = make_extensions()
        ext.register_inference_request("echoer", MEMBER)
        self.assertEqual(store.list_requests(MEMBER), [])


class TestAgentWorkflows(unittest.TestCase):
    def test_definition_run_outcome_shapes(self):
        ext, _store, _audit, _model = make_extensions()
        workflow = ext.define_agent_workflow(
            "triage-flow", MEMBER, steps=["intake", "route"],
            model_name="echoer")
        self.assertEqual(
            set(workflow.keys()),
            {"id", "name", "steps", "model", "definition_only",
             "reference_stub", "executed_here", "created_by", "created_utc"})
        self.assertTrue(workflow["definition_only"])
        self.assertTrue(workflow["reference_stub"])
        self.assertFalse(workflow["executed_here"])
        run = ext.request_agent_run(workflow["id"], MEMBER,
                                    input_ref="in-ref-1")
        self.assertEqual(
            set(run.keys()),
            {"id", "workflow_id", "input_ref", "reference_stub",
             "executed_here", "state", "created_by", "created_utc"})
        self.assertEqual(run["state"], "recorded_request_only")
        outcome = ext.record_agent_run_outcome(
            run["id"], "reported_complete", MEMBER, output_ref="out-9")
        self.assertEqual(
            set(outcome.keys()),
            {"id", "run_id", "outcome_label", "output_ref",
             "reference_stub", "executed_here", "result_held_here",
             "created_by", "created_utc"})
        self.assertFalse(outcome["executed_here"])

    def test_registry_never_executes(self):
        ext, store, _audit, _model = make_extensions()
        workflow = ext.define_agent_workflow("flow", MEMBER, steps=["a"])
        ext.request_agent_run(workflow["id"], MEMBER)
        # No core request and no core session was created.
        self.assertEqual(store.list_requests(MEMBER), [])
        self.assertEqual(store.list_sessions(MEMBER), [])
        # And the core gateway still serves its own reference stub.
        response = store.invoke("echoer", "hello", MEMBER)
        self.assertTrue(response["reference_stub"])
        self.assertEqual(response["output"], "hello")

    def test_workflow_requires_registered_model(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(NotFoundError):
            ext.define_agent_workflow("flow", MEMBER, model_name="ghost")

    def test_steps_must_be_label_strings(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(ValidationError):
            ext.define_agent_workflow("flow", MEMBER, steps=["ok", 3])
        with self.assertRaises(ValidationError):
            ext.define_agent_workflow("flow", MEMBER, steps="not-a-list")


class TestVoiceReference(unittest.TestCase):
    def test_job_and_outcome_shapes(self):
        ext, _store, _audit, _model = make_extensions()
        job = ext.register_voice_job(
            "speech_to_text", MEMBER, model_name="echoer",
            input_ref="media-ref-1")
        self.assertEqual(
            set(job.keys()),
            {"id", "kind", "model", "input_ref", "reference_stub",
             "processed_here", "media_held", "state", "created_by",
             "created_utc"})
        self.assertTrue(job["reference_stub"])
        self.assertFalse(job["processed_here"])
        self.assertFalse(job["media_held"])
        outcome = ext.record_voice_outcome(
            job["id"], "reported_complete", MEMBER, result_ref="tr-1")
        self.assertEqual(
            set(outcome.keys()),
            {"id", "job_id", "outcome_label", "result_ref",
             "reference_stub", "result_held_here", "created_by",
             "created_utc"})

    def test_kind_must_be_a_recorded_voice_kind(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(ValidationError):
            ext.register_voice_job("singing", MEMBER)

    def test_content_arguments_raise_typeerror(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(TypeError):
            ext.register_voice_job(
                "speech_to_text", MEMBER, **{"audio": b"..."})
        job = ext.register_voice_job("text_to_speech", MEMBER)
        with self.assertRaises(TypeError):
            ext.record_voice_outcome(
                job["id"], "x", MEMBER, **{"transcript_text": "hi"})


class TestDocumentReference(unittest.TestCase):
    def test_job_and_result_shapes(self):
        ext, _store, _audit, _model = make_extensions()
        job = ext.register_document_job(
            "summarization", "doc-ref-1", MEMBER, model_name="echoer",
            document_digest=DIGEST_B)
        self.assertEqual(
            set(job.keys()),
            {"id", "kind", "document_ref", "document_digest", "model",
             "reference_stub", "processed_here", "generated_here",
             "content_held", "state", "created_by", "created_utc"})
        self.assertTrue(job["reference_stub"])
        self.assertFalse(job["processed_here"])
        self.assertFalse(job["generated_here"])
        self.assertFalse(job["content_held"])
        result = ext.record_document_result(
            job["id"], "reported_complete", MEMBER, result_ref="sum-1")
        self.assertEqual(
            set(result.keys()),
            {"id", "job_id", "outcome_label", "result_ref",
             "reference_stub", "result_held_here", "created_by",
             "created_utc"})

    def test_kind_must_be_a_recorded_document_kind(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(ValidationError):
            ext.register_document_job("translation", "doc-ref-1", MEMBER)

    def test_content_arguments_raise_typeerror(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(TypeError):
            ext.register_document_job(
                "understanding", "doc-ref-1", MEMBER,
                **{"document_text": "the document"})
        with self.assertRaises(TypeError):
            ext.register_document_job(
                "understanding", "doc-ref-1", MEMBER, **{"content": "x"})
        job = ext.register_document_job("report_generation", "doc-ref-2",
                                        MEMBER)
        with self.assertRaises(TypeError):
            ext.record_document_result(
                job["id"], "x", MEMBER, **{"summary_text": "a summary"})


class TestKnowledgeBaseReference(unittest.TestCase):
    def test_definition_ingestion_query_result_shapes(self):
        ext, _store, _audit, _model = make_extensions()
        kb = ext.define_knowledge_base(
            "policy-kb", MEMBER, source_refs=["src-1", "src-2"])
        self.assertEqual(
            set(kb.keys()),
            {"id", "name", "source_refs", "definition_only",
             "reference_stub", "embeddings_computed_here", "index_built_here",
             "created_by", "created_utc"})
        self.assertTrue(kb["definition_only"])
        self.assertFalse(kb["embeddings_computed_here"])
        self.assertFalse(kb["index_built_here"])
        ingestion = ext.record_kb_ingestion(
            kb["id"], MEMBER, documents_reported=3, chunks_reported=9)
        self.assertEqual(
            set(ingestion.keys()),
            {"id", "kb_id", "documents_reported", "chunks_reported",
             "reference_stub", "indexed_here", "created_by", "created_utc"})
        self.assertEqual(ingestion["documents_reported"], 3)
        self.assertFalse(ingestion["indexed_here"])
        query = ext.register_retrieval_query(kb["id"], MEMBER,
                                             query_digest=DIGEST_C)
        self.assertEqual(
            set(query.keys()),
            {"id", "kb_id", "query_digest", "reference_stub",
             "retrieved_here", "state", "created_by", "created_utc"})
        self.assertFalse(query["retrieved_here"])
        result = ext.record_retrieval_result(
            query["id"], "reported_answered", MEMBER, answer_ref="ans-1",
            citation_refs=["cit-1"])
        self.assertEqual(
            set(result.keys()),
            {"id", "query_id", "outcome_label", "answer_ref",
             "citation_refs", "reference_stub", "answer_held",
             "grounded_here", "created_by", "created_utc"})
        self.assertFalse(result["answer_held"])
        self.assertFalse(result["grounded_here"])

    def test_vector_and_text_arguments_raise_typeerror(self):
        ext, _store, _audit, _model = make_extensions()
        kb = ext.define_knowledge_base("kb", MEMBER)
        with self.assertRaises(TypeError):
            ext.define_knowledge_base(
                "kb2", MEMBER, **{"embeddings": [0.1, 0.2]})
        with self.assertRaises(TypeError):
            ext.register_retrieval_query(kb["id"], MEMBER,
                                         **{"query_text": "what is..."})
        query = ext.register_retrieval_query(kb["id"], MEMBER)
        with self.assertRaises(TypeError):
            ext.record_retrieval_result(
                query["id"], "x", MEMBER, **{"answer_text": "the answer"})
        with self.assertRaises(TypeError):
            ext.record_retrieval_result(
                query["id"], "x", MEMBER, **{"vector": [1, 2, 3]})

    def test_ingestion_counts_must_be_integers(self):
        ext, _store, _audit, _model = make_extensions()
        kb = ext.define_knowledge_base("kb", MEMBER)
        with self.assertRaises(ValidationError):
            ext.record_kb_ingestion(kb["id"], MEMBER, documents_reported=-1)
        with self.assertRaises(ValidationError):
            ext.record_kb_ingestion(kb["id"], MEMBER, chunks_reported=1.5)


class TestVerticalReference(unittest.TestCase):
    def test_case_step_outcome_shapes(self):
        ext, _store, _audit, _model = make_extensions()
        case = ext.register_vertical_case(
            "public_records", "case-ref-1", MEMBER, model_name="echoer")
        self.assertEqual(
            set(case.keys()),
            {"id", "vertical", "case_ref", "model", "reference_stub",
             "casework_performed_here", "records_generated_here", "state",
             "created_by", "created_utc"})
        self.assertFalse(case["casework_performed_here"])
        self.assertFalse(case["records_generated_here"])
        step = ext.record_vertical_step(case["id"], "intake_reported",
                                        MEMBER)
        self.assertEqual(
            set(step.keys()),
            {"id", "case_id", "step_label", "reference_stub",
             "executed_here", "created_by", "created_utc"})
        outcome = ext.record_vertical_outcome(
            case["id"], "reported_fulfilled", MEMBER, output_ref="rec-1")
        self.assertEqual(
            set(outcome.keys()),
            {"id", "case_id", "outcome_label", "output_ref",
             "reference_stub", "result_held_here", "created_by",
             "created_utc"})

    def test_vertical_must_be_a_recorded_vertical(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(ValidationError):
            ext.register_vertical_case("defense", "case-ref-1", MEMBER)

    def test_content_arguments_raise_typeerror(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(TypeError):
            ext.register_vertical_case(
                "human_services", "case-ref-1", MEMBER,
                **{"subject_name": "a person"})
        case = ext.register_vertical_case("contact_center", "case-ref-2",
                                          MEMBER)
        with self.assertRaises(TypeError):
            ext.record_vertical_outcome(
                case["id"], "x", MEMBER, **{"record_text": "generated"})


class TestExtensionSummaryAndGuards(unittest.TestCase):
    def test_summary_counts_every_kind_derived(self):
        ext, store, _audit, _model = make_extensions()
        ext.register_serving_endpoint("echoer", MEMBER)
        dataset = make_dataset(store)
        benchmark = ext.define_benchmark("b", dataset["id"], "echoer",
                                         MEMBER)
        ext.run_benchmark(benchmark["id"], MEMBER)
        request = ext.register_inference_request("echoer", MEMBER)
        ext.record_inference_outcome(request["id"], "reported", MEMBER)
        summary = ext.extension_summary(MEMBER)
        self.assertTrue(summary["derived"])
        self.assertEqual(summary["records_total"], 5)
        self.assertEqual(
            summary["by_kind"],
            {"serving_endpoint": 1, "benchmark": 1, "benchmark_run": 1,
             "inference_request": 1, "inference_outcome": 1})

    def test_actorless_write_denied(self):
        ext, _store, _audit, _model = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.register_serving_endpoint("echoer", None)
        with self.assertRaises(PermissionDenied):
            ext.register_inference_request("echoer", None)

    def test_invoke_denied_for_viewer_and_audited(self):
        ext, _store, audit, _model = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.register_inference_request("echoer", VIEWER)
        denied = [e for e in audit.entries()
                  if e["action"] == "ext_inference_request_register:denied"]
        self.assertEqual(len(denied), 1)


class TestTierNullScan(unittest.TestCase):
    FORBIDDEN_KEY_PARTS = ("tier", "cmmc", "baseline", "equivalence",
                           "impact_level")

    def _everything(self):
        ext, store, _audit, _model = make_extensions()
        endpoint = ext.register_serving_endpoint(
            "echoer", ADMIN, replicas_reported=2, region_label="ref-region")
        ext.record_serving_event(endpoint["id"], "deployment_reported",
                                 ADMIN)
        dataset = make_dataset(store)
        benchmark = ext.define_benchmark("bench", dataset["id"], "echoer",
                                         ADMIN)
        ext.run_benchmark(benchmark["id"], ADMIN)
        request = ext.register_inference_request(
            "echoer", ADMIN, prompt_digest=DIGEST_A)
        ext.record_inference_outcome(request["id"], "reported_complete",
                                     ADMIN, output_ref="out-1")
        workflow = ext.define_agent_workflow(
            "flow", ADMIN, steps=["intake"], model_name="echoer")
        run = ext.request_agent_run(workflow["id"], ADMIN,
                                    input_ref="in-1")
        ext.record_agent_run_outcome(run["id"], "reported_complete", ADMIN,
                                     output_ref="out-2")
        job = ext.register_voice_job(
            "speech_to_text", ADMIN, model_name="echoer",
            input_ref="media-1")
        ext.record_voice_outcome(job["id"], "reported_complete", ADMIN,
                                 result_ref="tr-1")
        doc_job = ext.register_document_job(
            "summarization", "doc-1", ADMIN, model_name="echoer",
            document_digest=DIGEST_B)
        ext.record_document_result(doc_job["id"], "reported_complete",
                                   ADMIN, result_ref="sum-1")
        kb = ext.define_knowledge_base("kb", ADMIN, source_refs=["src-1"])
        ext.record_kb_ingestion(kb["id"], ADMIN, documents_reported=3,
                                chunks_reported=9)
        query = ext.register_retrieval_query(kb["id"], ADMIN,
                                             query_digest=DIGEST_C)
        ext.record_retrieval_result(query["id"], "reported_answered", ADMIN,
                                    answer_ref="ans-1",
                                    citation_refs=["cit-1"])
        case = ext.register_vertical_case(
            "public_records", "case-1", ADMIN, model_name="echoer")
        ext.record_vertical_step(case["id"], "intake_reported", ADMIN)
        ext.record_vertical_outcome(case["id"], "reported_fulfilled",
                                    ADMIN, output_ref="rec-1")
        collected = []
        collected += ext.list_serving_endpoints()
        collected += ext.list_serving_events()
        collected += ext.list_benchmarks()
        collected += ext.list_benchmark_runs()
        collected += ext.list_inference_requests()
        collected += ext.list_inference_outcomes()
        collected += ext.list_agent_workflows()
        collected += ext.list_agent_runs()
        collected += ext.list_agent_outcomes()
        collected += ext.list_voice_jobs()
        collected += ext.list_voice_outcomes()
        collected += ext.list_document_jobs()
        collected += ext.list_document_results()
        collected += ext.list_knowledge_bases()
        collected += ext.list_kb_ingestions()
        collected += ext.list_retrieval_queries()
        collected += ext.list_retrieval_results()
        collected += ext.list_vertical_cases()
        collected += ext.list_vertical_steps()
        collected += ext.list_vertical_outcomes()
        collected.append(ext.serving_summary(ADMIN))
        collected.append(ext.benchmark_view(benchmark["id"], ADMIN))
        collected.append(ext.extension_summary(ADMIN))
        return collected

    def _walk(self, node, path="root"):
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = str(key).lower()
                for part in self.FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(
                        part, lowered,
                        "tier-shaped key %r at %s" % (key, path))
                if key == "reference_stub":
                    self.assertIs(
                        value, True,
                        "reference_stub must be True at %s" % (path,))
                self._walk(value, "%s.%s" % (path, key))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                self.assertNotIsInstance(
                    value, (int, float),
                    "numeric list at %s[%d]" % (path, index))
                self.assertNotIsInstance(
                    value, bool,
                    "boolean list at %s[%d]" % (path, index))
                self._walk(value, "%s[%d]" % (path, index))
        else:
            self.assertNotIsInstance(
                node, float, "float value at %s" % (path,))

    def test_no_tier_key_no_float_no_numeric_list_anywhere(self):
        for record in self._everything():
            self._walk(record)


class MutantExtensions(AIGatewayExtensions):
    """The serving gate with its seam smashed open (drill mutant)."""

    @staticmethod
    def _serving_allowed(model):
        return True


class TestServingGateNegativeControl(unittest.TestCase):
    """Three-leg mutation control for the serving gate seam.

    Leg 1 (canonical): the real gate refuses a serving endpoint
    for a deprecated model. Leg 2 (mutant outcome): with
    ``_serving_allowed`` forced open, the registration succeeds --
    the seam, and nothing else, is what refuses. Leg 3: treating
    the mutant's outcome as the canonical expectation raises
    AssertionError, i.e. this test would fail against the mutant.
    """

    def _expect_refusal(self, ext):
        with self.assertRaises(ValidationError):
            ext.register_serving_endpoint("oldmodel", MEMBER)

    def test_three_leg_control(self):
        ext, store, _audit, _model = make_extensions()
        deprecated_model(store)
        # Leg 1: canonical refusal.
        self._expect_refusal(ext)
        self.assertEqual(ext.list_serving_endpoints(), [])
        # Leg 2: the mutant registers the deprecated model.
        mutant = MutantExtensions(store)
        endpoint = mutant.register_serving_endpoint("oldmodel", MEMBER)
        self.assertEqual(endpoint["model"], "oldmodel")
        # Leg 3: the canonical expectation rejects the mutant.
        with self.assertRaises(AssertionError):
            self._expect_refusal(mutant)


if __name__ == "__main__":
    unittest.main()
