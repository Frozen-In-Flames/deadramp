"""Education & training records store: course/catalog registry,
enrollments & registrations, learner progress & readiness records,
assessment administration records, certificate/credential records,
compliance assignments with derived status, scheduling records, and
reporting over the records.

Clean-room implementation of the union spec's 10 Core functions.
Records only: there is no content delivery, no assessment scoring
engine, and no credential issuance engine in this substrate (those
are Extended functions in the union spec).

Permission convention (mirrors the communication group): store
methods take an ``actor``. When the actor is a User-like object (it
has a ``role`` attribute) the store calls
:func:`learn.access.require` for the method's action *before* any
state change or id allocation, so a denied operation consumes no id
and changes nothing. Where a plain string is passed it carries
identity (for provenance) but no role, so there is nothing to enforce
against at this layer; the service layer, which knows the role
registry, is responsible for enforcement in that case -- and it
always passes User objects.

Learner scope: a ``learner``-role actor may only read records whose
``learner_id`` equals the actor's name; reading another learner's
record raises :class:`PermissionDenied`, and list methods return only
the learner's own records.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``crs-``, ``enr-``, ``prg-``,
``asm-``, ``cred-``, ``cmp-``, ``sch-``).

Compliance status is DERIVED at read time, never stored: given an
assignment, its due date, the learner's progress records, and an
explicit ``as_of`` reference date, the status is ``completed`` when a
completed progress record exists for the learner+course, ``overdue``
when ``as_of`` is after the due date, and ``current`` otherwise. The
derivation is deterministic in its inputs; tests always pass an
explicit ``as_of`` and never depend on the wall clock.

The store records every successful mutation to its audit log (when
one is attached).
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

COURSE_KINDS = ("course", "program")
ENROLLMENT_KINDS = ("enrollment", "registration")
PROGRESS_STATUSES = ("not_started", "in_progress", "completed")
READINESS_LEVELS = ("not_ready", "developing", "ready")
ASSESSMENT_STATES = ("scheduled", "administered", "completed", "cancelled")
CREDENTIAL_KINDS = ("certification", "licensure", "credential")
CREDENTIAL_STATUSES = ("pending", "active", "expired", "revoked")
SESSION_KINDS = ("training", "assessment")


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


class LearnStore:
    """In-memory store for the education & training records service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._courses = {}
        self._enrollments = {}
        self._progress = {}
        self._assessments = {}
        self._credentials = {}
        self._compliance = {}
        self._sessions = {}
        self._counters = {
            "crs": 0, "enr": 0, "prg": 0, "asm": 0, "cred": 0, "cmp": 0, "sch": 0,
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

    def _scope_check(self, actor, learner_id):
        """A learner-role actor may only touch their own records."""
        if self._is_learner(actor) and getattr(actor, "name", None) != learner_id:
            raise PermissionDenied(
                "permission denied: learner %r may not access records of learner %r"
                % (getattr(actor, "name", None), learner_id)
            )

    def _scoped(self, actor, records):
        """Filter learner-owned records to a learner actor's own."""
        if self._is_learner(actor):
            name = getattr(actor, "name", None)
            return [r for r in records if r.get("learner_id") == name]
        return list(records)

    def _get_course_record(self, course_id):
        course = self._courses.get(course_id)
        if course is None:
            raise NotFoundError("course not found: %r" % (course_id,))
        return course

    def _get_enrollment_record(self, enrollment_id):
        enrollment = self._enrollments.get(enrollment_id)
        if enrollment is None:
            raise NotFoundError("enrollment not found: %r" % (enrollment_id,))
        return enrollment

    def _get_progress_record(self, progress_id):
        record = self._progress.get(progress_id)
        if record is None:
            raise NotFoundError("progress record not found: %r" % (progress_id,))
        return record

    def _get_assessment_record(self, assessment_id):
        record = self._assessments.get(assessment_id)
        if record is None:
            raise NotFoundError("assessment record not found: %r" % (assessment_id,))
        return record

    def _get_credential_record(self, credential_id):
        record = self._credentials.get(credential_id)
        if record is None:
            raise NotFoundError("credential record not found: %r" % (credential_id,))
        return record

    def _get_compliance_record(self, assignment_id):
        record = self._compliance.get(assignment_id)
        if record is None:
            raise NotFoundError("compliance assignment not found: %r" % (assignment_id,))
        return record

    def _get_session_record(self, session_id):
        record = self._sessions.get(session_id)
        if record is None:
            raise NotFoundError("session not found: %r" % (session_id,))
        return record

    @staticmethod
    def _copy_assessment(record):
        copied = dict(record)
        copied["responses"] = [dict(r) for r in record["responses"]]
        return copied

    @staticmethod
    def _copy_session(record):
        copied = dict(record)
        copied["learner_ids"] = list(record["learner_ids"])
        return copied

    # -- courses / catalog (Core 1) ------------------------------------

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

    # -- enrollments & registrations (Core 2) ---------------------------

    def create_enrollment(self, learner_id, course_id, actor, kind="enrollment"):
        """Enroll/register a learner against a registry entry.

        Action: enrollment_write. A duplicate active enrollment for
        the same learner+course+kind is a validation error.
        """
        _require_actor(actor, "enrollment_write")
        _validate_non_empty(learner_id, "learner_id")
        if kind not in ENROLLMENT_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(ENROLLMENT_KINDS),))
        with self._lock:
            self._get_course_record(course_id)
            for existing in self._enrollments.values():
                if (
                    existing["learner_id"] == learner_id
                    and existing["course_id"] == course_id
                    and existing["kind"] == kind
                    and existing["status"] == "enrolled"
                ):
                    raise ValidationError(
                        "learner %r is already enrolled in course %r" % (learner_id, course_id)
                    )
            enrollment_id = self._next_id("enr")
            enrollment = {
                "id": enrollment_id,
                "learner_id": learner_id,
                "course_id": course_id,
                "kind": kind,
                "status": "enrolled",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._enrollments[enrollment_id] = enrollment
            self._audit(actor, "enrollment_create", enrollment_id,
                        details={"learner_id": learner_id, "course_id": course_id})
            return dict(enrollment)

    def get_enrollment(self, enrollment_id, actor=None):
        """Return one enrollment. Action: enrollment_read (+ learner scope)."""
        _maybe_require(actor, "enrollment_read")
        with self._lock:
            enrollment = self._get_enrollment_record(enrollment_id)
            self._scope_check(actor, enrollment["learner_id"])
            return dict(enrollment)

    def list_enrollments(self, actor=None, learner_id=None, course_id=None):
        """Return enrollments, optionally filtered. Action: enrollment_read."""
        _maybe_require(actor, "enrollment_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._enrollments.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- learner progress & readiness records (Core 3) ------------------

    def record_progress(self, learner_id, course_id, status, actor,
                        readiness=None, percent_complete=None, note=""):
        """Record a progress/readiness entry for a learner+course.

        Action: progress_write. ``completed`` is the terminal
        progress state and is what compliance derivation reads.
        """
        _require_actor(actor, "progress_write")
        _validate_non_empty(learner_id, "learner_id")
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
            self._get_course_record(course_id)
            progress_id = self._next_id("prg")
            record = {
                "id": progress_id,
                "learner_id": learner_id,
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
                        details={"learner_id": learner_id, "course_id": course_id, "status": status})
            return dict(record)

    def get_progress(self, progress_id, actor=None):
        """Return one progress record. Action: progress_read (+ scope)."""
        _maybe_require(actor, "progress_read")
        with self._lock:
            record = self._get_progress_record(progress_id)
            self._scope_check(actor, record["learner_id"])
            return dict(record)

    def list_progress(self, actor=None, learner_id=None, course_id=None):
        """Return progress records, optionally filtered. Action: progress_read."""
        _maybe_require(actor, "progress_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._progress.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [dict(r) for r in self._scoped(actor, records)]

    def _has_completion(self, learner_id, course_id):
        """True when a completed progress record exists for learner+course."""
        return any(
            r["learner_id"] == learner_id
            and r["course_id"] == course_id
            and r["status"] == "completed"
            for r in self._progress.values()
        )

    # -- assessment records (Core 4) -------------------------------------
    # Administration records only: sessions, attempts and item
    # responses held as records. There is deliberately NO scoring:
    # deterministic scoring was ruled Extended (0/8 claims).

    def create_assessment(self, title, learner_id, actor, course_id=None,
                          session_id=None, state="scheduled"):
        """Create an assessment administration record. Action: assessment_write."""
        _require_actor(actor, "assessment_write")
        _validate_non_empty(title, "assessment title")
        _validate_non_empty(learner_id, "learner_id")
        if state not in ASSESSMENT_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(ASSESSMENT_STATES),))
        with self._lock:
            if course_id is not None:
                self._get_course_record(course_id)
            if session_id is not None:
                self._get_session_record(session_id)
            assessment_id = self._next_id("asm")
            record = {
                "id": assessment_id,
                "title": title,
                "learner_id": learner_id,
                "course_id": course_id,
                "session_id": session_id,
                "state": state,
                "responses": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._assessments[assessment_id] = record
            self._audit(actor, "assessment_create", assessment_id,
                        details={"learner_id": learner_id, "state": state})
            return self._copy_assessment(record)

    def add_assessment_response(self, assessment_id, item_id, response, actor):
        """Record one item response on an assessment record.

        Action: assessment_write. The response is stored verbatim as
        a record; it is never scored. A duplicate item_id on the same
        assessment is a validation error.
        """
        _require_actor(actor, "assessment_write")
        _validate_non_empty(item_id, "item_id")
        if not isinstance(response, str):
            raise ValidationError("response must be a string")
        with self._lock:
            record = self._get_assessment_record(assessment_id)
            if any(r["item_id"] == item_id for r in record["responses"]):
                raise ValidationError(
                    "item %r already has a response on assessment %r" % (item_id, assessment_id)
                )
            record["responses"].append({"item_id": item_id, "response": response})
            self._audit(actor, "assessment_response", assessment_id, details={"item_id": item_id})
            return self._copy_assessment(record)

    def set_assessment_state(self, assessment_id, state, actor):
        """Set an assessment record's administration state. Action: assessment_write."""
        _require_actor(actor, "assessment_write")
        if state not in ASSESSMENT_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(ASSESSMENT_STATES),))
        with self._lock:
            record = self._get_assessment_record(assessment_id)
            record["state"] = state
            self._audit(actor, "assessment_set_state", assessment_id, details={"state": state})
            return self._copy_assessment(record)

    def get_assessment(self, assessment_id, actor=None):
        """Return one assessment record. Action: assessment_read (+ scope)."""
        _maybe_require(actor, "assessment_read")
        with self._lock:
            record = self._get_assessment_record(assessment_id)
            self._scope_check(actor, record["learner_id"])
            return self._copy_assessment(record)

    def list_assessments(self, actor=None, learner_id=None, course_id=None):
        """Return assessment records, optionally filtered. Action: assessment_read."""
        _maybe_require(actor, "assessment_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._assessments.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._copy_assessment(r) for r in self._scoped(actor, records)]

    # -- certificate/credential records (Core 5) --------------------------
    # Records only: this substrate holds and tracks credential
    # records; it does not issue credentials (issuance is claimed by
    # 0/8 siblings and is not in the Core).

    def create_credential(self, learner_id, name, actor, kind="certification",
                          status="active", issued_date=None, expiry_date=None):
        """Create a certificate/credential record. Action: credential_write."""
        _require_actor(actor, "credential_write")
        _validate_non_empty(learner_id, "learner_id")
        _validate_non_empty(name, "credential name")
        if kind not in CREDENTIAL_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(CREDENTIAL_KINDS),))
        if status not in CREDENTIAL_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(CREDENTIAL_STATUSES),))
        issued = _validate_date(issued_date, "issued_date") if issued_date is not None else None
        expiry = _validate_date(expiry_date, "expiry_date") if expiry_date is not None else None
        if issued is not None and expiry is not None and expiry < issued:
            raise ValidationError("expiry_date must not be before issued_date")
        with self._lock:
            credential_id = self._next_id("cred")
            record = {
                "id": credential_id,
                "learner_id": learner_id,
                "name": name,
                "kind": kind,
                "status": status,
                "issued_date": issued_date,
                "expiry_date": expiry_date,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._credentials[credential_id] = record
            self._audit(actor, "credential_create", credential_id,
                        details={"learner_id": learner_id, "kind": kind, "status": status})
            return dict(record)

    def set_credential_status(self, credential_id, status, actor):
        """Update a credential record's tracked status. Action: credential_write."""
        _require_actor(actor, "credential_write")
        if status not in CREDENTIAL_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(CREDENTIAL_STATUSES),))
        with self._lock:
            record = self._get_credential_record(credential_id)
            record["status"] = status
            self._audit(actor, "credential_set_status", credential_id, details={"status": status})
            return dict(record)

    def get_credential(self, credential_id, actor=None):
        """Return one credential record. Action: credential_read (+ scope)."""
        _maybe_require(actor, "credential_read")
        with self._lock:
            record = self._get_credential_record(credential_id)
            self._scope_check(actor, record["learner_id"])
            return dict(record)

    def list_credentials(self, actor=None, learner_id=None):
        """Return credential records, optionally filtered. Action: credential_read."""
        _maybe_require(actor, "credential_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        with self._lock:
            records = list(self._credentials.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- compliance assignments & derived status (Core 6) ---------------

    def create_compliance_assignment(self, learner_id, course_id, due_date, actor):
        """Assign compliance training with a due date. Action: compliance_write.

        No status is stored: status is derived at read time from the
        due date and the learner's progress records (see
        :meth:`_derive_status`).
        """
        _require_actor(actor, "compliance_write")
        _validate_non_empty(learner_id, "learner_id")
        _validate_date(due_date, "due_date")
        with self._lock:
            self._get_course_record(course_id)
            assignment_id = self._next_id("cmp")
            record = {
                "id": assignment_id,
                "learner_id": learner_id,
                "course_id": course_id,
                "due_date": due_date,
                "assigned_by": actor_name(actor),
                "assigned_utc": _utc_now(),
            }
            self._compliance[assignment_id] = record
            self._audit(actor, "compliance_assign", assignment_id,
                        details={"learner_id": learner_id, "course_id": course_id, "due_date": due_date})
            return dict(record)

    def _derive_status(self, assignment, as_of_date):
        """Derive current/overdue/completed status deterministically.

        MUTATION DRILL NOTE: the overdue branch of this function
        (``LearnStore._derive_status`` in ``src/learn/store.py``) is
        the load-bearing invariant for the negative-control drill:
        an incomplete assignment whose due date is before ``as_of``
        must read ``overdue``, never ``current``.
        """
        if self._has_completion(assignment["learner_id"], assignment["course_id"]):
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
            self._scope_check(actor, record["learner_id"])
            return self._compliance_view(record, as_of_date)

    def compliance_status(self, assignment_id, actor=None, as_of=None):
        """Return the derived-status summary for one assignment.

        Action: compliance_read (+ learner scope).
        """
        _maybe_require(actor, "compliance_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            record = self._get_compliance_record(assignment_id)
            self._scope_check(actor, record["learner_id"])
            status = self._derive_status(record, as_of_date)
            return {
                "assignment_id": record["id"],
                "learner_id": record["learner_id"],
                "course_id": record["course_id"],
                "due_date": record["due_date"],
                "status": status,
                "completed": status == "completed",
                "as_of": as_of_date.isoformat(),
            }

    def list_compliance(self, actor=None, as_of=None, learner_id=None):
        """Return assignments with derived status. Action: compliance_read."""
        _maybe_require(actor, "compliance_read")
        if learner_id is not None:
            self._scope_check(actor, learner_id)
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            records = list(self._compliance.values())
            if learner_id is not None:
                records = [r for r in records if r["learner_id"] == learner_id]
            return [self._compliance_view(r, as_of_date) for r in self._scoped(actor, records)]

    # -- scheduling records (Core 7) ---------------------------------------

    def create_session(self, title, course_id, starts_at, actor, ends_at=None,
                       kind="training", location="", learner_ids=None):
        """Create a scheduled training/assessment session record.

        Action: schedule_write.
        """
        _require_actor(actor, "schedule_write")
        _validate_non_empty(title, "session title")
        if kind not in SESSION_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(SESSION_KINDS),))
        start_dt = _parse_iso_datetime(starts_at, "starts_at")
        end_dt = _parse_iso_datetime(ends_at, "ends_at") if ends_at is not None else None
        if end_dt is not None and end_dt < start_dt:
            raise ValidationError("ends_at must not be before starts_at")
        if not isinstance(location, str):
            raise ValidationError("location must be a string")
        if learner_ids is None:
            learner_ids = []
        if not isinstance(learner_ids, (list, tuple)):
            raise ValidationError("learner_ids must be a list")
        for learner_id in learner_ids:
            _validate_non_empty(learner_id, "learner_id")
        with self._lock:
            self._get_course_record(course_id)
            session_id = self._next_id("sch")
            record = {
                "id": session_id,
                "title": title,
                "course_id": course_id,
                "kind": kind,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "location": location,
                "learner_ids": list(learner_ids),
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._sessions[session_id] = record
            self._audit(actor, "session_create", session_id,
                        details={"course_id": course_id, "kind": kind})
            return self._copy_session(record)

    def get_session(self, session_id, actor=None):
        """Return one session record. Action: schedule_read."""
        _maybe_require(actor, "schedule_read")
        with self._lock:
            return self._copy_session(self._get_session_record(session_id))

    def list_sessions(self, actor=None, course_id=None):
        """Return session records, optionally filtered. Action: schedule_read."""
        _maybe_require(actor, "schedule_read")
        with self._lock:
            records = list(self._sessions.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._copy_session(r) for r in records]

    # -- reporting over the records (Core 8) --------------------------------

    def report(self, actor, as_of=None):
        """Counts/summaries over the substrate records only.

        Action: report_read. Compliance counts use the same derived
        status as the compliance reads, against ``as_of``.
        """
        _require_actor(actor, "report_read")
        as_of_date = _coerce_as_of(as_of)
        with self._lock:
            progress_by_status = {s: 0 for s in PROGRESS_STATUSES}
            for record in self._progress.values():
                progress_by_status[record["status"]] += 1
            assessments_by_state = {s: 0 for s in ASSESSMENT_STATES}
            for record in self._assessments.values():
                assessments_by_state[record["state"]] += 1
            credentials_by_status = {s: 0 for s in CREDENTIAL_STATUSES}
            for record in self._credentials.values():
                credentials_by_status[record["status"]] += 1
            compliance_by_status = {"current": 0, "overdue": 0, "completed": 0}
            for record in self._compliance.values():
                compliance_by_status[self._derive_status(record, as_of_date)] += 1
            enrollments_by_course = {}
            for record in self._enrollments.values():
                enrollments_by_course[record["course_id"]] = (
                    enrollments_by_course.get(record["course_id"], 0) + 1
                )
            result = {
                "as_of": as_of_date.isoformat(),
                "courses": len(self._courses),
                "enrollments": len(self._enrollments),
                "enrollments_by_course": enrollments_by_course,
                "progress_records": len(self._progress),
                "progress_by_status": progress_by_status,
                "assessments": len(self._assessments),
                "assessments_by_state": assessments_by_state,
                "credentials": len(self._credentials),
                "credentials_by_status": credentials_by_status,
                "compliance_assignments": len(self._compliance),
                "compliance_by_status": compliance_by_status,
                "sessions": len(self._sessions),
            }
            self._audit(actor, "report", "report", details={"as_of": result["as_of"]})
            return result
