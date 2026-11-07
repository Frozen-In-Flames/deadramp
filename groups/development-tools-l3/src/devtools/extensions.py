"""Final GAPS batch extensions for the Development Tools
L3-adjacent singleton build (Remainder Singleton 58).

Clean-room, standard-library-only extensions for the 4 open
Extended entries of the GAPS.md section "Remainder Singleton 58
— Development Tools L3-adjacent (1 fork)" (see ``BATCH.md`` in
the group directory for the per-entry disposition). This module
wraps a :class:`~devtools.store.DevToolsStore`; every core
module is untouched and byte-identical to the shipped build.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records plus deterministic derivations over
the group's OWN records. Nothing in this module runs a
container, hosts an IDE, collects telemetry, provisions a
network, or calls an external system. The fork (Red Hat
OpenShift Service on AWS) is a managed container platform; this
build is the records substrate that platform's operation
presupposes, and the four entries land as follows:

- **Container orchestration platform** (idx 701, stub-engine)
  ships as a labeled reference implementation: cluster
  reference records plus outcome records whose status labels
  are the platform's own reports, stored verbatim. Every
  record carries ``reference_stub: True`` and
  ``orchestrated_here: False`` / ``containers_run_here:
  False`` — this build runs no containers.
- **Integrated development environment / developer
  workspace** (idx 702, build-extension) lands as workspace
  declaration records and session records, in the form the
  untiered sibling unit adjudicated for cloud development
  environments (idx 797 there): the records surface is built;
  hosting itself is a platform-layer property
  (PLATFORM-LAYER.md decision 6) and is not built —
  ``hosted_here: False``, ``provisioned_here: False``,
  ``filesystem_held_here: False`` on every record.
- **Platform monitoring & logging (observability)** (idx 703,
  stub-engine) ships as a labeled reference implementation:
  telemetry source records plus report records holding the
  reported summary labels and reported event counts verbatim.
  View totals are sums of the *recorded* counts, stated as
  such; nothing is collected or monitored here
  (``collected_here: False``, ``monitored_here: False``).
- **Platform networking** (idx 704, build-extension) lands as
  network configuration records held as data: route
  definitions and policy definitions bound to core
  environment records, plus route outcome records reported
  verbatim. The definitions are never applied
  (``applied_here: False``, ``provisioned_here: False``,
  ``enforced_here: False``) — the fabric itself, the actual
  network data plane, is the platform's infrastructure and is
  not built or claimed here.

Doctrines carried from the core: opaque ``*_ref`` strings
only; derived-never-stored for every computed value (views
derive counts, sums of recorded counts, and latest reported
labels at call time); validation fully before mutation, so a
failed operation consumes no id and changes nothing;
append-only audit on the core store's log with
``ext_``-prefixed actions for extension mutations and denied
attempts audited as ``<action>:denied``, exactly as the core
store does; RBAC via :mod:`devtools.access`, enforced before
any state change or id allocation. Plain-string actors carry
identity but no role, so — as in the core store — there is
nothing to enforce against at this layer for them.

High apparatus binds the extension: extension mutations write
to the core hash-chained audit log, and creation is
fail-closed in the core's AU-5 posture — if the audit append
raises, the new record and its id allocation roll back before
the error propagates (``_create``). The ``auditor`` role
holds ``audit_read`` only, so it is denied every extension
read and write (which ride operational actions) while its
core audit duty — reading and verifying the chain — works
unchanged.

RBAC action mapping (the core action set is fixed): cluster
references, cluster outcomes, telemetry sources, and
telemetry reports are platform-registry records about a
project and ride the project family (``project_write`` /
``project_read``), as the L2 unit's reference records did;
workspaces, workspace sessions, network routes, route
outcomes, and network policies are the environment surface
and ride the deployment family (``deployment_write`` /
``deployment_read``), as core environments and deployments do.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import _validate_non_empty, _validate_optional_str

WORKSPACE_ACCESS_MODES = ("browser", "ssh", "desktop_client")
WORKSPACE_SESSION_STATUSES = (
    "reported_active", "reported_idle", "reported_closed",
)
TELEMETRY_KINDS = ("metrics", "logs", "traces")
NETWORK_POLICY_EFFECTS = ("allow", "deny")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_access_modes(modes):
    if modes is None:
        return []
    if not isinstance(modes, list):
        raise ValidationError("access_modes must be a list")
    result = []
    for mode in modes:
        if mode not in WORKSPACE_ACCESS_MODES:
            raise ValidationError(
                "access mode must be one of %s"
                % (", ".join(WORKSPACE_ACCESS_MODES),)
            )
        if mode not in result:
            result.append(mode)
    return result


def _validate_non_negative_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be non-negative" % (what,))
    return value


def _validate_policy_rules(rules):
    """Normalize policy rules held as data: {rule_ref, effect}.

    Rule references must be unique within the policy; the
    effect is one of the recorded vocabulary. The rules are a
    definition — nothing evaluates or enforces them.
    """
    if not isinstance(rules, list) or not rules:
        raise ValidationError("policy rules must be a non-empty list")
    normalized = []
    seen = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValidationError("policy rule entries must be objects")
        rule_ref = _validate_non_empty(rule.get("rule_ref"), "rule_ref")
        effect = rule.get("effect")
        if effect not in NETWORK_POLICY_EFFECTS:
            raise ValidationError(
                "rule effect must be one of %s"
                % (", ".join(NETWORK_POLICY_EFFECTS),)
            )
        if rule_ref in seen:
            raise ValidationError("duplicate rule_ref %r" % (rule_ref,))
        seen.add(rule_ref)
        normalized.append({"rule_ref": rule_ref, "effect": effect})
    return normalized


class DevToolsExtensions:
    """Extension surface for the Singleton 58 final GAPS batch unit.

    Wraps a :class:`DevToolsStore`. All extension records live
    in this object; the core store's record sets are never
    written by this class (core records are only read, to bind
    extension records to real projects and environments, and to
    append to the core audit log).
    """

    def __init__(self, store):
        self.store = store
        self._clusters = {}
        self._cluster_outcomes = {}
        self._workspaces = {}
        self._workspace_sessions = {}
        self._telemetry_sources = {}
        self._telemetry_reports = {}
        self._network_routes = {}
        self._route_outcomes = {}
        self._network_policies = {}
        self._counters = {
            "clu": 0, "clo": 0, "wsp": 0, "wss": 0, "tsrc": 0,
            "trpt": 0, "nrt": 0, "nro": 0, "npl": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(
                actor_name(actor), action, target, details=details
            )

    def _enforce(self, actor, action, target):
        """Enforce for a User actor; audit the denied attempt, then raise."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, "%s:denied" % (action,), target)
                raise

    def _require_actor(self, actor, action, target):
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,)
            )
        self._enforce(actor, action, target)

    def _maybe_require(self, actor, action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, action)

    @staticmethod
    def _copy(record):
        return copy.deepcopy(record)

    def _get(self, table, record_id, what):
        rec = table.get(record_id)
        if rec is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return rec

    def _list(self, table, **filters):
        records = sorted(
            table.values(), key=lambda r: int(r["id"].rsplit("-", 1)[1])
        )
        for key, value in filters.items():
            if value is not None:
                records = [r for r in records if r.get(key) == value]
        return [self._copy(r) for r in records]

    def _create(self, table, prefix, fields, actor, audit_action,
                details=None):
        """Insert a record and audit it, fail closed [L3].

        The record is inserted and its id allocated, then the
        audit entry is appended to the core hash-chained log; if
        the append raises (AU-5), the insertion and the id roll
        back before the error propagates, mirroring the core
        store's fail-closed posture at this tier.
        """
        with self._lock:
            record_id = self._next_id(prefix)
            record = {"id": record_id}
            record.update(copy.deepcopy(fields))
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            table[record_id] = record
            try:
                self._audit(actor, audit_action, record_id,
                            details=details)
            except Exception:
                del table[record_id]
                self._counters[prefix] -= 1
                raise
            return self._copy(record)

    @staticmethod
    def _latest_label(records, key):
        """The latest recorded value of ``key`` over ``records``.

        ``records`` are in id (recording) order; the current
        reported label is the most recently recorded one. This
        is the batch unit's negative-control seam: an
        earliest-record derivation misstates every current
        label it feeds (the workspace, cluster, telemetry, and
        route views).
        """
        if not records:
            return None
        return records[-1][key]

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    def _core_environment(self, environment_id):
        return self.store.get_environment(environment_id)

    # -- Container orchestration platform (reference) -----------------

    def record_cluster_reference(self, project_id, name, actor,
                                 platform_ref=None):
        """Reference record for the container orchestration platform.

        Action: project_write. Points at the managed platform by
        opaque reference; no container is orchestrated or run
        here (``orchestrated_here: False``,
        ``containers_run_here: False``).
        """
        self._require_actor(actor, "project_write", project_id)
        _validate_non_empty(name, "cluster name")
        _validate_optional_str(platform_ref, "platform_ref")
        with self._lock:
            self._core_project(project_id)
            return self._create(
                self._clusters, "clu",
                {
                    "project_id": project_id,
                    "name": name,
                    "platform_ref": platform_ref,
                    "reference_stub": True,
                    "status": "recorded_reference_only",
                    "orchestrated_here": False,
                    "containers_run_here": False,
                    "managed_here": False,
                },
                actor, "ext_cluster_reference_record",
                details={"project_id": project_id, "name": name},
            )

    def get_cluster_reference(self, cluster_id, actor=None):
        """Return one cluster reference record. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._copy(
                self._get(self._clusters, cluster_id, "cluster reference")
            )

    def list_cluster_references(self, project_id=None, actor=None):
        """Return cluster reference records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._list(self._clusters, project_id=project_id)

    def record_cluster_outcome(self, cluster_id, status_label, actor,
                               workload_ref=None):
        """Record a cluster outcome reported by the platform.

        Action: project_write. The status label is the
        platform's own report, stored verbatim and never
        interpreted; the outcome changes no cluster state here
        (the stored reference record carries no status field).
        """
        self._require_actor(actor, "project_write", cluster_id)
        _validate_non_empty(status_label, "status_label")
        _validate_optional_str(workload_ref, "workload_ref")
        with self._lock:
            self._get(self._clusters, cluster_id, "cluster reference")
            return self._create(
                self._cluster_outcomes, "clo",
                {
                    "cluster_id": cluster_id,
                    "status_label": status_label,
                    "workload_ref": workload_ref,
                    "reference_stub": True,
                    "orchestrated_here": False,
                },
                actor, "ext_cluster_outcome_record",
                details={"cluster_id": cluster_id,
                         "status_label": status_label},
            )

    def list_cluster_outcomes(self, cluster_id, actor=None):
        """Return outcome records for one cluster. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            self._get(self._clusters, cluster_id, "cluster reference")
            return self._list(self._cluster_outcomes, cluster_id=cluster_id)

    def cluster_reference_view(self, cluster_id, actor=None):
        """Derive a cluster reference's reported state at read.

        Action: project_read. The outcome count and the latest
        reported status are computed at call time (via the
        ``_latest_label`` seam); the stored reference record
        carries no status field.
        """
        self._maybe_require(actor, "project_read")
        with self._lock:
            record = self._copy(
                self._get(self._clusters, cluster_id, "cluster reference")
            )
            outcomes = self._list(
                self._cluster_outcomes, cluster_id=cluster_id
            )
            record["outcome_count"] = len(outcomes)
            record["latest_reported_status"] = self._latest_label(
                outcomes, "status_label"
            )
            record["derived"] = True
            return record

    # -- Integrated development environment / developer workspace -----

    def create_workspace(self, project_id, name, actor, access_modes=None):
        """Declare a developer workspace. Action: deployment_write.

        A workspace is a declaration record bound to a core
        project: its name and the access modes recorded as
        labels. The workspace itself is hosted by an external
        platform — nothing is hosted, provisioned, or executed
        here, and no workspace filesystem is ever held
        (``hosted_here: False``, ``provisioned_here: False``,
        ``filesystem_held_here: False``).
        """
        self._require_actor(actor, "deployment_write", project_id)
        _validate_non_empty(name, "workspace name")
        modes = _validate_access_modes(access_modes)
        with self._lock:
            self._core_project(project_id)
            return self._create(
                self._workspaces, "wsp",
                {
                    "project_id": project_id,
                    "name": name,
                    "access_modes": modes,
                    "hosted_here": False,
                    "provisioned_here": False,
                    "filesystem_held_here": False,
                    "executed_here": False,
                },
                actor, "ext_workspace_create",
                details={"project_id": project_id, "name": name},
            )

    def get_workspace(self, workspace_id, actor=None):
        """Return one workspace record. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._copy(
                self._get(self._workspaces, workspace_id, "workspace")
            )

    def list_workspaces(self, project_id=None, actor=None):
        """Return workspace records. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._list(self._workspaces, project_id=project_id)

    def record_workspace_session(self, workspace_id, subject_ref,
                                 status_label, actor):
        """Record a workspace session as reported by the platform.

        Action: deployment_write. ``subject_ref`` is an opaque
        reference to the session's subject; the status is the
        platform's report from the recorded vocabulary, stored
        verbatim. The session itself runs on the external
        platform (``hosted_here: False``).
        """
        self._require_actor(actor, "deployment_write", workspace_id)
        _validate_non_empty(subject_ref, "subject_ref")
        if status_label not in WORKSPACE_SESSION_STATUSES:
            raise ValidationError(
                "status_label must be one of %s"
                % (", ".join(WORKSPACE_SESSION_STATUSES),)
            )
        with self._lock:
            self._get(self._workspaces, workspace_id, "workspace")
            return self._create(
                self._workspace_sessions, "wss",
                {
                    "workspace_id": workspace_id,
                    "subject_ref": subject_ref,
                    "status_label": status_label,
                    "hosted_here": False,
                },
                actor, "ext_workspace_session_record",
                details={"workspace_id": workspace_id,
                         "status_label": status_label},
            )

    def list_workspace_sessions(self, workspace_id, actor=None):
        """Return session records for one workspace.

        Action: deployment_read.
        """
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            self._get(self._workspaces, workspace_id, "workspace")
            return self._list(
                self._workspace_sessions, workspace_id=workspace_id
            )

    def workspace_view(self, workspace_id, actor=None):
        """Derive a workspace's reported state at read.

        Action: deployment_read. Session counts per reported
        status and the latest reported status are computed at
        call time (via the ``_latest_label`` seam); the stored
        workspace record carries no status field.
        """
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            record = self._copy(
                self._get(self._workspaces, workspace_id, "workspace")
            )
            sessions = self._list(
                self._workspace_sessions, workspace_id=workspace_id
            )
            by_status = {}
            for session in sessions:
                label = session["status_label"]
                by_status[label] = by_status.get(label, 0) + 1
            record["session_count"] = len(sessions)
            record["sessions_by_status"] = by_status
            record["latest_session_status"] = self._latest_label(
                sessions, "status_label"
            )
            record["derived"] = True
            return record

    # -- Platform monitoring & logging (reference) --------------------

    def record_telemetry_source(self, project_id, name, kind, actor,
                                source_ref=None):
        """Reference record for a platform telemetry source.

        Action: project_write. The source is the platform's own
        telemetry surface, named by opaque reference; nothing
        is collected or monitored here (``collected_here:
        False``, ``monitored_here: False``).
        """
        self._require_actor(actor, "project_write", project_id)
        _validate_non_empty(name, "telemetry source name")
        if kind not in TELEMETRY_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(TELEMETRY_KINDS),)
            )
        _validate_optional_str(source_ref, "source_ref")
        with self._lock:
            self._core_project(project_id)
            return self._create(
                self._telemetry_sources, "tsrc",
                {
                    "project_id": project_id,
                    "name": name,
                    "kind": kind,
                    "source_ref": source_ref,
                    "reference_stub": True,
                    "status": "recorded_reference_only",
                    "collected_here": False,
                    "monitored_here": False,
                },
                actor, "ext_telemetry_source_record",
                details={"project_id": project_id, "kind": kind},
            )

    def get_telemetry_source(self, source_id, actor=None):
        """Return one telemetry source record. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._copy(
                self._get(self._telemetry_sources, source_id,
                          "telemetry source")
            )

    def list_telemetry_sources(self, project_id=None, actor=None):
        """Return telemetry source records. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            return self._list(self._telemetry_sources,
                              project_id=project_id)

    def record_telemetry_report(self, source_id, summary_label, actor,
                                event_count=None):
        """Record a telemetry report as reported by the platform.

        Action: project_write. The summary label and the event
        count are the platform's own report, stored verbatim;
        the count is validated as a non-negative integer
        (bools and floats rejected). Nothing was collected
        here (``collected_here: False``).
        """
        self._require_actor(actor, "project_write", source_id)
        _validate_non_empty(summary_label, "summary_label")
        if event_count is not None:
            _validate_non_negative_int(event_count, "event_count")
        with self._lock:
            self._get(self._telemetry_sources, source_id,
                      "telemetry source")
            return self._create(
                self._telemetry_reports, "trpt",
                {
                    "source_id": source_id,
                    "summary_label": summary_label,
                    "event_count": event_count,
                    "reference_stub": True,
                    "collected_here": False,
                },
                actor, "ext_telemetry_report_record",
                details={"source_id": source_id,
                         "summary_label": summary_label},
            )

    def list_telemetry_reports(self, source_id, actor=None):
        """Return report records for one source. Action: project_read."""
        self._maybe_require(actor, "project_read")
        with self._lock:
            self._get(self._telemetry_sources, source_id,
                      "telemetry source")
            return self._list(self._telemetry_reports, source_id=source_id)

    def telemetry_source_view(self, source_id, actor=None):
        """Derive a telemetry source's reported totals at read.

        Action: project_read. ``total_reported_events`` is the
        sum of the *recorded* report counts — a sum of reports,
        stated as such, not a measurement; reports recorded
        without a count are tallied separately as
        ``reports_without_count`` rather than silently treated
        as zero. The latest summary label is derived via the
        ``_latest_label`` seam. The stored source record
        carries no totals.
        """
        self._maybe_require(actor, "project_read")
        with self._lock:
            record = self._copy(
                self._get(self._telemetry_sources, source_id,
                          "telemetry source")
            )
            reports = self._list(self._telemetry_reports,
                                 source_id=source_id)
            total = 0
            without_count = 0
            for report in reports:
                if report["event_count"] is None:
                    without_count += 1
                else:
                    total += report["event_count"]
            record["report_count"] = len(reports)
            record["total_reported_events"] = total
            record["reports_without_count"] = without_count
            record["latest_summary_label"] = self._latest_label(
                reports, "summary_label"
            )
            record["derived"] = True
            return record

    # -- Platform networking (configuration records) ------------------

    def define_network_route(self, environment_id, name, target_ref,
                             actor, host_label=None, path_label=None):
        """Define a network route as data. Action: deployment_write.

        A route definition is a configuration record bound to a
        core environment: a name, an opaque target reference,
        and optional host / path labels held as data. The
        definition is never applied to any fabric
        (``applied_here: False``, ``provisioned_here: False``);
        the platform's network data plane is not built here.
        """
        self._require_actor(actor, "deployment_write", environment_id)
        _validate_non_empty(name, "route name")
        _validate_non_empty(target_ref, "target_ref")
        _validate_optional_str(host_label, "host_label")
        _validate_optional_str(path_label, "path_label")
        with self._lock:
            self._core_environment(environment_id)
            return self._create(
                self._network_routes, "nrt",
                {
                    "environment_id": environment_id,
                    "name": name,
                    "target_ref": target_ref,
                    "host_label": host_label,
                    "path_label": path_label,
                    "applied_here": False,
                    "provisioned_here": False,
                },
                actor, "ext_network_route_define",
                details={"environment_id": environment_id, "name": name},
            )

    def get_network_route(self, route_id, actor=None):
        """Return one route definition. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._copy(
                self._get(self._network_routes, route_id, "network route")
            )

    def list_network_routes(self, environment_id=None, actor=None):
        """Return route definitions. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._list(self._network_routes,
                              environment_id=environment_id)

    def record_route_outcome(self, route_id, status_label, actor,
                             reporter_ref=None):
        """Record a route outcome reported by the platform.

        Action: deployment_write. The status label is the
        platform's own report, stored verbatim; recording it
        applies nothing (``applied_here: False``) and changes
        no route definition (the stored definition carries no
        status field).
        """
        self._require_actor(actor, "deployment_write", route_id)
        _validate_non_empty(status_label, "status_label")
        _validate_optional_str(reporter_ref, "reporter_ref")
        with self._lock:
            self._get(self._network_routes, route_id, "network route")
            return self._create(
                self._route_outcomes, "nro",
                {
                    "route_id": route_id,
                    "status_label": status_label,
                    "reporter_ref": reporter_ref,
                    "applied_here": False,
                },
                actor, "ext_route_outcome_record",
                details={"route_id": route_id,
                         "status_label": status_label},
            )

    def list_route_outcomes(self, route_id, actor=None):
        """Return outcome records for one route.

        Action: deployment_read.
        """
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            self._get(self._network_routes, route_id, "network route")
            return self._list(self._route_outcomes, route_id=route_id)

    def network_route_view(self, route_id, actor=None):
        """Derive a route's reported state at read.

        Action: deployment_read. The outcome count and the
        latest reported status are computed at call time (via
        the ``_latest_label`` seam); the stored definition
        carries no status field.
        """
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            record = self._copy(
                self._get(self._network_routes, route_id, "network route")
            )
            outcomes = self._list(self._route_outcomes, route_id=route_id)
            record["outcome_count"] = len(outcomes)
            record["latest_reported_status"] = self._latest_label(
                outcomes, "status_label"
            )
            record["derived"] = True
            return record

    def define_network_policy(self, environment_id, name, rules, actor):
        """Define a network policy as data. Action: deployment_write.

        A policy definition is a configuration record bound to
        a core environment: an ordered list of rules held as
        data (``{rule_ref, effect}``). The definition is never
        evaluated or enforced against any traffic
        (``enforced_here: False``, ``applied_here: False``).
        """
        self._require_actor(actor, "deployment_write", environment_id)
        _validate_non_empty(name, "policy name")
        normalized = _validate_policy_rules(rules)
        with self._lock:
            self._core_environment(environment_id)
            return self._create(
                self._network_policies, "npl",
                {
                    "environment_id": environment_id,
                    "name": name,
                    "rules": normalized,
                    "enforced_here": False,
                    "applied_here": False,
                },
                actor, "ext_network_policy_define",
                details={"environment_id": environment_id, "name": name},
            )

    def get_network_policy(self, policy_id, actor=None):
        """Return one policy definition. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._copy(
                self._get(self._network_policies, policy_id,
                          "network policy")
            )

    def list_network_policies(self, environment_id=None, actor=None):
        """Return policy definitions. Action: deployment_read."""
        self._maybe_require(actor, "deployment_read")
        with self._lock:
            return self._list(self._network_policies,
                              environment_id=environment_id)
