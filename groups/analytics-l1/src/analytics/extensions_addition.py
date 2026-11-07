"""Final GAPS batch, second unit — Remainder Addition extensions.

Records extensions for the 2 Extended functions the remainder
addition fork (HP WXP Collaboration) registered for this group in
``ADDENDUM.md`` §5 and GAPS.md's "Remainder Addition — Analytics
L1" section: the collaboration & unified-communications telemetry
engine, shipped as a labeled reference implementation, and the
end-user experience & productivity analytics engine, built as
records plus deterministic derivations over the core's own
datasets. See ``BATCH-ADDITION.md`` in the group directory for
the per-entry disposition.

Design, following the first batch unit's module
(:mod:`analytics.extensions`) and this tier's doctrines:

- This module wraps the core :class:`DatasetStore` in a second,
  independent wrapper; every existing module — including the
  first unit's ``extensions.py`` — is untouched (byte-identical).
  Dataset existence, rows, and descriptive statistics are always
  read through the core's public API (``get`` / ``describe``),
  never re-implemented.
- RBAC goes through :mod:`analytics.access` exactly as the core
  and the first unit enforce it: record creation maps onto the
  core ``ingest`` action, derivations and views onto ``query``,
  checked *before* any state change or id allocation; denied
  attempts are recorded on the core audit log with the extension
  action name suffixed ``:denied`` and every successful mutation
  as ``exta_<action>`` (the second-unit audit prefix). The
  baseline is the L1 Low union: a plain append-only audit log —
  no hash chain, no lockout, no auditor role is imported from
  the High sibling.
- Derived values are derived at read and never stored: telemetry
  report rollups, experience observation rollups. Stored records
  carry no derived key; tests pin that.
- The telemetry engine is a labeled reference implementation:
  nothing here collects from, connects to, or ingests from a
  UC environment. Telemetry arrives as *reported* counts
  (aggregates only — meeting/session counts and minutes, the
  metadata-only shape ``test_additions.py`` exercises this fork
  against the core in; no session content, no user data).
- The experience engine computes **no score**: the addition's
  prose defines none and neither does this build. Its view
  surfaces the core's own descriptive statistics over the
  values recorded in a core dataset — statistics of recorded
  data, stated as such — plus counts of recorded experience
  observations. No experience, productivity, or quality score
  key exists anywhere on this surface; tests pin that.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .query import describe


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


# -- vocabularies -----------------------------------------------------

TELEMETRY_SOURCE_KINDS = ("unified_communications", "endpoints",
                          "meeting_infrastructure",
                          "calling_infrastructure", "mixed_vendor")
KNOWN_TELEMETRY_SOURCE_KINDS = frozenset(TELEMETRY_SOURCE_KINDS)

EXPERIENCE_DIMENSIONS = ("call_quality", "meeting_reliability",
                         "join_experience", "audio_quality",
                         "video_quality", "productivity",
                         "it_efficiency")
KNOWN_EXPERIENCE_DIMENSIONS = frozenset(EXPERIENCE_DIMENSIONS)


# -- shared validators (mirroring the first unit's) ---------------------


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


def _validate_count(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


class AnalyticsExtensionsAddition:
    """Remainder-addition extension surface over a core DatasetStore."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.RLock()
        self._counters = {}
        self._telemetry_sources = {}
        self._telemetry_reports = {}
        self._experience_profiles = {}
        self._experience_observations = {}

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

    @staticmethod
    def _sum_reported_counts(counts):
        """Sum of reported counts, as reported.

        The totals on this surface are sums of values *reported*
        by external systems and recorded here; nothing was
        collected or measured here. This is the negative
        control's seam (see tests/test_gaps_batch_addition.py):
        a view whose total merely echoes the first reported
        count is the mutant the drill rejects -- the total must
        come from every recorded report.
        """
        return sum(counts)

    # -- UC telemetry engine (reference implementation) -------------------

    def register_telemetry_source_reference(self, name, vendor_label,
                                            source_kind, actor):
        """Register a UC telemetry source definition as a reference.

        Reference implementation only: nothing collects from,
        connects to, or monitors a UC environment
        (``collected_here`` / ``connected_here`` are False). The
        vendor label is recorded as data — multi-vendor telemetry
        is the entry's substance.
        """
        self._guard(actor, "ingest",
                    "exta_register_telemetry_source_reference")
        _require_text(name, "telemetry source name")
        _require_text(vendor_label, "telemetry vendor label")
        _validate_choice(source_kind, KNOWN_TELEMETRY_SOURCE_KINDS,
                         "telemetry source kind")
        with self._lock:
            source_id = self._next_id("uct")
            record = {
                "id": source_id,
                "name": name,
                "vendor_label": vendor_label,
                "source_kind": source_kind,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "collected_here": False,
                "connected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._telemetry_sources[source_id] = record
            self._record(actor, "exta_register_telemetry_source_reference",
                         source_id,
                         details={"source_kind": source_kind})
            return copy.deepcopy(record)

    def record_telemetry_report(self, source_id, reported_sessions,
                                reported_minutes, actor, outcome=None):
        """Record UC telemetry counts as reported; nothing ingested.

        Aggregates only — session counts and minutes as reported
        by the source environment's operator. No session content
        and no user data exist in this shape. Recording a report
        changes no core dataset (pinned by test).
        """
        self._guard(actor, "ingest", "exta_record_telemetry_report",
                    source_id)
        self._get(self._telemetry_sources, source_id,
                  "telemetry source reference")
        _validate_count(reported_sessions, "reported_sessions")
        _validate_count(reported_minutes, "reported_minutes")
        if outcome is not None:
            _require_text(outcome, "telemetry report outcome")
        with self._lock:
            report_id = self._next_id("uctr")
            record = {
                "id": report_id,
                "source_id": source_id,
                "reported_sessions": reported_sessions,
                "reported_minutes": reported_minutes,
                "outcome": outcome,
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "collected_here": False,
                "ingested_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._telemetry_reports[report_id] = record
            self._record(actor, "exta_record_telemetry_report", source_id,
                         details={"reported_sessions": reported_sessions,
                                  "reported_minutes": reported_minutes})
            return copy.deepcopy(record)

    def telemetry_source_view(self, source_id, actor):
        """Telemetry source reference plus reported rollup, derived."""
        self._guard(actor, "query", "exta_telemetry_source_view", source_id)
        record = self._get(self._telemetry_sources, source_id,
                           "telemetry source reference")
        with self._lock:
            reports = [copy.deepcopy(r)
                       for r in self._telemetry_reports.values()
                       if r["source_id"] == source_id]
        record["reports"] = reports
        record["report_count"] = len(reports)
        record["reported_sessions_total"] = self._sum_reported_counts(
            [r["reported_sessions"] for r in reports])
        record["reported_minutes_total"] = self._sum_reported_counts(
            [r["reported_minutes"] for r in reports])
        return record

    # -- End-user experience & productivity analytics (built) -------------

    def create_experience_profile(self, name, dataset_id, column, actor):
        """Record an experience-analytics profile over a core dataset.

        A profile is a definition only: a named core dataset and
        one of its columns. It stores no figure of any kind
        (pinned by test); the figures in ``experience_view`` are
        the core's descriptive statistics over the recorded
        values, derived at read. No experience or productivity
        score is defined by the addition fork's prose and none
        is computed here; the record carries no score-shaped
        key at all (pinned by a recursive scan in the tests).
        """
        self._guard(actor, "ingest", "exta_create_experience_profile",
                    dataset_id)
        _require_text(name, "experience profile name")
        dataset = self._dataset(dataset_id)
        if column not in dataset["columns"]:
            raise ValidationError(
                "experience column is not a column: %r" % (column,))
        with self._lock:
            profile_id = self._next_id("exp")
            record = {
                "id": profile_id,
                "name": name,
                "dataset_id": dataset_id,
                "column": column,
                "method": "core_describe_derivation",
                "basis": "recorded_dataset_values",
                "measured_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._experience_profiles[profile_id] = record
            self._record(actor, "exta_create_experience_profile", profile_id,
                         details={"dataset_id": dataset_id,
                                  "column": column})
            return copy.deepcopy(record)

    def record_experience_observation(self, profile_id, dimension,
                                      reported_label, reported_count, actor):
        """Record an experience/productivity observation as reported.

        The dimension is from the recorded vocabulary; the label
        and the count (sessions or users the observation covers,
        as reported by whoever observed them) are recorded
        verbatim. Nothing is measured or computed here, and no
        observation carries a score — there is no parameter that
        could accept one.
        """
        self._guard(actor, "ingest", "exta_record_experience_observation",
                    profile_id)
        self._get(self._experience_profiles, profile_id,
                  "experience profile")
        _validate_choice(dimension, KNOWN_EXPERIENCE_DIMENSIONS,
                         "experience dimension")
        _require_text(reported_label, "reported experience label")
        _validate_count(reported_count, "reported_count")
        with self._lock:
            observation_id = self._next_id("expo")
            record = {
                "id": observation_id,
                "profile_id": profile_id,
                "dimension": dimension,
                "reported_label": reported_label,
                "reported_count": reported_count,
                "measured_here": False,
                "computed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._experience_observations[observation_id] = record
            self._record(actor, "exta_record_experience_observation",
                         profile_id,
                         details={"dimension": dimension})
            return copy.deepcopy(record)

    def experience_view(self, profile_id, actor):
        """Experience profile plus derived statistics and rollup.

        ``statistics`` is the core's ``describe`` over the
        profile's recorded dataset column — descriptive
        statistics of the values the dataset holds, derived at
        read through the core's own machinery and stated as
        such; it is not an experience score, and no score is
        computed anywhere in this view.
        """
        self._guard(actor, "query", "exta_experience_view", profile_id)
        record = self._get(self._experience_profiles, profile_id,
                           "experience profile")
        statistics = describe(self.store, record["dataset_id"],
                              record["column"], actor)
        with self._lock:
            observations = [copy.deepcopy(o)
                            for o in self._experience_observations.values()
                            if o["profile_id"] == profile_id]
        by_dimension = {}
        by_label = {}
        for observation in observations:
            by_dimension[observation["dimension"]] = \
                by_dimension.get(observation["dimension"], 0) + 1
            by_label[observation["reported_label"]] = \
                by_label.get(observation["reported_label"], 0) + 1
        record["statistics"] = statistics
        record["statistics_basis"] = "recorded_dataset_values"
        record["observations"] = observations
        record["observation_count"] = len(observations)
        record["reported_observations_total"] = self._sum_reported_counts(
            [o["reported_count"] for o in observations])
        record["observations_by_dimension"] = by_dimension
        record["observations_by_label"] = by_label
        return record
