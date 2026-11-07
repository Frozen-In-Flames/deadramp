"""Final GAPS batch extensions for the Cybersecurity L3-adjacent build.

This module is the extension surface built for the group's Extended
families (see ``UNION-SPEC.md`` function ranking, rows 1, 5, 8-10,
15-19, 21-25, and the coverage statement's long-tail list). It is a
NEW module added by the final GAPS batch: every pre-existing core
module in this package stays byte-identical, and nothing here weakens
the High-baseline uplifts (hash-chained audit, fail-closed writes,
audit query/reduction, the auditor role, logon lockout).

Category discipline, carried from the founding build and stated
plainly: **this is the shared defensive substrate only.** Nothing in
this module scans, detects, enforces, blocks, quarantines, executes,
or talks to any external system. Where an Extended family names an
engine or an agent, what lands here is the in-substrate **records
form** of that family: registries of the engines/agents/feeds the
embedding organization runs elsewhere, ingestion records for the
output they produce, and tracking workflows over those records. A
policy record's declared effect is data about an external system's
configuration; recording it changes nothing outside this register.
The three families whose honest form is one step further removed
(AI/ML detection models, backup & recovery products, SOAR / workflow
automation) ship as labeled reference implementations: every record
they produce carries ``reference_stub: True``, their status
vocabulary contains only ``recorded``, and a playbook record is a
definition that is never executed by anything here.

Doctrines, carried from the core and applied unchanged:

- **Deterministic scoring stays where the founding build put it.**
  The only computed scores in this package are the core's published
  severity x criticality finding table and likelihood x impact risk
  table (``cyber.store``). This module computes no score of any kind:
  severities, verdicts, confidences and counts arriving from external
  engines are recorded as the source's own data, and every rollup
  here is **counts and buckets only** (pinned by a recursive key scan
  in the tests: no extension record or view carries a score key).
- **Derived, never stored, where a value is a derivation.** Check-in
  counts and latest posture, outcome counts, current proofing
  outcome, session totals and every summary are computed at read time
  in the ``*_view`` / ``*_summary`` functions and are never keys on a
  stored record (pinned by tests).
- **Opaque references only.** Assets, people, endpoints, indicators
  and systems are caller-supplied opaque ``*_ref`` tokens. A ref may
  not be an IPv4 literal, a dotted hostname, a URL, or contain
  whitespace (pinned by tests), so no field can hold a real system's
  address; no field holds a credential or any PII. Record shapes are
  pinned exactly, as the core pins its shapes.
- **RBAC via the core access module.** Registrations and definitions
  require ``manage_assets``; ingestion of engine output requires
  ``ingest``; workflow decisions require ``triage``; views and
  summaries require ``read``. The auditor role (``audit_read`` only,
  AC-5) therefore holds no permission on this surface at all.
- **Append-only audit (AU), fail-closed (AU-5).** Every successful
  mutation is recorded on the same hash-chained ``AuditLog`` the core
  uses; if the audit write raises ``AuditWriteError`` the whole
  extension mutation rolls back (no object created, no id consumed).
  Denied attempts on this surface are also audit-recorded (action
  ``extension_denied``) before the denial propagates.
- **Separation of duties where a workflow has a decider.** A proofing
  outcome is never recorded by the user who opened the case.
"""

import copy
import functools
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .catalog import CONTROL_IDS
from .errors import AuditWriteError, NotFoundError, PermissionDenied, ValidationError

# -- vocabularies ------------------------------------------------------

AGENT_PLATFORMS = ("windows", "linux", "macos", "other")
CHECKIN_POSTURES = ("compliant", "noncompliant", "unknown")
DLP_CHANNELS = ("email", "web", "storage", "removable_media", "other")
DLP_DECLARED_ACTIONS = ("monitor", "alert")
CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")
MODEL_OUTPUT_LABELS = ("malicious", "suspicious", "benign", "unknown")
ENFORCEMENT_KINDS = ("firewall", "proxy", "gateway", "other")
ENFORCEMENT_DIRECTIONS = ("inbound", "outbound")
DECLARED_EFFECTS = ("allow", "deny")
BACKUP_OUTCOMES = ("succeeded", "failed", "partial")
RUN_OUTCOMES = ("completed", "failed", "cancelled")
INDICATOR_KINDS = ("file_hash", "network_ref", "file_ref", "other")
CONFIDENCE_LABELS = ("low", "medium", "high")
DETECTION_VERDICTS = ("malicious", "suspicious", "benign", "unknown")
SEVERITIES = ("critical", "high", "medium", "low", "info")
SCOPE_KINDS = ("cloud", "saas", "other")
POSTURE_RESULTS = ("pass", "fail", "not_applicable")
CAMPAIGN_OUTCOMES = (
    "sent_recorded",
    "opened_recorded",
    "clicked_recorded",
    "reported",
    "training_completed",
)
PROOFING_METHODS = (
    "document_check",
    "knowledge_check",
    "biometric_check",
    "manual_review",
)
PROOFING_OUTCOMES = ("verified_declared", "not_verified", "escalated")
SCAN_KINDS = ("sast", "dast", "sca", "other")
SCAN_RUN_STATES = ("completed", "failed")
ENCLAVE_LABELS = ("cui", "other")

_IPV4_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_HOSTNAME_RE = re.compile(r"^([a-z0-9-]+\.)+[a-z]{2,}$", re.IGNORECASE)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def count_by(values, choices):
    """Count ``values`` per choice in ``choices`` (counts only).

    The single counting seam for every extension rollup: posture is
    counts and buckets, never a computed score. The final GAPS
    batch's fresh negative control mutates this function to a
    classification-blind form; see tests/README.md.
    """
    counts = {choice: 0 for choice in choices}
    for value in values:
        if value in counts:
            counts[value] += 1
    return counts


def _fail_closed(method):
    """Roll the extension state back if the audit write fails (AU-5)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        snapshot = (copy.deepcopy(self._data), dict(self._counters))
        try:
            return method(self, *args, **kwargs)
        except AuditWriteError:
            self._data, self._counters = snapshot
            raise

    return wrapper


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_choice(value, choices, what):
    if value not in choices:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(choices))
        )
    return value


def _validate_ref(value, what):
    """Validate an opaque reference token.

    Refs identify things in the caller's world without naming any
    real system: no whitespace, no URL, no IPv4 literal, no dotted
    hostname. Anything address-shaped is refused at the boundary.
    """
    _validate_non_empty(value, what)
    if any(ch.isspace() for ch in value) or "://" in value or "/" in value:
        raise ValidationError("%s must be an opaque reference token" % (what,))
    if _IPV4_RE.match(value) or _HOSTNAME_RE.match(value):
        raise ValidationError(
            "%s must be an opaque reference, not an address" % (what,)
        )
    return value


def _validate_count(value, what, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    return value


def _validate_string_list(value, what):
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValidationError("%s must be a list of non-empty strings" % (what,))
    return list(value)


class ExtensionStore:
    """In-memory records substrate for the group's Extended families."""

    _COLLECTIONS = (
        "endpoint_agents", "agent_checkins",
        "dlp_policies", "dlp_events",
        "detection_models", "model_outputs",
        "enforcement_points", "enforcement_rules",
        "backup_jobs", "backup_runs", "restore_tests",
        "playbooks", "playbook_runs",
        "intel_feeds", "indicators",
        "edr_agents", "edr_detections",
        "posture_scopes", "posture_checks",
        "campaigns", "campaign_outcomes",
        "proofing_cases", "proofing_outcomes",
        "app_refs", "appsec_scans",
        "log_pipelines", "log_batches",
        "enclaves", "enclave_sessions",
        "scanners", "scan_runs",
    )

    _PREFIXES = {
        "endpoint_agents": "epa", "agent_checkins": "epc",
        "dlp_policies": "dlpp", "dlp_events": "dlpe",
        "detection_models": "mlm", "model_outputs": "mlo",
        "enforcement_points": "enfp", "enforcement_rules": "enfr",
        "backup_jobs": "bkj", "backup_runs": "bkr", "restore_tests": "rst",
        "playbooks": "pbk", "playbook_runs": "pbr",
        "intel_feeds": "feed", "indicators": "ioc",
        "edr_agents": "edra", "edr_detections": "edrd",
        "posture_scopes": "scp", "posture_checks": "pchk",
        "campaigns": "camp", "campaign_outcomes": "cout",
        "proofing_cases": "prfc", "proofing_outcomes": "prfo",
        "app_refs": "app", "appsec_scans": "apps",
        "log_pipelines": "logp", "log_batches": "logb",
        "enclaves": "enc", "enclave_sessions": "encs",
        "scanners": "scan", "scan_runs": "scanr",
    }

    # Collections whose records are labeled reference implementations.
    _STUB_COLLECTIONS = frozenset(
        ("detection_models", "model_outputs", "backup_jobs",
         "backup_runs", "restore_tests", "playbooks", "playbook_runs")
    )

    def __init__(self, audit=None):
        self.audit = audit
        self._data = {name: {} for name in self._COLLECTIONS}
        self._counters = {name: 0 for name in self._COLLECTIONS}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _require(self, actor, action, target):
        """Enforce a permission; denied attempts are audit-recorded."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(
                    actor, "extension_denied", target,
                    details={"action": action},
                )
                raise

    def _create(self, collection, fields, actor, action_name):
        """Assign an id, stamp provenance, store, audit, return a copy."""
        self._counters[collection] += 1
        record_id = "%s-%d" % (self._PREFIXES[collection], self._counters[collection])
        now = _utc_now()
        record = {"id": record_id}
        record.update(fields)
        if collection in self._STUB_COLLECTIONS:
            record["reference_stub"] = True
        record["created_by"] = actor_name(actor)
        record["created_utc"] = now
        self._data[collection][record_id] = record
        self._audit(actor, action_name, record_id)
        return copy.deepcopy(record)

    def _get(self, collection, record_id, what):
        record = self._data[collection].get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _list(self, collection):
        return [copy.deepcopy(r) for r in self._data[collection].values()]

    def _children(self, collection, key, parent_id):
        return [
            copy.deepcopy(r)
            for r in self._data[collection].values()
            if r[key] == parent_id
        ]

    # -- endpoint management agents (records form) ----------------------

    @_fail_closed
    def register_endpoint_agent(self, agent_ref, platform, asset_ref, actor):
        """Register an endpoint management agent the organization runs.

        Records form only: this registers the agent; nothing here
        enrolls, patches, or manages any endpoint.
        """
        _validate_ref(agent_ref, "agent_ref")
        _validate_choice(platform, AGENT_PLATFORMS, "platform")
        _validate_ref(asset_ref, "asset_ref")
        self._require(actor, "manage_assets", "endpoint_agents")
        with self._lock:
            return self._create(
                "endpoint_agents",
                {"agent_ref": agent_ref, "platform": platform,
                 "asset_ref": asset_ref},
                actor, "endpoint_agent_register",
            )

    @_fail_closed
    def record_agent_checkin(self, agent_id, posture, actor):
        """Record a check-in report received from an external agent."""
        _validate_choice(posture, CHECKIN_POSTURES, "posture")
        self._require(actor, "ingest", "agent_checkins")
        with self._lock:
            self._get("endpoint_agents", agent_id, "endpoint agent")
            return self._create(
                "agent_checkins",
                {"agent_id": agent_id, "posture": posture},
                actor, "agent_checkin_record",
            )

    def endpoint_agent_view(self, agent_id, actor):
        """One agent plus its derived check-in count and latest posture.

        Both derived values are computed at read time; neither is a
        key on the stored agent record.
        """
        self._require(actor, "read", "endpoint_agents")
        with self._lock:
            agent = copy.deepcopy(
                self._get("endpoint_agents", agent_id, "endpoint agent")
            )
            checkins = self._children("agent_checkins", "agent_id", agent_id)
            agent["checkin_count"] = len(checkins)
            agent["latest_posture"] = (
                checkins[-1]["posture"] if checkins else None
            )
            return agent

    # -- DLP engines (records form) --------------------------------------

    @_fail_closed
    def create_dlp_policy(self, name, channel, declared_action, actor):
        """Record a DLP policy as configured in an external engine.

        ``declared_action`` is the policy's declared intent, recorded
        as data; this substrate takes no action on any content.
        """
        _validate_non_empty(name, "policy name")
        _validate_choice(channel, DLP_CHANNELS, "channel")
        _validate_choice(declared_action, DLP_DECLARED_ACTIONS, "declared_action")
        self._require(actor, "manage_assets", "dlp_policies")
        with self._lock:
            return self._create(
                "dlp_policies",
                {"name": name, "channel": channel,
                 "declared_action": declared_action},
                actor, "dlp_policy_create",
            )

    @_fail_closed
    def record_dlp_event(self, policy_id, asset_ref, classification, actor):
        """Ingest one alert record produced by an external DLP engine."""
        _validate_ref(asset_ref, "asset_ref")
        _validate_choice(classification, CLASSIFICATIONS, "classification")
        self._require(actor, "ingest", "dlp_events")
        with self._lock:
            self._get("dlp_policies", policy_id, "DLP policy")
            return self._create(
                "dlp_events",
                {"policy_id": policy_id, "asset_ref": asset_ref,
                 "classification": classification},
                actor, "dlp_event_record",
            )

    def dlp_summary(self, actor):
        """Counts of DLP events by classification (counts only)."""
        self._require(actor, "read", "dlp_events")
        with self._lock:
            events = self._list("dlp_events")
            return {
                "policies": len(self._data["dlp_policies"]),
                "events": len(events),
                "events_by_classification": count_by(
                    [e["classification"] for e in events], CLASSIFICATIONS
                ),
            }

    # -- AI/ML detection models (labeled reference implementation) -------

    @_fail_closed
    def register_detection_model(self, name, provider_ref, version_label, actor):
        """Register a detection model as a labeled reference record.

        Reference implementation: the record describes a model the
        organization runs elsewhere. No model is loaded, trained, or
        executed here, and no inference is performed or claimed.
        """
        _validate_non_empty(name, "model name")
        _validate_ref(provider_ref, "provider_ref")
        _validate_non_empty(version_label, "version_label")
        self._require(actor, "manage_assets", "detection_models")
        with self._lock:
            return self._create(
                "detection_models",
                {"name": name, "provider_ref": provider_ref,
                 "version_label": version_label, "status": "recorded"},
                actor, "detection_model_register",
            )

    @_fail_closed
    def record_model_output(self, model_id, asset_ref, label, actor):
        """Record one output label an external model produced.

        The label is the model's own recorded output. This substrate
        computes nothing from it: there is no score, confidence, or
        derived verdict on the record.
        """
        _validate_ref(asset_ref, "asset_ref")
        _validate_choice(label, MODEL_OUTPUT_LABELS, "label")
        self._require(actor, "ingest", "model_outputs")
        with self._lock:
            self._get("detection_models", model_id, "detection model")
            return self._create(
                "model_outputs",
                {"model_id": model_id, "asset_ref": asset_ref,
                 "label": label, "status": "recorded"},
                actor, "model_output_record",
            )

    # -- network enforcement planes (records form) -----------------------

    @_fail_closed
    def register_enforcement_point(self, point_ref, kind, actor):
        """Register a network enforcement point run elsewhere."""
        _validate_ref(point_ref, "point_ref")
        _validate_choice(kind, ENFORCEMENT_KINDS, "kind")
        self._require(actor, "manage_assets", "enforcement_points")
        with self._lock:
            return self._create(
                "enforcement_points",
                {"point_ref": point_ref, "kind": kind},
                actor, "enforcement_point_register",
            )

    @_fail_closed
    def create_enforcement_rule(self, point_id, direction, declared_effect,
                                protocol_label, actor):
        """Record a rule as configured on an external enforcement point.

        The rule is a record of declared configuration. Nothing here
        applies it: no traffic is allowed, denied, or inspected by
        this substrate.
        """
        _validate_choice(direction, ENFORCEMENT_DIRECTIONS, "direction")
        _validate_choice(declared_effect, DECLARED_EFFECTS, "declared_effect")
        _validate_non_empty(protocol_label, "protocol_label")
        self._require(actor, "manage_assets", "enforcement_rules")
        with self._lock:
            self._get("enforcement_points", point_id, "enforcement point")
            return self._create(
                "enforcement_rules",
                {"point_id": point_id, "direction": direction,
                 "declared_effect": declared_effect,
                 "protocol_label": protocol_label, "status": "recorded"},
                actor, "enforcement_rule_create",
            )

    def enforcement_point_view(self, point_id, actor):
        """One enforcement point plus its derived rule count."""
        self._require(actor, "read", "enforcement_points")
        with self._lock:
            point = copy.deepcopy(
                self._get("enforcement_points", point_id, "enforcement point")
            )
            point["rule_count"] = len(
                self._children("enforcement_rules", "point_id", point_id)
            )
            return point

    # -- backup & recovery products (labeled reference implementation) ---

    @_fail_closed
    def register_backup_job(self, name, source_ref, schedule_label, actor):
        """Register a backup job as a labeled reference record.

        Reference implementation: no data is copied, snapshotted, or
        restored by anything here; runs and restore tests below are
        records of outcomes reported from elsewhere.
        """
        _validate_non_empty(name, "job name")
        _validate_ref(source_ref, "source_ref")
        _validate_non_empty(schedule_label, "schedule_label")
        self._require(actor, "manage_assets", "backup_jobs")
        with self._lock:
            return self._create(
                "backup_jobs",
                {"name": name, "source_ref": source_ref,
                 "schedule_label": schedule_label, "status": "recorded"},
                actor, "backup_job_register",
            )

    @_fail_closed
    def record_backup_run(self, job_id, outcome, size_units, actor):
        """Record one reported backup run (outcome and size as data)."""
        _validate_choice(outcome, BACKUP_OUTCOMES, "outcome")
        _validate_count(size_units, "size_units")
        self._require(actor, "ingest", "backup_runs")
        with self._lock:
            self._get("backup_jobs", job_id, "backup job")
            return self._create(
                "backup_runs",
                {"job_id": job_id, "outcome": outcome,
                 "size_units": size_units, "status": "recorded"},
                actor, "backup_run_record",
            )

    @_fail_closed
    def record_restore_test(self, job_id, outcome, actor):
        """Record one reported restore-test outcome for a backup job."""
        _validate_choice(outcome, BACKUP_OUTCOMES, "outcome")
        self._require(actor, "ingest", "restore_tests")
        with self._lock:
            self._get("backup_jobs", job_id, "backup job")
            return self._create(
                "restore_tests",
                {"job_id": job_id, "outcome": outcome,
                 "status": "recorded"},
                actor, "restore_test_record",
            )

    # -- SOAR / workflow automation (labeled reference implementation) ---

    @_fail_closed
    def create_playbook(self, name, steps, actor):
        """Record a playbook definition as a labeled reference record.

        Reference implementation: the registry never executes a
        playbook. ``steps`` are stored as the definition's own text;
        no step is run, dispatched, or acted on by anything here.
        """
        _validate_non_empty(name, "playbook name")
        steps = _validate_string_list(steps, "steps")
        if not steps:
            raise ValidationError("steps must be a non-empty list")
        self._require(actor, "manage_assets", "playbooks")
        with self._lock:
            return self._create(
                "playbooks",
                {"name": name, "steps": steps, "status": "recorded"},
                actor, "playbook_create",
            )

    @_fail_closed
    def record_playbook_run(self, playbook_id, trigger_ref, outcome, actor):
        """Record one playbook run reported from an external SOAR tool."""
        _validate_ref(trigger_ref, "trigger_ref")
        _validate_choice(outcome, RUN_OUTCOMES, "outcome")
        self._require(actor, "ingest", "playbook_runs")
        with self._lock:
            self._get("playbooks", playbook_id, "playbook")
            return self._create(
                "playbook_runs",
                {"playbook_id": playbook_id, "trigger_ref": trigger_ref,
                 "outcome": outcome, "status": "recorded"},
                actor, "playbook_run_record",
            )

    # -- threat-intelligence feeds (records form) -------------------------

    @_fail_closed
    def register_intel_feed(self, name, provider_ref, actor):
        """Register a threat-intelligence feed the organization consumes."""
        _validate_non_empty(name, "feed name")
        _validate_ref(provider_ref, "provider_ref")
        self._require(actor, "manage_assets", "intel_feeds")
        with self._lock:
            return self._create(
                "intel_feeds",
                {"name": name, "provider_ref": provider_ref},
                actor, "intel_feed_register",
            )

    @_fail_closed
    def add_indicator(self, feed_id, indicator_ref, kind, confidence_label,
                      actor):
        """Record one indicator published by a registered feed.

        ``indicator_ref`` is the feed's own opaque token for the
        indicator and ``confidence_label`` is the feed's own label;
        both are recorded as source data, never resolved, fetched, or
        scored here.
        """
        _validate_ref(indicator_ref, "indicator_ref")
        _validate_choice(kind, INDICATOR_KINDS, "kind")
        _validate_choice(confidence_label, CONFIDENCE_LABELS, "confidence_label")
        self._require(actor, "ingest", "indicators")
        with self._lock:
            self._get("intel_feeds", feed_id, "intel feed")
            return self._create(
                "indicators",
                {"feed_id": feed_id, "indicator_ref": indicator_ref,
                 "kind": kind, "confidence_label": confidence_label},
                actor, "indicator_add",
            )

    def intel_summary(self, actor):
        """Counts of indicators by kind (counts only)."""
        self._require(actor, "read", "indicators")
        with self._lock:
            indicators = self._list("indicators")
            return {
                "feeds": len(self._data["intel_feeds"]),
                "indicators": len(indicators),
                "indicators_by_kind": count_by(
                    [i["kind"] for i in indicators], INDICATOR_KINDS
                ),
            }

    # -- EDR agents (records form) -----------------------------------------

    @_fail_closed
    def register_edr_agent(self, agent_ref, asset_ref, actor):
        """Register an EDR agent the organization runs on an asset.

        Records form only: nothing here monitors, detects, isolates,
        or responds on any endpoint.
        """
        _validate_ref(agent_ref, "agent_ref")
        _validate_ref(asset_ref, "asset_ref")
        self._require(actor, "manage_assets", "edr_agents")
        with self._lock:
            return self._create(
                "edr_agents",
                {"agent_ref": agent_ref, "asset_ref": asset_ref},
                actor, "edr_agent_register",
            )

    @_fail_closed
    def record_edr_detection(self, agent_id, verdict, severity, actor):
        """Ingest one detection record produced by an external EDR agent.

        ``verdict`` and ``severity`` are the agent's own recorded
        output. Unlike a core finding, a detection record is never
        scored here: it carries no score or band key (pinned by
        tests); scoring begins only if a human promotes it through
        the core finding ingestion path.
        """
        _validate_choice(verdict, DETECTION_VERDICTS, "verdict")
        _validate_choice(severity, SEVERITIES, "severity")
        self._require(actor, "ingest", "edr_detections")
        with self._lock:
            self._get("edr_agents", agent_id, "EDR agent")
            return self._create(
                "edr_detections",
                {"agent_id": agent_id, "verdict": verdict,
                 "severity": severity},
                actor, "edr_detection_record",
            )

    # -- cloud / SaaS posture engines (records form) -----------------------

    @_fail_closed
    def register_posture_scope(self, scope_ref, kind, actor):
        """Register a cloud/SaaS scope an external posture engine checks."""
        _validate_ref(scope_ref, "scope_ref")
        _validate_choice(kind, SCOPE_KINDS, "kind")
        self._require(actor, "manage_assets", "posture_scopes")
        with self._lock:
            return self._create(
                "posture_scopes",
                {"scope_ref": scope_ref, "kind": kind},
                actor, "posture_scope_register",
            )

    @_fail_closed
    def record_posture_check(self, scope_id, control_id, result, actor):
        """Record one posture check result reported by an external engine.

        ``control_id`` must name a control in the core catalog, so a
        recorded result traces to the same control families the core
        assesses. The result is the engine's own; nothing here
        evaluates the scope.
        """
        if control_id not in CONTROL_IDS:
            raise ValidationError("unknown control id: %r" % (control_id,))
        _validate_choice(result, POSTURE_RESULTS, "result")
        self._require(actor, "ingest", "posture_checks")
        with self._lock:
            self._get("posture_scopes", scope_id, "posture scope")
            return self._create(
                "posture_checks",
                {"scope_id": scope_id, "control_id": control_id,
                 "result": result},
                actor, "posture_check_record",
            )

    def posture_engine_summary(self, actor):
        """Counts of posture check results (counts/buckets only)."""
        self._require(actor, "read", "posture_checks")
        with self._lock:
            checks = self._list("posture_checks")
            return {
                "scopes": len(self._data["posture_scopes"]),
                "checks": len(checks),
                "checks_by_result": count_by(
                    [c["result"] for c in checks], POSTURE_RESULTS
                ),
            }

    # -- phishing simulation / training content (records form) -------------

    @_fail_closed
    def create_campaign(self, name, template_ref, actor):
        """Record a phishing-simulation campaign run elsewhere.

        Records form only: no message is composed or sent here, and
        the campaign's only status is ``recorded``; outcomes below
        are reports of what the external campaign observed.
        """
        _validate_non_empty(name, "campaign name")
        _validate_ref(template_ref, "template_ref")
        self._require(actor, "manage_assets", "campaigns")
        with self._lock:
            return self._create(
                "campaigns",
                {"name": name, "template_ref": template_ref,
                 "status": "recorded"},
                actor, "campaign_create",
            )

    @_fail_closed
    def record_campaign_outcome(self, campaign_id, participant_ref, outcome,
                                actor):
        """Record one participant outcome reported by a campaign."""
        _validate_ref(participant_ref, "participant_ref")
        _validate_choice(outcome, CAMPAIGN_OUTCOMES, "outcome")
        self._require(actor, "ingest", "campaign_outcomes")
        with self._lock:
            self._get("campaigns", campaign_id, "campaign")
            return self._create(
                "campaign_outcomes",
                {"campaign_id": campaign_id,
                 "participant_ref": participant_ref, "outcome": outcome},
                actor, "campaign_outcome_record",
            )

    def campaign_view(self, campaign_id, actor):
        """One campaign plus its derived outcome counts (counts only)."""
        self._require(actor, "read", "campaigns")
        with self._lock:
            campaign = copy.deepcopy(
                self._get("campaigns", campaign_id, "campaign")
            )
            outcomes = self._children(
                "campaign_outcomes", "campaign_id", campaign_id
            )
            campaign["outcome_counts"] = count_by(
                [o["outcome"] for o in outcomes], CAMPAIGN_OUTCOMES
            )
            return campaign

    # -- fraud / identity-proofing products (records form) -----------------

    @_fail_closed
    def create_proofing_case(self, subject_ref, method, actor):
        """Open a record of an identity-proofing case handled elsewhere.

        Records form only, and per PLATFORM-LAYER.md decision 1 this
        substrate is not an identity provider: it records that a
        proofing happened and what outcome was declared; it performs
        no proofing and its records are not identity evidence.
        """
        _validate_ref(subject_ref, "subject_ref")
        _validate_choice(method, PROOFING_METHODS, "method")
        self._require(actor, "manage_risks", "proofing_cases")
        with self._lock:
            return self._create(
                "proofing_cases",
                {"subject_ref": subject_ref, "method": method},
                actor, "proofing_case_create",
            )

    @_fail_closed
    def record_proofing_outcome(self, case_id, outcome, actor):
        """Record a declared proofing outcome (separation of duties).

        The decider is never the user who opened the case.
        """
        _validate_choice(outcome, PROOFING_OUTCOMES, "outcome")
        self._require(actor, "triage", "proofing_outcomes")
        with self._lock:
            case = self._get("proofing_cases", case_id, "proofing case")
            if case["created_by"] == actor_name(actor):
                raise ValidationError(
                    "proofing outcome must be recorded by someone other "
                    "than the case creator (separation of duties)"
                )
            return self._create(
                "proofing_outcomes",
                {"case_id": case_id, "outcome": outcome},
                actor, "proofing_outcome_record",
            )

    def proofing_case_view(self, case_id, actor):
        """One case plus its derived current outcome (never stored)."""
        self._require(actor, "read", "proofing_cases")
        with self._lock:
            case = copy.deepcopy(
                self._get("proofing_cases", case_id, "proofing case")
            )
            outcomes = self._children(
                "proofing_outcomes", "case_id", case_id
            )
            case["outcome_count"] = len(outcomes)
            case["current_outcome"] = (
                outcomes[-1]["outcome"] if outcomes else None
            )
            return case

    # -- AppSec engines (records form) --------------------------------------

    @_fail_closed
    def register_app(self, app_ref, language_label, actor):
        """Register an application an external AppSec engine tests."""
        _validate_ref(app_ref, "app_ref")
        _validate_non_empty(language_label, "language_label")
        self._require(actor, "manage_assets", "app_refs")
        with self._lock:
            return self._create(
                "app_refs",
                {"app_ref": app_ref, "language_label": language_label},
                actor, "app_register",
            )

    @_fail_closed
    def record_appsec_scan(self, app_id, scan_kind, findings_reported, actor):
        """Record one scan run reported by an external AppSec engine.

        ``findings_reported`` is the engine's own count, recorded as
        data; nothing here scans code, and no finding detail enters
        through this surface (findings belong to core ingestion).
        """
        _validate_choice(scan_kind, SCAN_KINDS, "scan_kind")
        _validate_count(findings_reported, "findings_reported")
        self._require(actor, "ingest", "appsec_scans")
        with self._lock:
            self._get("app_refs", app_id, "app")
            return self._create(
                "appsec_scans",
                {"app_id": app_id, "scan_kind": scan_kind,
                 "findings_reported": findings_reported},
                actor, "appsec_scan_record",
            )

    def appsec_summary(self, actor):
        """Counts of AppSec scan records by kind (counts only)."""
        self._require(actor, "read", "appsec_scans")
        with self._lock:
            scans = self._list("appsec_scans")
            return {
                "apps": len(self._data["app_refs"]),
                "scans": len(scans),
                "scans_by_kind": count_by(
                    [s["scan_kind"] for s in scans], SCAN_KINDS
                ),
                "findings_reported_total": sum(
                    s["findings_reported"] for s in scans
                ),
            }

    # -- log pipelines (records form) ----------------------------------------

    @_fail_closed
    def register_log_pipeline(self, name, source_ref, actor):
        """Register a log pipeline operated elsewhere.

        The pipeline surface accepts **counts about batches only**:
        no function on it can accept log content, so no log line,
        payload, or message text can enter this register through it
        (pinned by a signature test).
        """
        _validate_non_empty(name, "pipeline name")
        _validate_ref(source_ref, "source_ref")
        self._require(actor, "manage_assets", "log_pipelines")
        with self._lock:
            return self._create(
                "log_pipelines",
                {"name": name, "source_ref": source_ref},
                actor, "log_pipeline_register",
            )

    @_fail_closed
    def record_log_batch(self, pipeline_id, record_count, window_label, actor):
        """Record that a pipeline delivered a batch of ``record_count``
        log records in a labeled window. Counts only; no content."""
        _validate_count(record_count, "record_count", minimum=1)
        _validate_non_empty(window_label, "window_label")
        self._require(actor, "ingest", "log_batches")
        with self._lock:
            self._get("log_pipelines", pipeline_id, "log pipeline")
            return self._create(
                "log_batches",
                {"pipeline_id": pipeline_id, "record_count": record_count,
                 "window_label": window_label},
                actor, "log_batch_record",
            )

    def log_pipeline_view(self, pipeline_id, actor):
        """One pipeline plus derived batch count and records total."""
        self._require(actor, "read", "log_pipelines")
        with self._lock:
            pipeline = copy.deepcopy(
                self._get("log_pipelines", pipeline_id, "log pipeline")
            )
            batches = self._children(
                "log_batches", "pipeline_id", pipeline_id
            )
            pipeline["batch_count"] = len(batches)
            pipeline["records_total"] = sum(
                b["record_count"] for b in batches
            )
            return pipeline

    # -- CUI enclaves / VDI (records form) ------------------------------------

    @_fail_closed
    def register_enclave(self, name, label, capacity, actor):
        """Register a CUI enclave / VDI pool operated elsewhere.

        Records form only: no desktop, session, or enclave is
        provisioned here; sessions below are usage records.
        """
        _validate_non_empty(name, "enclave name")
        _validate_choice(label, ENCLAVE_LABELS, "label")
        _validate_count(capacity, "capacity", minimum=1)
        self._require(actor, "manage_assets", "enclaves")
        with self._lock:
            return self._create(
                "enclaves",
                {"name": name, "label": label, "capacity": capacity},
                actor, "enclave_register",
            )

    @_fail_closed
    def record_enclave_session(self, enclave_id, user_ref, duration_minutes,
                               actor):
        """Record one enclave session (opaque user ref, minutes only)."""
        _validate_ref(user_ref, "user_ref")
        _validate_count(duration_minutes, "duration_minutes", minimum=1)
        self._require(actor, "ingest", "enclave_sessions")
        with self._lock:
            self._get("enclaves", enclave_id, "enclave")
            return self._create(
                "enclave_sessions",
                {"enclave_id": enclave_id, "user_ref": user_ref,
                 "duration_minutes": duration_minutes},
                actor, "enclave_session_record",
            )

    def enclave_view(self, enclave_id, actor):
        """One enclave plus derived session count and total minutes."""
        self._require(actor, "read", "enclaves")
        with self._lock:
            enclave = copy.deepcopy(
                self._get("enclaves", enclave_id, "enclave")
            )
            sessions = self._children(
                "enclave_sessions", "enclave_id", enclave_id
            )
            enclave["session_count"] = len(sessions)
            enclave["session_minutes_total"] = sum(
                s["duration_minutes"] for s in sessions
            )
            return enclave

    # -- vulnerability scanners (records form; ingestion is core) ------------

    @_fail_closed
    def register_scanner(self, name, provider_ref, actor):
        """Register a vulnerability scanner the organization runs.

        The scanner registry is the extension; finding ingestion and
        tracking themselves are core (``CyberStore.ingest_finding``)
        and are not duplicated here. Nothing here scans anything.
        """
        _validate_non_empty(name, "scanner name")
        _validate_ref(provider_ref, "provider_ref")
        self._require(actor, "manage_assets", "scanners")
        with self._lock:
            return self._create(
                "scanners",
                {"name": name, "provider_ref": provider_ref},
                actor, "scanner_register",
            )

    @_fail_closed
    def record_scan_run(self, scanner_id, asset_ref, state,
                        findings_reported, actor):
        """Record one scan run reported by an external scanner."""
        _validate_ref(asset_ref, "asset_ref")
        _validate_choice(state, SCAN_RUN_STATES, "state")
        _validate_count(findings_reported, "findings_reported")
        self._require(actor, "ingest", "scan_runs")
        with self._lock:
            self._get("scanners", scanner_id, "scanner")
            return self._create(
                "scan_runs",
                {"scanner_id": scanner_id, "asset_ref": asset_ref,
                 "state": state, "findings_reported": findings_reported},
                actor, "scan_run_record",
            )

    def scanner_view(self, scanner_id, actor):
        """One scanner plus derived run count and reported total."""
        self._require(actor, "read", "scanners")
        with self._lock:
            scanner = copy.deepcopy(
                self._get("scanners", scanner_id, "scanner")
            )
            runs = self._children("scan_runs", "scanner_id", scanner_id)
            scanner["run_count"] = len(runs)
            scanner["findings_reported_total"] = sum(
                r["findings_reported"] for r in runs
            )
            return scanner
