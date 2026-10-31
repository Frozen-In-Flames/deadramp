"""Human resources records store: person records, position
classification records, vacancy announcements, applications,
evaluations, employee lifecycle cases, performance reviews, benefits
records, personnel cases, and reporting over the records.

Clean-room implementation of the union spec's 12 Core functions.
Records only: there is no weighted cumulative scoring engine and no
compensation engine in this substrate (those are Extended functions
in the union spec).

PRIVACY DISCIPLINE: records hold an opaque caller-supplied
``person_ref`` string only. No field anywhere holds a real name, SSN,
DOB, salary/compensation figure, address, phone, or email. The person
record shape is exactly ``{id, person_ref, kind, status, created_by,
created_utc}``. Positions carry ``series`` / ``grade`` classification
attributes only; no compensation field exists.

Permission convention (mirrors the education group): store methods
take an ``actor``. When the actor is a User-like object (it has a
``role`` attribute) the store calls :func:`hr.access.require` for the
method's action *before* any state change or id allocation, so a
denied operation consumes no id and changes nothing. Where a plain
string is passed it carries identity (for provenance) but no role, so
there is nothing to enforce against at this layer; the service layer,
which knows the role registry, is responsible for enforcement in that
case -- and it always passes User objects.

Employee scope: an ``employee``-role actor may only read records
whose ``person_ref`` equals the actor's name; reading another
person's record raises :class:`PermissionDenied`, and list methods
return only the employee's own records. Org-level records (positions,
vacancies) are NOT person-scoped. Evaluations are scoped through
their application's ``person_ref``.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``per-``, ``pos-``, ``vac-``,
``app-``, ``evl-``, ``lif-``, ``rev-``, ``ben-``, ``cas-``).

Lifecycle case status is DERIVED at read time, never stored: given a
case's tasks and its ``cancelled`` flag, the status is ``cancelled``
when cancelled, ``complete`` when every task is done/waived,
``not_started`` when there are no tasks or all are pending, and
``in_progress`` otherwise.

The store records every successful mutation to its audit log (when
one is attached).
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PERSON_KINDS = ("applicant", "employee")
PERSON_STATUSES = ("applicant", "active", "separated")
POSITION_STATUSES = ("vacant", "filled", "abolished")
VACANCY_STATUSES = ("draft", "posted", "closed")
APPLICATION_STAGES = ("applied", "screened", "referred", "selected", "not_selected", "withdrawn")
EVALUATION_KINDS = ("assessment", "panel")
EVALUATION_STATES = ("scheduled", "completed", "cancelled")
LIFECYCLE_KINDS = ("onboarding", "separation")
TASK_STATES = ("pending", "done", "waived")
REVIEW_STATES = ("planned", "in_progress", "completed")
BENEFITS_KINDS = ("benefit_enrollment", "retirement_case")
BENEFITS_STATES = ("pending", "active", "closed")
CASE_KINDS = ("personnel_action", "award", "labor_relations", "general")
CASE_STATES = ("opened", "in_review", "closed")
LIFECYCLE_STATUSES = ("cancelled", "not_started", "in_progress", "complete")


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


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class HrStore:
    """In-memory store for the human resources records service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._persons = {}
        self._positions = {}
        self._vacancies = {}
        self._applications = {}
        self._evaluations = {}
        self._lifecycle = {}
        self._reviews = {}
        self._benefits = {}
        self._cases = {}
        self._counters = {
            "per": 0, "pos": 0, "vac": 0, "app": 0, "evl": 0,
            "lif": 0, "rev": 0, "ben": 0, "cas": 0,
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
    def _is_employee(actor):
        return actor is not None and getattr(actor, "role", None) == "employee"

    def _scope_check(self, actor, person_ref):
        """An employee-role actor may only touch their own records."""
        if self._is_employee(actor) and getattr(actor, "name", None) != person_ref:
            raise PermissionDenied(
                "permission denied: employee %r may not access records of person %r"
                % (getattr(actor, "name", None), person_ref)
            )

    def _scoped(self, actor, records):
        """Filter person-owned records to an employee actor's own."""
        if self._is_employee(actor):
            name = getattr(actor, "name", None)
            return [r for r in records if r.get("person_ref") == name]
        return list(records)

    def _person_by_ref(self, person_ref):
        for person in self._persons.values():
            if person["person_ref"] == person_ref:
                return person
        return None

    def _require_person(self, person_ref):
        person = self._person_by_ref(person_ref)
        if person is None:
            raise NotFoundError("person not found: %r" % (person_ref,))
        return person

    def _get_person_record(self, person_id):
        record = self._persons.get(person_id)
        if record is None:
            raise NotFoundError("person not found: %r" % (person_id,))
        return record

    def _get_position_record(self, position_id):
        record = self._positions.get(position_id)
        if record is None:
            raise NotFoundError("position not found: %r" % (position_id,))
        return record

    def _get_vacancy_record(self, vacancy_id):
        record = self._vacancies.get(vacancy_id)
        if record is None:
            raise NotFoundError("vacancy not found: %r" % (vacancy_id,))
        return record

    def _get_application_record(self, application_id):
        record = self._applications.get(application_id)
        if record is None:
            raise NotFoundError("application not found: %r" % (application_id,))
        return record

    def _get_evaluation_record(self, evaluation_id):
        record = self._evaluations.get(evaluation_id)
        if record is None:
            raise NotFoundError("evaluation not found: %r" % (evaluation_id,))
        return record

    def _get_lifecycle_record(self, case_id):
        record = self._lifecycle.get(case_id)
        if record is None:
            raise NotFoundError("lifecycle case not found: %r" % (case_id,))
        return record

    def _get_review_record(self, review_id):
        record = self._reviews.get(review_id)
        if record is None:
            raise NotFoundError("performance review not found: %r" % (review_id,))
        return record

    def _get_benefits_record(self, record_id):
        record = self._benefits.get(record_id)
        if record is None:
            raise NotFoundError("benefits record not found: %r" % (record_id,))
        return record

    def _get_case_record(self, case_id):
        record = self._cases.get(case_id)
        if record is None:
            raise NotFoundError("case not found: %r" % (case_id,))
        return record

    def _evaluation_person_ref(self, record):
        application = self._applications.get(record["application_id"])
        return application["person_ref"] if application is not None else None

    @staticmethod
    def _copy_evaluation(record):
        copied = dict(record)
        copied["entries"] = [dict(e) for e in record["entries"]]
        return copied

    @staticmethod
    def _copy_lifecycle(record):
        copied = dict(record)
        copied["tasks"] = [dict(t) for t in record["tasks"]]
        return copied

    # -- persons (Core 1) ----------------------------------------------

    def create_person(self, person_ref, actor, kind="applicant"):
        """Create a person record from an opaque person_ref.

        Action: person_write. The record shape is exactly
        ``{id, person_ref, kind, status, created_by, created_utc}``;
        a duplicate person_ref is a validation error.
        """
        _require_actor(actor, "person_write")
        _validate_non_empty(person_ref, "person_ref")
        if kind not in PERSON_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(PERSON_KINDS),))
        with self._lock:
            if self._person_by_ref(person_ref) is not None:
                raise ValidationError("person_ref already exists: %r" % (person_ref,))
            person_id = self._next_id("per")
            record = {
                "id": person_id,
                "person_ref": person_ref,
                "kind": kind,
                "status": "applicant" if kind == "applicant" else "active",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._persons[person_id] = record
            self._audit(actor, "person_create", person_id,
                        details={"person_ref": person_ref, "kind": kind})
            return dict(record)

    def set_person_status(self, person_id, status, actor):
        """Set a person record's status. Action: person_write."""
        _require_actor(actor, "person_write")
        if status not in PERSON_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(PERSON_STATUSES),))
        with self._lock:
            record = self._get_person_record(person_id)
            record["status"] = status
            self._audit(actor, "person_set_status", person_id, details={"status": status})
            return dict(record)

    def get_person(self, person_id, actor=None):
        """Return one person record. Action: person_read (+ employee scope)."""
        _maybe_require(actor, "person_read")
        with self._lock:
            record = self._get_person_record(person_id)
            self._scope_check(actor, record["person_ref"])
            return dict(record)

    def list_persons(self, actor=None):
        """Return person records sorted by id. Action: person_read."""
        _maybe_require(actor, "person_read")
        with self._lock:
            records = sorted(self._persons.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in self._scoped(actor, records)]

    # -- positions (Core 2) ----------------------------------------------

    def create_position(self, title, actor, series=None, grade=None, organization=""):
        """Create a position classification record. Action: position_write.

        ``series`` / ``grade`` are classification attributes only;
        no compensation field exists on a position record.
        """
        _require_actor(actor, "position_write")
        _validate_non_empty(title, "position title")
        if series is not None and not isinstance(series, str):
            raise ValidationError("series must be a string")
        if grade is not None and not isinstance(grade, str):
            raise ValidationError("grade must be a string")
        if not isinstance(organization, str):
            raise ValidationError("organization must be a string")
        with self._lock:
            position_id = self._next_id("pos")
            record = {
                "id": position_id,
                "title": title,
                "series": series,
                "grade": grade,
                "organization": organization,
                "status": "vacant",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._positions[position_id] = record
            self._audit(actor, "position_create", position_id,
                        details={"title": title, "series": series, "grade": grade})
            return dict(record)

    def set_position_status(self, position_id, status, actor):
        """Set a position record's status. Action: position_write."""
        _require_actor(actor, "position_write")
        if status not in POSITION_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(POSITION_STATUSES),))
        with self._lock:
            record = self._get_position_record(position_id)
            record["status"] = status
            self._audit(actor, "position_set_status", position_id, details={"status": status})
            return dict(record)

    def get_position(self, position_id, actor=None):
        """Return one position record. Action: position_read (not person-scoped)."""
        _maybe_require(actor, "position_read")
        with self._lock:
            return dict(self._get_position_record(position_id))

    def list_positions(self, actor=None):
        """Return position records sorted by id. Action: position_read."""
        _maybe_require(actor, "position_read")
        with self._lock:
            records = sorted(self._positions.values(), key=lambda r: _id_num(r["id"]))
            return [dict(r) for r in records]

    # -- vacancies (Core 3) ----------------------------------------------

    def create_vacancy(self, position_id, title, actor, opens_on=None, closes_on=None):
        """Create a vacancy announcement bound to a position.

        Action: vacancy_write. The position must exist; ISO dates
        are validated and closes_on must not precede opens_on.
        """
        _require_actor(actor, "vacancy_write")
        _validate_non_empty(title, "vacancy title")
        opens = _validate_date(opens_on, "opens_on") if opens_on is not None else None
        closes = _validate_date(closes_on, "closes_on") if closes_on is not None else None
        if opens is not None and closes is not None and closes < opens:
            raise ValidationError("closes_on must not be before opens_on")
        with self._lock:
            self._get_position_record(position_id)
            vacancy_id = self._next_id("vac")
            record = {
                "id": vacancy_id,
                "position_id": position_id,
                "title": title,
                "opens_on": opens_on,
                "closes_on": closes_on,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._vacancies[vacancy_id] = record
            self._audit(actor, "vacancy_create", vacancy_id,
                        details={"position_id": position_id, "title": title})
            return dict(record)

    def set_vacancy_status(self, vacancy_id, status, actor):
        """Set a vacancy announcement's status. Action: vacancy_write."""
        _require_actor(actor, "vacancy_write")
        if status not in VACANCY_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(VACANCY_STATUSES),))
        with self._lock:
            record = self._get_vacancy_record(vacancy_id)
            record["status"] = status
            self._audit(actor, "vacancy_set_status", vacancy_id, details={"status": status})
            return dict(record)

    def get_vacancy(self, vacancy_id, actor=None):
        """Return one vacancy record. Action: vacancy_read (not person-scoped)."""
        _maybe_require(actor, "vacancy_read")
        with self._lock:
            return dict(self._get_vacancy_record(vacancy_id))

    def list_vacancies(self, actor=None, position_id=None):
        """Return vacancy records, optionally filtered. Action: vacancy_read."""
        _maybe_require(actor, "vacancy_read")
        with self._lock:
            records = list(self._vacancies.values())
            if position_id is not None:
                records = [r for r in records if r["position_id"] == position_id]
            return [dict(r) for r in records]

    # -- applications (Core 4) ----------------------------------------------

    def create_application(self, person_ref, vacancy_id, actor):
        """Create an application of a person to a vacancy.

        Action: application_write. The person (by person_ref) and
        the vacancy must exist. A duplicate live application (same
        person_ref + vacancy, stage not in not_selected/withdrawn)
        is a validation error.
        """
        _require_actor(actor, "application_write")
        _validate_non_empty(person_ref, "person_ref")
        with self._lock:
            self._require_person(person_ref)
            self._get_vacancy_record(vacancy_id)
            for existing in self._applications.values():
                if (
                    existing["person_ref"] == person_ref
                    and existing["vacancy_id"] == vacancy_id
                    and existing["stage"] not in ("not_selected", "withdrawn")
                ):
                    raise ValidationError(
                        "person %r already has a live application to vacancy %r"
                        % (person_ref, vacancy_id)
                    )
            application_id = self._next_id("app")
            record = {
                "id": application_id,
                "person_ref": person_ref,
                "vacancy_id": vacancy_id,
                "stage": "applied",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._applications[application_id] = record
            self._audit(actor, "application_create", application_id,
                        details={"person_ref": person_ref, "vacancy_id": vacancy_id})
            return dict(record)

    def set_application_stage(self, application_id, stage, actor):
        """Set an application's stage. Action: application_write."""
        _require_actor(actor, "application_write")
        if stage not in APPLICATION_STAGES:
            raise ValidationError("stage must be one of %s" % (", ".join(APPLICATION_STAGES),))
        with self._lock:
            record = self._get_application_record(application_id)
            record["stage"] = stage
            self._audit(actor, "application_set_stage", application_id, details={"stage": stage})
            return dict(record)

    def get_application(self, application_id, actor=None):
        """Return one application. Action: application_read (+ employee scope)."""
        _maybe_require(actor, "application_read")
        with self._lock:
            record = self._get_application_record(application_id)
            self._scope_check(actor, record["person_ref"])
            return dict(record)

    def list_applications(self, actor=None, person_ref=None, vacancy_id=None):
        """Return applications, optionally filtered. Action: application_read."""
        _maybe_require(actor, "application_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._applications.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            if vacancy_id is not None:
                records = [r for r in records if r["vacancy_id"] == vacancy_id]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- evaluations (Core 5) ----------------------------------------------
    # Records only: rater entries are held verbatim. There is
    # deliberately NO aggregate/average/score field anywhere:
    # weighted cumulative scoring was ruled Extended.

    def create_evaluation(self, application_id, kind, title, actor):
        """Create an evaluation record bound to an application.

        Action: evaluation_write. The application must exist.
        """
        _require_actor(actor, "evaluation_write")
        if kind not in EVALUATION_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(EVALUATION_KINDS),))
        _validate_non_empty(title, "evaluation title")
        with self._lock:
            self._get_application_record(application_id)
            evaluation_id = self._next_id("evl")
            record = {
                "id": evaluation_id,
                "application_id": application_id,
                "kind": kind,
                "title": title,
                "state": "scheduled",
                "entries": [],
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._evaluations[evaluation_id] = record
            self._audit(actor, "evaluation_create", evaluation_id,
                        details={"application_id": application_id, "kind": kind})
            return self._copy_evaluation(record)

    def add_evaluation_entry(self, evaluation_id, rater_ref, rating, comment, actor):
        """Record one rater entry on an evaluation record.

        Action: evaluation_write. The entry is stored verbatim as a
        record; it is never aggregated. ``rating`` must be a number
        (bool rejected), ``comment`` a string, and a duplicate
        rater_ref on the same evaluation is a validation error.
        """
        _require_actor(actor, "evaluation_write")
        _validate_non_empty(rater_ref, "rater_ref")
        if isinstance(rating, bool) or not isinstance(rating, (int, float)):
            raise ValidationError("rating must be a number")
        if not isinstance(comment, str):
            raise ValidationError("comment must be a string")
        with self._lock:
            record = self._get_evaluation_record(evaluation_id)
            if any(e["rater_ref"] == rater_ref for e in record["entries"]):
                raise ValidationError(
                    "rater %r already has an entry on evaluation %r" % (rater_ref, evaluation_id)
                )
            record["entries"].append(
                {"rater_ref": rater_ref, "rating": rating, "comment": comment}
            )
            self._audit(actor, "evaluation_entry", evaluation_id, details={"rater_ref": rater_ref})
            return self._copy_evaluation(record)

    def set_evaluation_state(self, evaluation_id, state, actor):
        """Set an evaluation record's state. Action: evaluation_write."""
        _require_actor(actor, "evaluation_write")
        if state not in EVALUATION_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(EVALUATION_STATES),))
        with self._lock:
            record = self._get_evaluation_record(evaluation_id)
            record["state"] = state
            self._audit(actor, "evaluation_set_state", evaluation_id, details={"state": state})
            return self._copy_evaluation(record)

    def get_evaluation(self, evaluation_id, actor=None):
        """Return one evaluation. Action: evaluation_read (+ scope via application)."""
        _maybe_require(actor, "evaluation_read")
        with self._lock:
            record = self._get_evaluation_record(evaluation_id)
            self._scope_check(actor, self._evaluation_person_ref(record))
            return self._copy_evaluation(record)

    def list_evaluations(self, actor=None, application_id=None):
        """Return evaluations, optionally filtered. Action: evaluation_read."""
        _maybe_require(actor, "evaluation_read")
        with self._lock:
            if application_id is not None and self._is_employee(actor):
                application = self._get_application_record(application_id)
                self._scope_check(actor, application["person_ref"])
            records = list(self._evaluations.values())
            if application_id is not None:
                records = [r for r in records if r["application_id"] == application_id]
            if self._is_employee(actor):
                name = getattr(actor, "name", None)
                records = [r for r in records if self._evaluation_person_ref(r) == name]
            return [self._copy_evaluation(r) for r in records]

    # -- lifecycle cases (Core 6) ----------------------------------------------

    def create_lifecycle_case(self, person_ref, kind, actor, task_titles=None):
        """Create an onboarding/separation lifecycle case for a person.

        Action: lifecycle_write. The person (by person_ref) must
        exist. Tasks start ``pending`` with sequential ``t-N`` ids;
        no status is stored (status is derived at read time).
        """
        _require_actor(actor, "lifecycle_write")
        _validate_non_empty(person_ref, "person_ref")
        if kind not in LIFECYCLE_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(LIFECYCLE_KINDS),))
        if task_titles is None:
            task_titles = []
        if not isinstance(task_titles, (list, tuple)):
            raise ValidationError("task_titles must be a list")
        for title in task_titles:
            _validate_non_empty(title, "task title")
        with self._lock:
            self._require_person(person_ref)
            case_id = self._next_id("lif")
            tasks = [
                {"task_id": "t-%d" % (i + 1), "title": title, "state": "pending"}
                for i, title in enumerate(task_titles)
            ]
            record = {
                "id": case_id,
                "person_ref": person_ref,
                "kind": kind,
                "tasks": tasks,
                "cancelled": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._lifecycle[case_id] = record
            self._audit(actor, "lifecycle_create", case_id,
                        details={"person_ref": person_ref, "kind": kind})
            return self._lifecycle_view(record)

    def add_task(self, case_id, title, actor):
        """Append a pending task to a lifecycle case. Action: lifecycle_write."""
        _require_actor(actor, "lifecycle_write")
        _validate_non_empty(title, "task title")
        with self._lock:
            record = self._get_lifecycle_record(case_id)
            task_id = "t-%d" % (len(record["tasks"]) + 1)
            record["tasks"].append({"task_id": task_id, "title": title, "state": "pending"})
            self._audit(actor, "lifecycle_add_task", case_id, details={"task_id": task_id})
            return self._lifecycle_view(record)

    def set_task_state(self, case_id, task_id, state, actor):
        """Set one task's state on a lifecycle case. Action: lifecycle_write."""
        _require_actor(actor, "lifecycle_write")
        if state not in TASK_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(TASK_STATES),))
        with self._lock:
            record = self._get_lifecycle_record(case_id)
            for task in record["tasks"]:
                if task["task_id"] == task_id:
                    task["state"] = state
                    self._audit(actor, "lifecycle_set_task_state", case_id,
                                details={"task_id": task_id, "state": state})
                    return self._lifecycle_view(record)
            raise NotFoundError("task not found: %r" % (task_id,))

    def cancel_case(self, case_id, actor):
        """Cancel a lifecycle case (a recorded event). Action: lifecycle_write."""
        _require_actor(actor, "lifecycle_write")
        with self._lock:
            record = self._get_lifecycle_record(case_id)
            record["cancelled"] = True
            self._audit(actor, "lifecycle_cancel", case_id, details={})
            return self._lifecycle_view(record)

    def _derive_case_status(self, case):
        """Derive cancelled/not_started/in_progress/complete deterministically.

        MUTATION DRILL NOTE: the complete branch of this function
        (``HrStore._derive_case_status`` in ``src/hr/store.py``) is
        the load-bearing invariant for the negative-control drill:
        a case whose every task is done/waived must read
        ``complete``, never ``in_progress``.
        """
        if case["cancelled"]:
            return "cancelled"
        tasks = case["tasks"]
        if not tasks or all(t["state"] == "pending" for t in tasks):
            return "not_started"
        if all(t["state"] in ("done", "waived") for t in tasks):
            return "complete"
        return "in_progress"

    def _lifecycle_view(self, record):
        view = self._copy_lifecycle(record)
        view["status"] = self._derive_case_status(record)
        view["complete"] = view["status"] == "complete"
        return view

    def get_lifecycle_case(self, case_id, actor=None):
        """Return one lifecycle case with derived status.

        Action: lifecycle_read (+ employee scope).
        """
        _maybe_require(actor, "lifecycle_read")
        with self._lock:
            record = self._get_lifecycle_record(case_id)
            self._scope_check(actor, record["person_ref"])
            return self._lifecycle_view(record)

    def list_lifecycle_cases(self, actor=None, person_ref=None):
        """Return lifecycle cases with derived status. Action: lifecycle_read."""
        _maybe_require(actor, "lifecycle_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._lifecycle.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            return [self._lifecycle_view(r) for r in self._scoped(actor, records)]

    # -- performance reviews (Core 7) ----------------------------------------------

    def create_performance_review(self, person_ref, cycle, actor,
                                  period_start=None, period_end=None):
        """Create a performance review record for a person.

        Action: performance_write. The person (by person_ref) must
        exist; ISO dates are validated and period_end must not
        precede period_start.
        """
        _require_actor(actor, "performance_write")
        _validate_non_empty(person_ref, "person_ref")
        _validate_non_empty(cycle, "cycle")
        start = _validate_date(period_start, "period_start") if period_start is not None else None
        end = _validate_date(period_end, "period_end") if period_end is not None else None
        if start is not None and end is not None and end < start:
            raise ValidationError("period_end must not be before period_start")
        with self._lock:
            self._require_person(person_ref)
            review_id = self._next_id("rev")
            record = {
                "id": review_id,
                "person_ref": person_ref,
                "cycle": cycle,
                "period_start": period_start,
                "period_end": period_end,
                "state": "planned",
                "outcome": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reviews[review_id] = record
            self._audit(actor, "performance_create", review_id,
                        details={"person_ref": person_ref, "cycle": cycle})
            return dict(record)

    def set_review_state(self, review_id, state, actor, outcome=None):
        """Set a performance review's state. Action: performance_write.

        ``outcome`` is an optional recorded label string stored on
        the record when given.
        """
        _require_actor(actor, "performance_write")
        if state not in REVIEW_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(REVIEW_STATES),))
        if outcome is not None and not isinstance(outcome, str):
            raise ValidationError("outcome must be a string")
        with self._lock:
            record = self._get_review_record(review_id)
            record["state"] = state
            if outcome is not None:
                record["outcome"] = outcome
            self._audit(actor, "performance_set_state", review_id,
                        details={"state": state, "outcome": outcome})
            return dict(record)

    def get_performance_review(self, review_id, actor=None):
        """Return one performance review. Action: performance_read (+ scope)."""
        _maybe_require(actor, "performance_read")
        with self._lock:
            record = self._get_review_record(review_id)
            self._scope_check(actor, record["person_ref"])
            return dict(record)

    def list_performance_reviews(self, actor=None, person_ref=None):
        """Return performance reviews, optionally filtered. Action: performance_read."""
        _maybe_require(actor, "performance_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._reviews.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- benefits records (Core 8) ----------------------------------------------

    def create_benefits_record(self, person_ref, kind, plan_ref, actor):
        """Create a benefits record for a person. Action: benefits_write.

        The person (by person_ref) must exist. ``plan_ref`` is an
        opaque caller-supplied plan reference only.
        """
        _require_actor(actor, "benefits_write")
        _validate_non_empty(person_ref, "person_ref")
        if kind not in BENEFITS_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(BENEFITS_KINDS),))
        _validate_non_empty(plan_ref, "plan_ref")
        with self._lock:
            self._require_person(person_ref)
            record_id = self._next_id("ben")
            record = {
                "id": record_id,
                "person_ref": person_ref,
                "kind": kind,
                "plan_ref": plan_ref,
                "state": "pending",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._benefits[record_id] = record
            self._audit(actor, "benefits_create", record_id,
                        details={"person_ref": person_ref, "kind": kind})
            return dict(record)

    def set_benefits_state(self, record_id, state, actor):
        """Set a benefits record's state. Action: benefits_write."""
        _require_actor(actor, "benefits_write")
        if state not in BENEFITS_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(BENEFITS_STATES),))
        with self._lock:
            record = self._get_benefits_record(record_id)
            record["state"] = state
            self._audit(actor, "benefits_set_state", record_id, details={"state": state})
            return dict(record)

    def get_benefits_record(self, record_id, actor=None):
        """Return one benefits record. Action: benefits_read (+ scope)."""
        _maybe_require(actor, "benefits_read")
        with self._lock:
            record = self._get_benefits_record(record_id)
            self._scope_check(actor, record["person_ref"])
            return dict(record)

    def list_benefits_records(self, actor=None, person_ref=None):
        """Return benefits records, optionally filtered. Action: benefits_read."""
        _maybe_require(actor, "benefits_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._benefits.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- personnel cases (Core 9) ----------------------------------------------

    def create_case(self, person_ref, kind, title, actor):
        """Create a personnel case for a person. Action: case_write.

        The person (by person_ref) must exist.
        """
        _require_actor(actor, "case_write")
        _validate_non_empty(person_ref, "person_ref")
        if kind not in CASE_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(CASE_KINDS),))
        _validate_non_empty(title, "case title")
        with self._lock:
            self._require_person(person_ref)
            case_id = self._next_id("cas")
            record = {
                "id": case_id,
                "person_ref": person_ref,
                "kind": kind,
                "title": title,
                "state": "opened",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._cases[case_id] = record
            self._audit(actor, "case_create", case_id,
                        details={"person_ref": person_ref, "kind": kind})
            return dict(record)

    def set_case_state(self, case_id, state, actor):
        """Set a personnel case's state. Action: case_write."""
        _require_actor(actor, "case_write")
        if state not in CASE_STATES:
            raise ValidationError("state must be one of %s" % (", ".join(CASE_STATES),))
        with self._lock:
            record = self._get_case_record(case_id)
            record["state"] = state
            self._audit(actor, "case_set_state", case_id, details={"state": state})
            return dict(record)

    def get_case(self, case_id, actor=None):
        """Return one personnel case. Action: case_read (+ scope)."""
        _maybe_require(actor, "case_read")
        with self._lock:
            record = self._get_case_record(case_id)
            self._scope_check(actor, record["person_ref"])
            return dict(record)

    def list_cases(self, actor=None, person_ref=None):
        """Return personnel cases, optionally filtered. Action: case_read."""
        _maybe_require(actor, "case_read")
        if person_ref is not None:
            self._scope_check(actor, person_ref)
        with self._lock:
            records = list(self._cases.values())
            if person_ref is not None:
                records = [r for r in records if r["person_ref"] == person_ref]
            return [dict(r) for r in self._scoped(actor, records)]

    # -- reporting over the records (Core 10) --------------------------------

    def report(self, actor):
        """Counts/summaries over the substrate records only.

        Action: report_read. Lifecycle counts use the same derived
        status as the lifecycle reads.
        """
        _require_actor(actor, "report_read")
        with self._lock:
            persons_by_status = {s: 0 for s in PERSON_STATUSES}
            for record in self._persons.values():
                persons_by_status[record["status"]] += 1
            positions_by_status = {s: 0 for s in POSITION_STATUSES}
            for record in self._positions.values():
                positions_by_status[record["status"]] += 1
            vacancies_by_status = {s: 0 for s in VACANCY_STATUSES}
            for record in self._vacancies.values():
                vacancies_by_status[record["status"]] += 1
            applications_by_stage = {s: 0 for s in APPLICATION_STAGES}
            for record in self._applications.values():
                applications_by_stage[record["stage"]] += 1
            evaluations_by_state = {s: 0 for s in EVALUATION_STATES}
            for record in self._evaluations.values():
                evaluations_by_state[record["state"]] += 1
            lifecycle_by_status = {s: 0 for s in LIFECYCLE_STATUSES}
            for record in self._lifecycle.values():
                lifecycle_by_status[self._derive_case_status(record)] += 1
            reviews_by_state = {s: 0 for s in REVIEW_STATES}
            for record in self._reviews.values():
                reviews_by_state[record["state"]] += 1
            benefits_by_state = {s: 0 for s in BENEFITS_STATES}
            for record in self._benefits.values():
                benefits_by_state[record["state"]] += 1
            cases_by_state = {s: 0 for s in CASE_STATES}
            for record in self._cases.values():
                cases_by_state[record["state"]] += 1
            result = {
                "persons": len(self._persons),
                "persons_by_status": persons_by_status,
                "positions": len(self._positions),
                "positions_by_status": positions_by_status,
                "vacancies": len(self._vacancies),
                "vacancies_by_status": vacancies_by_status,
                "applications": len(self._applications),
                "applications_by_stage": applications_by_stage,
                "evaluations": len(self._evaluations),
                "evaluations_by_state": evaluations_by_state,
                "lifecycle_cases": len(self._lifecycle),
                "lifecycle_cases_by_status": lifecycle_by_status,
                "performance_reviews": len(self._reviews),
                "performance_reviews_by_state": reviews_by_state,
                "benefits_records": len(self._benefits),
                "benefits_records_by_state": benefits_by_state,
                "cases": len(self._cases),
                "cases_by_state": cases_by_state,
            }
            self._audit(actor, "report", "report", details={})
            return result
