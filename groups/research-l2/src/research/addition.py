"""Final GAPS batch additions for Research L2 — remainder unit.

Clean-room, standard-library-only extension surface for the 9
open entries of the "Remainder Addition — Research L2 (+5 forks)"
section of GAPS.md (see ``BATCH-ADDITION.md`` in the group
directory for the per-entry disposition). This module is a second
wrapper around :class:`ResearchStore`, sibling to
``research.extensions``; every core module and ``extensions.py``
itself are untouched and byte-identical to the shipped build.

**The founding discipline binds absolutely, here as in the core
and the first batch unit:** the commons is a registry of dataset
records and counts, and every entity shape in this module carries
metadata and opaque caller-supplied references only. No shape has
a field for research subject data, a dataset payload, an analysis
result text, a sample's subject, a diagnosis, or a signature
value — those fields **do not exist**. Methods accept only their
named parameters, so a caller cannot smuggle a forbidden field
into a record (pinned by tests: an unexpected keyword raises
``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — definition and outcome records over the
group's OWN records (core records and addition records), plus
deterministic derivations at read:

- Bioinformatics pipelines are pipeline *definitions* held as
  data plus run-request and reported-outcome records; nothing
  runs an analysis here (``executed_here`` False).
- Elastic allocation is allocation *request* records plus
  reported allocation outcomes; no scheduler runs here
  (``allocated_here`` False), and derived totals are sums of
  recorded reported values only.
- AI analytics is analysis-request records whose results are held
  as opaque references only; no inference runs here and no result
  text exists to hold (``inference_here`` False).
- Technology transfer is disclosure and agreement records whose
  negotiated or executed terms are append-only reported state
  labels; the current state is derived at read, and nothing is
  executed here (``executed_here`` False).
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``. Interactive environments are
  definitions as data (nothing is provisioned), diagnostic
  monitoring / BioBank tracking keys samples by opaque sample
  references only — no subject identity and no diagnosis field
  exists — knowledge-graph nodes and edges are metadata
  references (nothing is traversed), survey definitions and
  reported response counts collect nothing, and document
  generation / e-signature / integration components are request
  and reference records that generate, sign, and connect nothing.

Doctrines carried from the core: derived-never-stored for every
computed value (agreement current state, all summaries);
append-only audit on the core store's log with ``add_``-prefixed
actions for every successful mutation, and denied write attempts
recorded with a ``:denied`` suffix; RBAC via
:mod:`research.access` with the core's existing actions, enforced
before any state change or id allocation, so a failed operation
consumes no id and changes nothing; the commons membership
boundary is enforced through the core store's own commons access
check on every operation.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PIPELINE_RUN_OUTCOMES = (
    "reported_completed",
    "reported_partial",
    "reported_failed",
)
ALLOCATION_OUTCOMES = (
    "reported_granted",
    "reported_partial",
    "reported_refused",
)
AGREEMENT_STATES = (
    "reported_proposed",
    "reported_negotiated",
    "reported_executed",
    "reported_lapsed",
)
ENVIRONMENT_SESSION_OUTCOMES = (
    "reported_completed",
    "reported_failed",
)
MONITOR_OUTCOMES = (
    "reported_detected",
    "reported_not_detected",
    "reported_inconclusive",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _count(value, what):
    """A non-negative integer count; booleans and floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _positive(value, what):
    """A positive integer amount; booleans and floats rejected."""
    _count(value, what)
    if value == 0:
        raise ValidationError("%s must be a positive integer" % (what,))
    return value


def _ref_list(value, what, unique=False):
    """A non-empty list of opaque reference names, held as data."""
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of reference names" % (what,))
    items = list(value)
    if not items:
        raise ValidationError("%s must be a non-empty list" % (what,))
    for item in items:
        _non_empty(item, what)
    if unique and len(set(items)) != len(items):
        raise ValidationError("%s must not contain duplicates" % (what,))
    return items


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class ResearchAdditions:
    """Addition surface wrapping one :class:`ResearchStore`."""

    def __init__(self, store):
        self.store = store
        self._pipeline_defs = {}
        self._pipeline_run_requests = {}
        self._pipeline_run_outcomes = {}
        self._allocation_requests = {}
        self._allocation_outcomes = {}
        self._analysis_requests = {}
        self._analysis_results = {}
        self._disclosures = {}
        self._agreements = {}
        self._agreement_states = {}
        self._environments = {}
        self._environment_sessions = {}
        self._samples = {}
        self._monitor_outcomes = {}
        self._graph_nodes = {}
        self._graph_edges = {}
        self._surveys = {}
        self._survey_responses = {}
        self._docgen_requests = {}
        self._signing_requests = {}
        self._integration_references = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`research.access.require`; a plain string carries
        identity but no role). A denied attempt is recorded on the
        audit log with a ``:denied`` suffix before the error
        propagates; a missing actor is denied outright.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    def _commons(self, actor, commons_id):
        """Resolve a commons through the core store, which enforces
        the read permission and the membership boundary (the
        platform admin reaches every commons)."""
        return self.store.get_commons(actor, commons_id)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _check_commons_of(self, actor, record):
        self._commons(actor, record["commons_id"])

    def _dataset_in(self, actor, commons_id, dataset_id):
        """Resolve a core dataset and require it to live in
        ``commons_id`` (the core store enforces membership)."""
        dataset = self.store.get_dataset(actor, dataset_id)
        if dataset["commons_id"] != commons_id:
            raise ValidationError(
                "dataset %r is not in commons %r" % (dataset_id, commons_id))
        return dataset

    def _workspace_in(self, actor, commons_id, workspace_id):
        """Resolve a core workspace and require it to live in
        ``commons_id`` (the core store enforces membership)."""
        workspace = self.store.get_workspace(actor, workspace_id)
        if workspace["commons_id"] != commons_id:
            raise ValidationError(
                "workspace %r is not in commons %r"
                % (workspace_id, commons_id))
        return workspace

    def _create(self, table, prefix, fields, actor, audit_action):
        record = {"id": self._next_id(prefix)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        table[record["id"]] = record
        self._audit(actor, audit_action, record["id"])
        return copy.deepcopy(record)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    def _in_commons(self, table, commons_id):
        return [r for r in table.values() if r["commons_id"] == commons_id]

    def _check_unique_ref(self, table, commons_id, field, value, what):
        for existing in self._in_commons(table, commons_id):
            if existing[field] == value:
                raise ValidationError(
                    "%s %r is already recorded in this commons"
                    % (what, value))

    # -- Bioinformatics analysis pipeline engines (idx 581, built) ------
    # Records form: pipeline *definitions* held as data (engine
    # label and step references are names) bound to a core dataset
    # record and optionally to a core workspace record, plus
    # run-request records and run-outcome records whose counts are
    # stored exactly as reported. Nothing runs an analysis here:
    # ``executed_here`` is False on every shape, and recording an
    # outcome changes no core dataset record (pinned by test).

    def define_analysis_pipeline(self, actor, commons_id, dataset_id,
                                 pipeline_ref, engine_label, step_refs,
                                 workspace_id=None):
        """Define one bioinformatics analysis pipeline. Action: record."""
        self._guard(actor, "record", "add_pipeline_define")
        self._commons(actor, commons_id)
        self._dataset_in(actor, commons_id, dataset_id)
        if workspace_id is not None:
            self._workspace_in(actor, commons_id, workspace_id)
        _non_empty(pipeline_ref, "pipeline_ref")
        _non_empty(engine_label, "engine_label")
        steps = _ref_list(step_refs, "step_refs")
        with self._lock:
            self._check_unique_ref(self._pipeline_defs, commons_id,
                                   "pipeline_ref", pipeline_ref, "pipeline_ref")
            return self._create(
                self._pipeline_defs, "bpd-",
                {"commons_id": commons_id, "dataset_id": dataset_id,
                 "workspace_id": workspace_id, "pipeline_ref": pipeline_ref,
                 "engine_label": engine_label, "step_refs": steps,
                 "executed_here": False, "data_held_here": False},
                actor, "add_pipeline_define")

    def get_analysis_pipeline(self, actor, pipeline_id):
        """Return one pipeline definition. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._pipeline_defs, pipeline_id, "pipeline")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def pipeline_view(self, actor, pipeline_id):
        """A pipeline definition plus its derived step count.

        Action: read. The count is derived at read; the stored
        record carries no count key."""
        record = self.get_analysis_pipeline(actor, pipeline_id)
        record["step_count"] = len(record["step_refs"])
        record["derived"] = True
        return record

    def list_analysis_pipelines(self, actor, commons_id):
        """List pipeline definitions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._pipeline_defs, commons_id)))

    def request_pipeline_run(self, actor, pipeline_id, request_ref, purpose):
        """Record one pipeline run request. Action: record.

        The request names a pipeline definition; it is a record
        only — no analysis is started by this build."""
        self._guard(actor, "record", "add_pipeline_run_request")
        pipeline = self._get(self._pipeline_defs, pipeline_id, "pipeline")
        self._commons(actor, pipeline["commons_id"])
        _non_empty(request_ref, "request_ref")
        _non_empty(purpose, "purpose")
        with self._lock:
            self._check_unique_ref(
                self._pipeline_run_requests, pipeline["commons_id"],
                "request_ref", request_ref, "request_ref")
            return self._create(
                self._pipeline_run_requests, "bpr-",
                {"commons_id": pipeline["commons_id"],
                 "pipeline_id": pipeline_id, "request_ref": request_ref,
                 "purpose": purpose, "executed_here": False},
                actor, "add_pipeline_run_request")

    def get_pipeline_run_request(self, actor, request_id):
        """Return one pipeline run request. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._pipeline_run_requests, request_id,
                           "pipeline run request")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_pipeline_run_requests(self, actor, pipeline_id):
        """List run requests of one pipeline. Action: read."""
        self._maybe_require(actor, "read")
        pipeline = self._get(self._pipeline_defs, pipeline_id, "pipeline")
        self._check_commons_of(actor, pipeline)
        requests = [r for r in self._pipeline_run_requests.values()
                    if r["pipeline_id"] == pipeline_id]
        return copy.deepcopy(self._sorted(requests))

    def record_pipeline_run_outcome(self, actor, run_request_id,
                                    outcome_label, records_reported,
                                    source_label):
        """Record one reported pipeline run outcome. Action: record.

        The outcome and its counts are stored exactly as reported
        by the external pipeline engine; nothing was executed
        here."""
        self._guard(actor, "record", "add_pipeline_run_outcome")
        request = self._get(self._pipeline_run_requests, run_request_id,
                            "pipeline run request")
        self._commons(actor, request["commons_id"])
        if outcome_label not in PIPELINE_RUN_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(PIPELINE_RUN_OUTCOMES),))
        _count(records_reported, "records_reported")
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._pipeline_run_outcomes, "bpo-",
                {"commons_id": request["commons_id"],
                 "run_request_id": run_request_id,
                 "outcome_label": outcome_label,
                 "records_reported": records_reported,
                 "source_label": source_label, "executed_here": False},
                actor, "add_pipeline_run_outcome")

    def list_pipeline_run_outcomes(self, actor, run_request_id):
        """List reported outcomes of one run request. Action: read."""
        self._maybe_require(actor, "read")
        request = self._get(self._pipeline_run_requests, run_request_id,
                            "pipeline run request")
        self._check_commons_of(actor, request)
        outcomes = [o for o in self._pipeline_run_outcomes.values()
                    if o["run_request_id"] == run_request_id]
        return copy.deepcopy(self._sorted(outcomes))

    def pipeline_summary(self, actor, commons_id):
        """Deterministic counts over the held pipeline records.

        Action: read. Method ``deterministic_counts`` — definition,
        request, and outcome counts plus the total of reported
        record counts; nothing is executed or ranked."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        definitions = self._in_commons(self._pipeline_defs, commons_id)
        requests = self._in_commons(self._pipeline_run_requests, commons_id)
        outcomes = self._in_commons(self._pipeline_run_outcomes, commons_id)
        by_outcome = {}
        for outcome in outcomes:
            by_outcome[outcome["outcome_label"]] = \
                by_outcome.get(outcome["outcome_label"], 0) + 1
        return {"commons_id": commons_id,
                "pipelines": len(definitions),
                "run_requests": len(requests),
                "run_outcomes": len(outcomes),
                "outcomes_by_label": by_outcome,
                "records_reported_total":
                    sum(o["records_reported"] for o in outcomes),
                "method": "deterministic_counts", "executed_here": False}

    # -- Elastic storage & compute allocation engine (idx 584, built) ---
    # Records form: allocation *request* records (resource label
    # and a positive integer amount, held as recorded) plus
    # reported allocation outcome records. No scheduler runs here:
    # ``allocated_here`` is False on both shapes, and the summary's
    # totals are sums of the recorded values only.

    def request_allocation(self, actor, commons_id, allocation_ref,
                           resource_label, units_requested, purpose,
                           workspace_id=None):
        """Record one elastic allocation request. Action: record."""
        self._guard(actor, "record", "add_allocation_request")
        self._commons(actor, commons_id)
        if workspace_id is not None:
            self._workspace_in(actor, commons_id, workspace_id)
        _non_empty(allocation_ref, "allocation_ref")
        _non_empty(resource_label, "resource_label")
        _positive(units_requested, "units_requested")
        _non_empty(purpose, "purpose")
        with self._lock:
            self._check_unique_ref(self._allocation_requests, commons_id,
                                   "allocation_ref", allocation_ref,
                                   "allocation_ref")
            return self._create(
                self._allocation_requests, "alr-",
                {"commons_id": commons_id, "workspace_id": workspace_id,
                 "allocation_ref": allocation_ref,
                 "resource_label": resource_label,
                 "units_requested": units_requested, "purpose": purpose,
                 "allocated_here": False},
                actor, "add_allocation_request")

    def get_allocation_request(self, actor, request_id):
        """Return one allocation request. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._allocation_requests, request_id,
                           "allocation request")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_allocation_requests(self, actor, commons_id):
        """List allocation requests in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._allocation_requests,
                                           commons_id)))

    def record_allocation_outcome(self, actor, allocation_request_id,
                                  outcome_label, units_reported,
                                  source_label):
        """Record one reported allocation outcome. Action: record.

        The outcome and its amount are stored exactly as reported
        by the external allocation service; nothing was allocated
        by this build."""
        self._guard(actor, "record", "add_allocation_outcome")
        request = self._get(self._allocation_requests, allocation_request_id,
                            "allocation request")
        self._commons(actor, request["commons_id"])
        if outcome_label not in ALLOCATION_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(ALLOCATION_OUTCOMES),))
        _count(units_reported, "units_reported")
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._allocation_outcomes, "alo-",
                {"commons_id": request["commons_id"],
                 "allocation_request_id": allocation_request_id,
                 "outcome_label": outcome_label,
                 "units_reported": units_reported,
                 "source_label": source_label, "allocated_here": False},
                actor, "add_allocation_outcome")

    def list_allocation_outcomes(self, actor, allocation_request_id):
        """List reported outcomes of one allocation request. Action: read."""
        self._maybe_require(actor, "read")
        request = self._get(self._allocation_requests, allocation_request_id,
                            "allocation request")
        self._check_commons_of(actor, request)
        outcomes = [o for o in self._allocation_outcomes.values()
                    if o["allocation_request_id"] == allocation_request_id]
        return copy.deepcopy(self._sorted(outcomes))

    def allocation_summary(self, actor, commons_id):
        """Deterministic counts and recorded-value totals.

        Action: read. Method ``deterministic_counts`` — the totals
        are sums of recorded requested units and recorded reported
        units only; no allocation is computed or scheduled."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        requests = self._in_commons(self._allocation_requests, commons_id)
        outcomes = self._in_commons(self._allocation_outcomes, commons_id)
        by_outcome = {}
        for outcome in outcomes:
            by_outcome[outcome["outcome_label"]] = \
                by_outcome.get(outcome["outcome_label"], 0) + 1
        return {"commons_id": commons_id,
                "requests": len(requests), "outcomes": len(outcomes),
                "outcomes_by_label": by_outcome,
                "units_requested_total":
                    sum(r["units_requested"] for r in requests),
                "units_reported_total":
                    sum(o["units_reported"] for o in outcomes),
                "method": "deterministic_counts", "allocated_here": False}

    # -- AI analytics engine over LLMs (idx 586, built) -----------------
    # Records form: analysis *request* records (a task label held
    # as a name and an opaque input reference) plus result records
    # that hold the result as an opaque reference only. No
    # inference runs here (``inference_here`` False on both
    # shapes), and no shape has a field in which result text could
    # be placed -- a ``result_text`` keyword raises TypeError.

    def request_analysis(self, actor, commons_id, request_ref, task_label,
                         input_ref, dataset_id=None):
        """Record one AI analytics request. Action: record."""
        self._guard(actor, "record", "add_analysis_request")
        self._commons(actor, commons_id)
        if dataset_id is not None:
            self._dataset_in(actor, commons_id, dataset_id)
        _non_empty(request_ref, "request_ref")
        _non_empty(task_label, "task_label")
        _non_empty(input_ref, "input_ref")
        with self._lock:
            self._check_unique_ref(self._analysis_requests, commons_id,
                                   "request_ref", request_ref, "request_ref")
            return self._create(
                self._analysis_requests, "anr-",
                {"commons_id": commons_id, "dataset_id": dataset_id,
                 "request_ref": request_ref, "task_label": task_label,
                 "input_ref": input_ref, "inference_here": False},
                actor, "add_analysis_request")

    def get_analysis_request(self, actor, request_id):
        """Return one analysis request. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._analysis_requests, request_id,
                           "analysis request")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_analysis_requests(self, actor, commons_id):
        """List analysis requests in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._analysis_requests, commons_id)))

    def record_analysis_result(self, actor, analysis_request_id, result_ref,
                               source_label):
        """Record one analysis result as an opaque reference.

        Action: record. The result itself lives with the external
        analytics engine; this record names it by reference only,
        and no result text is accepted or held here."""
        self._guard(actor, "record", "add_analysis_result")
        request = self._get(self._analysis_requests, analysis_request_id,
                            "analysis request")
        self._commons(actor, request["commons_id"])
        _non_empty(result_ref, "result_ref")
        _non_empty(source_label, "source_label")
        with self._lock:
            self._check_unique_ref(self._analysis_results,
                                   request["commons_id"],
                                   "result_ref", result_ref, "result_ref")
            return self._create(
                self._analysis_results, "anx-",
                {"commons_id": request["commons_id"],
                 "analysis_request_id": analysis_request_id,
                 "result_ref": result_ref, "source_label": source_label,
                 "inference_here": False},
                actor, "add_analysis_result")

    def list_analysis_results(self, actor, analysis_request_id):
        """List result references of one analysis request. Action: read."""
        self._maybe_require(actor, "read")
        request = self._get(self._analysis_requests, analysis_request_id,
                            "analysis request")
        self._check_commons_of(actor, request)
        results = [r for r in self._analysis_results.values()
                   if r["analysis_request_id"] == analysis_request_id]
        return copy.deepcopy(self._sorted(results))

    def analysis_summary(self, actor, commons_id):
        """Deterministic counts over the held analysis records.

        Action: read. Method ``deterministic_counts``."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        requests = self._in_commons(self._analysis_requests, commons_id)
        results = self._in_commons(self._analysis_results, commons_id)
        return {"commons_id": commons_id,
                "requests": len(requests), "results": len(results),
                "method": "deterministic_counts", "inference_here": False}

    # -- Technology transfer & IP management suite (idx 587, built) -----
    # Records form: invention *disclosure* records and *agreement*
    # records held as metadata (counterparty and terms are opaque
    # references / labels, never terms text), plus append-only
    # agreement state records holding reported labels. Negotiated
    # or executed terms are reported outcomes recorded verbatim:
    # ``executed_here`` is False on every shape. An agreement's
    # current state is DERIVED at read by the single seam
    # ``_current_agreement_label`` and never stored -- the stored
    # agreement record carries no state key.

    def record_disclosure(self, actor, commons_id, disclosure_ref,
                          title_label, holder_ref):
        """Record one invention disclosure. Action: record."""
        self._guard(actor, "record", "add_disclosure_record")
        self._commons(actor, commons_id)
        _non_empty(disclosure_ref, "disclosure_ref")
        _non_empty(title_label, "title_label")
        _non_empty(holder_ref, "holder_ref")
        with self._lock:
            self._check_unique_ref(self._disclosures, commons_id,
                                   "disclosure_ref", disclosure_ref,
                                   "disclosure_ref")
            return self._create(
                self._disclosures, "dsc-",
                {"commons_id": commons_id, "disclosure_ref": disclosure_ref,
                 "title_label": title_label, "holder_ref": holder_ref,
                 "executed_here": False},
                actor, "add_disclosure_record")

    def get_disclosure(self, actor, disclosure_id):
        """Return one disclosure record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._disclosures, disclosure_id, "disclosure")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_disclosures(self, actor, commons_id):
        """List disclosures in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._disclosures, commons_id)))

    def record_agreement(self, actor, commons_id, agreement_ref,
                         counterparty_ref, terms_label, disclosure_id=None):
        """Record one license / agreement record. Action: record.

        The agreement is metadata only: the counterparty is an
        opaque reference and the terms are a label naming an
        external terms record; no terms text is held here."""
        self._guard(actor, "record", "add_agreement_record")
        self._commons(actor, commons_id)
        if disclosure_id is not None:
            disclosure = self._get(self._disclosures, disclosure_id,
                                   "disclosure")
            if disclosure["commons_id"] != commons_id:
                raise ValidationError(
                    "disclosure %r is not in commons %r"
                    % (disclosure_id, commons_id))
        _non_empty(agreement_ref, "agreement_ref")
        _non_empty(counterparty_ref, "counterparty_ref")
        _non_empty(terms_label, "terms_label")
        with self._lock:
            self._check_unique_ref(self._agreements, commons_id,
                                   "agreement_ref", agreement_ref,
                                   "agreement_ref")
            return self._create(
                self._agreements, "agr-",
                {"commons_id": commons_id, "disclosure_id": disclosure_id,
                 "agreement_ref": agreement_ref,
                 "counterparty_ref": counterparty_ref,
                 "terms_label": terms_label, "executed_here": False},
                actor, "add_agreement_record")

    def get_agreement(self, actor, agreement_id):
        """Return the stored agreement record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._agreements, agreement_id, "agreement")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_agreements(self, actor, commons_id):
        """List agreement records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._agreements, commons_id)))

    def _states_of(self, agreement_id):
        states = [s for s in self._agreement_states.values()
                  if s["agreement_id"] == agreement_id]
        return self._sorted(states)

    @staticmethod
    def _current_agreement_label(states):
        """The current agreement state: the LATEST recorded label.

        MUTATION DRILL NOTE: this seam
        (``ResearchAdditions._current_agreement_label``) is the
        single derivation point for an agreement's current state --
        the addition's fresh negative control mutates it to read
        the earliest recorded label, and the canonical expectations
        reject that outcome.
        """
        if not states:
            return None
        return states[-1]["state_label"]

    def agreement_view(self, actor, agreement_id):
        """An agreement record plus its derived current state.

        Action: read. The current state and the state-record count
        are derived at read; the stored record carries neither."""
        record = self.get_agreement(actor, agreement_id)
        states = self._states_of(agreement_id)
        record["current_state"] = self._current_agreement_label(states)
        record["state_record_count"] = len(states)
        record["derived"] = True
        return record

    def record_agreement_state(self, actor, agreement_id, state_label,
                               source_label):
        """Append one reported agreement state. Action: record.

        State records are append-only; the label is stored verbatim
        from the reported-* vocabulary. A ``reported_executed``
        label is a report that an agreement was executed by the
        external parties -- nothing is executed by this build."""
        self._guard(actor, "record", "add_agreement_state_record")
        agreement = self._get(self._agreements, agreement_id, "agreement")
        self._commons(actor, agreement["commons_id"])
        if state_label not in AGREEMENT_STATES:
            raise ValidationError(
                "state_label must be one of %s"
                % (", ".join(AGREEMENT_STATES),))
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._agreement_states, "ags-",
                {"commons_id": agreement["commons_id"],
                 "agreement_id": agreement_id, "state_label": state_label,
                 "source_label": source_label, "executed_here": False},
                actor, "add_agreement_state_record")

    def list_agreement_states(self, actor, agreement_id):
        """List the recorded states of one agreement. Action: read."""
        self._maybe_require(actor, "read")
        agreement = self._get(self._agreements, agreement_id, "agreement")
        self._check_commons_of(actor, agreement)
        return copy.deepcopy(self._states_of(agreement_id))

    def tech_transfer_summary(self, actor, commons_id):
        """Deterministic counts over the held tech-transfer records.

        Action: read. Method ``deterministic_counts`` — agreements
        are also recounted by their derived current state."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        disclosures = self._in_commons(self._disclosures, commons_id)
        agreements = self._in_commons(self._agreements, commons_id)
        states = self._in_commons(self._agreement_states, commons_id)
        by_current_state = {}
        for agreement in agreements:
            label = self._current_agreement_label(
                self._states_of(agreement["id"]))
            by_current_state[label] = by_current_state.get(label, 0) + 1
        return {"commons_id": commons_id,
                "disclosures": len(disclosures),
                "agreements": len(agreements),
                "agreement_states": len(states),
                "agreements_by_current_state": by_current_state,
                "method": "deterministic_counts", "executed_here": False}

    # -- Interactive analysis environment & workflow execution (idx 580,
    #    reference) ------------------------------------------------------
    # Labeled reference implementation: an environment *definition*
    # record names an external interactive environment and its tool
    # references, held as data. Nothing is provisioned and no
    # workflow executes here (``provisioned_here`` and
    # ``executed_here`` False on every record); session records
    # hold outcomes verbatim as reported.

    def record_environment(self, actor, commons_id, environment_ref,
                           tool_refs, workspace_id=None):
        """Record one interactive environment definition. Action: record."""
        self._guard(actor, "record", "add_environment_record")
        self._commons(actor, commons_id)
        if workspace_id is not None:
            self._workspace_in(actor, commons_id, workspace_id)
        _non_empty(environment_ref, "environment_ref")
        tools = _ref_list(tool_refs, "tool_refs", unique=True)
        with self._lock:
            self._check_unique_ref(self._environments, commons_id,
                                   "environment_ref", environment_ref,
                                   "environment_ref")
            return self._create(
                self._environments, "env-",
                {"commons_id": commons_id, "workspace_id": workspace_id,
                 "environment_ref": environment_ref, "tool_refs": tools,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "provisioned_here": False, "executed_here": False},
                actor, "add_environment_record")

    def get_environment(self, actor, environment_id):
        """Return one environment definition record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._environments, environment_id, "environment")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def environment_view(self, actor, environment_id):
        """An environment definition plus its derived tool count.

        Action: read. The count is derived at read; the stored
        record carries no count key."""
        record = self.get_environment(actor, environment_id)
        record["tool_count"] = len(record["tool_refs"])
        record["derived"] = True
        return record

    def list_environments(self, actor, commons_id):
        """List environment definitions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._environments, commons_id)))

    def record_environment_session(self, actor, environment_id,
                                   outcome_label, source_label):
        """Record one reported environment session outcome.

        Action: record. The outcome is stored verbatim as reported
        by the external environment; no session ran here."""
        self._guard(actor, "record", "add_environment_session_record")
        environment = self._get(self._environments, environment_id,
                                "environment")
        self._commons(actor, environment["commons_id"])
        if outcome_label not in ENVIRONMENT_SESSION_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(ENVIRONMENT_SESSION_OUTCOMES),))
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._environment_sessions, "esn-",
                {"commons_id": environment["commons_id"],
                 "environment_id": environment_id,
                 "outcome_label": outcome_label,
                 "source_label": source_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "provisioned_here": False,
                 "executed_here": False},
                actor, "add_environment_session_record")

    def list_environment_sessions(self, actor, environment_id):
        """List reported sessions of one environment. Action: read."""
        self._maybe_require(actor, "read")
        environment = self._get(self._environments, environment_id,
                                "environment")
        self._check_commons_of(actor, environment)
        sessions = [s for s in self._environment_sessions.values()
                    if s["environment_id"] == environment_id]
        return copy.deepcopy(self._sorted(sessions))

    # -- Diagnostic monitoring & variant surveillance incl. BioBank
    #    sample tracking (idx 582, reference) ---------------------------
    # Labeled reference implementation: sample *tracking* records
    # keyed by an opaque caller-supplied sample reference ONLY.
    # The health privacy discipline binds absolutely: no shape has
    # a field for a sample's subject, an identity, or a diagnosis
    # -- a ``diagnosis`` or ``subject_ref`` keyword raises
    # TypeError. Monitoring outcome records hold labels verbatim
    # as reported; nothing is monitored here (``monitored_here``
    # False on every record).

    def record_sample(self, actor, commons_id, sample_ref, panel_label):
        """Record one BioBank sample tracking record. Action: record."""
        self._guard(actor, "record", "add_sample_record")
        self._commons(actor, commons_id)
        _non_empty(sample_ref, "sample_ref")
        _non_empty(panel_label, "panel_label")
        with self._lock:
            self._check_unique_ref(self._samples, commons_id,
                                   "sample_ref", sample_ref, "sample_ref")
            return self._create(
                self._samples, "smp-",
                {"commons_id": commons_id, "sample_ref": sample_ref,
                 "panel_label": panel_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "monitored_here": False},
                actor, "add_sample_record")

    def get_sample(self, actor, sample_id):
        """Return one sample tracking record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._samples, sample_id, "sample")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_samples(self, actor, commons_id):
        """List sample tracking records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._samples, commons_id)))

    def record_monitor_outcome(self, actor, sample_id, outcome_label,
                               source_label):
        """Record one reported diagnostic monitoring outcome.

        Action: record. The outcome label is stored verbatim as
        reported by the external monitoring platform; nothing was
        monitored or diagnosed here."""
        self._guard(actor, "record", "add_monitor_outcome_record")
        sample = self._get(self._samples, sample_id, "sample")
        self._commons(actor, sample["commons_id"])
        if outcome_label not in MONITOR_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(MONITOR_OUTCOMES),))
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._monitor_outcomes, "mon-",
                {"commons_id": sample["commons_id"], "sample_id": sample_id,
                 "outcome_label": outcome_label,
                 "source_label": source_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "monitored_here": False},
                actor, "add_monitor_outcome_record")

    def list_monitor_outcomes(self, actor, sample_id):
        """List reported outcomes of one sample. Action: read."""
        self._maybe_require(actor, "read")
        sample = self._get(self._samples, sample_id, "sample")
        self._check_commons_of(actor, sample)
        outcomes = [o for o in self._monitor_outcomes.values()
                    if o["sample_id"] == sample_id]
        return copy.deepcopy(self._sorted(outcomes))

    def monitoring_summary(self, actor, commons_id):
        """Deterministic counts over the held monitoring records.

        Action: read. Method ``deterministic_counts``."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        samples = self._in_commons(self._samples, commons_id)
        outcomes = self._in_commons(self._monitor_outcomes, commons_id)
        by_outcome = {}
        for outcome in outcomes:
            by_outcome[outcome["outcome_label"]] = \
                by_outcome.get(outcome["outcome_label"], 0) + 1
        return {"commons_id": commons_id, "samples": len(samples),
                "outcomes": len(outcomes), "outcomes_by_label": by_outcome,
                "method": "deterministic_counts", "monitored_here": False}

    # -- Knowledge-graph storage & searchable library engine (idx 583,
    #    reference) ------------------------------------------------------
    # Labeled reference implementation: node and edge records are
    # metadata references only -- a node names an external resource
    # by an opaque reference, an edge names a relation label
    # between two recorded node references. No graph content is
    # held here (``data_held_here`` False) and nothing is
    # traversed or searched by a graph engine (``traversed_here``
    # False); the records form is the whole claim.

    def record_graph_node(self, actor, commons_id, node_ref, node_label,
                          resource_ref):
        """Record one knowledge-graph node reference. Action: record."""
        self._guard(actor, "record", "add_graph_node_record")
        self._commons(actor, commons_id)
        _non_empty(node_ref, "node_ref")
        _non_empty(node_label, "node_label")
        _non_empty(resource_ref, "resource_ref")
        with self._lock:
            self._check_unique_ref(self._graph_nodes, commons_id,
                                   "node_ref", node_ref, "node_ref")
            return self._create(
                self._graph_nodes, "gnd-",
                {"commons_id": commons_id, "node_ref": node_ref,
                 "node_label": node_label, "resource_ref": resource_ref,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "data_held_here": False, "traversed_here": False},
                actor, "add_graph_node_record")

    def get_graph_node(self, actor, node_id):
        """Return one graph node record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._graph_nodes, node_id, "graph node")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_graph_nodes(self, actor, commons_id):
        """List graph node records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._graph_nodes, commons_id)))

    def record_graph_edge(self, actor, commons_id, edge_ref, from_node_ref,
                          to_node_ref, relation_label):
        """Record one knowledge-graph edge reference. Action: record.

        Both endpoint references must name graph nodes already
        recorded in this commons; the edge is a metadata record,
        not a traversal."""
        self._guard(actor, "record", "add_graph_edge_record")
        self._commons(actor, commons_id)
        _non_empty(edge_ref, "edge_ref")
        _non_empty(relation_label, "relation_label")
        node_refs = {n["node_ref"]
                     for n in self._in_commons(self._graph_nodes, commons_id)}
        for endpoint in (from_node_ref, to_node_ref):
            _non_empty(endpoint, "node reference")
            if endpoint not in node_refs:
                raise ValidationError(
                    "graph node %r is not recorded in this commons"
                    % (endpoint,))
        with self._lock:
            self._check_unique_ref(self._graph_edges, commons_id,
                                   "edge_ref", edge_ref, "edge_ref")
            return self._create(
                self._graph_edges, "ged-",
                {"commons_id": commons_id, "edge_ref": edge_ref,
                 "from_node_ref": from_node_ref, "to_node_ref": to_node_ref,
                 "relation_label": relation_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "data_held_here": False,
                 "traversed_here": False},
                actor, "add_graph_edge_record")

    def list_graph_edges(self, actor, commons_id):
        """List graph edge records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._graph_edges, commons_id)))

    def graph_summary(self, actor, commons_id):
        """Deterministic counts over the held graph records.

        Action: read. Method ``deterministic_counts`` — counts of
        recorded node and edge references; nothing is traversed."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        nodes = self._in_commons(self._graph_nodes, commons_id)
        edges = self._in_commons(self._graph_edges, commons_id)
        return {"commons_id": commons_id, "nodes": len(nodes),
                "edges": len(edges), "method": "deterministic_counts",
                "traversed_here": False}

    # -- Multi-modal survey research platform (idx 585, reference) ------
    # Labeled reference implementation: survey *definition* records
    # (channel references held as names) plus response records
    # whose counts are stored exactly as reported. Nothing is
    # collected here (``collected_here`` False on both shapes) and
    # no shape holds a response payload or a respondent reference.

    def record_survey(self, actor, commons_id, survey_ref, channel_refs):
        """Record one survey definition. Action: record."""
        self._guard(actor, "record", "add_survey_record")
        self._commons(actor, commons_id)
        _non_empty(survey_ref, "survey_ref")
        channels = _ref_list(channel_refs, "channel_refs", unique=True)
        with self._lock:
            self._check_unique_ref(self._surveys, commons_id,
                                   "survey_ref", survey_ref, "survey_ref")
            return self._create(
                self._surveys, "srv-",
                {"commons_id": commons_id, "survey_ref": survey_ref,
                 "channel_refs": channels, "reference_stub": True,
                 "state": _REFERENCE_STATE, "collected_here": False},
                actor, "add_survey_record")

    def get_survey(self, actor, survey_id):
        """Return one survey definition. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._surveys, survey_id, "survey")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def survey_view(self, actor, survey_id):
        """A survey definition plus its derived channel count.

        Action: read. The count is derived at read; the stored
        record carries no count key."""
        record = self.get_survey(actor, survey_id)
        record["channel_count"] = len(record["channel_refs"])
        record["derived"] = True
        return record

    def list_surveys(self, actor, commons_id):
        """List survey definitions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._surveys, commons_id)))

    def record_survey_responses(self, actor, survey_id, responses_reported,
                                source_label):
        """Record one reported survey response count. Action: record.

        The count is stored exactly as reported by the external
        survey platform; no response was collected here."""
        self._guard(actor, "record", "add_survey_response_record")
        survey = self._get(self._surveys, survey_id, "survey")
        self._commons(actor, survey["commons_id"])
        _count(responses_reported, "responses_reported")
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._survey_responses, "srr-",
                {"commons_id": survey["commons_id"], "survey_id": survey_id,
                 "responses_reported": responses_reported,
                 "source_label": source_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "collected_here": False},
                actor, "add_survey_response_record")

    def list_survey_responses(self, actor, survey_id):
        """List reported response counts of one survey. Action: read."""
        self._maybe_require(actor, "read")
        survey = self._get(self._surveys, survey_id, "survey")
        self._check_commons_of(actor, survey)
        responses = [r for r in self._survey_responses.values()
                     if r["survey_id"] == survey_id]
        return copy.deepcopy(self._sorted(responses))

    def survey_summary(self, actor, commons_id):
        """Deterministic counts over the held survey records.

        Action: read. Method ``deterministic_counts`` — the total
        is the sum of reported response counts only."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        surveys = self._in_commons(self._surveys, commons_id)
        responses = self._in_commons(self._survey_responses, commons_id)
        return {"commons_id": commons_id, "surveys": len(surveys),
                "response_reports": len(responses),
                "responses_reported_total":
                    sum(r["responses_reported"] for r in responses),
                "method": "deterministic_counts", "collected_here": False}

    # -- Document generation & e-signature workflow engines + external
    #    integration components (idx 588, reference) --------------------
    # Labeled reference implementation: document-generation
    # *request* records naming a template reference and holding the
    # generated document as an opaque output reference only
    # (``generated_here`` False; no document content exists here),
    # signing *request* records in the house e-signature form
    # (``signed_here`` False; no shape has a field in which a
    # signature value could be placed -- a ``signature_value``
    # keyword raises TypeError), and external-integration
    # *reference* records naming a component the embedding
    # deployment connects elsewhere (``connected_here`` False).

    def request_document_generation(self, actor, commons_id, request_ref,
                                    template_ref, output_ref):
        """Record one document generation request. Action: record."""
        self._guard(actor, "record", "add_docgen_request")
        self._commons(actor, commons_id)
        _non_empty(request_ref, "request_ref")
        _non_empty(template_ref, "template_ref")
        _non_empty(output_ref, "output_ref")
        with self._lock:
            self._check_unique_ref(self._docgen_requests, commons_id,
                                   "request_ref", request_ref, "request_ref")
            return self._create(
                self._docgen_requests, "dgr-",
                {"commons_id": commons_id, "request_ref": request_ref,
                 "template_ref": template_ref, "output_ref": output_ref,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "generated_here": False},
                actor, "add_docgen_request")

    def get_docgen_request(self, actor, request_id):
        """Return one document generation request. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._docgen_requests, request_id,
                           "document generation request")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_docgen_requests(self, actor, commons_id):
        """List document generation requests in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._docgen_requests, commons_id)))

    def request_signing(self, actor, commons_id, request_ref, document_ref,
                        signer_ref):
        """Record one e-signature request. Action: record.

        The request names a document and a signer by opaque
        reference only; nothing is signed here and no signature
        value is accepted or held."""
        self._guard(actor, "record", "add_signing_request")
        self._commons(actor, commons_id)
        _non_empty(request_ref, "request_ref")
        _non_empty(document_ref, "document_ref")
        _non_empty(signer_ref, "signer_ref")
        with self._lock:
            self._check_unique_ref(self._signing_requests, commons_id,
                                   "request_ref", request_ref, "request_ref")
            return self._create(
                self._signing_requests, "sgr-",
                {"commons_id": commons_id, "request_ref": request_ref,
                 "document_ref": document_ref, "signer_ref": signer_ref,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "signed_here": False},
                actor, "add_signing_request")

    def get_signing_request(self, actor, request_id):
        """Return one signing request record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._signing_requests, request_id,
                           "signing request")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_signing_requests(self, actor, commons_id):
        """List signing requests in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._signing_requests, commons_id)))

    def record_integration_reference(self, actor, commons_id, component_ref,
                                     component_label):
        """Record one external integration component reference.

        Action: record. The record names the component the
        embedding deployment integrates elsewhere; nothing
        connects here."""
        self._guard(actor, "record", "add_integration_reference_record")
        self._commons(actor, commons_id)
        _non_empty(component_ref, "component_ref")
        _non_empty(component_label, "component_label")
        with self._lock:
            self._check_unique_ref(self._integration_references, commons_id,
                                   "component_ref", component_ref,
                                   "component_ref")
            return self._create(
                self._integration_references, "igr-",
                {"commons_id": commons_id, "component_ref": component_ref,
                 "component_label": component_label,
                 "reference_stub": True, "state": _REFERENCE_STATE,
                 "connected_here": False},
                actor, "add_integration_reference_record")

    def get_integration_reference(self, actor, reference_id):
        """Return one integration reference record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._integration_references, reference_id,
                           "integration reference")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_integration_references(self, actor, commons_id):
        """List integration references in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(self._sorted(
            self._in_commons(self._integration_references, commons_id)))

    def document_workflow_summary(self, actor, commons_id):
        """Deterministic counts over the held idx-588 records.

        Action: read. Method ``deterministic_counts``."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        docgen = self._in_commons(self._docgen_requests, commons_id)
        signing = self._in_commons(self._signing_requests, commons_id)
        integrations = self._in_commons(self._integration_references,
                                        commons_id)
        return {"commons_id": commons_id,
                "docgen_requests": len(docgen),
                "signing_requests": len(signing),
                "integration_references": len(integrations),
                "method": "deterministic_counts",
                "generated_here": False, "signed_here": False,
                "connected_here": False}
