"""Network management store: customer organizations, network
registry, device inventory, configuration change records, automation
definitions, telemetry records, and alert records.

Clean-room implementation of the union spec's implementation
contract. The single fork in this category is a cloud-managed
networking platform; this store implements the records substrate
its description actually claims, and nothing else. It manages no
live network, pushes no configuration, and collects no telemetry.

Two boundaries are enforced on every organization-scoped operation:

1. Membership -- the actor must be a member of the organization,
   or hold the platform ``admin`` role, else
   :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be
   in the actor's role permission set (see :mod:`netmgmt.access`)
   when the actor is a User-like object. A plain string actor
   carries identity (for provenance) but no role, so role
   enforcement for those happens in the service layer.

Role actions: ``enter`` for creates / registrations / cancels,
``decide`` for change decisions, ``record`` for telemetry, change
closes, and alert acknowledgements, ``read`` for reads,
``manage_members`` for membership changes, and ``create_org`` for
organization creation.

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``net-``, ``dev-``, ``tel-``, ``chg-``, ``aut-``, ``alr-``).

Derivation discipline: a device's freshness status
(``derived_status``) and ``last_reading_utc`` are computed at read
from its telemetry records against a stated 24-hour window and
are never stored -- the stored device record carries no such key.
A device's lifecycle ``state`` (``registered`` / ``retired``), by
contrast, is event-driven, so it is stored.

Telemetry discipline: values are integers. Any value that is not
a Python ``int`` (booleans, floats -- even integral floats -- and
strings included) raises :class:`ValidationError`. Records carry
caller-supplied values and caller-supplied timestamps; nothing is
collected, polled, or streamed.

Change discipline: closing an approved change record records the
intent only; it modifies no device and no network record. The push
that would apply a change is Extended, never part of this store.

Scoring discipline: nothing in this store computes a score, a
rating, or any optimization value, and no record shape carries a
field for one. Summaries are counts only.

Privacy discipline: organizations, networks, and devices are
known only by caller-supplied opaque references and labels. The
network and device record shapes are pinned -- neither has a field
that could hold an IP address, a MAC address, a serial number, a
credential, or any other identifier of a live network -- and the
pins are enforced by tests.

The store records every successful mutation to its audit log
(when one is attached). Reads are not audited here; denied
attempts and audit reads are the HTTP layer's responsibility, so
nothing is recorded twice.
"""

import threading
from datetime import datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

DEVICE_CLASSES = ("switching", "wireless", "security_sdwan", "other")
DEVICE_STATES = ("registered", "retired")
DERIVED_STATUSES = ("fresh", "stale", "unknown")
CHANGE_KINDS = ("create", "update", "remove", "policy")
CHANGE_STATUSES = ("requested", "approved", "rejected", "closed", "cancelled")
ALERT_KINDS = ("telemetry_threshold", "device_stale", "general")

FRESHNESS_WINDOW = timedelta(hours=24)


def _utc_now():
    return datetime.now(timezone.utc)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _parse_iso(value, field):
    """Parse an ISO-8601 timestamp (a trailing ``Z`` is accepted).

    Returns an aware UTC-normalized datetime. Naive timestamps are
    treated as UTC.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise ValidationError(
                "%s must be an ISO-8601 timestamp: %r" % (field, value))
    else:
        raise ValidationError(
            "%s must be an ISO-8601 timestamp: %r" % (field, value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _telemetry_value(value):
    """Validate an integer telemetry value; bools/floats/strs rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("value must be an integer")
    return value


class NetmgmtStore:
    """In-memory network-management records store."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._networks = {}
        self._devices = {}
        self._telemetry = {}
        self._changes = {}
        self._automations = {}
        self._alerts = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _check_role(actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _organization(self, org_id):
        org = self._organizations.get(org_id)
        if org is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return org

    def _check_org_access(self, actor, org):
        name = actor_name(actor)
        role = getattr(actor, "role", None)
        if role == "admin" or name in org["members"]:
            return
        raise PermissionDenied(
            "permission denied: user %r is not a member of organization %r"
            % (name, org["id"])
        )

    def _scoped(self, actor, org_id, action):
        """Role check + org lookup + membership check, in that order."""
        self._check_role(actor, action)
        org = self._organization(org_id)
        self._check_org_access(actor, org)
        return org

    # -- customer organizations -------------------------------------------

    def create_organization(self, actor, ref, label):
        """Register a customer organization by opaque reference.

        The creator becomes owner and first member.
        """
        self._check_role(actor, "create_org")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["ref"] == ref:
                    raise ValidationError("organization ref already exists: %r" % (ref,))
            org = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "owner": actor_name(actor),
                "members": [actor_name(actor)],
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[org["id"]] = org
        self._record(actor, "organization_create", org["id"], {"ref": ref})
        return self._org_view(org)

    @staticmethod
    def _org_view(org):
        view = dict(org)
        view["members"] = list(org["members"])
        return view

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        org = self._organization(org_id)
        self._check_org_access(actor, org)
        return self._org_view(org)

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        name = actor_name(actor)
        role = getattr(actor, "role", None)
        return [
            self._org_view(org) for org in self._organizations.values()
            if role == "admin" or name in org["members"]
        ]

    def update_organization(self, actor, org_id, label):
        """Update an organization's profile label."""
        org = self._scoped(actor, org_id, "enter")
        _text(label, "label")
        with self._lock:
            org["label"] = label
        self._record(actor, "organization_update", org_id, {})
        return self._org_view(org)

    def add_member(self, actor, org_id, username):
        """Add a member (by username) to an organization."""
        org = self._scoped(actor, org_id, "manage_members")
        _text(username, "username")
        with self._lock:
            if username not in org["members"]:
                org["members"].append(username)
        self._record(actor, "member_add", org_id, {"username": username})
        return self._org_view(org)

    # -- network registry ---------------------------------------------------

    def create_network(self, actor, org_id, ref, label, site_ref):
        """Register one network in an organization.

        ``ref`` is the caller-supplied opaque network reference; it
        is unique within the organization. The record shape is
        pinned (see the module docstring's privacy discipline).
        """
        self._scoped(actor, org_id, "enter")
        _text(ref, "ref")
        _text(label, "label")
        _text(site_ref, "site_ref")
        with self._lock:
            for existing in self._networks.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "network ref already exists in this organization: %r" % (ref,))
            network = {
                "id": self._mint("net-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "site_ref": site_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._networks[network["id"]] = network
        self._record(actor, "network_create", network["id"], {"ref": ref})
        return dict(network)

    def _network(self, network_id):
        network = self._networks.get(network_id)
        if network is None:
            raise NotFoundError("no such network: %r" % (network_id,))
        return network

    def get_network(self, actor, network_id):
        self._check_role(actor, "read")
        network = self._network(network_id)
        self._check_org_access(actor, self._organizations[network["org_id"]])
        return dict(network)

    def list_networks(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        return [dict(n) for n in self._networks.values() if n["org_id"] == org_id]

    # -- device inventory -----------------------------------------------------

    def create_device(self, actor, org_id, network_id, ref, device_class,
                      model_ref):
        """Register one device to a network in an organization.

        ``ref`` is unique within the organization. The record shape
        is pinned (see the module docstring's privacy discipline);
        the device starts in the ``registered`` state.
        """
        self._scoped(actor, org_id, "enter")
        network = self._network(network_id)
        if network["org_id"] != org_id:
            raise ValidationError("network belongs to another organization")
        _text(ref, "ref")
        if device_class not in DEVICE_CLASSES:
            raise ValidationError(
                "device_class must be one of %r" % (DEVICE_CLASSES,))
        _text(model_ref, "model_ref")
        with self._lock:
            for existing in self._devices.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "device ref already exists in this organization: %r" % (ref,))
            device = {
                "id": self._mint("dev-"),
                "org_id": org_id,
                "network_id": network_id,
                "ref": ref,
                "device_class": device_class,
                "model_ref": model_ref,
                "state": "registered",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._devices[device["id"]] = device
        self._record(actor, "device_create", device["id"], {"ref": ref})
        return self._device_view(device)

    def _device(self, device_id):
        device = self._devices.get(device_id)
        if device is None:
            raise NotFoundError("no such device: %r" % (device_id,))
        return device

    def _latest_telemetry(self, device_id):
        """The device's most recent telemetry record, or None."""
        latest = None
        latest_dt = None
        for record in self._telemetry.values():
            if record["device_id"] != device_id:
                continue
            recorded_dt = _parse_iso(record["recorded_utc"], "recorded_utc")
            if latest is None or recorded_dt >= latest_dt:
                latest = record
                latest_dt = recorded_dt
        return latest

    def _derive_device_status(self, device, as_of_dt):
        """Derive a device's freshness status at ``as_of_dt``.

        ``unknown`` when the device has no telemetry records;
        ``fresh`` when its latest record is within 24 hours of
        ``as_of_dt``; ``stale`` when its latest record is older.
        This is the group's signature derivation (see the negative
        control in tests/test_negative_control.py).
        """
        if as_of_dt is None:
            as_of = _utc_now()
        else:
            as_of = _parse_iso(as_of_dt, "as_of")
        latest = self._latest_telemetry(device["id"])
        if latest is None:
            return "unknown"
        latest_dt = _parse_iso(latest["recorded_utc"], "recorded_utc")
        if abs(as_of - latest_dt) <= FRESHNESS_WINDOW:
            return "fresh"
        return "stale"

    def _device_view(self, device, as_of=None):
        view = dict(device)
        latest = self._latest_telemetry(device["id"])
        view["derived_status"] = self._derive_device_status(device, as_of)
        view["last_reading_utc"] = latest["recorded_utc"] if latest else None
        return view

    def get_device(self, actor, device_id, as_of=None):
        self._check_role(actor, "read")
        device = self._device(device_id)
        self._check_org_access(actor, self._organizations[device["org_id"]])
        if as_of is not None:
            _parse_iso(as_of, "as_of")
        return self._device_view(device, as_of=as_of)

    def list_devices(self, actor, org_id, as_of=None, network_id=None,
                     device_class=None, state=None):
        self._scoped(actor, org_id, "read")
        if as_of is not None:
            _parse_iso(as_of, "as_of")
        result = []
        for device in self._devices.values():
            if device["org_id"] != org_id:
                continue
            if network_id is not None and device["network_id"] != network_id:
                continue
            if device_class is not None and device["device_class"] != device_class:
                continue
            if state is not None and device["state"] != state:
                continue
            result.append(self._device_view(device, as_of=as_of))
        return result

    def retire_device(self, actor, device_id):
        """Retire a registered device. Retiring twice is an error."""
        device = self._device(device_id)
        self._scoped(actor, device["org_id"], "enter")
        if device["state"] == "retired":
            raise ValidationError("device is already retired")
        with self._lock:
            device["state"] = "retired"
        self._record(actor, "device_retire", device_id, {})
        return self._device_view(device)

    # -- telemetry records ------------------------------------------------------

    def record_telemetry(self, actor, org_id, device_id, metric, value,
                         unit, recorded_utc):
        """Record one caller-supplied telemetry reading for a device.

        The device must belong to the organization passed. The
        value must be an integer and ``recorded_utc`` must parse
        as ISO-8601. Nothing is collected or polled: this records
        what the caller supplies, verbatim.
        """
        self._scoped(actor, org_id, "record")
        device = self._device(device_id)
        if device["org_id"] != org_id:
            raise ValidationError("device belongs to another organization")
        _text(metric, "metric")
        _telemetry_value(value)
        _text(unit, "unit")
        _parse_iso(recorded_utc, "recorded_utc")
        if not isinstance(recorded_utc, str):
            raise ValidationError("recorded_utc must be an ISO-8601 string")
        with self._lock:
            record = {
                "id": self._mint("tel-"),
                "org_id": org_id,
                "device_id": device_id,
                "metric": metric,
                "value": value,
                "unit": unit,
                "recorded_utc": recorded_utc,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._telemetry[record["id"]] = record
        self._record(actor, "telemetry_create", record["id"],
                     {"device_id": device_id, "metric": metric})
        return dict(record)

    # The registry-verb alias used by some callers.
    create_telemetry = record_telemetry

    def list_telemetry(self, actor, device_id):
        self._check_role(actor, "read")
        device = self._device(device_id)
        self._check_org_access(actor, self._organizations[device["org_id"]])
        return [dict(r) for r in self._telemetry.values()
                if r["device_id"] == device_id]

    # -- configuration change records --------------------------------------------

    def create_change(self, actor, org_id, network_id, change_kind, summary,
                      device_id=None):
        """Record a configuration change request against a network.

        The change optionally targets a device, which must belong
        to that network. Recording a change never modifies any
        device or network record.
        """
        self._scoped(actor, org_id, "enter")
        network = self._network(network_id)
        if network["org_id"] != org_id:
            raise ValidationError("network belongs to another organization")
        if change_kind not in CHANGE_KINDS:
            raise ValidationError("change_kind must be one of %r" % (CHANGE_KINDS,))
        _text(summary, "summary")
        if device_id is not None:
            device = self._device(device_id)
            if device["org_id"] != org_id:
                raise ValidationError("device belongs to another organization")
            if device["network_id"] != network_id:
                raise ValidationError("device does not belong to that network")
        with self._lock:
            change = {
                "id": self._mint("chg-"),
                "org_id": org_id,
                "network_id": network_id,
                "device_id": device_id,
                "change_kind": change_kind,
                "summary": summary,
                "status": "requested",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._changes[change["id"]] = change
        self._record(actor, "change_create", change["id"],
                     {"change_kind": change_kind})
        return dict(change)

    def _change(self, change_id):
        change = self._changes.get(change_id)
        if change is None:
            raise NotFoundError("no such change: %r" % (change_id,))
        return change

    def get_change(self, actor, change_id):
        self._check_role(actor, "read")
        change = self._change(change_id)
        self._check_org_access(actor, self._organizations[change["org_id"]])
        return dict(change)

    def list_changes(self, actor, org_id, status=None):
        self._scoped(actor, org_id, "read")
        return [
            dict(c) for c in self._changes.values()
            if c["org_id"] == org_id and (status is None or c["status"] == status)
        ]

    def _check_decider_not_requester(self, change, actor):
        """AC-5 seam: the decider of a change is never its requester."""
        if actor_name(actor) == change["created_by"]:
            raise PermissionDenied(
                "the decider of a change is never its requester")

    def decide_change(self, actor, change_id, approve):
        """Approve or reject a requested change.

        Separation of duties: the decider is never the requester.
        """
        change = self._change(change_id)
        self._scoped(actor, change["org_id"], "decide")
        if not isinstance(approve, bool):
            raise ValidationError("approve must be a boolean")
        if change["status"] != "requested":
            raise ValidationError(
                "change is not awaiting decision: %r" % (change["status"],))
        self._check_decider_not_requester(change, actor)
        with self._lock:
            change["status"] = "approved" if approve else "rejected"
            change["decided_by"] = actor_name(actor)
            change["decided_utc"] = _utc_now().isoformat()
        self._record(actor, "change_decide", change_id, {"approve": approve})
        return dict(change)

    def close_change(self, actor, change_id):
        """Close an approved change.

        Closing records the intent only: it modifies no device and
        no network record -- the push that would apply the change
        is Extended.
        """
        change = self._change(change_id)
        self._scoped(actor, change["org_id"], "record")
        if change["status"] != "approved":
            raise ValidationError("only an approved change can be closed")
        with self._lock:
            change["status"] = "closed"
            change["closed_utc"] = _utc_now().isoformat()
        self._record(actor, "change_close", change_id, {})
        return dict(change)

    def cancel_change(self, actor, change_id):
        """Cancel a requested change.

        Only the requester, or a platform admin, may cancel.
        """
        change = self._change(change_id)
        self._scoped(actor, change["org_id"], "enter")
        if change["status"] != "requested":
            raise ValidationError(
                "change cannot be cancelled from %r" % (change["status"],))
        role = getattr(actor, "role", None)
        if actor_name(actor) != change["created_by"] and role != "admin":
            raise PermissionDenied(
                "only the requester or a platform admin may cancel a change")
        with self._lock:
            change["status"] = "cancelled"
        self._record(actor, "change_cancel", change_id, {})
        return dict(change)

    # -- automation definitions (registered, never executed) ----------------------

    def create_automation(self, actor, org_id, name, steps):
        """Register an automation definition as data. Never executed."""
        self._scoped(actor, org_id, "enter")
        _text(name, "name")
        if not isinstance(steps, list) or not steps:
            raise ValidationError("steps must be a non-empty list of step names")
        for step in steps:
            _text(step, "step")
        with self._lock:
            automation = {
                "id": self._mint("aut-"),
                "org_id": org_id,
                "name": name,
                "steps": list(steps),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._automations[automation["id"]] = automation
        self._record(actor, "automation_create", automation["id"], {"name": name})
        view = dict(automation)
        view["steps"] = list(automation["steps"])
        return view

    def get_automation(self, actor, automation_id):
        self._check_role(actor, "read")
        automation = self._automations.get(automation_id)
        if automation is None:
            raise NotFoundError("no such automation: %r" % (automation_id,))
        self._check_org_access(actor, self._organizations[automation["org_id"]])
        view = dict(automation)
        view["steps"] = list(automation["steps"])
        return view

    def list_automations(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        result = []
        for automation in self._automations.values():
            if automation["org_id"] == org_id:
                view = dict(automation)
                view["steps"] = list(automation["steps"])
                result.append(view)
        return result

    # -- alert records ---------------------------------------------------------------

    def create_alert(self, actor, org_id, kind, message, network_id=None,
                     device_id=None):
        """Record an alert. Delivery is Extended; this is the record."""
        self._scoped(actor, org_id, "record")
        if kind not in ALERT_KINDS:
            raise ValidationError("kind must be one of %r" % (ALERT_KINDS,))
        _text(message, "message")
        if network_id is not None:
            network = self._network(network_id)
            if network["org_id"] != org_id:
                raise ValidationError("network belongs to another organization")
        if device_id is not None:
            device = self._device(device_id)
            if device["org_id"] != org_id:
                raise ValidationError("device belongs to another organization")
            if network_id is not None and device["network_id"] != network_id:
                raise ValidationError("device does not belong to that network")
        with self._lock:
            alert = {
                "id": self._mint("alr-"),
                "org_id": org_id,
                "network_id": network_id,
                "device_id": device_id,
                "kind": kind,
                "message": message,
                "acknowledged_by": None,
                "acknowledged_utc": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._alerts[alert["id"]] = alert
        self._record(actor, "alert_create", alert["id"], {"kind": kind})
        return dict(alert)

    def get_alert(self, actor, alert_id):
        self._check_role(actor, "read")
        alert = self._alerts.get(alert_id)
        if alert is None:
            raise NotFoundError("no such alert: %r" % (alert_id,))
        self._check_org_access(actor, self._organizations[alert["org_id"]])
        return dict(alert)

    def list_alerts(self, actor, org_id):
        self._scoped(actor, org_id, "read")
        return [dict(a) for a in self._alerts.values() if a["org_id"] == org_id]

    def acknowledge_alert(self, actor, alert_id):
        """Record acknowledgement of an alert by the calling user."""
        alert = self._alerts.get(alert_id)
        if alert is None:
            raise NotFoundError("no such alert: %r" % (alert_id,))
        self._scoped(actor, alert["org_id"], "record")
        if alert["acknowledged_by"] is not None:
            raise ValidationError("alert is already acknowledged")
        with self._lock:
            alert["acknowledged_by"] = actor_name(actor)
            alert["acknowledged_utc"] = _utc_now().isoformat()
        self._record(actor, "alert_acknowledge", alert_id, {})
        return dict(alert)

    # -- search & summary ---------------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over accessible records."""
        self._check_role(actor, "read")
        needle = (query or "").strip().lower()
        orgs = self.list_organizations(actor)
        org_ids = {org["id"] for org in orgs}
        result = {"networks": [], "devices": [], "changes": [], "alerts": []}
        if not needle:
            return result
        for network in self._networks.values():
            if network["org_id"] in org_ids and (
                    needle in network["ref"].lower()
                    or needle in network["label"].lower()
                    or needle in network["site_ref"].lower()):
                result["networks"].append(dict(network))
        for device in self._devices.values():
            if device["org_id"] in org_ids and (
                    needle in device["ref"].lower()
                    or needle in device["model_ref"].lower()):
                result["devices"].append(self._device_view(device))
        for change in self._changes.values():
            if change["org_id"] in org_ids and needle in change["summary"].lower():
                result["changes"].append(dict(change))
        for alert in self._alerts.values():
            if alert["org_id"] in org_ids and needle in alert["message"].lower():
                result["alerts"].append(dict(alert))
        return result

    def organization_summary(self, actor, org_id):
        """Counts for one organization, computed on read. Counts only."""
        self._scoped(actor, org_id, "read")
        devices = [d for d in self._devices.values() if d["org_id"] == org_id]
        devices_by_class = {kind: 0 for kind in DEVICE_CLASSES}
        devices_by_state = {state: 0 for state in DEVICE_STATES}
        devices_by_derived = {status: 0 for status in DERIVED_STATUSES}
        now = _utc_now()
        for device in devices:
            devices_by_class[device["device_class"]] += 1
            devices_by_state[device["state"]] += 1
            devices_by_derived[self._derive_device_status(device, now)] += 1
        changes_by_status = {status: 0 for status in CHANGE_STATUSES}
        changes = [c for c in self._changes.values() if c["org_id"] == org_id]
        for change in changes:
            changes_by_status[change["status"]] += 1
        alerts = [a for a in self._alerts.values() if a["org_id"] == org_id]
        return {
            "org_id": org_id,
            "networks": sum(1 for n in self._networks.values()
                            if n["org_id"] == org_id),
            "devices": len(devices),
            "devices_by_class": devices_by_class,
            "devices_by_state": devices_by_state,
            "devices_by_derived_status": devices_by_derived,
            "telemetry_records": sum(1 for r in self._telemetry.values()
                                     if r["org_id"] == org_id),
            "changes": len(changes),
            "changes_by_status": changes_by_status,
            "automations": sum(1 for a in self._automations.values()
                               if a["org_id"] == org_id),
            "alerts": len(alerts),
            "alerts_unacknowledged": sum(
                1 for a in alerts if a["acknowledged_by"] is None),
        }
