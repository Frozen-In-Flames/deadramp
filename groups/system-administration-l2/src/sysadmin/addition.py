"""Final GAPS batch addition for System Administration L2.

Clean-room, standard-library-only extension surface for the 9 open
entries of the GAPS.md section "Remainder Addition -- System
Administration L2 (+8 forks)" (inventory idx 552-560; see
``BATCH-ADDITION.md`` in the group directory for the per-entry
disposition). This module is a wrapper around
:class:`SysadminStore`; every core module is untouched and
byte-identical to the shipped build, and this is the second batch
unit in the directory (the founding section's unit, when it lands,
keeps its own module).

Honesty of form, per the batch brief: each addition fork's engine
closes here as a records surface over this group's OWN records
substrate (customer organizations, managed systems, applications).
Nothing in this module delivers a desktop, discovers a device,
renders a map, scans a network, backs anything up, or computes a
score:

- Virtual workspace & desktop delivery is workspace/desktop
  DEFINITIONS held as data plus delivery-session records with
  verbatim reported outcomes (``delivered_here: False``). No
  session is brokered or delivered here.
- ITSM / ITAM is ticket and asset records whose current state
  derives at read from recorded state labels, in the group's
  records form; no service-desk workflow executes here.
- Universal discovery & CMDB is discovery-job records plus
  configuration-item records held as REPORTED data
  (``discovered_here: False``): a CI record is a report filed by
  the caller's discovery tooling, not a scan result produced
  here. Dependency mapping is relationship records between
  reported CIs.
- Project & portfolio management is portfolio and project
  records with counts derived at read. No portfolio score,
  ranking, or optimization value is computed anywhere.
- DEX analytics is endpoint-experience reports held verbatim
  (the vendor's own experience score is an engine output; when a
  caller reports one it arrives inside the verbatim report label
  and is never computed, averaged, or re-derived here) plus
  automation DEFINITIONS as data and automation-request records
  (``executed_here: False``).
- The GIS platform is dataset and layer records as metadata
  carrying an opaque ``geometry_ref`` only (``rendered_here:
  False``). No entity shape has a field that can hold geometry
  content or coordinates, so none can be stored here.
- Security operations is case and finding records held verbatim
  (severity is a reported label, never a computed value;
  ``scanning_here: False``, ``detected_here: False``): findings
  are reports of the operating service's work, not detections
  made by this substrate.
- The two stub-engine entries ship as labeled reference
  implementations: every record carries ``reference_stub: True``
  and state ``recorded_reference_only``. Observability / AIOps
  holds telemetry-source records and reported insight references
  (``observed_here: False``, ``inferred_here: False``). Managed
  backup & DR holds backup-job and restore-request records with
  verbatim outcomes (``backed_up_here: False``,
  ``restored_here: False``); retention enforcement is the
  embedding organization's records schedule at the deployment
  layer (PLATFORM-LAYER.md decision 4) and is not performed or
  claimed here.

Doctrines carried from the core: derived-never-stored for every
computed value (current ticket / asset / project / case state,
all summary counts); opaque references only -- no entity shape
has a field for a hostname, address, credential, geometry, or
any live-system identifier; validation before mutation, so a
failed operation consumes no id and changes nothing; append-only
audit on the core store's log with ``ext_``-prefixed actions for
every successful extension mutation, and denied write attempts
recorded with a ``:denied`` suffix; RBAC via
:mod:`sysadmin.access` -- extension writes map to the core
``enter`` action, and organization membership (the fork's
contract-gated access boundary) is enforced by resolving the
organization through the core store on every operation.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

DELIVERY_KINDS = ("desktop", "application", "bundle")
TELEMETRY_SOURCE_KINDS = ("metrics", "traces", "logs", "runtime_security", "other")
TICKET_KINDS = ("incident", "problem", "service_request", "change_request", "other")
TICKET_STATES = (
    "reported_open", "reported_in_progress", "reported_resolved",
    "reported_closed",
)
ASSET_KINDS = ("hardware", "software", "license", "peripheral", "other")
ASSET_STATES = (
    "reported_in_service", "reported_in_storage", "reported_under_repair",
    "reported_retired",
)
PROJECT_STATES = (
    "reported_proposed", "reported_active", "reported_on_hold",
    "reported_completed", "reported_cancelled",
)
DATASET_KINDS = ("vector", "raster", "imagery", "tabular", "other")
CASE_KINDS = ("alert", "incident", "vulnerability", "other")
CASE_STATES = (
    "reported_open", "reported_triaged", "reported_contained",
    "reported_closed",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _count(value, field):
    """A non-negative integer count of reported things; bools/floats rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (field,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (field,))
    return value


class SysadminAddition:
    """GAPS-batch extension surface wrapping one :class:`SysadminStore`."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._counters = {}
        # idx 552 -- virtual workspace & desktop delivery
        self._workspace_definitions = {}
        self._delivery_sessions = {}
        # idx 553 -- observability & AIOps (reference stub)
        self._telemetry_sources = {}
        self._insight_reports = {}
        # idx 554 -- ITSM / ITAM
        self._tickets = {}
        self._ticket_states = {}
        self._assets = {}
        self._asset_states = {}
        # idx 555 -- discovery & CMDB
        self._discovery_jobs = {}
        self._config_items = {}
        self._ci_relationships = {}
        # idx 556 -- project & portfolio management
        self._portfolios = {}
        self._projects = {}
        self._project_states = {}
        # idx 557 -- DEX analytics & endpoint automation
        self._experience_reports = {}
        self._automation_definitions = {}
        self._automation_requests = {}
        # idx 558 -- geospatial (GIS) platform
        self._gis_datasets = {}
        self._gis_layers = {}
        self._gis_services = {}
        # idx 559 -- managed backup & DR (reference stub)
        self._backup_jobs = {}
        self._backup_outcomes = {}
        self._restore_requests = {}
        # idx 560 -- security operations services
        self._security_cases = {}
        self._case_states = {}
        self._security_findings = {}

    # -- internal helpers ---------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor, action, target, details)

    def _guard(self, actor, audit_action):
        """Enforce the extension write permission before any mutation.

        Extension writes map to the core ``enter`` action. A denied
        attempt is recorded on the audit log with a ``:denied``
        suffix before the error propagates; a missing actor is
        denied outright. A plain string carries identity but no
        role (the service layer enforces its role), matching the
        core convention.
        """
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for 'enter'")
        if hasattr(actor, "role"):
            try:
                require(actor, "enter")
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": "enter"})
                raise

    def _org(self, actor, org_id):
        """Resolve an organization through the core store.

        The core enforces the ``read`` role permission and the
        organization membership boundary (or platform admin) and
        raises NotFoundError for an unknown organization.
        """
        return self.store.get_organization(actor, org_id)

    def _system_in_org(self, actor, org_id, system_id):
        system = self.store.get_system(actor, system_id)
        if system["org_id"] != org_id:
            raise ValidationError("system belongs to another organization")
        return system

    @staticmethod
    def _latest_state_label(state_records):
        """The current state of a record: its latest recorded label.

        State records are append-only and kept in recording order;
        the current state is the LAST label recorded, or
        ``recorded`` when no state has been recorded yet. This
        derivation is the batch unit's fresh negative-control seam
        (see tests/README.md): reading the earliest label instead
        would resurrect superseded states.
        """
        if not state_records:
            return "recorded"
        return state_records[-1]["state_label"]

    def _state_view(self, record, state_records):
        view = dict(record)
        view["current_state"] = self._latest_state_label(state_records)
        return view

    def _states_for(self, table, key, record_id):
        return [r for r in table.values() if r[key] == record_id]

    def _record_state(self, actor, org_id, table, prefix, key, record_id,
                      state_label, allowed, action, id_field="id"):
        self._guard(actor, action)
        self._org(actor, org_id)
        if state_label not in allowed:
            raise ValidationError(
                "state_label must be one of %r" % (allowed,))
        with self._lock:
            record = {
                id_field: self._mint(prefix),
                "org_id": org_id,
                key: record_id,
                "state_label": state_label,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            table[record[id_field]] = record
        self._audit(actor, action, record[id_field],
                    {"state_label": state_label})
        return dict(record)

    # -- idx 552: virtual workspace & desktop delivery -----------------------

    def create_workspace_definition(self, actor, org_id, ref, label,
                                    delivery_kind):
        """Record a virtual workspace/desktop definition as data.

        The definition describes what the delivery platform would
        serve; nothing is delivered, brokered, or provisioned
        here (``delivered_here: False`` on every record).
        """
        action = "ext_workspace_definition_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        if delivery_kind not in DELIVERY_KINDS:
            raise ValidationError(
                "delivery_kind must be one of %r" % (DELIVERY_KINDS,))
        with self._lock:
            for existing in self._workspace_definitions.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "workspace definition ref already exists in this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("wsd-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "delivery_kind": delivery_kind,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workspace_definitions[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _workspace_definition(self, definition_id):
        record = self._workspace_definitions.get(definition_id)
        if record is None:
            raise NotFoundError(
                "no such workspace definition: %r" % (definition_id,))
        return record

    def get_workspace_definition(self, actor, definition_id):
        record = self._workspace_definition(definition_id)
        self._org(actor, record["org_id"])
        return dict(record)

    def list_workspace_definitions(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._workspace_definitions.values()
                if r["org_id"] == org_id]

    def record_delivery_session(self, actor, org_id, definition_id,
                                session_ref, user_ref, outcome_label):
        """Record one reported delivery session, outcome verbatim.

        ``user_ref`` is an opaque caller-supplied reference; no
        identity is resolved and no session is established here.
        """
        action = "ext_delivery_session_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        definition = self._workspace_definition(definition_id)
        if definition["org_id"] != org_id:
            raise ValidationError(
                "workspace definition belongs to another organization")
        _text(session_ref, "session_ref")
        _text(user_ref, "user_ref")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("dss-"),
                "org_id": org_id,
                "definition_id": definition_id,
                "session_ref": session_ref,
                "user_ref": user_ref,
                "outcome_label": outcome_label,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._delivery_sessions[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"definition_id": definition_id})
        return dict(record)

    def list_delivery_sessions(self, actor, org_id, definition_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._delivery_sessions.values()
                if r["org_id"] == org_id
                and (definition_id is None
                     or r["definition_id"] == definition_id)]

    def delivery_summary(self, actor, org_id):
        """Counts only, derived at read: definitions by kind,
        sessions by verbatim outcome label."""
        self._org(actor, org_id)
        by_kind = {kind: 0 for kind in DELIVERY_KINDS}
        for record in self._workspace_definitions.values():
            if record["org_id"] == org_id:
                by_kind[record["delivery_kind"]] += 1
        by_outcome = {}
        sessions = 0
        for record in self._delivery_sessions.values():
            if record["org_id"] == org_id:
                sessions += 1
                by_outcome[record["outcome_label"]] = \
                    by_outcome.get(record["outcome_label"], 0) + 1
        return {
            "org_id": org_id,
            "workspace_definitions": sum(by_kind.values()),
            "definitions_by_kind": by_kind,
            "delivery_sessions": sessions,
            "sessions_by_outcome": by_outcome,
        }

    # -- idx 553: observability & AIOps (reference stub) ----------------------

    def create_telemetry_source(self, actor, org_id, ref, label, source_kind):
        """Record a telemetry source as a labeled reference.

        Reference implementation only: no telemetry is collected
        or observed here (``observed_here: False``).
        """
        action = "ext_telemetry_source_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        if source_kind not in TELEMETRY_SOURCE_KINDS:
            raise ValidationError(
                "source_kind must be one of %r" % (TELEMETRY_SOURCE_KINDS,))
        with self._lock:
            record = {
                "id": self._mint("obs-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "source_kind": source_kind,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "observed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._telemetry_sources[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _telemetry_source(self, source_id):
        record = self._telemetry_sources.get(source_id)
        if record is None:
            raise NotFoundError("no such telemetry source: %r" % (source_id,))
        return record

    def record_insight_report(self, actor, org_id, source_id, report_ref,
                              outcome_label):
        """Record a reported AI insight as an opaque reference.

        The insight itself is the platform's engine output; here
        it exists only as the caller's ``report_ref`` and a
        verbatim outcome label (``inferred_here: False``).
        """
        action = "ext_insight_report_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        source = self._telemetry_source(source_id)
        if source["org_id"] != org_id:
            raise ValidationError(
                "telemetry source belongs to another organization")
        _text(report_ref, "report_ref")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("ins-"),
                "org_id": org_id,
                "source_id": source_id,
                "report_ref": report_ref,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "inferred_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._insight_reports[record["id"]] = record
        self._audit(actor, action, record["id"], {"source_id": source_id})
        return dict(record)

    def list_telemetry_sources(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._telemetry_sources.values()
                if r["org_id"] == org_id]

    def list_insight_reports(self, actor, org_id, source_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._insight_reports.values()
                if r["org_id"] == org_id
                and (source_id is None or r["source_id"] == source_id)]

    # -- idx 554: ITSM / ITAM ---------------------------------------------------

    def create_service_ticket(self, actor, org_id, ref, summary, ticket_kind,
                              system_id=None):
        """Record a service-desk ticket against an organization.

        The ticket's current state is never stored on the ticket;
        it derives at read from recorded state labels (see
        :meth:`record_ticket_state`). Recording a ticket performs
        no service-desk work.
        """
        action = "ext_service_ticket_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(summary, "summary")
        if ticket_kind not in TICKET_KINDS:
            raise ValidationError(
                "ticket_kind must be one of %r" % (TICKET_KINDS,))
        if system_id is not None:
            self._system_in_org(actor, org_id, system_id)
        with self._lock:
            for existing in self._tickets.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "ticket ref already exists in this organization: %r"
                        % (ref,))
            record = {
                "id": self._mint("tkt-"),
                "org_id": org_id,
                "ref": ref,
                "summary": summary,
                "ticket_kind": ticket_kind,
                "system_id": system_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._tickets[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _ticket(self, ticket_id):
        record = self._tickets.get(ticket_id)
        if record is None:
            raise NotFoundError("no such service ticket: %r" % (ticket_id,))
        return record

    def record_ticket_state(self, actor, org_id, ticket_id, state_label):
        """Append one reported state label to a ticket."""
        ticket = self._ticket(ticket_id)
        if ticket["org_id"] != org_id:
            raise ValidationError("ticket belongs to another organization")
        return self._record_state(
            actor, org_id, self._ticket_states, "tkts-", "ticket_id",
            ticket_id, state_label, TICKET_STATES,
            "ext_service_ticket_state_record")

    def get_service_ticket(self, actor, ticket_id):
        ticket = self._ticket(ticket_id)
        self._org(actor, ticket["org_id"])
        return self._state_view(
            ticket, self._states_for(self._ticket_states, "ticket_id",
                                     ticket_id))

    def list_service_tickets(self, actor, org_id, ticket_kind=None):
        self._org(actor, org_id)
        return [
            self._state_view(t, self._states_for(
                self._ticket_states, "ticket_id", t["id"]))
            for t in self._tickets.values()
            if t["org_id"] == org_id
            and (ticket_kind is None or t["ticket_kind"] == ticket_kind)
        ]

    def create_asset_record(self, actor, org_id, ref, label, asset_kind,
                            system_id=None):
        """Record an IT asset. Its current state derives at read
        from recorded state labels, exactly as for tickets."""
        action = "ext_asset_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        if asset_kind not in ASSET_KINDS:
            raise ValidationError(
                "asset_kind must be one of %r" % (ASSET_KINDS,))
        if system_id is not None:
            self._system_in_org(actor, org_id, system_id)
        with self._lock:
            for existing in self._assets.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "asset ref already exists in this organization: %r"
                        % (ref,))
            record = {
                "id": self._mint("ast-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "asset_kind": asset_kind,
                "system_id": system_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assets[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _asset(self, asset_id):
        record = self._assets.get(asset_id)
        if record is None:
            raise NotFoundError("no such asset record: %r" % (asset_id,))
        return record

    def record_asset_state(self, actor, org_id, asset_id, state_label):
        """Append one reported state label to an asset record."""
        asset = self._asset(asset_id)
        if asset["org_id"] != org_id:
            raise ValidationError("asset belongs to another organization")
        return self._record_state(
            actor, org_id, self._asset_states, "asts-", "asset_id",
            asset_id, state_label, ASSET_STATES, "ext_asset_state_record")

    def get_asset_record(self, actor, asset_id):
        asset = self._asset(asset_id)
        self._org(actor, asset["org_id"])
        return self._state_view(
            asset, self._states_for(self._asset_states, "asset_id", asset_id))

    def list_asset_records(self, actor, org_id, asset_kind=None):
        self._org(actor, org_id)
        return [
            self._state_view(a, self._states_for(
                self._asset_states, "asset_id", a["id"]))
            for a in self._assets.values()
            if a["org_id"] == org_id
            and (asset_kind is None or a["asset_kind"] == asset_kind)
        ]

    def itsm_summary(self, actor, org_id):
        """Counts only, derived at read: tickets and assets by kind
        and by derived current state."""
        self._org(actor, org_id)
        tickets_by_kind = {kind: 0 for kind in TICKET_KINDS}
        tickets_by_state = {}
        for ticket in self._tickets.values():
            if ticket["org_id"] != org_id:
                continue
            tickets_by_kind[ticket["ticket_kind"]] += 1
            state = self._latest_state_label(self._states_for(
                self._ticket_states, "ticket_id", ticket["id"]))
            tickets_by_state[state] = tickets_by_state.get(state, 0) + 1
        assets_by_kind = {kind: 0 for kind in ASSET_KINDS}
        assets_by_state = {}
        for asset in self._assets.values():
            if asset["org_id"] != org_id:
                continue
            assets_by_kind[asset["asset_kind"]] += 1
            state = self._latest_state_label(self._states_for(
                self._asset_states, "asset_id", asset["id"]))
            assets_by_state[state] = assets_by_state.get(state, 0) + 1
        return {
            "org_id": org_id,
            "tickets": sum(tickets_by_kind.values()),
            "tickets_by_kind": tickets_by_kind,
            "tickets_by_current_state": tickets_by_state,
            "assets": sum(assets_by_kind.values()),
            "assets_by_kind": assets_by_kind,
            "assets_by_current_state": assets_by_state,
        }

    # -- idx 555: universal discovery & CMDB -------------------------------------

    def create_discovery_job(self, actor, org_id, ref, label, scope_ref):
        """Record a discovery job. The job is a record of work the
        caller's discovery engine performs elsewhere; nothing is
        discovered here (``discovered_here: False``)."""
        action = "ext_discovery_job_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        _text(scope_ref, "scope_ref")
        with self._lock:
            record = {
                "id": self._mint("dcj-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "scope_ref": scope_ref,
                "discovered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._discovery_jobs[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _discovery_job(self, job_id):
        record = self._discovery_jobs.get(job_id)
        if record is None:
            raise NotFoundError("no such discovery job: %r" % (job_id,))
        return record

    def record_configuration_item(self, actor, org_id, job_id, ci_ref, label,
                                  ci_kind, reported_state):
        """Record one configuration item as REPORTED data.

        A CI record is a report filed against a discovery job; it
        is held verbatim and is not a scan result produced here
        (``discovered_here: False``). ``ci_kind`` and
        ``reported_state`` are caller-supplied labels from the
        reporting tool's own vocabulary, carried as data.
        """
        action = "ext_configuration_item_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        job = self._discovery_job(job_id)
        if job["org_id"] != org_id:
            raise ValidationError(
                "discovery job belongs to another organization")
        _text(ci_ref, "ci_ref")
        _text(label, "label")
        _text(ci_kind, "ci_kind")
        _text(reported_state, "reported_state")
        with self._lock:
            for existing in self._config_items.values():
                if (existing["org_id"] == org_id
                        and existing["ci_ref"] == ci_ref):
                    raise ValidationError(
                        "configuration item ref already exists in this "
                        "organization: %r" % (ci_ref,))
            record = {
                "id": self._mint("cir-"),
                "org_id": org_id,
                "job_id": job_id,
                "ci_ref": ci_ref,
                "label": label,
                "ci_kind": ci_kind,
                "reported_state": reported_state,
                "discovered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._config_items[record["id"]] = record
        self._audit(actor, action, record["id"], {"ci_ref": ci_ref})
        return dict(record)

    def _config_item(self, ci_id):
        record = self._config_items.get(ci_id)
        if record is None:
            raise NotFoundError("no such configuration item: %r" % (ci_id,))
        return record

    def get_configuration_item(self, actor, ci_id):
        record = self._config_item(ci_id)
        self._org(actor, record["org_id"])
        return dict(record)

    def list_configuration_items(self, actor, org_id, job_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._config_items.values()
                if r["org_id"] == org_id
                and (job_id is None or r["job_id"] == job_id)]

    def record_ci_relationship(self, actor, org_id, from_ci_id, to_ci_id,
                               relationship_label):
        """Record a reported dependency between two CIs in one org."""
        action = "ext_ci_relationship_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        source = self._config_item(from_ci_id)
        target = self._config_item(to_ci_id)
        if source["org_id"] != org_id or target["org_id"] != org_id:
            raise ValidationError(
                "configuration items belong to another organization")
        if from_ci_id == to_ci_id:
            raise ValidationError(
                "a configuration item cannot depend on itself")
        _text(relationship_label, "relationship_label")
        with self._lock:
            record = {
                "id": self._mint("rel-"),
                "org_id": org_id,
                "from_ci_id": from_ci_id,
                "to_ci_id": to_ci_id,
                "relationship_label": relationship_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._ci_relationships[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"from_ci_id": from_ci_id, "to_ci_id": to_ci_id})
        return dict(record)

    def list_ci_relationships(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._ci_relationships.values()
                if r["org_id"] == org_id]

    def cmdb_summary(self, actor, org_id):
        """Counts only, derived at read: jobs, CIs by reported kind,
        relationships."""
        self._org(actor, org_id)
        jobs = sum(1 for r in self._discovery_jobs.values()
                   if r["org_id"] == org_id)
        by_kind = {}
        items = 0
        for record in self._config_items.values():
            if record["org_id"] == org_id:
                items += 1
                by_kind[record["ci_kind"]] = by_kind.get(record["ci_kind"], 0) + 1
        relationships = sum(1 for r in self._ci_relationships.values()
                            if r["org_id"] == org_id)
        return {
            "org_id": org_id,
            "discovery_jobs": jobs,
            "configuration_items": items,
            "items_by_kind": by_kind,
            "ci_relationships": relationships,
        }

    # -- idx 556: project & portfolio management ---------------------------------

    def create_portfolio(self, actor, org_id, ref, label):
        """Record a portfolio. A portfolio is a grouping record;
        no investment value is computed from it, ever."""
        action = "ext_portfolio_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._portfolios.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "portfolio ref already exists in this organization: "
                        "%r" % (ref,))
            record = {
                "id": self._mint("pfl-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._portfolios[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _portfolio(self, portfolio_id):
        record = self._portfolios.get(portfolio_id)
        if record is None:
            raise NotFoundError("no such portfolio: %r" % (portfolio_id,))
        return record

    def create_project_record(self, actor, org_id, portfolio_id, ref, label,
                              system_id=None):
        """Record a project in a portfolio, optionally linked to a
        managed system. Its current state derives at read from
        recorded state labels."""
        action = "ext_project_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        portfolio = self._portfolio(portfolio_id)
        if portfolio["org_id"] != org_id:
            raise ValidationError("portfolio belongs to another organization")
        _text(ref, "ref")
        _text(label, "label")
        if system_id is not None:
            self._system_in_org(actor, org_id, system_id)
        with self._lock:
            for existing in self._projects.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "project ref already exists in this organization: %r"
                        % (ref,))
            record = {
                "id": self._mint("prj-"),
                "org_id": org_id,
                "portfolio_id": portfolio_id,
                "ref": ref,
                "label": label,
                "system_id": system_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._projects[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _project(self, project_id):
        record = self._projects.get(project_id)
        if record is None:
            raise NotFoundError("no such project record: %r" % (project_id,))
        return record

    def record_project_state(self, actor, org_id, project_id, state_label):
        """Append one reported state label to a project record."""
        project = self._project(project_id)
        if project["org_id"] != org_id:
            raise ValidationError("project belongs to another organization")
        return self._record_state(
            actor, org_id, self._project_states, "prjs-", "project_id",
            project_id, state_label, PROJECT_STATES,
            "ext_project_state_record")

    def get_project_record(self, actor, project_id):
        project = self._project(project_id)
        self._org(actor, project["org_id"])
        return self._state_view(
            project, self._states_for(self._project_states, "project_id",
                                      project_id))

    def portfolio_view(self, actor, org_id, portfolio_id):
        """One portfolio with its projects and derived counts.

        Counts only: projects by derived current state. No score,
        ranking, or optimization value appears in this view.
        """
        self._org(actor, org_id)
        portfolio = self._portfolio(portfolio_id)
        if portfolio["org_id"] != org_id:
            raise ValidationError("portfolio belongs to another organization")
        projects = []
        by_state = {}
        for project in self._projects.values():
            if project["portfolio_id"] != portfolio_id:
                continue
            view = self._state_view(project, self._states_for(
                self._project_states, "project_id", project["id"]))
            projects.append(view)
            by_state[view["current_state"]] = \
                by_state.get(view["current_state"], 0) + 1
        view = dict(portfolio)
        view["projects"] = projects
        view["project_count"] = len(projects)
        view["projects_by_current_state"] = by_state
        return view

    def list_portfolios(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._portfolios.values()
                if r["org_id"] == org_id]

    # -- idx 557: DEX analytics & endpoint automation ------------------------------

    def record_experience_report(self, actor, org_id, endpoint_ref,
                                 report_ref, experience_label):
        """Record one endpoint-experience report, verbatim.

        ``endpoint_ref`` is an opaque caller-supplied reference.
        ``experience_label`` carries the reporting platform's own
        assessment verbatim -- including any vendor experience
        score, which is that engine's output: it is stored as
        reported text and never computed, averaged, or re-derived
        here.
        """
        action = "ext_experience_report_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(endpoint_ref, "endpoint_ref")
        _text(report_ref, "report_ref")
        _text(experience_label, "experience_label")
        with self._lock:
            record = {
                "id": self._mint("dxr-"),
                "org_id": org_id,
                "endpoint_ref": endpoint_ref,
                "report_ref": report_ref,
                "experience_label": experience_label,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._experience_reports[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"endpoint_ref": endpoint_ref})
        return dict(record)

    def list_experience_reports(self, actor, org_id, endpoint_ref=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._experience_reports.values()
                if r["org_id"] == org_id
                and (endpoint_ref is None
                     or r["endpoint_ref"] == endpoint_ref)]

    def create_automation_definition(self, actor, org_id, ref, label,
                                     action_label):
        """Record an endpoint-automation definition as data.

        Per the house doctrine, definitions are held as data and
        never executed by this registry (``executed_here:
        False``).
        """
        action = "ext_automation_definition_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        _text(action_label, "action_label")
        with self._lock:
            record = {
                "id": self._mint("dxa-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "action_label": action_label,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._automation_definitions[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _automation_definition(self, definition_id):
        record = self._automation_definitions.get(definition_id)
        if record is None:
            raise NotFoundError(
                "no such automation definition: %r" % (definition_id,))
        return record

    def record_automation_request(self, actor, org_id, definition_id,
                                  endpoint_ref, outcome_label):
        """Record a request to run an automation elsewhere, with
        its verbatim reported outcome. Nothing executes here."""
        action = "ext_automation_request_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        definition = self._automation_definition(definition_id)
        if definition["org_id"] != org_id:
            raise ValidationError(
                "automation definition belongs to another organization")
        _text(endpoint_ref, "endpoint_ref")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("dxq-"),
                "org_id": org_id,
                "definition_id": definition_id,
                "endpoint_ref": endpoint_ref,
                "outcome_label": outcome_label,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._automation_requests[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"definition_id": definition_id})
        return dict(record)

    def list_automation_requests(self, actor, org_id, definition_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._automation_requests.values()
                if r["org_id"] == org_id
                and (definition_id is None
                     or r["definition_id"] == definition_id)]

    def dex_summary(self, actor, org_id):
        """Counts only, derived at read: reports by verbatim label,
        definitions, requests by verbatim outcome."""
        self._org(actor, org_id)
        by_label = {}
        reports = 0
        for record in self._experience_reports.values():
            if record["org_id"] == org_id:
                reports += 1
                by_label[record["experience_label"]] = \
                    by_label.get(record["experience_label"], 0) + 1
        definitions = sum(1 for r in self._automation_definitions.values()
                          if r["org_id"] == org_id)
        by_outcome = {}
        requests = 0
        for record in self._automation_requests.values():
            if record["org_id"] == org_id:
                requests += 1
                by_outcome[record["outcome_label"]] = \
                    by_outcome.get(record["outcome_label"], 0) + 1
        return {
            "org_id": org_id,
            "experience_reports": reports,
            "reports_by_label": by_label,
            "automation_definitions": definitions,
            "automation_requests": requests,
            "requests_by_outcome": by_outcome,
        }

    # -- idx 558: geospatial (GIS) application platform ----------------------------

    def create_gis_dataset(self, actor, org_id, ref, label, dataset_kind):
        """Record a geospatial dataset as metadata only.

        The record shape has no field that can hold geometry or
        coordinate content, so none can be stored here.
        """
        action = "ext_gis_dataset_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        if dataset_kind not in DATASET_KINDS:
            raise ValidationError(
                "dataset_kind must be one of %r" % (DATASET_KINDS,))
        with self._lock:
            for existing in self._gis_datasets.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "GIS dataset ref already exists in this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("gis-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "dataset_kind": dataset_kind,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._gis_datasets[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _gis_dataset(self, dataset_id):
        record = self._gis_datasets.get(dataset_id)
        if record is None:
            raise NotFoundError("no such GIS dataset: %r" % (dataset_id,))
        return record

    def create_gis_layer(self, actor, org_id, dataset_id, ref, label,
                         geometry_ref):
        """Record a map layer over a dataset.

        ``geometry_ref`` is an opaque caller-supplied reference to
        geometry held elsewhere; the geometry itself never enters
        this substrate (``rendered_here: False``).
        """
        action = "ext_gis_layer_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        dataset = self._gis_dataset(dataset_id)
        if dataset["org_id"] != org_id:
            raise ValidationError("GIS dataset belongs to another organization")
        _text(ref, "ref")
        _text(label, "label")
        _text(geometry_ref, "geometry_ref")
        with self._lock:
            record = {
                "id": self._mint("lyr-"),
                "org_id": org_id,
                "dataset_id": dataset_id,
                "ref": ref,
                "label": label,
                "geometry_ref": geometry_ref,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._gis_layers[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _gis_layer(self, layer_id):
        record = self._gis_layers.get(layer_id)
        if record is None:
            raise NotFoundError("no such GIS layer: %r" % (layer_id,))
        return record

    def get_gis_layer(self, actor, layer_id):
        record = self._gis_layer(layer_id)
        self._org(actor, record["org_id"])
        return dict(record)

    def list_gis_layers(self, actor, org_id, dataset_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._gis_layers.values()
                if r["org_id"] == org_id
                and (dataset_id is None or r["dataset_id"] == dataset_id)]

    def record_gis_service(self, actor, org_id, layer_id, service_ref,
                           outcome_label):
        """Record a reported hosted geospatial content service
        over a layer. Nothing is hosted or rendered here."""
        action = "ext_gis_service_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        layer = self._gis_layer(layer_id)
        if layer["org_id"] != org_id:
            raise ValidationError("GIS layer belongs to another organization")
        _text(service_ref, "service_ref")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("gsv-"),
                "org_id": org_id,
                "layer_id": layer_id,
                "service_ref": service_ref,
                "outcome_label": outcome_label,
                "rendered_here": False,
                "hosted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._gis_services[record["id"]] = record
        self._audit(actor, action, record["id"], {"layer_id": layer_id})
        return dict(record)

    def gis_summary(self, actor, org_id):
        """Counts only, derived at read: datasets by kind, layers,
        services."""
        self._org(actor, org_id)
        by_kind = {kind: 0 for kind in DATASET_KINDS}
        for record in self._gis_datasets.values():
            if record["org_id"] == org_id:
                by_kind[record["dataset_kind"]] += 1
        return {
            "org_id": org_id,
            "datasets": sum(by_kind.values()),
            "datasets_by_kind": by_kind,
            "layers": sum(1 for r in self._gis_layers.values()
                          if r["org_id"] == org_id),
            "services": sum(1 for r in self._gis_services.values()
                            if r["org_id"] == org_id),
        }

    # -- idx 559: managed backup & disaster recovery (reference stub) -------------

    def create_backup_job(self, actor, org_id, ref, label, system_id):
        """Record a managed backup job against a managed system.

        Reference implementation only: no data is backed up here
        (``backed_up_here: False``). Retention enforcement is the
        embedding organization's records schedule at the
        deployment layer (PLATFORM-LAYER.md decision 4); this
        record carries no retention-enforcement claim.
        """
        action = "ext_backup_job_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        self._system_in_org(actor, org_id, system_id)
        with self._lock:
            record = {
                "id": self._mint("bkj-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "system_id": system_id,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "backed_up_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._backup_jobs[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _backup_job(self, job_id):
        record = self._backup_jobs.get(job_id)
        if record is None:
            raise NotFoundError("no such backup job: %r" % (job_id,))
        return record

    def record_backup_outcome(self, actor, org_id, job_id, outcome_label,
                              reported_bytes=None):
        """Record a backup job's verbatim reported outcome.

        ``reported_bytes`` is the operating service's own reported
        figure, carried as reported data; nothing here measures
        or moves any bytes.
        """
        action = "ext_backup_outcome_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        job = self._backup_job(job_id)
        if job["org_id"] != org_id:
            raise ValidationError("backup job belongs to another organization")
        _text(outcome_label, "outcome_label")
        if reported_bytes is not None:
            _count(reported_bytes, "reported_bytes")
        with self._lock:
            record = {
                "id": self._mint("bko-"),
                "org_id": org_id,
                "job_id": job_id,
                "outcome_label": outcome_label,
                "reported_bytes": reported_bytes,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "backed_up_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._backup_outcomes[record["id"]] = record
        self._audit(actor, action, record["id"], {"job_id": job_id})
        return dict(record)

    def create_restore_request(self, actor, org_id, job_id, request_ref,
                               outcome_label):
        """Record a disaster-recovery restore request and its
        verbatim reported outcome. Nothing is restored here
        (``restored_here: False``)."""
        action = "ext_restore_request_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        job = self._backup_job(job_id)
        if job["org_id"] != org_id:
            raise ValidationError("backup job belongs to another organization")
        _text(request_ref, "request_ref")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("rst-"),
                "org_id": org_id,
                "job_id": job_id,
                "request_ref": request_ref,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "restored_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._restore_requests[record["id"]] = record
        self._audit(actor, action, record["id"], {"job_id": job_id})
        return dict(record)

    def list_backup_jobs(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._backup_jobs.values()
                if r["org_id"] == org_id]

    def list_restore_requests(self, actor, org_id, job_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._restore_requests.values()
                if r["org_id"] == org_id
                and (job_id is None or r["job_id"] == job_id)]

    def backup_summary(self, actor, org_id):
        """Counts only, derived at read: jobs, outcomes by verbatim
        label, restore requests."""
        self._org(actor, org_id)
        by_outcome = {}
        outcomes = 0
        for record in self._backup_outcomes.values():
            if record["org_id"] == org_id:
                outcomes += 1
                by_outcome[record["outcome_label"]] = \
                    by_outcome.get(record["outcome_label"], 0) + 1
        return {
            "org_id": org_id,
            "backup_jobs": sum(1 for r in self._backup_jobs.values()
                               if r["org_id"] == org_id),
            "backup_outcomes": outcomes,
            "outcomes_by_label": by_outcome,
            "restore_requests": sum(1 for r in self._restore_requests.values()
                                    if r["org_id"] == org_id),
        }

    # -- idx 560: security operations services (SOC / SIEM / scanning) -------------

    def create_security_case(self, actor, org_id, ref, summary, case_kind,
                             system_id=None):
        """Record a security-operations case. Its current state
        derives at read from recorded state labels. Recording a
        case detects nothing (``detected_here: False``)."""
        action = "ext_security_case_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(summary, "summary")
        if case_kind not in CASE_KINDS:
            raise ValidationError(
                "case_kind must be one of %r" % (CASE_KINDS,))
        if system_id is not None:
            self._system_in_org(actor, org_id, system_id)
        with self._lock:
            for existing in self._security_cases.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "security case ref already exists in this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("sec-"),
                "org_id": org_id,
                "ref": ref,
                "summary": summary,
                "case_kind": case_kind,
                "system_id": system_id,
                "detected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._security_cases[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _security_case(self, case_id):
        record = self._security_cases.get(case_id)
        if record is None:
            raise NotFoundError("no such security case: %r" % (case_id,))
        return record

    def record_case_state(self, actor, org_id, case_id, state_label):
        """Append one reported state label to a security case."""
        case = self._security_case(case_id)
        if case["org_id"] != org_id:
            raise ValidationError("security case belongs to another organization")
        return self._record_state(
            actor, org_id, self._case_states, "secs-", "case_id",
            case_id, state_label, CASE_STATES, "ext_security_case_state_record")

    def get_security_case(self, actor, case_id):
        case = self._security_case(case_id)
        self._org(actor, case["org_id"])
        return self._state_view(
            case, self._states_for(self._case_states, "case_id", case_id))

    def record_security_finding(self, actor, org_id, case_id, finding_ref,
                                severity_label, outcome_label):
        """Record one reported finding on a security case.

        The finding is the operating service's report: severity is
        a verbatim reported label, never a computed value, and no
        scanning or detection happens here (``scanning_here:
        False``, ``detected_here: False``).
        """
        action = "ext_security_finding_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        case = self._security_case(case_id)
        if case["org_id"] != org_id:
            raise ValidationError("security case belongs to another organization")
        _text(finding_ref, "finding_ref")
        _text(severity_label, "severity_label")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("sef-"),
                "org_id": org_id,
                "case_id": case_id,
                "finding_ref": finding_ref,
                "severity_label": severity_label,
                "outcome_label": outcome_label,
                "scanning_here": False,
                "detected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._security_findings[record["id"]] = record
        self._audit(actor, action, record["id"], {"case_id": case_id})
        return dict(record)

    def list_security_findings(self, actor, org_id, case_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._security_findings.values()
                if r["org_id"] == org_id
                and (case_id is None or r["case_id"] == case_id)]

    def security_summary(self, actor, org_id):
        """Counts only, derived at read: cases by kind and derived
        current state; findings by verbatim severity label."""
        self._org(actor, org_id)
        by_kind = {kind: 0 for kind in CASE_KINDS}
        by_state = {}
        for case in self._security_cases.values():
            if case["org_id"] != org_id:
                continue
            by_kind[case["case_kind"]] += 1
            state = self._latest_state_label(self._states_for(
                self._case_states, "case_id", case["id"]))
            by_state[state] = by_state.get(state, 0) + 1
        by_severity = {}
        findings = 0
        for record in self._security_findings.values():
            if record["org_id"] == org_id:
                findings += 1
                by_severity[record["severity_label"]] = \
                    by_severity.get(record["severity_label"], 0) + 1
        return {
            "org_id": org_id,
            "security_cases": sum(by_kind.values()),
            "cases_by_kind": by_kind,
            "cases_by_current_state": by_state,
            "findings": findings,
            "findings_by_severity_label": by_severity,
        }
