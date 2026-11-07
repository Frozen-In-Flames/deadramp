"""Final GAPS batch extensions for System Administration,
untiered set (Untiered Set 10).

Clean-room, standard-library-only extension surface for the 7
open entries of the GAPS.md section "Untiered Set 10 -- System
Administration (4 forks, tier null)" (inventory idx 839-845;
see ``BATCH.md`` in the group directory for the per-entry
disposition). This module is a wrapper around
:class:`SysadminStore`; every core module is untouched and
byte-identical to the shipped build.

**Tier discipline, carried into the extension:** this set is
untiered -- every member's FedRAMP impact level is Unknown in
the source, so no tier is assigned, no CMMC equivalence is
drawn, and no control baseline is asserted, here or anywhere
in this surface. No record shape in this module has a key that
could hold a tier, a baseline, or an equivalence; the batch
tests pin that by a recursive key scan over every extension
record, view, and summary.

Honesty of form, per the batch brief: each entry closes as a
records surface over this group's OWN records substrate
(customer organizations, managed systems, applications).
Nothing in this module observes a system, runs an analysis,
works a service desk, discovers a device, touches an endpoint,
scans for a vulnerability, or measures a capacity pool:

- Observability & monitoring (idx 839) ships as a labeled
  reference implementation, following the adjacent Moderate
  build's form for the same engine family: telemetry-source
  records and reported observation records holding the
  platform's output as opaque references (``reference_stub:
  True``, ``observed_here: False``, ``sensed_here: False``).
  No telemetry is collected or sensed here.
- AI root-cause & predictive analytics (idx 840) closes in the
  prediction-records form: analysis DEFINITIONS held as data
  plus reported analysis records bound to a definition and a
  telemetry source, holding the engine's output as an opaque
  report reference and a verbatim outcome label
  (``inferred_here: False``, ``computed_here: False``). No
  field can hold analysis content or a numeric confidence.
- IT service management (idx 841) is service-case records
  (incident / problem / major incident / service request)
  whose current state derives at read from recorded state
  labels, case-link records for major-incident coordination,
  alert-policy DEFINITIONS held as data plus alert dispatch
  records (``reference_transport: True``,
  ``dispatched_here: False``), and on-call rotation
  definitions held as data. No service-desk workflow executes
  here, no alert is sent, and no one is paged.
- IT operations & asset discovery (idx 842) is discovery-job
  records plus inventory-item records held as REPORTED data
  (``discovered_here: False``): an inventory record is a
  report filed by the caller's discovery tooling, not a scan
  result produced here. Dependency mapping is relationship
  records between reported items; signal correlation is
  reported signal records plus caller-reported correlation
  links (``correlated_here: False``).
- Endpoint management operations (idx 843) is endpoint
  records known by opaque references only, operation
  DEFINITIONS held as data, and operation-run records with
  verbatim reported outcomes (``executed_here: False``
  throughout; nothing is patched, deployed, or remotely
  controlled here). A run may bind a core change record --
  patching rides Core's change records as records only, and
  recording a run modifies no core record.
- Vulnerability detection & remediation prioritization
  (idx 844) ships as a labeled reference implementation:
  scan-job records bound to a core managed system, finding
  records holding severity as a verbatim reported label
  (``scanned_here: False``, ``detected_here: False``), and
  remediation-priority records holding the engine's reported
  priority label verbatim (``prioritized_here: False`` --
  prioritization is a ranking the engine computes; this
  substrate derives none).
- Capacity, optimization & chargeback reporting (idx 845) is
  capacity-pool records, capacity-observation records holding
  quantities exactly as reported (``measured_here: False``),
  optimization-recommendation records held as opaque
  references (``optimized_here: False``), and chargeback
  report records holding the platform's reported amount in
  integer cents verbatim (``computed_here: False``,
  ``charged_here: False``; a float amount is rejected at the
  boundary). A pool's latest observation derives at read from
  its append-only observation records and is never stored.

Doctrines carried from the core: derived-never-stored for
every computed value (current case state, a pool's latest
observation, all summary counts); opaque references only --
no entity shape has a field for a hostname, address,
credential, telemetry payload, or any live-system identifier;
validation before mutation, so a failed operation consumes no
id and changes nothing; append-only audit on the core store's
log with ``ext_``-prefixed actions for every successful
extension mutation, and denied write attempts recorded with a
``:denied`` suffix; RBAC via :mod:`sysadmin.access` --
extension writes map to the core ``enter`` action, and
organization membership (the set's recorded access boundary)
is enforced by resolving the organization through the core
store on every operation. Summaries are counts only: nothing
in this module computes a score, a rating, a health or
posture value, an average, or a ranking.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

TELEMETRY_SOURCE_KINDS = ("metrics", "traces", "logs", "events", "other")
ANALYSIS_KINDS = ("root_cause", "prediction", "correlation", "other")
CASE_KINDS = ("incident", "problem", "major_incident", "service_request",
              "other")
CASE_STATES = (
    "reported_open", "reported_in_progress", "reported_resolved",
    "reported_closed",
)
ITEM_KINDS = ("system", "application", "device", "service", "other")
OPERATION_KINDS = ("patch", "deploy", "diagnostic", "remote_session",
                   "automation", "other")

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


def _cents(value, field):
    """An amount of money in integer cents; bools/floats rejected.

    Chargeback amounts arrive as the platform's reported
    figures and are held verbatim as data; money is never a
    float anywhere in this substrate.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % (field,))
    if value < 0:
        raise ValidationError("%s must be an integer number of cents" % (field,))
    return value


class SysadminExtensions:
    """GAPS-batch extension surface wrapping one :class:`SysadminStore`."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._counters = {}
        # idx 839 -- observability & monitoring (reference stub)
        self._telemetry_sources = {}
        self._observation_reports = {}
        # idx 840 -- AI root-cause & predictive analytics
        self._analysis_definitions = {}
        self._analysis_reports = {}
        # idx 841 -- IT service management systems
        self._service_cases = {}
        self._case_states = {}
        self._case_links = {}
        self._alert_policies = {}
        self._alert_dispatches = {}
        self._oncall_rotations = {}
        # idx 842 -- IT operations & asset discovery engines
        self._discovery_jobs = {}
        self._inventory_items = {}
        self._item_relationships = {}
        self._signal_reports = {}
        self._signal_correlations = {}
        # idx 843 -- endpoint management operations
        self._endpoints = {}
        self._operation_definitions = {}
        self._operation_runs = {}
        # idx 844 -- vulnerability detection & remediation
        # prioritization (reference stub)
        self._scan_jobs = {}
        self._vuln_findings = {}
        self._remediation_priorities = {}
        # idx 845 -- capacity, optimization & chargeback reporting
        self._capacity_pools = {}
        self._capacity_observations = {}
        self._optimization_recommendations = {}
        self._chargeback_reports = {}

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

    def _check_ref_unique(self, table, org_id, ref, what):
        for existing in table.values():
            if existing["org_id"] == org_id and existing["ref"] == ref:
                raise ValidationError(
                    "%s ref already exists in this organization: %r"
                    % (what, ref))

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

    # -- idx 839: observability & monitoring engines (reference) --------------

    def create_telemetry_source(self, actor, org_id, ref, label, source_kind):
        """Record a telemetry source as a labeled reference.

        Reference implementation only: no telemetry is collected,
        observed, or sensed here (``observed_here: False``,
        ``sensed_here: False``).
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
            self._check_ref_unique(self._telemetry_sources, org_id, ref,
                                   "telemetry source")
            record = {
                "id": self._mint("obs-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "source_kind": source_kind,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "observed_here": False,
                "sensed_here": False,
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

    def record_observation_report(self, actor, org_id, source_id, report_ref,
                                  outcome_label):
        """Record a reported observation as an opaque reference.

        The observation itself is the platform's engine output;
        here it exists only as the caller's ``report_ref`` and a
        verbatim outcome label. No telemetry payload is held --
        there is no field that could hold one.
        """
        action = "ext_observation_report_record"
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
                "id": self._mint("obr-"),
                "org_id": org_id,
                "source_id": source_id,
                "report_ref": report_ref,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "observed_here": False,
                "sensed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._observation_reports[record["id"]] = record
        self._audit(actor, action, record["id"], {"source_id": source_id})
        return dict(record)

    def list_telemetry_sources(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._telemetry_sources.values()
                if r["org_id"] == org_id]

    def list_observation_reports(self, actor, org_id, source_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._observation_reports.values()
                if r["org_id"] == org_id
                and (source_id is None or r["source_id"] == source_id)]

    def observability_summary(self, actor, org_id):
        """Counts only, derived at read: sources by kind and
        observation reports by verbatim outcome label."""
        self._org(actor, org_id)
        sources_by_kind = {kind: 0 for kind in TELEMETRY_SOURCE_KINDS}
        for source in self._telemetry_sources.values():
            if source["org_id"] == org_id:
                sources_by_kind[source["source_kind"]] += 1
        reports_by_outcome = {}
        for report in self._observation_reports.values():
            if report["org_id"] == org_id:
                label = report["outcome_label"]
                reports_by_outcome[label] = reports_by_outcome.get(label, 0) + 1
        return {
            "org_id": org_id,
            "telemetry_sources": sum(sources_by_kind.values()),
            "telemetry_sources_by_kind": sources_by_kind,
            "observation_reports": sum(reports_by_outcome.values()),
            "observation_reports_by_outcome": reports_by_outcome,
        }

    # -- idx 840: AI root-cause & predictive analytics -------------------------

    def create_analysis_definition(self, actor, org_id, ref, label,
                                   analysis_kind):
        """Record an analysis definition as data.

        The definition describes an analysis the caller's engine
        performs over telemetry; no analysis is defined into
        execution here and nothing is inferred or computed
        (``inferred_here: False``, ``computed_here: False``).
        """
        action = "ext_analysis_definition_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        if analysis_kind not in ANALYSIS_KINDS:
            raise ValidationError(
                "analysis_kind must be one of %r" % (ANALYSIS_KINDS,))
        with self._lock:
            self._check_ref_unique(self._analysis_definitions, org_id, ref,
                                   "analysis definition")
            record = {
                "id": self._mint("anl-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "analysis_kind": analysis_kind,
                "inferred_here": False,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._analysis_definitions[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _analysis_definition(self, definition_id):
        record = self._analysis_definitions.get(definition_id)
        if record is None:
            raise NotFoundError(
                "no such analysis definition: %r" % (definition_id,))
        return record

    def record_analysis_report(self, actor, org_id, definition_id, source_id,
                               report_ref, outcome_label):
        """Record a reported analysis outcome over a telemetry source.

        The analysis itself -- a root cause, a prediction -- is
        the engine's output; here it exists only as the caller's
        opaque ``report_ref`` and a verbatim outcome label,
        bound to the definition it ran under and the telemetry
        source it ran over. No field can hold analysis content
        or a numeric confidence, and none is computed here.
        """
        action = "ext_analysis_report_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        definition = self._analysis_definition(definition_id)
        if definition["org_id"] != org_id:
            raise ValidationError(
                "analysis definition belongs to another organization")
        source = self._telemetry_source(source_id)
        if source["org_id"] != org_id:
            raise ValidationError(
                "telemetry source belongs to another organization")
        _text(report_ref, "report_ref")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("anr-"),
                "org_id": org_id,
                "definition_id": definition_id,
                "source_id": source_id,
                "report_ref": report_ref,
                "outcome_label": outcome_label,
                "inferred_here": False,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._analysis_reports[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"definition_id": definition_id, "source_id": source_id})
        return dict(record)

    def list_analysis_definitions(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._analysis_definitions.values()
                if r["org_id"] == org_id]

    def list_analysis_reports(self, actor, org_id, definition_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._analysis_reports.values()
                if r["org_id"] == org_id
                and (definition_id is None
                     or r["definition_id"] == definition_id)]

    def analytics_summary(self, actor, org_id):
        """Counts only, derived at read: definitions by kind and
        analysis reports by verbatim outcome label."""
        self._org(actor, org_id)
        definitions_by_kind = {kind: 0 for kind in ANALYSIS_KINDS}
        for definition in self._analysis_definitions.values():
            if definition["org_id"] == org_id:
                definitions_by_kind[definition["analysis_kind"]] += 1
        reports_by_outcome = {}
        for report in self._analysis_reports.values():
            if report["org_id"] == org_id:
                label = report["outcome_label"]
                reports_by_outcome[label] = reports_by_outcome.get(label, 0) + 1
        return {
            "org_id": org_id,
            "analysis_definitions": sum(definitions_by_kind.values()),
            "analysis_definitions_by_kind": definitions_by_kind,
            "analysis_reports": sum(reports_by_outcome.values()),
            "analysis_reports_by_outcome": reports_by_outcome,
        }

    # -- idx 841: IT service management systems --------------------------------

    def create_service_case(self, actor, org_id, ref, summary, case_kind,
                            system_id=None):
        """Record a service-management case against an organization.

        The case's current state is never stored on the case; it
        derives at read from recorded state labels (see
        :meth:`record_case_state`). Recording a case performs no
        service-desk work: the working system a case belongs to
        is the operator's, and this is its records surface.
        """
        action = "ext_service_case_create"
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
            self._check_ref_unique(self._service_cases, org_id, ref,
                                   "service case")
            record = {
                "id": self._mint("svc-"),
                "org_id": org_id,
                "ref": ref,
                "summary": summary,
                "case_kind": case_kind,
                "system_id": system_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._service_cases[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _service_case(self, case_id):
        record = self._service_cases.get(case_id)
        if record is None:
            raise NotFoundError("no such service case: %r" % (case_id,))
        return record

    def record_case_state(self, actor, org_id, case_id, state_label):
        """Append one reported state label to a service case."""
        case = self._service_case(case_id)
        if case["org_id"] != org_id:
            raise ValidationError("service case belongs to another organization")
        return self._record_state(
            actor, org_id, self._case_states, "svcs-", "case_id",
            case_id, state_label, CASE_STATES,
            "ext_service_case_state_record")

    def get_service_case(self, actor, case_id):
        case = self._service_case(case_id)
        self._org(actor, case["org_id"])
        return self._state_view(
            case, self._states_for(self._case_states, "case_id", case_id))

    def list_service_cases(self, actor, org_id, case_kind=None):
        self._org(actor, org_id)
        return [
            self._state_view(c, self._states_for(
                self._case_states, "case_id", c["id"]))
            for c in self._service_cases.values()
            if c["org_id"] == org_id
            and (case_kind is None or c["case_kind"] == case_kind)
        ]

    def link_service_case(self, actor, org_id, major_case_id, case_id):
        """Record a coordination link from a case to a major incident.

        Major-incident coordination, in records form: the link
        states that the caller's service-management system is
        coordinating ``case_id`` under the major incident
        ``major_case_id``. Recording the link coordinates
        nothing here.
        """
        action = "ext_service_case_link"
        self._guard(actor, action)
        self._org(actor, org_id)
        major = self._service_case(major_case_id)
        if major["org_id"] != org_id:
            raise ValidationError("major case belongs to another organization")
        if major["case_kind"] != "major_incident":
            raise ValidationError(
                "coordination links target a major_incident case")
        case = self._service_case(case_id)
        if case["org_id"] != org_id:
            raise ValidationError("service case belongs to another organization")
        if case_id == major_case_id:
            raise ValidationError("a case cannot be coordinated under itself")
        with self._lock:
            for existing in self._case_links.values():
                if (existing["major_case_id"] == major_case_id
                        and existing["case_id"] == case_id):
                    raise ValidationError(
                        "case is already linked to this major incident")
            record = {
                "id": self._mint("svl-"),
                "org_id": org_id,
                "major_case_id": major_case_id,
                "case_id": case_id,
                "coordinated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._case_links[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"major_case_id": major_case_id, "case_id": case_id})
        return dict(record)

    def list_case_links(self, actor, org_id, major_case_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._case_links.values()
                if r["org_id"] == org_id
                and (major_case_id is None
                     or r["major_case_id"] == major_case_id)]

    def create_alert_policy(self, actor, org_id, ref, label, trigger_label):
        """Record an alert policy definition as data.

        The definition states the condition label under which
        the operator's system would alert; nothing evaluates it
        and nothing dispatches (``executed_here: False``,
        ``dispatched_here: False``).
        """
        action = "ext_alert_policy_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        _text(trigger_label, "trigger_label")
        with self._lock:
            self._check_ref_unique(self._alert_policies, org_id, ref,
                                   "alert policy")
            record = {
                "id": self._mint("alp-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "trigger_label": trigger_label,
                "executed_here": False,
                "dispatched_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._alert_policies[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _alert_policy(self, policy_id):
        record = self._alert_policies.get(policy_id)
        if record is None:
            raise NotFoundError("no such alert policy: %r" % (policy_id,))
        return record

    def record_alert_dispatch(self, actor, org_id, policy_id, case_id,
                              outcome_label):
        """Record a reported alert dispatch under a policy for a case.

        A dispatch receipt, in the records form for transport:
        the alert was dispatched by the operator's system, not
        by this build (``reference_transport: True``,
        ``dispatched_here: False``, ``delivered_here: False``).
        """
        action = "ext_alert_dispatch_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        policy = self._alert_policy(policy_id)
        if policy["org_id"] != org_id:
            raise ValidationError("alert policy belongs to another organization")
        case = self._service_case(case_id)
        if case["org_id"] != org_id:
            raise ValidationError("service case belongs to another organization")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("ald-"),
                "org_id": org_id,
                "policy_id": policy_id,
                "case_id": case_id,
                "outcome_label": outcome_label,
                "reference_transport": True,
                "dispatched_here": False,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._alert_dispatches[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"policy_id": policy_id, "case_id": case_id})
        return dict(record)

    def list_alert_policies(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._alert_policies.values()
                if r["org_id"] == org_id]

    def list_alert_dispatches(self, actor, org_id, policy_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._alert_dispatches.values()
                if r["org_id"] == org_id
                and (policy_id is None or r["policy_id"] == policy_id)]

    def create_oncall_rotation(self, actor, org_id, ref, label, schedule_ref):
        """Record an on-call rotation definition as data.

        The rotation is described by the caller's opaque
        ``schedule_ref``; no schedule is evaluated, no responder
        is resolved, and no one is paged from here
        (``executed_here: False``).
        """
        action = "ext_oncall_rotation_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        _text(schedule_ref, "schedule_ref")
        with self._lock:
            self._check_ref_unique(self._oncall_rotations, org_id, ref,
                                   "on-call rotation")
            record = {
                "id": self._mint("ocr-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "schedule_ref": schedule_ref,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._oncall_rotations[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def list_oncall_rotations(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._oncall_rotations.values()
                if r["org_id"] == org_id]

    def itsm_summary(self, actor, org_id):
        """Counts only, derived at read: cases by kind and by
        derived current state, coordination links, alert
        policies and dispatches, on-call rotations."""
        self._org(actor, org_id)
        cases_by_kind = {kind: 0 for kind in CASE_KINDS}
        cases_by_state = {}
        for case in self._service_cases.values():
            if case["org_id"] != org_id:
                continue
            cases_by_kind[case["case_kind"]] += 1
            state = self._latest_state_label(self._states_for(
                self._case_states, "case_id", case["id"]))
            cases_by_state[state] = cases_by_state.get(state, 0) + 1
        return {
            "org_id": org_id,
            "service_cases": sum(cases_by_kind.values()),
            "service_cases_by_kind": cases_by_kind,
            "service_cases_by_current_state": cases_by_state,
            "case_links": sum(1 for r in self._case_links.values()
                              if r["org_id"] == org_id),
            "alert_policies": sum(1 for r in self._alert_policies.values()
                                  if r["org_id"] == org_id),
            "alert_dispatches": sum(1 for r in self._alert_dispatches.values()
                                    if r["org_id"] == org_id),
            "oncall_rotations": sum(1 for r in self._oncall_rotations.values()
                                    if r["org_id"] == org_id),
        }

    # -- idx 842: IT operations & asset discovery engines -----------------------

    def create_discovery_job(self, actor, org_id, ref, label, scope_ref):
        """Record a discovery job.

        The job is a record of work the caller's discovery
        tooling performs elsewhere; nothing is discovered or
        scanned here (``discovered_here: False``,
        ``scanned_here: False``).
        """
        action = "ext_discovery_job_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        _text(scope_ref, "scope_ref")
        with self._lock:
            self._check_ref_unique(self._discovery_jobs, org_id, ref,
                                   "discovery job")
            record = {
                "id": self._mint("dcj-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "scope_ref": scope_ref,
                "discovered_here": False,
                "scanned_here": False,
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

    def record_inventory_item(self, actor, org_id, job_id, item_ref, label,
                              item_kind):
        """Record one reported inventory item under a discovery job.

        The item is REPORTED data -- a report filed by the
        caller's agentless discovery tooling -- not a discovery
        made here (``discovered_here: False``). The item is
        known by the caller's opaque ``item_ref``; no field can
        hold an address or credential of the item.
        """
        action = "ext_inventory_item_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        job = self._discovery_job(job_id)
        if job["org_id"] != org_id:
            raise ValidationError("discovery job belongs to another organization")
        _text(item_ref, "item_ref")
        _text(label, "label")
        if item_kind not in ITEM_KINDS:
            raise ValidationError(
                "item_kind must be one of %r" % (ITEM_KINDS,))
        with self._lock:
            for existing in self._inventory_items.values():
                if (existing["job_id"] == job_id
                        and existing["item_ref"] == item_ref):
                    raise ValidationError(
                        "inventory item ref already reported for this job: %r"
                        % (item_ref,))
            record = {
                "id": self._mint("inv-"),
                "org_id": org_id,
                "job_id": job_id,
                "item_ref": item_ref,
                "label": label,
                "item_kind": item_kind,
                "discovered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._inventory_items[record["id"]] = record
        self._audit(actor, action, record["id"], {"job_id": job_id})
        return dict(record)

    def _inventory_item(self, item_id):
        record = self._inventory_items.get(item_id)
        if record is None:
            raise NotFoundError("no such inventory item: %r" % (item_id,))
        return record

    def record_item_relationship(self, actor, org_id, from_item_id, to_item_id,
                                 relationship_label):
        """Record a dependency relationship between two reported items.

        Dependency mapping, in records form: the relationship
        is a reported fact about two reported items in one
        organization; no dependency is traced or traversed here.
        """
        action = "ext_item_relationship_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        from_item = self._inventory_item(from_item_id)
        if from_item["org_id"] != org_id:
            raise ValidationError("inventory item belongs to another organization")
        to_item = self._inventory_item(to_item_id)
        if to_item["org_id"] != org_id:
            raise ValidationError("inventory item belongs to another organization")
        if from_item_id == to_item_id:
            raise ValidationError("an item cannot depend on itself")
        _text(relationship_label, "relationship_label")
        with self._lock:
            record = {
                "id": self._mint("rel-"),
                "org_id": org_id,
                "from_item_id": from_item_id,
                "to_item_id": to_item_id,
                "relationship_label": relationship_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._item_relationships[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"from_item_id": from_item_id, "to_item_id": to_item_id})
        return dict(record)

    def record_signal_report(self, actor, org_id, job_id, signal_ref,
                             outcome_label):
        """Record one reported operations signal under a discovery job.

        The signal is the caller's tooling's report; it is held
        as an opaque reference with a verbatim outcome label
        (``correlated_here: False`` -- no signal is correlated
        here).
        """
        action = "ext_signal_report_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        job = self._discovery_job(job_id)
        if job["org_id"] != org_id:
            raise ValidationError("discovery job belongs to another organization")
        _text(signal_ref, "signal_ref")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("sgr-"),
                "org_id": org_id,
                "job_id": job_id,
                "signal_ref": signal_ref,
                "outcome_label": outcome_label,
                "correlated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._signal_reports[record["id"]] = record
        self._audit(actor, action, record["id"], {"job_id": job_id})
        return dict(record)

    def _signal_report(self, signal_id):
        record = self._signal_reports.get(signal_id)
        if record is None:
            raise NotFoundError("no such signal report: %r" % (signal_id,))
        return record

    def record_signal_correlation(self, actor, org_id, signal_id,
                                  related_signal_id, correlation_label):
        """Record a caller-reported correlation between two signals.

        Signal correlation, in records form: the caller's
        operations tooling asserts the correlation; this record
        holds the assertion. Correlating is the engine's work
        (``correlated_here: False``).
        """
        action = "ext_signal_correlation_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        signal = self._signal_report(signal_id)
        if signal["org_id"] != org_id:
            raise ValidationError("signal report belongs to another organization")
        related = self._signal_report(related_signal_id)
        if related["org_id"] != org_id:
            raise ValidationError("signal report belongs to another organization")
        if signal_id == related_signal_id:
            raise ValidationError("a signal cannot be correlated with itself")
        _text(correlation_label, "correlation_label")
        with self._lock:
            record = {
                "id": self._mint("sgc-"),
                "org_id": org_id,
                "signal_id": signal_id,
                "related_signal_id": related_signal_id,
                "correlation_label": correlation_label,
                "correlated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._signal_correlations[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"signal_id": signal_id,
                     "related_signal_id": related_signal_id})
        return dict(record)

    def list_discovery_jobs(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._discovery_jobs.values()
                if r["org_id"] == org_id]

    def list_inventory_items(self, actor, org_id, job_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._inventory_items.values()
                if r["org_id"] == org_id
                and (job_id is None or r["job_id"] == job_id)]

    def list_item_relationships(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._item_relationships.values()
                if r["org_id"] == org_id]

    def list_signal_reports(self, actor, org_id, job_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._signal_reports.values()
                if r["org_id"] == org_id
                and (job_id is None or r["job_id"] == job_id)]

    def discovery_summary(self, actor, org_id):
        """Counts only, derived at read: discovery jobs,
        inventory items by reported kind, relationships, signal
        reports, and correlation links."""
        self._org(actor, org_id)
        items_by_kind = {kind: 0 for kind in ITEM_KINDS}
        for item in self._inventory_items.values():
            if item["org_id"] == org_id:
                items_by_kind[item["item_kind"]] += 1
        return {
            "org_id": org_id,
            "discovery_jobs": sum(1 for r in self._discovery_jobs.values()
                                  if r["org_id"] == org_id),
            "inventory_items": sum(items_by_kind.values()),
            "inventory_items_by_kind": items_by_kind,
            "item_relationships": sum(
                1 for r in self._item_relationships.values()
                if r["org_id"] == org_id),
            "signal_reports": sum(1 for r in self._signal_reports.values()
                                  if r["org_id"] == org_id),
            "signal_correlations": sum(
                1 for r in self._signal_correlations.values()
                if r["org_id"] == org_id),
        }

    # -- idx 843: endpoint management operations ---------------------------------

    def create_endpoint_record(self, actor, org_id, endpoint_ref, label):
        """Record one managed endpoint by opaque reference.

        The endpoint is known only by the caller's opaque
        ``endpoint_ref`` and a label; the record shape has no
        field that could hold a hostname, address, or credential
        of the endpoint.
        """
        action = "ext_endpoint_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(endpoint_ref, "endpoint_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._endpoints.values():
                if (existing["org_id"] == org_id
                        and existing["endpoint_ref"] == endpoint_ref):
                    raise ValidationError(
                        "endpoint ref already exists in this organization: %r"
                        % (endpoint_ref,))
            record = {
                "id": self._mint("end-"),
                "org_id": org_id,
                "endpoint_ref": endpoint_ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._endpoints[record["id"]] = record
        self._audit(actor, action, record["id"], {"endpoint_ref": endpoint_ref})
        return dict(record)

    def _endpoint(self, endpoint_id):
        record = self._endpoints.get(endpoint_id)
        if record is None:
            raise NotFoundError("no such endpoint record: %r" % (endpoint_id,))
        return record

    def create_operation_definition(self, actor, org_id, ref, label,
                                    operation_kind):
        """Record an endpoint-operation definition as data.

        The definition describes an operation the caller's
        endpoint platform would run -- a patch, a deployment, a
        diagnostic, a remote session, an event-driven
        automation. Nothing is executed or triggered here
        (``executed_here: False``).
        """
        action = "ext_operation_definition_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        if operation_kind not in OPERATION_KINDS:
            raise ValidationError(
                "operation_kind must be one of %r" % (OPERATION_KINDS,))
        with self._lock:
            self._check_ref_unique(self._operation_definitions, org_id, ref,
                                   "operation definition")
            record = {
                "id": self._mint("opd-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "operation_kind": operation_kind,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._operation_definitions[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _operation_definition(self, definition_id):
        record = self._operation_definitions.get(definition_id)
        if record is None:
            raise NotFoundError(
                "no such operation definition: %r" % (definition_id,))
        return record

    def record_operation_run(self, actor, org_id, definition_id, endpoint_id,
                             outcome_label, change_id=None):
        """Record a reported endpoint-operation run.

        The run's outcome is reported verbatim by the caller's
        platform; the operation itself -- patching, deployment,
        a remote session -- happened there, not here
        (``executed_here: False``; nothing is patched, deployed,
        or connected to from this build). A run may bind a core
        change record: patching rides Core's change records as
        records only, and recording a run modifies no core
        record.
        """
        action = "ext_operation_run_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        definition = self._operation_definition(definition_id)
        if definition["org_id"] != org_id:
            raise ValidationError(
                "operation definition belongs to another organization")
        endpoint = self._endpoint(endpoint_id)
        if endpoint["org_id"] != org_id:
            raise ValidationError("endpoint belongs to another organization")
        if change_id is not None:
            change = self.store.get_change(actor, change_id)
            if change["org_id"] != org_id:
                raise ValidationError(
                    "change record belongs to another organization")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("opr-"),
                "org_id": org_id,
                "definition_id": definition_id,
                "endpoint_id": endpoint_id,
                "change_id": change_id,
                "outcome_label": outcome_label,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._operation_runs[record["id"]] = record
        self._audit(actor, action, record["id"],
                    {"definition_id": definition_id,
                     "endpoint_id": endpoint_id})
        return dict(record)

    def list_endpoints(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._endpoints.values()
                if r["org_id"] == org_id]

    def list_operation_definitions(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._operation_definitions.values()
                if r["org_id"] == org_id]

    def list_operation_runs(self, actor, org_id, definition_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._operation_runs.values()
                if r["org_id"] == org_id
                and (definition_id is None
                     or r["definition_id"] == definition_id)]

    def endpoint_summary(self, actor, org_id):
        """Counts only, derived at read: endpoints, operation
        definitions by kind, runs by verbatim outcome label."""
        self._org(actor, org_id)
        definitions_by_kind = {kind: 0 for kind in OPERATION_KINDS}
        for definition in self._operation_definitions.values():
            if definition["org_id"] == org_id:
                definitions_by_kind[definition["operation_kind"]] += 1
        runs_by_outcome = {}
        for run in self._operation_runs.values():
            if run["org_id"] == org_id:
                label = run["outcome_label"]
                runs_by_outcome[label] = runs_by_outcome.get(label, 0) + 1
        return {
            "org_id": org_id,
            "endpoints": sum(1 for r in self._endpoints.values()
                             if r["org_id"] == org_id),
            "operation_definitions": sum(definitions_by_kind.values()),
            "operation_definitions_by_kind": definitions_by_kind,
            "operation_runs": sum(runs_by_outcome.values()),
            "operation_runs_by_outcome": runs_by_outcome,
        }

    # -- idx 844: vulnerability detection & remediation prioritization (reference)

    def create_scan_job(self, actor, org_id, ref, label, system_id):
        """Record a vulnerability scan job as a labeled reference.

        Reference implementation only: the job names the core
        managed system the caller's scanner assesses; no scan
        runs and nothing is detected here (``scanned_here:
        False``, ``detected_here: False``).
        """
        action = "ext_scan_job_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        self._system_in_org(actor, org_id, system_id)
        with self._lock:
            self._check_ref_unique(self._scan_jobs, org_id, ref,
                                   "scan job")
            record = {
                "id": self._mint("scj-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "system_id": system_id,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "scanned_here": False,
                "detected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._scan_jobs[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _scan_job(self, job_id):
        record = self._scan_jobs.get(job_id)
        if record is None:
            raise NotFoundError("no such scan job: %r" % (job_id,))
        return record

    def record_vulnerability_finding(self, actor, org_id, job_id, finding_ref,
                                     severity_label):
        """Record a reported vulnerability finding under a scan job.

        The finding is the scanner's report: its severity is a
        verbatim reported label, never a computed value, and the
        vulnerability itself was detected by the scanner, not
        here (``detected_here: False``).
        """
        action = "ext_vuln_finding_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        job = self._scan_job(job_id)
        if job["org_id"] != org_id:
            raise ValidationError("scan job belongs to another organization")
        _text(finding_ref, "finding_ref")
        _text(severity_label, "severity_label")
        with self._lock:
            record = {
                "id": self._mint("vfd-"),
                "org_id": org_id,
                "job_id": job_id,
                "finding_ref": finding_ref,
                "severity_label": severity_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "detected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._vuln_findings[record["id"]] = record
        self._audit(actor, action, record["id"], {"job_id": job_id})
        return dict(record)

    def _vuln_finding(self, finding_id):
        record = self._vuln_findings.get(finding_id)
        if record is None:
            raise NotFoundError(
                "no such vulnerability finding: %r" % (finding_id,))
        return record

    def record_remediation_priority(self, actor, org_id, finding_id,
                                    priority_label):
        """Record the engine's reported remediation priority for a finding.

        Prioritization is a ranking the detection engine
        computes; this record holds its reported priority label
        verbatim and derives none (``prioritized_here:
        False``). One priority record per finding: a re-report
        supersedes nothing here -- a second record for the same
        finding is refused, so the recorded priority is the one
        report on file.
        """
        action = "ext_remediation_priority_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        finding = self._vuln_finding(finding_id)
        if finding["org_id"] != org_id:
            raise ValidationError("finding belongs to another organization")
        _text(priority_label, "priority_label")
        with self._lock:
            for existing in self._remediation_priorities.values():
                if existing["finding_id"] == finding_id:
                    raise ValidationError(
                        "a remediation priority is already recorded for "
                        "this finding")
            record = {
                "id": self._mint("rmp-"),
                "org_id": org_id,
                "finding_id": finding_id,
                "priority_label": priority_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "prioritized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._remediation_priorities[record["id"]] = record
        self._audit(actor, action, record["id"], {"finding_id": finding_id})
        return dict(record)

    def list_scan_jobs(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._scan_jobs.values()
                if r["org_id"] == org_id]

    def list_vulnerability_findings(self, actor, org_id, job_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._vuln_findings.values()
                if r["org_id"] == org_id
                and (job_id is None or r["job_id"] == job_id)]

    def list_remediation_priorities(self, actor, org_id):
        self._org(actor, org_id)
        return [dict(r) for r in self._remediation_priorities.values()
                if r["org_id"] == org_id]

    def vulnerability_summary(self, actor, org_id):
        """Counts only, derived at read: scan jobs, findings by
        verbatim severity label, priorities by verbatim priority
        label. No severity or priority value is computed."""
        self._org(actor, org_id)
        findings_by_severity = {}
        for finding in self._vuln_findings.values():
            if finding["org_id"] == org_id:
                label = finding["severity_label"]
                findings_by_severity[label] = \
                    findings_by_severity.get(label, 0) + 1
        priorities_by_label = {}
        for priority in self._remediation_priorities.values():
            if priority["org_id"] == org_id:
                label = priority["priority_label"]
                priorities_by_label[label] = \
                    priorities_by_label.get(label, 0) + 1
        return {
            "org_id": org_id,
            "scan_jobs": sum(1 for r in self._scan_jobs.values()
                             if r["org_id"] == org_id),
            "vulnerability_findings": sum(findings_by_severity.values()),
            "findings_by_severity_label": findings_by_severity,
            "remediation_priorities": sum(priorities_by_label.values()),
            "priorities_by_label": priorities_by_label,
        }

    # -- idx 845: capacity, optimization & chargeback reporting engines ----------

    def create_capacity_pool(self, actor, org_id, ref, label, system_id=None):
        """Record a capacity pool, optionally bound to a core system.

        The pool is a reporting boundary the caller's platform
        measures; nothing is measured here (``measured_here:
        False``).
        """
        action = "ext_capacity_pool_create"
        self._guard(actor, action)
        self._org(actor, org_id)
        _text(ref, "ref")
        _text(label, "label")
        if system_id is not None:
            self._system_in_org(actor, org_id, system_id)
        with self._lock:
            self._check_ref_unique(self._capacity_pools, org_id, ref,
                                   "capacity pool")
            record = {
                "id": self._mint("cap-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "system_id": system_id,
                "measured_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._capacity_pools[record["id"]] = record
        self._audit(actor, action, record["id"], {"ref": ref})
        return dict(record)

    def _capacity_pool(self, pool_id):
        record = self._capacity_pools.get(pool_id)
        if record is None:
            raise NotFoundError("no such capacity pool: %r" % (pool_id,))
        return record

    def record_capacity_observation(self, actor, org_id, pool_id, used_units,
                                    total_units, outcome_label):
        """Record one reported capacity observation for a pool.

        The quantities are the platform's reported figures,
        held exactly as reported -- non-negative integers
        (floats and booleans are rejected at the boundary), the
        reported used quantity never above the reported total.
        Nothing is measured or sensed here (``measured_here:
        False``).
        """
        action = "ext_capacity_observation_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        pool = self._capacity_pool(pool_id)
        if pool["org_id"] != org_id:
            raise ValidationError("capacity pool belongs to another organization")
        used_units = _count(used_units, "used_units")
        total_units = _count(total_units, "total_units")
        if used_units > total_units:
            raise ValidationError(
                "reported used_units cannot exceed reported total_units")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("cpo-"),
                "org_id": org_id,
                "pool_id": pool_id,
                "used_units": used_units,
                "total_units": total_units,
                "outcome_label": outcome_label,
                "measured_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._capacity_observations[record["id"]] = record
        self._audit(actor, action, record["id"], {"pool_id": pool_id})
        return dict(record)

    def _observations_for(self, pool_id):
        return [r for r in self._capacity_observations.values()
                if r["pool_id"] == pool_id]

    def get_capacity_pool(self, actor, pool_id):
        """Read a pool with its latest observation derived at read.

        The stored pool record carries no observation; the view
        adds ``latest_observation`` -- the last observation
        recorded for the pool, or None -- derived at read from
        the append-only observation records and never stored.
        """
        pool = self._capacity_pool(pool_id)
        self._org(actor, pool["org_id"])
        view = dict(pool)
        observations = self._observations_for(pool_id)
        view["latest_observation"] = (
            dict(observations[-1]) if observations else None)
        return view

    def list_capacity_pools(self, actor, org_id):
        self._org(actor, org_id)
        return [self.get_capacity_pool(actor, pool["id"])
                for pool in self._capacity_pools.values()
                if pool["org_id"] == org_id]

    def list_capacity_observations(self, actor, org_id, pool_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._capacity_observations.values()
                if r["org_id"] == org_id
                and (pool_id is None or r["pool_id"] == pool_id)]

    def record_optimization_recommendation(self, actor, org_id, pool_id,
                                           recommendation_ref, outcome_label):
        """Record a reported optimization recommendation for a pool.

        The recommendation is the optimization engine's output;
        here it exists only as the caller's opaque
        ``recommendation_ref`` and a verbatim outcome label
        (``optimized_here: False`` -- nothing is optimized,
        moved, or resized from this build).
        """
        action = "ext_optimization_recommendation_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        pool = self._capacity_pool(pool_id)
        if pool["org_id"] != org_id:
            raise ValidationError("capacity pool belongs to another organization")
        _text(recommendation_ref, "recommendation_ref")
        _text(outcome_label, "outcome_label")
        with self._lock:
            record = {
                "id": self._mint("opt-"),
                "org_id": org_id,
                "pool_id": pool_id,
                "recommendation_ref": recommendation_ref,
                "outcome_label": outcome_label,
                "optimized_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._optimization_recommendations[record["id"]] = record
        self._audit(actor, action, record["id"], {"pool_id": pool_id})
        return dict(record)

    def record_chargeback_report(self, actor, org_id, pool_id, period_label,
                                 amount_cents, report_ref):
        """Record a reported chargeback / showback figure for a pool.

        The amount is the platform's reported figure for the
        period, held verbatim as data in integer cents (a float
        is rejected at the boundary; money is never a float in
        this substrate). No charge is computed, apportioned, or
        levied here (``computed_here: False``, ``charged_here:
        False``).
        """
        action = "ext_chargeback_report_record"
        self._guard(actor, action)
        self._org(actor, org_id)
        pool = self._capacity_pool(pool_id)
        if pool["org_id"] != org_id:
            raise ValidationError("capacity pool belongs to another organization")
        _text(period_label, "period_label")
        amount_cents = _cents(amount_cents, "amount_cents")
        _text(report_ref, "report_ref")
        with self._lock:
            record = {
                "id": self._mint("cbr-"),
                "org_id": org_id,
                "pool_id": pool_id,
                "period_label": period_label,
                "amount_cents": amount_cents,
                "report_ref": report_ref,
                "computed_here": False,
                "charged_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._chargeback_reports[record["id"]] = record
        self._audit(actor, action, record["id"], {"pool_id": pool_id})
        return dict(record)

    def list_chargeback_reports(self, actor, org_id, pool_id=None):
        self._org(actor, org_id)
        return [dict(r) for r in self._chargeback_reports.values()
                if r["org_id"] == org_id
                and (pool_id is None or r["pool_id"] == pool_id)]

    def capacity_summary(self, actor, org_id):
        """Counts only, derived at read: pools, observations,
        optimization recommendations, chargeback reports.
        Reported amounts are never summed or averaged here --
        a total would be a figure no reporter reported."""
        self._org(actor, org_id)
        return {
            "org_id": org_id,
            "capacity_pools": sum(1 for r in self._capacity_pools.values()
                                  if r["org_id"] == org_id),
            "capacity_observations": sum(
                1 for r in self._capacity_observations.values()
                if r["org_id"] == org_id),
            "optimization_recommendations": sum(
                1 for r in self._optimization_recommendations.values()
                if r["org_id"] == org_id),
            "chargeback_reports": sum(
                1 for r in self._chargeback_reports.values()
                if r["org_id"] == org_id),
        }
