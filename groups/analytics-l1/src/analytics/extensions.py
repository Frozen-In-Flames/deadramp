"""Final GAPS batch extensions for the Analytics L1 merged build.

Clean-room, standard-library-only records extensions for the 8
Extended families the union spec ranked but the core did not
implement: 4 built as in-substrate records plus deterministic
derivations over the core's own datasets (collaboration, archiving,
transformation, text/NLP in the request-records form this tier's
brief prescribes), 4 shipped as labeled reference implementations
(real-time/streaming, proprietary-source connectors, predictive ML,
alerts/monitoring). See ``BATCH.md`` in the group directory for the
per-entry disposition.

Design, following the core's doctrines and the Analytics L2 batch
unit's adjudicated forms where this tier's spec supports them:

- This module wraps the core :class:`DatasetStore`; the core modules
  are untouched (byte-identical). Dataset existence, rows, queries,
  and descriptive statistics are always read through the core's
  public API (``get`` / ``rows`` / ``run_query`` / ``describe``),
  never re-implemented.
- RBAC goes through :mod:`analytics.access` exactly as the core
  enforces it: each operation maps onto an existing core action
  (record creation/registration -> ``ingest``; derivations and views
  -> ``query``), checked *before* any state change or id allocation
  for User-like actors; denied attempts are recorded on the core
  audit log with the extension action name suffixed ``:denied``, and
  every successful mutation as ``ext_<action>``. Plain-string actors
  carry identity but no role, mirroring the core convention.
- Derived values are derived at read and never stored: workspace
  member/share/annotation counts, archive status, transform run
  rollups, text-analysis rollups, and every reference-surface rollup.
  Stored records carry no derived key; tests pin that.
- The baseline is fresh for L1: the Low union, audit on the FedRAMP
  Low side only. No Moderate/High apparatus is imported downward.
- Nothing here learns, streams, connects, monitors, evaluates alert
  rules, or executes against an external system. The four
  stub-engine families ship as labeled reference implementations:
  every record they create carries ``reference_stub: True``.
"""

import copy
import hashlib
import json
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .query import describe, run_query


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


# -- vocabularies -----------------------------------------------------

WORKSPACE_MEMBER_ROLES = ("editor", "viewer")
KNOWN_WORKSPACE_MEMBER_ROLES = frozenset(WORKSPACE_MEMBER_ROLES)

ANNOTATION_TARGET_KINDS = ("dataset", "report")
KNOWN_ANNOTATION_TARGET_KINDS = frozenset(ANNOTATION_TARGET_KINDS)

ARCHIVE_TARGET_KINDS = ("dataset", "report")
KNOWN_ARCHIVE_TARGET_KINDS = frozenset(ARCHIVE_TARGET_KINDS)

TEXT_ANALYSIS_KINDS = ("sentiment", "topics", "keywords", "entities",
                       "summary", "classification")
KNOWN_TEXT_ANALYSIS_KINDS = frozenset(TEXT_ANALYSIS_KINDS)

MODEL_KINDS = ("regression", "classification", "forecasting", "clustering")
KNOWN_MODEL_KINDS = frozenset(MODEL_KINDS)

ALERT_OPS = ("lt", "le", "gt", "ge", "eq", "ne")
KNOWN_ALERT_OPS = frozenset(ALERT_OPS)
DESCRIBE_STATISTICS = ("count", "mean", "median", "min", "max", "stddev")
REPORTED_ALERT_STATUSES = ("triggered", "cleared", "acknowledged")
KNOWN_REPORTED_ALERT_STATUSES = frozenset(REPORTED_ALERT_STATUSES)

CONNECTOR_KINDS = ("database", "warehouse", "crm", "erp", "api", "file_server")
KNOWN_CONNECTOR_KINDS = frozenset(CONNECTOR_KINDS)


# -- shared validators ---------------------------------------------------


def _require_text(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_choice(value, known, what):
    if value not in known:
        raise ValidationError(
            "unknown %s: %r (expected one of %s)"
            % (what, value, ", ".join(sorted(known)))
        )
    return value


def _validate_number(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("%s must be a number" % (what,))
    return value


def _validate_count(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


class AnalyticsExtensions:
    """Records extension surface over a core DatasetStore (L1)."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.RLock()
        self._counters = {}
        self._workspaces = {}
        self._workspace_members = {}
        self._shares = {}
        self._annotations = {}
        self._archives = {}
        self._transforms = {}
        self._transform_runs = {}
        self._text_requests = {}
        self._text_results = {}
        self._streams = {}
        self._stream_reports = {}
        self._connectors = {}
        self._connector_syncs = {}
        self._models = {}
        self._prediction_requests = {}
        self._prediction_results = {}
        self._alert_rules = {}
        self._reported_alerts = {}

    # -- plumbing ------------------------------------------------------

    @property
    def _audit(self):
        return getattr(self.store, "audit", None)

    def _record(self, actor, action, target, details=None):
        audit = self._audit
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, ext_action, target=None):
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._record(actor, ext_action + ":denied", target)
                raise

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _dataset(self, dataset_id):
        return self.store.get(dataset_id)

    @staticmethod
    def _get(collection, record_id, what):
        record = collection.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return copy.deepcopy(record)

    # -- Collaboration (shared workspaces + annotations) ----------------

    def create_workspace(self, name, actor):
        """Create a shared workspace record around analytics artifacts.

        Sharing here is the records sense: membership and share
        records over core datasets. No live co-editing is claimed.
        """
        self._guard(actor, "ingest", "ext_create_workspace")
        _require_text(name, "workspace name")
        with self._lock:
            workspace_id = self._next_id("ws")
            record = {
                "id": workspace_id,
                "name": name,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workspaces[workspace_id] = record
            self._record(actor, "ext_create_workspace", workspace_id,
                         details={"name": name})
            return copy.deepcopy(record)

    def add_workspace_member(self, workspace_id, member_ref, member_role, actor):
        """Record membership of an opaque member ref in a workspace."""
        self._guard(actor, "ingest", "ext_add_workspace_member", workspace_id)
        self._get(self._workspaces, workspace_id, "workspace")
        _require_text(member_ref, "member ref")
        _validate_choice(member_role, KNOWN_WORKSPACE_MEMBER_ROLES,
                         "workspace member role")
        with self._lock:
            member_id = self._next_id("wsm")
            record = {
                "id": member_id,
                "workspace_id": workspace_id,
                "member_ref": member_ref,
                "role": member_role,
                "added_by": actor_name(actor),
                "added_utc": _utc_now(),
            }
            self._workspace_members[member_id] = record
            self._record(actor, "ext_add_workspace_member", workspace_id,
                         details={"member_ref": member_ref})
            return copy.deepcopy(record)

    def share_dataset(self, workspace_id, dataset_id, actor):
        """Record that a core dataset is shared into a workspace."""
        self._guard(actor, "ingest", "ext_share_dataset", workspace_id)
        self._get(self._workspaces, workspace_id, "workspace")
        self._dataset(dataset_id)
        with self._lock:
            share_id = self._next_id("shr")
            record = {
                "id": share_id,
                "workspace_id": workspace_id,
                "target_kind": "dataset",
                "target_ref": dataset_id,
                "shared_by": actor_name(actor),
                "shared_utc": _utc_now(),
            }
            self._shares[share_id] = record
            self._record(actor, "ext_share_dataset", workspace_id,
                         details={"target_ref": dataset_id})
            return copy.deepcopy(record)

    def add_annotation(self, target_kind, target_ref, text, actor):
        """Record an annotation over a core dataset or a report ref.

        The annotation text is the record's content, recorded
        verbatim. A ``report`` target is an opaque ref: report
        content is generated by the core reports surface and is not
        held here.
        """
        self._guard(actor, "ingest", "ext_add_annotation")
        _validate_choice(target_kind, KNOWN_ANNOTATION_TARGET_KINDS,
                         "annotation target kind")
        _require_text(target_ref, "annotation target ref")
        _require_text(text, "annotation text")
        if target_kind == "dataset":
            self._dataset(target_ref)
        with self._lock:
            annotation_id = self._next_id("ann")
            record = {
                "id": annotation_id,
                "target_kind": target_kind,
                "target_ref": target_ref,
                "text": text,
                "annotated_by": actor_name(actor),
                "annotated_utc": _utc_now(),
            }
            self._annotations[annotation_id] = record
            self._record(actor, "ext_add_annotation", annotation_id,
                         details={"target_kind": target_kind,
                                  "target_ref": target_ref})
            return copy.deepcopy(record)

    def workspace_view(self, workspace_id, actor):
        """Workspace record plus counts derived at read."""
        self._guard(actor, "query", "ext_workspace_view", workspace_id)
        record = self._get(self._workspaces, workspace_id, "workspace")
        with self._lock:
            members = [copy.deepcopy(m) for m in self._workspace_members.values()
                       if m["workspace_id"] == workspace_id]
            shares = [copy.deepcopy(s) for s in self._shares.values()
                      if s["workspace_id"] == workspace_id]
        record["members"] = members
        record["member_count"] = len(members)
        record["shares"] = shares
        record["share_count"] = len(shares)
        return record

    def annotations_for(self, target_ref, actor):
        """Annotations recorded over one target, in recording order."""
        self._guard(actor, "query", "ext_annotations_for")
        _require_text(target_ref, "annotation target ref")
        with self._lock:
            records = [copy.deepcopy(a) for a in self._annotations.values()
                       if a["target_ref"] == target_ref]
        return {"target_ref": target_ref, "annotations": records,
                "annotation_count": len(records)}

    # -- Archiving --------------------------------------------------------

    @staticmethod
    def _dataset_checksum(rows):
        canonical = json.dumps(rows, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def create_archive_record(self, target_kind, target_ref, actor, reason=None):
        """Record that an artifact is archived. Nothing is deleted.

        For a dataset target the record carries a SHA-256 checksum
        computed at archive time over the core rows (metadata about
        the archived content; the content itself stays in the core,
        byte-for-byte). A ``report`` target is an opaque ref and
        carries no checksum. Retention-period enforcement and
        eventual disposition are the embedding organization's
        records schedule at the deployment layer
        (PLATFORM-LAYER.md decision 4).
        """
        self._guard(actor, "ingest", "ext_create_archive_record")
        _validate_choice(target_kind, KNOWN_ARCHIVE_TARGET_KINDS,
                         "archive target kind")
        _require_text(target_ref, "archive target ref")
        if reason is not None:
            _require_text(reason, "archive reason")
        checksum = None
        if target_kind == "dataset":
            self._dataset(target_ref)
            checksum = self._dataset_checksum(self.store.rows(target_ref))
        with self._lock:
            archive_id = self._next_id("arc")
            record = {
                "id": archive_id,
                "target_kind": target_kind,
                "target_ref": target_ref,
                "reason": reason,
                "checksum": checksum,
                "disposition": "record_only",
                "retention_execution": "embedding_organization",
                "archived_by": actor_name(actor),
                "archived_utc": _utc_now(),
            }
            self._archives[archive_id] = record
            self._record(actor, "ext_create_archive_record", archive_id,
                         details={"target_kind": target_kind,
                                  "target_ref": target_ref})
            return copy.deepcopy(record)

    def archive_status(self, target_ref, actor):
        """Whether an artifact has archive records, derived at read."""
        self._guard(actor, "query", "ext_archive_status")
        _require_text(target_ref, "archive target ref")
        with self._lock:
            records = [copy.deepcopy(a) for a in self._archives.values()
                       if a["target_ref"] == target_ref]
        return {
            "target_ref": target_ref,
            "archived": bool(records),
            "archive_count": len(records),
            "latest_archive_id": records[-1]["id"] if records else None,
            "latest_checksum": records[-1]["checksum"] if records else None,
        }

    # -- Transformation (definitions as data, runs over the core) ---------

    def create_transform(self, name, dataset_id, query, actor):
        """Record a transformation definition over a core dataset.

        A definition is a named core query held as data, validated
        by executing it once through the core query surface at
        creation (the same discipline as the L2 saved-view form).
        Running it derives its output through the core's existing
        deterministic query/aggregation machinery; no transform
        engine is invented here.
        """
        self._guard(actor, "ingest", "ext_create_transform", dataset_id)
        _require_text(name, "transform name")
        self._dataset(dataset_id)
        if not isinstance(query, dict):
            raise ValidationError("transform query must be an object")
        run_query(self.store, dataset_id, copy.deepcopy(query), actor)
        with self._lock:
            transform_id = self._next_id("tr")
            record = {
                "id": transform_id,
                "name": name,
                "dataset_id": dataset_id,
                "query": copy.deepcopy(query),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._transforms[transform_id] = record
            self._record(actor, "ext_create_transform", transform_id,
                         details={"dataset_id": dataset_id})
            return copy.deepcopy(record)

    @staticmethod
    def _derive_rows_out(result, rows_in):
        """Output row count of a transform run, from the core result.

        The batch's fresh negative-control seam: a run record whose
        rows_out merely echoes rows_in is the mutant the drill
        rejects -- the count must come from the derived result.
        """
        return result["row_count"]

    def run_transform(self, transform_id, actor):
        """Run a transformation definition through the core machinery.

        Returns the derived result and stores a run *record*
        (counts and method only -- the derived rows are not stored).
        """
        self._guard(actor, "query", "ext_run_transform", transform_id)
        record = self._get(self._transforms, transform_id, "transform")
        dataset = self._dataset(record["dataset_id"])
        rows_in = dataset["row_count"]
        result = run_query(self.store, record["dataset_id"],
                           copy.deepcopy(record["query"]), actor)
        rows_out = self._derive_rows_out(result, rows_in)
        with self._lock:
            run_id = self._next_id("trr")
            run = {
                "id": run_id,
                "transform_id": transform_id,
                "dataset_id": record["dataset_id"],
                "rows_in": rows_in,
                "rows_out": rows_out,
                "method": "core_query_derivation",
                "executed_here": True,
                "reported": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._transform_runs[run_id] = run
            self._record(actor, "ext_run_transform", transform_id,
                         details={"rows_out": rows_out})
        out = dict(result)
        out["transform_id"] = transform_id
        out["run_id"] = run_id
        out["method"] = "core_query_derivation"
        return out

    def record_reported_transform_run(self, transform_id, rows_in, rows_out,
                                      actor, note=None):
        """Record a transform run performed outside this build.

        The counts are recorded verbatim as reported; the build
        derives nothing for it (``executed_here`` is False).
        """
        self._guard(actor, "ingest", "ext_record_transform_run", transform_id)
        record = self._get(self._transforms, transform_id, "transform")
        _validate_count(rows_in, "rows_in")
        _validate_count(rows_out, "rows_out")
        if note is not None:
            _require_text(note, "run note")
        with self._lock:
            run_id = self._next_id("trr")
            run = {
                "id": run_id,
                "transform_id": transform_id,
                "dataset_id": record["dataset_id"],
                "rows_in": rows_in,
                "rows_out": rows_out,
                "method": "reported",
                "executed_here": False,
                "reported": True,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._transform_runs[run_id] = run
            self._record(actor, "ext_record_transform_run", transform_id,
                         details={"rows_out": rows_out})
            return copy.deepcopy(run)

    def transform_view(self, transform_id, actor):
        """Transform definition plus run rollup derived at read."""
        self._guard(actor, "query", "ext_transform_view", transform_id)
        record = self._get(self._transforms, transform_id, "transform")
        with self._lock:
            runs = [copy.deepcopy(r) for r in self._transform_runs.values()
                    if r["transform_id"] == transform_id]
        record["runs"] = runs
        record["run_count"] = len(runs)
        return record

    # -- Text / NLP (request records; nothing is analyzed here) ------------

    def create_text_analysis_request(self, dataset_id, column, analysis_kind,
                                     actor):
        """Record a text-analysis request over a core dataset column.

        A request record only: no text is analyzed here, and no text
        content is stored beyond what the core dataset already
        holds. Results arrive as separate records (opaque result
        refs or verbatim reported labels).
        """
        self._guard(actor, "ingest", "ext_create_text_analysis_request",
                    dataset_id)
        dataset = self._dataset(dataset_id)
        if column not in dataset["columns"]:
            raise ValidationError("unknown column: %r" % (column,))
        _validate_choice(analysis_kind, KNOWN_TEXT_ANALYSIS_KINDS,
                         "text analysis kind")
        with self._lock:
            request_id = self._next_id("txr")
            record = {
                "id": request_id,
                "dataset_id": dataset_id,
                "column": column,
                "analysis_kind": analysis_kind,
                "analyzed_here": False,
                "requested_by": actor_name(actor),
                "requested_utc": _utc_now(),
            }
            self._text_requests[request_id] = record
            self._record(actor, "ext_create_text_analysis_request", request_id,
                         details={"dataset_id": dataset_id,
                                  "analysis_kind": analysis_kind})
            return copy.deepcopy(record)

    def record_text_analysis_result(self, request_id, actor, result_ref=None,
                                    reported_labels=None):
        """Record a text-analysis result as reported from outside.

        The result is held as an opaque ``result_ref`` and/or as
        verbatim reported labels; no result content is stored and
        nothing was analyzed here.
        """
        self._guard(actor, "ingest", "ext_record_text_analysis_result",
                    request_id)
        self._get(self._text_requests, request_id, "text analysis request")
        if result_ref is None and reported_labels is None:
            raise ValidationError(
                "a result needs a result_ref or reported labels")
        if result_ref is not None:
            _require_text(result_ref, "result ref")
        labels = None
        if reported_labels is not None:
            if (not isinstance(reported_labels, list) or not reported_labels
                    or any(not isinstance(x, str) or not x.strip()
                           for x in reported_labels)):
                raise ValidationError(
                    "reported labels must be a non-empty list of strings")
            labels = list(reported_labels)
        with self._lock:
            result_id = self._next_id("txres")
            record = {
                "id": result_id,
                "request_id": request_id,
                "result_ref": result_ref,
                "reported_labels": labels,
                "analyzed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._text_results[result_id] = record
            self._record(actor, "ext_record_text_analysis_result", request_id)
            return copy.deepcopy(record)

    def text_analysis_view(self, request_id, actor):
        """Text-analysis request plus result rollup derived at read."""
        self._guard(actor, "query", "ext_text_analysis_view", request_id)
        record = self._get(self._text_requests, request_id,
                           "text analysis request")
        with self._lock:
            results = [copy.deepcopy(r) for r in self._text_results.values()
                       if r["request_id"] == request_id]
        record["results"] = results
        record["result_count"] = len(results)
        return record

    # -- Real-time / streaming (reference implementation) -------------------

    def register_stream_reference(self, name, source_ref, actor):
        """Register a stream-source definition as a reference record.

        Reference implementation only: nothing ingests in real time
        and no stream is opened (``streamed_here`` is False).
        """
        self._guard(actor, "ingest", "ext_register_stream_reference")
        _require_text(name, "stream name")
        _require_text(source_ref, "stream source ref")
        with self._lock:
            stream_id = self._next_id("stm")
            record = {
                "id": stream_id,
                "name": name,
                "source_ref": source_ref,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "streamed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._streams[stream_id] = record
            self._record(actor, "ext_register_stream_reference", stream_id)
            return copy.deepcopy(record)

    def record_stream_event_report(self, stream_id, reported_event_count,
                                   actor):
        """Record a stream event count as reported; nothing ingested."""
        self._guard(actor, "ingest", "ext_record_stream_event_report",
                    stream_id)
        self._get(self._streams, stream_id, "stream reference")
        _validate_count(reported_event_count, "reported_event_count")
        with self._lock:
            report_id = self._next_id("stmr")
            record = {
                "id": report_id,
                "stream_id": stream_id,
                "reported_event_count": reported_event_count,
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "streamed_here": False,
                "ingested_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._stream_reports[report_id] = record
            self._record(actor, "ext_record_stream_event_report", stream_id,
                         details={"reported_event_count":
                                  reported_event_count})
            return copy.deepcopy(record)

    def stream_view(self, stream_id, actor):
        """Stream reference plus reported event rollup, derived."""
        self._guard(actor, "query", "ext_stream_view", stream_id)
        record = self._get(self._streams, stream_id, "stream reference")
        with self._lock:
            reports = [copy.deepcopy(r) for r in self._stream_reports.values()
                       if r["stream_id"] == stream_id]
        record["reports"] = reports
        record["report_count"] = len(reports)
        record["reported_events_total"] = sum(
            r["reported_event_count"] for r in reports)
        return record

    # -- Proprietary-source connectors (reference implementation) -----------

    def register_connector_reference(self, name, source_kind, actor):
        """Register a proprietary-source connector definition.

        Reference implementation only: nothing connects and nothing
        syncs (``connected_here`` / ``synced_here`` are False). The
        core's open CSV/JSON ingest coverage is unchanged.
        """
        self._guard(actor, "ingest", "ext_register_connector_reference")
        _require_text(name, "connector name")
        _validate_choice(source_kind, KNOWN_CONNECTOR_KINDS, "connector kind")
        with self._lock:
            connector_id = self._next_id("con")
            record = {
                "id": connector_id,
                "name": name,
                "source_kind": source_kind,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "connected_here": False,
                "synced_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connectors[connector_id] = record
            self._record(actor, "ext_register_connector_reference", connector_id,
                         details={"source_kind": source_kind})
            return copy.deepcopy(record)

    def record_connector_sync_reference(self, connector_id, reported_rows,
                                        actor, outcome=None):
        """Record a connector sync as reported; nothing is ingested.

        The outcome label, when given, is recorded verbatim.
        """
        self._guard(actor, "ingest", "ext_record_connector_sync_reference",
                    connector_id)
        self._get(self._connectors, connector_id, "connector reference")
        _validate_count(reported_rows, "reported_rows")
        if outcome is not None:
            _require_text(outcome, "sync outcome")
        with self._lock:
            sync_id = self._next_id("cons")
            record = {
                "id": sync_id,
                "connector_id": connector_id,
                "reported_rows": reported_rows,
                "outcome": outcome,
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "connected_here": False,
                "synced_here": False,
                "ingested_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._connector_syncs[sync_id] = record
            self._record(actor, "ext_record_connector_sync_reference",
                         connector_id,
                         details={"reported_rows": reported_rows})
            return copy.deepcopy(record)

    def connector_view(self, connector_id, actor):
        """Connector reference plus reported sync rollup, derived."""
        self._guard(actor, "query", "ext_connector_view", connector_id)
        record = self._get(self._connectors, connector_id,
                           "connector reference")
        with self._lock:
            syncs = [copy.deepcopy(s) for s in self._connector_syncs.values()
                     if s["connector_id"] == connector_id]
        record["syncs"] = syncs
        record["sync_count"] = len(syncs)
        record["reported_rows_total"] = sum(s["reported_rows"] for s in syncs)
        return record

    # -- Predictive ML (reference implementation) ----------------------------

    def register_model_reference(self, name, model_kind, actor, dataset_id=None):
        """Register a predictive-model definition as a reference record.

        Reference implementation only: nothing is trained and no
        inference runs here (``trained_here`` / ``predicted_here`` /
        ``inference_here`` are False). The descriptive statistics
        the core already computes are not relabeled as ML. There is
        deliberately no train or predict method on this surface.
        """
        self._guard(actor, "ingest", "ext_register_model_reference")
        _require_text(name, "model name")
        _validate_choice(model_kind, KNOWN_MODEL_KINDS, "model kind")
        if dataset_id is not None:
            self._dataset(dataset_id)
        with self._lock:
            model_id = self._next_id("mdl")
            record = {
                "id": model_id,
                "name": name,
                "model_kind": model_kind,
                "dataset_id": dataset_id,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "trained_here": False,
                "predicted_here": False,
                "inference_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._models[model_id] = record
            self._record(actor, "ext_register_model_reference", model_id,
                         details={"model_kind": model_kind})
            return copy.deepcopy(record)

    def record_prediction_request(self, model_id, actor, dataset_id=None):
        """Record a prediction request against a model reference."""
        self._guard(actor, "ingest", "ext_record_prediction_request", model_id)
        self._get(self._models, model_id, "model reference")
        if dataset_id is not None:
            self._dataset(dataset_id)
        with self._lock:
            request_id = self._next_id("pred")
            record = {
                "id": request_id,
                "model_id": model_id,
                "dataset_id": dataset_id,
                "reference_stub": True,
                "predicted_here": False,
                "inference_here": False,
                "requested_by": actor_name(actor),
                "requested_utc": _utc_now(),
            }
            self._prediction_requests[request_id] = record
            self._record(actor, "ext_record_prediction_request", model_id)
            return copy.deepcopy(record)

    def record_prediction_result_reference(self, request_id, result_ref, actor):
        """Record a prediction result as an opaque ref, as reported."""
        self._guard(actor, "ingest", "ext_record_prediction_result_reference",
                    request_id)
        self._get(self._prediction_requests, request_id, "prediction request")
        _require_text(result_ref, "result ref")
        with self._lock:
            result_id = self._next_id("predr")
            record = {
                "id": result_id,
                "request_id": request_id,
                "result_ref": result_ref,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "predicted_here": False,
                "inference_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._prediction_results[result_id] = record
            self._record(actor, "ext_record_prediction_result_reference",
                         request_id)
            return copy.deepcopy(record)

    def model_view(self, model_id, actor):
        """Model reference plus request/result rollup, derived."""
        self._guard(actor, "query", "ext_model_view", model_id)
        record = self._get(self._models, model_id, "model reference")
        with self._lock:
            requests = [copy.deepcopy(r)
                        for r in self._prediction_requests.values()
                        if r["model_id"] == model_id]
            request_ids = {r["id"] for r in requests}
            results = [copy.deepcopy(r)
                       for r in self._prediction_results.values()
                       if r["request_id"] in request_ids]
        record["requests"] = requests
        record["request_count"] = len(requests)
        record["results"] = results
        record["result_count"] = len(results)
        return record

    # -- Alerts / monitoring (reference implementation) -----------------------

    def create_alert_rule(self, name, dataset_id, column, statistic, op,
                          threshold, actor):
        """Record an alert-rule definition over a core statistic.

        Reference implementation only: the registry never evaluates
        or fires (``monitored_here`` / ``evaluated_here`` /
        ``fired_here`` are False). There is deliberately no evaluate
        method on this surface; alert occurrences arrive as reported
        records.
        """
        self._guard(actor, "ingest", "ext_create_alert_rule", dataset_id)
        _require_text(name, "alert rule name")
        dataset = self._dataset(dataset_id)
        if column not in dataset["columns"]:
            raise ValidationError("alert column is not a column: %r" % (column,))
        if statistic not in DESCRIBE_STATISTICS:
            raise ValidationError("unknown alert statistic: %r" % (statistic,))
        _validate_choice(op, KNOWN_ALERT_OPS, "alert operator")
        _validate_number(threshold, "alert threshold")
        with self._lock:
            rule_id = self._next_id("alr")
            record = {
                "id": rule_id,
                "name": name,
                "dataset_id": dataset_id,
                "column": column,
                "statistic": statistic,
                "op": op,
                "threshold": threshold,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "monitored_here": False,
                "evaluated_here": False,
                "fired_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._alert_rules[rule_id] = record
            self._record(actor, "ext_create_alert_rule", rule_id,
                         details={"dataset_id": dataset_id})
            return copy.deepcopy(record)

    def record_reported_alert(self, rule_id, reported_status, actor, note=None):
        """Record an alert occurrence as reported from outside.

        The status is recorded verbatim from the fixed reported
        vocabulary; the build fired nothing.
        """
        self._guard(actor, "ingest", "ext_record_reported_alert", rule_id)
        self._get(self._alert_rules, rule_id, "alert rule")
        _validate_choice(reported_status, KNOWN_REPORTED_ALERT_STATUSES,
                         "reported alert status")
        if note is not None:
            _require_text(note, "alert note")
        with self._lock:
            alert_id = self._next_id("alrt")
            record = {
                "id": alert_id,
                "rule_id": rule_id,
                "reported_status": reported_status,
                "note": note,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "monitored_here": False,
                "fired_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._reported_alerts[alert_id] = record
            self._record(actor, "ext_record_reported_alert", rule_id,
                         details={"reported_status": reported_status})
            return copy.deepcopy(record)

    def alert_rule_view(self, rule_id, actor):
        """Alert rule plus reported-alert rollup derived at read."""
        self._guard(actor, "query", "ext_alert_rule_view", rule_id)
        record = self._get(self._alert_rules, rule_id, "alert rule")
        with self._lock:
            alerts = [copy.deepcopy(a) for a in self._reported_alerts.values()
                      if a["rule_id"] == rule_id]
        by_status = {}
        for alert in alerts:
            by_status[alert["reported_status"]] = \
                by_status.get(alert["reported_status"], 0) + 1
        record["reported_alerts"] = alerts
        record["reported_alert_count"] = len(alerts)
        record["alerts_by_status"] = by_status
        record["last_reported_status"] = \
            alerts[-1]["reported_status"] if alerts else None
        return record
