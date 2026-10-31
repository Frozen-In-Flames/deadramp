"""Learning management records store: learner registry, course /
content catalog with lesson plans, events & registrations,
enrollment authorizations, individual development plans,
competencies, learner progress records, experience statements,
compliance assignments with derived status, workflows &
notifications, and reporting over the records.

Clean-room implementation. Records only: there is no content
delivery, no assessment scoring engine, and no workflow execution
engine in this substrate.

Permission convention (mirrors the communication group): store
methods take an ``actor``. When the actor is a User-like object (it
has a ``role`` attribute) the store calls
:func:`lms.access.require` for the method's action *before* any
state change or id allocation, so a denied operation consumes no id
and changes nothing. Where a plain string is passed it carries
identity (for provenance) but no role, so there is nothing to enforce
against at this layer; the service layer, which knows the role
registry, is responsible for enforcement in that case -- and it
always passes User objects.

Learner scope: a ``learner``-role actor may only read records whose
``learner_ref`` equals the actor's name; reading another learner's
record raises :class:`PermissionDenied`, and list methods return only
the learner's own records.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``lrn-``, ``crs-``, ``cnt-``,
``les-``, ``evt-``, ``reg-``, ``aut-``, ``idp-``, ``cpt-``, ``lcr-``,
``prg-``, ``stm-``, ``asg-``, ``wfl-``, ``ntf-``).

Compliance status and event seat counts are DERIVED at read time,
never stored: stored compliance records carry no ``status`` key and
stored event records carry no ``seats_taken`` / ``waitlist_count``
keys. Given an assignment, its due date, the learner's progress
records, and an explicit ``as_of`` reference date, the compliance
status is ``completed`` when a completed progress record exists for
the learner+course, ``overdue`` when ``as_of`` is after the due date,
and ``current`` otherwise. The derivation is deterministic in its
inputs; tests always pass an explicit ``as_of`` and never depend on
the wall clock.

The store records every successful mutation to its audit log (when
one is attached).
"""

import copy
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

COURSE_KINDS = ("course", "program")
CONTENT_STANDARDS = (
    "scorm_1_2", "scorm_2004", "aicc", "xapi", "cmi5",
    "mp3", "mp4", "pdf", "other",
)
EVENT_KINDS = ("live", "virtual")
REGISTRATION_STATES = ("registered", "waitlisted", "cancelled", "attended")
AUTHORIZATION_STATES = ("requested", "approved", "declined")
PROGRESS_STATUSES = ("not_started", "in_progress", "completed")
READINESS_LEVELS = ("not_ready", "developing", "ready")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role,
    so there is nothing to enforce against; enforcement for those
    happens in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _require_actor(actor, action):
    """For writes: an actor must be present, then _maybe_require."""
    if actor is None:
        raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    _maybe_require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_date(value, what):
    """Validate an ISO date string (YYYY-MM-DD); return a date object."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)" % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


def _coerce_as_of(as_of, what="as_of"):
    """Coerce an as_of reference (date, datetime, or ISO string) to a date.

    ``None`` means the current local date; deterministic callers
    (tests, compliance reads) always pass an explicit value.
    """
    if as_of is None:
        return date.today()
    if isinstance(as_of, datetime):
        return as_of.date()
    if isinstance(as_of, date):
        return as_of
    if isinstance(as_of, str):
        # Accept a full ISO datetime too; its date part governs.
        text = as_of.strip()
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass
        candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError as exc:
            raise ValidationError("%s is not a valid ISO date: %r" % (what, as_of)) from exc
    raise ValidationError("%s must be an ISO date string or date" % (what,))


def _parse_iso_datetime(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO-8601 datetime: %r" % (what, value)) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class LmsStore:
    """In-memory store for the learning management records service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._learners = {}
        self._courses = {}
        self._content_items = {}
        self._lesson_plans = {}
        self._events = {}
        self._registrations = {}
        self._authorizations = {}
        self._development_plans = {}
        self._competencies = {}
        self._learner_competencies = {}
        self._progress = {}
        self._statements = {}
        self._compliance = {}
        self._workflows = {}
        self._notifications = {}
        self._counters = {
            "lrn": 0, "crs": 0, "cnt": 0, "les": 0, "evt": 0,
            "reg": 0, "aut": 0, "idp": 0, "cpt": 0, "lcr": 0,
            "prg": 0, "stm": 0, "asg": 0, "wfl": 0, "ntf": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    @staticmethod
    def _is_learner(actor):
        return actor is not None and getattr(actor, "role", None) == "learner"

    def _scope_check(self, actor, learner_ref):
        """A learner-role actor may only touch their own records."""
        if self._is_learner(actor) and getattr(actor, "name", None) != learner_ref:
            raise PermissionDenied(
                "permission denied: learner %r may not access records of learner %r"
                % (getattr(actor, "name", None), learner_ref)
            )

    def _scoped(self, actor, records):
        """Filter learner-owned records to a learner actor's own."""
        if self._is_learner(actor):
            name = getattr(actor, "name", None)
            return [r for r in records if r.get("learner_ref") == name]
        return list(records)

    def _get_learner_record(self, learner_id):
        record = self._learners.get(learner_id)
        if record is None:
            raise NotFoundError("learner not found: %r" % (learner_id,))
        return record

    def _learner_by_ref(self, ref):
        for record in self._learners.values():
            if record["ref"] == ref:
                return record
        raise NotFoundError("learner not found: %r" % (ref,))

    def _get_course_record(self, course_id):
        course = self._courses.get(course_id)
        if course is None:
            raise NotFoundError("course not found: %r" % (course_id,))
        return course

    def _get_content_record(self, item_id):
        record = self._content_items.get(item_id)
        if record is None:
            raise NotFoundError("content item not found: %r" % (item_id,))
        return record

    def _get_lesson_plan_record(self, plan_id):
        record = self._lesson_plans.get(plan_id)
        if record is None:
            raise NotFoundError("lesson plan not found: %r" % (plan_id,))
        return record

    def _get_event_record(self, event_id):
        record = self._events.get(event_id)
        if record is None:
            raise NotFoundError("event not found: %r" % (event_id,))
        return record

    def _get_registration_record(self, registration_id):
        record = self._registrations.get(registration_id)
        if record is None:
            raise NotFoundError("registration not found: %r" % (registration_id,))
        return record

    def _get_authorization_record(self, authorization_id):
        record = self._authorizations.get(authorization_id)
        if record is None:
            raise NotFoundError("authorization not found: %r" % (authorization_id,))
        return record

    def _get_plan_record(self, plan_id):
        record = self._development_plans.get(plan_id)
        if record is None:
            raise NotFoundError("development plan not found: %r" % (plan_id,))
        return record

    def _get_competency_record(self, competency_id):
        record = self._competencies.get(competency_id)
        if record is None:
            raise NotFoundError("competency not found: %r" % (competency_id,))
        return record

    def _get_learner_competency_record(self, record_id):
        record = self._learner_competencies.get(record_id)
        if record is None:
            raise NotFoundError("learner competency not found: %r" % (record_id,))
        return record

    def _get_progress_record(self, progress_id):
        record = self._progress.get(progress_id)
        if record is None:
            raise NotFoundError("progress record not found: %r" % (progress_id,))
        return record

    def _get_statement_record(self, statement_id):
        record = self._statements.get(statement_id)
        if record is None:
            raise NotFoundError("statement not found: %r" % (statement_id,))
        return record

    def _get_compliance_record(self, assignment_id):
        record = self._compliance.get(assignment_id)
        if record is None:
            raise NotFoundError("compliance assignment not found: %r" % (assignment_id,))
        return record

    def _get_workflow_record(self, workflow_id):
        record = self._workflows.get(workflow_id)
        if record is None:
            raise NotFoundError("workflow not found: %r" % (workflow_id,))
        return record

    def _get_notification_record(self, notification_id):
        record = self._notifications.get(notification_id)
        if record is None:
            raise NotFoundError("notification not found: %r" % (notification_id,))
        return record

    @staticmethod
    def _copy_lesson_plan(record):
        copied = dict(record)
        copied["item_refs"] = list(record["item_refs"])
        return copied

    @staticmethod
    def _copy_plan(record):
        copied = dict(record)
        copied["activities"] = copy.deepcopy(record["activities"])
        return copied

    @staticmethod
    def _copy_workflow(record):
        copied = dict(record)
        copied["steps"] = list(record["steps"])
        return copied

    # -- learners ------------------------------------------------------

    def create_learner(self, ref, label, actor):
        """Create a learner registry entry. Action: learner_write.

        A duplicate ``ref`` is a validation error.
        """
        _require_actor(actor, "learner_write")
        _validate_non_empty(ref, "learner ref")
        _validate_non_empty(label, "learner label")
        with self._lock:
            for existing in self._learners.values():
                if existing["ref"] == ref:
                    raise ValidationError("learner ref %r already exists" % (ref,))
            learner_id = self._next_id("lrn")
            record = {
                "id": learner_id,
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._learners[learner_id] = record
            self._audit(actor, "learner_create", learner_id,
                        details={"ref": ref, "label": label})
            return dict(record)

    def get_learner(self, learner_id, actor=None):
        """Return one learner registry entry. Action: learner_read."""
        _maybe_require(actor, "learner_read")
        with self._lock:
            return dict(self._get_learner_record(learner_id))

    def list_learners(self, actor=None):
        """Return learner registry entries sorted by id. Action: learner_read."""
        _maybe_require(actor, "learner_read")
        with self._lock:
            learners = sorted(self._learners.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in learners]

    # -- catalog: courses, content items, lesson plans -----------------

    def create_course(self, title, actor, kind="course", code=None, description=""):
        """Create a course/program registry entry. Action: catalog_write."""
        _require_actor(actor, "catalog_write")
        _validate_non_empty(title, "course title")
        if kind not in COURSE_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(COURSE_KINDS),))
        if code is not None and not isinstance(code, str):
            raise ValidationError("code must be a string")
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        with self._lock:
            course_id = self._next_id("crs")
            course = {
                "id": course_id,
                "title": title,
                "kind": kind,
                "code": code,
                "description": description,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._courses[course_id] = course
            self._audit(actor, "course_create", course_id, details={"title": title, "kind": kind})
            return dict(course)

    def get_course(self, course_id, actor=None):
        """Return one registry entry. Action: catalog_read."""
        _maybe_require(actor, "catalog_read")
        with self._lock:
            return dict(self._get_course_record(course_id))

    def list_courses(self, actor=None):
        """Return registry entries sorted by id. Action: catalog_read."""
        _maybe_require(actor, "catalog_read")
        with self._lock:
            courses = sorted(self._courses.values(), key=lambda c: _id_num(c["id"]))
            return [dict(c) for c in courses]

    def create_content_item(self, title, standard, actor, course_id=None):
        """Create a content item record. Action: catalog_write."""
        _require_actor(actor, "catalog_write")
        _validate_non_empty(title, "content item title")
        if standard not in CONTENT_STANDARDS:
            raise ValidationError(
                "standard must be one of %s" % (", ".join(CONTENT_STANDARDS),)
            )
        with self._lock:
            if course_id is not None:
                self._get_course_record(course_id)
            item_id = self._next_id("cnt")
            record = {
                "id": item_id,
                "title": title,
                "standard": standard,
                "course_id": course_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._content_items[item_id] = record
            self._audit(actor, "content_create", item_id,
                        details={"title": title, "standard": standard, "course_id": course_id})
            return dict(record)

    def get_content_item(self, item_id, actor=None):
        """Return one content item. Action: catalog_read."""
        _maybe_require(actor, "catalog_read")
        with self._lock:
            return dict(self._get_content_record(item_id))

    def list_content_items(self, actor=None, course_id=None):
        """Return content items, optionally filtered. Action: catalog_read."""
        _maybe_require(actor, "catalog_read")
        with self._lock:
            records = list(self._content_items.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [dict(r) for r in records]

    def create_lesson_plan(self, title, course_id, actor, item_refs=None):
        """Create a lesson plan for a course. Action: catalog_write.

        Each entry of ``item_refs`` must resolve to an existing
        course or content item id.
        """
        _require_actor(actor, "catalog_write")
        _validate_non_empty(title, "lesson plan title")
        if item_refs is None:
            item_refs = []
        if not isinstance(item_refs, (list, tuple)):
            raise ValidationError("item_refs must be a list")
        item_refs = list(item_refs)
        with self._lock:
            self._get_course_record(course_id)
            for ref in item_refs:
                if ref not in self._courses and ref not in self._content_items:
                    raise NotFoundError("lesson plan item not found: %r" % (ref,))
            plan_id = self._next_id("les")
            record = {
                "id": plan_id,
                "title": title,
                "course_id": course_id,
                "item_refs": list(item_refs),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._lesson_plans[plan_id] = record
            self._audit(actor, "lesson_plan_create", plan_id,
                        details={"title": title, "course_id": course_id})
            return self._copy_lesson_plan(record)

    def get_lesson_plan(self, plan_id, actor=None):
        """Return one lesson plan. Action: catalog_read."""
        _maybe_require(actor, "catalog_read")
        with self._lock:
            return self._copy_lesson_plan(self._get_lesson_plan_record(plan_id))

    def list_lesson_plans(self, actor=None, course_id=None):
        """Return lesson plans, optionally filtered. Action: catalog_read."""
        _maybe_require(actor, "catalog_read")
        with self._lock:
            records = list(self._lesson_plans.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._copy_lesson_plan(r) for r in records]

    # -- events & registrations ------------------------------------------

    def create_event(self, title, starts_at, actor, course_id=None, ends_at=None,
                     kind="live", capacity=None, location=""):
        """Create an event record. Action: registration_write.

        No seat counts are stored: seats taken / waitlisted are
        derived at read time from the registration records (see
        :meth:`_event_view`).
        """
        _require_actor(actor, "registration_write")
        _validate_non_empty(title, "event title")
        if kind not in EVENT_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(EVENT_KINDS),))
        start_dt = _parse_iso_datetime(starts_at, "starts_at")
        end_dt = _parse_iso_datetime(ends_at, "ends_at") if ends_at is not None else None
        if end_dt is not None and end_dt < start_dt:
            raise ValidationError("ends_at must not be before starts_at")
        if capacity is not None:
            if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
                raise ValidationError("capacity must be a positive integer")
        if not isinstance(location, str):
            raise ValidationError("location must be a string")
        with self._lock:
            if course_id is not None:
                self._get_course_record(course_id)
            event_id = self._next_id("evt")
            record = {
                "id": event_id,
                "title": title,
                "course_id": course_id,
                "kind": kind,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "capacity": capacity,
                "location": location,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._events[event_id] = record
            self._audit(actor, "event_create", event_id,
                        details={"title": title, "course_id": course_id, "kind": kind})
            return dict(record)

    def _seats_taken(self, event_id):
        return sum(
            1 for r in self._registrations.values()
            if r["event_id"] == event_id and r["state"] == "registered"
        )

    def _waitlist_count(self, event_id):
        return sum(
            1 for r in self._registrations.values()
            if r["event_id"] == event_id and r["state"] == "waitlisted"
        )

    def _event_view(self, record):
        view = dict(record)
        seats_taken = self._seats_taken(record["id"])
        view["seats_taken"] = seats_taken
        view["waitlist_count"] = self._waitlist_count(record["id"])
        if record["capacity"] is None:
            view["seats_open"] = None
        else:
            view["seats_open"] = record["capacity"] - seats_taken
        return view

    def get_event(self, event_id, actor=None):
        """Return one event with derived seat counts. Action: registration_read."""
        _maybe_require(actor, "registration_read")
        with self._lock:
            return self._event_view(self._get_event_record(event_id))

    def list_events(self, actor=None, course_id=None):
        """Return events with derived seat counts. Action: registration_read."""
        _maybe_require(actor, "registration_read")
        with self._lock:
            records = list(self._events.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._event_view(r) for r in records]

    def register_learner(self, event_id, learner_ref, actor):
        """Register a learner for an event. Action: registration_write.

        The initial state is ``waitlisted`` when the event is at
        capacity, otherwise ``registered``. A duplicate active
        registration for the same event+learner is a validation error.
        """
        _require_actor(actor, "registration_write")
        _validate_non_empty(learner_ref, "learner_ref")
        with self._lock:
            self._learner_by_ref(learner_ref)
            event = self._get_event_record(event_id)
            for existing in self._registrations.values():
                if (
                    existing["event_id"] == event_id
                    and existing["learner_ref"] == learner_ref
                    and existing["state"] in ("registered", "waitlisted")
                ):
                    raise ValidationError(
                        "learner %r is already registered for event %r"
                        % (learner_ref, event_id)
                    )
            if event["capacity"] is not None and self._seats_taken(event_id) >= event["capacity"]:
                state = "waitlisted"
            else:
                state = "registered"
            registration_id = self._next_id("reg")
            record = {
                "id": registration_id,
                "event_id": event_id,
                "learner_ref": learner_ref,
                "state": state,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._registrations[registration_id] = record
            self._audit(actor, "registration_create", registration_id,
                        details={"event_id": event_id, "learner_ref": learner_ref,
                                 "state": state})
            return dict(record)

    def set_registration_state(self, registration_id, state, actor):
        """Set a registration's state. Action: registration_write."""
        _require_actor(actor, "registration_write")
        if state not in REGISTRATION_STATES:
            raise ValidationError(
                "state must be one of %s" % (", ".join(REGISTRATION_STATES),)
            )
        with self._lock:
            record = self._get_registration_record(registration_id)
            if state == "registered":
                event = self._get_event_record(record["event_id"])
                if event["capacity"] is not None:
                    seats_taken = self._seats_taken(record["event_id"])
                    if record["state"] == "registered":
                        seats_taken -= 1
                    if seats_taken >= event["capacity"]:
                        raise ValidationError(
                            "event %r is at capacity" % (record["event_id"],)
                        )
            record["state"] = state
            self._audit(actor, "registration_set_state", registration_id,
                        details={"state": state})
            return dict(record)

    def get_registration(self, registration_id, actor=None):
        """Return one registration. Action: registration_read (+ scope)."""
        _maybe_require(actor, "registration_read")
        with self._lock:
            record = self._get_registration_record(registration_id)
            self._scope_check(actor, record["learner_ref"])
            return dict(record)

    def list_registrations(self, actor=None, event_id=None, learner_ref=None):
        """Return registrations, optionally filtered. Action: registration_read."""
        _maybe_require(actor, "registration_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._registrations.values())
            if event_id is not None:
                records = [r for r in records if r["event_id"] == event_id]
            if learner_ref is not None:
                records = [r for r in records if r["learner_ref"] == learner_ref]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- authorizations ----------------------------------------------------

    def create_authorization(self, learner_ref, subject, actor, course_id=None,
                             event_id=None):
        """Create an authorization request. Action: authorization_write."""
        _require_actor(actor, "authorization_write")
        _validate_non_empty(learner_ref, "learner_ref")
        _validate_non_empty(subject, "subject")
        with self._lock:
            self._learner_by_ref(learner_ref)
            if course_id is not None:
                self._get_course_record(course_id)
            if event_id is not None:
                self._get_event_record(event_id)
            authorization_id = self._next_id("aut")
            record = {
                "id": authorization_id,
                "learner_ref": learner_ref,
                "subject": subject,
                "course_id": course_id,
                "event_id": event_id,
                "state": "requested",
                "decided_by": None,
                "decided_utc": None,
                "decision_note": "",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._authorizations[authorization_id] = record
            self._audit(actor, "authorization_create", authorization_id,
                        details={"learner_ref": learner_ref, "subject": subject})
            return dict(record)

    def decide_authorization(self, authorization_id, decision, actor, note=""):
        """Decide a requested authorization. Action: authorization_write.

        Separation of duties: the actor who created the request may
        not decide it.
        """
        _require_actor(actor, "authorization_write")
        if decision not in ("approved", "declined"):
            raise ValidationError("decision must be one of approved, declined")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            record = self._get_authorization_record(authorization_id)
            if record["state"] != "requested":
                raise ValidationError(
                    "authorization %r has already been decided" % (authorization_id,)
                )
            if actor_name(actor) == record["created_by"]:
                raise PermissionDenied(
                    "permission denied: the requester may not decide their own "
                    "authorization"
                )
            record["state"] = decision
            record["decided_by"] = actor_name(actor)
            record["decided_utc"] = _utc_now()
            record["decision_note"] = note
            self._audit(actor, "authorization_decide", authorization_id,
                        details={"decision": decision})
            return dict(record)

    def get_authorization(self, authorization_id, actor=None):
        """Return one authorization. Action: authorization_read (+ scope)."""
        _maybe_require(actor, "authorization_read")
        with self._lock:
            record = self._get_authorization_record(authorization_id)
            self._scope_check(actor, record["learner_ref"])
            return dict(record)

    def list_authorizations(self, actor=None, learner_ref=None):
        """Return authorizations, optionally filtered. Action: authorization_read."""
        _maybe_require(actor, "authorization_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._authorizations.values())
            if learner_ref is not None:
                records = [r for r in records if r["learner_ref"] == learner_ref]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- development plans ---------------------------------------------------

    def create_development_plan(self, learner_ref, goal, actor, target_date=None,
                                activities=None):
        """Create an individual development plan. Action: plan_write."""
        _require_actor(actor, "plan_write")
        _validate_non_empty(learner_ref, "learner_ref")
        _validate_non_empty(goal, "goal")
        if target_date is not None:
            _validate_date(target_date, "target_date")
        if activities is None:
            activities = []
        if not isinstance(activities, (list, tuple)):
            raise ValidationError("activities must be a list")
        activities = list(activities)
        for activity in activities:
            if not isinstance(activity, dict):
                raise ValidationError("each activity must be an object")
            _validate_non_empty(activity.get("activity"), "activity")
        with self._lock:
            self._learner_by_ref(learner_ref)
            for activity in activities:
                course_id = activity.get("course_id")
                if course_id is not None:
                    self._get_course_record(course_id)
            plan_id = self._next_id("idp")
            record = {
                "id": plan_id,
                "learner_ref": learner_ref,
                "goal": goal,
                "target_date": target_date,
                "activities": copy.deepcopy(activities),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._development_plans[plan_id] = record
            self._audit(actor, "plan_create", plan_id,
                        details={"learner_ref": learner_ref, "goal": goal})
            return self._copy_plan(record)

    def get_development_plan(self, plan_id, actor=None):
        """Return one development plan. Action: plan_read (+ scope)."""
        _maybe_require(actor, "plan_read")
        with self._lock:
            record = self._get_plan_record(plan_id)
            self._scope_check(actor, record["learner_ref"])
            return self._copy_plan(record)

    def list_development_plans(self, actor=None, learner_ref=None):
        """Return development plans, optionally filtered. Action: plan_read."""
        _maybe_require(actor, "plan_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._development_plans.values())
            if learner_ref is not None:
                records = [r for r in records if r["learner_ref"] == learner_ref]
            return [self._copy_plan(r) for r in self._scoped(actor, records)]

    # -- competencies ---------------------------------------------------------

    def create_competency(self, name, actor, description=""):
        """Create a competency definition. Action: competency_write."""
        _require_actor(actor, "competency_write")
        _validate_non_empty(name, "competency name")
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        with self._lock:
            competency_id = self._next_id("cpt")
            record = {
                "id": competency_id,
                "name": name,
                "description": description,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._competencies[competency_id] = record
            self._audit(actor, "competency_create", competency_id,
                        details={"name": name})
            return dict(record)

    def get_competency(self, competency_id, actor=None):
        """Return one competency definition. Action: competency_read."""
        _maybe_require(actor, "competency_read")
        with self._lock:
            return dict(self._get_competency_record(competency_id))

    def list_competencies(self, actor=None):
        """Return competency definitions. Action: competency_read."""
        _maybe_require(actor, "competency_read")
        with self._lock:
            return [dict(r) for r in self._competencies.values()]

    def record_learner_competency(self, learner_ref, competency_id, level, actor,
                                  note=""):
        """Record a learner's competency level verbatim.

        Action: competency_write. The level is a free-form record;
        it is never interpreted against a scale and never computed
        over.
        """
        _require_actor(actor, "competency_write")
        _validate_non_empty(learner_ref, "learner_ref")
        _validate_non_empty(level, "level")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            self._learner_by_ref(learner_ref)
            self._get_competency_record(competency_id)
            record_id = self._next_id("lcr")
            record = {
                "id": record_id,
                "learner_ref": learner_ref,
                "competency_id": competency_id,
                "level": level,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._learner_competencies[record_id] = record
            self._audit(actor, "learner_competency_record", record_id,
                        details={"learner_ref": learner_ref,
                                 "competency_id": competency_id, "level": level})
            return dict(record)

    def get_learner_competency(self, record_id, actor=None):
        """Return one learner competency record. Action: competency_read (+ scope)."""
        _maybe_require(actor, "competency_read")
        with self._lock:
            record = self._get_learner_competency_record(record_id)
            self._scope_check(actor, record["learner_ref"])
            return dict(record)

    def list_learner_competencies(self, actor=None, learner_ref=None,
                                  competency_id=None):
        """Return learner competency records. Action: competency_read."""
        _maybe_require(actor, "competency_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._learner_competencies.values())
            if learner_ref is not None:
                records = [r for r in records if r["learner_ref"] == learner_ref]
            if competency_id is not None:
                records = [r for r in records if r["competency_id"] == competency_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- learner progress & readiness records ----------------------------

    def record_progress(self, learner_ref, course_id, status, actor,
                        readiness=None, percent_complete=None, note=""):
        """Record a progress/readiness entry for a learner+course.

        Action: progress_write. ``completed`` is the terminal
        progress state and is what compliance derivation reads.
        """
        _require_actor(actor, "progress_write")
        _validate_non_empty(learner_ref, "learner_ref")
        if status not in PROGRESS_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(PROGRESS_STATUSES),))
        if readiness is not None and readiness not in READINESS_LEVELS:
            raise ValidationError("readiness must be one of %s" % (", ".join(READINESS_LEVELS),))
        if percent_complete is not None:
            if isinstance(percent_complete, bool) or not isinstance(percent_complete, (int, float)):
                raise ValidationError("percent_complete must be a number between 0 and 100")
            if not 0 <= percent_complete <= 100:
                raise ValidationError("percent_complete must be a number between 0 and 100")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            self._learner_by_ref(learner_ref)
            self._get_course_record(course_id)
            progress_id = self._next_id("prg")
            record = {
                "id": progress_id,
                "learner_ref": learner_ref,
                "course_id": course_id,
                "status": status,
                "readiness": readiness,
                "percent_complete": percent_complete,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._progress[progress_id] = record
            self._audit(actor, "progress_record", progress_id,
                        details={"learner_ref": learner_ref, "course_id": course_id,
                                 "status": status})
            return dict(record)

    def get_progress(self, progress_id, actor=None):
        """Return one progress record. Action: progress_read (+ scope)."""
        _maybe_require(actor, "progress_read")
        with self._lock:
            record = self._get_progress_record(progress_id)
            self._scope_check(actor, record["learner_ref"])
            return dict(record)

    def list_progress(self, actor=None, learner_ref=None, course_id=None):
        """Return progress records, optionally filtered. Action: progress_read."""
        _maybe_require(actor, "progress_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._progress.values())
            if learner_ref is not None:
                records = [r for r in records if r["learner_ref"] == learner_ref]
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def _has_completion(self, learner_ref, course_id):
        """True when a completed progress record exists for learner+course."""
        return any(
            r["learner_ref"] == learner_ref
            and r["course_id"] == course_id
            and r["status"] == "completed"
            for r in self._progress.values()
        )

    # -- experience statements ---------------------------------------------
    # Statements are held verbatim as records: the result text is
    # never parsed and there is deliberately no score field.

    def record_statement(self, learner_ref, verb, object_ref, actor, context="",
                         result_text=None):
        """Record one experience statement verbatim. Action: experience_write."""
        _require_actor(actor, "experience_write")
        _validate_non_empty(learner_ref, "learner_ref")
        _validate_non_empty(verb, "verb")
        _validate_non_empty(object_ref, "object_ref")
        if not isinstance(context, str):
            raise ValidationError("context must be a string")
        if result_text is not None and not isinstance(result_text, str):
            raise ValidationError("result_text must be a string")
        with self._lock:
            self._learner_by_ref(learner_ref)
            statement_id = self._next_id("stm")
            record = {
                "id": statement_id,
                "learner_ref": learner_ref,
                "verb": verb,
                "object_ref": object_ref,
                "context": context,
                "result_text": result_text,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._statements[statement_id] = record
            self._audit(actor, "statement_record", statement_id,
                        details={"learner_ref": learner_ref, "verb": verb,
                                 "object_ref": object_ref})
            return dict(record)

    def get_statement(self, statement_id, actor=None):
        """Return one experience statement. Action: experience_read (+ scope)."""
        _maybe_require(actor, "experience_read")
        with self._lock:
            record = self._get_statement_record(statement_id)
            self._scope_check(actor, record["learner_ref"])
            return dict(record)

    def list_statements(self, actor=None, learner_ref=None, object_ref=None):
        """Return experience statements, optionally filtered. Action: experience_read."""
        _maybe_require(actor, "experience_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._statements.values())
            if learner_ref is not None:
                records = [r for r in records if r["learner_ref"] == learner_ref]
            if object_ref is not None:
                records = [r for r in records if r["object_ref"] == object_ref]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- compliance assignments & derived status ---------------------------

    def create_compliance_assignment(self, learner_ref, course_id, due_date, actor):
        """Assign compliance training with a due date. Action: compliance_write.

        No status is stored: status is derived at read time from the
        due date and the learner's progress records (see
        :meth:`_derive_status`).
        """
        _require_actor(actor, "compliance_write")
        _validate_non_empty(learner_ref, "learner_ref")
        _validate_date(due_date, "due_date")
        with self._lock:
            self._learner_by_ref(learner_ref)
            self._get_course_record(course_id)
            assignment_id = self._next_id("asg")
            record = {
                "id": assignment_id,
                "learner_ref": learner_ref,
                "course_id": course_id,
                "due_date": due_date,
                "assigned_by": actor_name(actor),
                "assigned_utc": _utc_now(),
            }
            self._compliance[assignment_id] = record
            self._audit(actor, "compliance_assign", assignment_id,
                        details={"learner_ref": learner_ref, "course_id": course_id,
                                 "due_date": due_date})
            return dict(record)

    def _derive_status(self, assignment, as_of_date):
        """Derive current/overdue/completed status deterministically.

        MUTATION DRILL NOTE: the overdue branch of this function
        (``LmsStore._derive_status`` in ``src/lms/store.py``) is the
        load-bearing invariant for the negative-control drill: an
        incomplete assignment whose due date is before ``as_of``
        must read ``overdue``, never ``current``.
        """
        if self._has_completion(assignment["learner_ref"], assignment["course_id"]):
            return "completed"
        due = _validate_date(assignment["due_date"], "due_date")
        if as_of_date > due:
            return "overdue"
        return "current"

    def _compliance_view(self, assignment, as_of_date):
        view = dict(assignment)
        view["status"] = self._derive_status(assignment, as_of_date)
        view["completed"] = view["status"] == "completed"
        view["as_of"] = as_of_date.isoformat()
        return view

    def get_compliance_assignment(self, assignment_id, actor=None, as_of=None):
        """Return one assignment with its derived status.

        Action: compliance_read (+ learner scope). ``as_of`` is the
        reference date for derivation; pass it explicitly for
        deterministic results.
        """
        _maybe_require(actor, "compliance_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get_compliance_record(assignment_id)
            self._scope_check(actor, record["learner_ref"])
            return self._compliance_view(record, as_of_date)

    def compliance_status(self, assignment_id, actor=None, as_of=None):
        """Return the derived-status summary for one assignment.

        Action: compliance_read (+ learner scope).
        """
        _maybe_require(actor, "compliance_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get_compliance_record(assignment_id)
            self._scope_check(actor, record["learner_ref"])
            status = self._derive_status(record, as_of_date)
            return {
                "assignment_id": record["id"],
                "learner_ref": record["learner_ref"],
                "course_id": record["course_id"],
                "due_date": record["due_date"],
                "status": status,
                "completed": status == "completed",
                "as_of": as_of_date.isoformat(),
            }

    def list_compliance(self, actor=None, as_of=None, learner_ref=None):
        """Return assignments with derived status. Action: compliance_read."""
        _maybe_require(actor, "compliance_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            records = list(self._compliance.values())
            if learner_ref is not None:
                records = [r for r in records if r["learner_ref"] == learner_ref]
            return [self._compliance_view(r, as_of_date) for r in self._scoped(actor, records)]

    # -- workflows & notifications -------------------------------------------
    # Records only: registering a workflow never executes it -- it
    # changes no other record.

    def create_workflow(self, name, steps, actor, scope=""):
        """Register a workflow definition. Action: workflow_write."""
        _require_actor(actor, "workflow_write")
        _validate_non_empty(name, "workflow name")
        if not isinstance(steps, (list, tuple)) or len(steps) == 0:
            raise ValidationError("steps must be a non-empty list")
        steps = list(steps)
        for step in steps:
            _validate_non_empty(step, "workflow step")
        if not isinstance(scope, str):
            raise ValidationError("scope must be a string")
        with self._lock:
            workflow_id = self._next_id("wfl")
            record = {
                "id": workflow_id,
                "name": name,
                "scope": scope,
                "steps": list(steps),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflows[workflow_id] = record
            self._audit(actor, "workflow_create", workflow_id,
                        details={"name": name, "scope": scope})
            return self._copy_workflow(record)

    def get_workflow(self, workflow_id, actor=None):
        """Return one workflow definition. Action: workflow_read."""
        _maybe_require(actor, "workflow_read")
        with self._lock:
            return self._copy_workflow(self._get_workflow_record(workflow_id))

    def list_workflows(self, actor=None):
        """Return workflow definitions. Action: workflow_read."""
        _maybe_require(actor, "workflow_read")
        with self._lock:
            return [self._copy_workflow(r) for r in self._workflows.values()]

    def record_notification(self, recipient_ref, subject, actor, body="",
                            kind="general"):
        """Record a notification. Action: workflow_write."""
        _require_actor(actor, "workflow_write")
        _validate_non_empty(recipient_ref, "recipient_ref")
        _validate_non_empty(subject, "subject")
        if not isinstance(body, str):
            raise ValidationError("body must be a string")
        if not isinstance(kind, str):
            raise ValidationError("kind must be a string")
        with self._lock:
            notification_id = self._next_id("ntf")
            record = {
                "id": notification_id,
                "recipient_ref": recipient_ref,
                "subject": subject,
                "body": body,
                "kind": kind,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._notifications[notification_id] = record
            self._audit(actor, "notification_record", notification_id,
                        details={"recipient_ref": recipient_ref, "subject": subject,
                                 "kind": kind})
            return dict(record)

    def get_notification(self, notification_id, actor=None):
        """Return one notification. Action: workflow_read."""
        _maybe_require(actor, "workflow_read")
        with self._lock:
            return dict(self._get_notification_record(notification_id))

    def list_notifications(self, actor=None, recipient_ref=None):
        """Return notifications, optionally filtered. Action: workflow_read."""
        _maybe_require(actor, "workflow_read")
        with self._lock:
            records = list(self._notifications.values())
            if recipient_ref is not None:
                records = [r for r in records if r["recipient_ref"] == recipient_ref]
            return [dict(r) for r in records]

    # -- search & reporting over the records ---------------------------------

    def search(self, query, actor):
        """Literal case-insensitive substring search over the catalog.

        Action: report_read. Read-only: this does not audit.
        """
        _require_actor(actor, "report_read")
        _validate_non_empty(query, "query")
        needle = query.strip().lower()
        with self._lock:
            courses = [
                dict(c) for c in self._courses.values()
                if needle in c["title"].lower()
                or (c["code"] is not None and needle in c["code"].lower())
            ]
            content_items = [
                dict(r) for r in self._content_items.values()
                if needle in r["title"].lower()
            ]
            learners = [
                dict(r) for r in self._learners.values()
                if needle in r["ref"].lower() or needle in r["label"].lower()
            ]
            events = [
                self._event_view(r) for r in self._events.values()
                if needle in r["title"].lower()
            ]
            return {
                "courses": courses,
                "content_items": content_items,
                "learners": learners,
                "events": events,
            }

    def report(self, actor, as_of=None):
        """Counts/summaries over the substrate records only.

        Action: report_read. Compliance counts use the same derived
        status as the compliance reads, against ``as_of``.
        """
        _require_actor(actor, "report_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            registrations_by_state = {s: 0 for s in REGISTRATION_STATES}
            for record in self._registrations.values():
                registrations_by_state[record["state"]] += 1
            authorizations_by_state = {s: 0 for s in AUTHORIZATION_STATES}
            for record in self._authorizations.values():
                authorizations_by_state[record["state"]] += 1
            progress_by_status = {s: 0 for s in PROGRESS_STATUSES}
            for record in self._progress.values():
                progress_by_status[record["status"]] += 1
            compliance_by_status = {"current": 0, "overdue": 0, "completed": 0}
            for record in self._compliance.values():
                compliance_by_status[self._derive_status(record, as_of_date)] += 1
            result = {
                "as_of": as_of_date.isoformat(),
                "learners": len(self._learners),
                "courses": len(self._courses),
                "content_items": len(self._content_items),
                "lesson_plans": len(self._lesson_plans),
                "events": len(self._events),
                "registrations": len(self._registrations),
                "registrations_by_state": registrations_by_state,
                "authorizations": len(self._authorizations),
                "authorizations_by_state": authorizations_by_state,
                "development_plans": len(self._development_plans),
                "competencies": len(self._competencies),
                "learner_competency_records": len(self._learner_competencies),
                "progress_records": len(self._progress),
                "progress_by_status": progress_by_status,
                "statements": len(self._statements),
                "compliance_assignments": len(self._compliance),
                "compliance_by_status": compliance_by_status,
                "workflows": len(self._workflows),
                "notifications": len(self._notifications),
            }
            self._audit(actor, "report", "report", details={"as_of": result["as_of"]})
            return result
