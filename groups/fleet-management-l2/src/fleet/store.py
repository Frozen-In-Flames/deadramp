"""Fleet-management records store: vehicle & asset registry, operator
records (opaque references only), reservation & assignment records
with a lifecycle and a no-second-active-reservation rule, check-in /
check-out activity records, usage & odometer records with a monotonic
sanity rule, maintenance & inspection records whose due status is
DERIVED at read (never stored), charging session records (integer
watt-hours), registry reporting, and search over the records.

Clean-room implementation. Records only: there is no telematics/GPS
streaming, no dispatch optimization, no ELD integration, no
forecasting engine, no live station communication, and no payment
processing in this substrate.

Permission convention: store methods take an ``actor``. When the
actor is a User-like object (it has a ``role`` attribute) the store
calls :func:`fleet.access.require` *before* any state change or id
allocation, so a denied operation consumes no id and changes
nothing, and the denied attempt is audited. Where a plain string is
passed it carries identity (for provenance) but no role, so there is
nothing to enforce against at this layer; the service layer, which
knows the role registry, is responsible for enforcement in that
case -- and it always passes User objects.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type: ``veh-``, ``opr-``, ``res-``, ``chk-``, ``use-``,
``mnt-``, ``chg-``.
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

VEHICLE_STATUSES = ("active", "retired")
CREDENTIAL_STATUSES = ("active", "suspended", "revoked", "expired")
CHECKIN_KINDS = ("check_out", "check_in")
MAINTENANCE_KINDS = ("maintenance", "inspection")

RESERVATION_TRANSITIONS = {
    "reserved": {"checked_out", "cancelled"},
    "checked_out": {"returned"},
    "returned": set(),
    "cancelled": set(),
}
ACTIVE_RESERVATION_STATUSES = ("reserved", "checked_out")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _today():
    return datetime.now(timezone.utc).date()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_odometer(value, what="odometer"):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a non-negative integer" % (what,))
    if value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _parse_moment(value, what):
    """Parse an ISO date or datetime string for ordering checks."""
    _validate_non_empty(value, what)
    text = value.strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    try:
        parsed_date = date.fromisoformat(text)
    except ValueError:
        raise ValidationError("%s must be an ISO date or datetime string" % (what,))
    return datetime(parsed_date.year, parsed_date.month, parsed_date.day)


def _parse_date(value, what):
    """Parse a strict ISO date (YYYY-MM-DD) string to a date object."""
    _validate_non_empty(value, what)
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValidationError("%s must be an ISO date (YYYY-MM-DD)" % (what,))


def _coerce_as_of(as_of):
    """Coerce an as_of argument (None / date / datetime / ISO string) to a date."""
    if as_of is None:
        return _today()
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    return _parse_date(as_of, "as_of")


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class FleetStore:
    """In-memory store for the fleet-management records service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._vehicles = {}
        self._operators = {}
        self._reservations = {}
        self._checkins = {}
        self._usage = {}
        self._maintenance = {}
        self._charging_sessions = {}
        self._counters = {
            "veh": 0, "opr": 0, "res": 0, "chk": 0,
            "use": 0, "mnt": 0, "chg": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _enforce(self, actor, action, target):
        """Enforce for a User actor; audit the denied attempt, then raise."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit(actor, "%s:denied" % (action,), target)
                raise

    def _require_actor(self, actor, action, target):
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
        self._enforce(actor, action, target)

    def _maybe_require(self, actor, action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, action)

    def _get_vehicle_record(self, vehicle_id):
        rec = self._vehicles.get(vehicle_id)
        if rec is None:
            raise NotFoundError("vehicle not found: %r" % (vehicle_id,))
        return rec

    def _get_operator_record(self, operator_id):
        rec = self._operators.get(operator_id)
        if rec is None:
            raise NotFoundError("operator not found: %r" % (operator_id,))
        return rec

    def _get_reservation_record(self, reservation_id):
        rec = self._reservations.get(reservation_id)
        if rec is None:
            raise NotFoundError("reservation not found: %r" % (reservation_id,))
        return rec

    def _get_maintenance_record(self, maintenance_id):
        rec = self._maintenance.get(maintenance_id)
        if rec is None:
            raise NotFoundError("maintenance record not found: %r" % (maintenance_id,))
        return rec

    def _get_charging_record(self, session_id):
        rec = self._charging_sessions.get(session_id)
        if rec is None:
            raise NotFoundError("charging session not found: %r" % (session_id,))
        return rec

    # -- vehicles ------------------------------------------------------

    def create_vehicle(self, label, vehicle_type, actor, status="active"):
        """Create a vehicle registry entry. Action: write."""
        self._require_actor(actor, "write", label if isinstance(label, str) else "vehicle")
        _validate_non_empty(label, "vehicle label")
        _validate_non_empty(vehicle_type, "vehicle_type")
        if status not in VEHICLE_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(VEHICLE_STATUSES),))
        with self._lock:
            vehicle_id = self._next_id("veh")
            record = {
                "id": vehicle_id,
                "label": label,
                "vehicle_type": vehicle_type,
                "status": status,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._vehicles[vehicle_id] = record
            self._audit(actor, "vehicle_create", vehicle_id, details={"label": label})
            return dict(record)

    def get_vehicle(self, vehicle_id, actor=None):
        """Return one vehicle. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            return dict(self._get_vehicle_record(vehicle_id))

    def list_vehicles(self, actor=None):
        """Return vehicles sorted by id. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            records = sorted(self._vehicles.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- operators -------------------------------------------------------

    def create_operator(self, operator_ref, credential_kind, actor, credential_status="active"):
        """Create an operator record keyed by an OPAQUE reference. Action: write.

        Privacy discipline: the record carries ONLY an opaque
        caller-supplied reference, a credential kind, and a credential
        status. There are no fields that can hold a real name, a
        license number, or any other PII.
        """
        self._require_actor(actor, "write", operator_ref if isinstance(operator_ref, str) else "operator")
        _validate_non_empty(operator_ref, "operator_ref")
        _validate_non_empty(credential_kind, "credential_kind")
        if credential_status not in CREDENTIAL_STATUSES:
            raise ValidationError(
                "credential_status must be one of %s" % (", ".join(CREDENTIAL_STATUSES),))
        with self._lock:
            operator_id = self._next_id("opr")
            record = {
                "id": operator_id,
                "operator_ref": operator_ref,
                "credential_kind": credential_kind,
                "credential_status": credential_status,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._operators[operator_id] = record
            self._audit(actor, "operator_create", operator_id, details={"operator_ref": operator_ref})
            return dict(record)

    def get_operator(self, operator_id, actor=None):
        """Return one operator record. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            return dict(self._get_operator_record(operator_id))

    def list_operators(self, actor=None):
        """Return operator records sorted by id. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            records = sorted(self._operators.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- reservations ----------------------------------------------------

    def create_reservation(self, vehicle_id, operator_ref, start, end, actor):
        """Create a reservation & assignment record. Action: write.

        Lifecycle starts at ``reserved``. Overlap rule (implemented
        rule, stated in the README): a vehicle with an active
        reservation (status ``reserved`` or ``checked_out``) cannot be
        reserved again at all -- a second active reservation for the
        same vehicle is a ValidationError, regardless of the window.
        """
        self._require_actor(actor, "write", vehicle_id)
        _validate_non_empty(operator_ref, "operator_ref")
        start_moment = _parse_moment(start, "start")
        end_moment = _parse_moment(end, "end")
        if not end_moment > start_moment:
            raise ValidationError("end must be after start")
        with self._lock:
            self._get_vehicle_record(vehicle_id)
            for existing in self._reservations.values():
                if (existing["vehicle_id"] == vehicle_id
                        and existing["status"] in ACTIVE_RESERVATION_STATUSES):
                    raise ValidationError(
                        "vehicle %r already has an active reservation %r"
                        % (vehicle_id, existing["id"]))
            reservation_id = self._next_id("res")
            record = {
                "id": reservation_id,
                "vehicle_id": vehicle_id,
                "operator_ref": operator_ref,
                "start": start,
                "end": end,
                "status": "reserved",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reservations[reservation_id] = record
            self._audit(actor, "reservation_create", reservation_id,
                        details={"vehicle_id": vehicle_id, "operator_ref": operator_ref})
            return dict(record)

    def get_reservation(self, reservation_id, actor=None):
        """Return one reservation. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            return dict(self._get_reservation_record(reservation_id))

    def list_reservations(self, vehicle_id=None, status=None, actor=None):
        """Return reservations, optionally filtered. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            records = sorted(self._reservations.values(), key=lambda r: _id_num(r["id"]))
            if vehicle_id is not None:
                records = [r for r in records if r["vehicle_id"] == vehicle_id]
            if status is not None:
                records = [r for r in records if r["status"] == status]
            return [dict(r) for r in records]

    def set_reservation_status(self, reservation_id, status, actor):
        """Transition a reservation status. Action: write.

        Lifecycle ONLY: reserved->{checked_out, cancelled},
        checked_out->{returned}; returned/cancelled are terminal.
        Any other transition (incl. same-state and unknown status) is
        a ValidationError, state unchanged.
        """
        self._require_actor(actor, "write", reservation_id)
        with self._lock:
            record = self._get_reservation_record(reservation_id)
            return dict(self._transition_reservation(record, status, actor))

    def _transition_reservation(self, record, status, actor):
        allowed = RESERVATION_TRANSITIONS.get(record["status"], set())
        if status not in allowed:
            raise ValidationError(
                "reservation status transition %r -> %r is not allowed"
                % (record["status"], status))
        record["status"] = status
        self._audit(actor, "reservation_set_status", record["id"], details={"status": status})
        return record

    # -- check-in / check-out ---------------------------------------------

    def record_checkin(self, reservation_id, kind, odometer, actor):
        """Record a check-in / check-out activity record. Action: write.

        Coherent design (documented in the README): the activity
        record DRIVES the reservation lifecycle. ``check_out`` is only
        valid from ``reserved`` and moves the reservation to
        ``checked_out``; ``check_in`` is only valid from
        ``checked_out`` and moves it to ``returned``. An activity that
        does not match the reservation state is a ValidationError and
        records nothing.
        """
        self._require_actor(actor, "write", reservation_id)
        if kind not in CHECKIN_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(CHECKIN_KINDS),))
        _validate_odometer(odometer)
        with self._lock:
            reservation = self._get_reservation_record(reservation_id)
            target_status = "checked_out" if kind == "check_out" else "returned"
            allowed = RESERVATION_TRANSITIONS.get(reservation["status"], set())
            if target_status not in allowed:
                raise ValidationError(
                    "%s is not allowed for a reservation in status %r"
                    % (kind, reservation["status"]))
            checkin_id = self._next_id("chk")
            record = {
                "id": checkin_id,
                "reservation_id": reservation_id,
                "kind": kind,
                "odometer": odometer,
                "recorded_utc": _utc_now(),
                "created_by": actor_name(actor),
            }
            self._checkins[checkin_id] = record
            self._transition_reservation(reservation, target_status, actor)
            self._audit(actor, "checkin_record", checkin_id,
                        details={"reservation_id": reservation_id, "kind": kind})
            return dict(record)

    def list_checkins(self, reservation_id=None, actor=None):
        """Return check-in / check-out records, optionally filtered. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            records = sorted(self._checkins.values(), key=lambda r: _id_num(r["id"]))
            if reservation_id is not None:
                records = [r for r in records if r["reservation_id"] == reservation_id]
            return [dict(r) for r in records]

    # -- usage & odometer ---------------------------------------------------

    def record_usage(self, vehicle_id, odometer_reading, actor):
        """Record a usage / odometer reading. Action: write.

        Monotonic sanity rule (stated in the README): a reading lower
        than the vehicle's latest recorded usage reading is a
        ValidationError and records nothing; an equal or higher
        reading is accepted.
        """
        self._require_actor(actor, "write", vehicle_id)
        _validate_odometer(odometer_reading, "odometer_reading")
        with self._lock:
            self._get_vehicle_record(vehicle_id)
            latest = self._latest_odometer(vehicle_id)
            if latest is not None and odometer_reading < latest:
                raise ValidationError(
                    "odometer_reading %r is lower than the latest recorded reading %r for vehicle %r"
                    % (odometer_reading, latest, vehicle_id))
            usage_id = self._next_id("use")
            record = {
                "id": usage_id,
                "vehicle_id": vehicle_id,
                "odometer_reading": odometer_reading,
                "recorded_utc": _utc_now(),
                "created_by": actor_name(actor),
            }
            self._usage[usage_id] = record
            self._audit(actor, "usage_record", usage_id,
                        details={"vehicle_id": vehicle_id, "odometer_reading": odometer_reading})
            return dict(record)

    def _latest_odometer(self, vehicle_id):
        readings = [r["odometer_reading"] for r in self._usage.values()
                    if r["vehicle_id"] == vehicle_id]
        return readings[-1] if readings else None

    def list_usage(self, vehicle_id=None, actor=None):
        """Return usage records, optionally filtered. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            records = sorted(self._usage.values(), key=lambda r: _id_num(r["id"]))
            if vehicle_id is not None:
                records = [r for r in records if r["vehicle_id"] == vehicle_id]
            return [dict(r) for r in records]

    # -- maintenance & inspection -------------------------------------------

    def _derive_due_status(self, record, as_of_date):
        """Derive a maintenance record's due status at read time.

        The stored record carries NO status field; the status exists
        only in the view returned by get/list:

        - ``completed`` if ``completed_date`` is set,
        - else ``overdue`` if ``as_of_date`` is after ``due_date``,
        - else ``current``.

        MUTATION DRILL NOTE: this derivation is the load-bearing
        invariant for the negative-control drill.
        """
        if record.get("completed_date"):
            return "completed"
        due = date.fromisoformat(record["due_date"])
        if as_of_date > due:
            return "overdue"
        return "current"

    def _maintenance_view(self, record, as_of_date):
        view = dict(record)
        view["derived_status"] = self._derive_due_status(record, as_of_date)
        return view

    def create_maintenance(self, vehicle_id, kind, due_date, actor):
        """Create a maintenance / inspection record. Action: write.

        The stored record has NO status field; due status is derived
        at read (see :meth:`_derive_due_status`).
        """
        self._require_actor(actor, "write", vehicle_id)
        if kind not in MAINTENANCE_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(MAINTENANCE_KINDS),))
        _parse_date(due_date, "due_date")
        with self._lock:
            self._get_vehicle_record(vehicle_id)
            maintenance_id = self._next_id("mnt")
            record = {
                "id": maintenance_id,
                "vehicle_id": vehicle_id,
                "kind": kind,
                "due_date": due_date,
                "completed_date": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._maintenance[maintenance_id] = record
            self._audit(actor, "maintenance_create", maintenance_id,
                        details={"vehicle_id": vehicle_id, "kind": kind, "due_date": due_date})
            return self._maintenance_view(record, _today())

    def get_maintenance(self, maintenance_id, actor=None, as_of=None):
        """Return one maintenance record as a view with derived_status. Action: read."""
        self._maybe_require(actor, "read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            return self._maintenance_view(self._get_maintenance_record(maintenance_id), as_of_date)

    def list_maintenance(self, vehicle_id=None, actor=None, as_of=None):
        """Return maintenance views with derived_status, optionally filtered. Action: read."""
        self._maybe_require(actor, "read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            records = sorted(self._maintenance.values(), key=lambda r: _id_num(r["id"]))
            if vehicle_id is not None:
                records = [r for r in records if r["vehicle_id"] == vehicle_id]
            return [self._maintenance_view(r, as_of_date) for r in records]

    def complete_maintenance(self, maintenance_id, actor, completed_date=None):
        """Record completion of a maintenance record. Action: write.

        Sets ``completed_date`` (the given ISO date, or today UTC).
        Completing an already-completed record is a ValidationError.
        """
        self._require_actor(actor, "write", maintenance_id)
        if completed_date is None:
            completed = _today().isoformat()
        else:
            completed = _parse_date(completed_date, "completed_date").isoformat()
        with self._lock:
            record = self._get_maintenance_record(maintenance_id)
            if record["completed_date"] is not None:
                raise ValidationError(
                    "maintenance record %r is already completed" % (maintenance_id,))
            record["completed_date"] = completed
            self._audit(actor, "maintenance_complete", maintenance_id,
                        details={"completed_date": completed})
            return self._maintenance_view(record, _today())

    # -- charging sessions ----------------------------------------------------

    def create_charging_session(self, station_ref, operator_ref, actor,
                                started_utc=None, watt_hours=0):
        """Create a charging session record. Action: write.

        Energy is recorded as INTEGER watt-hours (``watt_hours``) --
        never a float -- to avoid float ambiguity. ``station_ref`` and
        ``operator_ref`` are opaque caller-supplied references. The
        session is open (``ended_utc`` is None) until closed.
        """
        self._require_actor(actor, "write", station_ref if isinstance(station_ref, str) else "charging_session")
        _validate_non_empty(station_ref, "station_ref")
        _validate_non_empty(operator_ref, "operator_ref")
        if started_utc is not None:
            _validate_non_empty(started_utc, "started_utc")
        _validate_odometer(watt_hours, "watt_hours")
        with self._lock:
            session_id = self._next_id("chg")
            record = {
                "id": session_id,
                "station_ref": station_ref,
                "operator_ref": operator_ref,
                "started_utc": started_utc if started_utc is not None else _utc_now(),
                "ended_utc": None,
                "watt_hours": watt_hours,
                "created_by": actor_name(actor),
            }
            self._charging_sessions[session_id] = record
            self._audit(actor, "charging_session_create", session_id,
                        details={"station_ref": station_ref, "operator_ref": operator_ref})
            return dict(record)

    def close_charging_session(self, session_id, actor, ended_utc=None, watt_hours=None):
        """Close a charging session by recording its end. Action: write.

        Sets ``ended_utc`` (the given timestamp, or now UTC) and, when
        ``watt_hours`` is given, replaces the recorded integer
        watt-hours. Closing an already-closed session is a
        ValidationError.
        """
        self._require_actor(actor, "write", session_id)
        if ended_utc is not None:
            _validate_non_empty(ended_utc, "ended_utc")
        if watt_hours is not None:
            _validate_odometer(watt_hours, "watt_hours")
        with self._lock:
            record = self._get_charging_record(session_id)
            if record["ended_utc"] is not None:
                raise ValidationError("charging session %r is already closed" % (session_id,))
            record["ended_utc"] = ended_utc if ended_utc is not None else _utc_now()
            if watt_hours is not None:
                record["watt_hours"] = watt_hours
            self._audit(actor, "charging_session_close", session_id,
                        details={"ended_utc": record["ended_utc"], "watt_hours": record["watt_hours"]})
            return dict(record)

    def get_charging_session(self, session_id, actor=None):
        """Return one charging session. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            return dict(self._get_charging_record(session_id))

    def list_charging_sessions(self, actor=None):
        """Return charging sessions sorted by id. Action: read."""
        self._maybe_require(actor, "read")
        with self._lock:
            records = sorted(self._charging_sessions.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- reporting ---------------------------------------------------------------

    def summary_report(self, actor=None):
        """Registry reporting. Action: read.

        Counts per record set, the aggregate charging energy (integer
        watt-hours over all sessions), and a per-vehicle usage
        summary: latest recorded odometer, and the counts of usage,
        reservation, check-in, and maintenance records for the
        vehicle. Charging sessions key to station/operator references,
        not to vehicles, so their energy is reported in aggregate
        only. Registry reporting only -- no analytics engine.
        """
        self._maybe_require(actor, "read")
        with self._lock:
            vehicles = []
            for vehicle in sorted(self._vehicles.values(), key=lambda r: _id_num(r["id"])):
                vid = vehicle["id"]
                vehicle_reservations = [r for r in self._reservations.values()
                                        if r["vehicle_id"] == vid]
                reservation_ids = {r["id"] for r in vehicle_reservations}
                vehicles.append({
                    "vehicle_id": vid,
                    "label": vehicle["label"],
                    "latest_odometer": self._latest_odometer(vid),
                    "usage_records": len([r for r in self._usage.values()
                                          if r["vehicle_id"] == vid]),
                    "reservations": len(vehicle_reservations),
                    "checkins": len([r for r in self._checkins.values()
                                     if r["reservation_id"] in reservation_ids]),
                    "maintenance_records": len([r for r in self._maintenance.values()
                                                if r["vehicle_id"] == vid]),
                })
            return {
                "counts": {
                    "vehicles": len(self._vehicles),
                    "operators": len(self._operators),
                    "reservations": len(self._reservations),
                    "checkins": len(self._checkins),
                    "usage": len(self._usage),
                    "maintenance": len(self._maintenance),
                    "charging_sessions": len(self._charging_sessions),
                },
                "total_watt_hours": sum(r["watt_hours"] for r in self._charging_sessions.values()),
                "vehicles": vehicles,
            }

    # -- search -------------------------------------------------------------------

    def search(self, query, actor):
        """Search registry metadata. Action: search.

        Case-insensitive substring match over vehicle labels/types,
        operator references, reservation fields, maintenance kinds,
        and charging station/operator references. Empty query is a
        ValidationError.
        """
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for 'search'")
        if hasattr(actor, "role"):
            try:
                require(actor, "search")
            except PermissionDenied:
                self._audit(actor, "search:denied", query if isinstance(query, str) else "search")
                raise
        _validate_non_empty(query, "query")
        needle = query.strip().lower()
        with self._lock:
            vehicles = [dict(r) for r in sorted(self._vehicles.values(), key=lambda r: _id_num(r["id"]))
                        if needle in r["label"].lower() or needle in r["vehicle_type"].lower()
                        or needle in r["id"].lower()]
            operators = [dict(r) for r in sorted(self._operators.values(), key=lambda r: _id_num(r["id"]))
                         if needle in r["operator_ref"].lower()
                         or needle in r["credential_kind"].lower()]
            reservations = [dict(r) for r in sorted(self._reservations.values(), key=lambda r: _id_num(r["id"]))
                            if needle in r["vehicle_id"].lower() or needle in r["operator_ref"].lower()
                            or needle in r["status"].lower() or needle in r["id"].lower()]
            maintenance = [self._maintenance_view(r, _today())
                           for r in sorted(self._maintenance.values(), key=lambda r: _id_num(r["id"]))
                           if needle in r["vehicle_id"].lower() or needle in r["kind"].lower()
                           or needle in r["id"].lower()]
            charging_sessions = [dict(r) for r in sorted(self._charging_sessions.values(), key=lambda r: _id_num(r["id"]))
                                 if needle in r["station_ref"].lower() or needle in r["operator_ref"].lower()
                                 or needle in r["id"].lower()]
            return {
                "vehicles": vehicles,
                "operators": operators,
                "reservations": reservations,
                "maintenance": maintenance,
                "charging_sessions": charging_sessions,
            }
