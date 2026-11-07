"""Final GAPS batch extensions for the Analytics L3-adjacent build.

Clean-room, standard-library-only reference records for the three
Extended entries the final GAPS batch registered against this group
(GAPS.md, "Group 3 — Analytics L3-adjacent (54 forks)"): alerts,
monitoring & detection; the predictive ML remainder; and the bundled
line carrying the remaining twelve Extended families. All three were
drafted ``stub-engine`` in ``gaps-batch/inventory.json`` and ship as
labeled reference implementations: records only, never execution.
See ``BATCH.md`` in the group directory for the per-entry
disposition.

Design, following the core's doctrines and the High baseline:

- This module is a wrapper around :class:`DatasetStore`; the core
  modules are untouched (byte-identical). Dataset existence and
  descriptive statistics are read through the core's public API
  (``get`` / ``describe``), never re-implemented.
- RBAC goes through :mod:`analytics.access` exactly as the core
  enforces it: the extension maps each operation onto an existing
  core action (the core action set is fixed), checks it *before* any
  state change or id allocation for User-like actors, and records
  denied attempts on the core audit log with the extension action
  name suffixed ``:denied``. Plain-string actors carry identity but
  no role, mirroring the core convention. Mapping: record
  creation/registration -> ``ingest``; evaluations and views ->
  ``query``. The High-baseline ``auditor`` role holds ``audit_read``
  only, so it is denied every operation on this surface, mutations
  and views alike; its audit-review duty runs on the core audit log
  itself and is untouched by this module.
- Mutations are **fail closed (AU-5)**, mirroring the core store's
  ingest rollback: the record is inserted and the audit entry is
  written on the core hash-chained log; if that write raises, the
  insert and the id allocation are rolled back and the error
  propagates — an extension operation whose audit write fails does
  not proceed.
- Derived values (evaluation rollups, run counts, per-family
  report/receipt counts, reported-row totals) are derived at read
  and never stored; stored records carry no derived key, and tests
  pin that. Reported figures are stored verbatim as reported and
  are never computed here; totals over reported row counts are
  sums of *reported* values and are named as such.
- Nothing here learns, predicts, monitors, streams, connects, or
  executes against an external system. Every record the surface
  creates carries ``reference_stub: True``; there is deliberately
  no train, predict, monitor, watch, connect, or execute method
  on this surface.
"""

import copy
import math
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .query import _compare, describe


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


# -- vocabularies -----------------------------------------------------

DESCRIBE_STATISTICS = ("count", "mean", "median", "min", "max", "stddev")

ALERT_OPS = ("lt", "le", "gt", "ge", "eq", "ne")
KNOWN_ALERT_OPS = frozenset(ALERT_OPS)

MODEL_KINDS = ("regression", "classification", "forecasting", "clustering")
KNOWN_MODEL_KINDS = frozenset(MODEL_KINDS)

# The twelve Extended families carried by the bundled GAPS entry
# (idx 25), with the sibling counts the entry's own text records.
# The counts are recorded data from the entry text, not a new
# measurement; the KPI family's recorded zero stands as recorded.
EXTENDED_FAMILY_CLAIM_COUNTS = {
    "real_time_streaming": 18,
    "collaboration": 17,
    "proprietary_connectors": 17,
    "governance": 11,
    "transformation": 10,
    "text_nlp": 6,
    "archiving": 4,
    "scheduling": 3,
    "geospatial": 3,
    "media_analytics": 2,
    "self_service_bi": 2,
    "kpi": 0,
}
EXTENDED_FAMILIES = tuple(EXTENDED_FAMILY_CLAIM_COUNTS)
KNOWN_EXTENDED_FAMILIES = frozenset(EXTENDED_FAMILIES)

STREAMING_FAMILY = "real_time_streaming"
CONNECTORS_FAMILY = "proprietary_connectors"


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
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError("%s must be finite" % (what,))
    return value


def _validate_count(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _validate_reported_figures(figures, what="reported_figures"):
    """Validate figures reported by an external system.

    Figures are held verbatim as reported; they are never computed
    here. ``None`` stays ``None``; otherwise the value must be an
    object mapping non-empty names to finite numbers (bools are not
    numbers). Returns a deep copy.
    """
    if figures is None:
        return None
    if not isinstance(figures, dict):
        raise ValidationError("%s must be an object" % (what,))
    for key, value in figures.items():
        _require_text(key, "%s key" % (what,))
        _validate_number(value, "%s[%r]" % (what, key))
    return copy.deepcopy(figures)


class AnalyticsExtensions:
    """Reference-records extension surface over a core DatasetStore."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.RLock()
        self._counters = {}
        self._alert_rules = {}
        self._alert_evaluations = {}
        self._models = {}
        self._model_runs = {}
        self._family_refs = {}
        self._family_ref_ids_by_family = {}
        self._family_reports = {}
        self._stream_batches = {}
        self._connector_syncs = {}

    # -- plumbing ------------------------------------------------------

    @property
    def _audit(self):
        return getattr(self.store, "audit", None)

    def _record(self, actor, action, target, details=None):
        audit = self._audit
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, ext_action, target=None):
        """Enforce RBAC for User-like actors, auditing denials.

        Mirrors the core store's convention: plain-string actors
        carry identity but no role, so there is nothing to enforce
        against; User-like actors are checked through the core
        permission matrix before any state change or id allocation.
        """
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._record(actor, ext_action + ":denied", target)
                raise

    def _next_id(self, prefix):
        """Allocate the next sequential id. Call only after validation."""
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _commit(self, collection, prefix, fields, actor, ext_action,
                target=None, details=None):
        """Insert a record and audit it, fail closed (AU-5).

        The id is allocated and the record inserted, then the audit
        entry is written on the core hash-chained log. If that write
        raises, the insert and the id allocation are rolled back and
        the error propagates — an extension operation whose audit
        write fails does not proceed, mirroring the core store's
        ingest rollback.
        """
        with self._lock:
            record_id = self._next_id(prefix)
            record = {"id": record_id}
            record.update(fields)
            collection[record_id] = record
            try:
                self._record(actor, ext_action,
                             record_id if target is None else target,
                             details=details)
            except Exception:
                del collection[record_id]
                self._counters[prefix] -= 1
                raise
            return copy.deepcopy(record)

    def _dataset(self, dataset_id):
        """Return the core dataset dict, raising NotFoundError."""
        return self.store.get(dataset_id)

    @staticmethod
    def _get(collection, record_id, what):
        record = collection.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return copy.deepcopy(record)

    @staticmethod
    def _sum_reported_counts(counts):
        """Sum of reported row counts, as reported.

        The total is a sum of values *reported* by external systems
        and recorded on receipts; nothing was ingested or measured
        here. This is the negative control's seam (see
        tests/test_gaps_batch.py).
        """
        return sum(counts)

    # -- Alerts, monitoring & detection (reference implementation) ------
    # GAPS idx 23: "Alerts, monitoring & detection (27 of 54 forks
    # claim it; kept Extended because each claimant binds alerting to
    # its own domain telemetry — reasoning in the group spec)".

    def create_alert_rule(self, name, dataset_id, column, statistic, op,
                          threshold, actor):
        """Record an alert rule over a core descriptive statistic.

        Reference implementation only: nothing monitors anything.
        A rule is a record; the only evaluation that exists is a
        point-in-time recorded receipt (record_alert_evaluation).
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
        fields = {
            "name": name,
            "dataset_id": dataset_id,
            "column": column,
            "statistic": statistic,
            "op": op,
            "threshold": threshold,
            "reference_stub": True,
            "state": "recorded_reference_only",
            "monitoring_here": False,
            "created_by": actor_name(actor),
            "created_utc": _utc_now(),
        }
        return self._commit(self._alert_rules, "alr", fields, actor,
                            "ext_create_alert_rule",
                            details={"dataset_id": dataset_id})

    def record_alert_evaluation(self, rule_id, actor):
        """Evaluate a rule once, now, and record the receipt.

        The evaluation is a deterministic comparison of the core
        ``describe`` statistic against the recorded threshold at
        this moment. It is a receipt, not monitoring: no watcher
        exists and nothing fires later.
        """
        self._guard(actor, "query", "ext_record_alert_evaluation", rule_id)
        rule = self._get(self._alert_rules, rule_id, "alert rule")
        stats = describe(self.store, rule["dataset_id"], rule["column"], actor)
        value = stats[rule["statistic"]]
        breached = bool(_compare(value, rule["op"], rule["threshold"]))
        fields = {
            "rule_id": rule_id,
            "statistic": rule["statistic"],
            "value": value,
            "op": rule["op"],
            "threshold": rule["threshold"],
            "breached": breached,
            "reference_stub": True,
            "method": "recorded_evaluation_over_core_describe",
            "monitoring_here": False,
            "evaluated_by": actor_name(actor),
            "evaluated_utc": _utc_now(),
        }
        return self._commit(self._alert_evaluations, "ale", fields, actor,
                            "ext_record_alert_evaluation", target=rule_id,
                            details={"breached": breached})

    def alert_rule_view(self, rule_id, actor):
        """Alert rule plus evaluation rollup derived at read."""
        self._guard(actor, "query", "ext_alert_rule_view", rule_id)
        record = self._get(self._alert_rules, rule_id, "alert rule")
        with self._lock:
            evaluations = [copy.deepcopy(e)
                           for e in self._alert_evaluations.values()
                           if e["rule_id"] == rule_id]
        record["evaluations"] = evaluations
        record["evaluation_count"] = len(evaluations)
        record["last_breached"] = evaluations[-1]["breached"] if evaluations else None
        return record

    # -- Predictive ML remainder (reference implementation) -------------
    # GAPS idx 24: "Predictive ML remainder (family #1 at 34 of 54)".

    def register_model_reference(self, name, model_kind, actor, dataset_id=None):
        """Register a predictive-model reference record.

        Reference implementation only: the build trains nothing and
        predicts nothing (there is deliberately no train or predict
        method on this surface). The record states what an external
        ML system would be, labeled as a reference.
        """
        self._guard(actor, "ingest", "ext_register_model_reference")
        _require_text(name, "model name")
        _validate_choice(model_kind, KNOWN_MODEL_KINDS, "model kind")
        if dataset_id is not None:
            self._dataset(dataset_id)
        fields = {
            "name": name,
            "model_kind": model_kind,
            "dataset_id": dataset_id,
            "reference_stub": True,
            "state": "recorded_reference_only",
            "trained_here": False,
            "predicted_here": False,
            "created_by": actor_name(actor),
            "created_utc": _utc_now(),
        }
        return self._commit(self._models, "mdl", fields, actor,
                            "ext_register_model_reference",
                            details={"model_kind": model_kind})

    def record_model_run_reference(self, model_id, outcome_summary, actor,
                                   reported_figures=None):
        """Record a model run as reported by an external system.

        The outcome summary and any reported figures are stored
        verbatim as reported; no figure is computed here.
        """
        self._guard(actor, "ingest", "ext_record_model_run_reference", model_id)
        self._get(self._models, model_id, "model reference")
        _require_text(outcome_summary, "outcome summary")
        figures = _validate_reported_figures(reported_figures)
        fields = {
            "model_id": model_id,
            "outcome_summary": outcome_summary,
            "reported_figures": figures,
            "reference_stub": True,
            "state": "recorded_reference_only",
            "executed": False,
            "computed_here": False,
            "recorded_by": actor_name(actor),
            "recorded_utc": _utc_now(),
        }
        return self._commit(self._model_runs, "mdlr", fields, actor,
                            "ext_record_model_run_reference", target=model_id)

    def model_view(self, model_id, actor):
        """Model reference record plus reported-run count, derived."""
        self._guard(actor, "query", "ext_model_view", model_id)
        record = self._get(self._models, model_id, "model reference")
        with self._lock:
            runs = [copy.deepcopy(r) for r in self._model_runs.values()
                    if r["model_id"] == model_id]
        record["runs"] = runs
        record["run_count"] = len(runs)
        return record

    # -- Bundled Extended families (reference implementation) -----------
    # GAPS idx 25: "Real-time / streaming (18), collaboration (17),
    # proprietary connectors (17), governance (11), transformation
    # (10), text/NLP (6), archiving (4), scheduling (3), geospatial
    # (3), media analytics (2), self-service BI (2), KPI (0 claims in
    # this group)".
    #
    # This tier's entry bundles the twelve families into a single
    # line, so the closure is one carried reference surface: one
    # reference record per family (the Communication L3 bundled-entry
    # form), plus reported outcome records and, for the two transport-
    # shaped families, the adjudicated reported-receipt forms. The
    # bundle's token is reference; per-family records do not
    # re-token it.

    def register_extended_family_reference(self, family, actor):
        """Register the reference record for one bundled family.

        One record per family; the family vocabulary and the
        sibling counts are the GAPS entry's own text, recorded as
        data. The record states the family is not implemented here.
        """
        self._guard(actor, "ingest", "ext_register_extended_family_reference")
        _validate_choice(family, KNOWN_EXTENDED_FAMILIES, "extended family")
        with self._lock:
            if family in self._family_ref_ids_by_family:
                raise ValidationError(
                    "extended family already registered: %r" % (family,))
            fields = {
                "family": family,
                "siblings_claiming": EXTENDED_FAMILY_CLAIM_COUNTS[family],
                "reference_stub": True,
                "state": "recorded_reference_only",
                "implemented_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            record = self._commit(self._family_refs, "efr", fields, actor,
                                  "ext_register_extended_family_reference",
                                  details={"family": family})
            self._family_ref_ids_by_family[family] = record["id"]
            return record

    def _family_ref(self, family_ref_id):
        return self._get(self._family_refs, family_ref_id,
                         "extended family reference")

    def record_extended_family_report(self, family_ref_id, outcome_summary,
                                      actor, reported_figures=None):
        """Record an outcome for a bundled family, as reported.

        The summary and any reported figures are stored verbatim;
        nothing is performed or computed here. Reported KPI values
        arrive through this same form: a value is held as reported,
        never derived.
        """
        self._guard(actor, "ingest", "ext_record_extended_family_report",
                    family_ref_id)
        ref = self._family_ref(family_ref_id)
        _require_text(outcome_summary, "outcome summary")
        figures = _validate_reported_figures(reported_figures)
        fields = {
            "family_ref_id": family_ref_id,
            "family": ref["family"],
            "outcome_summary": outcome_summary,
            "reported_figures": figures,
            "reference_stub": True,
            "state": "recorded_reference_only",
            "performed_here": False,
            "computed_here": False,
            "recorded_by": actor_name(actor),
            "recorded_utc": _utc_now(),
        }
        return self._commit(self._family_reports, "efp", fields, actor,
                            "ext_record_extended_family_report",
                            target=family_ref_id)

    def record_stream_batch_reference(self, family_ref_id, reported_row_count,
                                      actor):
        """Record a stream batch as reported; nothing is ingested.

        The reported-receipt form for the bundle's real-time /
        streaming family, bound to that family's reference record.
        """
        self._guard(actor, "ingest", "ext_record_stream_batch_reference",
                    family_ref_id)
        ref = self._family_ref(family_ref_id)
        if ref["family"] != STREAMING_FAMILY:
            raise ValidationError(
                "stream batches bind to the %r family reference, not %r"
                % (STREAMING_FAMILY, ref["family"]))
        _validate_count(reported_row_count, "reported_row_count")
        fields = {
            "family_ref_id": family_ref_id,
            "family": ref["family"],
            "reported_row_count": reported_row_count,
            "reference_stub": True,
            "reference_transport": True,
            "state": "recorded_reference_only",
            "ingested_here": False,
            "streamed_here": False,
            "recorded_by": actor_name(actor),
            "recorded_utc": _utc_now(),
        }
        return self._commit(self._stream_batches, "stmb", fields, actor,
                            "ext_record_stream_batch_reference",
                            target=family_ref_id,
                            details={"reported_row_count": reported_row_count})

    def record_connector_sync_reference(self, family_ref_id, reported_rows,
                                        actor):
        """Record a connector sync as reported; nothing is ingested.

        The reported-receipt form for the bundle's proprietary-
        connectors family, bound to that family's reference record.
        Core ingest (open CSV/JSON) is unchanged and nothing
        connects.
        """
        self._guard(actor, "ingest", "ext_record_connector_sync_reference",
                    family_ref_id)
        ref = self._family_ref(family_ref_id)
        if ref["family"] != CONNECTORS_FAMILY:
            raise ValidationError(
                "connector syncs bind to the %r family reference, not %r"
                % (CONNECTORS_FAMILY, ref["family"]))
        _validate_count(reported_rows, "reported_rows")
        fields = {
            "family_ref_id": family_ref_id,
            "family": ref["family"],
            "reported_rows": reported_rows,
            "reference_stub": True,
            "reference_transport": True,
            "state": "recorded_reference_only",
            "connected_here": False,
            "ingested_here": False,
            "recorded_by": actor_name(actor),
            "recorded_utc": _utc_now(),
        }
        return self._commit(self._connector_syncs, "cons", fields, actor,
                            "ext_record_connector_sync_reference",
                            target=family_ref_id,
                            details={"reported_rows": reported_rows})

    def _family_rollup(self, family_ref_id):
        """Derived per-family rollup: counts and reported totals."""
        with self._lock:
            reports = [copy.deepcopy(r) for r in self._family_reports.values()
                       if r["family_ref_id"] == family_ref_id]
            batches = [copy.deepcopy(b) for b in self._stream_batches.values()
                       if b["family_ref_id"] == family_ref_id]
            syncs = [copy.deepcopy(s) for s in self._connector_syncs.values()
                     if s["family_ref_id"] == family_ref_id]
        reported_counts = ([b["reported_row_count"] for b in batches]
                           + [s["reported_rows"] for s in syncs])
        return reports, batches, syncs, {
            "report_count": len(reports),
            "batch_count": len(batches),
            "sync_count": len(syncs),
            "reported_rows_total": self._sum_reported_counts(reported_counts),
        }

    def extended_family_view(self, family_ref_id, actor):
        """Family reference record plus derived rollup at read."""
        self._guard(actor, "query", "ext_extended_family_view", family_ref_id)
        record = self._family_ref(family_ref_id)
        reports, batches, syncs, rollup = self._family_rollup(family_ref_id)
        record["reports"] = reports
        record["batches"] = batches
        record["syncs"] = syncs
        record.update(rollup)
        return record

    def extended_bundle_view(self, actor):
        """All registered family references with derived rollups."""
        self._guard(actor, "query", "ext_extended_bundle_view")
        with self._lock:
            ref_ids = list(self._family_refs)
        families = []
        for ref_id in ref_ids:
            record = self._family_ref(ref_id)
            _reports, _batches, _syncs, rollup = self._family_rollup(ref_id)
            record.update(rollup)
            families.append(record)
        return {
            "families": families,
            "registered_family_count": len(families),
            "reported_rows_total": self._sum_reported_counts(
                [f["reported_rows_total"] for f in families]),
        }
