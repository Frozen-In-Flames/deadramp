"""Final GAPS batch extensions for the Data Management L3-adjacent
merged build (Group 28).

Clean-room, standard-library-only records/derivation extensions for
the 14 open Extended entries this group's GAPS.md section carries:
6 built as in-substrate records plus deterministic derivations over
the core's own records, 7 shipped as labeled reference
implementations (the drafted stub-engine families), and 1 (retention
disposition execution) re-judged to a labeled reference
implementation on the grounds in ``BATCH.md``. The family forms
follow the Group 12 (Data Management L2) batch unit's established
precedent family by family, adapted to this tier's core, which is
the L2 substrate carried up with the High-baseline uplifts. See
``BATCH.md`` in the group directory for the per-entry disposition,
the long-tail enumeration, and the re-judgment grounds.

Tier adaptations relative to the L2 precedent, stated plainly:

- **Fail closed (AU-5).** The core store wraps every mutation in a
  snapshot rollback so an operation whose audit write fails does
  not proceed. The extension surface holds its own records, so it
  applies the same posture itself: if the audit write for an
  extension mutation raises (``AuditWriteError``), the record
  insertion and its id are rolled back before the error propagates
  (see ``_create``). No extension record exists whose audit entry
  does not.
- **Hash-chained audit (AU-9).** Extension audit entries
  (``ext_*`` actions, ``:denied`` for denied attempts) are ordinary
  entries on the core's hash-chained log and are covered by
  ``verify_chain()`` like any other entry.
- **Auditor role (AC-5).** The High baseline's fourth role holds
  ``audit_read`` and nothing else; it therefore holds no permission
  anywhere on this surface -- every extension read and write maps
  onto an operational core action -- exactly as at the core store
  layer.

Design, following the core's doctrines:

- This module is a wrapper around :class:`DataMgmtStore`; the core
  modules are untouched (byte-identical). Dataset existence, schema,
  provenance, and retention due state are always read through the
  core store's public API, never re-implemented.
- RBAC goes through :mod:`datamgmt.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- All references to people, systems, assets, and evidence are opaque
  ``*_ref`` strings. Linkage records hold pairs of opaque references
  exactly as reported; no record shape in this module can hold an
  identifier value, a name, an email, or record payload rows.
- Derived values are derived at read and never stored: storage
  capacity/state views, linkage rollups, inspection rollups,
  capital-plan totals, case outcome views, lineage views. Stored
  records carry no derived key; tests pin that. (A query *run*
  record stores the result of evaluating a registered derivation
  over a supplied batch -- an event record, exactly as the core's
  quality-check runs store their outcome; nothing is written back
  onto the query definition or the dataset.)
- Case decisions carry the group's separation-of-duties signature
  in a new surface: the decider of a case may never be the actor
  who opened it, enforced at a single named seam
  (``_check_case_decider_not_opener``), the batch's fresh negative
  control.
- Nothing here executes against an external system. The
  stub-engine families ship as labeled reference implementations:
  every record they create carries ``reference_stub: True`` (file
  transfers carry ``reference_transport: True``), and no connector
  runs, no index is built, no content is processed, no workflow
  executes, nothing is hosted or provisioned, and no file moves.
"""

import copy
import json
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

STORAGE_ENGINE_KINDS = ("data_lake", "warehouse", "database", "replication_target")
KNOWN_STORAGE_ENGINE_KINDS = frozenset(STORAGE_ENGINE_KINDS)
LINKAGE_METHODS = (
    "reported_token_match",
    "reported_universal_key",
    "reported_cohort_overlap",
)
KNOWN_LINKAGE_METHODS = frozenset(LINKAGE_METHODS)
DEID_METHODS = (
    "expert_certification",
    "safe_harbor",
    "statistical_disclosure_control",
    "k_anonymity",
    "tokenization",
)
KNOWN_DEID_METHODS = frozenset(DEID_METHODS)
QUERY_KINDS = ("count_records", "count_by_field", "sum_field", "field_histogram")
KNOWN_QUERY_KINDS = frozenset(QUERY_KINDS)
CHART_KINDS = ("bar", "table", "line", "summary")
KNOWN_CHART_KINDS = frozenset(CHART_KINDS)
INSPECTION_OUTCOMES = ("satisfactory", "deficient", "critical", "not_inspected")
KNOWN_INSPECTION_OUTCOMES = frozenset(INSPECTION_OUTCOMES)
CASE_KINDS = ("vetting", "adjudication", "continuous_vetting")
KNOWN_CASE_KINDS = frozenset(CASE_KINDS)
CASE_OUTCOMES = ("favorable", "unfavorable", "pending_information")
KNOWN_CASE_OUTCOMES = frozenset(CASE_OUTCOMES)
TRANSFORMATION_STEP_KINDS = (
    "rename",
    "type_cast",
    "filter",
    "join",
    "aggregate",
    "mask",
    "derive",
)
KNOWN_TRANSFORMATION_STEP_KINDS = frozenset(TRANSFORMATION_STEP_KINDS)
DISPOSITION_DECISIONS = ("approve", "defer", "reject")
KNOWN_DISPOSITION_DECISIONS = frozenset(DISPOSITION_DECISIONS)
CONNECTOR_DIRECTIONS = ("inbound", "outbound", "bidirectional")
KNOWN_CONNECTOR_DIRECTIONS = frozenset(CONNECTOR_DIRECTIONS)
CONNECTOR_RUN_OUTCOMES = (
    "reported_success",
    "reported_failure",
    "reported_partial",
)
KNOWN_CONNECTOR_RUN_OUTCOMES = frozenset(CONNECTOR_RUN_OUTCOMES)
PROCESSING_KINDS = ("ocr", "transcription", "categorization")
KNOWN_PROCESSING_KINDS = frozenset(PROCESSING_KINDS)
CLUSTER_LIFECYCLE_EVENTS = (
    "provision_reported",
    "upgrade_reported",
    "decommission_reported",
    "day2_operation_reported",
)
KNOWN_CLUSTER_LIFECYCLE_EVENTS = frozenset(CLUSTER_LIFECYCLE_EVENTS)
HOSTING_KINDS = ("compute", "private_cloud", "virtual_desktop", "analytics_service")
KNOWN_HOSTING_KINDS = frozenset(HOSTING_KINDS)
TRANSFER_PROTOCOLS = ("sftp", "https", "as2", "managed_service")
KNOWN_TRANSFER_PROTOCOLS = frozenset(TRANSFER_PROTOCOLS)


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


def _int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    return value


def _nonneg_int(value, what):
    _int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _money(value, what):
    """Integer cents; booleans and floats are rejected (house rule)."""
    return _nonneg_int(value, what)


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
            raise ValidationError("each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


class DataMgmtExtensions:
    """GAPS-batch extension surface over a core DataMgmtStore."""

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

    def _dataset(self, dataset_id):
        """Return the core dataset record (NotFoundError if absent)."""
        return self.store.get_dataset(dataset_id)

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # AU-5, fail closed at this tier: an operation whose
                # audit write fails does not proceed. The core store
                # rolls its own state back under ``_atomic``; the
                # extension surface holds its own records, so it
                # rolls the insertion and the id back here before
                # the error propagates -- no record, no id consumed.
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

    # -- Distributed storage engines (records form) --------------------
    # Datasets/storage records with derived capacity/state views.
    # No storage engine runs: the build holds metadata about storage,
    # exactly as the core holds metadata about datasets.

    def register_storage_volume(self, dataset_id, name, engine_kind, actor,
                                capacity_units=None, replica_count=1):
        """Register a storage volume record for a dataset.

        Action: dataset_write. ``capacity_units`` is an opaque
        integer in whatever unit the registering system reports
        (the build does not interpret it); ``None`` means the
        capacity was not reported.
        """
        self._guard(actor, "dataset_write", "ext_storage_register", dataset_id)
        _non_empty(name, "storage volume name")
        _one_of(engine_kind, KNOWN_STORAGE_ENGINE_KINDS,
                STORAGE_ENGINE_KINDS, "engine_kind")
        if capacity_units is not None:
            _nonneg_int(capacity_units, "capacity_units")
        _int(replica_count, "replica_count")
        if replica_count < 1:
            raise ValidationError("replica_count must be at least 1")
        with self._lock:
            self._dataset(dataset_id)
            return self._create(
                "storage_volume", "stg",
                {"dataset_id": dataset_id, "name": name,
                 "engine_kind": engine_kind,
                 "capacity_units": capacity_units,
                 "replica_count": replica_count,
                 "state": "registered"},
                actor, "ext_storage_register")

    def get_storage_volume(self, volume_id, actor=None):
        """Return one storage volume record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_storage_read", volume_id)
        return self._fetch("storage_volume", volume_id)

    def list_storage_volumes(self, dataset_id=None, actor=None):
        """Return storage volume records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_storage_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("storage_volume", dataset_id=dataset_id)

    def storage_summary(self, dataset_id, actor=None):
        """Derived storage view for a dataset. Action: dataset_read.

        Counts, reported capacities, and replica totals are computed
        at read from the volume records and the core provenance view;
        nothing here is stored, and ``engine_executed`` is False:
        the volumes are records about storage, not a running engine.
        """
        self._guard_read(actor, "dataset_read", "ext_storage_summary", dataset_id)
        with self._lock:
            self._dataset(dataset_id)
            volumes = self._list("storage_volume", dataset_id=dataset_id)
            provenance = self.store.dataset_provenance(dataset_id)
            by_engine = {}
            for volume in volumes:
                kind = volume["engine_kind"]
                by_engine[kind] = by_engine.get(kind, 0) + 1
            capacities = [v["capacity_units"] for v in volumes
                          if v["capacity_units"] is not None]
            return {
                "dataset_id": dataset_id,
                "volumes": len(volumes),
                "by_engine": {k: by_engine[k] for k in sorted(by_engine)},
                "total_capacity_units": (
                    sum(capacities) if len(capacities) == len(volumes) else None
                ),
                "capacity_reported_for": len(capacities),
                "total_replicas": sum(v["replica_count"] for v in volumes),
                "ingested_records": provenance["total_records"],
                "state": "metadata_only",
                "engine_executed": False,
            }

    # -- PPRL record linkage & de-identification (records form) --------
    # Linkage is recorded as reported pairs between opaque references.
    # No identifier value is ever accepted, no matching algorithm runs
    # over data, and a de-identification declaration transforms
    # nothing: it records the method declared for a dataset.

    def record_linkage_report(self, dataset_id, left_ref, right_ref, method,
                              actor, ingestion_id=None):
        """Record a reported linkage between two opaque references.

        Action: ingest_record. The pair is stored exactly as
        reported by the external linkage process; the build computes
        no match (``match_computed_here`` is False on every record).
        """
        self._guard(actor, "ingest_record", "ext_linkage_record", dataset_id)
        _non_empty(left_ref, "left_ref")
        _non_empty(right_ref, "right_ref")
        if left_ref == right_ref:
            raise ValidationError("left_ref and right_ref must differ")
        _one_of(method, KNOWN_LINKAGE_METHODS, LINKAGE_METHODS, "method")
        with self._lock:
            self._dataset(dataset_id)
            if ingestion_id is not None:
                ingestion = self.store.get_ingestion(ingestion_id)
                if ingestion["dataset_id"] != dataset_id:
                    raise ValidationError(
                        "ingestion %r does not belong to dataset %r"
                        % (ingestion_id, dataset_id)
                    )
            return self._create(
                "linkage_report", "lnk",
                {"dataset_id": dataset_id, "left_ref": left_ref,
                 "right_ref": right_ref, "method": method,
                 "ingestion_id": ingestion_id,
                 "match_computed_here": False},
                actor, "ext_linkage_record")

    def get_linkage_report(self, report_id, actor=None):
        """Return one linkage report. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_linkage_read", report_id)
        return self._fetch("linkage_report", report_id)

    def list_linkage_reports(self, dataset_id=None, actor=None):
        """Return linkage reports. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_linkage_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("linkage_report", dataset_id=dataset_id)

    def linkage_summary(self, dataset_id, actor=None):
        """Derived linkage rollup for a dataset. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_linkage_summary", dataset_id)
        with self._lock:
            self._dataset(dataset_id)
            reports = self._list("linkage_report", dataset_id=dataset_id)
            refs = set()
            by_method = {}
            for report in reports:
                refs.add(report["left_ref"])
                refs.add(report["right_ref"])
                method = report["method"]
                by_method[method] = by_method.get(method, 0) + 1
            return {
                "dataset_id": dataset_id,
                "reports": len(reports),
                "distinct_refs": len(refs),
                "by_method": {k: by_method[k] for k in sorted(by_method)},
                "match_computed_here": False,
            }

    def declare_deidentification(self, dataset_id, method, actor, basis=None,
                                 ingestion_id=None):
        """Declare a de-identification method for a dataset.

        Action: quality_write. A declaration is a governance record:
        it states the method an external process declares it applied.
        The build transforms no records (``applied_here`` is False
        and ``records_transformed`` is 0 on every declaration).
        """
        self._guard(actor, "quality_write", "ext_deidentification_declare",
                    dataset_id)
        _one_of(method, KNOWN_DEID_METHODS, DEID_METHODS, "method")
        _string_or_none(basis, "basis")
        with self._lock:
            self._dataset(dataset_id)
            if ingestion_id is not None:
                ingestion = self.store.get_ingestion(ingestion_id)
                if ingestion["dataset_id"] != dataset_id:
                    raise ValidationError(
                        "ingestion %r does not belong to dataset %r"
                        % (ingestion_id, dataset_id)
                    )
            return self._create(
                "deidentification", "dei",
                {"dataset_id": dataset_id, "method": method,
                 "basis": basis, "ingestion_id": ingestion_id,
                 "applied_here": False, "records_transformed": 0},
                actor, "ext_deidentification_declare")

    def get_deidentification(self, declaration_id, actor=None):
        """Return one de-identification declaration. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_deidentification_read",
                         declaration_id)
        return self._fetch("deidentification", declaration_id)

    def list_deidentifications(self, dataset_id=None, actor=None):
        """Return de-identification declarations. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_deidentification_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("deidentification", dataset_id=dataset_id)

    # -- Query & visualization (deterministic derivations) -------------
    # A query definition is a registered, deterministic derivation
    # spec over records supplied at run time -- the same shape as the
    # core's quality checks. The build holds no live dataset store
    # and reaches into none; a run evaluates the spec over the batch
    # in the call and records the run as an event. A visualization
    # definition renders nothing: its view is derived from stored
    # run records.

    def define_query(self, name, dataset_id, kind, actor, field=None,
                     value_equals=None, has_filter=False):
        """Register a query definition. Action: dataset_write.

        ``kind`` is one of count_records / count_by_field /
        sum_field / field_histogram. The field-shaped kinds require
        ``field``. ``has_filter`` with ``value_equals`` restricts
        evaluation to records whose field equals the given JSON
        scalar.
        """
        self._guard(actor, "dataset_write", "ext_query_define", dataset_id)
        _non_empty(name, "query name")
        _one_of(kind, KNOWN_QUERY_KINDS, QUERY_KINDS, "kind")
        if kind in ("count_by_field", "sum_field", "field_histogram"):
            _non_empty(field, "field")
        elif field is not None:
            _non_empty(field, "field")
        if not isinstance(has_filter, bool):
            raise ValidationError("has_filter must be a bool")
        if has_filter and not (
                value_equals is None
                or isinstance(value_equals, (str, int, float, bool))):
            raise ValidationError(
                "value_equals must be a JSON scalar (string, number, "
                "boolean, or null)")
        with self._lock:
            self._dataset(dataset_id)
            return self._create(
                "query", "qry",
                {"name": name, "dataset_id": dataset_id, "kind": kind,
                 "field": field, "has_filter": has_filter,
                 "value_equals": value_equals if has_filter else None},
                actor, "ext_query_define")

    def get_query(self, query_id, actor=None):
        """Return one query definition. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_query_read", query_id)
        return self._fetch("query", query_id)

    def list_queries(self, dataset_id=None, actor=None):
        """Return query definitions. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_query_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("query", dataset_id=dataset_id)

    @staticmethod
    def _value_key(value):
        if isinstance(value, str):
            return value
        return json.dumps(value, sort_keys=True)

    def run_query(self, query_id, records, actor):
        """Evaluate a query definition over a supplied batch.

        Action: quality_run. Deterministic: the same definition and
        batch always produce the same result. The run is recorded
        as an event (like a core quality-check run); the definition
        and the dataset are not modified.
        """
        self._guard(actor, "quality_run", "ext_query_run", query_id)
        if not isinstance(records, list):
            raise ValidationError("records must be a list of dicts")
        for record in records:
            if not isinstance(record, dict):
                raise ValidationError("each record must be a dict")
        with self._lock:
            query = self._get("query", query_id)
            kind = query["kind"]
            field = query["field"]
            batch = records
            if query["has_filter"]:
                batch = [r for r in records
                         if r.get(field) == query["value_equals"]]
            if kind == "count_records":
                result = {"count": len(batch)}
            elif kind in ("count_by_field", "field_histogram"):
                counts = {}
                for record in batch:
                    key = self._value_key(record.get(field))
                    counts[key] = counts.get(key, 0) + 1
                result = {"counts": {k: counts[k] for k in sorted(counts)}}
            else:  # sum_field
                total = 0
                considered = 0
                skipped = 0
                for record in batch:
                    value = record.get(field)
                    if isinstance(value, bool) or not isinstance(
                            value, (int, float)):
                        skipped += 1
                    else:
                        total += value
                        considered += 1
                result = {"sum": total, "values_considered": considered,
                          "values_skipped": skipped}
            return self._create(
                "query_run", "qrs",
                {"query_id": query_id, "dataset_id": query["dataset_id"],
                 "kind": kind, "records_evaluated": len(records),
                 "records_matched": len(batch),
                 "result": result, "method": "deterministic_derivation"},
                actor, "ext_query_run")

    def get_query_run(self, run_id, actor=None):
        """Return one query run record. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_query_run_read", run_id)
        return self._fetch("query_run", run_id)

    def list_query_runs(self, query_id=None, actor=None):
        """Return query run records. Action: quality_read."""
        self._guard_read(actor, "quality_read", "ext_query_run_read", query_id)
        if query_id is not None:
            self._get("query", query_id)
        return self._list("query_run", query_id=query_id)

    def define_visualization(self, name, query_id, chart_kind, actor):
        """Register a visualization definition over a query.

        Action: dataset_write. A definition only: nothing is
        rendered or served (``definition_only`` is True).
        """
        self._guard(actor, "dataset_write", "ext_visualization_define",
                    query_id)
        _non_empty(name, "visualization name")
        _one_of(chart_kind, KNOWN_CHART_KINDS, CHART_KINDS, "chart_kind")
        with self._lock:
            self._get("query", query_id)
            return self._create(
                "visualization", "viz",
                {"name": name, "query_id": query_id,
                 "chart_kind": chart_kind, "definition_only": True},
                actor, "ext_visualization_define")

    def get_visualization(self, visualization_id, actor=None):
        """Return one visualization definition. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_visualization_read",
                         visualization_id)
        return self._fetch("visualization", visualization_id)

    def list_visualizations(self, query_id=None, actor=None):
        """Return visualization definitions. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_visualization_read",
                         query_id)
        if query_id is not None:
            self._get("query", query_id)
        return self._list("visualization", query_id=query_id)

    def render_visualization(self, visualization_id, actor=None):
        """Derived view of a visualization. Action: dataset_read.

        The series is the latest stored query-run result for the
        visualization's query, or None when no run exists. No query
        is executed here (``executes_query`` is False).
        """
        self._guard_read(actor, "dataset_read", "ext_visualization_render",
                         visualization_id)
        with self._lock:
            viz = self._get("visualization", visualization_id)
            runs = self._list("query_run", query_id=viz["query_id"])
            latest = runs[-1] if runs else None
            return {
                "visualization_id": visualization_id,
                "query_id": viz["query_id"],
                "chart_kind": viz["chart_kind"],
                "series": latest["result"] if latest else None,
                "latest_run_id": latest["id"] if latest else None,
                "runs_available": len(runs),
                "rendered_from": (
                    "stored_query_run_records" if latest else "no_runs"),
                "executes_query": False,
            }

    # -- Asset inspection & capital planning (records form) ------------

    def record_inspection(self, asset_ref, dataset_id, outcome, actor,
                          finding_count=0, notes=None):
        """Record an asset inspection outcome. Action: dataset_write.

        The inspection itself is performed by the owning program;
        this is the record of its reported outcome. Assets are
        opaque references; no asset data is held.
        """
        self._guard(actor, "dataset_write", "ext_inspection_record",
                    dataset_id)
        _non_empty(asset_ref, "asset_ref")
        _one_of(outcome, KNOWN_INSPECTION_OUTCOMES,
                INSPECTION_OUTCOMES, "outcome")
        _nonneg_int(finding_count, "finding_count")
        _string_or_none(notes, "notes")
        with self._lock:
            self._dataset(dataset_id)
            return self._create(
                "inspection", "insp",
                {"asset_ref": asset_ref, "dataset_id": dataset_id,
                 "outcome": outcome, "finding_count": finding_count,
                 "notes": notes},
                actor, "ext_inspection_record")

    def get_inspection(self, inspection_id, actor=None):
        """Return one inspection record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_inspection_read",
                         inspection_id)
        return self._fetch("inspection", inspection_id)

    def list_inspections(self, dataset_id=None, asset_ref=None, actor=None):
        """Return inspection records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_inspection_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("inspection", dataset_id=dataset_id,
                          asset_ref=asset_ref)

    def inspection_summary(self, dataset_id=None, actor=None):
        """Derived inspection rollup. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_inspection_summary",
                         dataset_id)
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            records = self._list("inspection", dataset_id=dataset_id)
            by_outcome = {}
            assets = set()
            findings = 0
            for record in records:
                outcome = record["outcome"]
                by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
                assets.add(record["asset_ref"])
                findings += record["finding_count"]
            return {
                "dataset_id": dataset_id,
                "inspections": len(records),
                "assets_inspected": len(assets),
                "total_findings": findings,
                "by_outcome": {k: by_outcome[k] for k in sorted(by_outcome)},
            }

    def create_capital_plan(self, name, actor, horizon_years=5):
        """Create a capital plan record. Action: dataset_write.

        The stored plan carries no totals: plan totals are derived
        at read from its items (see ``capital_plan_view``).
        """
        self._guard(actor, "dataset_write", "ext_capital_plan_create")
        _non_empty(name, "capital plan name")
        _int(horizon_years, "horizon_years")
        if horizon_years < 1 or horizon_years > 50:
            raise ValidationError("horizon_years must be between 1 and 50")
        return self._create(
            "capital_plan", "cap",
            {"name": name, "horizon_years": horizon_years},
            actor, "ext_capital_plan_create")

    def get_capital_plan(self, plan_id, actor=None):
        """Return one capital plan record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_capital_plan_read",
                         plan_id)
        return self._fetch("capital_plan", plan_id)

    def list_capital_plans(self, actor=None):
        """Return capital plan records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_capital_plan_read")
        return self._list("capital_plan")

    def add_capital_item(self, plan_id, label, amount_cents, actor,
                         year_offset=1, asset_ref=None):
        """Add a planned capital item. Action: dataset_write.

        Amounts are integer cents; booleans and floats are rejected
        at the boundary (house money rule).
        """
        self._guard(actor, "dataset_write", "ext_capital_item_add", plan_id)
        _non_empty(label, "label")
        _money(amount_cents, "amount_cents")
        _int(year_offset, "year_offset")
        _string_or_none(asset_ref, "asset_ref")
        if asset_ref is not None:
            _non_empty(asset_ref, "asset_ref")
        with self._lock:
            plan = self._get("capital_plan", plan_id)
            if year_offset < 1 or year_offset > plan["horizon_years"]:
                raise ValidationError(
                    "year_offset must be between 1 and the plan horizon "
                    "(%d)" % (plan["horizon_years"],))
            return self._create(
                "capital_item", "cit",
                {"plan_id": plan_id, "label": label,
                 "amount_cents": amount_cents,
                 "year_offset": year_offset, "asset_ref": asset_ref},
                actor, "ext_capital_item_add")

    def list_capital_items(self, plan_id, actor=None):
        """Return a plan's items. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_capital_item_read",
                         plan_id)
        self._get("capital_plan", plan_id)
        return self._list("capital_item", plan_id=plan_id)

    def capital_plan_view(self, plan_id, actor=None):
        """Derived capital plan view. Action: dataset_read.

        Total and per-year amounts are summed at read from the
        plan's item records; the stored plan record holds neither.
        """
        self._guard_read(actor, "dataset_read", "ext_capital_plan_view",
                         plan_id)
        with self._lock:
            plan = self._fetch("capital_plan", plan_id)
            items = self._list("capital_item", plan_id=plan_id)
            by_year = {}
            total = 0
            for item in items:
                total += item["amount_cents"]
                year = item["year_offset"]
                by_year[year] = by_year.get(year, 0) + item["amount_cents"]
            return {
                "plan_id": plan_id,
                "name": plan["name"],
                "horizon_years": plan["horizon_years"],
                "item_count": len(items),
                "total_cents": total,
                "by_year": {k: by_year[k] for k in sorted(by_year)},
            }

    # -- Case management depth: vetting / adjudication (records form) --
    # Cases are records with evidence references and a decision
    # workflow. The decision carries the group's separation-of-duties
    # signature: the decider may never be the actor who opened the
    # case, enforced at the single seam below -- the same doctrine
    # the core applies to access decisions
    # (``_check_decider_not_requester``).

    def open_case(self, subject_ref, kind, actor, dataset_id=None):
        """Open a vetting/adjudication case. Action: access_request.

        The subject is an opaque reference; the build holds no
        subject data and performs no investigation.
        """
        self._guard(actor, "access_request", "ext_case_open", dataset_id)
        _non_empty(subject_ref, "subject_ref")
        _one_of(kind, KNOWN_CASE_KINDS, CASE_KINDS, "kind")
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            return self._create(
                "case", "case",
                {"subject_ref": subject_ref, "kind": kind,
                 "dataset_id": dataset_id, "status": "open",
                 "opened_by": actor_name(actor), "outcome": None,
                 "decision_id": None, "decided_by": None,
                 "decided_utc": None},
                actor, "ext_case_open")

    def get_case(self, case_id, actor=None):
        """Return one case record. Action: access_read."""
        self._guard_read(actor, "access_read", "ext_case_read", case_id)
        return self._fetch("case", case_id)

    def list_cases(self, dataset_id=None, status=None, actor=None):
        """Return case records. Action: access_read."""
        self._guard_read(actor, "access_read", "ext_case_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        if status is not None and status not in ("open", "decided"):
            raise ValidationError("status must be 'open' or 'decided'")
        return self._list("case", dataset_id=dataset_id, status=status)

    def record_case_evidence(self, case_id, evidence_ref, actor, note=None):
        """Attach an evidence reference to an open case.

        Action: access_request. Evidence is an opaque reference
        only; the build never holds evidence content.
        """
        self._guard(actor, "access_request", "ext_case_evidence_record",
                    case_id)
        _non_empty(evidence_ref, "evidence_ref")
        _string_or_none(note, "note")
        with self._lock:
            case = self._get("case", case_id)
            if case["status"] != "open":
                raise ValidationError(
                    "case %r is already decided; evidence is closed"
                    % (case_id,))
            return self._create(
                "case_evidence", "cev",
                {"case_id": case_id, "evidence_ref": evidence_ref,
                 "note": note},
                actor, "ext_case_evidence_record")

    def list_case_evidence(self, case_id, actor=None):
        """Return a case's evidence references. Action: access_read."""
        self._guard_read(actor, "access_read", "ext_case_evidence_read",
                         case_id)
        self._get("case", case_id)
        return self._list("case_evidence", case_id=case_id)

    def _check_case_decider_not_opener(self, case, actor):
        """Separation-of-duties seam for case decisions.

        The actor deciding a case may never be the actor who opened
        it. This is the extension surface's signature guard and the
        batch's fresh negative control target.
        """
        if actor_name(actor) == case["opened_by"]:
            raise PermissionDenied("case decider may not be the case opener")

    def decide_case(self, case_id, outcome, actor, reason=None):
        """Decide an open case. Action: access_decide.

        The decider is never the opener (separation of duties,
        AC-5). A decision record is created and the case's outcome
        fields are set from it.
        """
        self._guard(actor, "access_decide", "ext_case_decide", case_id)
        _one_of(outcome, KNOWN_CASE_OUTCOMES, CASE_OUTCOMES, "outcome")
        _string_or_none(reason, "reason")
        with self._lock:
            case = self._get("case", case_id)
            self._check_case_decider_not_opener(case, actor)
            if case["status"] != "open":
                raise ValidationError(
                    "case %r has already been decided" % (case_id,))
            decision = self._create(
                "case_decision", "cde",
                {"case_id": case_id, "outcome": outcome,
                 "reason": reason},
                actor, "ext_case_decide")
            case["status"] = "decided"
            case["outcome"] = outcome
            case["decision_id"] = decision["id"]
            case["decided_by"] = actor_name(actor)
            case["decided_utc"] = decision["created_utc"]
            return copy.deepcopy(case)

    def list_case_decisions(self, case_id=None, actor=None):
        """Return case decision records. Action: access_read."""
        self._guard_read(actor, "access_read", "ext_case_decision_read",
                         case_id)
        if case_id is not None:
            self._get("case", case_id)
        return self._list("case_decision", case_id=case_id)

    # -- Field-level / transformation lineage (records form) -----------
    # The core's provenance is bounded to ingestion granularity and
    # the spec says so. This surface adds the field level as
    # *declared* transformation steps: records stating that a named
    # step kind was applied to a named field within a named core
    # ingestion. Steps are declarations about a pipeline, recorded
    # here; the build executes no transformation and holds no rows.

    def record_transformation_step(self, dataset_id, ingestion_id, step_kind,
                                   field, actor, source_field=None,
                                   note=None):
        """Record a declared transformation step. Action: ingest_record."""
        self._guard(actor, "ingest_record", "ext_lineage_step_record",
                    dataset_id)
        _one_of(step_kind, KNOWN_TRANSFORMATION_STEP_KINDS,
                TRANSFORMATION_STEP_KINDS, "step_kind")
        _non_empty(field, "field")
        if source_field is not None:
            _non_empty(source_field, "source_field")
        _string_or_none(note, "note")
        with self._lock:
            self._dataset(dataset_id)
            ingestion = self.store.get_ingestion(ingestion_id)
            if ingestion["dataset_id"] != dataset_id:
                raise ValidationError(
                    "ingestion %r does not belong to dataset %r"
                    % (ingestion_id, dataset_id))
            return self._create(
                "transformation_step", "stp",
                {"dataset_id": dataset_id, "ingestion_id": ingestion_id,
                 "step_kind": step_kind, "field": field,
                 "source_field": source_field, "note": note,
                 "executed_here": False},
                actor, "ext_lineage_step_record")

    def get_transformation_step(self, step_id, actor=None):
        """Return one transformation step record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_lineage_step_read",
                         step_id)
        return self._fetch("transformation_step", step_id)

    def list_transformation_steps(self, dataset_id=None, field=None,
                                  actor=None):
        """Return transformation step records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_lineage_step_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("transformation_step", dataset_id=dataset_id,
                          field=field)

    def field_lineage(self, dataset_id, field, actor=None):
        """Derived field-level lineage view. Action: ingest_read.

        Joins the declared steps for (dataset, field) with the
        core's ingestion-granularity provenance totals, computed at
        read; the view states both granularities plainly.
        """
        self._guard_read(actor, "ingest_read", "ext_field_lineage",
                         dataset_id)
        _non_empty(field, "field")
        with self._lock:
            self._dataset(dataset_id)
            steps = self._list("transformation_step",
                               dataset_id=dataset_id, field=field)
            provenance = self.store.dataset_provenance(dataset_id)
            return {
                "dataset_id": dataset_id,
                "field": field,
                "steps": steps,
                "step_count": len(steps),
                "step_kinds": sorted({s["step_kind"] for s in steps}),
                "ingestions_referenced": sorted(
                    {s["ingestion_id"] for s in steps}),
                "total_records_ingested": provenance["total_records"],
                "granularity": "field_level_declared_steps",
                "core_provenance_granularity": "ingestion",
            }

    # -- Retention disposition (RE-JUDGED: labeled reference) ----------
    # Grounds are recorded in BATCH.md. In short: PLATFORM-LAYER.md
    # decision 4 and this group's own spec both place disposition
    # *execution* (deletion, archival, NARA/FOIA production) with the
    # embedding organization's records schedule at the deployment
    # layer -- UNION-SPEC.md Core function 8: "The build schedules
    # and reports; it does not execute disposition" -- and the
    # Group 12 batch unit adjudicated the identical entry to this
    # same disposition one tier down. The build's audit is
    # append-only and nothing in this substrate may delete. What
    # honestly lands here is therefore a
    # labeled reference implementation of the decision layer:
    # disposition DECISION records whose eligibility is derived at
    # record time from the core's retention schedules and due
    # evaluation, plus execution *reference* records that execute
    # nothing. Every record carries ``reference_stub: True``.

    def record_disposition_decision(self, dataset_id, decision, actor,
                                    now=None, reason=None):
        """Record a disposition decision for a dataset.

        Action: retention_write. Eligibility is derived from the
        core's ``retention_due`` evaluation at ``now`` (default:
        the current time); a dataset under legal hold or inside its
        retention window records ``eligible: False``. The decision
        record carries ``reference_stub: True`` and
        ``disposition_executed: False``: recording a decision
        deletes and archives nothing.
        """
        self._guard(actor, "retention_write", "ext_disposition_decision",
                    dataset_id)
        _one_of(decision, KNOWN_DISPOSITION_DECISIONS,
                DISPOSITION_DECISIONS, "decision")
        _string_or_none(reason, "reason")
        with self._lock:
            self._dataset(dataset_id)
            policy = self.store.retention_policy_for(dataset_id)
            if policy is None:
                raise ValidationError(
                    "no retention policy exists for dataset %r; a "
                    "disposition decision requires the core schedule "
                    "first" % (dataset_id,))
            due = self.store.retention_due(actor, now=now)
            entry = next((d for d in due
                          if d["dataset_id"] == dataset_id), None)
            return self._create(
                "disposition_decision", "ddc",
                {"dataset_id": dataset_id, "policy_id": policy["id"],
                 "disposition": policy["disposition"],
                 "decision": decision,
                 "eligible": entry is not None,
                 "age_days": entry["age_days"] if entry else None,
                 "reference_utc": entry["reference_utc"] if entry else None,
                 "legal_hold": bool(policy["legal_hold"]),
                 "reason": reason,
                 "reference_stub": True,
                 "disposition_executed": False},
                actor, "ext_disposition_decision")

    def get_disposition_decision(self, decision_id, actor=None):
        """Return one disposition decision. Action: retention_read."""
        self._guard_read(actor, "retention_read",
                         "ext_disposition_decision_read", decision_id)
        return self._fetch("disposition_decision", decision_id)

    def list_disposition_decisions(self, dataset_id=None, actor=None):
        """Return disposition decisions. Action: retention_read."""
        self._guard_read(actor, "retention_read",
                         "ext_disposition_decision_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("disposition_decision", dataset_id=dataset_id)

    def record_disposition_execution_reference(self, decision_id, actor,
                                               target_ref=None):
        """Record an execution reference for an approved decision.

        Action: retention_write. A reference record only: it states
        that execution is handed to the embedding organization's
        records schedule (PLATFORM-LAYER.md decision 4). It executes
        nothing (``executed`` is False) and carries
        ``reference_stub: True``.
        """
        self._guard(actor, "retention_write",
                    "ext_disposition_execution_reference", decision_id)
        _string_or_none(target_ref, "target_ref")
        if target_ref is not None:
            _non_empty(target_ref, "target_ref")
        with self._lock:
            decision = self._get("disposition_decision", decision_id)
            if decision["decision"] != "approve":
                raise ValidationError(
                    "an execution reference requires an approved "
                    "decision; decision %r is %r"
                    % (decision_id, decision["decision"]))
            return self._create(
                "disposition_execution", "dex",
                {"decision_id": decision_id,
                 "dataset_id": decision["dataset_id"],
                 "target_ref": target_ref,
                 "reference_stub": True,
                 "status": "recorded_reference_only",
                 "executed": False, "executed_by": None},
                actor, "ext_disposition_execution_reference")

    def list_disposition_execution_references(self, decision_id=None,
                                              actor=None):
        """Return execution reference records. Action: retention_read."""
        self._guard_read(actor, "retention_read",
                         "ext_disposition_execution_read", decision_id)
        if decision_id is not None:
            self._get("disposition_decision", decision_id)
        return self._list("disposition_execution", decision_id=decision_id)

    # -- Stub-engine families: labeled reference implementations -------
    # Each surface below registers records about an engine the build
    # does not contain. Every record carries ``reference_stub: True``
    # (file transfers: ``reference_transport: True``) and a status of
    # ``recorded_reference_only``; run-shaped records state that
    # nothing executed here. This follows the house precedent for
    # stub engines (DECISION.md): records only, never execution, and
    # never a claim that an external system was touched.

    # Integration runtime & connector engine (iPaaS execution).
    def register_connector(self, name, system_ref, actor,
                           direction="bidirectional"):
        """Register a connector record. Action: source_write.

        A connector here is a registry record about an integration
        an external runtime performs; this build runs no connector.
        """
        self._guard(actor, "source_write", "ext_connector_register")
        _non_empty(name, "connector name")
        _non_empty(system_ref, "system_ref")
        _one_of(direction, KNOWN_CONNECTOR_DIRECTIONS,
                CONNECTOR_DIRECTIONS, "direction")
        return self._create(
            "connector", "con",
            {"name": name, "system_ref": system_ref,
             "direction": direction, "reference_stub": True,
             "status": "recorded_reference_only"},
            actor, "ext_connector_register")

    def get_connector(self, connector_id, actor=None):
        """Return one connector record. Action: source_read."""
        self._guard_read(actor, "source_read", "ext_connector_read",
                         connector_id)
        return self._fetch("connector", connector_id)

    def list_connectors(self, actor=None):
        """Return connector records. Action: source_read."""
        self._guard_read(actor, "source_read", "ext_connector_read")
        return self._list("connector")

    def record_connector_run(self, connector_id, outcome, actor,
                             records_reported=0):
        """Record a connector run as reported externally.

        Action: ingest_record. The outcome is the runtime's own
        report, stored verbatim as a label; nothing executed here.
        """
        self._guard(actor, "ingest_record", "ext_connector_run_record",
                    connector_id)
        _one_of(outcome, KNOWN_CONNECTOR_RUN_OUTCOMES,
                CONNECTOR_RUN_OUTCOMES, "outcome")
        _nonneg_int(records_reported, "records_reported")
        with self._lock:
            self._get("connector", connector_id)
            return self._create(
                "connector_run", "crn",
                {"connector_id": connector_id, "outcome": outcome,
                 "records_reported": records_reported,
                 "reference_stub": True, "executed_here": False},
                actor, "ext_connector_run_record")

    def list_connector_runs(self, connector_id=None, actor=None):
        """Return connector run records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_connector_run_read",
                         connector_id)
        if connector_id is not None:
            self._get("connector", connector_id)
        return self._list("connector_run", connector_id=connector_id)

    # Enterprise search indexing engine (the core searches registry
    # metadata; no index is built here).
    def define_search_index(self, name, actor, dataset_id=None):
        """Register a search-index definition. Action: dataset_write.

        A definition record only: no index is built, populated, or
        queried through this surface.
        """
        self._guard(actor, "dataset_write", "ext_search_index_define",
                    dataset_id)
        _non_empty(name, "search index name")
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            return self._create(
                "search_index", "idx",
                {"name": name, "dataset_id": dataset_id,
                 "reference_stub": True,
                 "status": "recorded_reference_only"},
                actor, "ext_search_index_define")

    def get_search_index(self, index_id, actor=None):
        """Return one search-index definition. Action: catalog_read."""
        self._guard_read(actor, "catalog_read", "ext_search_index_read",
                         index_id)
        return self._fetch("search_index", index_id)

    def list_search_indexes(self, dataset_id=None, actor=None):
        """Return search-index definitions. Action: catalog_read."""
        self._guard_read(actor, "catalog_read", "ext_search_index_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("search_index", dataset_id=dataset_id)

    def record_index_snapshot(self, index_id, documents_reported, actor):
        """Record an index-size snapshot as reported externally.

        Action: ingest_record.
        """
        self._guard(actor, "ingest_record", "ext_index_snapshot_record",
                    index_id)
        _nonneg_int(documents_reported, "documents_reported")
        with self._lock:
            self._get("search_index", index_id)
            return self._create(
                "index_snapshot", "isn",
                {"index_id": index_id,
                 "documents_reported": documents_reported,
                 "reference_stub": True, "indexed_here": False},
                actor, "ext_index_snapshot_record")

    def list_index_snapshots(self, index_id=None, actor=None):
        """Return index snapshot records. Action: catalog_read."""
        self._guard_read(actor, "catalog_read", "ext_index_snapshot_read",
                         index_id)
        if index_id is not None:
            self._get("search_index", index_id)
        return self._list("index_snapshot", index_id=index_id)

    # Content processing engines (OCR, transcription, categorization).
    def register_processing_job(self, kind, dataset_id, actor,
                                ingestion_id=None):
        """Register a content-processing job record.

        Action: ingest_record. The job is a record about processing
        an external engine performs; this build processes no
        content and holds no output content.
        """
        self._guard(actor, "ingest_record", "ext_processing_job_register",
                    dataset_id)
        _one_of(kind, KNOWN_PROCESSING_KINDS, PROCESSING_KINDS, "kind")
        with self._lock:
            self._dataset(dataset_id)
            if ingestion_id is not None:
                ingestion = self.store.get_ingestion(ingestion_id)
                if ingestion["dataset_id"] != dataset_id:
                    raise ValidationError(
                        "ingestion %r does not belong to dataset %r"
                        % (ingestion_id, dataset_id))
            return self._create(
                "processing_job", "prc",
                {"kind": kind, "dataset_id": dataset_id,
                 "ingestion_id": ingestion_id,
                 "reference_stub": True,
                 "status": "recorded_reference_only",
                 "outputs_held": False},
                actor, "ext_processing_job_register")

    def get_processing_job(self, job_id, actor=None):
        """Return one processing job record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_processing_job_read",
                         job_id)
        return self._fetch("processing_job", job_id)

    def list_processing_jobs(self, dataset_id=None, actor=None):
        """Return processing job records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_processing_job_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("processing_job", dataset_id=dataset_id)

    def record_processing_output(self, job_id, output_ref, actor):
        """Record an output reference for a processing job.

        Action: ingest_record. Only the opaque reference is held;
        the output content itself never enters this build.
        """
        self._guard(actor, "ingest_record", "ext_processing_output_record",
                    job_id)
        _non_empty(output_ref, "output_ref")
        with self._lock:
            self._get("processing_job", job_id)
            return self._create(
                "processing_output", "pro",
                {"job_id": job_id, "output_ref": output_ref,
                 "reference_stub": True, "content_held": False},
                actor, "ext_processing_output_record")

    def list_processing_outputs(self, job_id=None, actor=None):
        """Return processing output records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_processing_output_read",
                         job_id)
        if job_id is not None:
            self._get("processing_job", job_id)
        return self._list("processing_output", job_id=job_id)

    # Workflow / BPM execution & guided-interview engines.
    def define_workflow(self, name, actor, steps=None):
        """Register a workflow definition. Action: dataset_write.

        Definitions are data: the registry holds them and never
        executes them (``executed`` is False on every record), the
        same doctrine as the house workflow registries elsewhere in
        this repo.
        """
        self._guard(actor, "dataset_write", "ext_workflow_define")
        _non_empty(name, "workflow name")
        clean_steps = _string_list(steps, "steps")
        return self._create(
            "workflow", "wfl",
            {"name": name, "steps": clean_steps,
             "reference_stub": True,
             "status": "recorded_reference_only", "executed": False},
            actor, "ext_workflow_define")

    def get_workflow(self, workflow_id, actor=None):
        """Return one workflow definition. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_workflow_read",
                         workflow_id)
        return self._fetch("workflow", workflow_id)

    def list_workflows(self, actor=None):
        """Return workflow definitions. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_workflow_read")
        return self._list("workflow")

    def define_guided_interview(self, name, actor, workflow_id=None,
                                questions=None):
        """Register a guided-interview definition.

        Action: dataset_write. Questions are held verbatim as data;
        no interview is conducted.
        """
        self._guard(actor, "dataset_write", "ext_guided_interview_define",
                    workflow_id)
        _non_empty(name, "guided interview name")
        clean_questions = _string_list(questions, "questions")
        with self._lock:
            if workflow_id is not None:
                self._get("workflow", workflow_id)
            return self._create(
                "guided_interview", "giv",
                {"name": name, "workflow_id": workflow_id,
                 "questions": clean_questions,
                 "reference_stub": True,
                 "status": "recorded_reference_only"},
                actor, "ext_guided_interview_define")

    def get_guided_interview(self, interview_id, actor=None):
        """Return one guided-interview definition. Action: dataset_read."""
        self._guard_read(actor, "dataset_read",
                         "ext_guided_interview_read", interview_id)
        return self._fetch("guided_interview", interview_id)

    def list_guided_interviews(self, workflow_id=None, actor=None):
        """Return guided-interview definitions. Action: dataset_read."""
        self._guard_read(actor, "dataset_read",
                         "ext_guided_interview_read", workflow_id)
        if workflow_id is not None:
            self._get("workflow", workflow_id)
        return self._list("guided_interview", workflow_id=workflow_id)

    # IaaS / PaaS hosting (compute, private cloud, DaaS, AaaS).
    def record_hosting(self, kind, label, actor):
        """Record a hosting arrangement. Action: dataset_write.

        A posture record about hosting an external platform
        provides; this build hosts nothing (``hosted_here`` is
        False) and remains a single-tenant reference deployment.
        """
        self._guard(actor, "dataset_write", "ext_hosting_record")
        _one_of(kind, KNOWN_HOSTING_KINDS, HOSTING_KINDS, "kind")
        _non_empty(label, "label")
        return self._create(
            "hosting", "hst",
            {"kind": kind, "label": label, "reference_stub": True,
             "status": "recorded_reference_only", "hosted_here": False},
            actor, "ext_hosting_record")

    def get_hosting(self, hosting_id, actor=None):
        """Return one hosting record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_hosting_read",
                         hosting_id)
        return self._fetch("hosting", hosting_id)

    def list_hosting(self, actor=None):
        """Return hosting records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_hosting_read")
        return self._list("hosting")

    # Kubernetes provisioning & cluster lifecycle engine.
    def register_cluster(self, name, actor, blueprint_ref=None):
        """Register a cluster record. Action: dataset_write.

        A registry record about a cluster an external platform
        provisions; this build provisions nothing
        (``provisioned_here`` is False).
        """
        self._guard(actor, "dataset_write", "ext_cluster_register")
        _non_empty(name, "cluster name")
        _string_or_none(blueprint_ref, "blueprint_ref")
        if blueprint_ref is not None:
            _non_empty(blueprint_ref, "blueprint_ref")
        return self._create(
            "cluster", "clu",
            {"name": name, "blueprint_ref": blueprint_ref,
             "reference_stub": True,
             "status": "recorded_reference_only",
             "provisioned_here": False},
            actor, "ext_cluster_register")

    def get_cluster(self, cluster_id, actor=None):
        """Return one cluster record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_cluster_read",
                         cluster_id)
        return self._fetch("cluster", cluster_id)

    def list_clusters(self, actor=None):
        """Return cluster records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_cluster_read")
        return self._list("cluster")

    def record_cluster_lifecycle(self, cluster_id, event, actor):
        """Record a cluster lifecycle event as reported externally.

        Action: dataset_write. The event label is the platform's
        own report; no lifecycle operation is performed here.
        """
        self._guard(actor, "dataset_write", "ext_cluster_lifecycle_record",
                    cluster_id)
        _one_of(event, KNOWN_CLUSTER_LIFECYCLE_EVENTS,
                CLUSTER_LIFECYCLE_EVENTS, "event")
        with self._lock:
            self._get("cluster", cluster_id)
            return self._create(
                "cluster_lifecycle", "clc",
                {"cluster_id": cluster_id, "event": event,
                 "reference_stub": True, "performed_here": False},
                actor, "ext_cluster_lifecycle_record")

    def list_cluster_lifecycle(self, cluster_id=None, actor=None):
        """Return cluster lifecycle records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read",
                         "ext_cluster_lifecycle_read", cluster_id)
        if cluster_id is not None:
            self._get("cluster", cluster_id)
        return self._list("cluster_lifecycle", cluster_id=cluster_id)

    # Managed file transfer transport.
    def record_file_transfer(self, dataset_id, source_id, actor,
                             record_count=0, checksum=None,
                             protocol="sftp"):
        """Record a managed file transfer. Action: ingest_record.

        Transfers are ingestion-shaped records (per the union
        spec). The record carries ``reference_transport: True``:
        it states that a transfer was reported over the named
        protocol; no file moves through this build
        (``moved_here`` is False).
        """
        self._guard(actor, "ingest_record", "ext_file_transfer_record",
                    dataset_id)
        _one_of(protocol, KNOWN_TRANSFER_PROTOCOLS,
                TRANSFER_PROTOCOLS, "protocol")
        _nonneg_int(record_count, "record_count")
        _string_or_none(checksum, "checksum")
        with self._lock:
            self._dataset(dataset_id)
            self.store.get_source(source_id)
            return self._create(
                "file_transfer", "trf",
                {"dataset_id": dataset_id, "source_id": source_id,
                 "protocol": protocol, "record_count": record_count,
                 "checksum": checksum,
                 "reference_transport": True,
                 "status": "recorded_reference_only",
                 "moved_here": False},
                actor, "ext_file_transfer_record")

    def get_file_transfer(self, transfer_id, actor=None):
        """Return one file transfer record. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_file_transfer_read",
                         transfer_id)
        return self._fetch("file_transfer", transfer_id)

    def list_file_transfers(self, dataset_id=None, actor=None):
        """Return file transfer records. Action: ingest_read."""
        self._guard_read(actor, "ingest_read", "ext_file_transfer_read",
                         dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("file_transfer", dataset_id=dataset_id)

    # AI/ML analytics & orchestration in bundled applications.
    def register_model(self, name, actor, dataset_id=None, technique=None):
        """Register an AI/ML model record. Action: dataset_write.

        A declaration record about a model an external application
        contains; this build trains and runs no model
        (``method`` is ``recorded_declaration_only``).
        """
        self._guard(actor, "dataset_write", "ext_model_register",
                    dataset_id)
        _non_empty(name, "model name")
        _string_or_none(technique, "technique")
        if technique is not None:
            _non_empty(technique, "technique")
        with self._lock:
            if dataset_id is not None:
                self._dataset(dataset_id)
            return self._create(
                "model", "mdl",
                {"name": name, "dataset_id": dataset_id,
                 "technique": technique, "reference_stub": True,
                 "status": "recorded_reference_only",
                 "method": "recorded_declaration_only",
                 "trained_here": False, "inference_here": False},
                actor, "ext_model_register")

    def get_model(self, model_id, actor=None):
        """Return one model record. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_model_read", model_id)
        return self._fetch("model", model_id)

    def list_models(self, dataset_id=None, actor=None):
        """Return model records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_model_read", dataset_id)
        if dataset_id is not None:
            self._dataset(dataset_id)
        return self._list("model", dataset_id=dataset_id)

    def record_orchestration(self, model_id, note, actor):
        """Record an orchestration step for a registered model.

        Action: dataset_write. A record about orchestration an
        external application performs; nothing is orchestrated
        here (``executed_here`` is False).
        """
        self._guard(actor, "dataset_write", "ext_orchestration_record",
                    model_id)
        _non_empty(note, "note")
        with self._lock:
            self._get("model", model_id)
            return self._create(
                "orchestration", "orc",
                {"model_id": model_id, "note": note,
                 "reference_stub": True, "executed_here": False},
                actor, "ext_orchestration_record")

    def list_orchestrations(self, model_id=None, actor=None):
        """Return orchestration records. Action: dataset_read."""
        self._guard_read(actor, "dataset_read", "ext_orchestration_read",
                         model_id)
        if model_id is not None:
            self._get("model", model_id)
        return self._list("orchestration", model_id=model_id)
