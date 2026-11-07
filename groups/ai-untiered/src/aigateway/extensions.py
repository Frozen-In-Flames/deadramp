"""Final GAPS batch extensions for the Artificial Intelligence
(AI) untiered set.

Clean-room, standard-library-only records/derivation extensions
for the 8 open Extended entries of this set's union spec: 2 built
as in-substrate records plus deterministic derivations over the
core's own registries and harness, and 6 shipped as labeled
reference implementations -- two of them re-judged from their
drafted build-extension disposition (document understanding and
knowledge-base / retrieval: their substance is a running model,
and learned inference is never built in this category). See
``BATCH.md`` in the group directory for the per-entry disposition
and the re-judgment grounds.

Design, following the core's doctrines, the founding AI L2
build's honesty note, and this set's tier discipline:

- This module is a wrapper around :class:`AIGatewayStore`; the
  core modules are untouched (byte-identical). Model, template,
  and evaluation-dataset existence, and evaluation runs
  themselves, are always read or executed through the core
  store's public API, never re-implemented. Existence checks
  against the core pass ``actor=None`` internally: the
  extension's own guard has already enforced the mapped action
  before the check runs.
- **Tier null binds the whole surface.** The set's forks publish
  no FedRAMP impact level, so nothing here asserts or records a
  tier, a control baseline, or an equivalence: no record shape
  carries a tier-shaped key, and the batch tests scan every
  record and view recursively for one (and for floats and
  numeric lists). The forks' documented control claims stay
  where the union spec put them -- in the spec, as the forks'
  claims about themselves.
- **Learned inference is not built, here or anywhere in this
  category.** The core gateway's responder is a deterministic
  reference stub and remains the only thing that produces output
  in this build. Every surface below that names a model's own
  work -- inference, document understanding, retrieval,
  generation, speech -- ships as records about that work:
  requests, reported outcomes, and opaque result references,
  each record labeled ``reference_stub: True`` with
  ``inference_here`` / ``processed_here`` / ``retrieved_here``
  False as applicable. No parameter anywhere on this surface
  can accept prompt text, document content, generated text, an
  embedding, or a vector value (pinned by TypeError tests).
- RBAC goes through :mod:`aigateway.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like
  actors, and records denied attempts on the core audit log with
  the extension action name suffixed ``:denied``. Plain-string
  actors carry identity but no role, mirroring the core
  convention. The mapping is:

  - serving endpoints and serving events -> ``registry_write``
    / ``read`` (they configure the model registry's deployment
    picture);
  - benchmark definitions and benchmark runs -> ``eval_run``;
    benchmark views -> ``read`` (they bind core evaluation
    datasets and runs);
  - agent workflow definitions -> ``registry_write``; agent run
    requests and outcomes -> ``invoke``;
  - inference requests and outcomes -> ``invoke`` (the action a
    real invocation would take; nothing is invoked);
  - voice jobs and outcomes -> ``invoke``;
  - document jobs and results -> ``invoke``;
  - knowledge-base definitions and ingestion records ->
    ``registry_write``; retrieval queries and results ->
    ``invoke``;
  - vertical cases, steps, and outcomes -> ``invoke``;
  - the extension summary and all remaining reads -> ``read``.

- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- All references to people, systems, documents, media, and
  outputs are opaque ``*_ref`` strings, SHA-256 digests, or core
  record ids. No record shape in this module can hold content of
  any kind.
- Derived values are derived at read and never stored: serving
  rollups (endpoint/event counts, the reported-replica total),
  benchmark totals (run count, case and pass totals read from
  the core's own run records), and the extension summary.
  Stored records carry no derived key; tests pin that.
- The serving gate lives at a single named seam
  (``_serving_allowed``): a serving endpoint registers only for
  an *active* model version, mirroring the core's rule that
  deprecated models refuse requests. The seam is the batch's
  fresh negative control.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

BENCHMARK_SCORING = "core_eval_harness"
VOICE_KINDS = (
    "speech_to_text",
    "text_to_speech",
    "voice_agent",
    "real_time_interpretation",
)
KNOWN_VOICE_KINDS = frozenset(VOICE_KINDS)
DOCUMENT_KINDS = ("understanding", "summarization", "report_generation")
KNOWN_DOCUMENT_KINDS = frozenset(DOCUMENT_KINDS)
VERTICALS = ("public_records", "human_services", "contact_center")
KNOWN_VERTICALS = frozenset(VERTICALS)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _nonneg_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(names)))
    return value


def _string_list(value, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("%s must be a list of non-empty strings" % (what,))
    if len(value) > 50:
        raise ValidationError("%s may hold at most 50 entries" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                "each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


def _digest_or_none(value, what):
    """Validate an optional SHA-256 hex digest (content is never held)."""
    if value is None:
        return None
    if not isinstance(value, str) or not _DIGEST_RE.match(value):
        raise ValidationError(
            "%s must be a 64-character lowercase hex SHA-256 digest" % (what,))
    return value


class AIGatewayExtensions:
    """GAPS-batch extension surface over a core AIGatewayStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
        """Enforce a write permission, auditing a denial.

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
        anything changes; plain strings carry identity only.
        """
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r" % (core_action,)
                )
            if hasattr(actor, "role"):
                require(actor, core_action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    def _guard_read(self, actor, core_action, audit_action, target=None):
        """Enforce a read permission when the actor carries a role."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _core_model(self, name, version=None):
        """Return the core model record (NotFoundError if absent)."""
        return self.store.get_model(name, None, version)

    def _core_dataset(self, dataset_id):
        """Return the core eval dataset record (NotFoundError if absent)."""
        return self.store.get_eval_dataset(dataset_id, None)

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(copy.deepcopy(fields))
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id,
                        details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(name) == value for name, value in filters.items()
                   if value is not None):
                result.append(copy.deepcopy(record))
        return result

    # -- Model serving & inference infrastructure (configuration
    # records over the core model registry) -------------------------
    # An endpoint here is a configuration record: it declares that
    # a registered model version is the subject of a serving
    # deployment, with a replica count and region label recorded
    # exactly as reported by the owning platform. No infrastructure
    # is provisioned, nothing is autoscaled, and nothing is served
    # by these records -- the gateway's reference responder remains
    # the only responder in the build. Rollups are derived at read.

    @staticmethod
    def _serving_allowed(model):
        """The serving gate seam: only an active model version may
        be registered as served.

        Mirrors the core's rule that deprecated models refuse
        requests. This is the single derivation point for the
        gate -- the batch's fresh negative control mutates it (a
        gate that waves deprecated models through must not
        produce the canonical refusal).
        """
        return model["status"] == "active"

    @staticmethod
    def _replica_total(endpoint_records):
        """Sum the reported replica counts of endpoint records."""
        return sum(record["replicas_reported"] for record in endpoint_records)

    def register_serving_endpoint(self, model_name, actor, version=None,
                                  replicas_reported=1, region_label=None):
        """Register a serving-endpoint configuration record.

        Action: registry_write. The model must exist in the core
        registry and be active (the serving gate,
        :meth:`_serving_allowed`); ``version=None`` selects the
        highest registered version, as in the core. Ids: ``sep-``.
        """
        self._guard(actor, "registry_write", "ext_serving_endpoint_register",
                    model_name)
        _non_empty(model_name, "model name")
        _nonneg_int(replicas_reported, "replicas_reported")
        _string_or_none(region_label, "region_label")
        with self._lock:
            model = self._core_model(model_name, version)
            if not self._serving_allowed(model):
                raise ValidationError(
                    "model %r version %d is deprecated; serving endpoints "
                    "register only for active models"
                    % (model["name"], model["version"]))
            return self._create(
                "serving_endpoint", "sep",
                {"model": model["name"], "model_version": model["version"],
                 "replicas_reported": replicas_reported,
                 "region_label": region_label,
                 "provisioned_here": False, "autoscaled_here": False,
                 "state": "recorded_configuration"},
                actor, "ext_serving_endpoint_register")

    def get_serving_endpoint(self, endpoint_id, actor=None):
        """Return one serving-endpoint record. Action: read."""
        self._guard_read(actor, "read", "ext_serving_endpoint_read",
                         endpoint_id)
        return self._fetch("serving_endpoint", endpoint_id)

    def list_serving_endpoints(self, model=None, actor=None):
        """Return serving-endpoint records. Action: read."""
        self._guard_read(actor, "read", "ext_serving_endpoint_read", model)
        return self._list("serving_endpoint", model=model)

    def record_serving_event(self, endpoint_id, event_label, actor):
        """Record a serving event label as reported by the platform.

        Action: registry_write. Ids: ``sev-``. The label is the
        platform's own report (a deployment, a scaling action, a
        health transition), stored verbatim; no event is enacted
        here.
        """
        self._guard(actor, "registry_write", "ext_serving_event_record",
                    endpoint_id)
        _non_empty(event_label, "event_label")
        with self._lock:
            self._get("serving_endpoint", endpoint_id)
            return self._create(
                "serving_event", "sev",
                {"endpoint_id": endpoint_id, "event_label": event_label,
                 "reported": True, "enacted_here": False},
                actor, "ext_serving_event_record")

    def list_serving_events(self, endpoint_id=None, actor=None):
        """Return serving-event records. Action: read."""
        self._guard_read(actor, "read", "ext_serving_event_read", endpoint_id)
        if endpoint_id is not None:
            self._get("serving_endpoint", endpoint_id)
        return self._list("serving_event", endpoint_id=endpoint_id)

    def serving_summary(self, actor=None):
        """Serving rollup derived at read. Action: read.

        Counts of endpoint and event records, the total of the
        reported replica counts, and the sorted model names with
        endpoints. Nothing derived is stored anywhere.
        """
        self._guard_read(actor, "read", "ext_serving_summary_read")
        with self._lock:
            endpoints = self._list("serving_endpoint")
            events = self._list("serving_event")
            return {
                "endpoints": len(endpoints),
                "events": len(events),
                "replicas_reported_total": self._replica_total(endpoints),
                "models": sorted({e["model"] for e in endpoints}),
                "derived": True,
            }

    # -- Evaluation & benchmarking (records over the core harness) --
    # A benchmark here binds one core evaluation dataset to one
    # registered model. A benchmark run is a core evaluation run:
    # it is executed by the core harness itself (the deterministic
    # exact/contains/rubric scoring over the registered reference
    # responder) and recorded by the core; this surface keeps only
    # the link. Totals in the view are read back from the core's
    # run records at read time -- this surface scores nothing, and
    # no external model is ever benchmarked.

    def define_benchmark(self, name, dataset_id, model_name, actor,
                         model_version=None):
        """Define a benchmark over a core dataset and model.

        Action: eval_run. The dataset and the model must exist in
        the core. ``model_version=None`` resolves to the highest
        registered version at definition time. Ids: ``bmk-``.
        """
        self._guard(actor, "eval_run", "ext_benchmark_define", dataset_id)
        _non_empty(name, "benchmark name")
        with self._lock:
            self._core_dataset(dataset_id)
            model = self._core_model(model_name, model_version)
            return self._create(
                "benchmark", "bmk",
                {"name": name, "dataset_id": dataset_id,
                 "model": model["name"], "model_version": model["version"],
                 "scoring": BENCHMARK_SCORING,
                 "external_models_evaluated": False},
                actor, "ext_benchmark_define")

    def get_benchmark(self, benchmark_id, actor=None):
        """Return one benchmark definition record. Action: read."""
        self._guard_read(actor, "read", "ext_benchmark_read", benchmark_id)
        return self._fetch("benchmark", benchmark_id)

    def list_benchmarks(self, actor=None):
        """Return benchmark definition records. Action: read."""
        self._guard_read(actor, "read", "ext_benchmark_read")
        return self._list("benchmark")

    def run_benchmark(self, benchmark_id, actor):
        """Run a benchmark through the core evaluation harness.

        Action: eval_run. Executes ``store.run_eval`` for the
        benchmark's dataset and model and records the link
        (``bmr-``); returns the core run record itself. The core's
        rules apply unchanged (a deprecated model refuses, and a
        refused run records no link and consumes no id). Scoring
        is the harness's deterministic scoring of the reference
        responder -- nothing new is scored here.
        """
        self._guard(actor, "eval_run", "ext_benchmark_run", benchmark_id)
        with self._lock:
            benchmark = self._get("benchmark", benchmark_id)
            run = self.store.run_eval(
                benchmark["dataset_id"], benchmark["model"], actor,
                version=benchmark["model_version"])
            self._create(
                "benchmark_run", "bmr",
                {"benchmark_id": benchmark_id, "eval_run_id": run["id"],
                 "dataset_id": benchmark["dataset_id"],
                 "model": benchmark["model"],
                 "model_version": benchmark["model_version"]},
                actor, "ext_benchmark_run")
            return run

    def list_benchmark_runs(self, benchmark_id=None, actor=None):
        """Return benchmark run-link records. Action: read."""
        self._guard_read(actor, "read", "ext_benchmark_read", benchmark_id)
        if benchmark_id is not None:
            self._get("benchmark", benchmark_id)
        return self._list("benchmark_run", benchmark_id=benchmark_id)

    def benchmark_view(self, benchmark_id, actor):
        """A benchmark plus totals derived at read. Action: read.

        Run, case, and pass totals are summed at read from the
        core's own run records; the stored definition and link
        records carry no totals. Reading the runs inherits the
        core's discipline: the actor must be each run's creator
        or a platform admin.
        """
        self._guard_read(actor, "read", "ext_benchmark_read", benchmark_id)
        with self._lock:
            benchmark = self._fetch("benchmark", benchmark_id)
            links = self._list("benchmark_run", benchmark_id=benchmark_id)
            total_cases = 0
            total_passed = 0
            run_ids = []
            for link in links:
                run = self.store.get_eval_run(link["eval_run_id"], actor)
                run_ids.append(run["id"])
                total_cases += run["total"]
                total_passed += run["passed"]
            view = dict(benchmark)
            view["runs"] = run_ids
            view["run_count"] = len(run_ids)
            view["total_cases"] = total_cases
            view["total_passed"] = total_passed
            view["derived"] = True
            return view

    # -- Learned inference (reference implementation) ---------------
    # The models themselves are the vendors' own artifacts and are
    # never built in this category. What ships is the records form
    # of an inference request made elsewhere: a request record
    # bound to a registered model (the prompt is named only by its
    # SHA-256 digest -- no parameter accepts prompt text) and an
    # outcome record whose result is an opaque reference. Every
    # record carries reference_stub: True.

    def register_inference_request(self, model_name, actor, version=None,
                                   prompt_digest=None):
        """Record a request for inference by a registered model.

        Action: invoke. The model must exist in the core registry;
        the request is recorded, never executed -- no model runs
        here (``inference_here`` is False). The prompt is
        identified only by an optional SHA-256 digest. Ids:
        ``ireq-``.
        """
        self._guard(actor, "invoke", "ext_inference_request_register",
                    model_name)
        _non_empty(model_name, "model name")
        prompt_digest = _digest_or_none(prompt_digest, "prompt_digest")
        with self._lock:
            model = self._core_model(model_name, version)
            return self._create(
                "inference_request", "ireq",
                {"model": model["name"], "model_version": model["version"],
                 "prompt_digest": prompt_digest,
                 "reference_stub": True, "inference_here": False,
                 "executed_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_inference_request_register")

    def record_inference_outcome(self, request_id, outcome_label, actor,
                                 output_ref=None):
        """Record an inference outcome, verbatim as reported.

        Action: invoke. Ids: ``iout-``. The outcome label is the
        model operator's report; the output itself is named only
        by an opaque ``output_ref`` and is never held here.
        """
        self._guard(actor, "invoke", "ext_inference_outcome_record",
                    request_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(output_ref, "output_ref")
        with self._lock:
            self._get("inference_request", request_id)
            return self._create(
                "inference_outcome", "iout",
                {"request_id": request_id, "outcome_label": outcome_label,
                 "output_ref": output_ref, "reference_stub": True,
                 "result_held_here": False},
                actor, "ext_inference_outcome_record")

    def get_inference_request(self, request_id, actor=None):
        """Return one inference-request record. Action: read."""
        self._guard_read(actor, "read", "ext_inference_request_read",
                         request_id)
        return self._fetch("inference_request", request_id)

    def list_inference_requests(self, actor=None):
        """Return inference-request records. Action: read."""
        self._guard_read(actor, "read", "ext_inference_request_read")
        return self._list("inference_request")

    def list_inference_outcomes(self, request_id=None, actor=None):
        """Return inference-outcome records. Action: read."""
        self._guard_read(actor, "read", "ext_inference_outcome_read",
                         request_id)
        if request_id is not None:
            self._get("inference_request", request_id)
        return self._list("inference_outcome", request_id=request_id)

    # -- Agentic workflow execution (reference implementation) ------
    # Workflow definitions are held as data (step labels, an
    # optional registered model); run requests and reported
    # outcomes are records. The registry never executes an agent
    # or a workflow: defining a workflow and requesting a run
    # change no core state, invoke nothing, and create no core
    # request or session record (pinned by test).

    def define_agent_workflow(self, name, actor, steps=None, model_name=None):
        """Record an agent-workflow definition as data.

        Action: registry_write. Ids: ``awf-``. ``steps`` are step
        labels held verbatim as data; an optional ``model_name``
        must name a registered model. Nothing executes.
        """
        self._guard(actor, "registry_write", "ext_agent_workflow_define")
        _non_empty(name, "workflow name")
        steps = _string_list(steps, "steps")
        with self._lock:
            model = None
            if model_name is not None:
                model = self._core_model(model_name)["name"]
            return self._create(
                "agent_workflow", "awf",
                {"name": name, "steps": steps, "model": model,
                 "definition_only": True, "reference_stub": True,
                 "executed_here": False},
                actor, "ext_agent_workflow_define")

    def request_agent_run(self, workflow_id, actor, input_ref=None):
        """Record a request to run a workflow elsewhere.

        Action: invoke. Ids: ``arun-``. The run is requested, not
        performed: no agent runs here (``executed_here`` False).
        Any input is named only by an opaque ``input_ref``.
        """
        self._guard(actor, "invoke", "ext_agent_run_request", workflow_id)
        _string_or_none(input_ref, "input_ref")
        with self._lock:
            self._get("agent_workflow", workflow_id)
            return self._create(
                "agent_run", "arun",
                {"workflow_id": workflow_id, "input_ref": input_ref,
                 "reference_stub": True, "executed_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_agent_run_request")

    def record_agent_run_outcome(self, run_id, outcome_label, actor,
                                 output_ref=None):
        """Record an agent run's outcome, verbatim as reported.

        Action: invoke. Ids: ``aout-``. The outcome is the
        external runtime's report; any output is named only by an
        opaque ``output_ref`` and is never held here.
        """
        self._guard(actor, "invoke", "ext_agent_run_outcome_record", run_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(output_ref, "output_ref")
        with self._lock:
            self._get("agent_run", run_id)
            return self._create(
                "agent_outcome", "aout",
                {"run_id": run_id, "outcome_label": outcome_label,
                 "output_ref": output_ref, "reference_stub": True,
                 "executed_here": False, "result_held_here": False},
                actor, "ext_agent_run_outcome_record")

    def get_agent_workflow(self, workflow_id, actor=None):
        """Return one workflow definition record. Action: read."""
        self._guard_read(actor, "read", "ext_agent_workflow_read", workflow_id)
        return self._fetch("agent_workflow", workflow_id)

    def list_agent_workflows(self, actor=None):
        """Return workflow definition records. Action: read."""
        self._guard_read(actor, "read", "ext_agent_workflow_read")
        return self._list("agent_workflow")

    def list_agent_runs(self, workflow_id=None, actor=None):
        """Return agent run-request records. Action: read."""
        self._guard_read(actor, "read", "ext_agent_run_read", workflow_id)
        if workflow_id is not None:
            self._get("agent_workflow", workflow_id)
        return self._list("agent_run", workflow_id=workflow_id)

    def list_agent_outcomes(self, run_id=None, actor=None):
        """Return agent run-outcome records. Action: read."""
        self._guard_read(actor, "read", "ext_agent_outcome_read", run_id)
        if run_id is not None:
            self._get("agent_run", run_id)
        return self._list("agent_outcome", run_id=run_id)

    # -- Voice & speech AI (reference implementation) ---------------
    # Speech-to-text, text-to-speech, voice agents, and real-time
    # interpretation are learned-model and media engines; none
    # runs here. A voice job is a record: its kind, an optional
    # registered model, and an opaque input reference. Outcomes
    # are reported labels; transcripts, synthesized audio, and
    # every other result exist only as opaque references -- no
    # parameter accepts media or text content.

    def register_voice_job(self, kind, actor, model_name=None, input_ref=None):
        """Record a voice/speech job to be performed elsewhere.

        Action: invoke. Ids: ``voj-``. ``kind`` is one of the
        recorded voice kinds; an optional ``model_name`` must name
        a registered model. No audio is held and nothing is
        transcribed, synthesized, or interpreted here.
        """
        self._guard(actor, "invoke", "ext_voice_job_register")
        _one_of(kind, KNOWN_VOICE_KINDS, VOICE_KINDS, "voice kind")
        _string_or_none(input_ref, "input_ref")
        with self._lock:
            model = None
            if model_name is not None:
                model = self._core_model(model_name)["name"]
            return self._create(
                "voice_job", "voj",
                {"kind": kind, "model": model, "input_ref": input_ref,
                 "reference_stub": True, "processed_here": False,
                 "media_held": False, "state": "recorded_reference_only"},
                actor, "ext_voice_job_register")

    def record_voice_outcome(self, job_id, outcome_label, actor,
                             result_ref=None):
        """Record a voice job's outcome, verbatim as reported.

        Action: invoke. Ids: ``vou-``. Any transcript, audio, or
        interpretation result is named only by an opaque
        ``result_ref`` and is never held here.
        """
        self._guard(actor, "invoke", "ext_voice_outcome_record", job_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(result_ref, "result_ref")
        with self._lock:
            self._get("voice_job", job_id)
            return self._create(
                "voice_outcome", "vou",
                {"job_id": job_id, "outcome_label": outcome_label,
                 "result_ref": result_ref, "reference_stub": True,
                 "result_held_here": False},
                actor, "ext_voice_outcome_record")

    def get_voice_job(self, job_id, actor=None):
        """Return one voice-job record. Action: read."""
        self._guard_read(actor, "read", "ext_voice_job_read", job_id)
        return self._fetch("voice_job", job_id)

    def list_voice_jobs(self, actor=None):
        """Return voice-job records. Action: read."""
        self._guard_read(actor, "read", "ext_voice_job_read")
        return self._list("voice_job")

    def list_voice_outcomes(self, job_id=None, actor=None):
        """Return voice-outcome records. Action: read."""
        self._guard_read(actor, "read", "ext_voice_outcome_read", job_id)
        if job_id is not None:
            self._get("voice_job", job_id)
        return self._list("voice_outcome", job_id=job_id)

    # -- Document understanding, summarization & report generation
    # (reference implementation -- re-judged; see BATCH.md) --------
    # Understanding a document, summarizing it, and generating a
    # report are a running model's work. What ships is the
    # request/result records form: a job names its document by an
    # opaque reference and an optional SHA-256 digest (content is
    # never held -- no parameter accepts it), and a result names
    # its output by an opaque reference only.

    def register_document_job(self, kind, document_ref, actor,
                              model_name=None, document_digest=None):
        """Record a document job to be performed elsewhere.

        Action: invoke. Ids: ``dcj-``. ``kind`` is one of the
        recorded document kinds; ``document_ref`` is an opaque
        reference to the document and ``document_digest`` an
        optional SHA-256 of it. Nothing is read, understood,
        summarized, or generated here.
        """
        self._guard(actor, "invoke", "ext_document_job_register")
        _one_of(kind, KNOWN_DOCUMENT_KINDS, DOCUMENT_KINDS, "document kind")
        _non_empty(document_ref, "document_ref")
        document_digest = _digest_or_none(document_digest, "document_digest")
        with self._lock:
            model = None
            if model_name is not None:
                model = self._core_model(model_name)["name"]
            return self._create(
                "document_job", "dcj",
                {"kind": kind, "document_ref": document_ref,
                 "document_digest": document_digest, "model": model,
                 "reference_stub": True, "processed_here": False,
                 "generated_here": False, "content_held": False,
                 "state": "recorded_reference_only"},
                actor, "ext_document_job_register")

    def record_document_result(self, job_id, outcome_label, actor,
                               result_ref=None):
        """Record a document job's result, verbatim as reported.

        Action: invoke. Ids: ``dcr-``. The outcome label is the
        external system's report; the produced summary or report
        is named only by an opaque ``result_ref`` and is never
        held here.
        """
        self._guard(actor, "invoke", "ext_document_result_record", job_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(result_ref, "result_ref")
        with self._lock:
            self._get("document_job", job_id)
            return self._create(
                "document_result", "dcr",
                {"job_id": job_id, "outcome_label": outcome_label,
                 "result_ref": result_ref, "reference_stub": True,
                 "result_held_here": False},
                actor, "ext_document_result_record")

    def get_document_job(self, job_id, actor=None):
        """Return one document-job record. Action: read."""
        self._guard_read(actor, "read", "ext_document_job_read", job_id)
        return self._fetch("document_job", job_id)

    def list_document_jobs(self, actor=None):
        """Return document-job records. Action: read."""
        self._guard_read(actor, "read", "ext_document_job_read")
        return self._list("document_job")

    def list_document_results(self, job_id=None, actor=None):
        """Return document-result records. Action: read."""
        self._guard_read(actor, "read", "ext_document_result_read", job_id)
        if job_id is not None:
            self._get("document_job", job_id)
        return self._list("document_result", job_id=job_id)

    # -- Knowledge-base / retrieval (reference implementation --
    # re-judged; see BATCH.md) --------------------------------------
    # A knowledge base here is a definition record: a name and the
    # opaque references of its sources, plus ingestion records
    # whose counts are stored exactly as reported. Retrieval is
    # recorded, never performed: a query is named only by its
    # SHA-256 digest, and a result's answer exists only as an
    # opaque reference with its citation references. No embedding
    # is computed, no index is built, and no parameter can accept
    # a vector value, query text, or answer text.

    def define_knowledge_base(self, name, actor, source_refs=None):
        """Record a knowledge-base definition as data.

        Action: registry_write. Ids: ``kb-``. ``source_refs`` are
        opaque references to the sources the owning platform
        indexes; nothing is fetched, embedded, or indexed here.
        """
        self._guard(actor, "registry_write", "ext_knowledge_base_define")
        _non_empty(name, "knowledge base name")
        source_refs = _string_list(source_refs, "source_refs")
        with self._lock:
            return self._create(
                "knowledge_base", "kb",
                {"name": name, "source_refs": source_refs,
                 "definition_only": True, "reference_stub": True,
                 "embeddings_computed_here": False,
                 "index_built_here": False},
                actor, "ext_knowledge_base_define")

    def record_kb_ingestion(self, kb_id, actor, documents_reported=0,
                            chunks_reported=0):
        """Record an ingestion's counts as reported.

        Action: registry_write. Ids: ``kbi-``. The counts are the
        owning platform's report, stored verbatim; no source was
        fetched and nothing was embedded or indexed here.
        """
        self._guard(actor, "registry_write", "ext_kb_ingestion_record", kb_id)
        _nonneg_int(documents_reported, "documents_reported")
        _nonneg_int(chunks_reported, "chunks_reported")
        with self._lock:
            self._get("knowledge_base", kb_id)
            return self._create(
                "kb_ingestion", "kbi",
                {"kb_id": kb_id,
                 "documents_reported": documents_reported,
                 "chunks_reported": chunks_reported,
                 "reference_stub": True, "indexed_here": False},
                actor, "ext_kb_ingestion_record")

    def register_retrieval_query(self, kb_id, actor, query_digest=None):
        """Record a retrieval query against a knowledge base.

        Action: invoke. Ids: ``rtq-``. The query is identified
        only by an optional SHA-256 digest; no query text is
        accepted or held, and nothing is retrieved here.
        """
        self._guard(actor, "invoke", "ext_retrieval_query_register", kb_id)
        query_digest = _digest_or_none(query_digest, "query_digest")
        with self._lock:
            self._get("knowledge_base", kb_id)
            return self._create(
                "retrieval_query", "rtq",
                {"kb_id": kb_id, "query_digest": query_digest,
                 "reference_stub": True, "retrieved_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_retrieval_query_register")

    def record_retrieval_result(self, query_id, outcome_label, actor,
                                answer_ref=None, citation_refs=None):
        """Record a retrieval result, verbatim as reported.

        Action: invoke. Ids: ``rtr-``. The answer is named only by
        an opaque ``answer_ref`` and its grounding only by opaque
        ``citation_refs``; no answer text is held and no grounding
        is performed or verified here.
        """
        self._guard(actor, "invoke", "ext_retrieval_result_record", query_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(answer_ref, "answer_ref")
        citation_refs = _string_list(citation_refs, "citation_refs")
        with self._lock:
            self._get("retrieval_query", query_id)
            return self._create(
                "retrieval_result", "rtr",
                {"query_id": query_id, "outcome_label": outcome_label,
                 "answer_ref": answer_ref, "citation_refs": citation_refs,
                 "reference_stub": True, "answer_held": False,
                 "grounded_here": False},
                actor, "ext_retrieval_result_record")

    def get_knowledge_base(self, kb_id, actor=None):
        """Return one knowledge-base definition. Action: read."""
        self._guard_read(actor, "read", "ext_knowledge_base_read", kb_id)
        return self._fetch("knowledge_base", kb_id)

    def list_knowledge_bases(self, actor=None):
        """Return knowledge-base definitions. Action: read."""
        self._guard_read(actor, "read", "ext_knowledge_base_read")
        return self._list("knowledge_base")

    def list_kb_ingestions(self, kb_id=None, actor=None):
        """Return knowledge-base ingestion records. Action: read."""
        self._guard_read(actor, "read", "ext_kb_ingestion_read", kb_id)
        if kb_id is not None:
            self._get("knowledge_base", kb_id)
        return self._list("kb_ingestion", kb_id=kb_id)

    def list_retrieval_queries(self, kb_id=None, actor=None):
        """Return retrieval-query records. Action: read."""
        self._guard_read(actor, "read", "ext_retrieval_query_read", kb_id)
        if kb_id is not None:
            self._get("knowledge_base", kb_id)
        return self._list("retrieval_query", kb_id=kb_id)

    def list_retrieval_results(self, query_id=None, actor=None):
        """Return retrieval-result records. Action: read."""
        self._guard_read(actor, "read", "ext_retrieval_result_read", query_id)
        if query_id is not None:
            self._get("retrieval_query", query_id)
        return self._list("retrieval_result", query_id=query_id)

    # -- Vertical workflow applications (reference implementation) -
    # Public-records generation, human-services case work, and
    # constituent contact-center work are vertical applications of
    # the vendors' models and operations; none is performed here.
    # What ships is the case record form: a case keyed by an
    # opaque reference, step labels recorded as reported, and
    # outcome records whose outputs are opaque references.

    def register_vertical_case(self, vertical, case_ref, actor,
                               model_name=None):
        """Record a vertical-application case handled elsewhere.

        Action: invoke. Ids: ``vtc-``. ``vertical`` is one of the
        recorded verticals; ``case_ref`` is the owning system's
        opaque case reference. No casework is performed, no record
        is generated, and no constituent is contacted here.
        """
        self._guard(actor, "invoke", "ext_vertical_case_register")
        _one_of(vertical, KNOWN_VERTICALS, VERTICALS, "vertical")
        _non_empty(case_ref, "case_ref")
        with self._lock:
            model = None
            if model_name is not None:
                model = self._core_model(model_name)["name"]
            return self._create(
                "vertical_case", "vtc",
                {"vertical": vertical, "case_ref": case_ref, "model": model,
                 "reference_stub": True, "casework_performed_here": False,
                 "records_generated_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_vertical_case_register")

    def record_vertical_step(self, case_id, step_label, actor):
        """Record a vertical case's workflow step, as reported.

        Action: invoke. Ids: ``vts-``. The step label is the
        owning system's report, stored verbatim; no step is
        executed here.
        """
        self._guard(actor, "invoke", "ext_vertical_step_record", case_id)
        _non_empty(step_label, "step_label")
        with self._lock:
            self._get("vertical_case", case_id)
            return self._create(
                "vertical_step", "vts",
                {"case_id": case_id, "step_label": step_label,
                 "reference_stub": True, "executed_here": False},
                actor, "ext_vertical_step_record")

    def record_vertical_outcome(self, case_id, outcome_label, actor,
                                output_ref=None):
        """Record a vertical case's outcome, verbatim as reported.

        Action: invoke. Ids: ``vto-``. Any produced record,
        letter, or response is named only by an opaque
        ``output_ref`` and is never held or generated here.
        """
        self._guard(actor, "invoke", "ext_vertical_outcome_record", case_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(output_ref, "output_ref")
        with self._lock:
            self._get("vertical_case", case_id)
            return self._create(
                "vertical_outcome", "vto",
                {"case_id": case_id, "outcome_label": outcome_label,
                 "output_ref": output_ref, "reference_stub": True,
                 "result_held_here": False},
                actor, "ext_vertical_outcome_record")

    def get_vertical_case(self, case_id, actor=None):
        """Return one vertical-case record. Action: read."""
        self._guard_read(actor, "read", "ext_vertical_case_read", case_id)
        return self._fetch("vertical_case", case_id)

    def list_vertical_cases(self, vertical=None, actor=None):
        """Return vertical-case records. Action: read."""
        self._guard_read(actor, "read", "ext_vertical_case_read", vertical)
        return self._list("vertical_case", vertical=vertical)

    def list_vertical_steps(self, case_id=None, actor=None):
        """Return vertical-step records. Action: read."""
        self._guard_read(actor, "read", "ext_vertical_step_read", case_id)
        if case_id is not None:
            self._get("vertical_case", case_id)
        return self._list("vertical_step", case_id=case_id)

    def list_vertical_outcomes(self, case_id=None, actor=None):
        """Return vertical-outcome records. Action: read."""
        self._guard_read(actor, "read", "ext_vertical_outcome_read", case_id)
        if case_id is not None:
            self._get("vertical_case", case_id)
        return self._list("vertical_outcome", case_id=case_id)

    # -- Extension summary -------------------------------------------

    def extension_summary(self, actor=None):
        """Counts of every extension record kind, derived at read.

        Action: read. A census of the extension surface only --
        counts of records, nothing about any external system.
        """
        self._guard_read(actor, "read", "ext_summary_read")
        with self._lock:
            by_kind = {}
            for kind, _record_id in self._order:
                by_kind[kind] = by_kind.get(kind, 0) + 1
            return {
                "records_total": len(self._order),
                "by_kind": by_kind,
                "derived": True,
            }
