"""Final GAPS batch, second unit — Remainder Addition extensions
for the Mobile Device Management (MDM) L2 build.

The remainder census added a second fork to this group: Ivanti
Neurons for MDM (formerly MobileIron), a genuine mobile-device /
unified endpoint management platform. Under the group's
taxonomy — defined from the founding fork's telecom expense
management prose, which contains no device-management family —
the newcomer claims **zero** families (see ``../ADDENDUM.md``),
so nothing here is a claim-driven core extension. The two
entries this unit closes are the two Extended functions the
addendum registered from the newcomer's own described
functions (``../BATCH-ADDITION.md`` has the per-entry
disposition):

- **Zero-trust access validation** (idx 679, build-extension):
  the fork describes a validation *plane* — per-request
  evaluation of device, identity, context, and privacy,
  producing access-level decisions. A records substrate does
  not evaluate requests. What is built is the decision-record
  layer, in the first unit's adjudicated forms (device
  commands, idx 481: request plus reported outcome,
  ``executed_here: False``; compliance checks, idx 482:
  reported results, state derived at read, nothing enforced):
  validation profiles held as definitions-as-data (the
  declared evaluation dimensions and access-level labels),
  validation decision records holding the plane's reported
  dimension results and its reported access level verbatim,
  and a view deriving the current reported access level at
  read from the latest decision record. ``evaluated_here``
  and ``decided_here`` are False on every record: no request
  is evaluated and no access decision is made by this build.
  Identity is an opaque ``subject_ref`` only — IA-2 stays
  with the embedding organization (``../../PLATFORM-LAYER.md``
  decision 1); no identity data of any kind is held.
- **Mobile threat defense** (idx 680, stub-engine): continual
  on-device detection and remediation is an engine over live
  devices, so it ships as a labeled reference implementation,
  per the house precedent and this group's first unit
  (workflow execution, carrier integration, alert delivery,
  enrollment): deployment records and threat-event records
  carrying ``reference_stub: True`` and state
  ``recorded_reference_only``, with detections and
  remediations recorded as reported by the external engine.
  ``detected_here`` and ``remediated_here`` are False on every
  record; creating one changes no core record, pinned by test.

The founding privacy invariant binds this surface exactly as it
binds the core and the first unit's extensions: devices are
opaque caller-supplied ``device_ref`` strings only, and no
record shape has a field that could hold an IMEI, serial,
phone number, MAC address, or any location data — pinned by a
recursive key scan over every stored record in this module,
using the first unit's ``FORBIDDEN_KEYS`` set verbatim.

Doctrines carried from the core and the first unit: derived
values are computed at read and stored nowhere (the access
view's current level, the threat summary's counts); append-only
audit on the core store's log, with this unit's actions
prefixed ``exta_`` (the second-unit convention — the first
unit's are ``ext_``); RBAC via :mod:`mdm.access` through the
core store's scoping seam (role permission plus organization
membership), enforced before any state change or id
allocation, so a failed operation consumes no id and changes
nothing; malformed input is rejected whole. No money moves on
this surface, so no amount field exists anywhere in it.

RBAC action mapping (the core action set is fixed): validation
profiles and threat deployments ride ``enter``; decision and
threat-event records ride ``record``; all reads ride ``read``.
"""

import threading
from datetime import datetime, timezone

from .audit import actor_name
from .errors import NotFoundError, ValidationError
from .extensions import FORBIDDEN_KEYS  # noqa: F401  (re-exported pin)
from .store import _text

VALIDATION_DIMENSIONS = ("device", "identity", "context", "privacy")
DIMENSION_RESULTS = ("pass", "fail")
DEPLOYMENT_MODES = ("silent", "announced")
THREAT_SCOPES = ("device", "network", "app")
CONNECTIVITY_STATES = ("on_connectivity", "off_connectivity")
REMEDIATION_REPORTS = (
    "reported_remediated", "reported_contained", "reported_unresolved",
)

ACCESS_METHOD = "derived_from_recorded_decisions"
THREAT_METHOD = "recorded_reference_counts"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _ref(value, field):
    return _text(value, field)


def _choice(value, choices, field):
    if value not in choices:
        raise ValidationError("%s must be one of %r" % (field, choices))
    return value


def _text_list(value, field):
    if not isinstance(value, list) or not value:
        raise ValidationError("%s must be a non-empty list of names" % field)
    for item in value:
        _text(item, field)
    return list(value)


class MdmExtensionsAddition:
    """Second-unit GAPS-batch extension surface wrapping a core
    :class:`MdmStore` (the remainder addition's two entries)."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._counters = {}
        self._validation_profiles = {}
        self._validation_decisions = {}
        self._threat_deployments = {}
        self._threat_events = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _scoped(self, actor, org_id, action):
        return self.store._scoped(actor, org_id, action)

    def _record(self, actor, action, target, details=None):
        self.store._record(actor, "exta_" + action, target, details)

    def _fetch(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("no such %s: %r" % (what, record_id))
        return record

    def _get_scoped(self, actor, table, record_id, what):
        self.store._check_role(actor, "read")
        record = self._fetch(table, record_id, what)
        self._scoped(actor, record["org_id"], "read")
        return record

    def _list_scoped(self, actor, table, org_id):
        self._scoped(actor, org_id, "read")
        return [dict(r) for r in table.values() if r["org_id"] == org_id]

    # -- zero-trust access validation, records form (idx 679, built) -------
    # Validation profiles are definitions as data; decisions are
    # the external plane's reported outcomes; the current access
    # level is derived at read. Nothing is evaluated or decided
    # here: evaluated_here / decided_here are False throughout.

    def create_validation_profile(self, actor, org_id, profile_ref, name,
                                  dimensions, access_levels):
        """Record a zero-trust validation profile as data.

        The profile declares which evaluation dimensions the
        external validation plane reports on (from the entry's
        own vocabulary: device, identity, context, privacy) and
        the access-level labels it may report. Recording the
        declaration evaluates nothing.
        """
        self._scoped(actor, org_id, "enter")
        _ref(profile_ref, "profile_ref")
        _text(name, "name")
        dimensions = _text_list(dimensions, "dimensions")
        for dimension in dimensions:
            _choice(dimension, VALIDATION_DIMENSIONS, "dimension")
        if len(set(dimensions)) != len(dimensions):
            raise ValidationError("dimensions must not repeat")
        access_levels = _text_list(access_levels, "access_levels")
        if len(set(access_levels)) != len(access_levels):
            raise ValidationError("access_levels must not repeat")
        with self._lock:
            for existing in self._validation_profiles.values():
                if existing["org_id"] == org_id \
                        and existing["profile_ref"] == profile_ref:
                    raise ValidationError(
                        "profile ref already exists in this organization: %r"
                        % (profile_ref,))
            record = {
                "id": self._mint("zvp-"),
                "org_id": org_id,
                "profile_ref": profile_ref,
                "name": name,
                "dimensions": dimensions,
                "access_levels": access_levels,
                "evaluated_here": False,
                "decided_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._validation_profiles[record["id"]] = record
        self._record(actor, "validation_profile_create", record["id"],
                     {"profile_ref": profile_ref})
        view = dict(record)
        view["dimensions"] = list(record["dimensions"])
        view["access_levels"] = list(record["access_levels"])
        return view

    def get_validation_profile(self, actor, profile_id):
        record = self._get_scoped(actor, self._validation_profiles,
                                  profile_id, "validation profile")
        view = dict(record)
        view["dimensions"] = list(record["dimensions"])
        view["access_levels"] = list(record["access_levels"])
        return view

    def list_validation_profiles(self, actor, org_id):
        return [self.get_validation_profile(actor, r["id"])
                for r in self._list_scoped(
                    actor, self._validation_profiles, org_id)]

    def record_validation_decision(self, actor, profile_id, device_ref,
                                   subject_ref, dimension_results,
                                   reported_access_level):
        """Record one validation outcome, as reported by the plane.

        ``dimension_results`` maps the profile's declared
        dimension labels to the reported ``pass`` / ``fail``
        labels; ``reported_access_level`` is the plane's
        decision label, recorded verbatim and validated against
        the profile's declared levels. The device and the
        subject are opaque references only — no device
        identifier and no identity data exists in this record.
        Recording a decision evaluates nothing and grants or
        denies nothing here.
        """
        profile = self._fetch(self._validation_profiles, profile_id,
                              "validation profile")
        self._scoped(actor, profile["org_id"], "record")
        _ref(device_ref, "device_ref")
        _ref(subject_ref, "subject_ref")
        if not isinstance(dimension_results, dict) or not dimension_results:
            raise ValidationError("dimension_results must be a non-empty object")
        cleaned = {}
        for label, outcome in dimension_results.items():
            if label not in profile["dimensions"]:
                raise ValidationError(
                    "result label is not a dimension of this profile: %r"
                    % (label,))
            _choice(outcome, DIMENSION_RESULTS, "dimension result")
            cleaned[label] = outcome
        _choice(reported_access_level, tuple(profile["access_levels"]),
                "reported_access_level")
        with self._lock:
            record = {
                "id": self._mint("zvd-"),
                "org_id": profile["org_id"],
                "profile_id": profile_id,
                "device_ref": device_ref,
                "subject_ref": subject_ref,
                "dimension_results": cleaned,
                "reported_access_level": reported_access_level,
                "validated_here": False,
                "decided_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._validation_decisions[record["id"]] = record
        self._record(actor, "validation_decision_record", record["id"],
                     {"profile_id": profile_id, "device_ref": device_ref})
        view = dict(record)
        view["dimension_results"] = dict(record["dimension_results"])
        return view

    def get_validation_decision(self, actor, decision_id):
        record = self._get_scoped(actor, self._validation_decisions,
                                  decision_id, "validation decision")
        view = dict(record)
        view["dimension_results"] = dict(record["dimension_results"])
        return view

    def list_validation_decisions(self, actor, org_id):
        result = []
        for record in self._list_scoped(
                actor, self._validation_decisions, org_id):
            view = dict(record)
            view["dimension_results"] = dict(record["dimension_results"])
            result.append(view)
        return result

    def _current_decision(self, decisions):
        """The current reported decision is the LATEST recorded one.

        This seam is the unit's fresh negative-control target
        (see tests/README.md): a derivation that read the
        earliest decision instead would report a superseded
        access level as current.
        """
        return decisions[-1] if decisions else None

    def access_view(self, actor, profile_id, device_ref):
        """Derive one device's current reported access level.

        From the recorded decisions only: no decisions reads
        ``unreported`` with a null level; otherwise the latest
        decision's reported access level stands as current.
        Derived at read, stored nowhere; nothing is decided
        here — the level is the external plane's reported
        decision, read back.
        """
        profile = self._get_scoped(actor, self._validation_profiles,
                                   profile_id, "validation profile")
        _ref(device_ref, "device_ref")
        decisions = [d for d in self._validation_decisions.values()
                     if d["profile_id"] == profile_id
                     and d["device_ref"] == device_ref]
        latest = self._current_decision(decisions)
        return {
            "profile_id": profile["id"],
            "device_ref": device_ref,
            "state": "reported" if latest else "unreported",
            "current_access_level":
                latest["reported_access_level"] if latest else None,
            "decisions": len(decisions),
            "latest_decision_id": latest["id"] if latest else None,
            "method": ACCESS_METHOD,
            "decided_here": False,
            "derived": True,
            "stored": False,
        }

    # -- mobile threat defense reference (idx 680, stub-engine) ------------
    # Labeled reference implementation: deployment and threat
    # records only. Nothing detects or remediates anything
    # here; creating a record changes no core record.

    def record_threat_deployment(self, actor, org_id, device_ref,
                                 deployment_mode):
        """Record a threat-defense deployment, as reported.

        Labeled reference implementation: the record names a
        device (opaque reference only) and the reported
        deployment mode — ``silent`` is the fork's own word for
        its activation. Nothing is deployed to any device here.
        """
        self._scoped(actor, org_id, "enter")
        _ref(device_ref, "device_ref")
        _choice(deployment_mode, DEPLOYMENT_MODES, "deployment_mode")
        with self._lock:
            record = {
                "id": self._mint("mtd-"),
                "org_id": org_id,
                "device_ref": device_ref,
                "deployment_mode": deployment_mode,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "deployed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._threat_deployments[record["id"]] = record
        self._record(actor, "threat_deployment_record", record["id"],
                     {"device_ref": device_ref,
                      "deployment_mode": deployment_mode})
        return dict(record)

    def get_threat_deployment(self, actor, deployment_id):
        return dict(self._get_scoped(
            actor, self._threat_deployments, deployment_id,
            "threat defense deployment"))

    def list_threat_deployments(self, actor, org_id):
        return self._list_scoped(actor, self._threat_deployments, org_id)

    def record_threat_event(self, actor, deployment_id, scope, threat_label,
                            connectivity, reported_remediation):
        """Record a threat detection and its remediation, as reported.

        The scope is one of the fork's own three (device,
        network, app); the connectivity label records whether
        the engine reported the threat on or off connectivity;
        the remediation label is the engine's reported outcome.
        The device reference is taken from the deployment
        record, never supplied separately, so an event cannot
        name a device its deployment does not. Nothing is
        detected or remediated here.
        """
        deployment = self._fetch(self._threat_deployments, deployment_id,
                                 "threat defense deployment")
        self._scoped(actor, deployment["org_id"], "record")
        _choice(scope, THREAT_SCOPES, "scope")
        _text(threat_label, "threat_label")
        _choice(connectivity, CONNECTIVITY_STATES, "connectivity")
        _choice(reported_remediation, REMEDIATION_REPORTS,
                "reported_remediation")
        with self._lock:
            record = {
                "id": self._mint("mte-"),
                "org_id": deployment["org_id"],
                "deployment_id": deployment_id,
                "device_ref": deployment["device_ref"],
                "scope": scope,
                "threat_label": threat_label,
                "connectivity": connectivity,
                "reported_remediation": reported_remediation,
                "reference_stub": True,
                "status": "recorded_reference_only",
                "detected_here": False,
                "remediated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._threat_events[record["id"]] = record
        self._record(actor, "threat_event_record", record["id"],
                     {"deployment_id": deployment_id, "scope": scope})
        return dict(record)

    def get_threat_event(self, actor, event_id):
        return dict(self._get_scoped(
            actor, self._threat_events, event_id, "threat event"))

    def list_threat_events(self, actor, org_id):
        return self._list_scoped(actor, self._threat_events, org_id)

    def threat_summary(self, actor, org_id):
        """Derive counts over the recorded reference records.

        Counts of deployments and of reported threat events, by
        scope and by reported remediation — computed at read
        over this module's own records, stored nowhere. The
        summary is over reference records and carries the
        reference label itself.
        """
        self._scoped(actor, org_id, "read")
        deployments = [d for d in self._threat_deployments.values()
                       if d["org_id"] == org_id]
        events = [e for e in self._threat_events.values()
                  if e["org_id"] == org_id]
        by_scope = {}
        by_remediation = {}
        for event in events:
            by_scope[event["scope"]] = by_scope.get(event["scope"], 0) + 1
            key = event["reported_remediation"]
            by_remediation[key] = by_remediation.get(key, 0) + 1
        return {
            "org_id": org_id,
            "deployments": len(deployments),
            "threat_events": len(events),
            "events_by_scope": by_scope,
            "events_by_reported_remediation": by_remediation,
            "method": THREAT_METHOD,
            "reference_stub": True,
            "detected_here": False,
            "remediated_here": False,
            "derived": True,
            "stored": False,
        }
