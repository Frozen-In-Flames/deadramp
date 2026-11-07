"""Final GAPS batch extensions for the Operations Management L2 build.

Clean-room extension surface for the 13 OPEN Extended entries in
this group's section of the repo-root ``GAPS.md`` (the original
Group 36 section; the separate "Remainder Addition" section is a
different unit and is not touched or absorbed here). See
``BATCH.md`` in the group directory for the per-entry disposition.

Design, following the core's doctrines:

- This module wraps :class:`opsmgmt.store.OpsStore`; the core
  modules are untouched (byte-identical). Core records (projects,
  persons, assets, workflows) are always read through the core
  store's public API, never re-implemented.
- Nothing here executes, enforces, deploys, syncs, collects, hosts,
  or provides identity. The build-extension entries are built in
  their **records form**: registries of the thing, records of its
  reported state, and deterministic derivations over the group's
  own records. The two enforcement planes are policy /
  enforcement-point records with reported states
  (``enforced_here: False`` throughout), following the
  cybersecurity units' enforcement-point precedent. The low-code
  builder holds application definitions (components as data) plus
  deployment-intent records; nothing is built or deployed. Mobile
  sync is session and conflict records; no device syncs.
  Scheduling coverage is derived at read from roster/shift/
  assignment records. IoT devices are registration records keyed
  by opaque references (no identifier fields) plus reported
  reading records stored verbatim; nothing is collected here.
- The stub-engine entries ship as **labeled reference
  implementations**: every record they create carries
  ``reference_stub: True``; transport-shaped receipts (stream
  snapshots, connector runs) additionally carry
  ``reference_transport: True``. Workflow execution follows the
  house precedent: a run reference copies the core workflow
  definition as data and carries ``executed: False`` -- the
  registry never executes, here exactly as in the core.
- Identity stays with the embedding organization
  (PLATFORM-LAYER.md decision 1): the authorization-service entry
  is hook records only, carrying ``hook_only: True`` and
  ``identity_provider: False``. No build in this repo is an IdP.
- RBAC reuses the founding 16-action matrix with **no new
  actions**; each extension operation maps onto an existing core
  action, checked before any state change or id allocation for
  User-like actors, mirroring the core store's convention
  (plain-string actors carry identity but no role). Successful
  mutations are recorded on the core audit log with an
  ``ext_``-prefixed action name; denied attempts are recorded
  with the same name suffixed ``:denied`` before the denial
  propagates:

  ============================  ===============  ================
  surface                       write action     read action
  ============================  ===============  ================
  low-code apps / intents       workflow_write   workflow_read
  identity hooks                workflow_write   workflow_read
  policy definitions/assigns    workflow_write   workflow_read
  workflow run references       workflow_write   workflow_read
  mobile sync                   work_write       work_read
  security service points       work_write       work_read
  policy evaluations            work_write       workflow_read
  shift assignments/rosters     work_write       work_read
  connector references          work_write       work_read
  IoT devices                   asset_write      asset_read
  IoT readings                  usage_write      usage_read
  streams / models / platform   work_write       report_read
  governance references         work_write       report_read
  derived summaries/coverage    --               report_read
  ============================  ===============  ================

  (Configuration-shaped surfaces ride ``workflow_write`` -- the
  admin-only configuration write, as the core workflow registry
  does; operational records ride the matching operational write.)

- Derived values are derived at read and never stored: roster
  coverage, security-service coverage, sync / policy / telemetry /
  governance summaries, application deployment-intent counts.
  Stored records carry no derived key; tests pin that.
- All ``*_ref`` parameters naming things outside this build are
  opaque tokens: whitespace, URLs, hostnames, and IP-shaped values
  are rejected at the boundary, so a record cannot quietly carry a
  real system's address or a device identifier. Links into the
  core substrate use core ids (``proj-``, ``per-``, ``ast-``,
  ``wf-``), validated through the core store.
- Two guards are stated as named seams. ``_check_shift_overlap``:
  a person may not hold two active shift assignments whose
  windows overlap (the batch's fresh negative control).
  ``_check_evaluator_not_creator``: the actor who records a
  policy evaluation may never be the policy's creator
  (separation of duties).
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


_IP_LIKE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# -- option sets -------------------------------------------------------

SECURITY_SERVICE_KINDS = (
    "access_gateway",
    "endpoint_protection",
    "vulnerability_scanning",
    "logging_forwarding",
    "encryption_service",
    "other",
)
SECURITY_REPORTED_STATES = (
    "enforcing_reported",
    "degraded_reported",
    "offline_reported",
    "unknown",
)
POLICY_OUTCOMES = (
    "compliant_reported",
    "noncompliant_reported",
    "inconclusive",
)
DEVICE_KINDS = ("sensor", "tracker", "gateway", "vehicle_unit", "other")
SYNC_OUTCOMES = ("completed", "abandoned", "failed_reported")
SYNC_RESOLUTIONS = ("local_wins", "remote_wins", "merged", "deferred")
WORKFLOW_RUN_STATUSES = (
    "reported_running",
    "reported_completed",
    "reported_failed",
    "reported_cancelled",
)
STREAM_KINDS = ("event_stream", "metric_stream", "telemetry_stream", "other")
MODEL_KINDS = (
    "prediction",
    "classification",
    "optimization",
    "anomaly_detection",
    "other",
)
CONNECTOR_KINDS = ("api", "file", "database", "messaging", "other")
CONNECTOR_RUN_STATUSES = (
    "reported_success",
    "reported_partial",
    "reported_failed",
)
PLATFORM_SERVICE_KINDS = (
    "network_connectivity",
    "compute_hosting",
    "managed_platform",
    "other",
)
PLATFORM_OPERATION_STATUSES = (
    "reported_completed",
    "reported_failed",
    "reported_in_progress",
)
IDENTITY_HOOK_KINDS = (
    "sso",
    "mfa",
    "directory",
    "authorization_service",
    "pam",
    "iga",
)

# -- validation helpers --------------------------------------------------


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_ref(value, what):
    """Validate an opaque reference token.

    A reference names a thing in the caller's own world; it is
    never an address and never an identifier issued by a real
    system. Whitespace, URLs, hostnames, and IP-shaped values are
    rejected so records cannot carry a real system's location or
    a device identifier.
    """
    _validate_non_empty(value, what)
    if any(ch.isspace() for ch in value):
        raise ValidationError("%s must be an opaque reference (no spaces)" % (what,))
    if "://" in value or "/" in value or _IP_LIKE.match(value):
        raise ValidationError("%s must be an opaque reference, not an address" % (what,))
    if "." in value:
        raise ValidationError("%s must be an opaque reference, not a hostname" % (what,))
    if len(value) > 128:
        raise ValidationError("%s is too long for an opaque reference" % (what,))
    return value


def _validate_choice(value, options, what):
    if value not in options:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(options)))
    return value


def _validate_int(value, what, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    return value


def _validate_scalar(value, what):
    """A reported value stored verbatim: a string, integer, or
    float. Booleans, None, and containers are rejected -- a
    reported value is a scalar reading, not a document."""
    if isinstance(value, bool) or value is None or not isinstance(
        value, (str, int, float)
    ):
        raise ValidationError("%s must be a string, integer, or float" % (what,))
    return value


def _validate_counts(counts, what):
    if not isinstance(counts, dict) or not counts:
        raise ValidationError("%s must be a non-empty object of counts" % (what,))
    cleaned = {}
    for key, value in counts.items():
        _validate_non_empty(key, "%s key" % (what,))
        cleaned[key] = _validate_int(value, "%s[%s]" % (what, key), minimum=0)
    return cleaned


def _validate_components(components, what="components"):
    if components is None:
        return []
    if not isinstance(components, list):
        raise ValidationError("%s must be a list of component objects" % (what,))
    if len(components) > 100:
        raise ValidationError("%s may hold at most 100 entries" % (what,))
    cleaned = []
    for component in components:
        if not isinstance(component, dict):
            raise ValidationError("each entry in %s must be an object" % (what,))
        _validate_non_empty(component.get("kind"), "component kind")
        cleaned.append(copy.deepcopy(component))
    return cleaned


def _validate_string_list(value, what):
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
                "each entry in %s must be a non-empty string" % (what,)
            )
        result.append(item)
    return result


def _validate_optional_text(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string or None" % (what,))
    return value


def _parse_iso_datetime(value, what):
    """Parse an ISO-8601 datetime exactly as the core store does."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO-8601 datetime: %r" % (what, value)
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# -- guards (named seams) -------------------------------------------------


def _check_shift_overlap(existing_windows, new_window):
    """Overlap guard for shift assignments.

    ``existing_windows`` is the list of ``(starts_at, ends_at)``
    datetimes of the person's ACTIVE assignments; ``new_window``
    is the candidate shift's window. Windows are half-open:
    ``[starts_at, ends_at)`` -- a shift that ends exactly when
    another begins does not overlap it. A person may not hold two
    active assignments whose windows overlap; the guard is the
    load-bearing invariant behind ``assign_shift`` and the fresh
    negative control's mutation target for the gaps batch (see
    tests/README.md).
    """
    new_start, new_end = new_window
    for start, end in existing_windows:
        if new_start < end and start < new_end:
            raise ValidationError(
                "shift assignment overlaps an existing active assignment "
                "for this person"
            )


def _check_evaluator_not_creator(created_by, evaluator):
    """Separation-of-duties seam for policy evaluations.

    The actor who records a policy evaluation may never be the
    actor who created the policy.
    """
    if created_by is not None and evaluator is not None and created_by == evaluator:
        raise ValidationError(
            "policy evaluator must differ from the policy's creator (%r)"
            % (created_by,)
        )


class OpsExtensions:
    """GAPS-batch extension surface over a core OpsStore."""

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

        Mirrors the core store: an actor must be present;
        User-like actors are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only.
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

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            record["updated_utc"] = record["created_utc"]
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id, details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, collection, **filters):
        result = []
        for key in self._order:
            if key[0] != collection:
                continue
            record = self._records[key]
            if all(
                record.get(name) == value
                for name, value in filters.items()
                if value is not None
            ):
                result.append(copy.deepcopy(record))
        return result

    def _touch(self, record, actor, audit_action):
        record["updated_utc"] = _utc_now()
        self._audit(actor, audit_action, record["id"])

    # Core-record existence checks, read through the core store's
    # public API with no actor (internal reads; the caller's own
    # permission was already enforced by the guard).

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    def _core_person(self, person_id):
        return self.store.get_person(person_id)

    def _core_asset(self, asset_id):
        return self.store.get_asset(asset_id)

    def _core_workflow(self, workflow_id):
        return self.store.get_workflow(workflow_id)

    # -- Low-code application builder & deployment engine ------------
    # Records form: application definitions (components held as
    # data) plus deployment-intent records. Nothing is built,
    # compiled, rendered, or deployed by this build.

    def create_application(self, name, actor, project_id=None,
                           components=None, description=None):
        """Create a low-code application definition record.

        Action: workflow_write (configuration, as the core
        workflow registry). ``components`` are held verbatim as
        data; each must be an object with a non-empty ``kind``.
        """
        self._guard(actor, "workflow_write", "ext_app_create", name)
        _validate_non_empty(name, "application name")
        _validate_optional_text(description, "description")
        components = _validate_components(components)
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "application", "app",
            {
                "name": name,
                "project_id": project_id,
                "components": components,
                "description": description,
                "version": 1,
                "built_here": False,
                "deployed_here": False,
            },
            actor, "ext_app_create",
        )

    def update_application(self, app_id, actor, components=None,
                           description=None):
        """Replace an application definition's components and/or
        description, bumping its version. Action: workflow_write.
        The definition is data; updating it builds nothing."""
        self._guard(actor, "workflow_write", "ext_app_update", app_id)
        record = self._get("application", app_id)
        cleaned = None
        if components is not None:
            cleaned = _validate_components(components)
        _validate_optional_text(description, "description")
        with self._lock:
            if cleaned is not None:
                record["components"] = cleaned
            if description is not None:
                record["description"] = description
            record["version"] += 1
            self._touch(record, actor, "ext_app_update")
            return copy.deepcopy(record)

    def get_application(self, app_id, actor=None):
        """Read one application definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_app_read", app_id)
        return self._fetch("application", app_id)

    def list_applications(self, actor=None, project_id=None):
        """List application definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_app_read")
        return self._list("application", project_id=project_id)

    def record_deployment_intent(self, app_id, environment_ref, actor,
                                 note=None):
        """Record an intent to deploy an application definition to
        an environment named by an opaque reference.

        Action: workflow_write. The intent is a record only: it
        carries ``executed: False`` and ``deployed_here: False``,
        and recording it deploys nothing."""
        self._guard(actor, "workflow_write", "ext_app_deploy_intent", app_id)
        self._get("application", app_id)
        _validate_ref(environment_ref, "environment_ref")
        _validate_optional_text(note, "note")
        return self._create(
            "deployment_intent", "dep",
            {
                "application_id": app_id,
                "environment_ref": environment_ref,
                "status": "recorded",
                "executed": False,
                "deployed_here": False,
                "note": note,
            },
            actor, "ext_app_deploy_intent",
        )

    def list_deployment_intents(self, actor=None, application_id=None):
        """List deployment-intent records. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_app_read")
        return self._list("deployment_intent", application_id=application_id)

    def application_view(self, app_id, actor=None):
        """One application definition plus its derived
        deployment-intent count (derived at read, never stored on
        the definition record). Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_app_read", app_id)
        view = self._fetch("application", app_id)
        view["deployment_intent_count"] = len(
            self._list("deployment_intent", application_id=app_id)
        )
        return view

    # -- Mobile applications & offline sync ---------------------------
    # Records form: sync-session records and conflict records with
    # recorded states. No device syncs with this build; a recorded
    # resolution is data and is applied nowhere (applied_here:
    # False).

    def start_sync_session(self, device_ref, actor, client_ref=None,
                           note=None):
        """Open a sync-session record for an opaque device
        reference. Action: work_write. The session is a record of
        a sync relationship reported by the embedding system; no
        synchronization happens here."""
        self._guard(actor, "work_write", "ext_sync_start", device_ref)
        _validate_ref(device_ref, "device_ref")
        if client_ref is not None:
            _validate_ref(client_ref, "client_ref")
        _validate_optional_text(note, "note")
        return self._create(
            "sync_session", "syn",
            {
                "device_ref": device_ref,
                "client_ref": client_ref,
                "status": "open",
                "outcome": None,
                "note": note,
                "synced_here": False,
            },
            actor, "ext_sync_start",
        )

    def record_sync_conflict(self, session_id, actor, record_ref,
                             field_ref, local_value, remote_value):
        """Record a sync conflict on an open session, storing both
        reported values verbatim. Action: work_write."""
        self._guard(actor, "work_write", "ext_sync_conflict", session_id)
        session = self._get("sync_session", session_id)
        if session["status"] != "open":
            raise ValidationError(
                "sync session %r is not open" % (session_id,)
            )
        _validate_ref(record_ref, "record_ref")
        _validate_ref(field_ref, "field_ref")
        _validate_scalar(local_value, "local_value")
        _validate_scalar(remote_value, "remote_value")
        return self._create(
            "sync_conflict", "cnf",
            {
                "session_id": session_id,
                "record_ref": record_ref,
                "field_ref": field_ref,
                "local_value": local_value,
                "remote_value": remote_value,
                "resolution": None,
                "resolved_by": None,
                "applied_here": False,
            },
            actor, "ext_sync_conflict",
        )

    def resolve_sync_conflict(self, conflict_id, resolution, actor):
        """Record a resolution for a sync conflict. Action:
        work_write. The resolution is recorded as data; it is
        applied nowhere (``applied_here`` stays False)."""
        self._guard(actor, "work_write", "ext_sync_resolve", conflict_id)
        record = self._get("sync_conflict", conflict_id)
        _validate_choice(resolution, SYNC_RESOLUTIONS, "resolution")
        if record["resolution"] is not None:
            raise ValidationError(
                "sync conflict %r already has a recorded resolution"
                % (conflict_id,)
            )
        with self._lock:
            record["resolution"] = resolution
            record["resolved_by"] = actor_name(actor)
            self._touch(record, actor, "ext_sync_resolve")
            return copy.deepcopy(record)

    def close_sync_session(self, session_id, actor, outcome="completed"):
        """Close a sync-session record with a recorded outcome.
        Action: work_write."""
        self._guard(actor, "work_write", "ext_sync_close", session_id)
        record = self._get("sync_session", session_id)
        _validate_choice(outcome, SYNC_OUTCOMES, "outcome")
        if record["status"] != "open":
            raise ValidationError(
                "sync session %r is not open" % (session_id,)
            )
        with self._lock:
            record["status"] = "closed"
            record["outcome"] = outcome
            self._touch(record, actor, "ext_sync_close")
            return copy.deepcopy(record)

    def get_sync_session(self, session_id, actor=None):
        """Read one sync-session record. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_sync_read", session_id)
        return self._fetch("sync_session", session_id)

    def list_sync_sessions(self, actor=None, device_ref=None, status=None):
        """List sync-session records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_sync_read")
        return self._list("sync_session", device_ref=device_ref, status=status)

    def list_sync_conflicts(self, actor=None, session_id=None):
        """List sync-conflict records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_sync_read")
        return self._list("sync_conflict", session_id=session_id)

    def sync_summary(self, actor=None):
        """Derived sync counts (sessions by status, conflicts,
        unresolved conflicts). Derived at read, never stored.
        Action: report_read."""
        self._guard_read(actor, "report_read", "ext_sync_summary")
        sessions = self._list("sync_session")
        conflicts = self._list("sync_conflict")
        by_status = {}
        for session in sessions:
            by_status[session["status"]] = by_status.get(session["status"], 0) + 1
        return {
            "sessions": len(sessions),
            "sessions_by_status": by_status,
            "conflicts": len(conflicts),
            "conflicts_unresolved": len(
                [c for c in conflicts if c["resolution"] is None]
            ),
            "synced_here": False,
        }

    # -- Common security services enforcement plane -------------------
    # Records form, following the cybersecurity units'
    # enforcement-point precedent: a registry of enforcement
    # points plus state records as reported by the external
    # services. Nothing here enforces anything
    # (enforced_here: False on every record).

    def register_security_service_point(self, point_ref, kind, scope_ref,
                                        actor, policy_ref=None):
        """Register one security-service enforcement point (an
        access gateway, an endpoint-protection service, a scanning
        service) over opaque scope and policy references.
        Action: work_write."""
        self._guard(actor, "work_write", "ext_security_point_register",
                    point_ref)
        _validate_ref(point_ref, "point_ref")
        _validate_choice(kind, SECURITY_SERVICE_KINDS, "kind")
        _validate_ref(scope_ref, "scope_ref")
        if policy_ref is not None:
            _validate_ref(policy_ref, "policy_ref")
        return self._create(
            "security_point", "enf",
            {
                "point_ref": point_ref,
                "kind": kind,
                "scope_ref": scope_ref,
                "policy_ref": policy_ref,
                "status": "registered",
                "enforced_here": False,
            },
            actor, "ext_security_point_register",
        )

    def record_security_service_state(self, point_id, reported_state,
                                      actor, note=None):
        """Record the state of an enforcement point **as reported
        by the external service**. Action: work_write. The state
        is stored as reported, never computed, and recording it
        changes nothing outside this record."""
        self._guard(actor, "work_write", "ext_security_state_record",
                    point_id)
        self._get("security_point", point_id)
        _validate_choice(reported_state, SECURITY_REPORTED_STATES,
                         "reported_state")
        _validate_optional_text(note, "note")
        return self._create(
            "security_state", "enr",
            {
                "point_id": point_id,
                "reported_state": reported_state,
                "note": note,
                "enforced_here": False,
            },
            actor, "ext_security_state_record",
        )

    def retire_security_service_point(self, point_id, actor):
        """Retire a registered enforcement point record.
        Action: work_write."""
        self._guard(actor, "work_write", "ext_security_point_retire",
                    point_id)
        record = self._get("security_point", point_id)
        if record["status"] == "retired":
            raise ValidationError(
                "enforcement point %r is already retired" % (point_id,)
            )
        with self._lock:
            record["status"] = "retired"
            self._touch(record, actor, "ext_security_point_retire")
            return copy.deepcopy(record)

    def get_security_service_point(self, point_id, actor=None):
        """Read one enforcement point record. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_security_read", point_id)
        return self._fetch("security_point", point_id)

    def list_security_service_points(self, actor=None, kind=None,
                                     status=None):
        """List enforcement point records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_security_read")
        return self._list("security_point", kind=kind, status=status)

    def list_security_service_states(self, actor=None, point_id=None):
        """List reported-state records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_security_read")
        return self._list("security_state", point_id=point_id)

    def security_service_coverage(self, actor=None):
        """Derived coverage view: counts of registered enforcement
        points by kind and status, state records by reported
        state, and points with at least one state record. Derived
        at read, never stored. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_security_coverage")
        points = self._list("security_point")
        states = self._list("security_state")
        by_kind = {}
        by_status = {}
        for point in points:
            by_kind[point["kind"]] = by_kind.get(point["kind"], 0) + 1
            by_status[point["status"]] = by_status.get(point["status"], 0) + 1
        by_reported_state = {}
        for state in states:
            key = state["reported_state"]
            by_reported_state[key] = by_reported_state.get(key, 0) + 1
        return {
            "points": len(points),
            "points_by_kind": by_kind,
            "points_by_status": by_status,
            "state_records": len(states),
            "state_records_by_reported_state": by_reported_state,
            "points_with_state_records": len({s["point_id"] for s in states}),
            "enforced_here": False,
        }

    # -- Policy enforcement plane --------------------------------------
    # Records form: policy definitions and project assignments as
    # configuration records, plus evaluation records whose
    # outcomes are stored as reported by an external enforcement
    # plane. The registry records policies; the plane that would
    # enforce them is not here (enforced_here: False).

    def create_policy(self, name, rule_text, actor, project_id=None):
        """Create a policy definition record. Action:
        workflow_write (configuration, as the core workflow
        registry). ``rule_text`` is held verbatim as data; it is
        never evaluated by this build."""
        self._guard(actor, "workflow_write", "ext_policy_create", name)
        _validate_non_empty(name, "policy name")
        _validate_non_empty(rule_text, "rule_text")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "policy", "pol",
            {
                "name": name,
                "rule_text": rule_text,
                "project_id": project_id,
                "enforced_here": False,
            },
            actor, "ext_policy_create",
        )

    def assign_policy(self, policy_id, project_id, actor):
        """Assign a policy definition to a core project. Action:
        workflow_write. A duplicate active assignment of the same
        policy to the same project is a validation error."""
        self._guard(actor, "workflow_write", "ext_policy_assign", policy_id)
        self._get("policy", policy_id)
        self._core_project(project_id)
        for existing in self._list("policy_assignment", policy_id=policy_id,
                                   project_id=project_id):
            if existing["status"] == "active":
                raise ValidationError(
                    "policy %r is already assigned to project %r"
                    % (policy_id, project_id)
                )
        return self._create(
            "policy_assignment", "pas",
            {
                "policy_id": policy_id,
                "project_id": project_id,
                "status": "active",
                "enforced_here": False,
            },
            actor, "ext_policy_assign",
        )

    def record_policy_evaluation(self, policy_id, actor, outcome,
                                 project_id=None, note=None):
        """Record a policy evaluation outcome **as reported by an
        external enforcement plane**. Action: work_write. The
        outcome is stored as reported; the build evaluates no
        policy and enforces nothing. Separation of duties: the
        evaluator may never be the policy's creator
        (``_check_evaluator_not_creator``)."""
        self._guard(actor, "work_write", "ext_policy_evaluation", policy_id)
        policy = self._get("policy", policy_id)
        _check_evaluator_not_creator(policy["created_by"], actor_name(actor))
        _validate_choice(outcome, POLICY_OUTCOMES, "outcome")
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(note, "note")
        return self._create(
            "policy_evaluation", "pev",
            {
                "policy_id": policy_id,
                "project_id": project_id,
                "outcome": outcome,
                "note": note,
                "enforced_here": False,
            },
            actor, "ext_policy_evaluation",
        )

    def get_policy(self, policy_id, actor=None):
        """Read one policy definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_policy_read", policy_id)
        return self._fetch("policy", policy_id)

    def list_policies(self, actor=None, project_id=None):
        """List policy definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_policy_read")
        return self._list("policy", project_id=project_id)

    def list_policy_assignments(self, actor=None, policy_id=None,
                                project_id=None):
        """List policy assignment records. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_policy_read")
        return self._list("policy_assignment", policy_id=policy_id,
                          project_id=project_id)

    def list_policy_evaluations(self, actor=None, policy_id=None):
        """List policy evaluation records. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_policy_read")
        return self._list("policy_evaluation", policy_id=policy_id)

    def policy_summary(self, actor=None):
        """Derived policy counts (definitions, assignments,
        evaluations by outcome). Derived at read, never stored.
        Action: report_read."""
        self._guard_read(actor, "report_read", "ext_policy_summary")
        evaluations = self._list("policy_evaluation")
        by_outcome = {}
        for evaluation in evaluations:
            key = evaluation["outcome"]
            by_outcome[key] = by_outcome.get(key, 0) + 1
        return {
            "policies": len(self._list("policy")),
            "assignments": len(self._list("policy_assignment")),
            "evaluations": len(evaluations),
            "evaluations_by_outcome": by_outcome,
            "enforced_here": False,
        }

    # -- Scheduling & rostering -----------------------------------------
    # Records form for a named absence (0 of 2 claims): roster,
    # shift, and assignment records over the core directory.
    # Coverage is a deterministic derivation at read over those
    # records; the build schedules no one and notifies no one.

    def create_roster(self, name, actor, project_id=None):
        """Create a roster record. Action: work_write."""
        self._guard(actor, "work_write", "ext_roster_create", name)
        _validate_non_empty(name, "roster name")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "roster", "ros",
            {"name": name, "project_id": project_id},
            actor, "ext_roster_create",
        )

    def create_shift(self, roster_id, actor, starts_at, ends_at,
                     role_label=None, required_count=1):
        """Create a shift record on a roster. Action: work_write.
        ``ends_at`` must be after ``starts_at``; ``required_count``
        is the number of assignees the shift requires (an integer
        >= 1)."""
        self._guard(actor, "work_write", "ext_shift_create", roster_id)
        self._get("roster", roster_id)
        start_dt = _parse_iso_datetime(starts_at, "starts_at")
        end_dt = _parse_iso_datetime(ends_at, "ends_at")
        if end_dt <= start_dt:
            raise ValidationError("ends_at must be after starts_at")
        _validate_optional_text(role_label, "role_label")
        _validate_int(required_count, "required_count", minimum=1)
        return self._create(
            "shift", "shf",
            {
                "roster_id": roster_id,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "role_label": role_label,
                "required_count": required_count,
            },
            actor, "ext_shift_create",
        )

    def assign_shift(self, shift_id, person_id, actor):
        """Assign a core directory person to a shift. Action:
        work_write. Load-bearing guard: the person may not hold
        two ACTIVE assignments whose windows overlap
        (``_check_shift_overlap``); a duplicate active assignment
        to the same shift is a validation error."""
        self._guard(actor, "work_write", "ext_shift_assign", shift_id)
        shift = self._get("shift", shift_id)
        self._core_person(person_id)
        new_window = (
            _parse_iso_datetime(shift["starts_at"], "starts_at"),
            _parse_iso_datetime(shift["ends_at"], "ends_at"),
        )
        existing_windows = []
        for assignment in self._list("shift_assignment",
                                     person_id=person_id, status="active"):
            if assignment["shift_id"] == shift_id:
                raise ValidationError(
                    "person %r is already assigned to shift %r"
                    % (person_id, shift_id)
                )
            other = self._get("shift", assignment["shift_id"])
            existing_windows.append((
                _parse_iso_datetime(other["starts_at"], "starts_at"),
                _parse_iso_datetime(other["ends_at"], "ends_at"),
            ))
        _check_shift_overlap(existing_windows, new_window)
        return self._create(
            "shift_assignment", "sas",
            {
                "shift_id": shift_id,
                "roster_id": shift["roster_id"],
                "person_id": person_id,
                "status": "active",
            },
            actor, "ext_shift_assign",
        )

    def withdraw_shift_assignment(self, assignment_id, actor):
        """Withdraw an active shift assignment. Action:
        work_write. A withdrawn assignment frees the person's
        window for the overlap guard and no longer counts toward
        coverage."""
        self._guard(actor, "work_write", "ext_shift_withdraw", assignment_id)
        record = self._get("shift_assignment", assignment_id)
        if record["status"] != "active":
            raise ValidationError(
                "shift assignment %r is not active" % (assignment_id,)
            )
        with self._lock:
            record["status"] = "withdrawn"
            self._touch(record, actor, "ext_shift_withdraw")
            return copy.deepcopy(record)

    def get_roster(self, roster_id, actor=None):
        """Read one roster record. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_roster_read", roster_id)
        return self._fetch("roster", roster_id)

    def list_rosters(self, actor=None, project_id=None):
        """List roster records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_roster_read")
        return self._list("roster", project_id=project_id)

    def list_shifts(self, actor=None, roster_id=None):
        """List shift records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_shift_read")
        return self._list("shift", roster_id=roster_id)

    def list_shift_assignments(self, actor=None, shift_id=None,
                               person_id=None, status=None):
        """List shift assignment records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_shift_read")
        return self._list("shift_assignment", shift_id=shift_id,
                          person_id=person_id, status=status)

    def roster_coverage(self, roster_id, actor=None):
        """Derived coverage view for one roster: per shift, the
        active assignee count against the shift's required count,
        whether the shift is covered, and its shortfall; roster
        totals alongside. Derived at read from assignment
        records, never stored (the stored shift record carries no
        count). Action: report_read."""
        self._guard_read(actor, "report_read", "ext_roster_coverage",
                         roster_id)
        self._get("roster", roster_id)
        shifts = self._list("shift", roster_id=roster_id)
        assignments = self._list("shift_assignment", roster_id=roster_id,
                                 status="active")
        per_shift = []
        covered = 0
        for shift in shifts:
            assigned = len(
                [a for a in assignments if a["shift_id"] == shift["id"]]
            )
            is_covered = assigned >= shift["required_count"]
            if is_covered:
                covered += 1
            per_shift.append({
                "shift_id": shift["id"],
                "starts_at": shift["starts_at"],
                "ends_at": shift["ends_at"],
                "role_label": shift["role_label"],
                "required_count": shift["required_count"],
                "assigned_count": assigned,
                "covered": is_covered,
                "shortfall": max(0, shift["required_count"] - assigned),
            })
        return {
            "roster_id": roster_id,
            "shifts": per_shift,
            "shift_count": len(shifts),
            "covered_shift_count": covered,
            "active_assignment_count": len(assignments),
        }

    # -- IoT / telematics data collection --------------------------------
    # Records form for a named absence (0 of 2 claims):
    # device-registration records keyed by opaque references --
    # no record shape has a field for a device identifier -- plus
    # reported reading records stored verbatim. The build
    # collects nothing: readings arrive as reports from an
    # external collection path and are recorded
    # (collected_here: False).

    def register_device(self, device_ref, kind, actor, asset_id=None):
        """Register a telemetry device record under an opaque
        reference. Action: asset_write. ``asset_id`` optionally
        links the record to a core asset."""
        self._guard(actor, "asset_write", "ext_device_register", device_ref)
        _validate_ref(device_ref, "device_ref")
        _validate_choice(kind, DEVICE_KINDS, "kind")
        if asset_id is not None:
            self._core_asset(asset_id)
        return self._create(
            "device", "dev",
            {
                "device_ref": device_ref,
                "kind": kind,
                "asset_id": asset_id,
                "collected_here": False,
            },
            actor, "ext_device_register",
        )

    def record_telemetry_reading(self, device_id, metric, value, actor,
                                 reported_at=None):
        """Record a telemetry reading **as reported** for a
        registered device, storing the value verbatim. Action:
        usage_write (a metering-shaped record, as the core usage
        records are). The build collects nothing itself."""
        self._guard(actor, "usage_write", "ext_telemetry_record", device_id)
        self._get("device", device_id)
        _validate_non_empty(metric, "metric")
        _validate_scalar(value, "value")
        if reported_at is not None:
            _parse_iso_datetime(reported_at, "reported_at")
        return self._create(
            "telemetry_reading", "rdg",
            {
                "device_id": device_id,
                "metric": metric,
                "value": value,
                "reported_at": reported_at,
                "collected_here": False,
            },
            actor, "ext_telemetry_record",
        )

    def get_device(self, device_id, actor=None):
        """Read one device record. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_device_read", device_id)
        return self._fetch("device", device_id)

    def list_devices(self, actor=None, kind=None):
        """List device records. Action: asset_read."""
        self._guard_read(actor, "asset_read", "ext_device_read")
        return self._list("device", kind=kind)

    def list_telemetry_readings(self, actor=None, device_id=None,
                                metric=None):
        """List telemetry reading records. Action: usage_read."""
        self._guard_read(actor, "usage_read", "ext_telemetry_read")
        return self._list("telemetry_reading", device_id=device_id,
                          metric=metric)

    def telemetry_summary(self, actor=None):
        """Derived telemetry counts (devices by kind, readings by
        metric). Derived at read, never stored. Action:
        report_read."""
        self._guard_read(actor, "report_read", "ext_telemetry_summary")
        devices = self._list("device")
        readings = self._list("telemetry_reading")
        by_kind = {}
        for device in devices:
            by_kind[device["kind"]] = by_kind.get(device["kind"], 0) + 1
        by_metric = {}
        for reading in readings:
            by_metric[reading["metric"]] = by_metric.get(reading["metric"], 0) + 1
        return {
            "devices": len(devices),
            "devices_by_kind": by_kind,
            "readings": len(readings),
            "readings_by_metric": by_metric,
            "collected_here": False,
        }

    # -- Workflow automation execution engine (reference stub) ----------
    # House precedent: a run reference copies the core workflow's
    # current definition as data and is marked not executed. The
    # registry never executes -- here exactly as in the core, and
    # registering a run reference changes no core record.

    def register_workflow_run_reference(self, workflow_id, actor,
                                        reported_status="reported_completed",
                                        note=None):
        """Register a reference record of a workflow run reported
        by an external execution engine. Action: workflow_write.
        Carries ``reference_stub: True`` and ``executed: False``;
        the workflow's current definition is copied into the
        record as data."""
        self._guard(actor, "workflow_write", "ext_workflow_run_reference",
                    workflow_id)
        workflow = self._core_workflow(workflow_id)
        _validate_choice(reported_status, WORKFLOW_RUN_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        current = workflow["versions"][-1]
        return self._create(
            "workflow_run_reference", "wfr",
            {
                "workflow_id": workflow_id,
                "workflow_name": workflow["name"],
                "work_type": workflow["work_type"],
                "definition_version": workflow["version"],
                "definition_snapshot": {
                    "trigger_text": current["trigger_text"],
                    "action_text": current["action_text"],
                    "enabled": current["enabled"],
                },
                "reported_status": reported_status,
                "note": note,
                "reference_stub": True,
                "executed": False,
            },
            actor, "ext_workflow_run_reference",
        )

    def list_workflow_run_references(self, actor=None, workflow_id=None):
        """List workflow run reference records. Action:
        workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_workflow_run_read")
        return self._list("workflow_run_reference", workflow_id=workflow_id)

    # -- Real-time intelligence & analytics engine (reference stub) -----

    def register_stream_reference(self, stream_ref, kind, actor,
                                  scope_ref=None):
        """Register a reference record of an external real-time
        stream. Action: work_write. Carries ``reference_stub:
        True``; nothing streams through this build
        (``streamed_here: False``)."""
        self._guard(actor, "work_write", "ext_stream_register", stream_ref)
        _validate_ref(stream_ref, "stream_ref")
        _validate_choice(kind, STREAM_KINDS, "kind")
        if scope_ref is not None:
            _validate_ref(scope_ref, "scope_ref")
        return self._create(
            "stream_reference", "stm",
            {
                "stream_ref": stream_ref,
                "kind": kind,
                "scope_ref": scope_ref,
                "reference_stub": True,
                "streamed_here": False,
            },
            actor, "ext_stream_register",
        )

    def record_stream_snapshot_reference(self, stream_id, counts, actor,
                                         note=None):
        """Record a reference snapshot of stream output: counts
        exactly as reported by the external stream. Action:
        work_write. Carries ``reference_stub: True`` and
        ``reference_transport: True`` (the snapshot attests data
        movement reported by an external stream, not movement
        through this build); no analytics is computed here."""
        self._guard(actor, "work_write", "ext_stream_snapshot", stream_id)
        self._get("stream_reference", stream_id)
        counts = _validate_counts(counts, "counts")
        _validate_optional_text(note, "note")
        return self._create(
            "stream_snapshot", "snp",
            {
                "stream_id": stream_id,
                "counts": counts,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "computed_here": False,
            },
            actor, "ext_stream_snapshot",
        )

    def list_stream_references(self, actor=None, kind=None):
        """List stream reference records. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_stream_read")
        return self._list("stream_reference", kind=kind)

    def list_stream_snapshots(self, actor=None, stream_id=None):
        """List stream snapshot reference records. Action:
        report_read."""
        self._guard_read(actor, "report_read", "ext_stream_read")
        return self._list("stream_snapshot", stream_id=stream_id)

    # -- AI models (reference stub) --------------------------------------

    def register_model_reference(self, model_ref, kind, actor,
                                 project_id=None):
        """Register a reference record of an external AI model.
        Action: work_write. Carries ``reference_stub: True``; no
        model is loaded, trained, or run here
        (``trained_here: False``, ``inference_here: False``)."""
        self._guard(actor, "work_write", "ext_model_register", model_ref)
        _validate_ref(model_ref, "model_ref")
        _validate_choice(kind, MODEL_KINDS, "kind")
        if project_id is not None:
            self._core_project(project_id)
        return self._create(
            "model_reference", "mdl",
            {
                "model_ref": model_ref,
                "kind": kind,
                "project_id": project_id,
                "reference_stub": True,
                "trained_here": False,
                "inference_here": False,
            },
            actor, "ext_model_register",
        )

    def record_model_output_reference(self, model_id, label, actor,
                                      subject_ref=None):
        """Record a reference to one model output: the label
        exactly as the external model reported it. Action:
        work_write. The record shape has no score field -- an
        output's label is stored as reported and no confidence or
        grade is computed here."""
        self._guard(actor, "work_write", "ext_model_output", model_id)
        self._get("model_reference", model_id)
        _validate_non_empty(label, "label")
        if subject_ref is not None:
            _validate_ref(subject_ref, "subject_ref")
        return self._create(
            "model_output_reference", "mdo",
            {
                "model_id": model_id,
                "label": label,
                "subject_ref": subject_ref,
                "reference_stub": True,
            },
            actor, "ext_model_output",
        )

    def list_model_references(self, actor=None, kind=None):
        """List model reference records. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_model_read")
        return self._list("model_reference", kind=kind)

    def list_model_output_references(self, actor=None, model_id=None):
        """List model output reference records. Action:
        report_read."""
        self._guard_read(actor, "report_read", "ext_model_read")
        return self._list("model_output_reference", model_id=model_id)

    # -- Integration connector engines & catalog (reference stub) -------

    def register_connector_reference(self, connector_ref, kind, actor,
                                     target_ref=None):
        """Register a catalog reference record for an external
        integration connector. Action: work_write. Carries
        ``reference_stub: True``; nothing connects here
        (``connected_here: False``)."""
        self._guard(actor, "work_write", "ext_connector_register",
                    connector_ref)
        _validate_ref(connector_ref, "connector_ref")
        _validate_choice(kind, CONNECTOR_KINDS, "kind")
        if target_ref is not None:
            _validate_ref(target_ref, "target_ref")
        return self._create(
            "connector_reference", "con",
            {
                "connector_ref": connector_ref,
                "kind": kind,
                "target_ref": target_ref,
                "reference_stub": True,
                "connected_here": False,
            },
            actor, "ext_connector_register",
        )

    def record_connector_run_reference(self, connector_id,
                                       reported_status, actor,
                                       records_reported=None):
        """Record a reference to a connector run reported by an
        external connector engine. Action: work_write. Carries
        ``reference_stub: True`` and ``reference_transport:
        True``; no run executes and no record moves through this
        build (``executed_here: False``)."""
        self._guard(actor, "work_write", "ext_connector_run", connector_id)
        self._get("connector_reference", connector_id)
        _validate_choice(reported_status, CONNECTOR_RUN_STATUSES,
                         "reported_status")
        if records_reported is not None:
            _validate_int(records_reported, "records_reported", minimum=0)
        return self._create(
            "connector_run_reference", "cnr",
            {
                "connector_id": connector_id,
                "reported_status": reported_status,
                "records_reported": records_reported,
                "reference_stub": True,
                "reference_transport": True,
                "executed_here": False,
            },
            actor, "ext_connector_run",
        )

    def list_connector_references(self, actor=None, kind=None):
        """List connector reference records. Action: work_read."""
        self._guard_read(actor, "work_read", "ext_connector_read")
        return self._list("connector_reference", kind=kind)

    def list_connector_run_references(self, actor=None, connector_id=None):
        """List connector run reference records. Action:
        work_read."""
        self._guard_read(actor, "work_read", "ext_connector_read")
        return self._list("connector_run_reference",
                          connector_id=connector_id)

    # -- Network connectivity services & cloud platform operations ------
    # (reference stub; platform layer -- PLATFORM-LAYER.md
    # decision 6: a sibling's hosting substrate does not transfer)

    def register_platform_service_reference(self, service_ref, kind,
                                            actor, scope_ref=None):
        """Register a reference record of an external platform
        service (network connectivity, compute hosting, a managed
        platform). Action: work_write. Carries ``reference_stub:
        True``; nothing is hosted or operated here
        (``hosted_here: False``, ``operated_here: False``)."""
        self._guard(actor, "work_write", "ext_platform_service_register",
                    service_ref)
        _validate_ref(service_ref, "service_ref")
        _validate_choice(kind, PLATFORM_SERVICE_KINDS, "kind")
        if scope_ref is not None:
            _validate_ref(scope_ref, "scope_ref")
        return self._create(
            "platform_service_reference", "svc",
            {
                "service_ref": service_ref,
                "kind": kind,
                "scope_ref": scope_ref,
                "reference_stub": True,
                "hosted_here": False,
                "operated_here": False,
            },
            actor, "ext_platform_service_register",
        )

    def record_platform_operation_reference(self, service_id, operation,
                                            reported_status, actor):
        """Record a reference to a platform operation reported by
        an external platform operator. Action: work_write.
        Carries ``reference_stub: True``; no operation is
        performed here (``performed_here: False``)."""
        self._guard(actor, "work_write", "ext_platform_operation",
                    service_id)
        self._get("platform_service_reference", service_id)
        _validate_non_empty(operation, "operation")
        _validate_choice(reported_status, PLATFORM_OPERATION_STATUSES,
                         "reported_status")
        return self._create(
            "platform_operation_reference", "opr",
            {
                "service_id": service_id,
                "operation": operation,
                "reported_status": reported_status,
                "reference_stub": True,
                "performed_here": False,
            },
            actor, "ext_platform_operation",
        )

    def list_platform_service_references(self, actor=None, kind=None):
        """List platform service reference records. Action:
        report_read."""
        self._guard_read(actor, "report_read", "ext_platform_read")
        return self._list("platform_service_reference", kind=kind)

    def list_platform_operation_references(self, actor=None,
                                           service_id=None):
        """List platform operation reference records. Action:
        report_read."""
        self._guard_read(actor, "report_read", "ext_platform_read")
        return self._list("platform_operation_reference",
                          service_id=service_id)

    # -- Authorization service / identity provider (reference stub) -----
    # PLATFORM-LAYER.md decision 1: identity stays with the
    # embedding organization. This surface is hook records only --
    # it is not, and does not claim to be, an identity provider.

    def register_identity_hook(self, hook_ref, kind, actor, scope_ref=None):
        """Register an identity integration hook record. Action:
        workflow_write (configuration). The record carries
        ``hook_only: True``, ``identity_provider: False``, and
        ``reference_stub: True`` in its own shape: the build ships
        RBAC hooks, not an IdP."""
        self._guard(actor, "workflow_write", "ext_identity_hook_register",
                    hook_ref)
        _validate_ref(hook_ref, "hook_ref")
        _validate_choice(kind, IDENTITY_HOOK_KINDS, "kind")
        if scope_ref is not None:
            _validate_ref(scope_ref, "scope_ref")
        return self._create(
            "identity_hook", "idh",
            {
                "hook_ref": hook_ref,
                "kind": kind,
                "scope_ref": scope_ref,
                "hook_only": True,
                "identity_provider": False,
                "reference_stub": True,
            },
            actor, "ext_identity_hook_register",
        )

    def list_identity_hooks(self, actor=None, kind=None):
        """List identity hook records. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "ext_identity_hook_read")
        return self._list("identity_hook", kind=kind)

    # -- Governance / compliance console engine (reference stub) --------

    def register_governance_framework_reference(self, framework_ref, name,
                                                actor, control_refs=None):
        """Register a reference record of an external governance /
        compliance framework, with its control references held as
        data. Action: work_write. Carries ``reference_stub:
        True``; no continuous monitoring happens here
        (``monitored_here: False``)."""
        self._guard(actor, "work_write", "ext_governance_framework_register",
                    framework_ref)
        _validate_ref(framework_ref, "framework_ref")
        _validate_non_empty(name, "framework name")
        control_refs = _validate_string_list(control_refs, "control_refs")
        return self._create(
            "governance_framework_reference", "gov",
            {
                "framework_ref": framework_ref,
                "name": name,
                "control_refs": control_refs,
                "reference_stub": True,
                "monitored_here": False,
            },
            actor, "ext_governance_framework_register",
        )

    def record_compliance_snapshot_reference(self, framework_id, counts,
                                             actor, note=None):
        """Record a reference compliance snapshot: counts exactly
        as reported by an external console. Action: work_write.
        Carries ``reference_stub: True``; no posture score, rate,
        or grade is computed here (``computed_here: False``) --
        snapshots are counts as reported."""
        self._guard(actor, "work_write", "ext_compliance_snapshot",
                    framework_id)
        self._get("governance_framework_reference", framework_id)
        counts = _validate_counts(counts, "counts")
        _validate_optional_text(note, "note")
        return self._create(
            "compliance_snapshot_reference", "cmp",
            {
                "framework_id": framework_id,
                "counts": counts,
                "note": note,
                "reference_stub": True,
                "computed_here": False,
            },
            actor, "ext_compliance_snapshot",
        )

    def list_governance_frameworks(self, actor=None):
        """List governance framework reference records. Action:
        report_read."""
        self._guard_read(actor, "report_read", "ext_governance_read")
        return self._list("governance_framework_reference")

    def list_compliance_snapshots(self, actor=None, framework_id=None):
        """List compliance snapshot reference records. Action:
        report_read."""
        self._guard_read(actor, "report_read", "ext_governance_read")
        return self._list("compliance_snapshot_reference",
                          framework_id=framework_id)

    def governance_summary(self, actor=None):
        """Derived governance counts only: framework references,
        snapshot references, snapshots per framework. No score,
        rate, or grade key appears anywhere in the view. Derived
        at read, never stored. Action: report_read."""
        self._guard_read(actor, "report_read", "ext_governance_summary")
        frameworks = self._list("governance_framework_reference")
        snapshots = self._list("compliance_snapshot_reference")
        per_framework = {}
        for snapshot in snapshots:
            key = snapshot["framework_id"]
            per_framework[key] = per_framework.get(key, 0) + 1
        return {
            "frameworks": len(frameworks),
            "snapshots": len(snapshots),
            "snapshots_by_framework": per_framework,
            "monitored_here": False,
        }
