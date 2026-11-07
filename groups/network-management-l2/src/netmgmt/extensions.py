"""Final GAPS batch extensions — Singleton 51 (Network Management L2).

Records-form implementations and labeled reference implementations
for the eleven open Extended families of this singleton's union
spec, built over the founding substrate in :mod:`netmgmt.store`.
This module is the only code the batch adds; every core module is
unchanged.

The founding discipline binds throughout: this build manages no
live network, pushes no configuration, provisions no device, and
collects no telemetry. Every surface below is records over the
core's organization / network / device / change / automation /
alert records, and nothing here reaches a device or a network.

Honesty labels, per family:

- **Network optimization** closes as *recorded recommendation
  records* (``computed_here: False``, ``applied_here: False``).
  The fork's "optimize" is a real verb in its description, but no
  optimizer runs in a records substrate: a recommendation is a
  record of advice produced elsewhere, held with its stated basis
  (telemetry review, manual review, external analysis). Counts are
  derived at read; no record holds an optimization value, and the
  summary key is a count of records, exactly as the core's counts
  discipline requires.
- **Network intelligence / AI** closes as model-profile records
  carrying ``reference_stub: True`` and ``inference_here: False``,
  plus reported-output records (observations) whose labels are
  recorded verbatim (``computed_here: False``). Profile lookup is
  a deterministic exact-match search over the recorded profiles.
  No model is trained, run, or inferred from here.
- **Configuration push / control plane** closes as change-linked
  push records with recorded outcome states. A push record's
  current state is *derived at read* from its recorded outcomes
  by the single seam :meth:`_derive_push_state` — the latest
  outcome wins, and with no outcome the state is ``recorded``.
  ``applied_here: False`` on every record: recording a push and
  its outcomes modifies no core device, network, or change
  record, pinned by test.
- **Firmware management** closes as firmware records (a version
  label per device class) and assignment records binding a
  firmware record to a core device, with reported install states
  recorded verbatim and the current state derived at read
  (``deployed_here: False`` — nothing is deployed).
- **Traffic control & SD-WAN policy** closes as policy
  *definition* records: the rules are held as data, deep-copied
  at the boundary, and are never evaluated against traffic and
  never enforced (``evaluated_here: False``,
  ``enforced_here: False``). Reported policy states are recorded
  verbatim; the current state is derived at read.
- **Automation execution** closes as run *reference* records
  against core automation definitions: a reported status held
  verbatim, ``reference_stub: True``, ``executed_here: False``.
  Recording a run changes no core record — the
  registry-never-executes doctrine stands.
- **Cloud management web application** closes as page
  *configuration* records (page reference, title, widget
  definitions held as data). Nothing is rendered and nothing is
  served (``rendered_here: False``, ``served_here: False``);
  widget counts and kinds are derived at read.
- **Device provisioning & deployment** (stub) ships as labeled
  reference records (``reference_stub: True``,
  ``provisioned_here: False``) keyed by an opaque caller-chosen
  device reference for a device not yet in the inventory, with
  reported states recorded verbatim. Creating one creates no
  core device record, pinned by test.
- **Telemetry collection & polling** (stub) ships as labeled
  reference records (``reference_stub: True``,
  ``reference_transport: True``, ``collected_here: False``):
  a collection reference names a core device and metric, and a
  receipt holds a record count and window label *as reported*.
  A receipt creates no core telemetry record, pinned by test.
- **Alert evaluation & delivery transport** (stub) ships as
  labeled reference records: evaluation records hold a verdict
  label verbatim (``evaluated_here: False`` — the verdict was
  reached elsewhere), and delivery receipts hold a channel and a
  reported state (``reference_transport: True``,
  ``delivered_here: False``). Recording either changes no core
  alert record, pinned by test.
- **Integration connectors** (stub) ship as labeled reference
  records (``reference_stub: True``,
  ``reference_transport: True``, ``connected_here: False``)
  naming an external system by opaque reference. Nothing
  connects.

Access control reuses the founding enforcement point-for-point:
every operation goes through the core store's scoped check (role
permission + organization membership), with the founding action
vocabulary — ``enter`` for creates and registrations, ``record``
for outcome / state / receipt records, ``read`` for reads. Denied
attempts on extension writes are recorded in the core audit log
as ``<action>:denied``, mirroring the service layer's convention.
Extension mutations are audited in the same log under
``ext_*`` action names.

Ids are sequential per object type with fixed prefixes (``opt-``,
``mdl-``, ``obs-``, ``cfg-``, ``out-``, ``fw-``, ``fwa-``,
``fws-``, ``pol-``, ``pst-``, ``run-``, ``pgc-``, ``prv-``,
``pvs-``, ``tcl-``, ``rcp-``, ``evl-``, ``dlv-``, ``con-``). A
failed operation consumes no id and changes nothing: all
validation happens before any mutation. All timestamps are UTC
ISO-8601. Records returned are copies; mutating a returned
record changes nothing stored.
"""

import copy
import threading
from datetime import datetime, timezone

from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import DEVICE_CLASSES

OPTIMIZATION_BASES = ("telemetry_review", "manual_review", "external_analysis")
MODEL_KINDS = ("anomaly_detection", "insight_generation", "classification", "other")
PUSH_REPORTED_STATES = ("reported_applied", "reported_failed", "reported_partial")
ASSIGNMENT_REPORTED_STATES = (
    "reported_installed", "reported_failed", "reported_pending")
POLICY_ACTIONS = ("allow", "deny", "shape", "prioritize")
POLICY_REPORTED_STATES = (
    "reported_active", "reported_inactive", "reported_degraded")
RUN_REPORTED_STATUSES = (
    "reported_completed", "reported_failed", "reported_cancelled")
WIDGET_KINDS = (
    "device_list", "telemetry_chart", "alert_feed", "change_list",
    "summary_counts", "other")
PROVISIONING_REPORTED_STATES = (
    "reported_provisioned", "reported_failed", "reported_pending")
DELIVERY_CHANNELS = ("email", "sms", "push", "webhook", "other")
DELIVERY_REPORTED_STATES = (
    "reported_delivered", "reported_failed", "reported_queued")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_ref(value, field):
    """An optional opaque reference: None, or a non-empty string."""
    if value is None:
        return None
    return _text(value, field)


def _count(value, field):
    """A non-negative integer count; bools/floats/strings rejected."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % field)
    return value


class NetmgmtExtensions:
    """The final-batch extension surface over a NetmgmtStore."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._counters = {}
        self._recommendations = {}
        self._model_profiles = {}
        self._model_observations = {}
        self._pushes = {}
        self._push_outcomes = {}
        self._firmware = {}
        self._assignments = {}
        self._assignment_states = {}
        self._policies = {}
        self._policy_states = {}
        self._runs = {}
        self._pages = {}
        self._provisioning = {}
        self._provisioning_states = {}
        self._collections = {}
        self._receipts = {}
        self._evaluations = {}
        self._deliveries = {}
        self._connectors = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor, action, target, details)

    def _guard(self, actor, org_id, action, audit_action):
        """The core's scoped check (role + membership), with denied
        extension writes audited as ``<action>:denied``."""
        try:
            return self.store._scoped(actor, org_id, action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", org_id, {})
            raise

    def _get(self, collection, obj_id, what):
        record = collection.get(obj_id)
        if record is None:
            raise NotFoundError("no such %s: %r" % (what, obj_id))
        return record

    # -- network optimization: recorded recommendations ---------------------

    def create_recommendation(self, actor, org_id, network_id, title, basis,
                              detail_ref=None):
        """Record an optimization recommendation for a network.

        The recommendation is advice produced elsewhere, recorded
        with its stated basis. Nothing is computed and nothing is
        applied here.
        """
        self._guard(actor, org_id, "enter", "ext_recommendation_create")
        network = self.store.get_network(actor, network_id)
        if network["org_id"] != org_id:
            raise ValidationError("network belongs to another organization")
        _text(title, "title")
        if basis not in OPTIMIZATION_BASES:
            raise ValidationError(
                "basis must be one of %r" % (OPTIMIZATION_BASES,))
        _optional_ref(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("opt-"),
                "org_id": org_id,
                "network_id": network_id,
                "title": title,
                "basis": basis,
                "detail_ref": detail_ref,
                "computed_here": False,
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._recommendations[record["id"]] = record
        self._audit(actor, "ext_recommendation_create", record["id"],
                    {"network_id": network_id, "basis": basis})
        return dict(record)

    def list_recommendations(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_recommendation_read")
        return [dict(r) for r in self._recommendations.values()
                if r["org_id"] == org_id]

    # -- network intelligence: model profiles + reported outputs ------------

    def create_model_profile(self, actor, org_id, network_id, name, model_kind):
        """Register a network-intelligence model profile.

        A profile is a reference record for a model that lives
        elsewhere: nothing is trained or run here.
        """
        self._guard(actor, org_id, "enter", "ext_model_profile_create")
        network = self.store.get_network(actor, network_id)
        if network["org_id"] != org_id:
            raise ValidationError("network belongs to another organization")
        _text(name, "name")
        if model_kind not in MODEL_KINDS:
            raise ValidationError(
                "model_kind must be one of %r" % (MODEL_KINDS,))
        with self._lock:
            record = {
                "id": self._mint("mdl-"),
                "org_id": org_id,
                "network_id": network_id,
                "name": name,
                "model_kind": model_kind,
                "reference_stub": True,
                "inference_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._model_profiles[record["id"]] = record
        self._audit(actor, "ext_model_profile_create", record["id"],
                    {"network_id": network_id, "model_kind": model_kind})
        return dict(record)

    def record_model_observation(self, actor, org_id, profile_id, label,
                                 detail_ref=None):
        """Record one output of a profiled model, verbatim as reported."""
        self._guard(actor, org_id, "record", "ext_model_observation_create")
        profile = self._get(self._model_profiles, profile_id, "model profile")
        if profile["org_id"] != org_id:
            raise ValidationError("model profile belongs to another organization")
        _text(label, "label")
        _optional_ref(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("obs-"),
                "org_id": org_id,
                "profile_id": profile_id,
                "label": label,
                "detail_ref": detail_ref,
                "reference_stub": True,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._model_observations[record["id"]] = record
        self._audit(actor, "ext_model_observation_create", record["id"],
                    {"profile_id": profile_id})
        return dict(record)

    def _profile_view(self, profile):
        view = dict(profile)
        view["observation_count"] = sum(
            1 for o in self._model_observations.values()
            if o["profile_id"] == profile["id"])
        return view

    def get_model_profile(self, actor, profile_id):
        profile = self._get(self._model_profiles, profile_id, "model profile")
        self._guard(actor, profile["org_id"], "read", "ext_model_profile_read")
        return self._profile_view(profile)

    def find_model_profiles(self, actor, org_id, network_id=None,
                            model_kind=None):
        """Deterministic record lookup: exact-match filters over the
        recorded profiles, in registration order."""
        self._guard(actor, org_id, "read", "ext_model_profile_read")
        if model_kind is not None and model_kind not in MODEL_KINDS:
            raise ValidationError(
                "model_kind must be one of %r" % (MODEL_KINDS,))
        result = []
        for profile in self._model_profiles.values():
            if profile["org_id"] != org_id:
                continue
            if network_id is not None and profile["network_id"] != network_id:
                continue
            if model_kind is not None and profile["model_kind"] != model_kind:
                continue
            result.append(self._profile_view(profile))
        return result

    def list_model_observations(self, actor, org_id, profile_id=None):
        self._guard(actor, org_id, "read", "ext_model_observation_read")
        return [dict(o) for o in self._model_observations.values()
                if o["org_id"] == org_id
                and (profile_id is None or o["profile_id"] == profile_id)]

    # -- configuration push: change-linked records, nothing applied ---------

    def create_config_push(self, actor, org_id, change_id):
        """Record a configuration push against a core change record.

        The push is a record of intent against the change; applying
        it is the control plane's work, not this build's. Recording
        one modifies no core record.
        """
        self._guard(actor, org_id, "enter", "ext_config_push_create")
        change = self.store.get_change(actor, change_id)
        if change["org_id"] != org_id:
            raise ValidationError("change belongs to another organization")
        with self._lock:
            record = {
                "id": self._mint("cfg-"),
                "org_id": org_id,
                "change_id": change_id,
                "network_id": change["network_id"],
                "device_id": change["device_id"],
                "applied_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._pushes[record["id"]] = record
        self._audit(actor, "ext_config_push_create", record["id"],
                    {"change_id": change_id})
        return self._push_view(record)

    def record_push_outcome(self, actor, push_id, reported_state, note=""):
        """Record the reported outcome of a push, verbatim.

        The state is what an external control plane reported; this
        build applied nothing and verifies nothing.
        """
        push = self._get(self._pushes, push_id, "config push")
        self._guard(actor, push["org_id"], "record", "ext_push_outcome_create")
        if reported_state not in PUSH_REPORTED_STATES:
            raise ValidationError(
                "reported_state must be one of %r" % (PUSH_REPORTED_STATES,))
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            record = {
                "id": self._mint("out-"),
                "org_id": push["org_id"],
                "push_id": push_id,
                "reported_state": reported_state,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._push_outcomes[record["id"]] = record
        self._audit(actor, "ext_push_outcome_create", record["id"],
                    {"push_id": push_id, "reported_state": reported_state})
        return dict(record)

    def _push_outcomes_for(self, push_id):
        return [o for o in self._push_outcomes.values()
                if o["push_id"] == push_id]

    def _derive_push_state(self, outcomes):
        """A push's current state, derived at read: the
        ``reported_state`` of the LATEST recorded outcome, or
        ``recorded`` when no outcome exists. Never stored on the
        push record. This seam is the batch's fresh negative
        control target (see tests/README.md)."""
        if not outcomes:
            return "recorded"
        return outcomes[-1]["reported_state"]

    def _push_view(self, push):
        view = dict(push)
        outcomes = self._push_outcomes_for(push["id"])
        view["current_state"] = self._derive_push_state(outcomes)
        view["outcome_count"] = len(outcomes)
        return view

    def get_config_push(self, actor, push_id):
        push = self._get(self._pushes, push_id, "config push")
        self._guard(actor, push["org_id"], "read", "ext_config_push_read")
        return self._push_view(push)

    def list_config_pushes(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_config_push_read")
        return [self._push_view(p) for p in self._pushes.values()
                if p["org_id"] == org_id]

    # -- firmware management: records + assignments, nothing deployed -------

    def create_firmware(self, actor, org_id, device_class, version_label,
                        detail_ref=None):
        """Register a firmware record: a version label for a device class."""
        self._guard(actor, org_id, "enter", "ext_firmware_create")
        if device_class not in DEVICE_CLASSES:
            raise ValidationError(
                "device_class must be one of %r" % (DEVICE_CLASSES,))
        _text(version_label, "version_label")
        _optional_ref(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("fw-"),
                "org_id": org_id,
                "device_class": device_class,
                "version_label": version_label,
                "detail_ref": detail_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._firmware[record["id"]] = record
        self._audit(actor, "ext_firmware_create", record["id"],
                    {"device_class": device_class,
                     "version_label": version_label})
        return dict(record)

    def assign_firmware(self, actor, org_id, firmware_id, device_id):
        """Record that a firmware record is assigned to a core device.

        The device's class must match the firmware record's class.
        Assignment is a record; nothing is deployed to the device.
        """
        self._guard(actor, org_id, "enter", "ext_firmware_assign")
        firmware = self._get(self._firmware, firmware_id, "firmware record")
        if firmware["org_id"] != org_id:
            raise ValidationError("firmware record belongs to another organization")
        device = self.store.get_device(actor, device_id)
        if device["org_id"] != org_id:
            raise ValidationError("device belongs to another organization")
        if device["device_class"] != firmware["device_class"]:
            raise ValidationError(
                "device class %r does not match firmware class %r"
                % (device["device_class"], firmware["device_class"]))
        with self._lock:
            record = {
                "id": self._mint("fwa-"),
                "org_id": org_id,
                "firmware_id": firmware_id,
                "device_id": device_id,
                "deployed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assignments[record["id"]] = record
        self._audit(actor, "ext_firmware_assign", record["id"],
                    {"firmware_id": firmware_id, "device_id": device_id})
        return self._assignment_view(record)

    def record_assignment_state(self, actor, assignment_id, reported_state):
        """Record a reported install state for an assignment, verbatim."""
        assignment = self._get(self._assignments, assignment_id,
                               "firmware assignment")
        self._guard(actor, assignment["org_id"], "record",
                    "ext_assignment_state_create")
        if reported_state not in ASSIGNMENT_REPORTED_STATES:
            raise ValidationError(
                "reported_state must be one of %r"
                % (ASSIGNMENT_REPORTED_STATES,))
        with self._lock:
            record = {
                "id": self._mint("fws-"),
                "org_id": assignment["org_id"],
                "assignment_id": assignment_id,
                "reported_state": reported_state,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assignment_states[record["id"]] = record
        self._audit(actor, "ext_assignment_state_create", record["id"],
                    {"assignment_id": assignment_id,
                     "reported_state": reported_state})
        return dict(record)

    def _assignment_view(self, assignment):
        view = dict(assignment)
        states = [s for s in self._assignment_states.values()
                  if s["assignment_id"] == assignment["id"]]
        view["current_state"] = (
            states[-1]["reported_state"] if states else "recorded")
        view["state_count"] = len(states)
        return view

    def get_assignment(self, actor, assignment_id):
        assignment = self._get(self._assignments, assignment_id,
                               "firmware assignment")
        self._guard(actor, assignment["org_id"], "read", "ext_assignment_read")
        return self._assignment_view(assignment)

    def list_assignments(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_assignment_read")
        return [self._assignment_view(a) for a in self._assignments.values()
                if a["org_id"] == org_id]

    # -- traffic control & SD-WAN policy: definitions as data ---------------

    @staticmethod
    def _validate_rules(rules):
        if not isinstance(rules, list) or not rules:
            raise ValidationError("rules must be a non-empty list of rule records")
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValidationError("each rule must be a record")
            if set(rule.keys()) != {"name", "action", "match_ref"}:
                raise ValidationError(
                    "each rule carries exactly name, action, match_ref")
            _text(rule["name"], "rule name")
            if rule["action"] not in POLICY_ACTIONS:
                raise ValidationError(
                    "rule action must be one of %r" % (POLICY_ACTIONS,))
            _text(rule["match_ref"], "rule match_ref")
        return copy.deepcopy(rules)

    def create_traffic_policy(self, actor, org_id, network_id, name, rules):
        """Register a traffic / SD-WAN policy definition as data.

        The rules are held, never evaluated against traffic and
        never enforced; reported states are recorded separately.
        """
        self._guard(actor, org_id, "enter", "ext_traffic_policy_create")
        network = self.store.get_network(actor, network_id)
        if network["org_id"] != org_id:
            raise ValidationError("network belongs to another organization")
        _text(name, "name")
        rules = self._validate_rules(rules)
        with self._lock:
            record = {
                "id": self._mint("pol-"),
                "org_id": org_id,
                "network_id": network_id,
                "name": name,
                "rules": rules,
                "evaluated_here": False,
                "enforced_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._policies[record["id"]] = record
        self._audit(actor, "ext_traffic_policy_create", record["id"],
                    {"network_id": network_id})
        return self._policy_view(record)

    def record_policy_state(self, actor, org_id, policy_id, reported_state):
        """Record a reported state for a policy definition, verbatim."""
        self._guard(actor, org_id, "record", "ext_policy_state_create")
        policy = self._get(self._policies, policy_id, "traffic policy")
        if policy["org_id"] != org_id:
            raise ValidationError("traffic policy belongs to another organization")
        if reported_state not in POLICY_REPORTED_STATES:
            raise ValidationError(
                "reported_state must be one of %r" % (POLICY_REPORTED_STATES,))
        with self._lock:
            record = {
                "id": self._mint("pst-"),
                "org_id": org_id,
                "policy_id": policy_id,
                "reported_state": reported_state,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._policy_states[record["id"]] = record
        self._audit(actor, "ext_policy_state_create", record["id"],
                    {"policy_id": policy_id, "reported_state": reported_state})
        return dict(record)

    def _policy_view(self, policy):
        view = dict(policy)
        view["rules"] = copy.deepcopy(policy["rules"])
        states = [s for s in self._policy_states.values()
                  if s["policy_id"] == policy["id"]]
        view["current_state"] = (
            states[-1]["reported_state"] if states else "unreported")
        view["state_count"] = len(states)
        return view

    def get_traffic_policy(self, actor, policy_id):
        policy = self._get(self._policies, policy_id, "traffic policy")
        self._guard(actor, policy["org_id"], "read", "ext_traffic_policy_read")
        return self._policy_view(policy)

    def list_traffic_policies(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_traffic_policy_read")
        return [self._policy_view(p) for p in self._policies.values()
                if p["org_id"] == org_id]

    # -- automation execution: run references, never execution ---------------

    def record_automation_run(self, actor, org_id, automation_id,
                              reported_status, detail_ref=None):
        """Record a reported run of a core automation definition.

        A run reference only: the definition is data in the core
        registry, and recording a run executes nothing and changes
        no core record.
        """
        self._guard(actor, org_id, "record", "ext_automation_run_create")
        automation = self.store.get_automation(actor, automation_id)
        if automation["org_id"] != org_id:
            raise ValidationError("automation belongs to another organization")
        if reported_status not in RUN_REPORTED_STATUSES:
            raise ValidationError(
                "reported_status must be one of %r" % (RUN_REPORTED_STATUSES,))
        _optional_ref(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("run-"),
                "org_id": org_id,
                "automation_id": automation_id,
                "reported_status": reported_status,
                "detail_ref": detail_ref,
                "reference_stub": True,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._runs[record["id"]] = record
        self._audit(actor, "ext_automation_run_create", record["id"],
                    {"automation_id": automation_id,
                     "reported_status": reported_status})
        return dict(record)

    def list_automation_runs(self, actor, org_id, automation_id=None):
        self._guard(actor, org_id, "read", "ext_automation_run_read")
        return [dict(r) for r in self._runs.values()
                if r["org_id"] == org_id
                and (automation_id is None or r["automation_id"] == automation_id)]

    # -- cloud management web application: page configurations ---------------

    @staticmethod
    def _validate_widgets(widgets):
        if not isinstance(widgets, list):
            raise ValidationError("widgets must be a list of widget records")
        for widget in widgets:
            if not isinstance(widget, dict):
                raise ValidationError("each widget must be a record")
            if set(widget.keys()) != {"kind", "title"}:
                raise ValidationError("each widget carries exactly kind, title")
            if widget["kind"] not in WIDGET_KINDS:
                raise ValidationError(
                    "widget kind must be one of %r" % (WIDGET_KINDS,))
            _text(widget["title"], "widget title")
        return copy.deepcopy(widgets)

    def create_page_config(self, actor, org_id, page_ref, title, widgets):
        """Register a management-page configuration as data.

        ``page_ref`` is unique within the organization. The page
        is a configuration record; nothing is rendered or served.
        """
        self._guard(actor, org_id, "enter", "ext_page_config_create")
        _text(page_ref, "page_ref")
        _text(title, "title")
        widgets = self._validate_widgets(widgets)
        with self._lock:
            for existing in self._pages.values():
                if existing["org_id"] == org_id and existing["page_ref"] == page_ref:
                    raise ValidationError(
                        "page_ref already exists in this organization: %r"
                        % (page_ref,))
            record = {
                "id": self._mint("pgc-"),
                "org_id": org_id,
                "page_ref": page_ref,
                "title": title,
                "widgets": widgets,
                "rendered_here": False,
                "served_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._pages[record["id"]] = record
        self._audit(actor, "ext_page_config_create", record["id"],
                    {"page_ref": page_ref})
        return self._page_view(record)

    def _page_view(self, page):
        view = dict(page)
        view["widgets"] = copy.deepcopy(page["widgets"])
        view["widget_count"] = len(page["widgets"])
        view["widget_kinds"] = sorted({w["kind"] for w in page["widgets"]})
        return view

    def get_page_config(self, actor, page_id):
        page = self._get(self._pages, page_id, "page configuration")
        self._guard(actor, page["org_id"], "read", "ext_page_config_read")
        return self._page_view(page)

    def list_page_configs(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_page_config_read")
        return [self._page_view(p) for p in self._pages.values()
                if p["org_id"] == org_id]

    # -- stub: device provisioning & deployment references --------------------

    def create_provisioning_reference(self, actor, org_id, network_id,
                                      device_ref, detail_ref=None):
        """Register a provisioning reference for a device not yet in
        the inventory, keyed by an opaque caller-chosen reference.

        A labeled reference record: nothing is provisioned and no
        core device record is created.
        """
        self._guard(actor, org_id, "enter", "ext_provisioning_create")
        network = self.store.get_network(actor, network_id)
        if network["org_id"] != org_id:
            raise ValidationError("network belongs to another organization")
        _text(device_ref, "device_ref")
        _optional_ref(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("prv-"),
                "org_id": org_id,
                "network_id": network_id,
                "device_ref": device_ref,
                "detail_ref": detail_ref,
                "reference_stub": True,
                "provisioned_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._provisioning[record["id"]] = record
        self._audit(actor, "ext_provisioning_create", record["id"],
                    {"network_id": network_id, "device_ref": device_ref})
        return self._provisioning_view(record)

    def record_provisioning_state(self, actor, org_id, reference_id,
                                  reported_state):
        """Record a reported provisioning state, verbatim."""
        self._guard(actor, org_id, "record", "ext_provisioning_state_create")
        reference = self._get(self._provisioning, reference_id,
                              "provisioning reference")
        if reference["org_id"] != org_id:
            raise ValidationError(
                "provisioning reference belongs to another organization")
        if reported_state not in PROVISIONING_REPORTED_STATES:
            raise ValidationError(
                "reported_state must be one of %r"
                % (PROVISIONING_REPORTED_STATES,))
        with self._lock:
            record = {
                "id": self._mint("pvs-"),
                "org_id": org_id,
                "reference_id": reference_id,
                "reported_state": reported_state,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._provisioning_states[record["id"]] = record
        self._audit(actor, "ext_provisioning_state_create", record["id"],
                    {"reference_id": reference_id,
                     "reported_state": reported_state})
        return dict(record)

    def _provisioning_view(self, reference):
        view = dict(reference)
        states = [s for s in self._provisioning_states.values()
                  if s["reference_id"] == reference["id"]]
        view["current_state"] = (
            states[-1]["reported_state"] if states else "recorded")
        view["state_count"] = len(states)
        return view

    def get_provisioning_reference(self, actor, reference_id):
        reference = self._get(self._provisioning, reference_id,
                              "provisioning reference")
        self._guard(actor, reference["org_id"], "read", "ext_provisioning_read")
        return self._provisioning_view(reference)

    def list_provisioning_references(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_provisioning_read")
        return [self._provisioning_view(r) for r in self._provisioning.values()
                if r["org_id"] == org_id]

    # -- stub: telemetry collection & polling references -----------------------

    def create_collection_reference(self, actor, org_id, device_id, metric,
                                    interval_label):
        """Register a telemetry collection reference for a core device.

        A labeled reference record naming what an external
        collector would poll; this build collects and polls
        nothing — core telemetry stays caller-supplied records.
        """
        self._guard(actor, org_id, "enter", "ext_collection_create")
        device = self.store.get_device(actor, device_id)
        if device["org_id"] != org_id:
            raise ValidationError("device belongs to another organization")
        _text(metric, "metric")
        _text(interval_label, "interval_label")
        with self._lock:
            record = {
                "id": self._mint("tcl-"),
                "org_id": org_id,
                "device_id": device_id,
                "metric": metric,
                "interval_label": interval_label,
                "reference_stub": True,
                "reference_transport": True,
                "collected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collections[record["id"]] = record
        self._audit(actor, "ext_collection_create", record["id"],
                    {"device_id": device_id, "metric": metric})
        return dict(record)

    def record_collection_receipt(self, actor, org_id, reference_id,
                                  records_reported, window_label):
        """Record a collection receipt: a count and window label as
        reported by an external collector. Creates no core
        telemetry record."""
        self._guard(actor, org_id, "record", "ext_collection_receipt_create")
        reference = self._get(self._collections, reference_id,
                              "collection reference")
        if reference["org_id"] != org_id:
            raise ValidationError(
                "collection reference belongs to another organization")
        _count(records_reported, "records_reported")
        _text(window_label, "window_label")
        with self._lock:
            record = {
                "id": self._mint("rcp-"),
                "org_id": org_id,
                "reference_id": reference_id,
                "records_reported": records_reported,
                "window_label": window_label,
                "reference_stub": True,
                "reference_transport": True,
                "collected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._receipts[record["id"]] = record
        self._audit(actor, "ext_collection_receipt_create", record["id"],
                    {"reference_id": reference_id,
                     "records_reported": records_reported})
        return dict(record)

    def list_collection_references(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_collection_read")
        return [dict(r) for r in self._collections.values()
                if r["org_id"] == org_id]

    def list_collection_receipts(self, actor, org_id, reference_id=None):
        self._guard(actor, org_id, "read", "ext_collection_read")
        return [dict(r) for r in self._receipts.values()
                if r["org_id"] == org_id
                and (reference_id is None or r["reference_id"] == reference_id)]

    # -- stub: alert evaluation & delivery --------------------------------------

    def _alert_in_org(self, actor, org_id, alert_id):
        alert = self.store.get_alert(actor, alert_id)
        if alert["org_id"] != org_id:
            raise ValidationError("alert belongs to another organization")
        return alert

    def record_alert_evaluation(self, actor, org_id, alert_id, verdict_label,
                                detail_ref=None):
        """Record an evaluation verdict for a core alert, verbatim.

        The verdict was reached elsewhere; recording it evaluates
        nothing and changes no core alert record.
        """
        self._guard(actor, org_id, "record", "ext_alert_evaluation_create")
        self._alert_in_org(actor, org_id, alert_id)
        _text(verdict_label, "verdict_label")
        _optional_ref(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("evl-"),
                "org_id": org_id,
                "alert_id": alert_id,
                "verdict_label": verdict_label,
                "detail_ref": detail_ref,
                "reference_stub": True,
                "evaluated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._evaluations[record["id"]] = record
        self._audit(actor, "ext_alert_evaluation_create", record["id"],
                    {"alert_id": alert_id})
        return dict(record)

    def record_alert_delivery(self, actor, org_id, alert_id, channel,
                              reported_state):
        """Record a reported delivery of a core alert over a channel.

        A labeled transport receipt: nothing is delivered here.
        """
        self._guard(actor, org_id, "record", "ext_alert_delivery_create")
        self._alert_in_org(actor, org_id, alert_id)
        if channel not in DELIVERY_CHANNELS:
            raise ValidationError(
                "channel must be one of %r" % (DELIVERY_CHANNELS,))
        if reported_state not in DELIVERY_REPORTED_STATES:
            raise ValidationError(
                "reported_state must be one of %r" % (DELIVERY_REPORTED_STATES,))
        with self._lock:
            record = {
                "id": self._mint("dlv-"),
                "org_id": org_id,
                "alert_id": alert_id,
                "channel": channel,
                "reported_state": reported_state,
                "reference_stub": True,
                "reference_transport": True,
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._deliveries[record["id"]] = record
        self._audit(actor, "ext_alert_delivery_create", record["id"],
                    {"alert_id": alert_id, "channel": channel})
        return dict(record)

    def list_alert_evaluations(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_alert_evaluation_read")
        return [dict(r) for r in self._evaluations.values()
                if r["org_id"] == org_id]

    def list_alert_deliveries(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_alert_delivery_read")
        return [dict(r) for r in self._deliveries.values()
                if r["org_id"] == org_id]

    # -- stub: integration connector references -----------------------------------

    def create_connector_reference(self, actor, org_id, name, system_ref,
                                   detail_ref=None):
        """Register an integration connector reference.

        A labeled reference record naming an external system by
        opaque reference; nothing connects to it.
        """
        self._guard(actor, org_id, "enter", "ext_connector_create")
        _text(name, "name")
        _text(system_ref, "system_ref")
        _optional_ref(detail_ref, "detail_ref")
        with self._lock:
            record = {
                "id": self._mint("con-"),
                "org_id": org_id,
                "name": name,
                "system_ref": system_ref,
                "detail_ref": detail_ref,
                "reference_stub": True,
                "reference_transport": True,
                "connected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._connectors[record["id"]] = record
        self._audit(actor, "ext_connector_create", record["id"],
                    {"system_ref": system_ref})
        return dict(record)

    def list_connector_references(self, actor, org_id):
        self._guard(actor, org_id, "read", "ext_connector_read")
        return [dict(r) for r in self._connectors.values()
                if r["org_id"] == org_id]

    # -- extension summary -----------------------------------------------------------

    def extension_summary(self, actor, org_id):
        """Counts over the extension surface for one organization,
        computed on read. Counts only — never scores."""
        self._guard(actor, org_id, "read", "ext_summary_read")

        def count(collection):
            return sum(1 for r in collection.values() if r["org_id"] == org_id)

        return {
            "org_id": org_id,
            "recommendations": count(self._recommendations),
            "model_profiles": count(self._model_profiles),
            "model_observations": count(self._model_observations),
            "config_pushes": count(self._pushes),
            "push_outcomes": count(self._push_outcomes),
            "firmware_records": count(self._firmware),
            "firmware_assignments": count(self._assignments),
            "traffic_policies": count(self._policies),
            "automation_runs": count(self._runs),
            "page_configs": count(self._pages),
            "provisioning_references": count(self._provisioning),
            "collection_references": count(self._collections),
            "collection_receipts": count(self._receipts),
            "alert_evaluations": count(self._evaluations),
            "alert_deliveries": count(self._deliveries),
            "connector_references": count(self._connectors),
        }
