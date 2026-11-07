"""Final GAPS batch extensions for Research L2 (Singleton 53).

Clean-room, standard-library-only extensions for the 10 open
entries of the "Singleton 53 — Research L2" section of GAPS.md
(see ``BATCH.md`` in the group directory for the per-entry
disposition). This module is a wrapper around
:class:`ResearchStore`; every core module is untouched and
byte-identical to the shipped build.

**The founding discipline binds absolutely, here as in the
core:** the commons is a registry of dataset records and counts,
and every entity shape in this module carries metadata and opaque
caller-supplied references only. No shape has a field for
research subject data, a dataset payload, a query text, a cohort
member, or a score — those fields **do not exist**. Methods
accept only their named parameters, so a caller cannot smuggle a
forbidden field into a record (pinned by tests: an unexpected
keyword raises ``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — definition and outcome records over the
group's OWN records (core records and extension records), plus
deterministic derivations at read:

- The commons runtime is a *configuration* record over a commons
  record; no runtime is started here.
- Ingestion / ETL is pipeline definitions held as data plus run
  records whose counts are stored exactly as reported; nothing is
  ingested, and a run changes no dataset record.
- Harmonization is mapping definitions (source/target field
  references held as names) plus verbatim reported conformance
  outcomes; nothing is harmonized here.
- Query / analysis is workspace-bound query *definitions* held as
  text-free structure (field references and operator names as
  data); no query ever executes here, and results are verbatim
  reported counts.
- Cohort building is cohort *definitions* (criteria references as
  data) with membership counts stored as reported; no member is
  ever computed or named here.
- Federation is peer-commons records plus exchange request /
  outcome records; nothing connects here, and exchange receipts
  carry ``reference_transport: True``.
- Data delivery is delivery records over dataset references with
  reported state labels whose current value is derived at read;
  no data moves here.
- Access enforcement on delivery is decision records plus a view
  that derives the linked core grant's status through the core
  store's own derivation. The founding line stands: **grants are
  records that confer nothing** — recording a grant or an
  enforcement decision changes no delivery state, and nothing
  here confers or enforces access to any data.
- Stub-engine entries ship as labeled reference implementations:
  every record carries ``reference_stub: True`` and state
  ``recorded_reference_only``. Indexing builds no index (the
  core registry's literal search stands unchanged), and the
  identity entry follows PLATFORM-LAYER.md decision 1: IA-2
  stays with the embedding organization; no build in this repo
  is an identity provider.

Doctrines carried from the core: derived-never-stored for every
computed value (definition field counts, delivery current state,
grant status in the enforcement view, all summaries);
append-only audit on the core store's log with ``ext_``-prefixed
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

RUN_STATES = (
    "reported_completed",
    "reported_partial",
    "reported_failed",
)
CONFORMANCE_OUTCOMES = (
    "reported_conformant",
    "reported_nonconformant",
    "reported_partial",
)
DELIVERY_STATES = (
    "reported_prepared",
    "reported_dispatched",
    "reported_received",
    "reported_failed",
)
EXCHANGE_OUTCOMES = (
    "reported_completed",
    "reported_refused",
    "reported_pending",
)
ENFORCEMENT_DECISIONS = (
    "reported_permitted",
    "reported_refused",
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


class ResearchExtensions:
    """Extension surface wrapping one :class:`ResearchStore`."""

    def __init__(self, store):
        self.store = store
        self._runtime_configs = {}
        self._pipelines = {}
        self._pipeline_runs = {}
        self._mappings = {}
        self._conformance_outcomes = {}
        self._index_references = {}
        self._queries = {}
        self._query_results = {}
        self._cohorts = {}
        self._cohort_memberships = {}
        self._peers = {}
        self._exchange_requests = {}
        self._exchange_outcomes = {}
        self._deliveries = {}
        self._delivery_states = {}
        self._enforcement_decisions = {}
        self._identity_references = {}
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

    # -- Data commons runtime engine (idx 521, built) -------------------
    # Records form: a runtime *configuration* record over a core
    # commons record -- profile label and parameter references held
    # as data. No runtime is started, configured, or operated here:
    # ``runtime_started_here`` is False on every record, and the
    # parameter count is derived at read, never stored.

    def record_runtime_config(self, actor, commons_id, config_ref,
                              profile_label, parameter_refs):
        """Record one commons runtime configuration. Action: record."""
        self._guard(actor, "record", "ext_runtime_config_record")
        self._commons(actor, commons_id)
        _non_empty(config_ref, "config_ref")
        _non_empty(profile_label, "profile_label")
        refs = _ref_list(parameter_refs, "parameter_refs", unique=True)
        with self._lock:
            for existing in self._in_commons(self._runtime_configs, commons_id):
                if existing["config_ref"] == config_ref:
                    raise ValidationError(
                        "config_ref %r is already recorded in this commons"
                        % (config_ref,))
            return self._create(
                self._runtime_configs, "rt-",
                {"commons_id": commons_id, "config_ref": config_ref,
                 "profile_label": profile_label, "parameter_refs": refs,
                 "runtime_started_here": False},
                actor, "ext_runtime_config_record")

    def get_runtime_config(self, actor, config_id):
        """Return one runtime configuration record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._runtime_configs, config_id,
                           "runtime configuration")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def runtime_config_view(self, actor, config_id):
        """A runtime configuration plus its derived parameter count.

        Action: read. The count is derived at read from the held
        reference list; the stored record carries no count key."""
        record = self.get_runtime_config(actor, config_id)
        record["parameter_count"] = len(record["parameter_refs"])
        record["derived"] = True
        return record

    def list_runtime_configs(self, actor, commons_id):
        """List runtime configurations in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._runtime_configs, commons_id)))

    # -- Data ingestion / ETL engine (idx 522, built) -------------------
    # Records form: pipeline *definitions* held as data (source
    # reference and transform-step references are names) bound to a
    # core dataset record, plus run records whose counts are stored
    # exactly as reported. Nothing is ingested or transformed
    # here: ``data_held_here`` is False on both shapes, and a run
    # record changes no dataset record (pinned by test).

    def define_pipeline(self, actor, commons_id, dataset_id, pipeline_ref,
                        source_ref, transform_step_refs):
        """Define one ingestion pipeline over a dataset. Action: record."""
        self._guard(actor, "record", "ext_pipeline_define")
        self._commons(actor, commons_id)
        self._dataset_in(actor, commons_id, dataset_id)
        _non_empty(pipeline_ref, "pipeline_ref")
        _non_empty(source_ref, "source_ref")
        steps = _ref_list(transform_step_refs, "transform_step_refs")
        with self._lock:
            for existing in self._in_commons(self._pipelines, commons_id):
                if existing["pipeline_ref"] == pipeline_ref:
                    raise ValidationError(
                        "pipeline_ref %r is already recorded in this commons"
                        % (pipeline_ref,))
            return self._create(
                self._pipelines, "pl-",
                {"commons_id": commons_id, "dataset_id": dataset_id,
                 "pipeline_ref": pipeline_ref, "source_ref": source_ref,
                 "transform_step_refs": steps, "data_held_here": False},
                actor, "ext_pipeline_define")

    def get_pipeline(self, actor, pipeline_id):
        """Return one pipeline definition. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._pipelines, pipeline_id, "pipeline")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_pipelines(self, actor, commons_id):
        """List pipeline definitions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._pipelines, commons_id)))

    def record_pipeline_run(self, actor, pipeline_id, state_label,
                            records_reported, source_label):
        """Record one reported pipeline run. Action: record.

        The run's counts are stored exactly as reported by the
        external engine; nothing was ingested by this build."""
        self._guard(actor, "record", "ext_pipeline_run_record")
        pipeline = self._get(self._pipelines, pipeline_id, "pipeline")
        self._commons(actor, pipeline["commons_id"])
        if state_label not in RUN_STATES:
            raise ValidationError(
                "state_label must be one of %s" % (", ".join(RUN_STATES),))
        _count(records_reported, "records_reported")
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._pipeline_runs, "run-",
                {"commons_id": pipeline["commons_id"],
                 "pipeline_id": pipeline_id, "state_label": state_label,
                 "records_reported": records_reported,
                 "source_label": source_label, "data_held_here": False,
                 "ingested_here": False},
                actor, "ext_pipeline_run_record")

    def list_pipeline_runs(self, actor, pipeline_id):
        """List reported runs of one pipeline. Action: read."""
        self._maybe_require(actor, "read")
        pipeline = self._get(self._pipelines, pipeline_id, "pipeline")
        self._check_commons_of(actor, pipeline)
        runs = [r for r in self._pipeline_runs.values()
                if r["pipeline_id"] == pipeline_id]
        return copy.deepcopy(self._sorted(runs))

    def ingestion_summary(self, actor, commons_id):
        """Deterministic counts over the held pipeline records.

        Action: read. Method ``deterministic_counts`` -- definition
        and run counts plus the total of reported record counts;
        nothing is ingested or ranked."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        pipelines = self._in_commons(self._pipelines, commons_id)
        runs = self._in_commons(self._pipeline_runs, commons_id)
        by_state = {}
        for run in runs:
            by_state[run["state_label"]] = by_state.get(run["state_label"], 0) + 1
        return {"commons_id": commons_id,
                "pipelines": len(pipelines), "runs": len(runs),
                "runs_by_state": by_state,
                "records_reported_total": sum(r["records_reported"] for r in runs),
                "method": "deterministic_counts", "ingested_here": False}

    # -- Data harmonization engine (idx 523, built) ---------------------
    # Records form: mapping *definitions* held as data -- source
    # and target field references are names, never values -- plus
    # conformance outcome records stored verbatim as reported.
    # Nothing is harmonized here: ``harmonized_here`` is False on
    # both shapes, and field counts are derived at read.

    def define_mapping(self, actor, commons_id, mapping_ref,
                       source_field_refs, target_field_refs):
        """Define one harmonization mapping. Action: record."""
        self._guard(actor, "record", "ext_mapping_define")
        self._commons(actor, commons_id)
        _non_empty(mapping_ref, "mapping_ref")
        sources = _ref_list(source_field_refs, "source_field_refs", unique=True)
        targets = _ref_list(target_field_refs, "target_field_refs", unique=True)
        with self._lock:
            for existing in self._in_commons(self._mappings, commons_id):
                if existing["mapping_ref"] == mapping_ref:
                    raise ValidationError(
                        "mapping_ref %r is already recorded in this commons"
                        % (mapping_ref,))
            return self._create(
                self._mappings, "map-",
                {"commons_id": commons_id, "mapping_ref": mapping_ref,
                 "source_field_refs": sources, "target_field_refs": targets,
                 "harmonized_here": False},
                actor, "ext_mapping_define")

    def get_mapping(self, actor, mapping_id):
        """Return one mapping definition. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._mappings, mapping_id, "mapping")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def mapping_view(self, actor, mapping_id):
        """A mapping plus its derived field-reference counts.

        Action: read. The counts are derived at read; the stored
        record carries no count key."""
        record = self.get_mapping(actor, mapping_id)
        record["source_field_count"] = len(record["source_field_refs"])
        record["target_field_count"] = len(record["target_field_refs"])
        record["derived"] = True
        return record

    def list_mappings(self, actor, commons_id):
        """List mapping definitions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._mappings, commons_id)))

    def record_conformance_outcome(self, actor, mapping_id, outcome_label,
                                   fields_reported, source_label):
        """Record one reported conformance outcome. Action: record.

        The outcome is stored verbatim as reported by the external
        harmonization process; nothing was harmonized here."""
        self._guard(actor, "record", "ext_conformance_record")
        mapping = self._get(self._mappings, mapping_id, "mapping")
        self._commons(actor, mapping["commons_id"])
        if outcome_label not in CONFORMANCE_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(CONFORMANCE_OUTCOMES),))
        _count(fields_reported, "fields_reported")
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._conformance_outcomes, "cfm-",
                {"commons_id": mapping["commons_id"],
                 "mapping_id": mapping_id, "outcome_label": outcome_label,
                 "fields_reported": fields_reported,
                 "source_label": source_label, "harmonized_here": False},
                actor, "ext_conformance_record")

    def list_conformance_outcomes(self, actor, mapping_id):
        """List reported outcomes of one mapping. Action: read."""
        self._maybe_require(actor, "read")
        mapping = self._get(self._mappings, mapping_id, "mapping")
        self._check_commons_of(actor, mapping)
        outcomes = [o for o in self._conformance_outcomes.values()
                    if o["mapping_id"] == mapping_id]
        return copy.deepcopy(self._sorted(outcomes))

    def harmonization_summary(self, actor, commons_id):
        """Deterministic counts over the held mapping records.

        Action: read. Method ``deterministic_counts``."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        mappings = self._in_commons(self._mappings, commons_id)
        outcomes = self._in_commons(self._conformance_outcomes, commons_id)
        by_outcome = {}
        for outcome in outcomes:
            by_outcome[outcome["outcome_label"]] = \
                by_outcome.get(outcome["outcome_label"], 0) + 1
        return {"commons_id": commons_id,
                "mappings": len(mappings), "outcomes": len(outcomes),
                "outcomes_by_label": by_outcome,
                "fields_reported_total": sum(o["fields_reported"] for o in outcomes),
                "method": "deterministic_counts", "harmonized_here": False}

    # -- Indexing & metadata catalog engines (idx 524, reference) -------
    # Labeled reference implementation: an index *reference* record
    # names an external index and its scope. No index is built
    # here (``index_built_here`` False), and the core registry's
    # own literal substring search stands unchanged -- recording a
    # reference changes no search result (pinned by test).

    def record_index_reference(self, actor, commons_id, index_ref, scope_label):
        """Record one external index reference. Action: record."""
        self._guard(actor, "record", "ext_index_reference_record")
        self._commons(actor, commons_id)
        _non_empty(index_ref, "index_ref")
        _non_empty(scope_label, "scope_label")
        with self._lock:
            for existing in self._in_commons(self._index_references, commons_id):
                if existing["index_ref"] == index_ref:
                    raise ValidationError(
                        "index_ref %r is already recorded in this commons"
                        % (index_ref,))
            return self._create(
                self._index_references, "idx-",
                {"commons_id": commons_id, "index_ref": index_ref,
                 "scope_label": scope_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "index_built_here": False},
                actor, "ext_index_reference_record")

    def get_index_reference(self, actor, reference_id):
        """Return one index reference record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._index_references, reference_id,
                           "index reference")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_index_references(self, actor, commons_id):
        """List index references in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._index_references, commons_id)))


    # -- Query & analysis workspace engines (idx 525, built) ------------
    # Records form: query *definitions* bound to a core workspace
    # record, held as text-free structure -- field references and
    # operator names as data. No parameter accepts query text, and
    # no query ever executes here (``executed_here`` False on both
    # shapes); result records hold counts exactly as reported.

    def define_query(self, actor, commons_id, workspace_id, query_ref,
                     field_refs, operator_names):
        """Define one query over a workspace. Action: record."""
        self._guard(actor, "record", "ext_query_define")
        self._commons(actor, commons_id)
        workspace = self.store.get_workspace(actor, workspace_id)
        if workspace["commons_id"] != commons_id:
            raise ValidationError(
                "workspace %r is not in commons %r" % (workspace_id, commons_id))
        _non_empty(query_ref, "query_ref")
        fields = _ref_list(field_refs, "field_refs", unique=True)
        operators = _ref_list(operator_names, "operator_names")
        with self._lock:
            for existing in self._in_commons(self._queries, commons_id):
                if existing["query_ref"] == query_ref:
                    raise ValidationError(
                        "query_ref %r is already recorded in this commons"
                        % (query_ref,))
            return self._create(
                self._queries, "qry-",
                {"commons_id": commons_id, "workspace_id": workspace_id,
                 "query_ref": query_ref, "field_refs": fields,
                 "operator_names": operators, "executed_here": False},
                actor, "ext_query_define")

    def get_query(self, actor, query_id):
        """Return one query definition. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._queries, query_id, "query")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def query_view(self, actor, query_id):
        """A query definition plus its derived structure counts.

        Action: read. The counts are derived at read; the stored
        record carries no count key."""
        record = self.get_query(actor, query_id)
        record["field_ref_count"] = len(record["field_refs"])
        record["operator_count"] = len(record["operator_names"])
        record["derived"] = True
        return record

    def list_queries(self, actor, commons_id):
        """List query definitions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._queries, commons_id)))

    def record_query_result(self, actor, query_id, result_count_reported,
                            source_label):
        """Record one reported query result count. Action: record.

        The count is stored exactly as reported by the external
        analysis process; no query was executed or computed here."""
        self._guard(actor, "record", "ext_query_result_record")
        query = self._get(self._queries, query_id, "query")
        self._commons(actor, query["commons_id"])
        _count(result_count_reported, "result_count_reported")
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._query_results, "qrs-",
                {"commons_id": query["commons_id"], "query_id": query_id,
                 "result_count_reported": result_count_reported,
                 "source_label": source_label, "executed_here": False,
                 "computed_here": False},
                actor, "ext_query_result_record")

    def list_query_results(self, actor, query_id):
        """List reported results of one query. Action: read."""
        self._maybe_require(actor, "read")
        query = self._get(self._queries, query_id, "query")
        self._check_commons_of(actor, query)
        results = [r for r in self._query_results.values()
                   if r["query_id"] == query_id]
        return copy.deepcopy(self._sorted(results))

    # -- Cohort builder / cohort discovery engine (idx 526, built) ------
    # Records form: cohort *definitions* over a core dataset
    # record -- criteria references held as names (data) -- plus
    # membership records whose counts are stored exactly as
    # reported. No member is ever computed, discovered, or named
    # here (``members_computed_here`` False on both shapes), and
    # no shape has a field that could hold a subject reference.

    def define_cohort(self, actor, commons_id, dataset_id, cohort_ref,
                      criteria_refs):
        """Define one cohort over a dataset. Action: record."""
        self._guard(actor, "record", "ext_cohort_define")
        self._commons(actor, commons_id)
        self._dataset_in(actor, commons_id, dataset_id)
        _non_empty(cohort_ref, "cohort_ref")
        criteria = _ref_list(criteria_refs, "criteria_refs", unique=True)
        with self._lock:
            for existing in self._in_commons(self._cohorts, commons_id):
                if existing["cohort_ref"] == cohort_ref:
                    raise ValidationError(
                        "cohort_ref %r is already recorded in this commons"
                        % (cohort_ref,))
            return self._create(
                self._cohorts, "coh-",
                {"commons_id": commons_id, "dataset_id": dataset_id,
                 "cohort_ref": cohort_ref, "criteria_refs": criteria,
                 "members_computed_here": False},
                actor, "ext_cohort_define")

    def get_cohort(self, actor, cohort_id):
        """Return one cohort definition. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._cohorts, cohort_id, "cohort")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def cohort_view(self, actor, cohort_id):
        """A cohort definition plus its derived criteria count.

        Action: read. The count is derived at read; the stored
        record carries no count key."""
        record = self.get_cohort(actor, cohort_id)
        record["criteria_count"] = len(record["criteria_refs"])
        record["derived"] = True
        return record

    def list_cohorts(self, actor, commons_id):
        """List cohort definitions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._cohorts, commons_id)))

    def record_cohort_membership(self, actor, cohort_id, members_reported,
                                 source_label):
        """Record one reported cohort membership count. Action: record.

        The count is stored exactly as reported by the external
        cohort process; no member was computed or named here."""
        self._guard(actor, "record", "ext_cohort_membership_record")
        cohort = self._get(self._cohorts, cohort_id, "cohort")
        self._commons(actor, cohort["commons_id"])
        _count(members_reported, "members_reported")
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._cohort_memberships, "cmr-",
                {"commons_id": cohort["commons_id"], "cohort_id": cohort_id,
                 "members_reported": members_reported,
                 "source_label": source_label,
                 "members_computed_here": False},
                actor, "ext_cohort_membership_record")

    def list_cohort_memberships(self, actor, cohort_id):
        """List reported membership counts of one cohort. Action: read."""
        self._maybe_require(actor, "read")
        cohort = self._get(self._cohorts, cohort_id, "cohort")
        self._check_commons_of(actor, cohort)
        records = [r for r in self._cohort_memberships.values()
                   if r["cohort_id"] == cohort_id]
        return copy.deepcopy(self._sorted(records))

    def cohort_summary(self, actor, commons_id):
        """Deterministic counts over the held cohort records.

        Action: read. Method ``deterministic_counts`` -- definition
        and report counts plus the total of reported member
        counts; no membership is computed."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        cohorts = self._in_commons(self._cohorts, commons_id)
        reports = self._in_commons(self._cohort_memberships, commons_id)
        return {"commons_id": commons_id,
                "cohorts": len(cohorts), "membership_reports": len(reports),
                "members_reported_total": sum(r["members_reported"] for r in reports),
                "method": "deterministic_counts",
                "members_computed_here": False}

    # -- Cross-commons federation / data mesh networking (idx 527, built)
    # Records form: peer-commons records (an opaque peer reference
    # and a label) plus exchange request and outcome records over
    # core dataset references. Nothing connects, meshes, or moves
    # here: ``connected_here`` is False on every shape, outcomes
    # are stored verbatim as reported, and transport-shaped
    # receipts carry ``reference_transport: True``.

    def record_peer_commons(self, actor, commons_id, peer_ref, peer_label):
        """Record one peer commons reference. Action: record."""
        self._guard(actor, "record", "ext_peer_record")
        self._commons(actor, commons_id)
        _non_empty(peer_ref, "peer_ref")
        _non_empty(peer_label, "peer_label")
        with self._lock:
            for existing in self._in_commons(self._peers, commons_id):
                if existing["peer_ref"] == peer_ref:
                    raise ValidationError(
                        "peer_ref %r is already recorded in this commons"
                        % (peer_ref,))
            return self._create(
                self._peers, "per-",
                {"commons_id": commons_id, "peer_ref": peer_ref,
                 "peer_label": peer_label, "connected_here": False},
                actor, "ext_peer_record")

    def get_peer_commons(self, actor, peer_id):
        """Return one peer commons record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._peers, peer_id, "peer commons")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_peer_commons(self, actor, commons_id):
        """List peer commons records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._peers, commons_id)))

    def record_exchange_request(self, actor, peer_id, dataset_id, purpose):
        """Record one federation exchange request. Action: record.

        The request names a core dataset in the peer record's
        commons; it is a record only — nothing is sent."""
        self._guard(actor, "record", "ext_exchange_request_record")
        peer = self._get(self._peers, peer_id, "peer commons")
        self._commons(actor, peer["commons_id"])
        self._dataset_in(actor, peer["commons_id"], dataset_id)
        _non_empty(purpose, "purpose")
        with self._lock:
            return self._create(
                self._exchange_requests, "exr-",
                {"commons_id": peer["commons_id"], "peer_id": peer_id,
                 "dataset_id": dataset_id, "purpose": purpose,
                 "connected_here": False, "reference_transport": True},
                actor, "ext_exchange_request_record")

    def get_exchange_request(self, actor, request_id):
        """Return one exchange request record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._exchange_requests, request_id,
                           "exchange request")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_exchange_requests(self, actor, commons_id):
        """List exchange requests in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._exchange_requests, commons_id)))

    def record_exchange_outcome(self, actor, exchange_request_id,
                                outcome_label, source_label):
        """Record one reported exchange outcome. Action: record.

        The outcome is stored verbatim as reported; no data moved
        and nothing connected here."""
        self._guard(actor, "record", "ext_exchange_outcome_record")
        request = self._get(self._exchange_requests, exchange_request_id,
                            "exchange request")
        self._commons(actor, request["commons_id"])
        if outcome_label not in EXCHANGE_OUTCOMES:
            raise ValidationError(
                "outcome_label must be one of %s"
                % (", ".join(EXCHANGE_OUTCOMES),))
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._exchange_outcomes, "exo-",
                {"commons_id": request["commons_id"],
                 "exchange_request_id": exchange_request_id,
                 "outcome_label": outcome_label,
                 "source_label": source_label, "connected_here": False,
                 "data_moved_here": False, "reference_transport": True},
                actor, "ext_exchange_outcome_record")

    def list_exchange_outcomes(self, actor, exchange_request_id):
        """List reported outcomes of one exchange request. Action: read."""
        self._maybe_require(actor, "read")
        request = self._get(self._exchange_requests, exchange_request_id,
                            "exchange request")
        self._check_commons_of(actor, request)
        outcomes = [o for o in self._exchange_outcomes.values()
                    if o["exchange_request_id"] == exchange_request_id]
        return copy.deepcopy(self._sorted(outcomes))

    def federation_summary(self, actor, commons_id):
        """Deterministic counts over the held federation records.

        Action: read. Method ``deterministic_counts``."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        peers = self._in_commons(self._peers, commons_id)
        requests = self._in_commons(self._exchange_requests, commons_id)
        outcomes = self._in_commons(self._exchange_outcomes, commons_id)
        by_outcome = {}
        for outcome in outcomes:
            by_outcome[outcome["outcome_label"]] = \
                by_outcome.get(outcome["outcome_label"], 0) + 1
        return {"commons_id": commons_id, "peers": len(peers),
                "exchange_requests": len(requests),
                "exchange_outcomes": len(outcomes),
                "outcomes_by_label": by_outcome,
                "method": "deterministic_counts", "connected_here": False}

    # -- Data delivery / transfer engine (idx 528, built) ---------------
    # Records form: delivery records over core dataset references
    # (with an optional core grant reference), plus append-only
    # delivery state records holding reported labels. The current
    # state is DERIVED at read by the single seam
    # ``_current_delivery_label`` and never stored -- the stored
    # delivery record carries no state key. No data moves here:
    # ``data_moved_here`` is False on both shapes.

    def record_delivery(self, actor, commons_id, dataset_id, recipient_ref,
                        grant_id=None):
        """Record one data delivery. Action: record.

        ``recipient_ref`` is an opaque reference (for example a
        core organization reference). When ``grant_id`` is given
        it must name a core grant for the same dataset in the
        same commons; the linkage is recorded, and confers
        nothing."""
        self._guard(actor, "record", "ext_delivery_record")
        self._commons(actor, commons_id)
        self._dataset_in(actor, commons_id, dataset_id)
        _non_empty(recipient_ref, "recipient_ref")
        if grant_id is not None:
            grant = self.store.get_grant(actor, grant_id)
            if grant["dataset_id"] != dataset_id \
                    or grant["commons_id"] != commons_id:
                raise ValidationError(
                    "grant %r is not a grant for dataset %r in this commons"
                    % (grant_id, dataset_id))
        with self._lock:
            return self._create(
                self._deliveries, "dlv-",
                {"commons_id": commons_id, "dataset_id": dataset_id,
                 "grant_id": grant_id, "recipient_ref": recipient_ref,
                 "data_moved_here": False},
                actor, "ext_delivery_record")

    def get_delivery(self, actor, delivery_id):
        """Return the stored delivery record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._deliveries, delivery_id, "delivery")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def _states_of(self, delivery_id):
        states = [s for s in self._delivery_states.values()
                  if s["delivery_id"] == delivery_id]
        return self._sorted(states)

    @staticmethod
    def _current_delivery_label(states):
        """The current delivery state: the LATEST recorded label.

        MUTATION DRILL NOTE: this seam
        (``ResearchExtensions._current_delivery_label``) is the
        single derivation point for a delivery's current state --
        the batch's fresh negative control mutates it to read the
        earliest recorded label, and the canonical expectations
        reject that outcome.
        """
        if not states:
            return None
        return states[-1]["state_label"]

    def delivery_view(self, actor, delivery_id):
        """A delivery record plus its derived current state.

        Action: read. The current state and the state-record count
        are derived at read; the stored record carries neither."""
        record = self.get_delivery(actor, delivery_id)
        states = self._states_of(delivery_id)
        record["current_state"] = self._current_delivery_label(states)
        record["state_record_count"] = len(states)
        record["derived"] = True
        return record

    def list_deliveries(self, actor, commons_id):
        """List delivery records in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(
            self._sorted(self._in_commons(self._deliveries, commons_id)))

    def record_delivery_state(self, actor, delivery_id, state_label):
        """Append one reported delivery state. Action: record.

        State records are append-only; the label is stored
        verbatim from the reported-* vocabulary, and recording a
        state moves no data."""
        self._guard(actor, "record", "ext_delivery_state_record")
        delivery = self._get(self._deliveries, delivery_id, "delivery")
        self._commons(actor, delivery["commons_id"])
        if state_label not in DELIVERY_STATES:
            raise ValidationError(
                "state_label must be one of %s" % (", ".join(DELIVERY_STATES),))
        with self._lock:
            return self._create(
                self._delivery_states, "dls-",
                {"commons_id": delivery["commons_id"],
                 "delivery_id": delivery_id, "state_label": state_label,
                 "data_moved_here": False},
                actor, "ext_delivery_state_record")

    def list_delivery_states(self, actor, delivery_id):
        """List the recorded states of one delivery. Action: read."""
        self._maybe_require(actor, "read")
        delivery = self._get(self._deliveries, delivery_id, "delivery")
        self._check_commons_of(actor, delivery)
        return copy.deepcopy(self._states_of(delivery_id))

    # -- Access enforcement on data delivery (idx 529, built) -----------
    # Records form: enforcement *decision* records over a delivery
    # record, plus a view deriving the linked core grant's status
    # through the core store's own derivation. The founding line
    # is intact and pinned by tests: grants are records that
    # confer nothing -- ``conferred_here`` and ``enforced_here``
    # are False on every record, recording a decision changes no
    # core grant record and no delivery state, and minting a core
    # grant changes no delivery record.

    def record_enforcement_decision(self, actor, delivery_id, decision_label,
                                    source_label):
        """Record one reported enforcement decision. Action: record.

        The decision is recorded as reported by the delivery
        layer's own enforcement point; this build confers and
        enforces nothing."""
        self._guard(actor, "record", "ext_enforcement_record")
        delivery = self._get(self._deliveries, delivery_id, "delivery")
        self._commons(actor, delivery["commons_id"])
        if decision_label not in ENFORCEMENT_DECISIONS:
            raise ValidationError(
                "decision_label must be one of %s"
                % (", ".join(ENFORCEMENT_DECISIONS),))
        _non_empty(source_label, "source_label")
        with self._lock:
            return self._create(
                self._enforcement_decisions, "enf-",
                {"commons_id": delivery["commons_id"],
                 "delivery_id": delivery_id,
                 "grant_id": delivery["grant_id"],
                 "decision_label": decision_label,
                 "source_label": source_label, "conferred_here": False,
                 "enforced_here": False},
                actor, "ext_enforcement_record")

    def get_enforcement_decision(self, actor, decision_id):
        """Return one enforcement decision record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._enforcement_decisions, decision_id,
                           "enforcement decision")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_enforcement_decisions(self, actor, commons_id):
        """List enforcement decisions in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(self._sorted(
            self._in_commons(self._enforcement_decisions, commons_id)))

    def delivery_access_view(self, actor, delivery_id, now=None):
        """A delivery's access view: the linked core grant's status,
        derived by the CORE store's own derivation at ``now``.

        Action: read. The view reports the grant record's derived
        status and confers nothing: recording or viewing changes
        no state anywhere (pinned by test)."""
        self._maybe_require(actor, "read")
        delivery = self._get(self._deliveries, delivery_id, "delivery")
        self._check_commons_of(actor, delivery)
        grant_status = None
        if delivery["grant_id"] is not None:
            grant_status = self.store.get_grant(
                actor, delivery["grant_id"], now=now)["status"]
        return {"delivery_id": delivery_id,
                "dataset_id": delivery["dataset_id"],
                "grant_id": delivery["grant_id"],
                "grant_status": grant_status,
                "method": "core_grant_status_derivation",
                "conferred_here": False, "enforced_here": False,
                "data_moved_here": False}

    def enforcement_summary(self, actor, commons_id):
        """Deterministic counts of enforcement decisions by label.

        Action: read. Method ``deterministic_counts``."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        decisions = self._in_commons(self._enforcement_decisions, commons_id)
        by_label = {}
        for decision in decisions:
            by_label[decision["decision_label"]] = \
                by_label.get(decision["decision_label"], 0) + 1
        return {"commons_id": commons_id, "decisions": len(decisions),
                "decisions_by_label": by_label,
                "method": "deterministic_counts", "conferred_here": False,
                "enforced_here": False}

    # -- Identity provider / identity management (idx 530, reference) ---
    # Labeled reference implementation, per PLATFORM-LAYER.md
    # decision 1: identity proofing, authenticator management,
    # and any identity-provider service stay with the embedding
    # organization. An identity *reference* record names the
    # external provider the embedding organization uses; this
    # build is not one (``identity_provider`` False on every
    # record) and the core's demo identities remain hooks.

    def record_identity_reference(self, actor, commons_id, provider_ref,
                                  provider_label):
        """Record one external identity provider reference. Action: record."""
        self._guard(actor, "record", "ext_identity_reference_record")
        self._commons(actor, commons_id)
        _non_empty(provider_ref, "provider_ref")
        _non_empty(provider_label, "provider_label")
        with self._lock:
            for existing in self._in_commons(self._identity_references,
                                             commons_id):
                if existing["provider_ref"] == provider_ref:
                    raise ValidationError(
                        "provider_ref %r is already recorded in this commons"
                        % (provider_ref,))
            return self._create(
                self._identity_references, "idr-",
                {"commons_id": commons_id, "provider_ref": provider_ref,
                 "provider_label": provider_label, "reference_stub": True,
                 "state": _REFERENCE_STATE, "identity_provider": False},
                actor, "ext_identity_reference_record")

    def get_identity_reference(self, actor, reference_id):
        """Return one identity reference record. Action: read."""
        self._maybe_require(actor, "read")
        record = self._get(self._identity_references, reference_id,
                           "identity reference")
        self._check_commons_of(actor, record)
        return copy.deepcopy(record)

    def list_identity_references(self, actor, commons_id):
        """List identity references in a commons. Action: read."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        return copy.deepcopy(self._sorted(
            self._in_commons(self._identity_references, commons_id)))

    # -- Cross-entry summary ---------------------------------------------

    def engine_summary(self, actor, commons_id):
        """Deterministic counts over every extension record type.

        Action: read. Method ``deterministic_counts`` -- counts
        only, over this module's own records; nothing is executed,
        moved, computed about subjects, or scored."""
        self._maybe_require(actor, "read")
        self._commons(actor, commons_id)
        tables = (
            ("runtime_configs", self._runtime_configs),
            ("pipelines", self._pipelines),
            ("pipeline_runs", self._pipeline_runs),
            ("mappings", self._mappings),
            ("conformance_outcomes", self._conformance_outcomes),
            ("index_references", self._index_references),
            ("query_definitions", self._queries),
            ("query_results", self._query_results),
            ("cohorts", self._cohorts),
            ("cohort_membership_reports", self._cohort_memberships),
            ("peer_commons", self._peers),
            ("exchange_requests", self._exchange_requests),
            ("exchange_outcomes", self._exchange_outcomes),
            ("deliveries", self._deliveries),
            ("delivery_states", self._delivery_states),
            ("enforcement_decisions", self._enforcement_decisions),
            ("identity_references", self._identity_references),
        )
        summary = {"commons_id": commons_id, "method": "deterministic_counts"}
        total = 0
        for name, table in tables:
            count = len(self._in_commons(table, commons_id))
            summary[name] = count
            total += count
        summary["total_records"] = total
        return summary

