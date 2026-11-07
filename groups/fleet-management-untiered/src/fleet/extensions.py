"""Final GAPS batch extensions for the Fleet Management untiered
set (Untiered Set 15).

Clean-room, standard-library-only extensions for the 7 open
entries of the "Untiered Set 15 — Fleet Management (2 forks,
tier null)" section of GAPS.md (see ``BATCH.md`` in the group
directory for the per-entry disposition). This module is a
wrapper around :class:`FleetStore`; every core module is
untouched and byte-identical to the shipped build.

**Tier discipline binds absolutely:** this set is untiered —
the source publishes no FedRAMP impact level for either fork —
so this module asserts no tier, no baseline, and no CMMC
equivalence, and no record or view it produces carries a tier,
baseline, impact-level, or CMMC key (pinned by a recursive
scan in the tests).

**The category's founding discipline binds absolutely, here as
in the core:** this build holds records about fleet operations.
It streams no telemetry, senses no position, ingests no device
data, analyzes no video, connects to no external system,
dispatches no vehicle, controls no charging station, moves no
money, and renders no front-end. In particular, the category's
defining inverse invariant holds on this surface too: **there
is no charge-control surface anywhere** — no method here can
start, stop, limit, or otherwise command a charging session;
charging in this build is custody accounting in the core, and
nothing in this module adds a command path to it. Every entity
shape in this module carries metadata and opaque
caller-supplied references only, plus figures and outcomes
stored exactly as reported by the external systems and people
who actually did the work. Methods accept only their named
parameters, so a caller cannot smuggle an unlisted field into
a record (pinned by tests: an unexpected keyword raises
``TypeError`` — there is no ``latitude=`` or ``longitude=``
parameter anywhere, and no coordinate field exists in any
shape).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records over the group's OWN records
(core records and extension records), plus deterministic
derivations at read:

- Live telematics & GPS streaming ships as a labeled reference
  implementation: stream-subscription records held as data plus
  caller-REPORTED position/status records, each holding the
  reported position label verbatim (``tracked_here`` /
  ``sensed_here`` are False). Each record is standalone — no
  track, trail, or history structure exists.
- Integration engines & external connectors ship as a labeled
  reference implementation: connector records naming an
  external system by label and opaque reference, plus reported
  invocation/sync outcome records with labels verbatim
  (``connected_here`` / ``invoked_here`` are False). The
  build's own REST API is its contract, not a connector, and
  is not what this entry closes.
- Video-based safety & dash-camera analytics ships as a
  labeled reference implementation: camera-binding records
  plus reported safety-event records with the event kind and
  severity held verbatim as reported (``analyzed_here`` /
  ``footage_held_here`` are False — no frame, clip, or image
  can exist in any shape here).
- IoT device telemetry ingestion & equipment / environmental
  monitoring ships as a labeled reference implementation:
  device records plus reported observation records holding
  the reported value label verbatim (``ingested_here`` /
  ``sensed_here`` are False). Nothing is received from any
  device through this surface.
- Alerting & notification engines ship in records form:
  alert-rule records held as data (a condition label, never
  evaluated — ``evaluated_here`` False), alert records raised
  by reporters against a rule (``detected_here`` False — the
  detection happened in the system that reported it), and
  notification records in the house delivery-attempt form
  (``reference_transport`` True, ``delivered_here`` False,
  outcome labels verbatim). Counts derive at read.
- Driver workflow & compliance applications ship as a
  labeled reference implementation: workflow-task records
  bound to core operator records holding the reported status
  label verbatim (``executed_here`` False), plus
  compliance-application records holding the reported
  compliance label verbatim (``evaluated_here`` False — no
  compliance status is determined here; the set's "regulatory
  compliance" prose is an application area, not a control
  claim, and nothing here converts it into one).
- Dashboarding front-ends beyond registry reporting ship as
  dashboard-definition records (panel kinds held as data from
  a fixed set) plus a read-time DERIVATION of the panel
  figures over the substrate's own core records — counts,
  aggregate recorded watt-hours, latest recorded odometer,
  and the maintenance completed share as an exact fraction.
  No front-end is rendered (``rendered_here`` False); the
  view is data. The derivation seam is
  :func:`_maintenance_completed_share` — the batch's fresh
  negative control target.

Doctrines carried from the core: derived-never-stored for
every computed value (report counts, outcome counts, panel
figures); append-only audit on the core store's log with
``ext_``-prefixed actions for every successful mutation, and
denied write attempts recorded with a ``:denied`` suffix;
RBAC via :mod:`fleet.access` with the core's existing actions
(``read`` / ``write``), enforced before any state change or
id allocation, so a failed operation consumes no id and
changes nothing. The RBAC and audit hooks are baseline-neutral
substrate at tier null, claimed against no baseline.
"""

import copy
import threading
from datetime import datetime, timezone
from fractions import Fraction

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

TELEMATICS_STREAM_KINDS = (
    "gps_stream",
    "telematics_feed",
    "status_feed",
)
TELEMATICS_REPORT_KINDS = (
    "position_report",
    "status_report",
)
CONNECTOR_DIRECTION_LABELS = (
    "inbound",
    "outbound",
    "bidirectional",
)
CONNECTOR_OUTCOME_LABELS = (
    "reported_succeeded",
    "reported_failed",
    "reported_partial",
)
CAMERA_DEVICE_KINDS = (
    "dash_camera",
    "cabin_camera",
    "external_camera",
)
VIDEO_EVENT_KINDS = (
    "reported_hard_brake",
    "reported_distraction",
    "reported_collision",
    "reported_near_miss",
    "reported_speeding",
)
VIDEO_SEVERITY_LABELS = (
    "reported_low",
    "reported_medium",
    "reported_high",
    "reported_critical",
)
IOT_DEVICE_KINDS = (
    "vehicle_gateway",
    "dash_camera",
    "environmental_sensor",
    "equipment_monitor",
)
ALERT_SEVERITY_LABELS = (
    "reported_info",
    "reported_warning",
    "reported_critical",
)
NOTIFICATION_CHANNEL_KINDS = (
    "email",
    "sms",
    "webhook",
    "push",
)
NOTIFICATION_OUTCOME_LABELS = (
    "reported_delivered",
    "reported_failed",
    "reported_pending",
)
WORKFLOW_STATUS_LABELS = (
    "reported_assigned",
    "reported_in_progress",
    "reported_completed",
    "reported_blocked",
)
COMPLIANCE_LABELS = (
    "reported_compliant",
    "reported_noncompliant",
    "reported_exempt",
    "reported_pending_review",
)
DASHBOARD_PANEL_KINDS = (
    "record_counts",
    "charging_energy",
    "maintenance_completed_share",
    "latest_odometer",
)

_REFERENCE_STATE = "recorded_reference_only"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _fraction_out(amount):
    """Render an exact Fraction for a view: an int when whole,
    else the exact ``"num/den"`` string. Nothing is rounded."""
    if amount.denominator == 1:
        return amount.numerator
    return "%d/%d" % (amount.numerator, amount.denominator)


def _maintenance_completed_share(views):
    """Maintenance completed-share derivation seam: the single
    point where a dashboard's maintenance panel figure is
    derived.

    Given core maintenance views (each carrying the core's
    ``derived_status``), return the exact :class:`Fraction` of
    views whose derived status is ``completed``, or ``None``
    when there are no maintenance records at all. The share is
    over the core's own derived statuses — nothing is
    re-derived or re-judged here.

    MUTATION DRILL NOTE: this seam is the batch unit's fresh
    negative control target — counting a different status
    (e.g. ``overdue``) as completed would silently corrupt
    every dashboard maintenance panel while leaving the record
    shapes intact (see tests/README.md).
    """
    if not views:
        return None
    completed = sum(1 for v in views
                    if v["derived_status"] == "completed")
    return Fraction(completed, len(views))


class FleetUntieredExtensions:
    """Extension surface wrapping one :class:`FleetStore`."""

    def __init__(self, store):
        self.store = store
        self._telematics_streams = {}
        self._telematics_reports = {}
        self._connectors = {}
        self._connector_outcomes = {}
        self._camera_bindings = {}
        self._video_events = {}
        self._iot_devices = {}
        self._iot_observations = {}
        self._alert_rules = {}
        self._alerts = {}
        self._notifications = {}
        self._workflow_tasks = {}
        self._compliance_records = {}
        self._dashboards = {}
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
        """Enforce a permission before any state change.

        Mirrors the core convention (a User-like actor is checked
        via :func:`fleet.access.require`; a plain string carries
        identity but no role). A denied attempt is recorded on
        the audit log with a ``:denied`` suffix before the error
        propagates; a missing actor is denied outright.
        """
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

    # -- telematics & GPS streaming (entry: Live telematics & GPS
    #    streaming — labeled reference implementation) ----------------

    def create_telematics_stream(self, actor, vehicle_id, kind,
                                 source_ref):
        """Record a telematics stream subscription. Action: write.

        Reference implementation only: the record states that an
        external stream exists; no stream is opened and nothing
        is received through this surface. ``source_ref`` is an
        opaque reference to the external stream.
        """
        self._guard(actor, "write", "ext_telematics_stream_create")
        if kind not in TELEMATICS_STREAM_KINDS:
            raise ValidationError(
                "unknown telematics stream kind: %r" % (kind,))
        _non_empty(source_ref, "source_ref")
        self.store.get_vehicle(vehicle_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("tlm-"),
                "vehicle_id": vehicle_id,
                "kind": kind,
                "source_ref": source_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "streamed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._telematics_streams[record["id"]] = record
        self._audit(actor, "ext_telematics_stream_create", record["id"],
                    {"vehicle_id": vehicle_id})
        return copy.deepcopy(record)

    def record_telematics_report(self, actor, stream_id, kind,
                                 position_label, status_label=None):
        """Record a telematics report exactly as reported. Action:
        write.

        The position and status labels are caller-reported data,
        stored verbatim; nothing here senses, locates, or tracks
        a vehicle (``tracked_here`` / ``sensed_here`` are False).
        Each report is a standalone record — there is no track,
        trail, or history structure, and no coordinate field
        exists in this shape.
        """
        self._guard(actor, "write", "ext_telematics_report_create")
        if kind not in TELEMATICS_REPORT_KINDS:
            raise ValidationError(
                "unknown telematics report kind: %r" % (kind,))
        _non_empty(position_label, "position_label")
        if status_label is not None:
            _non_empty(status_label, "status_label")
        with self._lock:
            self._get(self._telematics_streams, stream_id,
                      "telematics stream")
            record = {
                "id": self._next_id("tlr-"),
                "stream_id": stream_id,
                "kind": kind,
                "position_label": position_label,
                "status_label": status_label,
                "tracked_here": False,
                "sensed_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._telematics_reports[record["id"]] = record
        self._audit(actor, "ext_telematics_report_create", record["id"],
                    {"stream_id": stream_id})
        return copy.deepcopy(record)

    def telematics_stream_view(self, actor, stream_id):
        """A stream record plus its report count, derived at read.
        Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            stream = self._get(self._telematics_streams, stream_id,
                               "telematics stream")
            view = copy.deepcopy(stream)
            reports = [r for r in self._telematics_reports.values()
                       if r["stream_id"] == stream_id]
            view["report_count"] = len(reports)
            return view

    # -- integration engines & external connectors (entry:
    #    Integration engines & external connectors — labeled
    #    reference implementation) --------------------------------------

    def create_connector(self, actor, system_label, direction_label,
                         endpoint_ref):
        """Record an external connector. Action: write.

        Reference implementation only: the record names an
        external system the fork's platform would integrate
        with, by label and opaque reference. Nothing here
        connects to, authenticates against, or exchanges data
        with that system (``connected_here`` / ``invoked_here``
        are False). The build's own REST API is its contract,
        not a connector, and is not recorded here.
        """
        self._guard(actor, "write", "ext_connector_create")
        _non_empty(system_label, "system_label")
        if direction_label not in CONNECTOR_DIRECTION_LABELS:
            raise ValidationError(
                "unknown connector direction label: %r"
                % (direction_label,))
        _non_empty(endpoint_ref, "endpoint_ref")
        with self._lock:
            record = {
                "id": self._next_id("con-"),
                "system_label": system_label,
                "direction_label": direction_label,
                "endpoint_ref": endpoint_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "connected_here": False,
                "invoked_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connectors[record["id"]] = record
        self._audit(actor, "ext_connector_create", record["id"],
                    {"system_label": system_label})
        return copy.deepcopy(record)

    def record_connector_outcome(self, actor, connector_id,
                                 outcome_label):
        """Record a connector invocation/sync outcome exactly as
        reported. Action: write. The label is stored verbatim;
        the outcome was produced by the external integration
        that actually ran, not here."""
        self._guard(actor, "write", "ext_connector_outcome_create")
        if outcome_label not in CONNECTOR_OUTCOME_LABELS:
            raise ValidationError(
                "unknown connector outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get(self._connectors, connector_id, "connector")
            record = {
                "id": self._next_id("cno-"),
                "connector_id": connector_id,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connector_outcomes[record["id"]] = record
        self._audit(actor, "ext_connector_outcome_create", record["id"],
                    {"connector_id": connector_id})
        return copy.deepcopy(record)

    def connector_view(self, actor, connector_id):
        """A connector record plus its outcome count, derived at
        read. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            connector = self._get(self._connectors, connector_id,
                                  "connector")
            view = copy.deepcopy(connector)
            view["outcome_count"] = len(
                [o for o in self._connector_outcomes.values()
                 if o["connector_id"] == connector_id])
            return view

    # -- video-based safety & dash-camera analytics (entry:
    #    Video-based safety & dash-camera analytics engines —
    #    labeled reference implementation) ------------------------------

    def create_camera_binding(self, actor, vehicle_id, device_kind,
                              device_ref):
        """Record a binding between a core vehicle and an
        external camera device. Action: write.

        Reference implementation only: ``device_ref`` is an
        opaque reference; nothing here connects to a camera,
        receives a frame, or holds footage (``connected_here``
        / ``footage_held_here`` are False).
        """
        self._guard(actor, "write", "ext_camera_binding_create")
        if device_kind not in CAMERA_DEVICE_KINDS:
            raise ValidationError(
                "unknown camera device kind: %r" % (device_kind,))
        _non_empty(device_ref, "device_ref")
        self.store.get_vehicle(vehicle_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("cam-"),
                "vehicle_id": vehicle_id,
                "device_kind": device_kind,
                "device_ref": device_ref,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "connected_here": False,
                "footage_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._camera_bindings[record["id"]] = record
        self._audit(actor, "ext_camera_binding_create", record["id"],
                    {"vehicle_id": vehicle_id})
        return copy.deepcopy(record)

    def record_video_event(self, actor, binding_id, event_kind,
                           severity_label):
        """Record a video-safety event exactly as reported.
        Action: write.

        The event kind and severity are stored verbatim, as
        classified by the external video system that actually
        analyzed the footage. Nothing here analyzes video,
        detects an event, or holds a frame (``analyzed_here``
        / ``detected_here`` / ``footage_held_here`` are False).
        """
        self._guard(actor, "write", "ext_video_event_create")
        if event_kind not in VIDEO_EVENT_KINDS:
            raise ValidationError(
                "unknown video event kind: %r" % (event_kind,))
        if severity_label not in VIDEO_SEVERITY_LABELS:
            raise ValidationError(
                "unknown video severity label: %r" % (severity_label,))
        with self._lock:
            self._get(self._camera_bindings, binding_id,
                      "camera binding")
            record = {
                "id": self._next_id("vse-"),
                "binding_id": binding_id,
                "event_kind": event_kind,
                "severity_label": severity_label,
                "analyzed_here": False,
                "detected_here": False,
                "footage_held_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._video_events[record["id"]] = record
        self._audit(actor, "ext_video_event_create", record["id"],
                    {"binding_id": binding_id})
        return copy.deepcopy(record)

    def camera_binding_view(self, actor, binding_id):
        """A camera binding plus its reported-event count,
        derived at read. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            binding = self._get(self._camera_bindings, binding_id,
                                "camera binding")
            view = copy.deepcopy(binding)
            view["event_count"] = len(
                [e for e in self._video_events.values()
                 if e["binding_id"] == binding_id])
            return view

    # -- IoT device telemetry ingestion & monitoring (entry: IoT
    #    device telemetry ingestion & equipment/environmental
    #    monitoring engines — labeled reference implementation) --------

    def create_iot_device(self, actor, device_kind, device_ref,
                          subject_label):
        """Record an IoT device. Action: write.

        Reference implementation only: the record names a
        device by kind, opaque reference, and the subject it
        is reported to monitor. Nothing here connects to,
        provisions, or receives data from a device
        (``connected_here`` / ``ingested_here`` are False).
        """
        self._guard(actor, "write", "ext_iot_device_create")
        if device_kind not in IOT_DEVICE_KINDS:
            raise ValidationError(
                "unknown IoT device kind: %r" % (device_kind,))
        _non_empty(device_ref, "device_ref")
        _non_empty(subject_label, "subject_label")
        with self._lock:
            record = {
                "id": self._next_id("iot-"),
                "device_kind": device_kind,
                "device_ref": device_ref,
                "subject_label": subject_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "connected_here": False,
                "ingested_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._iot_devices[record["id"]] = record
        self._audit(actor, "ext_iot_device_create", record["id"],
                    {"device_kind": device_kind})
        return copy.deepcopy(record)

    def record_iot_observation(self, actor, device_id, metric_label,
                               reported_value_label):
        """Record a device observation exactly as reported.
        Action: write.

        The metric and its value are stored verbatim as labels,
        as reported by the device platform that actually sensed
        them. Nothing here senses, measures, or ingests a
        telemetry stream (``sensed_here`` / ``ingested_here``
        are False). Each observation is a standalone record —
        there is no stream, series, or history structure.
        """
        self._guard(actor, "write", "ext_iot_observation_create")
        _non_empty(metric_label, "metric_label")
        _non_empty(reported_value_label, "reported_value_label")
        with self._lock:
            self._get(self._iot_devices, device_id, "IoT device")
            record = {
                "id": self._next_id("obs-"),
                "device_id": device_id,
                "metric_label": metric_label,
                "reported_value_label": reported_value_label,
                "sensed_here": False,
                "ingested_here": False,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._iot_observations[record["id"]] = record
        self._audit(actor, "ext_iot_observation_create", record["id"],
                    {"device_id": device_id})
        return copy.deepcopy(record)

    def iot_device_view(self, actor, device_id):
        """A device record plus its observation count, derived
        at read. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            device = self._get(self._iot_devices, device_id,
                               "IoT device")
            view = copy.deepcopy(device)
            view["observation_count"] = len(
                [o for o in self._iot_observations.values()
                 if o["device_id"] == device_id])
            return view

    # -- alerting & notification (entry: Alerting & notification
    #    engines — records form) -----------------------------------------

    def create_alert_rule(self, actor, label, condition_label):
        """Record an alert rule as data. Action: write.

        ``condition_label`` names, in the reporter's own words,
        the condition the rule is about. The rule is a
        definition held as data: it is never evaluated against
        any record or stream here (``evaluated_here`` False).
        """
        self._guard(actor, "write", "ext_alert_rule_create")
        _non_empty(label, "alert rule label")
        _non_empty(condition_label, "condition_label")
        with self._lock:
            record = {
                "id": self._next_id("alr-"),
                "label": label,
                "condition_label": condition_label,
                "evaluated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._alert_rules[record["id"]] = record
        self._audit(actor, "ext_alert_rule_create", record["id"],
                    {"label": label})
        return copy.deepcopy(record)

    def record_alert(self, actor, rule_id, subject_ref, severity_label):
        """Record an alert raised by a reporter against a rule.
        Action: write.

        The alert is recorded because a reporter — a person or
        an external system — reported that the rule's condition
        occurred for the named subject. Nothing here detects a
        condition (``detected_here`` False); the severity label
        is stored verbatim as reported.
        """
        self._guard(actor, "write", "ext_alert_create")
        _non_empty(subject_ref, "subject_ref")
        if severity_label not in ALERT_SEVERITY_LABELS:
            raise ValidationError(
                "unknown alert severity label: %r" % (severity_label,))
        with self._lock:
            self._get(self._alert_rules, rule_id, "alert rule")
            record = {
                "id": self._next_id("alt-"),
                "rule_id": rule_id,
                "subject_ref": subject_ref,
                "severity_label": severity_label,
                "detected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._alerts[record["id"]] = record
        self._audit(actor, "ext_alert_create", record["id"],
                    {"rule_id": rule_id})
        return copy.deepcopy(record)

    def record_notification(self, actor, alert_id, channel_kind,
                            recipient_ref, outcome_label):
        """Record a notification delivery attempt against an
        alert. Action: write.

        The delivery-attempt form: ``channel_kind`` and
        ``recipient_ref`` (opaque) name where the notification
        was sent by whoever sent it, and ``outcome_label`` is
        the reported delivery outcome, stored verbatim. This
        surface transmits nothing (``reference_transport``
        True, ``delivered_here`` False) — no message field
        exists in this shape, so no message content can be
        held.
        """
        self._guard(actor, "write", "ext_notification_create")
        if channel_kind not in NOTIFICATION_CHANNEL_KINDS:
            raise ValidationError(
                "unknown notification channel kind: %r" % (channel_kind,))
        _non_empty(recipient_ref, "recipient_ref")
        if outcome_label not in NOTIFICATION_OUTCOME_LABELS:
            raise ValidationError(
                "unknown notification outcome label: %r"
                % (outcome_label,))
        with self._lock:
            self._get(self._alerts, alert_id, "alert")
            record = {
                "id": self._next_id("ntf-"),
                "alert_id": alert_id,
                "channel_kind": channel_kind,
                "recipient_ref": recipient_ref,
                "outcome_label": outcome_label,
                "reference_transport": True,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._notifications[record["id"]] = record
        self._audit(actor, "ext_notification_create", record["id"],
                    {"alert_id": alert_id})
        return copy.deepcopy(record)

    def alerts_view(self, actor):
        """Derived view over the alerting records. Action: read.

        Counts of rules, alerts by recorded severity label, and
        notifications by reported outcome label, derived at
        read — counts only, stored nowhere.
        """
        self._maybe_require(actor, "read")
        with self._lock:
            by_severity = {}
            for alert in self._alerts.values():
                label = alert["severity_label"]
                by_severity[label] = by_severity.get(label, 0) + 1
            by_outcome = {}
            for note in self._notifications.values():
                label = note["outcome_label"]
                by_outcome[label] = by_outcome.get(label, 0) + 1
            return {
                "rule_count": len(self._alert_rules),
                "alert_count": len(self._alerts),
                "alerts_by_severity": by_severity,
                "notification_count": len(self._notifications),
                "notifications_by_outcome": by_outcome,
                "detected_here": False,
                "delivered_here": False,
            }

    # -- driver workflow & compliance applications (entry: Driver
    #    workflow & compliance applications — labeled reference
    #    implementation) --------------------------------------------------

    def create_workflow_task(self, actor, operator_id, task_label,
                             status_label):
        """Record a driver-workflow task against a core operator
        record. Action: write.

        Reference implementation only: the task and its
        reported status label are held verbatim, as reported by
        the driver-workflow application that actually runs the
        workflow. Nothing here assigns, routes, or executes a
        workflow step (``executed_here`` False).
        """
        self._guard(actor, "write", "ext_workflow_task_create")
        _non_empty(task_label, "task_label")
        if status_label not in WORKFLOW_STATUS_LABELS:
            raise ValidationError(
                "unknown workflow status label: %r" % (status_label,))
        self.store.get_operator(operator_id, actor)
        with self._lock:
            record = {
                "id": self._next_id("dwf-"),
                "operator_id": operator_id,
                "task_label": task_label,
                "status_label": status_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_tasks[record["id"]] = record
        self._audit(actor, "ext_workflow_task_create", record["id"],
                    {"operator_id": operator_id})
        return copy.deepcopy(record)

    def record_compliance_application(self, actor, application_label,
                                      compliance_label):
        """Record a compliance-application outcome exactly as
        reported. Action: write.

        ``application_label`` names the compliance application
        area (the descriptions' "regulatory compliance"
        substance); ``compliance_label`` is the outcome that
        application reported, stored verbatim. No compliance
        status is evaluated or determined here
        (``evaluated_here`` False), and no control claim is
        made by this record — an application area is not a
        control family.
        """
        self._guard(actor, "write", "ext_compliance_record_create")
        _non_empty(application_label, "application_label")
        if compliance_label not in COMPLIANCE_LABELS:
            raise ValidationError(
                "unknown compliance label: %r" % (compliance_label,))
        with self._lock:
            record = {
                "id": self._next_id("cmp-"),
                "application_label": application_label,
                "compliance_label": compliance_label,
                "reference_stub": True,
                "state": _REFERENCE_STATE,
                "evaluated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._compliance_records[record["id"]] = record
        self._audit(actor, "ext_compliance_record_create", record["id"],
                    {"application_label": application_label})
        return copy.deepcopy(record)

    def workflow_view(self, actor, operator_id):
        """Derived view of one operator's workflow records.
        Action: read. Task count and counts by reported status
        label, derived at read."""
        self._maybe_require(actor, "read")
        self.store.get_operator(operator_id, actor)
        with self._lock:
            tasks = [t for t in self._workflow_tasks.values()
                     if t["operator_id"] == operator_id]
            by_status = {}
            for task in tasks:
                label = task["status_label"]
                by_status[label] = by_status.get(label, 0) + 1
            return {
                "operator_id": operator_id,
                "task_count": len(tasks),
                "tasks_by_status": by_status,
                "executed_here": False,
            }

    # -- dashboarding beyond registry reporting (entry:
    #    Dashboarding front-ends beyond registry reporting) --------------

    def create_dashboard(self, actor, label, panel_kinds):
        """Record a dashboard definition as data. Action: write.

        ``panel_kinds`` is a list of panel kinds from the fixed
        set :data:`DASHBOARD_PANEL_KINDS`; the definition is
        held as data and no front-end is rendered from it here
        (``rendered_here`` False). Each named panel's figure is
        derived at read by :meth:`dashboard_view` over the
        substrate's own core records.
        """
        self._guard(actor, "write", "ext_dashboard_create")
        _non_empty(label, "dashboard label")
        if isinstance(panel_kinds, str) or not isinstance(
                panel_kinds, (list, tuple)) or not panel_kinds:
            raise ValidationError(
                "panel_kinds must be a non-empty list of panel kinds")
        panels = []
        for kind in panel_kinds:
            if kind not in DASHBOARD_PANEL_KINDS:
                raise ValidationError(
                    "unknown dashboard panel kind: %r" % (kind,))
            panels.append(kind)
        with self._lock:
            record = {
                "id": self._next_id("dsh-"),
                "label": label,
                "panel_kinds": panels,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._dashboards[record["id"]] = record
        self._audit(actor, "ext_dashboard_create", record["id"],
                    {"label": label})
        return copy.deepcopy(record)

    def dashboard_view(self, actor, dashboard_id):
        """A dashboard definition plus its panel figures, derived
        at read. Action: read.

        Deterministic derivations over the substrate's own core
        records only, for exactly the panels the definition
        names: record counts per core record set; aggregate
        recorded charging energy in integer watt-hours; the
        maintenance completed share (via the seam
        :func:`_maintenance_completed_share`) rendered as an
        exact int/``"num/den"`` fraction or ``None`` when no
        maintenance records exist; and the fleet's latest
        recorded odometer (the maximum recorded reading, or
        ``None``). Figures derive at read and are stored
        nowhere, so a dashboard recorded earlier reports the
        registry as it stands when read. No front-end is
        rendered (``rendered_here`` False) and no score,
        rating, ranking, or index is computed.
        """
        self._maybe_require(actor, "read")
        with self._lock:
            dashboard = self._get(self._dashboards, dashboard_id,
                                  "dashboard")
            view = copy.deepcopy(dashboard)
            panels = {}
            wanted = dashboard["panel_kinds"]
            if "record_counts" in wanted:
                summary = self.store.summary_report(actor)
                panels["record_counts"] = dict(summary["counts"])
            if "charging_energy" in wanted:
                summary = self.store.summary_report(actor)
                panels["charging_energy"] = {
                    "total_watt_hours": summary["total_watt_hours"],
                }
            if "maintenance_completed_share" in wanted:
                maintenance = self.store.list_maintenance(actor=actor)
                share = _maintenance_completed_share(maintenance)
                panels["maintenance_completed_share"] = (
                    None if share is None else _fraction_out(share))
            if "latest_odometer" in wanted:
                usage = self.store.list_usage(actor=actor)
                readings = [u["odometer_reading"] for u in usage]
                panels["latest_odometer"] = (
                    max(readings) if readings else None)
            view["panels"] = panels
            return view
