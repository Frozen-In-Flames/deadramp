"""Construction store: organizations, projects, documents, contracts,
construction records (submittals, RFIs, milestones, dispatches,
inspections, punch items, incidents), workforce records (workers,
time entries, payrolls, violations, compliance), costs, derived
alerts, reports, and search.

Clean-room implementation of the contract.

Permission convention (mirrors the communication group): store
methods take an ``actor``. When the actor is a User-like object (it
has a ``role`` attribute) the store calls
:func:`construct.access.require` for the method's action *before* any
state change or id allocation, so a denied operation consumes no id
and changes nothing. Where a plain string is passed it carries
identity (for provenance) but no role, so there is nothing to enforce
against at this layer; the service layer, which knows the role
registry, is responsible for enforcement in that case -- and it
always passes User objects.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``org-``, ``prj-``, ``doc-``,
``con-``, ``sub-``, ``rfi-``, ``ms-``, ``dsp-``, ``insp-``, ``pun-``,
``inc-``, ``wrk-``, ``time-``, ``pay-``, ``vio-``, ``cost-``).

Money rule (everywhere): cent amounts must be ``int`` (``bool`` and
``float`` are rejected) and >= 0, or ``None``, else ValidationError.

Derived values (mirrors the education-training group's pattern):
a contract's expiry state, a record's overdue flag, a milestone's due
state, and a contractor's compliance status are DERIVED at read time
from stored fields and the reference ``now`` -- they are never
stored. Derivation lives in exactly three small methods,
:meth:`ConstructStore._contract_expiry_state`,
:meth:`ConstructStore._record_overdue` /
:meth:`ConstructStore._milestone_due_state`, and
:meth:`ConstructStore._contractor_compliance`, which the
negative-control drill patches.

Design constraint: a worker's ``reference`` is a REQUIRED opaque
caller-supplied string. This build NEVER stores a real government
identifier or SSN as such; it is an opaque external reference only.
The same opaque-reference rule applies to an organization's
``reference`` (optional).
"""

import copy
import threading
from datetime import datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

DOC_TYPES = ("drawing", "specification", "contract", "submittal", "form", "report", "other")
KNOWN_DOC_TYPES = frozenset(DOC_TYPES)
SEVERITIES = ("info", "warning", "critical")
KNOWN_SEVERITIES = frozenset(SEVERITIES)
COST_KINDS = ("budget", "estimate", "change_order", "actual")
KNOWN_COST_KINDS = frozenset(COST_KINDS)
INSPECTION_RESULTS = ("pass", "fail", "conditional")
KNOWN_INSPECTION_RESULTS = frozenset(INSPECTION_RESULTS)

PROJECT_TRANSITIONS = {
    "planned": frozenset({"active", "cancelled"}),
    "active": frozenset({"on_hold", "completed", "cancelled"}),
    "on_hold": frozenset({"active", "cancelled"}),
    "completed": frozenset({"closed"}),
    "closed": frozenset(),
    "cancelled": frozenset(),
}
CONTRACT_TRANSITIONS = {
    "draft": frozenset({"in_review", "terminated"}),
    "in_review": frozenset({"draft", "executed", "terminated"}),
    "executed": frozenset({"active", "terminated"}),
    "active": frozenset({"completed", "terminated"}),
    "completed": frozenset({"closed"}),
    "closed": frozenset(),
    "terminated": frozenset(),
}
SUBMITTAL_TRANSITIONS = {
    "draft": frozenset({"submitted"}),
    "submitted": frozenset({"under_review"}),
    "under_review": frozenset({"approved", "approved_as_noted", "revise_resubmit", "rejected"}),
    "revise_resubmit": frozenset({"submitted"}),
    "approved": frozenset(),
    "approved_as_noted": frozenset(),
    "rejected": frozenset(),
}
SUBMITTAL_TERMINAL = frozenset({"approved", "approved_as_noted", "rejected"})
RFI_TRANSITIONS = {
    "open": frozenset({"answered", "closed"}),
    "answered": frozenset({"closed", "open"}),
    "closed": frozenset(),
}
RFI_TERMINAL = frozenset({"closed"})
DISPATCH_TRANSITIONS = {
    "assigned": frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset({"completed", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}
PUNCH_TRANSITIONS = {
    "open": frozenset({"corrected"}),
    "corrected": frozenset({"verified", "open"}),
    "verified": frozenset(),
}
PUNCH_TERMINAL = frozenset({"verified"})
INCIDENT_TRANSITIONS = {
    "reported": frozenset({"under_review"}),
    "under_review": frozenset({"closed", "reported"}),
    "closed": frozenset(),
}


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


def _validate_optional_str(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string or None" % (what,))
    return value


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


def _coerce_now(now, what="now"):
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, datetime):
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now
    if isinstance(now, str):
        return _parse_iso_datetime(now, what)
    raise ValidationError("%s must be an ISO-8601 string or datetime" % (what,))


def _validate_attributes(attributes):
    if attributes is None:
        return {}
    if not isinstance(attributes, dict):
        raise ValidationError("attributes must be a dict")
    return copy.deepcopy(attributes)


def _validate_money(value, what):
    """Money rule: int (not bool) >= 0, or None."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents or None" % (what,))
    if value < 0:
        raise ValidationError("%s must be >= 0" % (what,))
    return value


def _validate_key_dates(key_dates):
    if key_dates is None:
        return []
    if not isinstance(key_dates, (list, tuple)):
        raise ValidationError("key_dates must be a list")
    result = []
    for item in key_dates:
        if not isinstance(item, dict):
            raise ValidationError("each key date must be an object with label and at")
        label = item.get("label")
        at = item.get("at")
        if not isinstance(label, str) or not label.strip():
            raise ValidationError("key date label must be a non-empty string")
        _parse_iso_datetime(at, "key date at")
        result.append(copy.deepcopy(item))
    return result


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class ConstructStore:
    """In-memory store for the construction records service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._orgs = {}
        self._projects = {}
        self._participants = {}
        self._documents = {}
        self._contracts = {}
        self._submittals = {}
        self._rfis = {}
        self._milestones = {}
        self._dispatches = {}
        self._inspections = {}
        self._punch_items = {}
        self._incidents = {}
        self._workers = {}
        self._time_entries = {}
        self._payrolls = {}
        self._violations = {}
        self._costs = {}
        self._counters = {
            "org": 0, "prj": 0, "doc": 0, "con": 0, "sub": 0, "rfi": 0,
            "ms": 0, "dsp": 0, "insp": 0, "pun": 0, "inc": 0, "wrk": 0,
            "time": 0, "pay": 0, "vio": 0, "cost": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _get_org_record(self, org_id):
        record = self._orgs.get(org_id)
        if record is None:
            raise NotFoundError("organization not found: %r" % (org_id,))
        return record

    def _get_project_record(self, project_id):
        record = self._projects.get(project_id)
        if record is None:
            raise NotFoundError("project not found: %r" % (project_id,))
        return record

    def _get_document_record(self, doc_id):
        record = self._documents.get(doc_id)
        if record is None:
            raise NotFoundError("document not found: %r" % (doc_id,))
        return record

    def _get_contract_record(self, contract_id):
        record = self._contracts.get(contract_id)
        if record is None:
            raise NotFoundError("contract not found: %r" % (contract_id,))
        return record

    def _get_submittal_record(self, submittal_id):
        record = self._submittals.get(submittal_id)
        if record is None:
            raise NotFoundError("submittal not found: %r" % (submittal_id,))
        return record

    def _get_rfi_record(self, rfi_id):
        record = self._rfis.get(rfi_id)
        if record is None:
            raise NotFoundError("rfi not found: %r" % (rfi_id,))
        return record

    def _get_milestone_record(self, milestone_id):
        record = self._milestones.get(milestone_id)
        if record is None:
            raise NotFoundError("milestone not found: %r" % (milestone_id,))
        return record

    def _get_dispatch_record(self, dispatch_id):
        record = self._dispatches.get(dispatch_id)
        if record is None:
            raise NotFoundError("dispatch not found: %r" % (dispatch_id,))
        return record

    def _get_inspection_record(self, inspection_id):
        record = self._inspections.get(inspection_id)
        if record is None:
            raise NotFoundError("inspection not found: %r" % (inspection_id,))
        return record

    def _get_punch_record(self, punch_id):
        record = self._punch_items.get(punch_id)
        if record is None:
            raise NotFoundError("punch item not found: %r" % (punch_id,))
        return record

    def _get_incident_record(self, incident_id):
        record = self._incidents.get(incident_id)
        if record is None:
            raise NotFoundError("incident not found: %r" % (incident_id,))
        return record

    def _get_worker_record(self, worker_id):
        record = self._workers.get(worker_id)
        if record is None:
            raise NotFoundError("worker not found: %r" % (worker_id,))
        return record

    def _get_time_entry_record(self, entry_id):
        record = self._time_entries.get(entry_id)
        if record is None:
            raise NotFoundError("time entry not found: %r" % (entry_id,))
        return record

    def _get_payroll_record(self, payroll_id):
        record = self._payrolls.get(payroll_id)
        if record is None:
            raise NotFoundError("payroll not found: %r" % (payroll_id,))
        return record

    def _get_violation_record(self, violation_id):
        record = self._violations.get(violation_id)
        if record is None:
            raise NotFoundError("violation not found: %r" % (violation_id,))
        return record

    def _get_cost_record(self, cost_id):
        record = self._costs.get(cost_id)
        if record is None:
            raise NotFoundError("cost entry not found: %r" % (cost_id,))
        return record

    @staticmethod
    def _copy(record):
        return copy.deepcopy(record)

    def _transition(self, record, transitions, to_status, kind, record_id):
        allowed = transitions[record["status"]]
        if to_status not in allowed:
            raise ValidationError(
                "%s %r cannot transition from %r to %r"
                % (kind, record_id, record["status"], to_status)
            )
        record["status"] = to_status
        record["updated_utc"] = _utc_now()
        return record

    # -- derivation (single points; see module docstring) -------------

    def _contract_expiry_state(self, contract, now_dt):
        """Derived contract expiry state at ``now_dt``.

        MUTATION DRILL NOTE: this method
        (``ConstructStore._contract_expiry_state`` in
        ``src/construct/store.py``) is a load-bearing derivation
        point for the negative-control drill: an executed contract
        past its ``end_at`` must read ``expiry_state='expired'``.
        Derived values are NEVER stored.
        """
        if contract["status"] in ("draft", "in_review"):
            return "pre_execution"
        if contract["status"] in ("completed", "closed", "terminated"):
            return "ended"
        if contract.get("end_at") is None:
            return "open_ended"
        end_dt = _parse_iso_datetime(contract["end_at"], "end_at")
        if now_dt > end_dt:
            return "expired"
        if end_dt - now_dt <= timedelta(days=30):
            return "expiring"
        return "active"

    def _record_overdue(self, record, now_dt, terminal_statuses):
        """True iff the record has a due date, is not terminal, and
        ``now`` is past due. Derived at read time; never stored."""
        if record.get("due_at") is None:
            return False
        if record["status"] in terminal_statuses:
            return False
        due_dt = _parse_iso_datetime(record["due_at"], "due_at")
        return now_dt > due_dt

    def _milestone_due_state(self, milestone, now_dt):
        """Derived milestone due state at ``now_dt``: ``completed``
        if completed, else ``overdue`` / ``due_soon`` (within 7 days)
        / ``upcoming``. Derived at read time; never stored."""
        if milestone.get("completed"):
            return "completed"
        due_dt = _parse_iso_datetime(milestone["due_at"], "due_at")
        if now_dt > due_dt:
            return "overdue"
        if due_dt - now_dt <= timedelta(days=7):
            return "due_soon"
        return "upcoming"

    def _contractor_compliance(self, project_id, org_id):
        """Derived compliance status for one (project, org) pair.

        MUTATION DRILL NOTE: this method
        (``ConstructStore._contractor_compliance`` in
        ``src/construct/store.py``) is THE load-bearing derivation
        point for the mutation drill: a participant with an open
        violation must read ``noncompliant``. ``noncompliant`` if any
        open violation exists for the pair; else ``compliant`` if at
        least one certified payroll exists for the pair; else
        ``no_records``. Derived at read time; never stored.
        """
        for violation in self._violations.values():
            if (violation["project_id"] == project_id
                    and violation["org_id"] == org_id
                    and violation["status"] == "open"):
                return "noncompliant"
        for payroll in self._payrolls.values():
            if (payroll["project_id"] == project_id
                    and payroll["org_id"] == org_id
                    and payroll["certified"] is True):
                return "compliant"
        return "no_records"

    def _contract_view(self, contract, now_dt):
        view = copy.deepcopy(contract)
        view["expiry_state"] = self._contract_expiry_state(contract, now_dt)
        if contract.get("end_at") is not None:
            end_dt = _parse_iso_datetime(contract["end_at"], "end_at")
            view["days_to_expiry"] = int((end_dt - now_dt).total_seconds() // 86400)
        else:
            view["days_to_expiry"] = None
        return view

    def _submittal_view(self, record, now_dt):
        view = copy.deepcopy(record)
        view["overdue"] = self._record_overdue(record, now_dt, SUBMITTAL_TERMINAL)
        return view

    def _rfi_view(self, record, now_dt):
        view = copy.deepcopy(record)
        view["overdue"] = self._record_overdue(record, now_dt, RFI_TERMINAL)
        return view

    def _punch_view(self, record, now_dt):
        view = copy.deepcopy(record)
        view["overdue"] = self._record_overdue(record, now_dt, PUNCH_TERMINAL)
        return view

    def _milestone_view(self, record, now_dt):
        view = copy.deepcopy(record)
        view["due_state"] = self._milestone_due_state(record, now_dt)
        return view

    # -- organizations -----------------------------------------------

    def create_org(self, name, actor, reference=None, attributes=None):
        """Create an organization. Action: org_write. Id prefix: org-.

        ``reference`` is an opaque external reference string or None.
        """
        _require_actor(actor, "org_write")
        _validate_non_empty(name, "organization name")
        _validate_optional_str(reference, "reference")
        attributes = _validate_attributes(attributes)
        with self._lock:
            org_id = self._next_id("org")
            org = {
                "id": org_id,
                "name": name,
                "reference": reference,
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._orgs[org_id] = org
            self._audit(actor, "org_create", org_id, details={"name": name})
            return self._copy(org)

    def get_org(self, org_id, actor=None):
        """Return one organization. Action: org_read."""
        _maybe_require(actor, "org_read")
        with self._lock:
            return self._copy(self._get_org_record(org_id))

    def list_orgs(self, actor=None):
        """Return organizations sorted by id. Action: org_read."""
        _maybe_require(actor, "org_read")
        with self._lock:
            orgs = sorted(self._orgs.values(), key=lambda o: _id_num(o["id"]))
            return [self._copy(o) for o in orgs]

    # -- projects ------------------------------------------------------

    def create_project(self, name, actor, agency_ref=None, location=None,
                       start_at=None, end_at=None):
        """Create a project with status ``planned``.

        Action: project_write. Id prefix: prj-. Dates are
        ISO-validated when given.
        """
        _require_actor(actor, "project_write")
        _validate_non_empty(name, "project name")
        _validate_optional_str(agency_ref, "agency_ref")
        _validate_optional_str(location, "location")
        if start_at is not None:
            _parse_iso_datetime(start_at, "start_at")
        if end_at is not None:
            _parse_iso_datetime(end_at, "end_at")
        with self._lock:
            project_id = self._next_id("prj")
            now = _utc_now()
            project = {
                "id": project_id,
                "name": name,
                "agency_ref": agency_ref,
                "location": location,
                "start_at": start_at,
                "end_at": end_at,
                "status": "planned",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._projects[project_id] = project
            self._participants[project_id] = []
            self._audit(actor, "project_create", project_id, details={"name": name})
            return self._copy(project)

    def transition_project(self, project_id, actor, to_status):
        """Transition a project's status. Action: project_write."""
        _require_actor(actor, "project_write")
        with self._lock:
            project = self._get_project_record(project_id)
            self._transition(project, PROJECT_TRANSITIONS, to_status, "project", project_id)
            self._audit(actor, "project_transition", project_id,
                        details={"to_status": to_status})
            return self._copy(project)

    def get_project(self, project_id, actor=None):
        """Return one project. Action: project_read."""
        _maybe_require(actor, "project_read")
        with self._lock:
            return self._copy(self._get_project_record(project_id))

    def list_projects(self, actor=None, status=None):
        """Return projects, optionally filtered by status.

        Action: project_read.
        """
        _maybe_require(actor, "project_read")
        with self._lock:
            projects = list(self._projects.values())
            if status is not None:
                projects = [p for p in projects if p["status"] == status]
            return [self._copy(p) for p in projects]

    def add_participant(self, project_id, org_id, actor, tier, role=None):
        """Add an organization as a project participant.

        Action: project_write. ``tier`` must be an int (not bool)
        >= 1 (1 = prime). Duplicate org on the same project ->
        ValidationError; unknown ids -> NotFoundError.
        """
        _require_actor(actor, "project_write")
        if isinstance(tier, bool) or not isinstance(tier, int) or tier < 1:
            raise ValidationError("tier must be an integer >= 1")
        _validate_optional_str(role, "role")
        with self._lock:
            self._get_project_record(project_id)
            self._get_org_record(org_id)
            participants = self._participants.setdefault(project_id, [])
            for existing in participants:
                if existing["org_id"] == org_id:
                    raise ValidationError(
                        "organization %r is already a participant of project %r"
                        % (org_id, project_id)
                    )
            participant = {
                "project_id": project_id,
                "org_id": org_id,
                "tier": tier,
                "role": role,
                "added_by": actor_name(actor),
                "added_utc": _utc_now(),
            }
            participants.append(participant)
            self._audit(actor, "participant_add", project_id,
                        details={"org_id": org_id, "tier": tier})
            return dict(participant)

    def list_participants(self, project_id, actor=None):
        """Return participant dicts sorted by (tier, org_id number).

        Action: project_read.
        """
        _maybe_require(actor, "project_read")
        with self._lock:
            self._get_project_record(project_id)
            participants = list(self._participants.get(project_id, []))
            participants.sort(key=lambda p: (p["tier"], _id_num(p["org_id"])))
            return [dict(p) for p in participants]

    # -- documents -----------------------------------------------------

    def create_document(self, actor, title, project_id=None, doc_type="other",
                        checksum=None, note=None):
        """Create a document at version 1. Action: document_write.

        Id prefix: doc-. The project must exist if given. Version 1
        is ``{version, checksum, note, ts}``; the record mirrors the
        current checksum/note/version.
        """
        _require_actor(actor, "document_write")
        _validate_non_empty(title, "document title")
        if doc_type not in KNOWN_DOC_TYPES:
            raise ValidationError("doc_type must be one of %s" % (", ".join(DOC_TYPES),))
        _validate_optional_str(checksum, "checksum")
        _validate_optional_str(note, "note")
        with self._lock:
            if project_id is not None:
                self._get_project_record(project_id)
            doc_id = self._next_id("doc")
            now = _utc_now()
            first = {"version": 1, "checksum": checksum, "note": note, "ts": now}
            document = {
                "id": doc_id,
                "title": title,
                "project_id": project_id,
                "doc_type": doc_type,
                "checksum": checksum,
                "note": note,
                "version": 1,
                "versions": [first],
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._documents[doc_id] = document
            self._audit(actor, "document_create", doc_id, details={"title": title})
            return self._copy(document)

    def update_document(self, doc_id, actor, checksum=None, note=None):
        """Append a new version to a document. Action: document_write.

        At least one of checksum/note must be given, else
        ValidationError. The unchanged field is carried forward.
        """
        _require_actor(actor, "document_write")
        if checksum is None and note is None:
            raise ValidationError("update_document requires at least one of checksum, note")
        _validate_optional_str(checksum, "checksum")
        _validate_optional_str(note, "note")
        with self._lock:
            document = self._get_document_record(doc_id)
            new_version = {
                "version": document["version"] + 1,
                "checksum": checksum if checksum is not None else document["checksum"],
                "note": note if note is not None else document["note"],
                "ts": _utc_now(),
            }
            document["versions"].append(new_version)
            document["version"] = new_version["version"]
            document["checksum"] = new_version["checksum"]
            document["note"] = new_version["note"]
            document["updated_utc"] = new_version["ts"]
            self._audit(actor, "document_update", doc_id,
                        details={"version": new_version["version"]})
            return self._copy(document)

    def get_document(self, doc_id, actor=None):
        """Return one document (versions in full). Action: document_read."""
        _maybe_require(actor, "document_read")
        with self._lock:
            return self._copy(self._get_document_record(doc_id))

    def list_documents(self, actor=None, project_id=None):
        """Return documents, optionally for one project.

        Action: document_read.
        """
        _maybe_require(actor, "document_read")
        with self._lock:
            docs = list(self._documents.values())
            if project_id is not None:
                docs = [d for d in docs if d["project_id"] == project_id]
            return [self._copy(d) for d in docs]

    # -- contracts -----------------------------------------------------

    def create_contract(self, actor, title, project_id, org_id=None,
                        value_cents=None, start_at=None, end_at=None, key_dates=None):
        """Create a contract with status ``draft``.

        Action: contract_write. Id prefix: con-. The project must
        exist; the org must exist if given; ``value_cents`` follows
        the money rule; ``key_dates`` is a list of
        ``{label: non-empty str, at: ISO datetime}`` validated and
        deep-copied.
        """
        _require_actor(actor, "contract_write")
        _validate_non_empty(title, "contract title")
        value_cents = _validate_money(value_cents, "value_cents")
        if start_at is not None:
            _parse_iso_datetime(start_at, "start_at")
        if end_at is not None:
            _parse_iso_datetime(end_at, "end_at")
        key_dates = _validate_key_dates(key_dates)
        with self._lock:
            self._get_project_record(project_id)
            if org_id is not None:
                self._get_org_record(org_id)
            contract_id = self._next_id("con")
            now = _utc_now()
            contract = {
                "id": contract_id,
                "title": title,
                "project_id": project_id,
                "org_id": org_id,
                "value_cents": value_cents,
                "start_at": start_at,
                "end_at": end_at,
                "key_dates": key_dates,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._contracts[contract_id] = contract
            self._audit(actor, "contract_create", contract_id, details={"title": title})
            return self._contract_view(contract, _coerce_now(None))

    def transition_contract(self, contract_id, actor, to_status):
        """Transition a contract's status. Action: contract_write."""
        _require_actor(actor, "contract_write")
        with self._lock:
            contract = self._get_contract_record(contract_id)
            self._transition(contract, CONTRACT_TRANSITIONS, to_status, "contract", contract_id)
            self._audit(actor, "contract_transition", contract_id,
                        details={"to_status": to_status})
            return self._contract_view(contract, _coerce_now(None))

    def get_contract(self, contract_id, actor=None, now=None):
        """Return one contract with derived expiry fields.

        Action: contract_read.
        """
        _maybe_require(actor, "contract_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return self._contract_view(self._get_contract_record(contract_id), now_dt)

    def list_contracts(self, actor=None, now=None, project_id=None, status=None):
        """Return contracts with derived expiry fields, optionally
        filtered. Action: contract_read."""
        _maybe_require(actor, "contract_read")
        now_dt = _coerce_now(now)
        with self._lock:
            contracts = list(self._contracts.values())
            if project_id is not None:
                contracts = [c for c in contracts if c["project_id"] == project_id]
            if status is not None:
                contracts = [c for c in contracts if c["status"] == status]
            return [self._contract_view(c, now_dt) for c in contracts]

    # -- submittals ------------------------------------------------------

    def create_submittal(self, actor, project_id, title, org_id=None, due_at=None):
        """Create a submittal with status ``draft``.

        Action: record_write. Id prefix: sub-.
        """
        _require_actor(actor, "record_write")
        _validate_non_empty(title, "submittal title")
        if due_at is not None:
            _parse_iso_datetime(due_at, "due_at")
        with self._lock:
            self._get_project_record(project_id)
            if org_id is not None:
                self._get_org_record(org_id)
            submittal_id = self._next_id("sub")
            now = _utc_now()
            record = {
                "id": submittal_id,
                "project_id": project_id,
                "title": title,
                "org_id": org_id,
                "due_at": due_at,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._submittals[submittal_id] = record
            self._audit(actor, "submittal_create", submittal_id, details={"title": title})
            return self._submittal_view(record, _coerce_now(None))

    def transition_submittal(self, submittal_id, actor, to_status):
        """Transition a submittal's status. Action: record_write."""
        _require_actor(actor, "record_write")
        with self._lock:
            record = self._get_submittal_record(submittal_id)
            self._transition(record, SUBMITTAL_TRANSITIONS, to_status, "submittal", submittal_id)
            self._audit(actor, "submittal_transition", submittal_id,
                        details={"to_status": to_status})
            return self._submittal_view(record, _coerce_now(None))

    def get_submittal(self, submittal_id, actor=None, now=None):
        """Return one submittal with derived ``overdue``. Action: record_read."""
        _maybe_require(actor, "record_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return self._submittal_view(self._get_submittal_record(submittal_id), now_dt)

    def list_submittals(self, actor=None, now=None, project_id=None, status=None):
        """Return submittals with derived ``overdue``, optionally
        filtered. Action: record_read."""
        _maybe_require(actor, "record_read")
        now_dt = _coerce_now(now)
        with self._lock:
            records = list(self._submittals.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            if status is not None:
                records = [r for r in records if r["status"] == status]
            return [self._submittal_view(r, now_dt) for r in records]

    # -- RFIs --------------------------------------------------------------

    def create_rfi(self, actor, project_id, question, org_id=None, due_at=None):
        """Create an RFI with status ``open``.

        Action: record_write. Id prefix: rfi-. ``question`` must be
        non-empty.
        """
        _require_actor(actor, "record_write")
        _validate_non_empty(question, "rfi question")
        if due_at is not None:
            _parse_iso_datetime(due_at, "due_at")
        with self._lock:
            self._get_project_record(project_id)
            if org_id is not None:
                self._get_org_record(org_id)
            rfi_id = self._next_id("rfi")
            now = _utc_now()
            record = {
                "id": rfi_id,
                "project_id": project_id,
                "question": question,
                "org_id": org_id,
                "due_at": due_at,
                "status": "open",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._rfis[rfi_id] = record
            self._audit(actor, "rfi_create", rfi_id, details={"question": question})
            return self._rfi_view(record, _coerce_now(None))

    def transition_rfi(self, rfi_id, actor, to_status):
        """Transition an RFI's status. Action: record_write."""
        _require_actor(actor, "record_write")
        with self._lock:
            record = self._get_rfi_record(rfi_id)
            self._transition(record, RFI_TRANSITIONS, to_status, "rfi", rfi_id)
            self._audit(actor, "rfi_transition", rfi_id, details={"to_status": to_status})
            return self._rfi_view(record, _coerce_now(None))

    def get_rfi(self, rfi_id, actor=None, now=None):
        """Return one RFI with derived ``overdue``. Action: record_read."""
        _maybe_require(actor, "record_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return self._rfi_view(self._get_rfi_record(rfi_id), now_dt)

    def list_rfis(self, actor=None, now=None, project_id=None, status=None):
        """Return RFIs with derived ``overdue``, optionally filtered.

        Action: record_read.
        """
        _maybe_require(actor, "record_read")
        now_dt = _coerce_now(now)
        with self._lock:
            records = list(self._rfis.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            if status is not None:
                records = [r for r in records if r["status"] == status]
            return [self._rfi_view(r, now_dt) for r in records]

    # -- milestones ----------------------------------------------------------

    def create_milestone(self, actor, project_id, name, due_at):
        """Create a milestone. Action: record_write. Id prefix: ms-.

        ``due_at`` is REQUIRED and ISO-validated. ``completed``
        starts False, ``completed_at`` starts None.
        """
        _require_actor(actor, "record_write")
        _validate_non_empty(name, "milestone name")
        _parse_iso_datetime(due_at, "due_at")
        with self._lock:
            self._get_project_record(project_id)
            milestone_id = self._next_id("ms")
            now = _utc_now()
            record = {
                "id": milestone_id,
                "project_id": project_id,
                "name": name,
                "due_at": due_at,
                "completed": False,
                "completed_at": None,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._milestones[milestone_id] = record
            self._audit(actor, "milestone_create", milestone_id, details={"name": name})
            return self._milestone_view(record, _coerce_now(None))

    def complete_milestone(self, milestone_id, actor, completed_at=None):
        """Complete a milestone. Action: record_write.

        Only when not already completed, else ValidationError.
        ``completed_at`` defaults to now (ISO string).
        """
        _require_actor(actor, "record_write")
        if completed_at is not None:
            _parse_iso_datetime(completed_at, "completed_at")
        with self._lock:
            record = self._get_milestone_record(milestone_id)
            if record["completed"]:
                raise ValidationError(
                    "milestone %r is already completed" % (milestone_id,)
                )
            record["completed"] = True
            record["completed_at"] = completed_at if completed_at is not None else _utc_now()
            record["updated_utc"] = _utc_now()
            self._audit(actor, "milestone_complete", milestone_id,
                        details={"completed_at": record["completed_at"]})
            return self._milestone_view(record, _coerce_now(None))

    def get_milestone(self, milestone_id, actor=None, now=None):
        """Return one milestone with derived ``due_state``.

        Action: record_read.
        """
        _maybe_require(actor, "record_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return self._milestone_view(self._get_milestone_record(milestone_id), now_dt)

    def list_milestones(self, actor=None, now=None, project_id=None):
        """Return milestones with derived ``due_state``, optionally
        for one project. Action: record_read."""
        _maybe_require(actor, "record_read")
        now_dt = _coerce_now(now)
        with self._lock:
            records = list(self._milestones.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [self._milestone_view(r, now_dt) for r in records]

    # -- dispatches ------------------------------------------------------------

    def create_dispatch(self, actor, project_id, task, org_id=None,
                        worker_ref=None, scheduled_for=None):
        """Create a dispatch with status ``assigned``.

        Action: record_write. Id prefix: dsp-.
        """
        _require_actor(actor, "record_write")
        _validate_non_empty(task, "dispatch task")
        _validate_optional_str(worker_ref, "worker_ref")
        if scheduled_for is not None:
            _parse_iso_datetime(scheduled_for, "scheduled_for")
        with self._lock:
            self._get_project_record(project_id)
            if org_id is not None:
                self._get_org_record(org_id)
            dispatch_id = self._next_id("dsp")
            now = _utc_now()
            record = {
                "id": dispatch_id,
                "project_id": project_id,
                "task": task,
                "org_id": org_id,
                "worker_ref": worker_ref,
                "scheduled_for": scheduled_for,
                "status": "assigned",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._dispatches[dispatch_id] = record
            self._audit(actor, "dispatch_create", dispatch_id, details={"task": task})
            return self._copy(record)

    def transition_dispatch(self, dispatch_id, actor, to_status):
        """Transition a dispatch's status. Action: record_write."""
        _require_actor(actor, "record_write")
        with self._lock:
            record = self._get_dispatch_record(dispatch_id)
            self._transition(record, DISPATCH_TRANSITIONS, to_status, "dispatch", dispatch_id)
            self._audit(actor, "dispatch_transition", dispatch_id,
                        details={"to_status": to_status})
            return self._copy(record)

    def get_dispatch(self, dispatch_id, actor=None):
        """Return one dispatch. Action: record_read."""
        _maybe_require(actor, "record_read")
        with self._lock:
            return self._copy(self._get_dispatch_record(dispatch_id))

    def list_dispatches(self, actor=None, project_id=None):
        """Return dispatches, optionally for one project.

        Action: record_read.
        """
        _maybe_require(actor, "record_read")
        with self._lock:
            records = list(self._dispatches.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [self._copy(r) for r in records]

    # -- inspections -----------------------------------------------------------

    def create_inspection(self, actor, project_id, inspection_type,
                          inspector_ref=None, occurred_at=None, result=None):
        """Create an inspection. Action: record_write. Id prefix: insp-.

        ``result`` must be one of (pass, fail, conditional) or None.
        Inspections are IMMUTABLE: there is deliberately no update API.
        """
        _require_actor(actor, "record_write")
        _validate_non_empty(inspection_type, "inspection_type")
        _validate_optional_str(inspector_ref, "inspector_ref")
        if occurred_at is not None:
            _parse_iso_datetime(occurred_at, "occurred_at")
        if result is not None and result not in KNOWN_INSPECTION_RESULTS:
            raise ValidationError(
                "result must be one of %s or None" % (", ".join(INSPECTION_RESULTS),))
        with self._lock:
            self._get_project_record(project_id)
            inspection_id = self._next_id("insp")
            record = {
                "id": inspection_id,
                "project_id": project_id,
                "inspection_type": inspection_type,
                "inspector_ref": inspector_ref,
                "occurred_at": occurred_at,
                "result": result,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._inspections[inspection_id] = record
            self._audit(actor, "inspection_create", inspection_id,
                        details={"inspection_type": inspection_type})
            return self._copy(record)

    def get_inspection(self, inspection_id, actor=None):
        """Return one inspection. Action: record_read."""
        _maybe_require(actor, "record_read")
        with self._lock:
            return self._copy(self._get_inspection_record(inspection_id))

    def list_inspections(self, actor=None, project_id=None):
        """Return inspections, optionally for one project.

        Action: record_read.
        """
        _maybe_require(actor, "record_read")
        with self._lock:
            records = list(self._inspections.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [self._copy(r) for r in records]

    # -- punch items -------------------------------------------------------------

    def create_punch_item(self, actor, project_id, description,
                          inspection_id=None, org_id=None, due_at=None):
        """Create a punch item with status ``open``.

        Action: record_write. Id prefix: pun-. The inspection and
        org must exist if given.
        """
        _require_actor(actor, "record_write")
        _validate_non_empty(description, "punch item description")
        if due_at is not None:
            _parse_iso_datetime(due_at, "due_at")
        with self._lock:
            self._get_project_record(project_id)
            if inspection_id is not None:
                self._get_inspection_record(inspection_id)
            if org_id is not None:
                self._get_org_record(org_id)
            punch_id = self._next_id("pun")
            now = _utc_now()
            record = {
                "id": punch_id,
                "project_id": project_id,
                "description": description,
                "inspection_id": inspection_id,
                "org_id": org_id,
                "due_at": due_at,
                "status": "open",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._punch_items[punch_id] = record
            self._audit(actor, "punch_create", punch_id, details={"description": description})
            return self._punch_view(record, _coerce_now(None))

    def transition_punch_item(self, punch_id, actor, to_status):
        """Transition a punch item's status. Action: record_write."""
        _require_actor(actor, "record_write")
        with self._lock:
            record = self._get_punch_record(punch_id)
            self._transition(record, PUNCH_TRANSITIONS, to_status, "punch item", punch_id)
            self._audit(actor, "punch_transition", punch_id,
                        details={"to_status": to_status})
            return self._punch_view(record, _coerce_now(None))

    def get_punch_item(self, punch_id, actor=None, now=None):
        """Return one punch item with derived ``overdue``.

        Action: record_read.
        """
        _maybe_require(actor, "record_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return self._punch_view(self._get_punch_record(punch_id), now_dt)

    def list_punch_items(self, actor=None, now=None, project_id=None):
        """Return punch items with derived ``overdue``, optionally
        for one project. Action: record_read."""
        _maybe_require(actor, "record_read")
        now_dt = _coerce_now(now)
        with self._lock:
            records = list(self._punch_items.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            return [self._punch_view(r, now_dt) for r in records]

    # -- incidents -----------------------------------------------------------------

    def create_incident(self, actor, project_id, category, description,
                        severity="info", occurred_at=None):
        """Create an incident with status ``reported``.

        Action: record_write. Id prefix: inc-. ``category`` and
        ``description`` must be non-empty; ``severity`` must be one
        of (info, warning, critical).
        """
        _require_actor(actor, "record_write")
        _validate_non_empty(category, "incident category")
        _validate_non_empty(description, "incident description")
        if severity not in KNOWN_SEVERITIES:
            raise ValidationError("severity must be one of %s" % (", ".join(SEVERITIES),))
        if occurred_at is not None:
            _parse_iso_datetime(occurred_at, "occurred_at")
        with self._lock:
            self._get_project_record(project_id)
            incident_id = self._next_id("inc")
            now = _utc_now()
            record = {
                "id": incident_id,
                "project_id": project_id,
                "category": category,
                "description": description,
                "severity": severity,
                "occurred_at": occurred_at,
                "status": "reported",
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._incidents[incident_id] = record
            self._audit(actor, "incident_create", incident_id,
                        details={"category": category, "severity": severity})
            return self._copy(record)

    def transition_incident(self, incident_id, actor, to_status):
        """Transition an incident's status. Action: record_write."""
        _require_actor(actor, "record_write")
        with self._lock:
            record = self._get_incident_record(incident_id)
            self._transition(record, INCIDENT_TRANSITIONS, to_status, "incident", incident_id)
            self._audit(actor, "incident_transition", incident_id,
                        details={"to_status": to_status})
            return self._copy(record)

    def get_incident(self, incident_id, actor=None):
        """Return one incident. Action: record_read."""
        _maybe_require(actor, "record_read")
        with self._lock:
            return self._copy(self._get_incident_record(incident_id))

    def list_incidents(self, actor=None, project_id=None, status=None):
        """Return incidents, optionally filtered. Action: record_read."""
        _maybe_require(actor, "record_read")
        with self._lock:
            records = list(self._incidents.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            if status is not None:
                records = [r for r in records if r["status"] == status]
            return [self._copy(r) for r in records]

    # -- workers ---------------------------------------------------------------------

    def create_worker(self, actor, project_id, org_id, reference, trade=None,
                      attributes=None):
        """Create a worker. Action: workforce_write. Id prefix: wrk-.

        ``reference`` is a REQUIRED non-empty OPAQUE caller-supplied
        string (design constraint: never a real government identifier
        or SSN). The project and org must exist.
        """
        _require_actor(actor, "workforce_write")
        _validate_non_empty(reference, "worker reference")
        _validate_optional_str(trade, "trade")
        attributes = _validate_attributes(attributes)
        with self._lock:
            self._get_project_record(project_id)
            self._get_org_record(org_id)
            worker_id = self._next_id("wrk")
            record = {
                "id": worker_id,
                "project_id": project_id,
                "org_id": org_id,
                "reference": reference,
                "trade": trade,
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workers[worker_id] = record
            self._audit(actor, "worker_create", worker_id, details={"reference": reference})
            return self._copy(record)

    def get_worker(self, worker_id, actor=None):
        """Return one worker. Action: workforce_read."""
        _maybe_require(actor, "workforce_read")
        with self._lock:
            return self._copy(self._get_worker_record(worker_id))

    def list_workers(self, actor=None, project_id=None, org_id=None):
        """Return workers, optionally filtered. Action: workforce_read."""
        _maybe_require(actor, "workforce_read")
        with self._lock:
            records = list(self._workers.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            if org_id is not None:
                records = [r for r in records if r["org_id"] == org_id]
            return [self._copy(r) for r in records]

    # -- time entries ------------------------------------------------------------------

    def create_time_entry(self, actor, worker_id, minutes, occurred_on=None, note=None):
        """Create a time entry. Action: workforce_write. Id prefix: time-.

        ``minutes`` must be an int (not bool) > 0; the worker must
        exist; ``occurred_on`` is ISO-validated when given. Time
        entries are IMMUTABLE: no update API.
        """
        _require_actor(actor, "workforce_write")
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValidationError("minutes must be a positive integer")
        if occurred_on is not None:
            _parse_iso_datetime(occurred_on, "occurred_on")
        _validate_optional_str(note, "note")
        with self._lock:
            self._get_worker_record(worker_id)
            entry_id = self._next_id("time")
            record = {
                "id": entry_id,
                "worker_id": worker_id,
                "minutes": minutes,
                "occurred_on": occurred_on,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._time_entries[entry_id] = record
            self._audit(actor, "time_entry_create", entry_id,
                        details={"worker_id": worker_id, "minutes": minutes})
            return self._copy(record)

    def get_time_entry(self, entry_id, actor=None):
        """Return one time entry. Action: workforce_read."""
        _maybe_require(actor, "workforce_read")
        with self._lock:
            return self._copy(self._get_time_entry_record(entry_id))

    def list_time_entries(self, actor=None, worker_id=None, project_id=None):
        """Return time entries, optionally filtered.

        Action: workforce_read. The ``project_id`` filter resolves
        through each worker's project_id.
        """
        _maybe_require(actor, "workforce_read")
        with self._lock:
            records = list(self._time_entries.values())
            if worker_id is not None:
                records = [r for r in records if r["worker_id"] == worker_id]
            if project_id is not None:
                records = [
                    r for r in records
                    if r["worker_id"] in self._workers
                    and self._workers[r["worker_id"]]["project_id"] == project_id
                ]
            return [self._copy(r) for r in records]

    # -- payrolls -------------------------------------------------------------------------

    def create_payroll(self, actor, project_id, org_id, period_start, period_end,
                       certified=False, worker_count=None, total_wages_cents=None):
        """Create a payroll record. Action: workforce_write. Id prefix: pay-.

        ``period_start`` / ``period_end`` are required ISO datetimes
        with end >= start, else ValidationError; ``certified`` must
        be a bool; ``worker_count`` int (not bool) >= 0 or None;
        ``total_wages_cents`` follows the money rule. Payrolls are
        IMMUTABLE: no update API.
        """
        _require_actor(actor, "workforce_write")
        start_dt = _parse_iso_datetime(period_start, "period_start")
        end_dt = _parse_iso_datetime(period_end, "period_end")
        if end_dt < start_dt:
            raise ValidationError("period_end must be >= period_start")
        if not isinstance(certified, bool):
            raise ValidationError("certified must be a bool")
        if worker_count is not None:
            if isinstance(worker_count, bool) or not isinstance(worker_count, int) or worker_count < 0:
                raise ValidationError("worker_count must be an integer >= 0 or None")
        total_wages_cents = _validate_money(total_wages_cents, "total_wages_cents")
        with self._lock:
            self._get_project_record(project_id)
            self._get_org_record(org_id)
            payroll_id = self._next_id("pay")
            record = {
                "id": payroll_id,
                "project_id": project_id,
                "org_id": org_id,
                "period_start": period_start,
                "period_end": period_end,
                "certified": certified,
                "worker_count": worker_count,
                "total_wages_cents": total_wages_cents,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._payrolls[payroll_id] = record
            self._audit(actor, "payroll_create", payroll_id,
                        details={"project_id": project_id, "org_id": org_id})
            return self._copy(record)

    def get_payroll(self, payroll_id, actor=None):
        """Return one payroll. Action: workforce_read."""
        _maybe_require(actor, "workforce_read")
        with self._lock:
            return self._copy(self._get_payroll_record(payroll_id))

    def list_payrolls(self, actor=None, project_id=None, org_id=None):
        """Return payrolls, optionally filtered. Action: workforce_read."""
        _maybe_require(actor, "workforce_read")
        with self._lock:
            records = list(self._payrolls.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            if org_id is not None:
                records = [r for r in records if r["org_id"] == org_id]
            return [self._copy(r) for r in records]

    # -- violations --------------------------------------------------------------------------

    def create_violation(self, actor, project_id, org_id, kind, description):
        """Create a violation with status ``open``.

        Action: violation_write (ADMIN ONLY via the permission
        matrix). Id prefix: vio-. ``kind`` and ``description`` must
        be non-empty.
        """
        _require_actor(actor, "violation_write")
        _validate_non_empty(kind, "violation kind")
        _validate_non_empty(description, "violation description")
        with self._lock:
            self._get_project_record(project_id)
            self._get_org_record(org_id)
            violation_id = self._next_id("vio")
            now = _utc_now()
            record = {
                "id": violation_id,
                "project_id": project_id,
                "org_id": org_id,
                "kind": kind,
                "description": description,
                "status": "open",
                "resolution": None,
                "resolved_utc": None,
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._violations[violation_id] = record
            self._audit(actor, "violation_create", violation_id, details={"kind": kind})
            return self._copy(record)

    def resolve_violation(self, violation_id, actor, resolution=None):
        """Resolve a violation. Action: violation_write.

        Only from status ``open``, else ValidationError. Sets status
        ``resolved``, ``resolution`` and ``resolved_utc``.
        """
        _require_actor(actor, "violation_write")
        _validate_optional_str(resolution, "resolution")
        with self._lock:
            record = self._get_violation_record(violation_id)
            if record["status"] != "open":
                raise ValidationError(
                    "violation %r cannot be resolved from status %r"
                    % (violation_id, record["status"])
                )
            record["status"] = "resolved"
            record["resolution"] = resolution
            record["resolved_utc"] = _utc_now()
            record["updated_utc"] = _utc_now()
            self._audit(actor, "violation_resolve", violation_id,
                        details={"resolution": resolution})
            return self._copy(record)

    def get_violation(self, violation_id, actor=None):
        """Return one violation. Action: workforce_read."""
        _maybe_require(actor, "workforce_read")
        with self._lock:
            return self._copy(self._get_violation_record(violation_id))

    def list_violations(self, actor=None, project_id=None, org_id=None, status=None):
        """Return violations, optionally filtered.

        Action: workforce_read.
        """
        _maybe_require(actor, "workforce_read")
        with self._lock:
            records = list(self._violations.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            if org_id is not None:
                records = [r for r in records if r["org_id"] == org_id]
            if status is not None:
                records = [r for r in records if r["status"] == status]
            return [self._copy(r) for r in records]

    # -- compliance derivation ------------------------------------------------------------------

    def contractor_compliance(self, project_id, org_id, actor=None):
        """Compliance view for one (project, org) pair.

        Action: workforce_read. Returns ``{project_id, org_id,
        status, certified_payrolls, open_violations}`` where
        ``status`` is derived by :meth:`_contractor_compliance`.
        Project and org must exist (NotFoundError).
        """
        _maybe_require(actor, "workforce_read")
        with self._lock:
            self._get_project_record(project_id)
            self._get_org_record(org_id)
            certified = sum(
                1 for p in self._payrolls.values()
                if p["project_id"] == project_id and p["org_id"] == org_id
                and p["certified"] is True
            )
            open_violations = sum(
                1 for v in self._violations.values()
                if v["project_id"] == project_id and v["org_id"] == org_id
                and v["status"] == "open"
            )
            return {
                "project_id": project_id,
                "org_id": org_id,
                "status": self._contractor_compliance(project_id, org_id),
                "certified_payrolls": certified,
                "open_violations": open_violations,
            }

    # -- costs --------------------------------------------------------------------------------------

    def create_cost_entry(self, actor, project_id, category, description,
                          kind="actual", budgeted_cents=None, actual_cents=None):
        """Create a cost entry. Action: cost_write. Id prefix: cost-.

        ``category`` / ``description`` must be non-empty; ``kind``
        must be one of (budget, estimate, change_order, actual);
        amounts follow the money rule. Cost entries are IMMUTABLE:
        no update API.
        """
        _require_actor(actor, "cost_write")
        _validate_non_empty(category, "cost category")
        _validate_non_empty(description, "cost description")
        if kind not in KNOWN_COST_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(COST_KINDS),))
        budgeted_cents = _validate_money(budgeted_cents, "budgeted_cents")
        actual_cents = _validate_money(actual_cents, "actual_cents")
        with self._lock:
            self._get_project_record(project_id)
            cost_id = self._next_id("cost")
            record = {
                "id": cost_id,
                "project_id": project_id,
                "category": category,
                "description": description,
                "kind": kind,
                "budgeted_cents": budgeted_cents,
                "actual_cents": actual_cents,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._costs[cost_id] = record
            self._audit(actor, "cost_create", cost_id, details={"kind": kind})
            return self._copy(record)

    def get_cost_entry(self, cost_id, actor=None):
        """Return one cost entry. Action: cost_read."""
        _maybe_require(actor, "cost_read")
        with self._lock:
            return self._copy(self._get_cost_record(cost_id))

    def list_cost_entries(self, actor=None, project_id=None, kind=None):
        """Return cost entries, optionally filtered. Action: cost_read."""
        _maybe_require(actor, "cost_read")
        with self._lock:
            records = list(self._costs.values())
            if project_id is not None:
                records = [r for r in records if r["project_id"] == project_id]
            if kind is not None:
                records = [r for r in records if r["kind"] == kind]
            return [self._copy(r) for r in records]

    def project_cost_summary(self, project_id, actor=None):
        """Cost summary for one project. Action: cost_read.

        Returns ``{project_id, entries, total_budgeted_cents,
        total_actual_cents, variance_cents}``; a None amount counts
        as 0 and variance is budgeted - actual.
        """
        _maybe_require(actor, "cost_read")
        with self._lock:
            self._get_project_record(project_id)
            entries = [r for r in self._costs.values() if r["project_id"] == project_id]
            total_budgeted = sum(r["budgeted_cents"] or 0 for r in entries)
            total_actual = sum(r["actual_cents"] or 0 for r in entries)
            return {
                "project_id": project_id,
                "entries": len(entries),
                "total_budgeted_cents": total_budgeted,
                "total_actual_cents": total_actual,
                "variance_cents": total_budgeted - total_actual,
            }

    # -- derived alerts -------------------------------------------------------------------------------

    def list_alerts(self, actor=None, now=None):
        """Derived alerts computed at read time. Action: report_read.

        Returns a list of ``{kind, project_id, ref_id, message}``
        sorted by (kind, ref_id). Kinds: contract_expired /
        contract_expiring (via :meth:`_contract_expiry_state`),
        milestone_overdue (via :meth:`_milestone_due_state`),
        submittal_overdue / rfi_overdue / punch_overdue (via
        :meth:`_record_overdue`), compliance_noncompliant and
        compliance_no_records (via :meth:`_contractor_compliance`
        over project participants). Nothing is stored.
        """
        _maybe_require(actor, "report_read")
        now_dt = _coerce_now(now)
        with self._lock:
            alerts = []
            for contract in self._contracts.values():
                state = self._contract_expiry_state(contract, now_dt)
                if state == "expired":
                    alerts.append({
                        "kind": "contract_expired",
                        "project_id": contract["project_id"],
                        "ref_id": contract["id"],
                        "message": "contract %s expired" % (contract["id"],),
                    })
                elif state == "expiring":
                    alerts.append({
                        "kind": "contract_expiring",
                        "project_id": contract["project_id"],
                        "ref_id": contract["id"],
                        "message": "contract %s expiring" % (contract["id"],),
                    })
            for milestone in self._milestones.values():
                if self._milestone_due_state(milestone, now_dt) == "overdue":
                    alerts.append({
                        "kind": "milestone_overdue",
                        "project_id": milestone["project_id"],
                        "ref_id": milestone["id"],
                        "message": "milestone %s overdue" % (milestone["id"],),
                    })
            for record in self._submittals.values():
                if self._record_overdue(record, now_dt, SUBMITTAL_TERMINAL):
                    alerts.append({
                        "kind": "submittal_overdue",
                        "project_id": record["project_id"],
                        "ref_id": record["id"],
                        "message": "submittal %s overdue" % (record["id"],),
                    })
            for record in self._rfis.values():
                if self._record_overdue(record, now_dt, RFI_TERMINAL):
                    alerts.append({
                        "kind": "rfi_overdue",
                        "project_id": record["project_id"],
                        "ref_id": record["id"],
                        "message": "rfi %s overdue" % (record["id"],),
                    })
            for record in self._punch_items.values():
                if self._record_overdue(record, now_dt, PUNCH_TERMINAL):
                    alerts.append({
                        "kind": "punch_overdue",
                        "project_id": record["project_id"],
                        "ref_id": record["id"],
                        "message": "punch item %s overdue" % (record["id"],),
                    })
            for project_id, participants in self._participants.items():
                for participant in participants:
                    org_id = participant["org_id"]
                    status = self._contractor_compliance(project_id, org_id)
                    if status == "noncompliant":
                        alerts.append({
                            "kind": "compliance_noncompliant",
                            "project_id": project_id,
                            "ref_id": org_id,
                            "message": "contractor %s noncompliant on project %s" % (org_id, project_id),
                        })
                    elif status == "no_records":
                        alerts.append({
                            "kind": "compliance_no_records",
                            "project_id": project_id,
                            "ref_id": org_id,
                            "message": "contractor %s has no compliance records on project %s" % (org_id, project_id),
                        })
            alerts.sort(key=lambda a: (a["kind"], a["ref_id"]))
            return alerts

    # -- report ------------------------------------------------------------------------------------------

    def report(self, actor=None, now=None):
        """Deterministic aggregate report at ``now``. Action: report_read.

        All counts are derived at call time using the same derivation
        points as the read views. Compliance counts are over all
        project participants; cost totals are over all cost entries.
        """
        _maybe_require(actor, "report_read")
        now_dt = _coerce_now(now)
        with self._lock:
            projects_by_status = {}
            for project in self._projects.values():
                projects_by_status[project["status"]] = projects_by_status.get(project["status"], 0) + 1
            contracts_by_status = {}
            contracts_by_expiry = {}
            for contract in self._contracts.values():
                contracts_by_status[contract["status"]] = contracts_by_status.get(contract["status"], 0) + 1
                state = self._contract_expiry_state(contract, now_dt)
                contracts_by_expiry[state] = contracts_by_expiry.get(state, 0) + 1
            milestones_by_state = {}
            for milestone in self._milestones.values():
                state = self._milestone_due_state(milestone, now_dt)
                milestones_by_state[state] = milestones_by_state.get(state, 0) + 1
            submittals_overdue = sum(
                1 for r in self._submittals.values()
                if self._record_overdue(r, now_dt, SUBMITTAL_TERMINAL)
            )
            rfis_overdue = sum(
                1 for r in self._rfis.values()
                if self._record_overdue(r, now_dt, RFI_TERMINAL)
            )
            punch_open = sum(1 for r in self._punch_items.values() if r["status"] == "open")
            punch_overdue = sum(
                1 for r in self._punch_items.values()
                if self._record_overdue(r, now_dt, PUNCH_TERMINAL)
            )
            incidents_by_status = {}
            for incident in self._incidents.values():
                incidents_by_status[incident["status"]] = incidents_by_status.get(incident["status"], 0) + 1
            compliance = {"compliant": 0, "noncompliant": 0, "no_records": 0}
            for project_id, participants in self._participants.items():
                for participant in participants:
                    status = self._contractor_compliance(project_id, participant["org_id"])
                    compliance[status] = compliance.get(status, 0) + 1
            total_budgeted = sum(r["budgeted_cents"] or 0 for r in self._costs.values())
            total_actual = sum(r["actual_cents"] or 0 for r in self._costs.values())
            return {
                "projects": {"total": len(self._projects), "by_status": projects_by_status},
                "contracts": {
                    "total": len(self._contracts),
                    "by_status": contracts_by_status,
                    "by_expiry_state": contracts_by_expiry,
                },
                "milestones": {"total": len(self._milestones), "by_due_state": milestones_by_state},
                "submittals": {"total": len(self._submittals), "overdue": submittals_overdue},
                "rfis": {"total": len(self._rfis), "overdue": rfis_overdue},
                "punch_items": {
                    "total": len(self._punch_items),
                    "open": punch_open,
                    "overdue": punch_overdue,
                },
                "incidents": {"total": len(self._incidents), "by_status": incidents_by_status},
                "compliance": compliance,
                "costs": {
                    "entries": len(self._costs),
                    "total_budgeted_cents": total_budgeted,
                    "total_actual_cents": total_actual,
                    "variance_cents": total_budgeted - total_actual,
                },
            }

    # -- search --------------------------------------------------------------------------------------------

    def search(self, query, actor):
        """Literal case-insensitive substring search.

        Over projects (name), organizations (name + reference),
        documents (title), and contracts (title). Returns
        ``{projects, organizations, documents, contracts}``; contract
        views include derived expiry at the current time.
        Action: project_read. An empty query -> ValidationError.
        Records a 'search' audit entry.
        """
        _require_actor(actor, "project_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.lower()
        with self._lock:
            now_dt = _coerce_now(None)
            result = {
                "projects": [
                    self._copy(p) for p in self._projects.values()
                    if needle in p["name"].lower()
                ],
                "organizations": [
                    self._copy(o) for o in self._orgs.values()
                    if needle in o["name"].lower()
                    or (o["reference"] is not None and needle in o["reference"].lower())
                ],
                "documents": [
                    self._copy(d) for d in self._documents.values()
                    if needle in d["title"].lower()
                ],
                "contracts": [
                    self._contract_view(c, now_dt) for c in self._contracts.values()
                    if needle in c["title"].lower()
                ],
            }
            self._audit(actor, "search", "search", details={"query": query})
            return result
