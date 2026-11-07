"""Final GAPS batch extensions for the Storage L3-adjacent
singleton.

Clean-room, standard-library-only extensions for the 7 open
entries of the singleton's GAPS.md section (see ``BATCH.md`` in
the group directory for the per-entry disposition). This module
is a wrapper around :class:`StorageStore`; every core module is
untouched and byte-identical to the shipped singleton build.

**The founding disciplines bind absolutely, here as in the
core.** The core holds metadata records only -- no field on any
core shape can hold a subject, a body, or any content -- and
neither can any shape here. In particular this build backs up
nothing, detects nothing, remediates nothing, connects to
nothing, synchronizes nothing, and renders no console: the
fork's substance (Commvault's backup & recovery service) is
engines over external systems and protected payloads this
substrate structurally does not hold. What lands is each
engine's in-substrate records form -- job, condition, outcome,
and receipt records over the carried core records, with every
current state derived at read. Methods accept only their named
parameters, so a caller cannot smuggle a forbidden field into
a record (pinned by tests: a ``content=``, ``payload=``, or
``key_material=`` keyword raises ``TypeError``).

Honesty of form, per the batch brief and the house precedent:

- Stub-engine entries ship as labeled reference
  implementations: every record carries ``reference_stub:
  True``. The backup & recovery engine lands as backup *job*
  records plus reported outcome and recovery records over core
  collections (``backed_up_here`` / ``recovered_here`` False --
  nothing leaves this process and no payload exists here to
  move). The anomaly detection & alerting engine lands as
  anomaly *report* records holding counts and severity labels
  **as reported** by an external detector (``detected_here``
  False) plus alert dispatch receipts (``alerted_here`` False,
  ``reference_transport: True``). Workload protection
  connectors land as connector records naming the catalogue
  workloads by label plus reported coverage records
  (``connected_here`` / ``protected_here`` False; per
  PLATFORM-LAYER.md decision 1 a connector record authenticates
  no one and opens no connection).
- Build-extension entries land in records form without the
  stub label, each with its execution half stated absent on
  the record. The granular remediation engine lands as
  remediation *action* records gated by a derivation over the
  core message's derived retention state through the single
  seam :meth:`StorageExtensions._derive_remediation_eligibility`
  (``executed_here`` False); recording one changes no core
  record (pinned by test). The management console lands as
  panel *definition* records held as data (``rendered_here``
  False) plus a console view derived at read from the core
  summary and this module's own counts -- the records function
  the fork's spec names for its console, per PLATFORM-LAYER.md
  decision 6; nothing is rendered or operated. SaaS operations
  automation lands as automation *rule* definitions held as
  data and reported run records (``executed_here`` /
  ``operated_here`` False) -- definitions are held, never run
  (the house registry rule). The hybrid cloud synchronization
  engine lands as sync *condition* records bound to a core
  collection and a registered integration, plus reported sync
  outcome records with the current outcome derived at read
  (``synchronized_here`` False -- peers and endpoints are
  records, never live systems).

**The High apparatus binds every extension.** Audit writes go
to the core store's hash-chained, fail-closed log with
``ext_``-prefixed actions for every successful mutation, and
denied write attempts are recorded with a ``:denied`` suffix
before the error propagates, so the chain covers the extension
surface exactly as it covers the core. RBAC is the core's
four-role matrix via :mod:`storage.access`, enforced before
any state change or id allocation, so a failed operation
consumes no id and changes nothing; the separated ``auditor``
role holds ``audit_read`` and nothing else, so it is denied
every extension operation, reads included (audit review stays
available to it through the core's ``audit_read``).

Doctrines carried from the core: derived-never-stored for
every computed value (current backup / recovery / automation /
sync outcome labels, dispatch and coverage counts, console and
extension counts -- each through a single derivation seam);
sizes and counts are integers only -- booleans and floats are
rejected at the boundary, as in the core.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

BACKUP_OUTCOME_LABELS = (
    "reported_succeeded",
    "reported_failed",
    "reported_partial",
)
RECOVERY_OUTCOME_LABELS = (
    "reported_restored",
    "reported_failed",
    "reported_pending",
)
REMEDIATION_ACTIONS = (
    "quarantine_copy",
    "remove_copy",
    "revoke_access",
    "restore_copy",
)
AUTOMATION_OUTCOME_LABELS = (
    "reported_applied",
    "reported_failed",
    "reported_skipped",
)
SYNC_OUTCOME_LABELS = (
    "reported_in_sync",
    "reported_diverged",
    "reported_failed",
)

# Keys that may never appear on any extension record or view:
# the founding discipline is that no shape here can hold
# content, a payload, key material, a free-text query, or a
# computed score. The test suite scans every record and view
# recursively against this set.
FORBIDDEN_KEYS = frozenset({
    "content", "body", "subject", "payload", "attachment",
    "message_text", "extracted_text", "key_material",
    "private_key", "secret", "password",
    "query", "query_text", "search_text", "full_text",
    "score", "rating", "rank",
})


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_moment(value, field):
    """Parse an ISO date or datetime into an aware datetime
    (the core store's convention, restated for the ``at`` /
    ``now`` parameters of the gated and derived surfaces)."""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                moment = datetime.strptime(text, "%Y-%m-%d")
            else:
                moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError(
                "%s is not an ISO date or datetime: %r" % (field, value))
    else:
        raise ValidationError(
            "%s must be an ISO date or datetime string" % field)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _count(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(
            "%s must be a non-negative integer" % field)
    return value


def _id_num(record_id):
    return int(record_id.rsplit("-", 1)[1])


def _latest_label(records):
    """Shared outcome derivation: the latest recorded record's
    outcome label, or ``unreported`` when none has been
    recorded. Pure function over records in creation order; a
    current outcome is never stored anywhere."""
    if not records:
        return "unreported"
    return records[-1]["outcome_label"]


class StorageExtensions:
    """Final-batch extension surface wrapping a core
    :class:`StorageStore`. Holds only extension records; every
    core record it names is resolved through the core store's
    own read API, so the core's permission checks, derivations,
    and fail-closed audit govern throughout."""

    def __init__(self, store):
        self.store = store
        self._backup_jobs = {}
        self._backup_outcomes = {}
        self._recovery_reports = {}
        self._anomaly_reports = {}
        self._alert_dispatches = {}
        self._remediation_actions = {}
        self._workload_connectors = {}
        self._connector_coverages = {}
        self._console_panels = {}
        self._automation_rules = {}
        self._automation_runs = {}
        self._sync_conditions = {}
        self._sync_outcomes = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`storage.access.require`; a plain string
        carries identity but no role). A denied attempt is
        recorded on the audit log with a ``:denied`` suffix
        before the error propagates; a missing actor is denied
        outright."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _create(self, table, prefix, fields, actor, audit_action):
        record = {"id": self._next_id(prefix)}
        record.update(fields)
        record["created_by"] = actor_name(actor)
        record["created_utc"] = _utc_now()
        table[record["id"]] = record
        self._audit(actor, audit_action, record["id"])
        return copy.deepcopy(record)

    @staticmethod
    def _sorted(records):
        return sorted(records, key=lambda r: _id_num(r["id"]))

    # Core-record resolution, always through the core's read API.

    def _core_message(self, actor, message_id, now=None):
        return self.store.get_message(actor, message_id, now=now)

    def _core_integration(self, actor, integration_id):
        for integration in self.store.list_integrations(actor):
            if integration["id"] == integration_id:
                return integration
        raise NotFoundError(
            "no such integration record: %r" % (integration_id,))

    # -- backup & recovery engine (idx 735, stub) -----------------------
    # Backup job records plus reported outcome / recovery
    # records. Nothing is backed up or restored here: this
    # substrate holds no payloads, and nothing leaves this
    # process.

    def record_backup_job(self, actor, collection_id, integration_id,
                          schedule_label, reported_item_count,
                          reported_byte_total):
        """Record one backup job for a core collection, as
        defined against a registered integration (the connector
        record naming the protected workload's platform): the
        schedule named by label and the item / byte counts
        stored **as reported** by the external backup system.
        Action: archive. Ids: bak-{n}. Labeled reference
        implementation (``reference_stub: True``,
        ``reference_transport: True``): ``backed_up_here`` is
        False -- recording a job backs nothing up, moves no
        bytes, and creates or changes no core record (pinned by
        test)."""
        self._guard(actor, "archive", "ext_backup_job_record")
        self.store.get_collection(actor, collection_id)
        integration = self._core_integration(actor, integration_id)
        _text(schedule_label, "schedule_label")
        _count(reported_item_count, "reported_item_count")
        _count(reported_byte_total, "reported_byte_total")
        with self._lock:
            return self._create(
                self._backup_jobs, "bak-",
                {"collection_id": collection_id,
                 "integration_id": integration_id,
                 "integration_kind": integration["kind"],
                 "schedule_label": schedule_label,
                 "reported_item_count": reported_item_count,
                 "reported_byte_total": reported_byte_total,
                 "reference_stub": True,
                 "reference_transport": True,
                 "backed_up_here": False},
                actor, "ext_backup_job_record")

    def record_backup_outcome(self, actor, job_id, outcome_label):
        """Record the reported outcome of a backup job: what the
        external backup system reports happened when it ran.
        Action: archive. Ids: bout-{n}. The label is stored as
        reported from the ``reported_*`` vocabulary;
        ``backed_up_here`` stays False. The job's current outcome
        is derived at read by :meth:`backup_job_view`, never
        stored."""
        self._guard(actor, "archive", "ext_backup_outcome_record")
        self._get(self._backup_jobs, job_id, "backup job")
        if outcome_label not in BACKUP_OUTCOME_LABELS:
            raise ValidationError(
                "unknown backup outcome label: %r" % (outcome_label,))
        with self._lock:
            return self._create(
                self._backup_outcomes, "bout-",
                {"job_id": job_id,
                 "outcome_label": outcome_label,
                 "reference_stub": True,
                 "backed_up_here": False},
                actor, "ext_backup_outcome_record")

    def record_recovery_report(self, actor, job_id, outcome_label):
        """Record the reported outcome of a recovery run for a
        backup job: what the external system reports happened
        when protected data was restored from the job's backups.
        Action: archive. Ids: rcv-{n}. The label is stored as
        reported from the ``reported_*`` vocabulary;
        ``recovered_here`` is False -- this build holds no
        payloads to restore and restores nothing. The current
        recovery outcome is derived at read, never stored."""
        self._guard(actor, "archive", "ext_recovery_report_record")
        self._get(self._backup_jobs, job_id, "backup job")
        if outcome_label not in RECOVERY_OUTCOME_LABELS:
            raise ValidationError(
                "unknown recovery outcome label: %r" % (outcome_label,))
        with self._lock:
            return self._create(
                self._recovery_reports, "rcv-",
                {"job_id": job_id,
                 "outcome_label": outcome_label,
                 "reference_stub": True,
                 "recovered_here": False},
                actor, "ext_recovery_report_record")

    def backup_job_view(self, actor, job_id):
        """One backup job record plus its derived outcome state:
        the outcome and recovery record counts, and the current
        outcome / recovery labels, each derived at read from the
        latest recorded label (``unreported`` when none). No
        derived key is stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._backup_jobs, job_id, "backup job")
        outcomes = [r for r in self._sorted(self._backup_outcomes.values())
                    if r["job_id"] == job_id]
        recoveries = [r for r in
                      self._sorted(self._recovery_reports.values())
                      if r["job_id"] == job_id]
        view = copy.deepcopy(record)
        view["outcome_count"] = len(outcomes)
        view["current_outcome_label"] = _latest_label(outcomes)
        view["recovery_count"] = len(recoveries)
        view["current_recovery_label"] = _latest_label(recoveries)
        return view

    def list_backup_jobs(self, actor, collection_id=None):
        self._maybe_require(actor, "read")
        if collection_id is not None:
            self.store.get_collection(actor, collection_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._backup_jobs.values())
                if collection_id is None
                or r["collection_id"] == collection_id]

    def list_backup_outcomes(self, actor, job_id=None):
        self._maybe_require(actor, "read")
        if job_id is not None:
            self._get(self._backup_jobs, job_id, "backup job")
        return [copy.deepcopy(r) for r in
                self._sorted(self._backup_outcomes.values())
                if job_id is None or r["job_id"] == job_id]

    def list_recovery_reports(self, actor, job_id=None):
        self._maybe_require(actor, "read")
        if job_id is not None:
            self._get(self._backup_jobs, job_id, "backup job")
        return [copy.deepcopy(r) for r in
                self._sorted(self._recovery_reports.values())
                if job_id is None or r["job_id"] == job_id]

    # -- anomaly detection & alerting engine (idx 736, stub) ------------
    # Anomaly reports hold what an external detector reported;
    # alert dispatches are receipts. Nothing is detected or
    # alerted here.

    def record_anomaly_report(self, actor, collection_id, detector_label,
                              reported_anomaly_count, severity_label):
        """Record one anomaly report for a core collection, as
        reported by an external detector: the detector named by
        label, the anomaly count and the severity label stored
        **as reported**, verbatim. Action: discover. Ids:
        anm-{n}. Labeled reference implementation
        (``reference_stub: True``): ``detected_here`` is False --
        detection is inference over protected data this
        substrate does not hold, performed by the external
        system; only its report lands here."""
        self._guard(actor, "discover", "ext_anomaly_report_record")
        self.store.get_collection(actor, collection_id)
        _text(detector_label, "detector_label")
        _count(reported_anomaly_count, "reported_anomaly_count")
        _text(severity_label, "severity_label")
        with self._lock:
            return self._create(
                self._anomaly_reports, "anm-",
                {"collection_id": collection_id,
                 "detector_label": detector_label,
                 "reported_anomaly_count": reported_anomaly_count,
                 "severity_label": severity_label,
                 "reference_stub": True,
                 "detected_here": False},
                actor, "ext_anomaly_report_record")

    def record_alert_dispatch(self, actor, anomaly_id, channel_label):
        """Record an alert dispatch receipt for an anomaly
        report: the alert channel named by label. Action:
        discover. Ids: alr-{n}. Labeled reference implementation
        (``reference_stub: True``, ``reference_transport:
        True``): ``alerted_here`` is False -- the alert path is
        the external system's; this record is its receipt."""
        self._guard(actor, "discover", "ext_alert_dispatch_record")
        self._get(self._anomaly_reports, anomaly_id, "anomaly report")
        _text(channel_label, "channel_label")
        with self._lock:
            return self._create(
                self._alert_dispatches, "alr-",
                {"anomaly_id": anomaly_id,
                 "channel_label": channel_label,
                 "reference_stub": True,
                 "reference_transport": True,
                 "alerted_here": False},
                actor, "ext_alert_dispatch_record")

    def anomaly_report_view(self, actor, anomaly_id):
        """One anomaly report plus ``dispatch_count`` derived at
        read from this module's dispatch receipts. The derived
        key is never stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._anomaly_reports, anomaly_id,
                           "anomaly report")
        view = copy.deepcopy(record)
        view["dispatch_count"] = sum(
            1 for r in self._alert_dispatches.values()
            if r["anomaly_id"] == anomaly_id)
        return view

    def list_anomaly_reports(self, actor, collection_id=None):
        self._maybe_require(actor, "read")
        if collection_id is not None:
            self.store.get_collection(actor, collection_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._anomaly_reports.values())
                if collection_id is None
                or r["collection_id"] == collection_id]

    def list_alert_dispatches(self, actor, anomaly_id=None):
        self._maybe_require(actor, "read")
        if anomaly_id is not None:
            self._get(self._anomaly_reports, anomaly_id, "anomaly report")
        return [copy.deepcopy(r) for r in
                self._sorted(self._alert_dispatches.values())
                if anomaly_id is None or r["anomaly_id"] == anomaly_id]

    # -- granular data remediation engine (idx 737) ----------------------
    # Remediation action records, gated by the eligibility seam.

    @staticmethod
    def _derive_remediation_eligibility(retention_state):
        """Remediation-eligibility seam: a remediation action may
        be recorded for a message in any derived retention state
        except ``disposed`` -- once disposition has been recorded
        there is nothing left in this substrate for a data-level
        action to concern. Pure function over the core's derived
        state string; the fresh negative control mutates it (see
        tests/README.md)."""
        return retention_state != "disposed"

    def record_remediation_action(self, actor, message_id, action_label,
                                  policy_ref, at=None):
        """Record a granular remediation action for an archived
        message: an action from this module's remediation
        vocabulary, taken under a stated policy reference.
        Action: enforce. Ids: rem-{n}. The record is **gated**:
        the message's derived retention state at the action
        moment is computed through the core's seam, and an
        action for a ``disposed`` message is refused whole via
        :meth:`_derive_remediation_eligibility`. The record
        states that an action was recorded; acting on the
        protected data itself is the external system's
        (``executed_here`` False), and recording one changes no
        core record (pinned by test)."""
        self._guard(actor, "enforce", "ext_remediation_action_record")
        if action_label not in REMEDIATION_ACTIONS:
            raise ValidationError(
                "unknown remediation action: %r" % (action_label,))
        _text(policy_ref, "policy_ref")
        moment = _parse_moment(at, "at") if at is not None else None
        view = self._core_message(actor, message_id, now=moment)
        if not self._derive_remediation_eligibility(
                view["retention_state"]):
            raise ValidationError(
                "message %s is 'disposed'; remediation actions are "
                "recorded only for messages not yet disposed"
                % (message_id,))
        with self._lock:
            return self._create(
                self._remediation_actions, "rem-",
                {"message_id": message_id,
                 "action_label": action_label,
                 "policy_ref": policy_ref,
                 "executed_here": False},
                actor, "ext_remediation_action_record")

    def remediation_action_view(self, actor, remediation_id, now=None):
        """One remediation action record plus the message's
        *current* derived retention state and whether an action
        would still be recordable for it, both derived at read
        through the core's seam and this module's eligibility
        seam. Neither derived key is stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._remediation_actions, remediation_id,
                           "remediation action")
        moment = _parse_moment(now, "now") if now is not None else None
        view = self._core_message(actor, record["message_id"],
                                  now=moment)
        out = copy.deepcopy(record)
        out["current_retention_state"] = view["retention_state"]
        out["currently_actionable"] = \
            self._derive_remediation_eligibility(
                view["retention_state"])
        return out

    def list_remediation_actions(self, actor, message_id=None):
        self._maybe_require(actor, "read")
        if message_id is not None:
            self._core_message(actor, message_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._remediation_actions.values())
                if message_id is None
                or r["message_id"] == message_id]

    # -- workload protection connectors (idx 738, stub) ------------------
    # Connector records naming catalogue workloads by label,
    # plus reported coverage records. Nothing connects here.

    def record_workload_connector(self, actor, org_id, workload_label,
                                  connector_label):
        """Record a workload protection connector for an
        organization: the protected workload and the connector
        named by labels (the fork's catalogue names -- Microsoft
        365, Salesforce, Kubernetes, endpoints, and the rest --
        held as data). Action: register. Ids: wlc-{n}. Labeled
        reference implementation (``reference_stub: True``):
        ``connected_here`` is False -- recording a connector
        opens no connection, authenticates no one (identity
        stays with the embedding organization, PLATFORM-LAYER.md
        decision 1), and protects nothing (``protected_here``
        False); the live connector is the external system's."""
        self._guard(actor, "register", "ext_workload_connector_record")
        self.store.get_organization(actor, org_id)
        _text(workload_label, "workload_label")
        _text(connector_label, "connector_label")
        with self._lock:
            return self._create(
                self._workload_connectors, "wlc-",
                {"org_id": org_id,
                 "workload_label": workload_label,
                 "connector_label": connector_label,
                 "reference_stub": True,
                 "connected_here": False,
                 "protected_here": False},
                actor, "ext_workload_connector_record")

    def record_connector_coverage(self, actor, connector_id,
                                  reported_protected_count):
        """Record a coverage report for a workload connector:
        the count of protected items stored **as reported** by
        the external connector. Action: register. Ids: cov-{n}.
        Labeled reference implementation (``reference_stub:
        True``, ``reference_transport: True``): the report is a
        receipt; nothing was synced or protected here."""
        self._guard(actor, "register", "ext_connector_coverage_record")
        self._get(self._workload_connectors, connector_id,
                  "workload connector")
        _count(reported_protected_count, "reported_protected_count")
        with self._lock:
            return self._create(
                self._connector_coverages, "cov-",
                {"connector_id": connector_id,
                 "reported_protected_count": reported_protected_count,
                 "reference_stub": True,
                 "reference_transport": True,
                 "protected_here": False},
                actor, "ext_connector_coverage_record")

    def workload_connector_view(self, actor, connector_id):
        """One workload connector record plus ``coverage_count``
        (the number of coverage reports recorded for it) derived
        at read. The derived key is never stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._workload_connectors, connector_id,
                           "workload connector")
        view = copy.deepcopy(record)
        view["coverage_count"] = sum(
            1 for r in self._connector_coverages.values()
            if r["connector_id"] == connector_id)
        return view

    def list_workload_connectors(self, actor, org_id=None):
        self._maybe_require(actor, "read")
        if org_id is not None:
            self.store.get_organization(actor, org_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._workload_connectors.values())
                if org_id is None or r["org_id"] == org_id]

    def list_connector_coverages(self, actor, connector_id=None):
        self._maybe_require(actor, "read")
        if connector_id is not None:
            self._get(self._workload_connectors, connector_id,
                      "workload connector")
        return [copy.deepcopy(r) for r in
                self._sorted(self._connector_coverages.values())
                if connector_id is None
                or r["connector_id"] == connector_id]

    # -- management console (idx 739) -------------------------------------
    # Panel definitions held as data, plus a console view
    # derived at read. Nothing is rendered or operated.

    def record_console_panel(self, actor, org_id, panel_label,
                             scope_label, widget_labels):
        """Record a management console panel definition as data:
        the panel's label, the scope it presents, and the widget
        labels it would show, for an organization. Action:
        admin (console configuration is the administrative
        plane). Ids: pan-{n}. Definitions are held, never
        rendered (``rendered_here`` False): the console surface
        this build carries is its records form -- panel
        definitions plus the derived :meth:`console_view` -- per
        PLATFORM-LAYER.md decision 6, the records function the
        fork's spec names for its Command Center console."""
        self._guard(actor, "admin", "ext_console_panel_record")
        self.store.get_organization(actor, org_id)
        _text(panel_label, "panel_label")
        _text(scope_label, "scope_label")
        if not isinstance(widget_labels, (list, tuple)) \
                or not widget_labels:
            raise ValidationError(
                "widget_labels must be a non-empty list of labels")
        labels = []
        for label in widget_labels:
            _text(label, "widget_label")
            labels.append(label)
        with self._lock:
            return self._create(
                self._console_panels, "pan-",
                {"org_id": org_id,
                 "panel_label": panel_label,
                 "scope_label": scope_label,
                 "widget_labels": labels,
                 "rendered_here": False},
                actor, "ext_console_panel_record")

    def list_console_panels(self, actor, org_id=None):
        self._maybe_require(actor, "read")
        if org_id is not None:
            self.store.get_organization(actor, org_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._console_panels.values())
                if org_id is None or r["org_id"] == org_id]

    def console_view(self, actor):
        """The console surface, derived at read: the core
        summary carried whole (the archive's own counts, through
        the core's seam) plus this module's extension counts.
        Every value is computed at read from records; the view
        itself is stored nowhere and renders nothing
        (``rendered_here`` False)."""
        self._maybe_require(actor, "read")
        return {
            "core_summary": self.store.summary(actor),
            "extension_counts": self._extension_counts(),
            "panel_count": len(self._console_panels),
            "rendered_here": False,
        }

    # -- SaaS operations automation (idx 740) ------------------------------
    # Rule definitions held as data, plus reported run records.
    # Definitions are held, never run; the service itself is
    # never operated.

    def record_automation_rule(self, actor, org_id, rule_label,
                               trigger_label, action_label):
        """Record a SaaS operations automation rule definition
        as data: what the vendor-side automation would do (a
        deployment, a patch cycle, an upgrade), named by labels,
        for an organization. Action: admin. Ids: aut-{n}.
        Definitions are held, never executed (``executed_here``
        False) -- the house rule that registries hold definitions
        only -- and nothing here operates the service
        (``operated_here`` False)."""
        self._guard(actor, "admin", "ext_automation_rule_record")
        self.store.get_organization(actor, org_id)
        _text(rule_label, "rule_label")
        _text(trigger_label, "trigger_label")
        _text(action_label, "action_label")
        with self._lock:
            return self._create(
                self._automation_rules, "aut-",
                {"org_id": org_id,
                 "rule_label": rule_label,
                 "trigger_label": trigger_label,
                 "action_label": action_label,
                 "executed_here": False,
                 "operated_here": False},
                actor, "ext_automation_rule_record")

    def record_automation_run(self, actor, rule_id, outcome_label):
        """Record the reported outcome of an automation rule's
        run: what the vendor-side automation reports it did.
        Action: register. Ids: run-{n}. The label is stored as
        reported from the ``reported_*`` vocabulary;
        ``executed_here`` is False -- the run happened (or not)
        in the vendor's operation of its own service, and only
        its report lands here. The rule's current outcome is
        derived at read, never stored."""
        self._guard(actor, "register", "ext_automation_run_record")
        self._get(self._automation_rules, rule_id, "automation rule")
        if outcome_label not in AUTOMATION_OUTCOME_LABELS:
            raise ValidationError(
                "unknown automation outcome label: %r" % (outcome_label,))
        with self._lock:
            return self._create(
                self._automation_runs, "run-",
                {"rule_id": rule_id,
                 "outcome_label": outcome_label,
                 "executed_here": False},
                actor, "ext_automation_run_record")

    def automation_rule_view(self, actor, rule_id):
        """One automation rule record plus ``run_count`` and
        ``current_outcome_label`` derived at read from its run
        records (``unreported`` when none). Neither derived key
        is stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._automation_rules, rule_id,
                           "automation rule")
        runs = [r for r in self._sorted(self._automation_runs.values())
                if r["rule_id"] == rule_id]
        view = copy.deepcopy(record)
        view["run_count"] = len(runs)
        view["current_outcome_label"] = _latest_label(runs)
        return view

    def list_automation_rules(self, actor, org_id=None):
        self._maybe_require(actor, "read")
        if org_id is not None:
            self.store.get_organization(actor, org_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._automation_rules.values())
                if org_id is None or r["org_id"] == org_id]

    def list_automation_runs(self, actor, rule_id=None):
        self._maybe_require(actor, "read")
        if rule_id is not None:
            self._get(self._automation_rules, rule_id, "automation rule")
        return [copy.deepcopy(r) for r in
                self._sorted(self._automation_runs.values())
                if rule_id is None or r["rule_id"] == rule_id]

    # -- hybrid cloud synchronization engine (idx 741) --------------------
    # Sync condition records plus reported outcome records.
    # Peers are records, never live endpoints; nothing is
    # synchronized here.

    def record_sync_condition(self, actor, collection_id, integration_id,
                              condition_label):
        """Record a hybrid cloud synchronization condition for a
        core collection, as defined against a registered
        integration (the record naming the estate side the
        collection is kept in step with): the condition named by
        an opaque label. Action: archive. Ids: hsc-{n}.
        ``synchronized_here`` is False: the condition is a
        records statement of what is to be kept synchronized;
        the keeping itself is the external engine's, and no peer
        is contacted (peers are records, never live endpoints).
        """
        self._guard(actor, "archive", "ext_sync_condition_record")
        self.store.get_collection(actor, collection_id)
        integration = self._core_integration(actor, integration_id)
        _text(condition_label, "condition_label")
        with self._lock:
            return self._create(
                self._sync_conditions, "hsc-",
                {"collection_id": collection_id,
                 "integration_id": integration_id,
                 "integration_kind": integration["kind"],
                 "condition_label": condition_label,
                 "synchronized_here": False},
                actor, "ext_sync_condition_record")

    def record_sync_outcome(self, actor, condition_id, outcome_label,
                            reported_object_count):
        """Record the reported outcome of a synchronization
        cycle for a sync condition: the outcome label and the
        object count stored **as reported** by the external
        synchronization engine. Action: archive. Ids: sout-{n}.
        ``synchronized_here`` stays False -- nothing was moved
        or reconciled in this process; only the engine's report
        lands here. The condition's current outcome is derived
        at read by :meth:`sync_condition_view`, never stored."""
        self._guard(actor, "archive", "ext_sync_outcome_record")
        self._get(self._sync_conditions, condition_id, "sync condition")
        if outcome_label not in SYNC_OUTCOME_LABELS:
            raise ValidationError(
                "unknown sync outcome label: %r" % (outcome_label,))
        _count(reported_object_count, "reported_object_count")
        with self._lock:
            return self._create(
                self._sync_outcomes, "sout-",
                {"condition_id": condition_id,
                 "outcome_label": outcome_label,
                 "reported_object_count": reported_object_count,
                 "synchronized_here": False},
                actor, "ext_sync_outcome_record")

    def sync_condition_view(self, actor, condition_id):
        """One sync condition record plus its derived outcome
        state: the outcome record count, the current outcome
        label (latest recorded, ``unreported`` when none), and
        the latest reported object count -- each derived at
        read. No derived key is stored."""
        self._maybe_require(actor, "read")
        record = self._get(self._sync_conditions, condition_id,
                           "sync condition")
        outcomes = [r for r in self._sorted(self._sync_outcomes.values())
                    if r["condition_id"] == condition_id]
        view = copy.deepcopy(record)
        view["outcome_count"] = len(outcomes)
        view["current_outcome_label"] = _latest_label(outcomes)
        view["latest_reported_object_count"] = (
            outcomes[-1]["reported_object_count"] if outcomes else None)
        return view

    def list_sync_conditions(self, actor, collection_id=None):
        self._maybe_require(actor, "read")
        if collection_id is not None:
            self.store.get_collection(actor, collection_id)
        return [copy.deepcopy(r) for r in
                self._sorted(self._sync_conditions.values())
                if collection_id is None
                or r["collection_id"] == collection_id]

    def list_sync_outcomes(self, actor, condition_id=None):
        self._maybe_require(actor, "read")
        if condition_id is not None:
            self._get(self._sync_conditions, condition_id,
                      "sync condition")
        return [copy.deepcopy(r) for r in
                self._sorted(self._sync_outcomes.values())
                if condition_id is None
                or r["condition_id"] == condition_id]

    # -- extension summary -------------------------------------------------

    def _extension_counts(self):
        """Deterministic counts over this module's own records,
        computed fresh each call. Counts only -- never scores."""
        return {
            "backup_jobs": len(self._backup_jobs),
            "backup_outcomes": len(self._backup_outcomes),
            "recovery_reports": len(self._recovery_reports),
            "anomaly_reports": len(self._anomaly_reports),
            "alert_dispatches": len(self._alert_dispatches),
            "remediation_actions": len(self._remediation_actions),
            "workload_connectors": len(self._workload_connectors),
            "connector_coverages": len(self._connector_coverages),
            "console_panels": len(self._console_panels),
            "automation_rules": len(self._automation_rules),
            "automation_runs": len(self._automation_runs),
            "sync_conditions": len(self._sync_conditions),
            "sync_outcomes": len(self._sync_outcomes),
        }

    def extension_summary(self, actor):
        """Counts over the extension records only, derived at
        read. Counts and recorded values -- never scores."""
        self._maybe_require(actor, "read")
        return self._extension_counts()
