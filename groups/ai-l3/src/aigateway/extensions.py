"""Final GAPS batch extensions for Artificial Intelligence (AI)
L3-adjacent (Group 22).

Clean-room, standard-library-only records/derivation extensions
for the 6 open Extended entries of Group 22's union spec: 2 built
as in-substrate records plus deterministic derivations over the
core's own registries and records (analytics, dashboards &
reporting; the siblings' vertical domain applications), and 4
shipped as labeled reference implementations (learned AI/ML
inference; agentic & automated workflow engines; document
processing & generation workloads; contact center & customer
experience). See ``BATCH.md`` in the group directory for the
per-entry disposition.

This build is Group 9's (AI L2) substrate carried up whole under
the Merge Rule and uplifted to the FedRAMP High baseline; the
extension surface follows the Group 9 batch unit's forms
(``../ai-l2/src/aigateway/extensions.py``) adapted to this group's
baseline as this group's docs state it. The differences that
matter:

- The High apparatus binds every extension operation. Extension
  mutations are recorded on the core's hash-chained audit log,
  and extension record creation is **fail-closed** exactly like
  the core store's mutations (AU-5): if the audit append raises,
  the extension record is rolled back, no object is created, and
  no id is consumed.
- The separated ``auditor`` role (AC-5) holds ``audit_read`` and
  nothing else, so it is denied every extension operation,
  reads included, and the denial is audited ``:denied``; its
  audit-review duty runs through the core log, unchanged.
- The vertical domains are this group's own three, named by the
  entry itself: an AI software-development platform (Cognition),
  an ML lifecycle development & governance platform (DataRobot),
  and digitization-as-a-service (Ripcord).

Design, following the core's doctrines and the founding build's
honesty note (UNION-SPEC.md, "The honesty note on row 1"):

- This module is a wrapper around :class:`AIGatewayStore`; the
  core modules are untouched (byte-identical). Model existence
  and every core record the derivations read are always accessed
  through the core store's public API, never re-implemented.
- **Learned inference is not built, here or anywhere in this
  category.** The core gateway's responder is a deterministic
  reference stub and remains the only thing that produces output
  in this build. Every surface below that names a model's own
  work -- inference, agent execution, document understanding or
  generation, contact orchestration -- ships as records about
  that work: requests, definitions held as data, reported
  outcomes, and opaque result references, each record labeled
  ``reference_stub: True`` with ``inference_here`` /
  ``executed_here`` / ``processed_here`` / ``routed_here`` False
  as applicable. No parameter anywhere on this surface can
  accept prompt text for an external model, document content,
  generated text, or a conversation transcript (pinned by
  TypeError tests).
- The two built surfaces build only what a records substrate can
  honestly hold. Analytics figures are deterministic counts and
  token sums derived at read from the core's own request,
  registry, session, and evaluation-dataset records -- the same
  records the core itself keeps -- over exactly the records
  visible to the requesting actor under the core's read
  discipline; dashboard definitions are held as data (panel
  labels only) and store no figure. Vertical domain applications
  are application profile records bound to the core model
  registry plus activity records and views derived at read; the
  verticals' own engines (Cognition's autonomous coding agent,
  DataRobot's model training, Ripcord's robotics and OCR) are
  stated absent on every record (``operated_here: False``).
- RBAC goes through :mod:`aigateway.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like
  actors, and records denied attempts on the core audit log with
  the extension action name suffixed ``:denied``. Plain-string
  actors carry identity but no role, mirroring the core
  convention. The mapping is:

  - inference requests and outcomes -> ``invoke``;
  - agent workflow definitions -> ``registry_write``; agent run
    requests and outcomes -> ``invoke``;
  - document jobs and results -> ``invoke``;
  - dashboard definitions -> ``registry_write``; analytics and
    dashboard views -> ``read`` (they derive from core records);
  - contact cases, events, and outcomes -> ``invoke``;
  - vertical application registrations -> ``registry_write``;
    application activity records -> ``invoke``; application
    views -> ``read``;
  - the extension summary and all remaining reads -> ``read``.

- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- All references to documents, outputs, cases, and subjects are
  opaque ``*_ref`` strings, SHA-256 digests, or core record ids.
  No record shape in this module can hold content of any kind.
- Derived values are derived at read and never stored: the
  analytics figures, the dashboard panel figures, the
  application activity rollups, and the extension summary.
  Stored records carry no derived key; tests pin that.
- The figure-inclusion rule lives at a single named seam
  (``_counts_toward_figures``): every stored core request record
  counts toward the derived figures, completed and blocked
  alike, mirroring the core's own usage accounting (UNION-SPEC
  core function 4: usage aggregates include blocked records).
  The seam is the batch's fresh negative control.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

DOCUMENT_KINDS = ("extraction", "classification", "summarization", "generation")
KNOWN_DOCUMENT_KINDS = frozenset(DOCUMENT_KINDS)
CONTACT_CHANNELS = ("voice", "chat", "email", "messaging", "social")
KNOWN_CONTACT_CHANNELS = frozenset(CONTACT_CHANNELS)
VERTICAL_DOMAINS = (
    "ai_software_development_platform",
    "ml_lifecycle_development_governance_platform",
    "digitization_as_a_service",
)
KNOWN_VERTICAL_DOMAINS = frozenset(VERTICAL_DOMAINS)
DASHBOARD_PANELS = (
    "requests_by_status",
    "requests_by_model",
    "token_totals",
    "model_registry",
    "evaluation_datasets",
    "usage",
)
KNOWN_DASHBOARD_PANELS = frozenset(DASHBOARD_PANELS)

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

    def _create(self, kind, prefix, fields, actor, audit_action):
        """Create one extension record, fail-closed on audit (AU-5).

        The record is appended and then audited on the core's
        hash-chained log; if the audit append raises (at the High
        baseline, :class:`AuditWriteError`), the record, its order
        entry, and its id allocation are all rolled back and the
        error propagates -- an operation whose audit write fails
        creates no object and consumes no id, exactly like the
        core store's own mutations.
        """
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(copy.deepcopy(fields))
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
                raise
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

    # -- Learned AI/ML inference (reference implementation) ---------
    # The group's #1 family (3 of 3 forks) and the vendors' own
    # proprietary artifacts: real LLMs, ML, NLU, and predictive
    # models are never built here. What ships is the records form
    # of an inference request made elsewhere: a request record
    # bound to a registered model (the prompt is named only by its
    # SHA-256 digest -- no parameter accepts prompt text) and an
    # outcome record whose result is an opaque reference. The core
    # gateway's deterministic responder remains a reference stub
    # and is not a substitute for inference; these records do not
    # invoke it or anything else.

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

    # -- Agentic & automated workflow engines (reference) -----------
    # Workflow definitions are held as data (step labels, an
    # optional registered model); run requests and reported
    # outcomes are records. The registry never executes an agent
    # or a workflow: defining a workflow and requesting a run
    # change no core state, invoke nothing, and create no core
    # request or session record (pinned by test). The agents
    # themselves are inference, per the union spec.

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

    # -- Document processing & generation workloads (reference) -----
    # Extraction, classification, summarization, and generation
    # are inference workloads (UNION-SPEC row 14; in this group
    # one sibling's entire domain in prose). What ships is the
    # job/result records form: a job names its document by an
    # opaque reference and an optional SHA-256 digest (content is
    # never held -- no parameter accepts it), and a result names
    # its output by an opaque reference only.

    def register_document_job(self, kind, document_ref, actor,
                              model_name=None, document_digest=None):
        """Record a document job to be performed elsewhere.

        Action: invoke. Ids: ``dcj-``. ``kind`` is one of the
        recorded document kinds; ``document_ref`` is an opaque
        reference to the document and ``document_digest`` an
        optional SHA-256 of it. Nothing is read, extracted,
        classified, summarized, or generated here.
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
        external system's report; the produced extraction or
        document is named only by an opaque ``result_ref`` and is
        never held here.
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

    # -- Analytics, dashboards & reporting (built) ------------------
    # Dashboard definitions are held as data: a name and panel
    # labels from the fixed panel set. No definition stores a
    # figure. The figures themselves are deterministic derivations
    # over the core's own records -- request records (counts by
    # status and model, token totals), the model and template
    # registries, session records, evaluation datasets, and the
    # core's own usage aggregate for the requesting actor --
    # computed at read over exactly the records visible to the
    # actor under the core's read discipline, and never stored.

    @staticmethod
    def _counts_toward_figures(record):
        """The figure-inclusion seam: every stored core request
        record counts toward the derived figures.

        Completed and blocked alike -- the core's usage accounting
        includes blocked records (UNION-SPEC core function 4), and
        a dashboard that silently dropped blocked traffic would
        misstate the platform's picture. This is the single
        inclusion point for the request figures; the batch's fresh
        negative control mutates it (counting only completed
        records must understate the figures and fail the suite).
        """
        return True

    def _request_figures(self, records):
        """Derive request counts and token totals at read."""
        total = 0
        by_status = {}
        by_model = {}
        total_tokens = 0
        for record in records:
            if not self._counts_toward_figures(record):
                continue
            total += 1
            status = record["status"]
            by_status[status] = by_status.get(status, 0) + 1
            model = record["model"]
            by_model[model] = by_model.get(model, 0) + 1
            total_tokens += record["usage"]["total_tokens"]
        return {
            "total": total,
            "by_status": by_status,
            "by_model": by_model,
            "total_tokens": total_tokens,
        }

    def _platform_figures(self, actor):
        """Derive the full figure set from core records at read."""
        models = self.store.list_models(actor)
        templates = self.store.list_templates(actor)
        requests = self.store.list_requests(actor)
        sessions = self.store.list_sessions(actor)
        datasets = self.store.list_eval_datasets(actor)
        models_by_status = {}
        models_by_responder = {}
        for model in models:
            status = model["status"]
            models_by_status[status] = models_by_status.get(status, 0) + 1
            responder = model["responder"]
            models_by_responder[responder] = \
                models_by_responder.get(responder, 0) + 1
        usage = None
        if actor is not None and actor_name(actor):
            usage = self.store.usage_for(actor_name(actor), actor)
        return {
            "requests": self._request_figures(requests),
            "models_total": len(models),
            "models_by_status": models_by_status,
            "models_by_responder": models_by_responder,
            "templates_total": len(templates),
            "sessions_total": len(sessions),
            "eval_datasets_total": len(datasets),
            "eval_cases_total": sum(len(d["cases"]) for d in datasets),
            "usage_current_month": usage,
        }

    @staticmethod
    def _panel_figures(panel, figures):
        """Select one dashboard panel's figures from the full set."""
        requests = figures["requests"]
        if panel == "requests_by_status":
            return {"total": requests["total"],
                    "by_status": dict(requests["by_status"])}
        if panel == "requests_by_model":
            return {"total": requests["total"],
                    "by_model": dict(requests["by_model"])}
        if panel == "token_totals":
            return {"total_tokens": requests["total_tokens"]}
        if panel == "model_registry":
            return {"models_total": figures["models_total"],
                    "models_by_status": dict(figures["models_by_status"]),
                    "models_by_responder":
                        dict(figures["models_by_responder"]),
                    "templates_total": figures["templates_total"]}
        if panel == "evaluation_datasets":
            return {"eval_datasets_total": figures["eval_datasets_total"],
                    "eval_cases_total": figures["eval_cases_total"]}
        if panel == "usage":
            return {"usage_current_month": figures["usage_current_month"]}
        raise ValidationError("unknown dashboard panel: %r" % (panel,))

    def define_dashboard(self, name, actor, panels=None):
        """Record a dashboard definition as data.

        Action: registry_write. Ids: ``dash-``. ``panels`` are
        panel labels from the fixed panel set, held verbatim as
        data; the definition stores no figure -- figures are
        derived at read by :meth:`dashboard_view`.
        """
        self._guard(actor, "registry_write", "ext_dashboard_define")
        _non_empty(name, "dashboard name")
        panels = _string_list(panels, "panels")
        for panel in panels:
            _one_of(panel, KNOWN_DASHBOARD_PANELS, DASHBOARD_PANELS, "panel")
        with self._lock:
            return self._create(
                "dashboard", "dash",
                {"name": name, "panels": panels},
                actor, "ext_dashboard_define")

    def get_dashboard(self, dashboard_id, actor=None):
        """Return one dashboard definition record. Action: read."""
        self._guard_read(actor, "read", "ext_dashboard_read", dashboard_id)
        return self._fetch("dashboard", dashboard_id)

    def list_dashboards(self, actor=None):
        """Return dashboard definition records. Action: read."""
        self._guard_read(actor, "read", "ext_dashboard_read")
        return self._list("dashboard")

    def analytics_view(self, actor):
        """Platform figures derived at read from core records.

        Action: read. Counts and token sums over exactly the
        records visible to the actor under the core's own read
        discipline (an admin sees all request records; a member
        sees their own), plus the core's usage aggregate for the
        actor themself. Nothing derived is stored anywhere.
        """
        self._guard_read(actor, "read", "ext_analytics_view_read")
        with self._lock:
            figures = self._platform_figures(actor)
            view = dict(figures)
            view["requests"] = dict(figures["requests"])
            view["scope_actor"] = actor_name(actor)
            view["derived"] = True
            return view

    def dashboard_view(self, dashboard_id, actor):
        """A dashboard definition plus its panels' figures.

        Action: read. Each panel's figures are derived at read
        from the core's records (see :meth:`analytics_view`); the
        stored definition carries no figure.
        """
        self._guard_read(actor, "read", "ext_dashboard_read", dashboard_id)
        with self._lock:
            dashboard = self._fetch("dashboard", dashboard_id)
            figures = self._platform_figures(actor)
            view = dict(dashboard)
            view["panels"] = {
                panel: self._panel_figures(panel, figures)
                for panel in dashboard["panels"]
            }
            view["derived"] = True
            return view

    # -- Contact center & customer experience (reference) -----------
    # A vertical application of routing and engagement engines,
    # not platform substrate (UNION-SPEC row 16, carried from the
    # Group 9 union at 0 claims here). What ships is the case
    # record form: a case keyed by an opaque reference with a
    # channel label, event labels recorded as reported, and
    # outcome records whose outputs are opaque references. No
    # customer is contacted, no interaction is routed or
    # orchestrated, and no conversation content exists anywhere
    # on the surface (``customer_name=``, ``message_text=``,
    # ``transcript=`` raise TypeError).

    def register_contact_case(self, case_ref, actor, channel=None,
                              model_name=None):
        """Record a contact-center case handled elsewhere.

        Action: invoke. Ids: ``ccc-``. ``case_ref`` is the owning
        system's opaque case reference; ``channel`` is one of the
        recorded channel labels. No interaction is routed,
        orchestrated, or conducted here.
        """
        self._guard(actor, "invoke", "ext_contact_case_register")
        _non_empty(case_ref, "case_ref")
        if channel is not None:
            _one_of(channel, KNOWN_CONTACT_CHANNELS, CONTACT_CHANNELS,
                    "channel")
        with self._lock:
            model = None
            if model_name is not None:
                model = self._core_model(model_name)["name"]
            return self._create(
                "contact_case", "ccc",
                {"case_ref": case_ref, "channel": channel, "model": model,
                 "reference_stub": True, "routed_here": False,
                 "orchestrated_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_contact_case_register")

    def record_contact_event(self, case_id, event_label, actor):
        """Record a contact case's event, verbatim as reported.

        Action: invoke. Ids: ``cce-``. The event label is the
        owning system's report, stored verbatim; no event is
        enacted here.
        """
        self._guard(actor, "invoke", "ext_contact_event_record", case_id)
        _non_empty(event_label, "event_label")
        with self._lock:
            self._get("contact_case", case_id)
            return self._create(
                "contact_event", "cce",
                {"case_id": case_id, "event_label": event_label,
                 "reference_stub": True, "executed_here": False},
                actor, "ext_contact_event_record")

    def record_contact_outcome(self, case_id, outcome_label, actor,
                               output_ref=None):
        """Record a contact case's outcome, verbatim as reported.

        Action: invoke. Ids: ``cco-``. Any response, summary, or
        follow-up is named only by an opaque ``output_ref`` and is
        never held or produced here.
        """
        self._guard(actor, "invoke", "ext_contact_outcome_record", case_id)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(output_ref, "output_ref")
        with self._lock:
            self._get("contact_case", case_id)
            return self._create(
                "contact_outcome", "cco",
                {"case_id": case_id, "outcome_label": outcome_label,
                 "output_ref": output_ref, "reference_stub": True,
                 "result_held_here": False},
                actor, "ext_contact_outcome_record")

    def get_contact_case(self, case_id, actor=None):
        """Return one contact-case record. Action: read."""
        self._guard_read(actor, "read", "ext_contact_case_read", case_id)
        return self._fetch("contact_case", case_id)

    def list_contact_cases(self, channel=None, actor=None):
        """Return contact-case records. Action: read."""
        self._guard_read(actor, "read", "ext_contact_case_read", channel)
        return self._list("contact_case", channel=channel)

    def list_contact_events(self, case_id=None, actor=None):
        """Return contact-event records. Action: read."""
        self._guard_read(actor, "read", "ext_contact_event_read", case_id)
        if case_id is not None:
            self._get("contact_case", case_id)
        return self._list("contact_event", case_id=case_id)

    def list_contact_outcomes(self, case_id=None, actor=None):
        """Return contact-outcome records. Action: read."""
        self._guard_read(actor, "read", "ext_contact_outcome_read", case_id)
        if case_id is not None:
            self._get("contact_case", case_id)
        return self._list("contact_outcome", case_id=case_id)

    # -- Vertical domain applications (built) -----------------------
    # This group's three siblings are three different verticals
    # wearing one category (UNION-SPEC ranking notes): an AI
    # software-development platform (Cognition), an ML lifecycle
    # development & governance platform (DataRobot), and
    # digitization-as-a-service (Ripcord). What a records
    # substrate can honestly hold for a vertical application is
    # its platform-side surface: an application profile (its
    # domain, from the entry's own named set; its name; its
    # binding to a registered core model), activity records over
    # that profile, and views derived at read. The verticals' own
    # engines -- Cognition's autonomous coding agent, DataRobot's
    # model training and governance machinery, Ripcord's robotics
    # and OCR -- are the siblings' products and are stated absent
    # on every record (``operated_here`` False). No parameter
    # accepts a payload, code, a dataset, a document, or any
    # domain content.

    def register_vertical_application(self, domain, name, actor,
                                      model_name=None):
        """Register a vertical application's profile record.

        Action: registry_write. Ids: ``vap-``. ``domain`` is one
        of the vertical domains named by the gap entry itself;
        an optional ``model_name`` binds the application to a
        registered core model. The application's own engine is
        not operated here.
        """
        self._guard(actor, "registry_write",
                    "ext_vertical_application_register")
        _one_of(domain, KNOWN_VERTICAL_DOMAINS, VERTICAL_DOMAINS, "domain")
        _non_empty(name, "application name")
        with self._lock:
            model = None
            if model_name is not None:
                model = self._core_model(model_name)["name"]
            return self._create(
                "vertical_application", "vap",
                {"domain": domain, "name": name, "model": model,
                 "operated_here": False, "state": "recorded_profile"},
                actor, "ext_vertical_application_register")

    def record_application_activity(self, application_id, activity_label,
                                    actor, subject_ref=None):
        """Record a vertical application's activity, as reported.

        Action: invoke. Ids: ``vaa-``. The activity label is the
        application's own report, stored verbatim; any subject is
        named only by an opaque ``subject_ref``. No activity is
        performed here.
        """
        self._guard(actor, "invoke", "ext_application_activity_record",
                    application_id)
        _non_empty(activity_label, "activity_label")
        _string_or_none(subject_ref, "subject_ref")
        with self._lock:
            self._get("vertical_application", application_id)
            return self._create(
                "application_activity", "vaa",
                {"application_id": application_id,
                 "activity_label": activity_label,
                 "subject_ref": subject_ref, "executed_here": False},
                actor, "ext_application_activity_record")

    def get_vertical_application(self, application_id, actor=None):
        """Return one vertical-application profile. Action: read."""
        self._guard_read(actor, "read", "ext_vertical_application_read",
                         application_id)
        return self._fetch("vertical_application", application_id)

    def list_vertical_applications(self, domain=None, actor=None):
        """Return vertical-application profiles. Action: read."""
        self._guard_read(actor, "read", "ext_vertical_application_read",
                         domain)
        return self._list("vertical_application", domain=domain)

    def list_application_activities(self, application_id=None, actor=None):
        """Return application-activity records. Action: read."""
        self._guard_read(actor, "read", "ext_application_activity_read",
                         application_id)
        if application_id is not None:
            self._get("vertical_application", application_id)
        return self._list("application_activity",
                          application_id=application_id)

    def application_view(self, application_id, actor=None):
        """A profile plus activity rollups derived at read.

        Action: read. Activity totals and the distinct activity
        labels are derived from the application's activity
        records at read; the stored profile carries no totals.
        """
        self._guard_read(actor, "read", "ext_vertical_application_read",
                         application_id)
        with self._lock:
            profile = self._fetch("vertical_application", application_id)
            activities = self._list("application_activity",
                                    application_id=application_id)
            view = dict(profile)
            view["activity_total"] = len(activities)
            view["activity_labels"] = sorted(
                {a["activity_label"] for a in activities})
            view["derived"] = True
            return view

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
