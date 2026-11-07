"""Final GAPS batch extensions for the Analytics L2 merged build.

Clean-room, standard-library-only records/derivation extensions for
the 14 Extended families the union spec ranked but the core did not
implement: 10 built as in-substrate records plus deterministic
derivations over the core's own datasets, 4 shipped as labeled
reference implementations. See ``BATCH.md`` in the group directory
for the per-entry disposition.

Design, following the core's doctrines:

- This module is a wrapper around :class:`DatasetStore`; the core
  modules are untouched (byte-identical). Dataset existence, rows,
  queries, and descriptive statistics are always read through the
  core's public API (``get`` / ``rows`` / ``run_query`` /
  ``describe``), never re-implemented.
- RBAC goes through :mod:`analytics.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Plain-string actors
  carry identity but no role, mirroring the core convention.
  Mapping: record creation/registration -> ``ingest``; derivations
  and views -> ``query``; governance access-review decisions ->
  ``admin`` (a decision surface, not a data operation).
- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``.
- Derived values are derived at read and never stored: workspace
  member/share counts, transform run rollups, governance review
  rollups, KPI values, schedule run rollups, media totals, and all
  geospatial distances/bearings. Stored records carry no derived
  key; tests pin that.
- Nothing here learns, streams, monitors, connects, or executes
  against an external system. The four stub-engine families ship as
  labeled reference implementations: every record they create
  carries ``reference_stub: True``, and no model is trained, no
  stream is opened, no connector connects, and no alert monitors
  anything (alert evaluations are point-in-time recorded receipts
  over the core's ``describe`` output).
"""

import copy
import math
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .query import AGG_FUNCS, WHERE_OPS, _compare, _num, describe, run_query


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


# -- vocabularies -----------------------------------------------------

WORKSPACE_MEMBER_ROLES = ("editor", "viewer")
KNOWN_WORKSPACE_MEMBER_ROLES = frozenset(WORKSPACE_MEMBER_ROLES)

TRANSFORM_STEP_KINDS = ("rename", "select_columns", "filter", "sort", "limit")
KNOWN_TRANSFORM_STEP_KINDS = frozenset(TRANSFORM_STEP_KINDS)
SORT_DIRECTIONS = ("asc", "desc")

POLICY_KINDS = ("classification", "access_review", "quality_rule", "retention_note")
KNOWN_POLICY_KINDS = frozenset(POLICY_KINDS)
REVIEW_DECISIONS = ("approved", "changes_requested", "rejected")
KNOWN_REVIEW_DECISIONS = frozenset(REVIEW_DECISIONS)

EARTH_RADIUS_KM = 6371.0088
GEO_METHOD = "haversine_great_circle"

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
TEXT_METHOD = "deterministic_token_count"

ARCHIVE_TARGET_KINDS = ("dataset", "saved_view", "report")
KNOWN_ARCHIVE_TARGET_KINDS = frozenset(ARCHIVE_TARGET_KINDS)

DESCRIBE_STATISTICS = ("count", "mean", "median", "min", "max", "stddev")

SCHEDULE_CADENCES = ("daily", "weekly", "monthly", "quarterly")
KNOWN_SCHEDULE_CADENCES = frozenset(SCHEDULE_CADENCES)
SCHEDULE_TARGET_KINDS = ("saved_view", "transform", "dataset_export")
KNOWN_SCHEDULE_TARGET_KINDS = frozenset(SCHEDULE_TARGET_KINDS)
SCHEDULE_RUN_OUTCOMES = ("completed", "failed", "skipped")
KNOWN_SCHEDULE_RUN_OUTCOMES = frozenset(SCHEDULE_RUN_OUTCOMES)

MEDIA_KINDS = ("image", "video", "audio")
KNOWN_MEDIA_KINDS = frozenset(MEDIA_KINDS)

MODEL_KINDS = ("regression", "classification", "forecasting", "clustering")
KNOWN_MODEL_KINDS = frozenset(MODEL_KINDS)

ALERT_OPS = ("lt", "le", "gt", "ge", "eq", "ne")
KNOWN_ALERT_OPS = frozenset(ALERT_OPS)

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
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError("%s must be finite" % (what,))
    return value


def _validate_count(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


class AnalyticsExtensions:
    """Records/derivation extension surface over a core DatasetStore."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.RLock()
        self._counters = {}
        self._workspaces = {}
        self._workspace_members = {}
        self._shares = {}
        self._transforms = {}
        self._transform_runs = {}
        self._policies = {}
        self._reviews = {}
        self._places = {}
        self._place_ids_by_ref = {}
        self._archives = {}
        self._saved_views = {}
        self._dashboards = {}
        self._dashboard_panels = {}
        self._kpis = {}
        self._schedules = {}
        self._schedule_runs = {}
        self._media_assets = {}
        self._models = {}
        self._model_runs = {}
        self._alert_rules = {}
        self._alert_evaluations = {}
        self._streams = {}
        self._stream_batches = {}
        self._connectors = {}
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

    def _dataset(self, dataset_id):
        """Return the core dataset dict, raising NotFoundError."""
        return self.store.get(dataset_id)

    @staticmethod
    def _get(collection, record_id, what):
        record = collection.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return copy.deepcopy(record)

    # -- Collaboration (shared workspaces around analytics) -------------

    def create_workspace(self, name, actor):
        """Create a shared workspace record around analytics artifacts."""
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
        return self._share(workspace_id, "dataset", dataset_id, actor)

    def share_saved_view(self, workspace_id, view_id, actor):
        """Record that a saved view is shared into a workspace."""
        self._guard(actor, "ingest", "ext_share_saved_view", workspace_id)
        self._get(self._workspaces, workspace_id, "workspace")
        self._get(self._saved_views, view_id, "saved view")
        return self._share(workspace_id, "saved_view", view_id, actor)

    def _share(self, workspace_id, target_kind, target_ref, actor):
        with self._lock:
            share_id = self._next_id("shr")
            record = {
                "id": share_id,
                "workspace_id": workspace_id,
                "target_kind": target_kind,
                "target_ref": target_ref,
                "shared_by": actor_name(actor),
                "shared_utc": _utc_now(),
            }
            self._shares[share_id] = record
            self._record(actor, "ext_share_" + target_kind, workspace_id,
                         details={"target_ref": target_ref})
            return copy.deepcopy(record)

    def workspace_view(self, workspace_id, actor):
        """Workspace record plus member/share counts derived at read."""
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

    # -- Data transformation / ETL ----------------------------------------

    def _validate_steps(self, steps, columns):
        if not isinstance(steps, list) or not steps:
            raise ValidationError("transform steps must be a non-empty list")
        working = list(columns)
        validated = []
        for step in steps:
            if not isinstance(step, dict):
                raise ValidationError("each transform step must be an object")
            kind = step.get("step")
            _validate_choice(kind, KNOWN_TRANSFORM_STEP_KINDS, "transform step")
            if kind == "rename":
                source = step.get("from")
                target = step.get("to")
                if source not in working:
                    raise ValidationError("rename source is not a column: %r" % (source,))
                _require_text(target, "rename target")
                if target in working:
                    raise ValidationError("rename target already a column: %r" % (target,))
                working = [target if c == source else c for c in working]
                validated.append({"step": "rename", "from": source, "to": target})
            elif kind == "select_columns":
                selected = step.get("columns")
                if (not isinstance(selected, list) or not selected
                        or any(not isinstance(c, str) for c in selected)):
                    raise ValidationError(
                        "select_columns requires a non-empty list of column names")
                for col in selected:
                    if col not in working:
                        raise ValidationError(
                            "select_columns names an unknown column: %r" % (col,))
                working = list(selected)
                validated.append({"step": "select_columns", "columns": list(selected)})
            elif kind == "filter":
                column = step.get("column")
                if column not in working:
                    raise ValidationError("filter column is not a column: %r" % (column,))
                op = step.get("op")
                if op not in WHERE_OPS:
                    raise ValidationError("unknown filter operator: %r" % (op,))
                if "value" not in step:
                    raise ValidationError("filter step is missing 'value'")
                validated.append({"step": "filter", "column": column, "op": op,
                                  "value": copy.deepcopy(step["value"])})
            elif kind == "sort":
                column = step.get("column")
                if column not in working:
                    raise ValidationError("sort column is not a column: %r" % (column,))
                direction = step.get("direction", "asc")
                if direction not in SORT_DIRECTIONS:
                    raise ValidationError("unknown sort direction: %r" % (direction,))
                validated.append({"step": "sort", "column": column,
                                  "direction": direction})
            elif kind == "limit":
                limit = step.get("limit")
                _validate_count(limit, "limit")
                validated.append({"step": "limit", "limit": limit})
        return validated, working

    def create_transform(self, name, dataset_id, steps, actor):
        """Record a transformation definition over a core dataset.

        A definition is an ordered list of stated rules from the
        fixed step vocabulary; running it is a deterministic
        derivation over the core dataset's rows (see run_transform).
        """
        self._guard(actor, "ingest", "ext_create_transform", dataset_id)
        _require_text(name, "transform name")
        dataset = self._dataset(dataset_id)
        validated, _ = self._validate_steps(steps, dataset["columns"])
        with self._lock:
            transform_id = self._next_id("tr")
            record = {
                "id": transform_id,
                "name": name,
                "dataset_id": dataset_id,
                "steps": validated,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._transforms[transform_id] = record
            self._record(actor, "ext_create_transform", transform_id,
                         details={"dataset_id": dataset_id})
            return copy.deepcopy(record)

    def _apply_step(self, rows, columns, step):
        kind = step["step"]
        if kind == "rename":
            renamed = []
            for row in rows:
                renamed.append({
                    (step["to"] if col == step["from"] else col): row.get(col)
                    for col in columns
                })
            return renamed, [step["to"] if c == step["from"] else c
                             for c in columns]
        if kind == "select_columns":
            selected = step["columns"]
            return [{col: row.get(col) for col in selected} for row in rows], list(selected)
        if kind == "filter":
            column = step["column"]
            return (
                [row for row in rows
                 if _compare(row.get(column), step["op"], step["value"])],
                columns,
            )
        if kind == "sort":
            column = step["column"]
            numeric = all(
                _num(row.get(column)) is not None
                for row in rows if row.get(column) is not None
            ) and any(row.get(column) is not None for row in rows)

            def key_fn(row, column=column, numeric=numeric):
                value = row.get(column)
                if value is None:
                    return (1, 0.0 if numeric else "")
                if numeric:
                    return (0, _num(value))
                return (0, str(value))

            return (sorted(rows, key=key_fn,
                           reverse=(step["direction"] == "desc")), columns)
        if kind == "limit":
            return rows[: step["limit"]], columns
        raise ValidationError("unknown transform step: %r" % (kind,))

    def _apply_transform_steps(self, rows, columns, steps):
        """Apply stated-rule steps in order. The batch's fresh
        negative-control seam: a filter step that does not filter
        is the mutant the drill rejects."""
        out_rows = [dict(row) for row in rows]
        out_columns = list(columns)
        for step in steps:
            out_rows, out_columns = self._apply_step(out_rows, out_columns, step)
        return out_rows, out_columns

    def run_transform(self, transform_id, actor):
        """Run a transformation definition deterministically.

        Returns the derived result ({columns, rows, row_count}) and
        stores a run *record* (counts and method only -- the derived
        rows themselves are not stored).
        """
        self._guard(actor, "query", "ext_run_transform", transform_id)
        record = self._get(self._transforms, transform_id, "transform")
        dataset = self._dataset(record["dataset_id"])
        rows = self.store.rows(record["dataset_id"])
        out_rows, out_columns = self._apply_transform_steps(
            rows, dataset["columns"], record["steps"])
        with self._lock:
            run_id = self._next_id("trr")
            run = {
                "id": run_id,
                "transform_id": transform_id,
                "dataset_id": record["dataset_id"],
                "rows_in": len(rows),
                "rows_out": len(out_rows),
                "method": "deterministic_rules",
                "reported": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._transform_runs[run_id] = run
            self._record(actor, "ext_run_transform", transform_id,
                         details={"rows_out": len(out_rows)})
        return {
            "transform_id": transform_id,
            "run_id": run_id,
            "method": "deterministic_rules",
            "columns": out_columns,
            "rows": out_rows,
            "row_count": len(out_rows),
        }

    def record_reported_transform_run(self, transform_id, rows_in, rows_out,
                                      actor, note=None):
        """Record a transform run performed outside the stated rules.

        For transformations beyond the step vocabulary, the run is
        recorded as reported (counts as stated by the reporter); the
        build derives nothing for it.
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

    # -- Governance beyond the dataset registry --------------------------

    def create_policy(self, dataset_id, kind, statement, actor):
        """Record a governance policy statement over a core dataset."""
        self._guard(actor, "ingest", "ext_create_policy", dataset_id)
        self._dataset(dataset_id)
        _validate_choice(kind, KNOWN_POLICY_KINDS, "policy kind")
        _require_text(statement, "policy statement")
        with self._lock:
            policy_id = self._next_id("pol")
            record = {
                "id": policy_id,
                "dataset_id": dataset_id,
                "kind": kind,
                "statement": statement,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._policies[policy_id] = record
            self._record(actor, "ext_create_policy", dataset_id,
                         details={"kind": kind})
            return copy.deepcopy(record)

    def record_access_review(self, dataset_id, reviewer_ref, decision, actor):
        """Record an access-review decision for a dataset.

        A decision surface: mapped to the core ``admin`` action.
        The reviewer is an opaque ref; the decision is recorded
        verbatim, never derived.
        """
        self._guard(actor, "admin", "ext_record_access_review", dataset_id)
        self._dataset(dataset_id)
        _require_text(reviewer_ref, "reviewer ref")
        _validate_choice(decision, KNOWN_REVIEW_DECISIONS, "review decision")
        with self._lock:
            review_id = self._next_id("rev")
            record = {
                "id": review_id,
                "dataset_id": dataset_id,
                "reviewer_ref": reviewer_ref,
                "decision": decision,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._reviews[review_id] = record
            self._record(actor, "ext_record_access_review", dataset_id,
                         details={"decision": decision})
            return copy.deepcopy(record)

    def governance_view(self, dataset_id, actor):
        """Policies plus review rollup for a dataset, derived at read."""
        self._guard(actor, "query", "ext_governance_view", dataset_id)
        self._dataset(dataset_id)
        with self._lock:
            policies = [copy.deepcopy(p) for p in self._policies.values()
                        if p["dataset_id"] == dataset_id]
            reviews = [copy.deepcopy(r) for r in self._reviews.values()
                       if r["dataset_id"] == dataset_id]
        by_decision = {}
        for review in reviews:
            by_decision[review["decision"]] = by_decision.get(review["decision"], 0) + 1
        return {
            "dataset_id": dataset_id,
            "policies": policies,
            "policy_count": len(policies),
            "reviews": reviews,
            "review_count": len(reviews),
            "reviews_by_decision": by_decision,
            "current_decision": reviews[-1]["decision"] if reviews else None,
        }

    # -- Geospatial analytics ----------------------------------------------

    def register_place(self, place_ref, latitude, longitude, actor):
        """Register a named coordinate pair as a place record.

        Coordinates are the record; every distance and bearing is
        derived at read and never stored on the record.
        """
        self._guard(actor, "ingest", "ext_register_place")
        _require_text(place_ref, "place ref")
        _validate_number(latitude, "latitude")
        _validate_number(longitude, "longitude")
        if not -90.0 <= float(latitude) <= 90.0:
            raise ValidationError("latitude out of range: %r" % (latitude,))
        if not -180.0 <= float(longitude) <= 180.0:
            raise ValidationError("longitude out of range: %r" % (longitude,))
        with self._lock:
            if place_ref in self._place_ids_by_ref:
                raise ValidationError("place ref already registered: %r" % (place_ref,))
            place_id = self._next_id("geo")
            record = {
                "id": place_id,
                "place_ref": place_ref,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._places[place_id] = record
            self._place_ids_by_ref[place_ref] = place_id
            self._record(actor, "ext_register_place", place_id,
                         details={"place_ref": place_ref})
            return copy.deepcopy(record)

    def _place_by_ref(self, place_ref):
        place_id = self._place_ids_by_ref.get(place_ref)
        if place_id is None:
            raise NotFoundError("place not found: %r" % (place_ref,))
        return self._places[place_id]

    @staticmethod
    def _haversine_km(lat1, lon1, lat2, lon2):
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2.0) ** 2
             + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2)
        return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))

    def distance_km(self, from_ref, to_ref, actor):
        """Great-circle distance between two registered places.

        Derived at read by the haversine formula (the math, labeled
        with its method); nothing is stored.
        """
        self._guard(actor, "query", "ext_distance_km")
        origin = self._place_by_ref(from_ref)
        dest = self._place_by_ref(to_ref)
        distance = self._haversine_km(origin["latitude"], origin["longitude"],
                                      dest["latitude"], dest["longitude"])
        self._record(actor, "ext_distance_km", dest["id"],
                     details={"from_ref": from_ref})
        return {"from_ref": from_ref, "to_ref": to_ref,
                "distance_km": distance, "method": GEO_METHOD}

    def initial_bearing_degrees(self, from_ref, to_ref, actor):
        """Initial great-circle bearing between two places, derived."""
        self._guard(actor, "query", "ext_initial_bearing")
        origin = self._place_by_ref(from_ref)
        dest = self._place_by_ref(to_ref)
        phi1 = math.radians(origin["latitude"])
        phi2 = math.radians(dest["latitude"])
        dlambda = math.radians(dest["longitude"] - origin["longitude"])
        y = math.sin(dlambda) * math.cos(phi2)
        x = (math.cos(phi1) * math.sin(phi2)
             - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda))
        bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
        self._record(actor, "ext_initial_bearing", dest["id"],
                     details={"from_ref": from_ref})
        return {"from_ref": from_ref, "to_ref": to_ref,
                "bearing_degrees": bearing, "method": GEO_METHOD}

    def nearest_place(self, place_ref, actor):
        """Nearest other registered place, derived at read."""
        self._guard(actor, "query", "ext_nearest_place")
        origin = self._place_by_ref(place_ref)
        with self._lock:
            others = [p for p in self._places.values()
                      if p["place_ref"] != place_ref]
        if not others:
            return {"place_ref": place_ref, "nearest_ref": None,
                    "distance_km": None, "method": GEO_METHOD}
        best = min(
            others,
            key=lambda p: self._haversine_km(
                origin["latitude"], origin["longitude"],
                p["latitude"], p["longitude"]),
        )
        return {
            "place_ref": place_ref,
            "nearest_ref": best["place_ref"],
            "distance_km": self._haversine_km(
                origin["latitude"], origin["longitude"],
                best["latitude"], best["longitude"]),
            "method": GEO_METHOD,
        }

    def place_record(self, place_ref, actor):
        """The stored place record (coordinates only, no derivations)."""
        self._guard(actor, "query", "ext_place_record")
        return copy.deepcopy(self._place_by_ref(place_ref))

    # -- Text / NLP analytics ------------------------------------------------

    def _text_values(self, dataset_id, column):
        dataset = self._dataset(dataset_id)
        if column not in dataset["columns"]:
            raise ValidationError("unknown column: %r" % (column,))
        return [row.get(column) for row in self.store.rows(dataset_id)
                if isinstance(row.get(column), str)]

    def analyze_text(self, dataset_id, column, actor, top_n=10):
        """Deterministic term counts over the text held in a column.

        Tokenization is lowercase alphanumeric runs; the result is
        counts only -- no learned model, no classification, no
        sentiment or inference of any kind. Derived at read;
        nothing is stored.
        """
        self._guard(actor, "query", "ext_analyze_text", dataset_id)
        if isinstance(top_n, bool) or not isinstance(top_n, int) \
                or not 1 <= top_n <= 100:
            raise ValidationError("top_n must be an integer in 1..100")
        values = self._text_values(dataset_id, column)
        counts = {}
        token_total = 0
        for value in values:
            for token in TOKEN_PATTERN.findall(value.lower()):
                counts[token] = counts.get(token, 0) + 1
                token_total += 1
        top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
        result = {
            "dataset_id": dataset_id,
            "column": column,
            "document_count": len(values),
            "token_count": token_total,
            "distinct_terms": len(counts),
            "top_terms": [{"term": term, "count": count} for term, count in top],
            "method": TEXT_METHOD,
        }
        self._record(actor, "ext_analyze_text", dataset_id,
                     details={"column": column})
        return result

    def term_count(self, dataset_id, column, term, actor):
        """Exact count of one normalized term across the column's text."""
        self._guard(actor, "query", "ext_term_count", dataset_id)
        _require_text(term, "term")
        normalized = term.lower()
        if not TOKEN_PATTERN.fullmatch(normalized):
            raise ValidationError("term is not a single token: %r" % (term,))
        values = self._text_values(dataset_id, column)
        total = 0
        documents = 0
        for value in values:
            hits = TOKEN_PATTERN.findall(value.lower()).count(normalized)
            total += hits
            if hits:
                documents += 1
        result = {"dataset_id": dataset_id, "column": column, "term": normalized,
                  "count": total, "document_count": documents,
                  "method": TEXT_METHOD}
        self._record(actor, "ext_term_count", dataset_id,
                     details={"column": column, "term": normalized})
        return result

    # -- Archiving -------------------------------------------------------------

    def create_archive_record(self, target_kind, target_ref, actor, reason=None):
        """Record that an artifact is archived. Nothing is deleted.

        The record is the disposition record only: retention-period
        enforcement and eventual disposition are the embedding
        organization's records schedule at the deployment layer
        (PLATFORM-LAYER.md decision 4). The target artifact remains
        fully present in the build.
        """
        self._guard(actor, "ingest", "ext_create_archive_record")
        _validate_choice(target_kind, KNOWN_ARCHIVE_TARGET_KINDS,
                         "archive target kind")
        _require_text(target_ref, "archive target ref")
        if reason is not None:
            _require_text(reason, "archive reason")
        if target_kind == "dataset":
            self._dataset(target_ref)
        elif target_kind == "saved_view":
            self._get(self._saved_views, target_ref, "saved view")
        with self._lock:
            archive_id = self._next_id("arc")
            record = {
                "id": archive_id,
                "target_kind": target_kind,
                "target_ref": target_ref,
                "reason": reason,
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
            records = [a for a in self._archives.values()
                       if a["target_ref"] == target_ref]
        return {
            "target_ref": target_ref,
            "archived": bool(records),
            "archive_count": len(records),
            "latest_archive_id": records[-1]["id"] if records else None,
        }

    # -- Self-service BI (saved views & dashboards) -----------------------------

    def create_saved_view(self, name, dataset_id, query, actor):
        """Record a saved view: a named core query over a dataset.

        The query is validated by executing it once through the
        core query surface at creation; the definition is stored
        verbatim and results are never stored on the record.
        """
        self._guard(actor, "ingest", "ext_create_saved_view", dataset_id)
        _require_text(name, "saved view name")
        self._dataset(dataset_id)
        if not isinstance(query, dict):
            raise ValidationError("saved view query must be an object")
        run_query(self.store, dataset_id, copy.deepcopy(query), actor)
        with self._lock:
            view_id = self._next_id("vw")
            record = {
                "id": view_id,
                "name": name,
                "dataset_id": dataset_id,
                "query": copy.deepcopy(query),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._saved_views[view_id] = record
            self._record(actor, "ext_create_saved_view", view_id,
                         details={"dataset_id": dataset_id})
            return copy.deepcopy(record)

    def run_saved_view(self, view_id, actor):
        """Execute a saved view through the core query surface.

        The result is derived at read from the live dataset; it is
        not written back onto the view record.
        """
        self._guard(actor, "query", "ext_run_saved_view", view_id)
        record = self._get(self._saved_views, view_id, "saved view")
        result = run_query(self.store, record["dataset_id"],
                           copy.deepcopy(record["query"]), actor)
        result = dict(result)
        result["view_id"] = view_id
        return result

    def get_saved_view(self, view_id, actor):
        """The stored saved-view record (definition only, no result)."""
        self._guard(actor, "query", "ext_get_saved_view", view_id)
        return self._get(self._saved_views, view_id, "saved view")

    def create_dashboard(self, name, actor):
        """Create a dashboard record: a named panel collection."""
        self._guard(actor, "ingest", "ext_create_dashboard")
        _require_text(name, "dashboard name")
        with self._lock:
            dashboard_id = self._next_id("db")
            record = {
                "id": dashboard_id,
                "name": name,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dashboards[dashboard_id] = record
            self._record(actor, "ext_create_dashboard", dashboard_id,
                         details={"name": name})
            return copy.deepcopy(record)

    def add_dashboard_panel(self, dashboard_id, view_id, title, actor):
        """Record a panel on a dashboard, bound to a saved view."""
        self._guard(actor, "ingest", "ext_add_dashboard_panel", dashboard_id)
        self._get(self._dashboards, dashboard_id, "dashboard")
        self._get(self._saved_views, view_id, "saved view")
        _require_text(title, "panel title")
        with self._lock:
            position = sum(1 for p in self._dashboard_panels.values()
                           if p["dashboard_id"] == dashboard_id) + 1
            panel_id = self._next_id("dbp")
            record = {
                "id": panel_id,
                "dashboard_id": dashboard_id,
                "view_id": view_id,
                "title": title,
                "position": position,
                "added_by": actor_name(actor),
                "added_utc": _utc_now(),
            }
            self._dashboard_panels[panel_id] = record
            self._record(actor, "ext_add_dashboard_panel", dashboard_id,
                         details={"view_id": view_id})
            return copy.deepcopy(record)

    def dashboard_view(self, dashboard_id, actor):
        """Dashboard plus panels with view names resolved at read."""
        self._guard(actor, "query", "ext_dashboard_view", dashboard_id)
        record = self._get(self._dashboards, dashboard_id, "dashboard")
        with self._lock:
            panels = [copy.deepcopy(p) for p in self._dashboard_panels.values()
                      if p["dashboard_id"] == dashboard_id]
        panels.sort(key=lambda p: p["position"])
        for panel in panels:
            view = self._saved_views.get(panel["view_id"])
            panel["view_name"] = view["name"] if view else None
        record["panels"] = panels
        record["panel_count"] = len(panels)
        return record

    # -- KPI & performance management ---------------------------------------------

    def _validate_measure(self, measure, dataset):
        if not isinstance(measure, dict):
            raise ValidationError("KPI measure must be an object")
        kind = measure.get("kind")
        if kind == "describe":
            column = measure.get("column")
            if column not in dataset["columns"]:
                raise ValidationError("KPI column is not a column: %r" % (column,))
            statistic = measure.get("statistic")
            if statistic not in DESCRIBE_STATISTICS:
                raise ValidationError("unknown describe statistic: %r" % (statistic,))
            return {"kind": "describe", "column": column, "statistic": statistic}
        if kind == "aggregate":
            func = measure.get("func")
            if func not in AGG_FUNCS:
                raise ValidationError("unknown aggregate function: %r" % (func,))
            column = measure.get("column")
            if column not in (None, "*") and column not in dataset["columns"]:
                raise ValidationError("KPI column is not a column: %r" % (column,))
            validated = {"kind": "aggregate", "func": func, "column": column}
            where = measure.get("where")
            if where is not None:
                if not isinstance(where, list):
                    raise ValidationError("KPI 'where' must be a list of conditions")
                for cond in where:
                    if not isinstance(cond, dict) \
                            or cond.get("column") not in dataset["columns"] \
                            or cond.get("op") not in WHERE_OPS \
                            or "value" not in cond:
                        raise ValidationError("invalid KPI 'where' condition")
                validated["where"] = copy.deepcopy(where)
            return validated
        raise ValidationError("unknown KPI measure kind: %r" % (kind,))

    def define_kpi(self, name, dataset_id, measure, actor, target=None):
        """Record a KPI definition over a core dataset.

        The definition stores the measure (and an optional target,
        as data). No value is stored: the value is derived at read
        from the core statistics/query surfaces.
        """
        self._guard(actor, "ingest", "ext_define_kpi", dataset_id)
        _require_text(name, "KPI name")
        dataset = self._dataset(dataset_id)
        validated = self._validate_measure(measure, dataset)
        if target is not None:
            _validate_number(target, "KPI target")
        with self._lock:
            kpi_id = self._next_id("kpi")
            record = {
                "id": kpi_id,
                "name": name,
                "dataset_id": dataset_id,
                "measure": validated,
                "target": target,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._kpis[kpi_id] = record
            self._record(actor, "ext_define_kpi", kpi_id,
                         details={"dataset_id": dataset_id})
            return copy.deepcopy(record)

    def kpi_value(self, kpi_id, actor):
        """The KPI's current value, derived at read from the core.

        Describe measures read the core ``describe`` surface;
        aggregate measures run a one-aggregate core query. The
        delta against a recorded target is likewise derived, never
        stored.
        """
        self._guard(actor, "query", "ext_kpi_value", kpi_id)
        record = self._get(self._kpis, kpi_id, "KPI")
        measure = record["measure"]
        if measure["kind"] == "describe":
            stats = describe(self.store, record["dataset_id"],
                             measure["column"], actor)
            value = stats[measure["statistic"]]
        else:
            query = {"aggregates": [{"func": measure["func"],
                                     "column": measure["column"],
                                     "alias": "value"}]}
            if measure.get("where"):
                query["where"] = copy.deepcopy(measure["where"])
            result = run_query(self.store, record["dataset_id"], query, actor)
            value = result["rows"][0]["value"] if result["rows"] else None
        target = record["target"]
        value_num = _num(value)
        delta = None
        if value_num is not None and target is not None:
            delta = value_num - float(target)
        self._record(actor, "ext_kpi_value", kpi_id,
                     details={"value": value_num})
        return {
            "kpi_id": kpi_id,
            "dataset_id": record["dataset_id"],
            "value": value,
            "target": target,
            "delta": delta,
            "method": "derived_from_core_statistics",
        }

    def get_kpi(self, kpi_id, actor):
        """The stored KPI definition (measure and target, no value)."""
        self._guard(actor, "query", "ext_get_kpi", kpi_id)
        return self._get(self._kpis, kpi_id, "KPI")

    # -- Scheduling ---------------------------------------------------------------

    def create_schedule(self, name, target_kind, target_ref, cadence, actor):
        """Record a schedule definition for an analytics artifact.

        A schedule here is a definition record plus recorded run
        receipts: nothing in this build runs on a timer, and no
        scheduled execution takes place.
        """
        self._guard(actor, "ingest", "ext_create_schedule")
        _require_text(name, "schedule name")
        _validate_choice(target_kind, KNOWN_SCHEDULE_TARGET_KINDS,
                         "schedule target kind")
        _validate_choice(cadence, KNOWN_SCHEDULE_CADENCES, "schedule cadence")
        _require_text(target_ref, "schedule target ref")
        if target_kind == "saved_view":
            self._get(self._saved_views, target_ref, "saved view")
        elif target_kind == "transform":
            self._get(self._transforms, target_ref, "transform")
        else:
            self._dataset(target_ref)
        with self._lock:
            schedule_id = self._next_id("sch")
            record = {
                "id": schedule_id,
                "name": name,
                "target_kind": target_kind,
                "target_ref": target_ref,
                "cadence": cadence,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._schedules[schedule_id] = record
            self._record(actor, "ext_create_schedule", schedule_id,
                         details={"target_kind": target_kind})
            return copy.deepcopy(record)

    def record_schedule_run(self, schedule_id, outcome, actor, note=None):
        """Record a run receipt for a schedule, as reported.

        The receipt records that a run was reported with the stated
        outcome; the build executed nothing (``executed_here`` is
        False on every receipt).
        """
        self._guard(actor, "ingest", "ext_record_schedule_run", schedule_id)
        self._get(self._schedules, schedule_id, "schedule")
        _validate_choice(outcome, KNOWN_SCHEDULE_RUN_OUTCOMES,
                         "schedule run outcome")
        if note is not None:
            _require_text(note, "run note")
        with self._lock:
            run_id = self._next_id("schr")
            record = {
                "id": run_id,
                "schedule_id": schedule_id,
                "outcome": outcome,
                "note": note,
                "executed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._schedule_runs[run_id] = record
            self._record(actor, "ext_record_schedule_run", schedule_id,
                         details={"outcome": outcome})
            return copy.deepcopy(record)

    def schedule_view(self, schedule_id, actor):
        """Schedule definition plus run rollup derived at read."""
        self._guard(actor, "query", "ext_schedule_view", schedule_id)
        record = self._get(self._schedules, schedule_id, "schedule")
        with self._lock:
            runs = [copy.deepcopy(r) for r in self._schedule_runs.values()
                    if r["schedule_id"] == schedule_id]
        by_outcome = {}
        for run in runs:
            by_outcome[run["outcome"]] = by_outcome.get(run["outcome"], 0) + 1
        record["runs"] = runs
        record["run_count"] = len(runs)
        record["runs_by_outcome"] = by_outcome
        record["last_outcome"] = runs[-1]["outcome"] if runs else None
        return record

    # -- Media analytics (metadata records) ------------------------------------------

    def register_media_asset(self, media_ref, media_kind, actor,
                             dataset_id=None, duration_seconds=None,
                             format_label=None):
        """Register a media asset as a metadata record.

        Metadata only: the build holds no media content and performs
        no content analysis; every media number is a count or sum
        over these records, derived at read.
        """
        self._guard(actor, "ingest", "ext_register_media_asset")
        _require_text(media_ref, "media ref")
        _validate_choice(media_kind, KNOWN_MEDIA_KINDS, "media kind")
        if dataset_id is not None:
            self._dataset(dataset_id)
        if duration_seconds is not None:
            _validate_count(duration_seconds, "duration_seconds")
        if format_label is not None:
            _require_text(format_label, "format label")
        with self._lock:
            asset_id = self._next_id("med")
            record = {
                "id": asset_id,
                "media_ref": media_ref,
                "media_kind": media_kind,
                "dataset_id": dataset_id,
                "duration_seconds": duration_seconds,
                "format_label": format_label,
                "analysis": "metadata_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._media_assets[asset_id] = record
            self._record(actor, "ext_register_media_asset", asset_id,
                         details={"media_kind": media_kind})
            return copy.deepcopy(record)

    def media_summary(self, actor):
        """Counts over the media metadata records, derived at read."""
        self._guard(actor, "query", "ext_media_summary")
        with self._lock:
            assets = list(self._media_assets.values())
        by_kind = {}
        total_duration = 0
        for asset in assets:
            by_kind[asset["media_kind"]] = by_kind.get(asset["media_kind"], 0) + 1
            if asset["duration_seconds"] is not None:
                total_duration += asset["duration_seconds"]
        return {
            "total": len(assets),
            "by_kind": by_kind,
            "total_duration_seconds": total_duration,
            "method": "metadata_counts",
        }

    # -- Predictive ML (reference implementation) --------------------------------------

    def register_model_reference(self, name, model_kind, actor, dataset_id=None):
        """Register a predictive-model reference record.

        Reference implementation only: the build trains nothing and
        predicts nothing (there is deliberately no predict method on
        this surface). The record states what an external ML system
        would be, labeled as a reference.
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
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._models[model_id] = record
            self._record(actor, "ext_register_model_reference", model_id,
                         details={"model_kind": model_kind})
            return copy.deepcopy(record)

    def record_model_run_reference(self, model_id, outcome_summary, actor):
        """Record a model run as reported by an external system."""
        self._guard(actor, "ingest", "ext_record_model_run_reference", model_id)
        self._get(self._models, model_id, "model reference")
        _require_text(outcome_summary, "outcome summary")
        with self._lock:
            run_id = self._next_id("mdlr")
            record = {
                "id": run_id,
                "model_id": model_id,
                "outcome_summary": outcome_summary,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "executed": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._model_runs[run_id] = record
            self._record(actor, "ext_record_model_run_reference", model_id)
            return copy.deepcopy(record)

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

    # -- Alerts, monitoring & detection (reference implementation) ----------------------

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
                "monitoring_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._alert_rules[rule_id] = record
            self._record(actor, "ext_create_alert_rule", rule_id,
                         details={"dataset_id": dataset_id})
            return copy.deepcopy(record)

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
        with self._lock:
            evaluation_id = self._next_id("ale")
            record = {
                "id": evaluation_id,
                "rule_id": rule_id,
                "statistic": rule["statistic"],
                "value": value,
                "op": rule["op"],
                "threshold": rule["threshold"],
                "breached": breached,
                "reference_stub": True,
                "method": "recorded_evaluation_over_core_describe",
                "evaluated_by": actor_name(actor),
                "evaluated_utc": _utc_now(),
            }
            self._alert_evaluations[evaluation_id] = record
            self._record(actor, "ext_record_alert_evaluation", rule_id,
                         details={"breached": breached})
            return copy.deepcopy(record)

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

    # -- Real-time / streaming analytics (reference implementation) ----------------------

    def register_stream_reference(self, name, source_ref, actor):
        """Register a stream reference record.

        Reference implementation only: no stream is opened, no event
        is consumed, and nothing is ingested through this surface.
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
                "streaming_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._streams[stream_id] = record
            self._record(actor, "ext_register_stream_reference", stream_id)
            return copy.deepcopy(record)

    def record_stream_batch_reference(self, stream_id, reported_row_count, actor):
        """Record a stream batch as reported; nothing is ingested."""
        self._guard(actor, "ingest", "ext_record_stream_batch_reference", stream_id)
        self._get(self._streams, stream_id, "stream reference")
        _validate_count(reported_row_count, "reported_row_count")
        with self._lock:
            batch_id = self._next_id("stmb")
            record = {
                "id": batch_id,
                "stream_id": stream_id,
                "reported_row_count": reported_row_count,
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "ingested_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._stream_batches[batch_id] = record
            self._record(actor, "ext_record_stream_batch_reference", stream_id,
                         details={"reported_row_count": reported_row_count})
            return copy.deepcopy(record)

    def stream_view(self, stream_id, actor):
        """Stream reference plus reported batch rollup, derived."""
        self._guard(actor, "query", "ext_stream_view", stream_id)
        record = self._get(self._streams, stream_id, "stream reference")
        with self._lock:
            batches = [copy.deepcopy(b) for b in self._stream_batches.values()
                       if b["stream_id"] == stream_id]
        record["batches"] = batches
        record["batch_count"] = len(batches)
        record["reported_rows_total"] = sum(b["reported_row_count"] for b in batches)
        return record

    # -- Proprietary-source connectors (reference implementation) -------------------------

    def register_connector_reference(self, name, source_kind, actor):
        """Register a proprietary-source connector reference record.

        Reference implementation only: nothing connects. Core ingest
        covers open CSV/JSON only, and this surface changes nothing
        about it; the record states what an external connector
        would be, labeled as a reference.
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
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connectors[connector_id] = record
            self._record(actor, "ext_register_connector_reference", connector_id,
                         details={"source_kind": source_kind})
            return copy.deepcopy(record)

    def record_connector_sync_reference(self, connector_id, reported_rows, actor):
        """Record a connector sync as reported; nothing is ingested."""
        self._guard(actor, "ingest", "ext_record_connector_sync_reference",
                    connector_id)
        self._get(self._connectors, connector_id, "connector reference")
        _validate_count(reported_rows, "reported_rows")
        with self._lock:
            sync_id = self._next_id("cons")
            record = {
                "id": sync_id,
                "connector_id": connector_id,
                "reported_rows": reported_rows,
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "ingested_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._connector_syncs[sync_id] = record
            self._record(actor, "ext_record_connector_sync_reference", connector_id,
                         details={"reported_rows": reported_rows})
            return copy.deepcopy(record)

    def connector_view(self, connector_id, actor):
        """Connector reference plus reported sync rollup, derived."""
        self._guard(actor, "query", "ext_connector_view", connector_id)
        record = self._get(self._connectors, connector_id, "connector reference")
        with self._lock:
            syncs = [copy.deepcopy(s) for s in self._connector_syncs.values()
                     if s["connector_id"] == connector_id]
        record["syncs"] = syncs
        record["sync_count"] = len(syncs)
        record["reported_rows_total"] = sum(s["reported_rows"] for s in syncs)
        return record
