"""Media store: organization registry; endpoint, route, and
stream-session records; device and control-action records;
optimization-profile records; status-snapshot records.

Clean-room implementation of the union spec's implementation
contract. This category is new — no tiered group exists — and the
core is claim-driven: every record type traces to a claim in the
set's spec sheet (see UNION-SPEC.md), except the organization
registry, search/summary, and API/access/audit substrate every
DeadRamp build carries, whose reason is stated in the spec.

Role permission is enforced on every operation when the actor is
a User-like object: the action named for the operation must be in
the actor's role permission set (see :mod:`media.access`). A
plain string actor carries identity (for provenance) but no role,
so role enforcement for those happens in the service layer (the
sibling builds' convention).

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``end-``, ``rou-``, ``ses-``, ``dev-``, ``ctl-``, ``opt-``,
``sta-``).

Media discipline (the core-boundary decision): this store holds
**records about media, never media**. No record shape has a field
that could hold video, audio, a stream payload, or a file: routes
name endpoints and labels, sessions name a route and two moments,
snapshots name a subject and a status word. Nothing is
transported, recorded, played back, or transcoded here — the
transport itself is Extended, and the shapes are pinned by test.

Derivation discipline: a session's state and a route's state are
derived at read time and never stored. The seam
:func:`_derive_session_state` computes ``live`` / ``ended`` from
the session record's stop moment; the seam
:func:`_derive_route_state` computes ``live`` / ``idle`` from the
count of the route's open sessions. A subject's current status is
likewise derived: the status word of its most recently
**recorded** snapshot (recording order in this store, not the
caller's timestamps — caller moments are data, the derivation is
the store's own order of record). Stored session and route
records carry no state key.

One-live-session guard (the signature invariant): a route carries
at most one live session. Starting a session on a route that
already has one is refused through the single seam
:func:`_check_route_available`; the refusal records nothing and
consumes no id. The guard is what makes the derived route state
well-defined — a route is live because exactly one session is
open on it — and it binds at start time only: stopping the open
session frees the route, and a stopped session is never
resurrected.

Control discipline: control-action records describe device
control actions an operator took or intends; recording one sends
nothing and changes no device, route, or session. Optimization
profiles likewise record settings text verbatim, never executed:
there is deliberately no execution entry point anywhere in this
package (pinned by test). The registry describes; engines are
Extended.

Encryption discipline: a route record carries a caller-stated
encryption **label** from a fixed vocabulary (``aes_256`` /
``none_stated``) — metadata recording what the route's transport
is stated to use. This build performs no cryptography of any
kind; the fork's AES-256 claim is its own, traced in the union
spec's Documented control claims, and the label neither performs
nor attains it.

Scoring discipline: nothing in this store computes a score, a
rating, a quality metric, or a latency figure. The description
says the service adds "minimal latency"; no latency is measured,
computed, or stored here. Reports and the summary return counts
and recorded values only.

Money discipline: no record in this store carries money. The
description states no fee, price, or budget, so no money shape
was built — the same deliberate omission the sibling new-category
builds recorded.

The store records every successful mutation to its audit log
(when one is attached). Reads are not audited here; denied
attempts and audit reads are the HTTP layer's responsibility, so
nothing is recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError

ENDPOINT_KINDS = ("agency_network", "cloud_destination")
ENCRYPTION_LABELS = ("aes_256", "none_stated")
DEVICE_ACTIONS = ("start", "stop", "restart", "adjust")
STATUS_VALUES = ("up", "degraded", "down", "unknown")
SUBJECT_KINDS = ("route", "device")
ROUTE_STATES = ("idle", "live")
SESSION_STATES = ("live", "ended")


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_moment(value, field):
    """Parse an ISO date or datetime into an aware datetime."""
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
            raise ValidationError("%s is not an ISO date or datetime: %r" % (field, value))
    else:
        raise ValidationError("%s must be an ISO date or datetime string" % field)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _ref(value, field):
    """An opaque reference. It must be a non-empty string with no
    whitespace and no ``@`` — a value of that shape cannot be an
    email address, so no record keyed by it can hold one."""
    _text(value, field)
    if "@" in value or any(ch.isspace() for ch in value):
        raise ValidationError(
            "%s must be an opaque reference (no whitespace, no '@')" % field)
    return value


def _derive_session_state(session):
    """Session state derivation seam: ``live`` while the session
    has no recorded stop moment, ``ended`` once it does. Pure
    function over the recorded values; nothing about the state is
    stored."""
    return "ended" if session.get("stopped_at") is not None else "live"


def _derive_route_state(open_session_count):
    """Route state derivation seam: ``live`` while at least one
    session is open on the route, ``idle`` otherwise. The
    one-live-session guard caps the count at one, so this is a
    binary fact, never an aggregate."""
    return "live" if open_session_count > 0 else "idle"


def _check_route_available(open_session):
    """One-live-session guard seam: the single check the session
    start operation reads before recording a new session.

    A route that already has a live session refuses another: two
    simultaneous live streams on one recorded route would make
    the route's derived state — and every status view over it —
    ambiguous about which stream it describes.
    """
    if open_session is not None:
        raise ValidationError(
            "route %r already has a live session (%s); stop it "
            "before starting another"
            % (open_session["route_id"], open_session["id"]))


class MediaStore:
    """In-memory Media records store with an optional audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._endpoints = {}
        self._routes = {}
        self._sessions = {}
        self._devices = {}
        self._control_actions = {}
        self._profiles = {}
        self._snapshots = {}
        self._counters = {}

    # -- internal helpers ---------------------------------------------------

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
        organization = self._organizations.get(org_id)
        if organization is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return organization

    def _endpoint(self, endpoint_id):
        endpoint = self._endpoints.get(endpoint_id)
        if endpoint is None:
            raise NotFoundError("no such endpoint: %r" % (endpoint_id,))
        return endpoint

    def _route(self, route_id):
        route = self._routes.get(route_id)
        if route is None:
            raise NotFoundError("no such route: %r" % (route_id,))
        return route

    def _session(self, session_id):
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("no such session: %r" % (session_id,))
        return session

    def _device(self, device_id):
        device = self._devices.get(device_id)
        if device is None:
            raise NotFoundError("no such device: %r" % (device_id,))
        return device

    def _profile(self, profile_id):
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise NotFoundError(
                "no such optimization profile: %r" % (profile_id,))
        return profile

    def _open_session(self, route_id):
        for session in self._sessions.values():
            if (session["route_id"] == route_id
                    and session["stopped_at"] is None):
                return session
        return None

    def _subject(self, subject_kind, subject_id):
        if subject_kind == "route":
            return self._route(subject_id)
        if subject_kind == "device":
            return self._device(subject_id)
        raise ValidationError(
            "subject_kind must be one of %r" % (SUBJECT_KINDS,))

    # -- organizations ---------------------------------------------------------

    def create_organization(self, actor, ref, label):
        """Register an organization by opaque reference."""
        self._check_role(actor, "register")
        _ref(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["ref"] == ref:
                    raise ValidationError(
                        "organization ref already registered: %r" % (ref,))
            record = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[record["id"]] = record
        self._record(actor, "create_organization", record["id"],
                     {"ref": ref})
        return dict(record)

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        return dict(self._organization(org_id))

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        return [dict(o) for o in self._organizations.values()]

    # -- endpoints ---------------------------------------------------------

    def create_endpoint(self, actor, org_id, ref, label, kind):
        """Record one endpoint of the video network: an agency
        network or a cloud destination, keyed by an opaque
        reference unique within its organization. Endpoints are
        the nouns the fork's transport sentence moves video
        between — "from agency networks to other inter- and
        intra-agency destinations ... and commercial cloud
        destinations"."""
        self._check_role(actor, "register")
        _ref(ref, "ref")
        _text(label, "label")
        if kind not in ENDPOINT_KINDS:
            raise ValidationError(
                "kind must be one of %r" % (ENDPOINT_KINDS,))
        with self._lock:
            self._organization(org_id)
            for existing in self._endpoints.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "endpoint ref already recorded for this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("end-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "kind": kind,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._endpoints[record["id"]] = record
        self._record(actor, "create_endpoint", record["id"],
                     {"org_id": org_id, "ref": ref, "kind": kind})
        return dict(record)

    def get_endpoint(self, actor, endpoint_id):
        self._check_role(actor, "read")
        return dict(self._endpoint(endpoint_id))

    def list_endpoints(self, actor, org_id=None, kind=None):
        self._check_role(actor, "read")
        if kind is not None and kind not in ENDPOINT_KINDS:
            raise ValidationError(
                "kind must be one of %r" % (ENDPOINT_KINDS,))
        return [dict(e) for e in self._endpoints.values()
                if (org_id is None or e["org_id"] == org_id)
                and (kind is None or e["kind"] == kind)]

    # -- routes -----------------------------------------------------------

    def create_route(self, actor, org_id, label, source_endpoint_id,
                     destination_endpoint_id, encryption="aes_256",
                     protocol_label=None):
        """Record a route between two endpoints of one
        organization. The route carries a caller-stated encryption
        label (metadata only — this build performs no
        cryptography) and an optional caller-stated protocol
        label (the description names no protocol, so none is
        defaulted or validated against a list). The stored record
        carries no state key: state is derived at read (see
        :func:`_derive_route_state`)."""
        self._check_role(actor, "routes")
        _text(label, "label")
        if encryption not in ENCRYPTION_LABELS:
            raise ValidationError(
                "encryption must be one of %r" % (ENCRYPTION_LABELS,))
        _optional_text(protocol_label, "protocol_label")
        with self._lock:
            self._organization(org_id)
            source = self._endpoint(source_endpoint_id)
            destination = self._endpoint(destination_endpoint_id)
            if source["org_id"] != org_id or destination["org_id"] != org_id:
                raise ValidationError(
                    "both endpoints must belong to the route's "
                    "organization")
            if source_endpoint_id == destination_endpoint_id:
                raise ValidationError(
                    "a route's source and destination must differ")
            record = {
                "id": self._mint("rou-"),
                "org_id": org_id,
                "label": label,
                "source_endpoint_id": source_endpoint_id,
                "destination_endpoint_id": destination_endpoint_id,
                "encryption": encryption,
                "protocol_label": protocol_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._routes[record["id"]] = record
        self._record(actor, "create_route", record["id"],
                     {"org_id": org_id, "label": label,
                      "encryption": encryption})
        return self._route_view(record)

    def _route_view(self, route):
        view = dict(route)
        open_count = 1 if self._open_session(route["id"]) else 0
        view["state"] = _derive_route_state(open_count)
        return view

    def get_route(self, actor, route_id):
        self._check_role(actor, "read")
        return self._route_view(self._route(route_id))

    def list_routes(self, actor, org_id=None, state=None):
        self._check_role(actor, "read")
        if state is not None and state not in ROUTE_STATES:
            raise ValidationError(
                "state must be one of %r" % (ROUTE_STATES,))
        result = []
        for route in self._routes.values():
            if org_id is not None and route["org_id"] != org_id:
                continue
            view = self._route_view(route)
            if state is not None and view["state"] != state:
                continue
            result.append(view)
        return result

    # -- stream sessions ------------------------------------------------------

    def start_session(self, actor, route_id, started_at=None):
        """Start a stream session on a route — the recorded form
        of the offering's start-up and of transport itself.

        The one-live-session guard binds here (see
        :func:`_check_route_available`): a second start while a
        session is live on the route is refused and changes
        nothing. The stored record carries no state key; its
        state is derived from the absence of a stop moment.
        """
        self._check_role(actor, "sessions")
        started = None
        if started_at is not None:
            started = _parse_moment(started_at, "started_at")
        with self._lock:
            self._route(route_id)
            _check_route_available(self._open_session(route_id))
            record = {
                "id": self._mint("ses-"),
                "route_id": route_id,
                "started_at": (started.isoformat() if started is not None
                               else _utc_now().isoformat()),
                "stopped_at": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._sessions[record["id"]] = record
        self._record(actor, "start_session", record["id"],
                     {"route_id": route_id})
        return self._session_view(record)

    def stop_session(self, actor, session_id, stopped_at=None):
        """Record the stop of a live session. Stopping an ended
        session is refused, and a stop moment before the start
        moment is refused; both refusals change nothing."""
        self._check_role(actor, "sessions")
        stopped = None
        if stopped_at is not None:
            stopped = _parse_moment(stopped_at, "stopped_at")
        with self._lock:
            session = self._session(session_id)
            if session["stopped_at"] is not None:
                raise ValidationError(
                    "session %r has already ended" % (session_id,))
            moment = stopped if stopped is not None else _utc_now()
            if moment < _parse_moment(session["started_at"], "started_at"):
                raise ValidationError(
                    "stopped_at precedes the session's started_at")
            session["stopped_at"] = moment.isoformat()
            result = dict(session)
        self._record(actor, "stop_session", session_id,
                     {"route_id": result["route_id"]})
        return self._session_view(result)

    def _session_view(self, session):
        view = dict(session)
        view["state"] = _derive_session_state(session)
        return view

    def get_session(self, actor, session_id):
        self._check_role(actor, "read")
        return self._session_view(self._session(session_id))

    def list_sessions(self, actor, route_id=None, state=None):
        self._check_role(actor, "read")
        if state is not None and state not in SESSION_STATES:
            raise ValidationError(
                "state must be one of %r" % (SESSION_STATES,))
        result = []
        for session in self._sessions.values():
            if route_id is not None and session["route_id"] != route_id:
                continue
            view = self._session_view(session)
            if state is not None and view["state"] != state:
                continue
            result.append(view)
        return result

    # -- devices -----------------------------------------------------------

    def create_device(self, actor, org_id, ref, label, kind_label=None,
                      endpoint_id=None):
        """Record a device under integrated control: an opaque
        reference and labels, optionally sited at an endpoint of
        the same organization. The record names the device; it
        holds no address, credential, or identifier a network
        could use to reach one."""
        self._check_role(actor, "devices")
        _ref(ref, "ref")
        _text(label, "label")
        _optional_text(kind_label, "kind_label")
        with self._lock:
            self._organization(org_id)
            if endpoint_id is not None:
                endpoint = self._endpoint(endpoint_id)
                if endpoint["org_id"] != org_id:
                    raise ValidationError(
                        "the device's endpoint must belong to the "
                        "device's organization")
            for existing in self._devices.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "device ref already recorded for this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("dev-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "kind_label": kind_label,
                "endpoint_id": endpoint_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._devices[record["id"]] = record
        self._record(actor, "create_device", record["id"],
                     {"org_id": org_id, "ref": ref})
        return dict(record)

    def get_device(self, actor, device_id):
        self._check_role(actor, "read")
        return dict(self._device(device_id))

    def list_devices(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(d) for d in self._devices.values()
                if org_id is None or d["org_id"] == org_id]

    # -- control actions (records only; nothing is sent) ----------------------

    def record_control_action(self, actor, device_id, action, note=None,
                              at=None):
        """Record one device control action (start / stop /
        restart / adjust) with an optional verbatim note.

        A record only: recording an action sends nothing to any
        device and changes no device, route, or session — the
        control channel itself is Extended (see UNION-SPEC.md).
        The registry exists so control activity is named,
        attributed, and auditable.
        """
        self._check_role(actor, "control")
        if action not in DEVICE_ACTIONS:
            raise ValidationError(
                "action must be one of %r" % (DEVICE_ACTIONS,))
        _optional_text(note, "note")
        moment = None
        if at is not None:
            moment = _parse_moment(at, "at")
        with self._lock:
            self._device(device_id)
            record = {
                "id": self._mint("ctl-"),
                "device_id": device_id,
                "action": action,
                "note": note,
                "recorded_at": (moment.isoformat() if moment is not None
                                else _utc_now().isoformat()),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._control_actions[record["id"]] = record
        self._record(actor, "record_control_action", record["id"],
                     {"device_id": device_id, "action": action})
        return dict(record)

    def list_control_actions(self, actor, device_id=None, action=None):
        self._check_role(actor, "read")
        if action is not None and action not in DEVICE_ACTIONS:
            raise ValidationError(
                "action must be one of %r" % (DEVICE_ACTIONS,))
        return [dict(c) for c in self._control_actions.values()
                if (device_id is None or c["device_id"] == device_id)
                and (action is None or c["action"] == action)]

    # -- optimization profiles (records only; never executed) ------------------

    def create_optimization_profile(self, actor, org_id, label,
                                    settings_text, route_id=None,
                                    enabled=True):
        """Record a stream-optimization profile: a label, the
        settings text stored **verbatim** (never parsed, never
        executed), an optional route of the same organization,
        and an enabled flag. The optimization engine that would
        apply a profile to a live stream is Extended."""
        self._check_role(actor, "optimize")
        _text(label, "label")
        _text(settings_text, "settings_text")
        if not isinstance(enabled, bool):
            raise ValidationError("enabled must be a boolean")
        with self._lock:
            self._organization(org_id)
            if route_id is not None:
                route = self._route(route_id)
                if route["org_id"] != org_id:
                    raise ValidationError(
                        "the profile's route must belong to the "
                        "profile's organization")
            record = {
                "id": self._mint("opt-"),
                "org_id": org_id,
                "label": label,
                "settings_text": settings_text,
                "route_id": route_id,
                "enabled": enabled,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._profiles[record["id"]] = record
        self._record(actor, "create_optimization_profile", record["id"],
                     {"org_id": org_id, "label": label})
        return dict(record)

    def set_profile_enabled(self, actor, profile_id, enabled):
        """Record a profile's enabled flag. Toggling the flag
        applies nothing to any stream; it is a recorded state."""
        self._check_role(actor, "optimize")
        if not isinstance(enabled, bool):
            raise ValidationError("enabled must be a boolean")
        with self._lock:
            profile = self._profile(profile_id)
            profile["enabled"] = enabled
            result = dict(profile)
        self._record(actor, "set_profile_enabled", profile_id,
                     {"enabled": enabled})
        return result

    def list_profiles(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(p) for p in self._profiles.values()
                if org_id is None or p["org_id"] == org_id]

    # -- status snapshots -----------------------------------------------------

    def record_status_snapshot(self, actor, subject_kind, subject_id,
                               status, at=None):
        """Record one status snapshot for a route or a device:
        a status word from the fixed vocabulary (up / degraded /
        down / unknown) at a moment. The telemetry that would
        produce snapshots in operation is Extended; this is the
        record it would produce."""
        self._check_role(actor, "monitor")
        if subject_kind not in SUBJECT_KINDS:
            raise ValidationError(
                "subject_kind must be one of %r" % (SUBJECT_KINDS,))
        if status not in STATUS_VALUES:
            raise ValidationError(
                "status must be one of %r" % (STATUS_VALUES,))
        moment = None
        if at is not None:
            moment = _parse_moment(at, "at")
        with self._lock:
            self._subject(subject_kind, subject_id)
            record = {
                "id": self._mint("sta-"),
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "status": status,
                "recorded_at": (moment.isoformat() if moment is not None
                                else _utc_now().isoformat()),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._snapshots[record["id"]] = record
        self._record(actor, "record_status_snapshot", record["id"],
                     {"subject_kind": subject_kind,
                      "subject_id": subject_id, "status": status})
        return dict(record)

    def list_snapshots(self, actor, subject_kind=None, subject_id=None):
        self._check_role(actor, "read")
        if subject_kind is not None and subject_kind not in SUBJECT_KINDS:
            raise ValidationError(
                "subject_kind must be one of %r" % (SUBJECT_KINDS,))
        return [dict(s) for s in self._snapshots.values()
                if (subject_kind is None
                    or s["subject_kind"] == subject_kind)
                and (subject_id is None or s["subject_id"] == subject_id)]

    def _current_snapshot(self, subject_kind, subject_id):
        """The most recently recorded snapshot for the subject,
        in this store's recording order — the derivation behind
        every current-status view."""
        current = None
        for snapshot in self._snapshots.values():
            if (snapshot["subject_kind"] == subject_kind
                    and snapshot["subject_id"] == subject_id):
                current = snapshot
        return current

    def current_status(self, actor, subject_kind, subject_id):
        """The subject's current status, derived at read: the
        status word of its most recently recorded snapshot, or
        None when no snapshot exists. Nothing is stored."""
        self._check_role(actor, "read")
        if subject_kind not in SUBJECT_KINDS:
            raise ValidationError(
                "subject_kind must be one of %r" % (SUBJECT_KINDS,))
        with self._lock:
            self._subject(subject_kind, subject_id)
            snapshot = self._current_snapshot(subject_kind, subject_id)
            return {
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "status": (snapshot["status"] if snapshot is not None
                           else None),
                "snapshot_id": (snapshot["id"] if snapshot is not None
                                else None),
            }

    def network_status(self, actor, org_id):
        """The network status view for one organization: for each
        of its routes, the derived route state and the derived
        current status word, with counts. Derived on read from
        the records; counts and recorded values only."""
        self._check_role(actor, "read")
        with self._lock:
            self._organization(org_id)
            routes = []
            by_state = {s: 0 for s in ROUTE_STATES}
            by_status = {s: 0 for s in STATUS_VALUES}
            unreported = 0
            for route in self._routes.values():
                if route["org_id"] != org_id:
                    continue
                view = self._route_view(route)
                snapshot = self._current_snapshot("route", route["id"])
                status = (snapshot["status"] if snapshot is not None
                          else None)
                by_state[view["state"]] += 1
                if status is None:
                    unreported += 1
                else:
                    by_status[status] += 1
                routes.append({
                    "route_id": route["id"],
                    "label": route["label"],
                    "state": view["state"],
                    "status": status,
                })
            return {
                "org_id": org_id,
                "routes": routes,
                "routes_by_state": by_state,
                "routes_by_status": by_status,
                "routes_unreported": unreported,
            }

    # -- search, summary, audit ---------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over the
        registered metadata: organizations, endpoints, routes,
        devices, and optimization profiles."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()

        def hit(*fields):
            return any(needle in (f or "").lower() for f in fields)

        return {
            "organizations": [dict(o) for o in self._organizations.values()
                              if hit(o["ref"], o["label"])],
            "endpoints": [dict(e) for e in self._endpoints.values()
                          if hit(e["ref"], e["label"])],
            "routes": [self._route_view(r) for r in self._routes.values()
                       if hit(r["label"])],
            "devices": [dict(d) for d in self._devices.values()
                        if hit(d["ref"], d["label"])],
            "profiles": [dict(p) for p in self._profiles.values()
                         if hit(p["label"])],
        }

    def summary(self, actor):
        """Counts computed on read from the records. Counts only:
        no scores, no rates, no latency figures."""
        self._check_role(actor, "read")
        endpoints_by_kind = {k: 0 for k in ENDPOINT_KINDS}
        for endpoint in self._endpoints.values():
            endpoints_by_kind[endpoint["kind"]] += 1
        routes_by_state = {s: 0 for s in ROUTE_STATES}
        for route in self._routes.values():
            routes_by_state[self._route_view(route)["state"]] += 1
        sessions_by_state = {s: 0 for s in SESSION_STATES}
        for session in self._sessions.values():
            sessions_by_state[_derive_session_state(session)] += 1
        actions_by_kind = {a: 0 for a in DEVICE_ACTIONS}
        for control in self._control_actions.values():
            actions_by_kind[control["action"]] += 1
        snapshots_by_status = {s: 0 for s in STATUS_VALUES}
        for snapshot in self._snapshots.values():
            snapshots_by_status[snapshot["status"]] += 1
        return {
            "organizations": len(self._organizations),
            "endpoints": len(self._endpoints),
            "endpoints_by_kind": endpoints_by_kind,
            "routes": len(self._routes),
            "routes_by_state": routes_by_state,
            "sessions": len(self._sessions),
            "sessions_by_state": sessions_by_state,
            "devices": len(self._devices),
            "control_actions": len(self._control_actions),
            "control_actions_by_kind": actions_by_kind,
            "profiles": len(self._profiles),
            "profiles_enabled": sum(1 for p in self._profiles.values()
                                    if p["enabled"]),
            "snapshots": len(self._snapshots),
            "snapshots_by_status": snapshots_by_status,
        }

    def audit_read(self, actor):
        """Return the audit entries (requires ``audit_read``)."""
        self._check_role(actor, "audit_read")
        entries = self.audit.entries() if self.audit is not None else []
        return {"count": len(entries), "entries": entries}
