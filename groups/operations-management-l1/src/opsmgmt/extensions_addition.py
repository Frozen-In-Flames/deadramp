"""Final GAPS batch extensions, second unit: the remainder
additions to the Operations Management L1 singleton build
(3 forks joining Singleton 52 -- Booz Allen Hamilton SCMC,
FM:Systems OpenBlue Employee, Tango).

Clean-room extension surface for the 7 OPEN entries in the
"Remainder Addition -- Operations Management L1 (+3 forks)"
section of the repo-root ``GAPS.md`` (inventory idx 613-619,
specified in ``ADDENDUM.md`` section 5). See ``BATCH-ADDITION.md``
in the group directory for the per-entry disposition.

Design, following the core's doctrines, the first batch unit's
forms (``opsmgmt/extensions.py``, which this module does not
modify), and this group's spec:

- This module wraps :class:`opsmgmt.store.OpsStore`; the core
  modules and the first unit's extension module are untouched
  (byte-identical). Core records (persons, organizations,
  projects, assets, work orders, usage records) are always read
  through the core store's public API, never re-implemented.
  The baseline claim stays Low / FAR 52.204-21 only; no
  Moderate-tier apparatus is imported.
- The 7 entries land in the same records-form discipline as the
  first unit: registries of the thing, records of its reported
  state, and deterministic derivations over the group's own
  records. Nothing in this module schedules externally,
  reserves, senses, renders, publishes, hosts, signs, pays,
  connects, syncs, routes, or computes a score or a prediction.
  Reservation state, visitor handling state, lease obligation
  state, and plan state are all **derived at read** from
  recorded events and never stored -- the same
  derived-never-stored doctrine the core uses for work-order
  overdue.
- The one stub-engine entry (IoT sensor integration &
  utilization sensing) ships as a **labeled reference
  implementation**: every record carries
  ``reference_stub: True``; feed records additionally carry
  ``reference_transport: True``; every record states
  ``received_here: False`` and ``sensed_here: False``. Nothing
  is received from or measured on any physical sensor; readings
  exist only as reported batches with utilization figures
  stored verbatim as reported.
- Identity stays with the embedding organization
  (PLATFORM-LAYER.md decision 1): visitor records hold an
  opaque visitor reference by design; no identity surface
  exists here at all.
- RBAC reuses the founding 16-action matrix with **no new
  actions**; each operation maps onto an existing core action,
  checked before any state change or id allocation for
  User-like actors, mirroring the core store's convention
  (plain-string actors carry identity but no role). Successful
  mutations are recorded on the core audit log with an
  ``exta_``-prefixed action name (``exta_`` distinguishes this
  second unit's actions from the first unit's ``ext_`` ones);
  denied attempts are recorded with the same name suffixed
  ``:denied`` before the denial propagates:

  ==============================  ================  ================
  surface                         write action      read action
  ==============================  ================  ================
  reservations                    work_write        work_read
  reservation current view        --                work_read
  visitor registrations / events  work_write        work_read
  event definitions               workflow_write    workflow_read
  event check-ins                 work_write        work_read
  floor-plan definitions          workflow_write    workflow_read
  signage definitions             workflow_write    workflow_read
  digital notices                 work_write        work_read
  sensor references / feeds       work_write        work_read
  utilization views               --                usage_read
  analytics definitions           workflow_write    workflow_read
  analytics runs / figures        work_write        report_read
  catalog listings                asset_write       asset_read
  requisitions                    work_write        work_read
  purchase records / outcomes     usage_write       usage_read
  portfolio spaces                asset_write       asset_read
  move / lease / transaction /    work_write        work_read
    prediction records
  portfolio views                 --                report_read
  ==============================  ================  ================

  (Configuration-shaped surfaces ride ``workflow_write`` -- the
  admin-only configuration write, as the core workflow registry
  does; quantity-shaped records ride ``usage_write``, as the
  core metering records do; money-shaped records ride
  ``usage_write`` too, as the first unit's payments do.)

- All ``*_ref`` parameters naming things outside this build are
  opaque tokens: whitespace, URLs, hostnames, and IP-shaped
  values are rejected at the boundary, so a record cannot
  quietly carry a real system's address (sensor references
  included -- nothing here can hold a sensor endpoint). Links
  into the core substrate use core ids (``proj-``, ``per-``,
  ``org-``, ``ast-``, ``wo-``), validated through the core
  store.
- One derivation is stated as a named seam.
  ``_current_reported_status``: the latest-reported-status
  derivation shared by reservations, visitor registrations,
  leases, and moves -- the batch unit's fresh negative control
  mutates it (see tests/README.md).
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


_IP_LIKE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# -- option sets -------------------------------------------------------

RESERVATION_KINDS = ("desk", "room", "resource", "other")
RESERVATION_REPORTED_STATUSES = (
    "reported_reserved",
    "reported_checked_in",
    "reported_completed",
    "reported_cancelled",
    "reported_no_show",
)
VISITOR_REPORTED_STATUSES = (
    "reported_registered",
    "reported_checked_in",
    "reported_checked_out",
    "reported_cancelled",
    "reported_no_show",
)
EVENT_KINDS = ("setup", "visit", "meeting", "program", "other")
SIGNAGE_KINDS = ("room", "lobby", "desk", "directory", "other")
SENSOR_KINDS = ("occupancy", "environmental", "utilization", "other")
FEED_REPORTED_STATUSES = (
    "reported_connected",
    "reported_disconnected",
    "reported_degraded",
)
ANALYTICS_METRICS = (
    "reservation_count",
    "active_reservation_count",
    "visitor_registration_count",
    "checkin_count",
    "notice_count",
    "requisition_count",
    "purchase_total_cents",
    "utilization_report_count",
)
TRANSACTION_REPORTED_STATUSES = (
    "reported_proposed",
    "reported_under_review",
    "reported_approved",
    "reported_closed",
    "reported_withdrawn",
)
LEASE_REPORTED_STATUSES = (
    "reported_active",
    "reported_renewed",
    "reported_expired",
    "reported_terminated",
)
MOVE_REPORTED_STATUSES = (
    "reported_planned",
    "reported_in_progress",
    "reported_completed",
    "reported_cancelled",
)
PURCHASE_REPORTED_STATUSES = (
    "reported_paid",
    "reported_failed",
    "reported_refunded",
)

# -- validation helpers --------------------------------------------------


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_ref(value, what):
    """Validate an opaque reference token.

    A reference names a thing in the caller's own world; it is
    never an address and never an identifier issued by a real
    system. Whitespace, URLs, hostnames, and IP-shaped values are
    rejected so records cannot carry a real system's location.
    """
    _validate_non_empty(value, what)
    if any(ch.isspace() for ch in value):
        raise ValidationError("%s must be an opaque reference (no spaces)" % (what,))
    if "://" in value or "/" in value or _IP_LIKE.match(value):
        raise ValidationError("%s must be an opaque reference, not an address" % (what,))
    if "." in value:
        raise ValidationError("%s must be an opaque reference, not a hostname" % (what,))
    if len(value) > 128:
        raise ValidationError("%s is too long for an opaque reference" % (what,))
    return value


def _validate_choice(value, options, what):
    if value not in options:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(options)))
    return value


def _validate_int(value, what, minimum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if minimum is not None and value < minimum:
        raise ValidationError("%s must be at least %d" % (what, minimum))
    return value


def _validate_optional_text(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string or None" % (what,))
    return value


def _parse_iso_datetime(value, what):
    """Parse an ISO-8601 datetime exactly as the core store does."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO-8601 datetime: %r" % (what, value)
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _validate_metric_values(metric_values, what="metric_values"):
    """Reported metric values held verbatim: an object mapping
    non-empty metric names to scalar reported values (string or
    integer). Floats and booleans are rejected -- a reported
    figure is a whole count or a label, and a float would
    pretend to a measured precision this substrate never
    performed."""
    if metric_values is None:
        return {}
    if not isinstance(metric_values, dict):
        raise ValidationError("%s must be an object" % (what,))
    if len(metric_values) > 50:
        raise ValidationError("%s may hold at most 50 entries" % (what,))
    cleaned = {}
    for key, value in metric_values.items():
        _validate_non_empty(key, "metric name")
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValidationError(
                "metric value for %r must be a string or integer "
                "reported verbatim" % (key,)
            )
        if isinstance(value, str) and not value.strip():
            raise ValidationError(
                "metric value for %r must be a non-empty string" % (key,)
            )
        cleaned[key] = value
    return cleaned


def _validate_zones(zones, what="zones"):
    """Floor-plan zone definitions held as data: a list of
    objects, each with a non-empty ``label`` and a non-empty
    ``kind``; labels must be unique within the plan. There is
    deliberately no coordinate or geometry field on the shape --
    a zone is a label, not a location."""
    if zones is None:
        return []
    if not isinstance(zones, list):
        raise ValidationError("%s must be a list of zone objects" % (what,))
    if len(zones) > 100:
        raise ValidationError("%s may hold at most 100 entries" % (what,))
    cleaned = []
    seen = set()
    for zone in zones:
        if not isinstance(zone, dict):
            raise ValidationError("each entry in %s must be an object" % (what,))
        _validate_non_empty(zone.get("label"), "zone label")
        _validate_non_empty(zone.get("kind"), "zone kind")
        extra = set(zone) - {"label", "kind"}
        if extra:
            raise ValidationError(
                "zone objects hold only label and kind -- no geometry "
                "keys are accepted: %s" % (", ".join(sorted(extra)),)
            )
        if zone["label"] in seen:
            raise ValidationError(
                "duplicate zone label in %s: %r" % (what, zone["label"])
            )
        seen.add(zone["label"])
        cleaned.append(copy.deepcopy(zone))
    return cleaned


def _validate_analytics_metrics(metrics, what="metrics"):
    """Analytics metric names: a list drawn from the fixed
    ANALYTICS_METRICS set; unknown names are refused at the
    boundary so no metric can be invented at write time."""
    if metrics is None:
        return []
    if not isinstance(metrics, list):
        raise ValidationError("%s must be a list of metric names" % (what,))
    cleaned = []
    for metric in metrics:
        _validate_choice(metric, ANALYTICS_METRICS, "metric")
        if metric not in cleaned:
            cleaned.append(metric)
    return cleaned


# -- derivation seam -----------------------------------------------------


def _current_reported_status(events, initial):
    """Latest-reported-status derivation.

    ``events`` is a list of outcome/status records in creation
    order, each carrying ``reported_status``; the current
    reported status is the LAST event's reported status, or
    ``initial`` when no event has been reported yet. This is the
    single derivation point behind the reservation, visitor,
    lease, and move current views; the batch unit's fresh
    negative control mutates it (see tests/README.md).
    """
    if not events:
        return initial
    return events[-1]["reported_status"]


class OpsExtensionsAddition:
    """Second-unit GAPS-batch extension surface over a core
    OpsStore: the remainder additions' 7 registered gap entries
    in records form (plus the labeled IoT reference stub)."""

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

        Mirrors the core store: an actor must be present;
        User-like actors are checked against the core permission
        matrix before anything changes; plain strings carry
        identity only.
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
            record["created_utc"] = _utc_now()
            record["updated_utc"] = record["created_utc"]
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            self._audit(actor, audit_action, record_id, details={"kind": kind})
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, collection, **filters):
        result = []
        for key in self._order:
            if key[0] != collection:
                continue
            record = self._records[key]
            if all(
                record.get(name) == value
                for name, value in filters.items()
                if value is not None
            ):
                result.append(copy.deepcopy(record))
        return result

    def _touch(self, record, actor, audit_action):
        record["updated_utc"] = _utc_now()
        self._audit(actor, audit_action, record["id"])

    # Core-record existence checks, read through the core store's
    # public API with no actor (internal reads; the caller's own
    # permission was already enforced by the guard).

    def _core_project(self, project_id):
        return self.store.get_project(project_id)

    def _core_person(self, person_id):
        return self.store.get_person(person_id)

    def _core_organization(self, organization_id):
        return self.store.get_organization(organization_id)

    def _core_asset(self, asset_id):
        return self.store.get_asset(asset_id)

    def _core_work_order(self, work_order_id):
        return self.store.get_work_order(work_order_id)

    # -- Workspace scheduling & reservation (records form) -----------
    # Records form: reservation request records over core
    # assets/projects/persons plus outcome records stored
    # exactly as reported by the external scheduling system.
    # The reservation's current reported status derives at read
    # from its latest outcome record; the stored record carries
    # no derived key and its own status field never changes.
    # Records, never booking execution (booked_here: False on
    # every record): this build reserves nothing.

    def create_reservation(self, name, actor, kind="room",
                           asset_id=None, project_id=None,
                           person_id=None, starts_at=None,
                           ends_at=None, note=None):
        """Create a reservation request record.

        Action: work_write. ``kind`` is one of desk/room/
        resource/other. The optional asset/project/person links
        must be core records. ``starts_at``/``ends_at``, when
        given, are ISO-8601 datetimes and the end must follow
        the start. The record reserves nothing
        (``booked_here: False``).
        """
        self._guard(actor, "work_write", "exta_reservation_create", name)
        _validate_non_empty(name, "reservation name")
        _validate_choice(kind, RESERVATION_KINDS, "kind")
        if asset_id is not None:
            self._core_asset(asset_id)
        if project_id is not None:
            self._core_project(project_id)
        if person_id is not None:
            self._core_person(person_id)
        if starts_at is not None:
            _parse_iso_datetime(starts_at, "starts_at")
        if ends_at is not None:
            _parse_iso_datetime(ends_at, "ends_at")
        if starts_at is not None and ends_at is not None:
            if _parse_iso_datetime(ends_at, "ends_at") <= _parse_iso_datetime(
                starts_at, "starts_at"
            ):
                raise ValidationError("ends_at must follow starts_at")
        _validate_optional_text(note, "note")
        return self._create(
            "reservation", "rsv",
            {
                "name": name,
                "kind": kind,
                "asset_id": asset_id,
                "project_id": project_id,
                "person_id": person_id,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "note": note,
                "status": "recorded",
                "booked_here": False,
            },
            actor, "exta_reservation_create",
        )

    def record_reservation_outcome(self, reservation_id, reported_status,
                                   actor, note=None):
        """Record a reservation outcome **as reported by the
        external scheduling system**. Action: work_write. The
        outcome is stored as reported; this build executed no
        booking and verifies none."""
        self._guard(actor, "work_write", "exta_reservation_outcome",
                    reservation_id)
        self._get("reservation", reservation_id)
        _validate_choice(reported_status, RESERVATION_REPORTED_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "reservation_outcome", "rso",
            {
                "reservation_id": reservation_id,
                "reported_status": reported_status,
                "note": note,
                "booked_here": False,
            },
            actor, "exta_reservation_outcome",
        )

    def get_reservation(self, reservation_id, actor=None):
        """Read one reservation record. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_reservation_read",
                         reservation_id)
        return self._fetch("reservation", reservation_id)

    def list_reservations(self, actor=None, asset_id=None, project_id=None,
                          kind=None):
        """List reservation records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_reservation_read")
        return self._list("reservation", asset_id=asset_id,
                          project_id=project_id, kind=kind)

    def list_reservation_outcomes(self, actor=None, reservation_id=None):
        """List reservation-outcome records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_reservation_read")
        return self._list("reservation_outcome",
                          reservation_id=reservation_id)

    def reservation_view(self, reservation_id, actor=None):
        """One reservation record plus its derived
        ``current_reported_status``: the reported status of its
        latest outcome record, or ``"recorded"`` when no outcome
        has been reported. Derived at read via the seam
        ``_current_reported_status``, never stored.
        Action: work_read."""
        self._guard_read(actor, "work_read", "exta_reservation_read",
                         reservation_id)
        view = self._fetch("reservation", reservation_id)
        outcomes = self._list("reservation_outcome",
                              reservation_id=reservation_id)
        view["current_reported_status"] = _current_reported_status(
            outcomes, "recorded"
        )
        return view

    # -- Visitor & event management ----------------------------------
    # Records form: visitor registration records keyed by an
    # opaque visitor reference (no real identity can be stored,
    # per PLATFORM-LAYER.md decision 1) plus handling-event
    # records stored exactly as reported. A registration's
    # current reported state derives at read from its latest
    # handling event; nothing is admitted, badged, or escorted
    # here (admitted_here: False).

    def register_visitor(self, visitor_ref, actor, host_person_id=None,
                         project_id=None, note=None):
        """Register a visitor record. Action: work_write.
        ``visitor_ref`` is an opaque reference supplied by the
        embedding organization's own visitor process -- never a
        name, credential, or real identifier. The optional host
        must be a core directory person."""
        self._guard(actor, "work_write", "exta_visitor_register", visitor_ref)
        _validate_ref(visitor_ref, "visitor_ref")
        if host_person_id is not None:
            self._core_person(host_person_id)
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(note, "note")
        return self._create(
            "visitor_registration", "vis",
            {
                "visitor_ref": visitor_ref,
                "host_person_id": host_person_id,
                "project_id": project_id,
                "note": note,
                "status": "recorded",
                "admitted_here": False,
            },
            actor, "exta_visitor_register",
        )

    def record_visitor_event(self, registration_id, reported_status, actor,
                             note=None):
        """Record a visitor handling event **as reported** by
        the embedding organization's visitor process. Action:
        work_write. Stored verbatim; this build admitted no
        one."""
        self._guard(actor, "work_write", "exta_visitor_event", registration_id)
        self._get("visitor_registration", registration_id)
        _validate_choice(reported_status, VISITOR_REPORTED_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "visitor_event", "vie",
            {
                "registration_id": registration_id,
                "reported_status": reported_status,
                "note": note,
                "admitted_here": False,
            },
            actor, "exta_visitor_event",
        )

    def get_visitor_registration(self, registration_id, actor=None):
        """Read one visitor registration. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_visitor_read",
                         registration_id)
        return self._fetch("visitor_registration", registration_id)

    def list_visitor_registrations(self, actor=None, host_person_id=None,
                                   project_id=None):
        """List visitor registrations. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_visitor_read")
        return self._list("visitor_registration",
                          host_person_id=host_person_id,
                          project_id=project_id)

    def list_visitor_events(self, actor=None, registration_id=None):
        """List visitor handling events. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_visitor_read")
        return self._list("visitor_event", registration_id=registration_id)

    def visitor_view(self, registration_id, actor=None):
        """One visitor registration plus its derived
        ``current_reported_status`` (latest handling event's
        reported status, or ``"recorded"``). Derived at read,
        never stored. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_visitor_read",
                         registration_id)
        view = self._fetch("visitor_registration", registration_id)
        events = self._list("visitor_event", registration_id=registration_id)
        view["current_reported_status"] = _current_reported_status(
            events, "recorded"
        )
        return view

    # -- Event definitions & check-ins (records form) -----------------
    # Records form: event definitions held as data (nothing is
    # staged or run here) and check-in records against a
    # definition or a visitor registration -- a headcount
    # record, not an admission (admitted_here: False).

    def create_event_definition(self, name, actor, kind="program",
                                project_id=None, description=None):
        """Create an event definition record. Action:
        workflow_write (configuration, as the core workflow
        registry). The definition is data only."""
        self._guard(actor, "workflow_write", "exta_event_create", name)
        _validate_non_empty(name, "event name")
        _validate_choice(kind, EVENT_KINDS, "kind")
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(description, "description")
        return self._create(
            "event_definition", "evt",
            {
                "name": name,
                "kind": kind,
                "project_id": project_id,
                "description": description,
                "version": 1,
                "staged_here": False,
            },
            actor, "exta_event_create",
        )

    def update_event_definition(self, event_id, actor, description=None):
        """Replace an event definition's description, bumping
        its version. Action: workflow_write."""
        self._guard(actor, "workflow_write", "exta_event_update", event_id)
        record = self._get("event_definition", event_id)
        _validate_optional_text(description, "description")
        with self._lock:
            if description is not None:
                record["description"] = description
            record["version"] += 1
            self._touch(record, actor, "exta_event_update")
            return copy.deepcopy(record)

    def get_event_definition(self, event_id, actor=None):
        """Read one event definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_event_read", event_id)
        return self._fetch("event_definition", event_id)

    def list_event_definitions(self, actor=None, project_id=None, kind=None):
        """List event definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_event_read")
        return self._list("event_definition", project_id=project_id,
                          kind=kind)

    def record_event_checkin(self, event_id, actor, registration_id=None,
                             person_id=None, note=None):
        """Record an event check-in. Action: work_write. The
        check-in names either a visitor registration or a core
        directory person (or neither, for an unregistered
        attendee counted only). A check-in record is a
        headcount record; it admits no one."""
        self._guard(actor, "work_write", "exta_event_checkin", event_id)
        self._get("event_definition", event_id)
        if registration_id is not None:
            self._get("visitor_registration", registration_id)
        if person_id is not None:
            self._core_person(person_id)
        _validate_optional_text(note, "note")
        return self._create(
            "event_checkin", "eck",
            {
                "event_id": event_id,
                "registration_id": registration_id,
                "person_id": person_id,
                "note": note,
                "admitted_here": False,
            },
            actor, "exta_event_checkin",
        )

    def list_event_checkins(self, actor=None, event_id=None):
        """List event check-in records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_event_checkin_read")
        return self._list("event_checkin", event_id=event_id)

    # -- Interactive floor plans, wayfinding & signage (records form) -
    # Records form: floor-plan definitions whose zones are held
    # verbatim as data (each an object with a non-empty ``label``
    # and ``kind``) -- there is deliberately no coordinate or
    # geometry field anywhere in this module, so a plan record
    # cannot be a map; signage definitions as data; and digital
    # notice records carrying text verbatim as data. Nothing is
    # rendered, displayed, published, or routed
    # (rendered_here/displayed_here/published_here/routed_here
    # all False). Colleague location is not here: no record in
    # this module can hold a person's location.

    def create_floor_plan_definition(self, name, actor, zones=None,
                                     project_id=None, description=None):
        """Create a floor-plan definition record. Action:
        workflow_write. ``zones`` are held verbatim as data;
        each must be an object with a non-empty ``label`` and
        ``kind``, and labels must be unique. The definition is
        data only -- no geometry exists on the shape."""
        self._guard(actor, "workflow_write", "exta_floorplan_create", name)
        _validate_non_empty(name, "floor plan name")
        zones = _validate_zones(zones)
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(description, "description")
        return self._create(
            "floor_plan_definition", "flp",
            {
                "name": name,
                "zones": zones,
                "project_id": project_id,
                "description": description,
                "version": 1,
                "rendered_here": False,
            },
            actor, "exta_floorplan_create",
        )

    def update_floor_plan_definition(self, plan_id, actor, zones=None,
                                     description=None):
        """Replace a floor-plan definition's zones and/or
        description, bumping its version. Action:
        workflow_write."""
        self._guard(actor, "workflow_write", "exta_floorplan_update", plan_id)
        record = self._get("floor_plan_definition", plan_id)
        cleaned = None
        if zones is not None:
            cleaned = _validate_zones(zones)
        _validate_optional_text(description, "description")
        with self._lock:
            if cleaned is not None:
                record["zones"] = cleaned
            if description is not None:
                record["description"] = description
            record["version"] += 1
            self._touch(record, actor, "exta_floorplan_update")
            return copy.deepcopy(record)

    def get_floor_plan_definition(self, plan_id, actor=None):
        """Read one floor-plan definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_floorplan_read",
                         plan_id)
        return self._fetch("floor_plan_definition", plan_id)

    def list_floor_plan_definitions(self, actor=None, project_id=None):
        """List floor-plan definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_floorplan_read")
        return self._list("floor_plan_definition", project_id=project_id)

    def create_signage_definition(self, name, actor, kind="room",
                                  plan_id=None, zone_label=None,
                                  content_text=None):
        """Create a signage definition record. Action:
        workflow_write. ``content_text`` is held verbatim as
        data; nothing is displayed. The optional plan link must
        be a floor-plan definition of this surface, and
        ``zone_label``, when both are given, must name a zone
        the plan defines."""
        self._guard(actor, "workflow_write", "exta_signage_create", name)
        _validate_non_empty(name, "signage name")
        _validate_choice(kind, SIGNAGE_KINDS, "kind")
        plan = None
        if plan_id is not None:
            plan = self._get("floor_plan_definition", plan_id)
        if zone_label is not None:
            _validate_non_empty(zone_label, "zone_label")
            if plan is not None and zone_label not in {
                zone["label"] for zone in plan["zones"]
            }:
                raise ValidationError(
                    "zone_label %r is not a zone of floor plan %r"
                    % (zone_label, plan_id)
                )
        _validate_optional_text(content_text, "content_text")
        return self._create(
            "signage_definition", "sgn",
            {
                "name": name,
                "kind": kind,
                "plan_id": plan_id,
                "zone_label": zone_label,
                "content_text": content_text,
                "version": 1,
                "displayed_here": False,
            },
            actor, "exta_signage_create",
        )

    def update_signage_definition(self, signage_id, actor, content_text=None):
        """Replace a signage definition's content text, bumping
        its version. Action: workflow_write. Updating the data
        displays nothing."""
        self._guard(actor, "workflow_write", "exta_signage_update",
                    signage_id)
        record = self._get("signage_definition", signage_id)
        _validate_optional_text(content_text, "content_text")
        with self._lock:
            if content_text is not None:
                record["content_text"] = content_text
            record["version"] += 1
            self._touch(record, actor, "exta_signage_update")
            return copy.deepcopy(record)

    def get_signage_definition(self, signage_id, actor=None):
        """Read one signage definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_signage_read",
                         signage_id)
        return self._fetch("signage_definition", signage_id)

    def list_signage_definitions(self, actor=None, plan_id=None, kind=None):
        """List signage definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_signage_read")
        return self._list("signage_definition", plan_id=plan_id, kind=kind)

    def create_digital_notice(self, title, actor, body_text=None,
                              plan_id=None, zone_label=None):
        """Create a digital notice record. Action: work_write.
        ``body_text`` is held verbatim as data; nothing is
        published or displayed."""
        self._guard(actor, "work_write", "exta_notice_create", title)
        _validate_non_empty(title, "notice title")
        _validate_optional_text(body_text, "body_text")
        plan = None
        if plan_id is not None:
            plan = self._get("floor_plan_definition", plan_id)
        if zone_label is not None:
            _validate_non_empty(zone_label, "zone_label")
            if plan is not None and zone_label not in {
                zone["label"] for zone in plan["zones"]
            }:
                raise ValidationError(
                    "zone_label %r is not a zone of floor plan %r"
                    % (zone_label, plan_id)
                )
        return self._create(
            "digital_notice", "ntc",
            {
                "title": title,
                "body_text": body_text,
                "plan_id": plan_id,
                "zone_label": zone_label,
                "published_here": False,
                "displayed_here": False,
            },
            actor, "exta_notice_create",
        )

    def get_digital_notice(self, notice_id, actor=None):
        """Read one digital notice. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_notice_read", notice_id)
        return self._fetch("digital_notice", notice_id)

    def list_digital_notices(self, actor=None, plan_id=None):
        """List digital notices. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_notice_read")
        return self._list("digital_notice", plan_id=plan_id)

    def wayfinding_view(self, plan_id, actor=None):
        """One floor-plan definition plus derived counts of the
        signage definitions and digital notices recorded
        against it. Counts only, derived at read, never stored;
        nothing is routed (``routed_here: False``).
        Action: report_read."""
        self._guard_read(actor, "report_read", "exta_wayfinding_view", plan_id)
        view = self._fetch("floor_plan_definition", plan_id)
        view["signage_count"] = len(
            self._list("signage_definition", plan_id=plan_id)
        )
        view["notice_count"] = len(
            self._list("digital_notice", plan_id=plan_id)
        )
        view["routed_here"] = False
        return view

    # -- IoT sensor integration & sensing (reference stub) ------------
    # Labeled reference implementation: sensor reference
    # records, feed reference records, and reported reading
    # batches. Every record carries reference_stub: True (feed
    # records additionally reference_transport: True),
    # received_here: False, and sensed_here: False. Nothing is
    # received from, connected to, or measured on any physical
    # sensor; a reading batch is a caller's report, and its
    # utilization figures are stored verbatim as reported.

    def register_sensor_reference(self, sensor_ref, kind, actor,
                                  asset_id=None, note=None):
        """Register a reference record of an IoT sensor.
        Action: work_write. ``sensor_ref`` is an opaque
        reference -- never an endpoint or a device address.
        Carries ``reference_stub: True``; the sensor it names
        lives outside this build and is not connected here."""
        self._guard(actor, "work_write", "exta_sensor_reference", sensor_ref)
        _validate_ref(sensor_ref, "sensor_ref")
        _validate_choice(kind, SENSOR_KINDS, "kind")
        if asset_id is not None:
            self._core_asset(asset_id)
        _validate_optional_text(note, "note")
        return self._create(
            "sensor_reference", "sen",
            {
                "sensor_ref": sensor_ref,
                "kind": kind,
                "asset_id": asset_id,
                "note": note,
                "reference_stub": True,
                "received_here": False,
                "sensed_here": False,
            },
            actor, "exta_sensor_reference",
        )

    def record_sensor_feed_reference(self, sensor_id, reported_status, actor,
                                     note=None):
        """Record the reported state of a sensor feed **as
        reported** by the external system. Action: work_write.
        Carries ``reference_stub: True`` and
        ``reference_transport: True``; no data moved through
        this build."""
        self._guard(actor, "work_write", "exta_sensor_feed", sensor_id)
        self._get("sensor_reference", sensor_id)
        _validate_choice(reported_status, FEED_REPORTED_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "sensor_feed_reference", "sfd",
            {
                "sensor_id": sensor_id,
                "reported_status": reported_status,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "received_here": False,
                "sensed_here": False,
            },
            actor, "exta_sensor_feed",
        )

    def record_utilization_report(self, sensor_id, actor, metric_values=None,
                                  reported_at=None, note=None):
        """Record a batch of utilization figures **as reported**
        for a sensor. Action: usage_write (a quantity-shaped
        report, as the core metering records are).
        ``metric_values`` are stored verbatim; nothing here
        measured them."""
        self._guard(actor, "usage_write", "exta_utilization_report", sensor_id)
        self._get("sensor_reference", sensor_id)
        metric_values = _validate_metric_values(metric_values)
        if reported_at is not None:
            _parse_iso_datetime(reported_at, "reported_at")
        _validate_optional_text(note, "note")
        return self._create(
            "utilization_report", "utl",
            {
                "sensor_id": sensor_id,
                "metric_values": metric_values,
                "reported_at": reported_at,
                "note": note,
                "reference_stub": True,
                "received_here": False,
                "sensed_here": False,
            },
            actor, "exta_utilization_report",
        )

    def get_sensor_reference(self, sensor_id, actor=None):
        """Read one sensor reference record. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_sensor_read", sensor_id)
        return self._fetch("sensor_reference", sensor_id)

    def list_sensor_references(self, actor=None, kind=None, asset_id=None):
        """List sensor reference records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_sensor_read")
        return self._list("sensor_reference", kind=kind, asset_id=asset_id)

    def list_sensor_feed_references(self, actor=None, sensor_id=None):
        """List sensor feed reference records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_sensor_read")
        return self._list("sensor_feed_reference", sensor_id=sensor_id)

    def list_utilization_reports(self, actor=None, sensor_id=None):
        """List reported utilization batches. Action: usage_read."""
        self._guard_read(actor, "usage_read", "exta_utilization_read")
        return self._list("utilization_report", sensor_id=sensor_id)

    def utilization_view(self, sensor_id, actor=None):
        """One sensor reference plus derived counts: feed
        records, reported batches, and the latest reported feed
        status (or ``"unreported"``). Counts and the reported
        status only, derived at read, never stored; nothing is
        sensed here. Action: usage_read."""
        self._guard_read(actor, "usage_read", "exta_utilization_read",
                         sensor_id)
        view = self._fetch("sensor_reference", sensor_id)
        feeds = self._list("sensor_feed_reference", sensor_id=sensor_id)
        view["feed_count"] = len(feeds)
        view["report_count"] = len(
            self._list("utilization_report", sensor_id=sensor_id)
        )
        view["latest_reported_feed_status"] = _current_reported_status(
            feeds, "unreported"
        )
        return view

    # -- Workplace analytics & optimization (records form) ------------
    # Records form, mirroring the first unit's reporting: metric
    # definitions held as data over a fixed metric set of counts
    # and sums over THIS substrate's own recorded values, and run
    # records that store no figures -- a run's figures derive at
    # read. No new metric is invented: in particular no
    # utilization rate, trend, or optimization output is
    # derivable from the metric set (optimized_here: False).

    def create_analytics_definition(self, name, actor, metrics=None,
                                    project_id=None, description=None):
        """Create a workplace-analytics definition record.
        Action: workflow_write. ``metrics`` must name metrics
        from the fixed set (unknown names are refused at the
        boundary); the definition is data only."""
        self._guard(actor, "workflow_write", "exta_analytics_create", name)
        _validate_non_empty(name, "analytics definition name")
        metrics = _validate_analytics_metrics(metrics)
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(description, "description")
        return self._create(
            "analytics_definition", "anl",
            {
                "name": name,
                "metrics": metrics,
                "project_id": project_id,
                "description": description,
                "version": 1,
                "optimized_here": False,
            },
            actor, "exta_analytics_create",
        )

    def update_analytics_definition(self, definition_id, actor, metrics=None,
                                    description=None):
        """Replace an analytics definition's metrics and/or
        description, bumping its version. Action:
        workflow_write."""
        self._guard(actor, "workflow_write", "exta_analytics_update",
                    definition_id)
        record = self._get("analytics_definition", definition_id)
        cleaned = None
        if metrics is not None:
            cleaned = _validate_analytics_metrics(metrics)
        _validate_optional_text(description, "description")
        with self._lock:
            if cleaned is not None:
                record["metrics"] = cleaned
            if description is not None:
                record["description"] = description
            record["version"] += 1
            self._touch(record, actor, "exta_analytics_update")
            return copy.deepcopy(record)

    def get_analytics_definition(self, definition_id, actor=None):
        """Read one analytics definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_analytics_read",
                         definition_id)
        return self._fetch("analytics_definition", definition_id)

    def list_analytics_definitions(self, actor=None, project_id=None):
        """List analytics definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_analytics_read")
        return self._list("analytics_definition", project_id=project_id)

    def record_analytics_run(self, definition_id, actor, note=None):
        """Record that an analytics run was recorded against a
        definition. Action: work_write. **The run record stores
        no figures** (pinned by test); figures exist only
        derived at read in :meth:`analytics_run_view`."""
        self._guard(actor, "work_write", "exta_analytics_run", definition_id)
        self._get("analytics_definition", definition_id)
        _validate_optional_text(note, "note")
        return self._create(
            "analytics_run", "anr",
            {
                "definition_id": definition_id,
                "note": note,
                "optimized_here": False,
            },
            actor, "exta_analytics_run",
        )

    def list_analytics_runs(self, actor=None, definition_id=None):
        """List analytics run records (no figures on them).
        Action: report_read."""
        self._guard_read(actor, "report_read", "exta_analytics_run_read")
        return self._list("analytics_run", definition_id=definition_id)

    def _analytics_figures(self, definition):
        """Derive a definition's figures from this substrate's
        own records: counts and the sum of recorded purchase
        cents only. Scoped to the definition's project when it
        names one (unscoped families count whole; utilization
        batches are sensor-scoped and count whole)."""
        project_id = definition["project_id"]
        reservations = self._list("reservation", project_id=project_id)
        active = [
            r for r in reservations
            if self.reservation_view(r["id"])["current_reported_status"]
            in ("reported_reserved", "reported_checked_in")
        ]
        purchases = self._list("purchase_record", project_id=project_id)
        return {
            "reservation_count": len(reservations),
            "active_reservation_count": len(active),
            "visitor_registration_count": len(
                self._list("visitor_registration", project_id=project_id)
            ),
            "checkin_count": len(self._list("event_checkin")),
            "notice_count": len(self._list("digital_notice")),
            "requisition_count": len(
                self._list("requisition", project_id=project_id)
            ),
            "purchase_total_cents": sum(
                p["amount_cents"] for p in purchases
            ),
            "utilization_report_count": len(self._list("utilization_report")),
        }

    def analytics_run_view(self, run_id, actor=None):
        """One analytics run record plus its derived figures:
        exactly the definition's metrics, computed at read from
        this substrate's own records (counts and a sum of
        recorded cents only). Derived, never stored.
        Action: report_read."""
        self._guard_read(actor, "report_read", "exta_analytics_run_read",
                         run_id)
        view = self._fetch("analytics_run", run_id)
        definition = self._get("analytics_definition", view["definition_id"])
        figures = self._analytics_figures(definition)
        view["figures"] = {
            metric: figures[metric] for metric in definition["metrics"]
        }
        return view

    # -- Procurement marketplace & requisitioning (records form) ------
    # Records form: catalog listing records over core vendor
    # organizations (a listing is a record of an offering, not a
    # storefront -- ordered_here: False), requisition records
    # optionally bound to a core work order and/or listing
    # (records of a request, never an order --
    # ordered_here: False), and purchase records over
    # integer-cent amounts with verbatim reported outcomes
    # (records, never execution -- paid_here: False). Contract
    # utilization is counted, never directed: no preferred-source
    # or direction field exists on any shape, and the summary is
    # counts and sums of recorded values only.

    def create_catalog_listing(self, name, actor, organization_id=None,
                               vendor_ref=None, project_id=None, note=None):
        """Create a catalog listing record. Action: asset_write
        (a catalog/inventory-shaped record, as the core asset
        records are). The optional organization must be a core
        directory organization (the vendor); ``vendor_ref`` is
        an alternative opaque vendor reference. A listing
        record sells nothing."""
        self._guard(actor, "asset_write", "exta_listing_create", name)
        _validate_non_empty(name, "listing name")
        if organization_id is not None:
            self._core_organization(organization_id)
        if vendor_ref is not None:
            _validate_ref(vendor_ref, "vendor_ref")
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(note, "note")
        return self._create(
            "catalog_listing", "lst",
            {
                "name": name,
                "organization_id": organization_id,
                "vendor_ref": vendor_ref,
                "project_id": project_id,
                "note": note,
                "ordered_here": False,
            },
            actor, "exta_listing_create",
        )

    def get_catalog_listing(self, listing_id, actor=None):
        """Read one catalog listing. Action: asset_read."""
        self._guard_read(actor, "asset_read", "exta_listing_read", listing_id)
        return self._fetch("catalog_listing", listing_id)

    def list_catalog_listings(self, actor=None, organization_id=None,
                              project_id=None):
        """List catalog listings. Action: asset_read."""
        self._guard_read(actor, "asset_read", "exta_listing_read")
        return self._list("catalog_listing", organization_id=organization_id,
                          project_id=project_id)

    def create_requisition(self, subject, actor, project_id=None,
                           work_order_id=None, listing_id=None,
                           requester_ref=None, note=None):
        """Create a requisition record. Action: work_write.
        The optional work order must be a core work order and
        the optional listing a catalog listing of this surface.
        A requisition record orders nothing."""
        self._guard(actor, "work_write", "exta_requisition_create", subject)
        _validate_non_empty(subject, "requisition subject")
        if project_id is not None:
            self._core_project(project_id)
        if work_order_id is not None:
            self._core_work_order(work_order_id)
        if listing_id is not None:
            self._get("catalog_listing", listing_id)
        if requester_ref is not None:
            _validate_ref(requester_ref, "requester_ref")
        _validate_optional_text(note, "note")
        return self._create(
            "requisition", "req",
            {
                "subject": subject,
                "project_id": project_id,
                "work_order_id": work_order_id,
                "listing_id": listing_id,
                "requester_ref": requester_ref,
                "note": note,
                "status": "recorded",
                "ordered_here": False,
            },
            actor, "exta_requisition_create",
        )

    def get_requisition(self, requisition_id, actor=None):
        """Read one requisition record. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_requisition_read",
                         requisition_id)
        return self._fetch("requisition", requisition_id)

    def list_requisitions(self, actor=None, project_id=None,
                          work_order_id=None, listing_id=None):
        """List requisition records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_requisition_read")
        return self._list("requisition", project_id=project_id,
                          work_order_id=work_order_id, listing_id=listing_id)

    def record_purchase(self, actor, amount_cents, requisition_id=None,
                        listing_id=None, project_id=None, payer_ref=None,
                        note=None):
        """Record a purchase of ``amount_cents`` integer cents.

        Action: usage_write (a money-shaped record, as the
        first unit's payments are). The amount must be an
        int >= 1; floats and booleans are rejected. Recording
        a purchase moves no money.
        """
        self._guard(actor, "usage_write", "exta_purchase_record")
        _validate_int(amount_cents, "amount_cents", minimum=1)
        if requisition_id is not None:
            self._get("requisition", requisition_id)
        if listing_id is not None:
            self._get("catalog_listing", listing_id)
        if project_id is not None:
            self._core_project(project_id)
        if payer_ref is not None:
            _validate_ref(payer_ref, "payer_ref")
        _validate_optional_text(note, "note")
        return self._create(
            "purchase_record", "pur",
            {
                "amount_cents": amount_cents,
                "requisition_id": requisition_id,
                "listing_id": listing_id,
                "project_id": project_id,
                "payer_ref": payer_ref,
                "note": note,
                "status": "recorded",
                "paid_here": False,
            },
            actor, "exta_purchase_record",
        )

    def record_purchase_outcome(self, purchase_id, reported_status, actor,
                                note=None):
        """Record a purchase outcome **as reported by the
        external payment system**. Action: usage_write. Stored
        as reported; this build executed no payment."""
        self._guard(actor, "usage_write", "exta_purchase_outcome", purchase_id)
        self._get("purchase_record", purchase_id)
        _validate_choice(reported_status, PURCHASE_REPORTED_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "purchase_outcome", "puo",
            {
                "purchase_id": purchase_id,
                "reported_status": reported_status,
                "note": note,
                "paid_here": False,
            },
            actor, "exta_purchase_outcome",
        )

    def get_purchase(self, purchase_id, actor=None):
        """Read one purchase record. Action: usage_read."""
        self._guard_read(actor, "usage_read", "exta_purchase_read", purchase_id)
        return self._fetch("purchase_record", purchase_id)

    def list_purchases(self, actor=None, project_id=None, requisition_id=None):
        """List purchase records. Action: usage_read."""
        self._guard_read(actor, "usage_read", "exta_purchase_read")
        return self._list("purchase_record", project_id=project_id,
                          requisition_id=requisition_id)

    def list_purchase_outcomes(self, actor=None, purchase_id=None):
        """List purchase-outcome records. Action: usage_read."""
        self._guard_read(actor, "usage_read", "exta_purchase_read")
        return self._list("purchase_outcome", purchase_id=purchase_id)

    def purchase_view(self, purchase_id, actor=None):
        """One purchase record plus its derived
        ``current_reported_status`` (latest outcome's reported
        status, or ``"recorded"``). Derived at read, never
        stored. Action: usage_read."""
        self._guard_read(actor, "usage_read", "exta_purchase_read", purchase_id)
        view = self._fetch("purchase_record", purchase_id)
        outcomes = self._list("purchase_outcome", purchase_id=purchase_id)
        view["current_reported_status"] = _current_reported_status(
            outcomes, "recorded"
        )
        return view

    def procurement_summary(self, actor=None):
        """Derived procurement counts and sums: listings,
        requisitions, purchases, the sum of recorded purchase
        cents, purchase outcomes by reported status, and
        requisitions per listing -- counts of recorded linkages
        only (utilization is counted, never directed:
        ``directed_here: False``). Derived at read, never
        stored. Action: report_read."""
        self._guard_read(actor, "report_read", "exta_procurement_summary")
        purchases = self._list("purchase_record")
        outcomes = self._list("purchase_outcome")
        by_reported_status = {}
        for outcome in outcomes:
            key = outcome["reported_status"]
            by_reported_status[key] = by_reported_status.get(key, 0) + 1
        per_listing = {}
        for requisition in self._list("requisition"):
            if requisition["listing_id"] is not None:
                key = requisition["listing_id"]
                per_listing[key] = per_listing.get(key, 0) + 1
        return {
            "listings": len(self._list("catalog_listing")),
            "requisitions": len(self._list("requisition")),
            "purchases": len(purchases),
            "total_recorded_cents": sum(
                p["amount_cents"] for p in purchases
            ),
            "outcomes": len(outcomes),
            "outcomes_by_reported_status": by_reported_status,
            "requisitions_by_listing": per_listing,
            "paid_here": False,
            "directed_here": False,
        }

    # -- Real-estate portfolio suite (records form) -------------------
    # Records form (Tango catalogue excess): space records over
    # core assets/projects; space-plan definitions held as data
    # over those spaces (the registry never executes them); move
    # records whose current reported
    # status derives at read; lease records over integer-cent
    # amounts with obligation-event records -- a lease's total
    # obligation and current reported status derive at read,
    # and nothing is signed, enforced, or posted to any
    # accounting ledger (signed_here/accounted_here: False);
    # transaction records with verbatim reported lifecycle
    # labels; and predictive-analytics records whose figures are
    # stored verbatim as reported by an external engine --
    # nothing is predicted here (predicted_here: False).

    def create_portfolio_space(self, name, actor, kind="office",
                                 asset_id=None, project_id=None, note=None):
        """Create a portfolio space record. Action: asset_write.
        The optional asset/project links must be core records."""
        self._guard(actor, "asset_write", "exta_space_create", name)
        _validate_non_empty(name, "space name")
        _validate_non_empty(kind, "kind")
        if asset_id is not None:
            self._core_asset(asset_id)
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(note, "note")
        return self._create(
            "portfolio_space", "spc",
            {
                "name": name,
                "kind": kind,
                "asset_id": asset_id,
                "project_id": project_id,
                "note": note,
            },
            actor, "exta_space_create",
        )

    def get_portfolio_space(self, space_id, actor=None):
        """Read one portfolio space. Action: asset_read."""
        self._guard_read(actor, "asset_read", "exta_space_read", space_id)
        return self._fetch("portfolio_space", space_id)

    def list_portfolio_spaces(self, actor=None, asset_id=None, project_id=None):
        """List portfolio spaces. Action: asset_read."""
        self._guard_read(actor, "asset_read", "exta_space_read")
        return self._list("portfolio_space", asset_id=asset_id,
                          project_id=project_id)

    def create_space_plan_definition(self, name, actor, space_ids=None,
                                     note=None):
        """Create a space-plan definition, held as data. Action:
        workflow_write. ``space_ids`` are portfolio spaces of
        this surface, validated at write time. The registry
        never executes: a plan definition moves no one and
        changes no space."""
        self._guard(actor, "workflow_write", "exta_spaceplan_create", name)
        _validate_non_empty(name, "plan name")
        space_ids = self._validate_space_ids(space_ids)
        _validate_optional_text(note, "note")
        return self._create(
            "space_plan", "spl",
            {
                "name": name,
                "space_ids": space_ids,
                "note": note,
                "version": 1,
                "executed_here": False,
            },
            actor, "exta_spaceplan_create",
        )

    def _validate_space_ids(self, space_ids):
        if space_ids is None:
            return []
        if not isinstance(space_ids, list):
            raise ValidationError("space_ids must be a list of space ids")
        cleaned = []
        for space_id in space_ids:
            self._get("portfolio_space", space_id)
            if space_id not in cleaned:
                cleaned.append(space_id)
        return cleaned

    def update_space_plan_definition(self, plan_id, actor, name=None,
                                     space_ids=None, note=None):
        """Update a space-plan definition; bumps ``version``.
        Action: workflow_write."""
        self._guard(actor, "workflow_write", "exta_spaceplan_update", plan_id)
        record = self._get("space_plan", plan_id)
        if name is not None:
            _validate_non_empty(name, "plan name")
        if space_ids is not None:
            space_ids = self._validate_space_ids(space_ids)
        if note is not None:
            _validate_optional_text(note, "note")
        with self._lock:
            if name is not None:
                record["name"] = name
            if space_ids is not None:
                record["space_ids"] = space_ids
            if note is not None:
                record["note"] = note
            record["version"] += 1
            self._touch(record, actor, "exta_spaceplan_update")
            return copy.deepcopy(record)

    def get_space_plan_definition(self, plan_id, actor=None):
        """Read one space-plan definition. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_spaceplan_read",
                         plan_id)
        return self._fetch("space_plan", plan_id)

    def list_space_plan_definitions(self, actor=None):
        """List space-plan definitions. Action: workflow_read."""
        self._guard_read(actor, "workflow_read", "exta_spaceplan_read")
        return self._list("space_plan")

    def create_move_record(self, subject, actor, from_space_id=None,
                           to_space_id=None, project_id=None, note=None):
        """Create a move record. Action: work_write. The
        optional spaces must be portfolio spaces of this
        surface. A move record moves nothing."""
        self._guard(actor, "work_write", "exta_move_create", subject)
        _validate_non_empty(subject, "move subject")
        if from_space_id is not None:
            self._get("portfolio_space", from_space_id)
        if to_space_id is not None:
            self._get("portfolio_space", to_space_id)
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(note, "note")
        return self._create(
            "move_record", "mov",
            {
                "subject": subject,
                "from_space_id": from_space_id,
                "to_space_id": to_space_id,
                "project_id": project_id,
                "note": note,
                "status": "recorded",
                "moved_here": False,
            },
            actor, "exta_move_create",
        )

    def record_move_outcome(self, move_id, reported_status, actor, note=None):
        """Record a move outcome **as reported**. Action:
        work_write. Stored verbatim; this build moved no one."""
        self._guard(actor, "work_write", "exta_move_outcome", move_id)
        self._get("move_record", move_id)
        _validate_choice(reported_status, MOVE_REPORTED_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "move_outcome", "mvo",
            {
                "move_id": move_id,
                "reported_status": reported_status,
                "note": note,
                "moved_here": False,
            },
            actor, "exta_move_outcome",
        )

    def get_move_record(self, move_id, actor=None):
        """Read one move record. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_move_read", move_id)
        return self._fetch("move_record", move_id)

    def list_move_records(self, actor=None, project_id=None):
        """List move records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_move_read")
        return self._list("move_record", project_id=project_id)

    def list_move_outcomes(self, actor=None, move_id=None):
        """List move-outcome records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_move_read")
        return self._list("move_outcome", move_id=move_id)

    def move_view(self, move_id, actor=None):
        """One move record plus its derived
        ``current_reported_status`` (latest outcome's reported
        status, or ``"recorded"``). Derived at read, never
        stored. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_move_read", move_id)
        view = self._fetch("move_record", move_id)
        outcomes = self._list("move_outcome", move_id=move_id)
        view["current_reported_status"] = _current_reported_status(
            outcomes, "recorded"
        )
        return view

    def create_lease_record(self, name, actor, amount_cents=None,
                            term_months=None, counterparty_ref=None,
                            space_id=None, project_id=None, starts_on=None,
                            note=None):
        """Create a lease administration record. Action:
        work_write. ``amount_cents``/``term_months``, when
        given, are integers (amount >= 1, term >= 1); floats
        and booleans are rejected. ``counterparty_ref`` is an
        opaque reference. A lease record signs nothing and
        posts nothing to any ledger."""
        self._guard(actor, "work_write", "exta_lease_create", name)
        _validate_non_empty(name, "lease name")
        if amount_cents is not None:
            _validate_int(amount_cents, "amount_cents", minimum=1)
        if term_months is not None:
            _validate_int(term_months, "term_months", minimum=1)
        if counterparty_ref is not None:
            _validate_ref(counterparty_ref, "counterparty_ref")
        if space_id is not None:
            self._get("portfolio_space", space_id)
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(starts_on, "starts_on")
        _validate_optional_text(note, "note")
        return self._create(
            "lease_record", "lea",
            {
                "name": name,
                "amount_cents": amount_cents,
                "term_months": term_months,
                "counterparty_ref": counterparty_ref,
                "space_id": space_id,
                "project_id": project_id,
                "starts_on": starts_on,
                "note": note,
                "status": "recorded",
                "signed_here": False,
                "accounted_here": False,
            },
            actor, "exta_lease_create",
        )

    def record_lease_event(self, lease_id, reported_status, actor, note=None):
        """Record a lease obligation event **as reported**.
        Action: work_write. Stored verbatim; this build signed
        and enforced nothing."""
        self._guard(actor, "work_write", "exta_lease_event", lease_id)
        self._get("lease_record", lease_id)
        _validate_choice(reported_status, LEASE_REPORTED_STATUSES,
                         "reported_status")
        _validate_optional_text(note, "note")
        return self._create(
            "lease_event", "lee",
            {
                "lease_id": lease_id,
                "reported_status": reported_status,
                "note": note,
                "signed_here": False,
                "accounted_here": False,
            },
            actor, "exta_lease_event",
        )

    def get_lease_record(self, lease_id, actor=None):
        """Read one lease record. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_lease_read", lease_id)
        return self._fetch("lease_record", lease_id)

    def list_lease_records(self, actor=None, space_id=None, project_id=None):
        """List lease records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_lease_read")
        return self._list("lease_record", space_id=space_id,
                          project_id=project_id)

    def list_lease_events(self, actor=None, lease_id=None):
        """List lease-event records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_lease_read")
        return self._list("lease_event", lease_id=lease_id)

    def lease_view(self, lease_id, actor=None):
        """One lease record plus derived values: its
        ``current_reported_status`` (latest event's reported
        status, or ``"recorded"``) and its
        ``derived_total_obligation_cents`` -- the recorded
        amount times the recorded term, an arithmetic product
        of two recorded integers, derived at read and never
        stored (``None`` when either is unrecorded). No
        amortization schedule, present value, or ASC 842
        classification is computed anywhere. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_lease_read", lease_id)
        view = self._fetch("lease_record", lease_id)
        events = self._list("lease_event", lease_id=lease_id)
        view["current_reported_status"] = _current_reported_status(
            events, "recorded"
        )
        if view["amount_cents"] is not None and view["term_months"] is not None:
            view["derived_total_obligation_cents"] = (
                view["amount_cents"] * view["term_months"]
            )
        else:
            view["derived_total_obligation_cents"] = None
        return view

    def record_transaction(self, subject, actor, reported_status,
                           space_id=None, project_id=None,
                           amount_cents=None, note=None):
        """Record a portfolio transaction with its lifecycle
        status **as reported**. Action: work_write.
        ``amount_cents``, when given, is an integer >= 1.
        This build closed no transaction."""
        self._guard(actor, "work_write", "exta_transaction_record", subject)
        _validate_non_empty(subject, "transaction subject")
        _validate_choice(reported_status, TRANSACTION_REPORTED_STATUSES,
                         "reported_status")
        if space_id is not None:
            self._get("portfolio_space", space_id)
        if project_id is not None:
            self._core_project(project_id)
        if amount_cents is not None:
            _validate_int(amount_cents, "amount_cents", minimum=1)
        _validate_optional_text(note, "note")
        return self._create(
            "transaction_record", "txn",
            {
                "subject": subject,
                "reported_status": reported_status,
                "space_id": space_id,
                "project_id": project_id,
                "amount_cents": amount_cents,
                "note": note,
                "closed_here": False,
            },
            actor, "exta_transaction_record",
        )

    def get_transaction(self, transaction_id, actor=None):
        """Read one transaction record. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_transaction_read",
                         transaction_id)
        return self._fetch("transaction_record", transaction_id)

    def list_transactions(self, actor=None, space_id=None, project_id=None,
                          reported_status=None):
        """List transaction records. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_transaction_read")
        return self._list("transaction_record", space_id=space_id,
                          project_id=project_id,
                          reported_status=reported_status)

    def record_prediction_report(self, subject, actor, metric_values=None,
                                 model_ref=None, space_id=None,
                                 project_id=None, note=None):
        """Record a predictive-analytics report **as reported
        by an external engine**. Action: work_write.
        ``metric_values`` are stored verbatim; the optional
        ``model_ref`` names the external model as an opaque
        reference. Nothing here predicts anything
        (``predicted_here: False``)."""
        self._guard(actor, "work_write", "exta_prediction_record", subject)
        _validate_non_empty(subject, "prediction subject")
        metric_values = _validate_metric_values(metric_values)
        if model_ref is not None:
            _validate_ref(model_ref, "model_ref")
        if space_id is not None:
            self._get("portfolio_space", space_id)
        if project_id is not None:
            self._core_project(project_id)
        _validate_optional_text(note, "note")
        return self._create(
            "prediction_report", "prd",
            {
                "subject": subject,
                "metric_values": metric_values,
                "model_ref": model_ref,
                "space_id": space_id,
                "project_id": project_id,
                "note": note,
                "predicted_here": False,
            },
            actor, "exta_prediction_record",
        )

    def get_prediction_report(self, report_id, actor=None):
        """Read one prediction report. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_prediction_read", report_id)
        return self._fetch("prediction_report", report_id)

    def list_prediction_reports(self, actor=None, space_id=None,
                                project_id=None):
        """List prediction reports. Action: work_read."""
        self._guard_read(actor, "work_read", "exta_prediction_read")
        return self._list("prediction_report", space_id=space_id,
                          project_id=project_id)

    def portfolio_summary(self, actor=None):
        """Derived portfolio counts: spaces, moves, leases,
        transactions by reported status, and prediction reports.
        Counts of recorded values only; nothing is predicted,
        signed, or accounted here. Derived at read, never
        stored. Action: report_read."""
        self._guard_read(actor, "report_read", "exta_portfolio_summary")
        transactions = self._list("transaction_record")
        by_reported_status = {}
        for txn in transactions:
            key = txn["reported_status"]
            by_reported_status[key] = by_reported_status.get(key, 0) + 1
        return {
            "spaces": len(self._list("portfolio_space")),
            "space_plans": len(self._list("space_plan")),
            "moves": len(self._list("move_record")),
            "leases": len(self._list("lease_record")),
            "transactions": len(transactions),
            "transactions_by_reported_status": by_reported_status,
            "prediction_reports": len(self._list("prediction_report")),
            "predicted_here": False,
            "signed_here": False,
            "accounted_here": False,
        }
