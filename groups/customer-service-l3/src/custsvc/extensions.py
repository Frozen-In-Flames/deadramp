"""Final GAPS batch extensions for the Customer Service
L3-adjacent singleton build (Group 41 singleton).

Clean-room, standard-library-only records/derivation extensions for
the 7 open entries this group's GAPS.md section carries -- the
fork's own platform substance, named from its prose in
``../UNION-SPEC.md``: 2 built as in-substrate records plus
deterministic derivations, and 5 shipped as labeled reference
implementations (4 drafted stub-engine, plus the hosted-application
ecosystem entry re-judged from build-extension -- see ``BATCH.md``
for the grounds). See ``BATCH.md`` in the group directory for the
per-entry disposition.

Design, following the core's doctrines and the High apparatus:

- This module is a wrapper around :class:`CustsvcStore`; the core
  modules are untouched (byte-identical). Core state (cases,
  alerts) is always read through the core store's public API,
  never re-implemented, and no extension operation writes core
  state.
- RBAC goes through :mod:`custsvc.access` exactly as the core
  enforces it: the extension maps each of its operations onto an
  existing core action (the core action set is fixed), checks it
  *before* any state change or id allocation for User-like actors,
  and records denied attempts on the core audit log with the
  extension action name suffixed ``:denied``. Plain-string actors
  carry identity but no role, mirroring the core convention. The
  mapping is:

  - operational records (hosting environments, inheritance,
    monitoring, vulnerabilities, patching, incidents, migrations,
    hosted applications) -> ``case_write`` / ``case_read``;
  - monitoring observation lists (records that bind core alerts)
    -> ``alert_read``;
  - derived summaries -> ``report_read``.

  The auditor role (``audit_read`` only, AC-5) is therefore denied
  every operation on this surface, reads included -- audit review
  stays separable from operations at this tier.

- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_`` -- the
  same hash-chained, fail-closed log as every core mutation
  (AU-9 / AU-5). If the audit write raises, the record insertion
  and its id roll back before the error propagates:
  audit-before-commit, so no extension record exists whose audit
  entry does not.
- All references to systems, customers, assets and applications
  are opaque ``*_ref`` strings, exactly as in the core. No record
  shape in this module can hold a real identifier, a credential, a
  certificate, or conversation content of any kind: there is no
  parameter anywhere on this surface that accepts message text, a
  transcript, a body, or a comment, and the test suite pins that
  content-shaped arguments raise ``TypeError`` and that no
  content- or score-shaped key exists on any record or view.
- Nothing is scored, routed, matched or inferred here: severity
  and outcome values are caller-reported labels held as data, and
  no record or view carries a score-shaped key (pinned by a
  recursive scan in the tests).
- Derived values are derived at read and never stored: a
  vulnerability's remediation state (from its recorded events, at
  the single seam :meth:`CustsvcExtensions._derive_vulnerability_state`),
  a migration project's current phase (from its recorded steps),
  and every summary count. Stored records carry no derived key;
  tests pin the exact stored key sets.
- Nothing here executes against an external system, and nothing
  is hosted, operated, monitored, scanned, patched, migrated or
  responded to by this build. The reference families carry
  ``reference_stub: True`` on every record; the built families are
  the records layer in front of operations that happen elsewhere,
  and their operation-facing records say so on their face
  (``scanned_here`` / ``applied_here`` / ``migrated_here`` are
  False wherever the question arises).
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

DELIVERY_MODELS = ("iaas", "paas", "saas")
KNOWN_DELIVERY_MODELS = frozenset(DELIVERY_MODELS)
ENVIRONMENT_REPORT_OUTCOMES = (
    "reported_operational",
    "reported_degraded",
    "reported_down",
)
KNOWN_ENVIRONMENT_REPORT_OUTCOMES = frozenset(ENVIRONMENT_REPORT_OUTCOMES)
ASSESSMENT_OUTCOMES = (
    "reported_completed",
    "reported_completed_with_findings",
    "reported_failed",
)
KNOWN_ASSESSMENT_OUTCOMES = frozenset(ASSESSMENT_OUTCOMES)
MONITORING_OUTCOMES = (
    "reported_nominal",
    "reported_anomaly",
    "reported_outage",
)
KNOWN_MONITORING_OUTCOMES = frozenset(MONITORING_OUTCOMES)
# Caller-reported severity labels, held as data. A label is not a
# score: nothing in this module combines, weights or computes one.
VULNERABILITY_SEVERITIES = ("critical", "high", "medium", "low")
KNOWN_VULNERABILITY_SEVERITIES = frozenset(VULNERABILITY_SEVERITIES)
VULNERABILITY_EVENT_KINDS = (
    "triage",
    "patch_report",
    "verification",
    "risk_acceptance",
)
# (kind, outcome) -> derived remediation state. Outcomes are the
# reporting system's labels, stored verbatim on the event records;
# the state exists only as this derivation, never on a record.
_VULNERABILITY_EVENT_OUTCOMES = {
    "triage": ("confirmed", "false_positive"),
    "patch_report": ("applied", "scheduled", "failed"),
    "verification": ("verified", "still_present"),
    "risk_acceptance": ("accepted",),
}
_VULNERABILITY_STATES = {
    ("triage", "confirmed"): "triaged",
    ("triage", "false_positive"): "closed_false_positive",
    ("patch_report", "applied"): "remediation_reported",
    ("patch_report", "scheduled"): "remediation_scheduled",
    ("patch_report", "failed"): "remediation_failed",
    ("verification", "verified"): "verified_closed",
    ("verification", "still_present"): "reopened",
    ("risk_acceptance", "accepted"): "risk_accepted",
}
PATCH_REPORT_OUTCOMES = (
    "reported_applied",
    "reported_partial",
    "reported_failed",
)
KNOWN_PATCH_REPORT_OUTCOMES = frozenset(PATCH_REPORT_OUTCOMES)
RESPONSE_OUTCOMES = (
    "reported_contained",
    "reported_eradicated",
    "reported_recovered",
    "reported_ongoing",
)
KNOWN_RESPONSE_OUTCOMES = frozenset(RESPONSE_OUTCOMES)
MIGRATION_STEPS = (
    "assessment",
    "planning",
    "wave_scheduling",
    "cutover",
    "validation",
    "closure",
)
KNOWN_MIGRATION_STEPS = frozenset(MIGRATION_STEPS)
MIGRATION_STEP_OUTCOMES = (
    "reported_completed",
    "reported_partial",
    "reported_failed",
)
KNOWN_MIGRATION_STEP_OUTCOMES = frozenset(MIGRATION_STEP_OUTCOMES)
_MIGRATION_PHASES = {
    "assessment": "assessed",
    "planning": "planned",
    "wave_scheduling": "wave_scheduled",
    "cutover": "cutover_reported",
    "validation": "validated",
    "closure": "closed",
}
HOSTING_REPORT_OUTCOMES = (
    "reported_available",
    "reported_degraded",
    "reported_unavailable",
)
KNOWN_HOSTING_REPORT_OUTCOMES = frozenset(HOSTING_REPORT_OUTCOMES)


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


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
            raise ValidationError(
                "each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


def _id_list(value, what):
    if value is None:
        return []
    if not isinstance(value, list) or not value:
        raise ValidationError("%s must be a non-empty list of ids" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError("each entry in %s must be an id string" % (what,))
        result.append(item)
    return result


class CustsvcExtensions:
    """GAPS-batch extension surface over a core CustsvcStore."""

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

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _iso(_utc_now())
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed (AU-5), mirroring the core store: an
                # operation whose audit write fails does not proceed
                # -- the insertion and the id roll back before the
                # error propagates.
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
            if all(record.get(f) == v for f, v in filters.items()):
                result.append(copy.deepcopy(record))
        return result

    def _core_case(self, case_id, actor):
        """Return the core case view (NotFoundError if absent)."""
        return self.store.get_case(case_id, actor)

    def _core_alert(self, alert_id, actor):
        """Return the core alert record (NotFoundError if absent)."""
        for alert in self.store.list_alerts(actor):
            if alert["id"] == alert_id:
                return alert
        raise NotFoundError("alert not found: %r" % (alert_id,))

    # -- virtualization & cloud hosting platform (stub-engine) --------
    #
    # The fork's product itself, shipped as labeled reference
    # records: environment registrations over opaque environment
    # refs and state reports stored verbatim. No environment is
    # provisioned, hosted or operated here, and no record shape
    # can hold a credential or a network address.

    def register_hosting_environment(self, environment_ref, delivery_model,
                                     actor):
        """Register a hosting-environment reference record.
        ``delivery_model`` is the caller's own label for the
        environment's delivery model (iaas / paas / saas), held
        as data."""
        self._guard(actor, "case_write", "ext_hosting_environment_register")
        _non_empty(environment_ref, "environment_ref")
        _one_of(delivery_model, KNOWN_DELIVERY_MODELS, DELIVERY_MODELS,
                "delivery_model")
        return self._create(
            "hosting_environment", "env",
            {"environment_ref": environment_ref,
             "delivery_model": delivery_model,
             "reference_stub": True, "hosted_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_hosting_environment_register")

    def get_hosting_environment(self, environment_id, actor):
        self._guard_read(actor, "case_read", "ext_hosting_environment_get",
                         target=environment_id)
        return self._fetch("hosting_environment", environment_id)

    def list_hosting_environments(self, actor):
        self._guard_read(actor, "case_read", "ext_hosting_environment_list")
        return self._list("hosting_environment")

    def record_environment_report(self, environment_id, outcome, actor):
        """Record a hosting platform's reported state for an
        environment, verbatim. The build operates nothing, so the
        report also carries ``operated_here: False``."""
        self._guard(actor, "case_write", "ext_environment_report",
                    target=environment_id)
        _one_of(outcome, KNOWN_ENVIRONMENT_REPORT_OUTCOMES,
                ENVIRONMENT_REPORT_OUTCOMES, "outcome")
        self._get("hosting_environment", environment_id)
        return self._create(
            "environment_report", "envr",
            {"environment_id": environment_id, "outcome": outcome,
             "reported": True, "reference_stub": True,
             "operated_here": False},
            actor, "ext_environment_report")

    def list_environment_reports(self, environment_id, actor):
        self._guard_read(actor, "case_read", "ext_environment_report_list",
                         target=environment_id)
        self._get("hosting_environment", environment_id)
        return self._list("environment_report", environment_id=environment_id)

    # -- authorization acceleration & control inheritance (stub) ------
    #
    # Inheritance records: a hosted customer (opaque ref), a
    # framework label and control labels held as data, and
    # assessment reports stored verbatim. Registering a record
    # named for a framework asserts no support for it, no control
    # is assessed here, and nothing is authorized: assessment and
    # authorization belong to assessors and authorizing officials
    # elsewhere (PLATFORM-LAYER.md decisions 1 and 6).

    def record_control_inheritance(self, customer_ref, framework_label,
                                   control_labels, actor):
        """Record that a hosted customer was reported to inherit a
        set of controls. ``control_labels`` are the caller's own
        labels for the controls, held as data."""
        self._guard(actor, "case_write", "ext_control_inheritance_record")
        _non_empty(customer_ref, "customer_ref")
        _non_empty(framework_label, "framework_label")
        labels = _string_list(control_labels, "control_labels")
        if not labels:
            raise ValidationError("control_labels must name at least one control")
        return self._create(
            "control_inheritance", "inh",
            {"customer_ref": customer_ref,
             "framework_label": framework_label,
             "control_labels": labels,
             "reference_stub": True, "assessed_here": False,
             "authorized_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_control_inheritance_record")

    def get_control_inheritance(self, inheritance_id, actor):
        self._guard_read(actor, "case_read", "ext_control_inheritance_get",
                         target=inheritance_id)
        return self._fetch("control_inheritance", inheritance_id)

    def list_control_inheritances(self, actor, customer_ref=None):
        self._guard_read(actor, "case_read", "ext_control_inheritance_list")
        filters = {}
        if customer_ref is not None:
            filters["customer_ref"] = customer_ref
        return self._list("control_inheritance", **filters)

    def record_assessment_report(self, inheritance_id, outcome, actor,
                                 reuse_label=None):
        """Record an assessor's reported outcome for an inheritance
        record, verbatim, with the assessor's reported reuse label
        held as data. The build assessed nothing."""
        self._guard(actor, "case_write", "ext_assessment_report",
                    target=inheritance_id)
        _one_of(outcome, KNOWN_ASSESSMENT_OUTCOMES, ASSESSMENT_OUTCOMES,
                "outcome")
        _string_or_none(reuse_label, "reuse_label")
        self._get("control_inheritance", inheritance_id)
        return self._create(
            "assessment_report", "asr",
            {"inheritance_id": inheritance_id, "outcome": outcome,
             "reuse_label": reuse_label, "reported": True,
             "reference_stub": True, "assessed_here": False},
            actor, "ext_assessment_report")

    def list_assessment_reports(self, inheritance_id, actor):
        self._guard_read(actor, "case_read", "ext_assessment_report_list",
                         target=inheritance_id)
        self._get("control_inheritance", inheritance_id)
        return self._list("assessment_report", inheritance_id=inheritance_id)

    # -- continuous monitoring & SOC operations (stub-engine) ---------
    #
    # Monitoring-source registrations and observation records
    # stored verbatim as reported by monitoring systems elsewhere.
    # Monitoring happens in those systems; a SOC is a staffed
    # operation, not a records function. An observation may
    # reference an existing core alert -- and only an existing
    # one: the core's alert ingest remains the only path by which
    # an alert record comes to exist, and an observation record
    # creates none (pinned by test).

    def register_monitoring_source(self, source_ref, actor):
        """Register a monitoring-source reference record."""
        self._guard(actor, "case_write", "ext_monitoring_source_register")
        _non_empty(source_ref, "source_ref")
        return self._create(
            "monitoring_source", "mon",
            {"source_ref": source_ref, "reference_stub": True,
             "monitors_here": False, "state": "recorded_reference_only"},
            actor, "ext_monitoring_source_register")

    def get_monitoring_source(self, source_id, actor):
        self._guard_read(actor, "case_read", "ext_monitoring_source_get",
                         target=source_id)
        return self._fetch("monitoring_source", source_id)

    def record_monitoring_observation(self, source_id, outcome, actor,
                                      alert_id=None):
        """Record a monitoring system's reported observation,
        verbatim. ``alert_id``, when given, must name an existing
        core alert -- the observation references it; it does not
        create or modify it. The outcome is the source system's
        reported label, held as data: nothing is detected here."""
        self._guard(actor, "case_write", "ext_monitoring_observation",
                    target=source_id)
        _one_of(outcome, KNOWN_MONITORING_OUTCOMES, MONITORING_OUTCOMES,
                "outcome")
        self._get("monitoring_source", source_id)
        if alert_id is not None:
            self._core_alert(alert_id, actor)
        return self._create(
            "monitoring_observation", "obs",
            {"source_id": source_id, "outcome": outcome,
             "alert_id": alert_id, "reported": True,
             "reference_stub": True, "detected_here": False},
            actor, "ext_monitoring_observation")

    def list_monitoring_observations(self, source_id, actor):
        self._guard_read(actor, "alert_read", "ext_monitoring_observation_list",
                         target=source_id)
        self._get("monitoring_source", source_id)
        return self._list("monitoring_observation", source_id=source_id)

    # -- vulnerability management & patching operations (built) -------
    #
    # The records layer of vulnerability management: a registry of
    # reported vulnerabilities over opaque asset refs, an append-only
    # event stream per vulnerability (triage, patch reports,
    # verifications, risk acceptances -- each outcome the reporting
    # system's label, stored verbatim), and patch campaign records
    # with their own reported outcomes. A vulnerability's
    # remediation state is derived at read from its event stream at
    # the single seam ``_derive_vulnerability_state`` and is never
    # stored. Scanning and patch application happen in other
    # systems: ``scanned_here`` and ``applied_here`` are False
    # wherever the question arises, and severity values are
    # caller-reported labels -- nothing here combines, weights or
    # computes a score from them.

    def register_vulnerability(self, asset_ref, severity, source_ref,
                               actor, cve_ref=None):
        """Register a reported vulnerability. ``asset_ref`` and
        ``source_ref`` are opaque caller references (the affected
        asset, the reporting system); ``cve_ref`` is an optional
        caller-supplied label held as data -- no lookup is done."""
        self._guard(actor, "case_write", "ext_vulnerability_register")
        _non_empty(asset_ref, "asset_ref")
        _one_of(severity, KNOWN_VULNERABILITY_SEVERITIES,
                VULNERABILITY_SEVERITIES, "severity")
        _non_empty(source_ref, "source_ref")
        _string_or_none(cve_ref, "cve_ref")
        return self._create(
            "vulnerability", "vuln",
            {"asset_ref": asset_ref, "severity": severity,
             "source_ref": source_ref, "cve_ref": cve_ref,
             "scanned_here": False},
            actor, "ext_vulnerability_register")

    def get_vulnerability(self, vulnerability_id, actor):
        """The stored vulnerability record. It carries no state
        key; remediation state exists only as the derivation in
        :meth:`vulnerability_view`."""
        self._guard_read(actor, "case_read", "ext_vulnerability_get",
                         target=vulnerability_id)
        return self._fetch("vulnerability", vulnerability_id)

    def list_vulnerabilities(self, actor, asset_ref=None):
        self._guard_read(actor, "case_read", "ext_vulnerability_list")
        filters = {}
        if asset_ref is not None:
            filters["asset_ref"] = asset_ref
        return self._list("vulnerability", **filters)

    def record_vulnerability_event(self, vulnerability_id, kind, outcome,
                                   actor):
        """Append one reported event to a vulnerability's stream.
        The (kind, outcome) pair is validated against the recorded
        vocabulary; the outcome is the reporting system's label,
        stored verbatim."""
        self._guard(actor, "case_write", "ext_vulnerability_event",
                    target=vulnerability_id)
        if kind not in _VULNERABILITY_EVENT_OUTCOMES:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(VULNERABILITY_EVENT_KINDS),))
        _one_of(outcome, frozenset(_VULNERABILITY_EVENT_OUTCOMES[kind]),
                _VULNERABILITY_EVENT_OUTCOMES[kind], "outcome")
        self._get("vulnerability", vulnerability_id)
        return self._create(
            "vulnerability_event", "vulne",
            {"vulnerability_id": vulnerability_id, "kind": kind,
             "outcome": outcome, "reported": True},
            actor, "ext_vulnerability_event")

    def list_vulnerability_events(self, vulnerability_id, actor):
        self._guard_read(actor, "case_read", "ext_vulnerability_event_list",
                         target=vulnerability_id)
        self._get("vulnerability", vulnerability_id)
        return self._list("vulnerability_event",
                          vulnerability_id=vulnerability_id)

    def _derive_vulnerability_state(self, events):
        """Derive a vulnerability's remediation state from its
        recorded events: the state named by the LATEST event, or
        ``reported`` when no event has been recorded.

        Single derivation point for remediation state; see the
        mutation record in tests/README.md (the batch's fresh
        negative control). Only validated (kind, outcome) pairs
        can be recorded, so the table lookup cannot miss.
        """
        if not events:
            return "reported"
        latest = events[-1]
        return _VULNERABILITY_STATES[(latest["kind"], latest["outcome"])]

    def vulnerability_view(self, vulnerability_id, actor):
        """Derived at read: the vulnerability record plus its
        derived remediation state and event count. Nothing derived
        is stored, and the stored record itself carries no state
        key."""
        self._guard_read(actor, "case_read", "ext_vulnerability_view",
                         target=vulnerability_id)
        record = self._fetch("vulnerability", vulnerability_id)
        events = self._list("vulnerability_event",
                            vulnerability_id=vulnerability_id)
        view = dict(record)
        view["state"] = self._derive_vulnerability_state(events)
        view["event_count"] = len(events)
        view["derived"] = True
        return view

    def create_patch_campaign(self, name, actor, vulnerability_ids=None):
        """Register a patch campaign record: a named operation
        against a set of registered vulnerabilities. Every named
        vulnerability must exist. The campaign is a record about
        patching done elsewhere; it applies nothing."""
        self._guard(actor, "case_write", "ext_patch_campaign_create")
        _non_empty(name, "name")
        ids = _id_list(vulnerability_ids, "vulnerability_ids")
        for vulnerability_id in ids:
            self._get("vulnerability", vulnerability_id)
        return self._create(
            "patch_campaign", "patch",
            {"name": name, "vulnerability_ids": ids,
             "applied_here": False},
            actor, "ext_patch_campaign_create")

    def get_patch_campaign(self, campaign_id, actor):
        self._guard_read(actor, "case_read", "ext_patch_campaign_get",
                         target=campaign_id)
        return self._fetch("patch_campaign", campaign_id)

    def list_patch_campaigns(self, actor):
        self._guard_read(actor, "case_read", "ext_patch_campaign_list")
        return self._list("patch_campaign")

    def record_patch_report(self, campaign_id, outcome, actor):
        """Record a patching system's reported outcome for a
        campaign, verbatim. The build applied nothing, so the
        report also carries ``applied_here: False``."""
        self._guard(actor, "case_write", "ext_patch_report",
                    target=campaign_id)
        _one_of(outcome, KNOWN_PATCH_REPORT_OUTCOMES,
                PATCH_REPORT_OUTCOMES, "outcome")
        self._get("patch_campaign", campaign_id)
        return self._create(
            "patch_report", "patchr",
            {"campaign_id": campaign_id, "outcome": outcome,
             "reported": True, "applied_here": False},
            actor, "ext_patch_report")

    def list_patch_reports(self, campaign_id, actor):
        self._guard_read(actor, "case_read", "ext_patch_report_list",
                         target=campaign_id)
        self._get("patch_campaign", campaign_id)
        return self._list("patch_report", campaign_id=campaign_id)

    def vulnerability_summary(self, actor):
        """Derived at read: registry counts -- vulnerabilities by
        reported severity label and by derived remediation state,
        event and campaign counts. Counts only; no score is
        computed from the severity labels."""
        self._guard_read(actor, "report_read", "ext_vulnerability_summary")
        vulnerabilities = self._list("vulnerability")
        by_severity = {s: 0 for s in VULNERABILITY_SEVERITIES}
        by_state = {}
        for record in vulnerabilities:
            by_severity[record["severity"]] += 1
            state = self._derive_vulnerability_state(
                self._list("vulnerability_event",
                           vulnerability_id=record["id"]))
            by_state[state] = by_state.get(state, 0) + 1
        return {"vulnerabilities": len(vulnerabilities),
                "by_severity": by_severity,
                "by_state": by_state,
                "events": len(self._list("vulnerability_event")),
                "patch_campaigns": len(self._list("patch_campaign")),
                "patch_reports": len(self._list("patch_report")),
                "scanned_here": False, "applied_here": False,
                "derived": True,
                "method": "counts_over_vulnerability_records"}

    # -- incident response operations, hosting boundary (stub) --------
    #
    # Incident records bound to the core substrate: an incident is
    # recorded against an existing core case (the response
    # operation's paper trail lives on the case record), optionally
    # linked to an existing core alert, and response reports store
    # the responding organization's reported outcome verbatim.
    # Response itself -- containment, eradication, recovery on the
    # hosting boundary -- is an operation performed elsewhere; a
    # test pins that recording an incident and its reports leaves
    # the core case exactly as it was.

    def record_incident_response(self, case_id, actor, alert_id=None):
        """Record an incident-response operation against a core
        case. Both ends, when named, must exist in the core."""
        self._guard(actor, "case_write", "ext_incident_response_record",
                    target=case_id)
        self._core_case(case_id, actor)
        if alert_id is not None:
            self._core_alert(alert_id, actor)
        return self._create(
            "incident_response", "inc",
            {"case_id": case_id, "alert_id": alert_id,
             "reference_stub": True, "responded_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_incident_response_record")

    def get_incident_response(self, incident_id, actor):
        self._guard_read(actor, "case_read", "ext_incident_response_get",
                         target=incident_id)
        return self._fetch("incident_response", incident_id)

    def list_incident_responses(self, actor, case_id=None):
        self._guard_read(actor, "case_read", "ext_incident_response_list")
        filters = {}
        if case_id is not None:
            filters["case_id"] = case_id
        return self._list("incident_response", **filters)

    def record_response_report(self, incident_id, outcome, actor):
        """Record a responding organization's reported outcome for
        an incident, verbatim. The build responded to nothing."""
        self._guard(actor, "case_write", "ext_response_report",
                    target=incident_id)
        _one_of(outcome, KNOWN_RESPONSE_OUTCOMES, RESPONSE_OUTCOMES,
                "outcome")
        self._get("incident_response", incident_id)
        return self._create(
            "response_report", "incr",
            {"incident_id": incident_id, "outcome": outcome,
             "reported": True, "reference_stub": True,
             "responded_here": False},
            actor, "ext_response_report")

    def list_response_reports(self, incident_id, actor):
        self._guard_read(actor, "case_read", "ext_response_report_list",
                         target=incident_id)
        self._get("incident_response", incident_id)
        return self._list("response_report", incident_id=incident_id)

    # -- migration & lift-and-shift services (built) -------------------
    #
    # The records layer of a migration service: project records
    # over opaque system refs with source/target environment
    # labels held as data, and step records in the service's
    # workflow shape (assessment -> planning -> wave scheduling ->
    # cutover -> validation -> closure), each with the migration
    # team's reported outcome stored verbatim. A project's current
    # phase is derived at read from its recorded steps at the seam
    # ``_derive_migration_phase`` and is never stored. No system is
    # migrated by this build: ``migrated_here`` is False on every
    # record and view where the question arises.

    def create_migration_project(self, system_ref, source_label,
                                 target_label, actor):
        """Register a migration project record. ``system_ref`` is
        an opaque reference to the system being migrated; the
        source and target environment labels are held as data."""
        self._guard(actor, "case_write", "ext_migration_project_create")
        _non_empty(system_ref, "system_ref")
        _non_empty(source_label, "source_label")
        _non_empty(target_label, "target_label")
        return self._create(
            "migration_project", "mig",
            {"system_ref": system_ref, "source_label": source_label,
             "target_label": target_label, "migrated_here": False},
            actor, "ext_migration_project_create")

    def get_migration_project(self, project_id, actor):
        """The stored project record. It carries no phase or
        status key; the phase exists only as the derivation in
        :meth:`migration_view`."""
        self._guard_read(actor, "case_read", "ext_migration_project_get",
                         target=project_id)
        return self._fetch("migration_project", project_id)

    def list_migration_projects(self, actor):
        self._guard_read(actor, "case_read", "ext_migration_project_list")
        return self._list("migration_project")

    def record_migration_step(self, project_id, step, outcome, actor):
        """Record one step of a migration project, with the
        migration team's reported outcome stored verbatim.
        Recording a cutover step performs no cutover."""
        self._guard(actor, "case_write", "ext_migration_step",
                    target=project_id)
        _one_of(step, KNOWN_MIGRATION_STEPS, MIGRATION_STEPS, "step")
        _one_of(outcome, KNOWN_MIGRATION_STEP_OUTCOMES,
                MIGRATION_STEP_OUTCOMES, "outcome")
        self._get("migration_project", project_id)
        return self._create(
            "migration_step", "migs",
            {"project_id": project_id, "step": step,
             "outcome": outcome, "reported": True,
             "executed_here": False},
            actor, "ext_migration_step")

    def list_migration_steps(self, project_id, actor):
        self._guard_read(actor, "case_read", "ext_migration_step_list",
                         target=project_id)
        self._get("migration_project", project_id)
        return self._list("migration_step", project_id=project_id)

    def _derive_migration_phase(self, steps):
        """Derive a migration project's current phase from its
        recorded steps: the phase named by the LATEST recorded
        step, or ``registered`` when no step has been recorded."""
        if not steps:
            return "registered"
        return _MIGRATION_PHASES[steps[-1]["step"]]

    def migration_view(self, project_id, actor):
        """Derived at read: the project record plus its derived
        current phase, recorded-step count and latest step
        outcome. Nothing derived is stored."""
        self._guard_read(actor, "case_read", "ext_migration_view",
                         target=project_id)
        record = self._fetch("migration_project", project_id)
        steps = self._list("migration_step", project_id=project_id)
        view = dict(record)
        view["phase"] = self._derive_migration_phase(steps)
        view["steps_recorded"] = len(steps)
        view["latest_step_outcome"] = steps[-1]["outcome"] if steps else None
        view["derived"] = True
        return view

    def migration_summary(self, actor):
        """Derived at read: project counts overall and by derived
        phase, plus step counts. No system is migrated here."""
        self._guard_read(actor, "report_read", "ext_migration_summary")
        projects = self._list("migration_project")
        by_phase = {}
        for record in projects:
            phase = self._derive_migration_phase(
                self._list("migration_step", project_id=record["id"]))
            by_phase[phase] = by_phase.get(phase, 0) + 1
        return {"projects": len(projects), "by_phase": by_phase,
                "steps": len(self._list("migration_step")),
                "migrated_here": False, "derived": True,
                "method": "counts_over_migration_records"}

    # -- hosted third-party application ecosystem (stub-engine) -------
    #
    # RE-JUDGED from build-extension to a labeled reference
    # implementation (DECISION.md qualification 1; grounds in
    # BATCH.md): the ecosystem is the hosting umbrella over other
    # vendors' products -- each catalogue application is its own
    # vendor's product and belongs to its own category's build --
    # and PLATFORM-LAYER.md decision 6 holds hosting surfaces to
    # be deployment properties unless a group's spec claims a
    # records function for them, which this group's spec does not.
    # What lands is therefore the declaration layer: application
    # registrations over opaque refs with vendor and category
    # labels held as data, and hosting reports stored verbatim.
    # No application is hosted, run or operated here.

    def register_hosted_application(self, app_ref, vendor_label,
                                    category_label, actor):
        """Register a hosted-application reference record. The
        vendor and category labels are the catalogue's own labels,
        held as data; the application remains its vendor's
        product."""
        self._guard(actor, "case_write", "ext_hosted_application_register")
        _non_empty(app_ref, "app_ref")
        _non_empty(vendor_label, "vendor_label")
        _non_empty(category_label, "category_label")
        return self._create(
            "hosted_application", "app",
            {"app_ref": app_ref, "vendor_label": vendor_label,
             "category_label": category_label,
             "reference_stub": True, "hosted_here": False,
             "operated_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_hosted_application_register")

    def get_hosted_application(self, application_id, actor):
        self._guard_read(actor, "case_read", "ext_hosted_application_get",
                         target=application_id)
        return self._fetch("hosted_application", application_id)

    def list_hosted_applications(self, actor):
        self._guard_read(actor, "case_read", "ext_hosted_application_list")
        return self._list("hosted_application")

    def record_hosting_report(self, application_id, outcome, actor):
        """Record a hosting platform's reported state for a hosted
        application, verbatim. The build hosts and operates
        nothing."""
        self._guard(actor, "case_write", "ext_hosting_report",
                    target=application_id)
        _one_of(outcome, KNOWN_HOSTING_REPORT_OUTCOMES,
                HOSTING_REPORT_OUTCOMES, "outcome")
        self._get("hosted_application", application_id)
        return self._create(
            "hosting_report", "appr",
            {"application_id": application_id, "outcome": outcome,
             "reported": True, "reference_stub": True,
             "hosted_here": False},
            actor, "ext_hosting_report")

    def list_hosting_reports(self, application_id, actor):
        self._guard_read(actor, "case_read", "ext_hosting_report_list",
                         target=application_id)
        self._get("hosted_application", application_id)
        return self._list("hosting_report", application_id=application_id)
