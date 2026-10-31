"""Operations-management store: directory (persons/organizations),
projects, assets, work orders, inspections, usage records, workflow
registry, reports, and search.

Clean-room implementation of the contract.

Permission convention (mirrors the contact-center group): store
methods take an ``actor``. When the actor is a User-like object (it
has a ``role`` attribute) the store calls
:func:`opsmgmt.access.require` for the method's action *before* any
state change or id allocation, so a denied operation consumes no id
and changes nothing. Where a plain string is passed it carries
identity (for provenance) but no role, so there is nothing to enforce
against at this layer; the service layer, which knows the role
registry, is responsible for enforcement in that case -- and it
always passes User objects.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``per-``, ``org-``, ``proj-``,
``ast-``, ``wo-``, ``insp-``, ``use-``, ``wf-``).

Derived status: a work order's overdue state is DERIVED at read time
from its stored ``due_at`` and status against the reference ``now``
-- it is never stored. Derivation lives in exactly one small method,
:meth:`OpsStore._is_overdue`, which the negative-control drill
patches.

Design constraint: a person's or organization's ``reference`` is an
opaque external reference string. This build NEVER stores a real
personal identifier as such; records here are operational records,
keyed by opaque references.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

WORK_TYPES = ("inspection", "maintenance", "field_operation", "task", "general")
KNOWN_WORK_TYPES = frozenset(WORK_TYPES)
PRIORITIES = ("low", "normal", "high", "critical")
KNOWN_PRIORITIES = frozenset(PRIORITIES)
INSPECTION_OUTCOMES = ("pass", "fail", "follow_up", "not_recorded")
KNOWN_INSPECTION_OUTCOMES = frozenset(INSPECTION_OUTCOMES)

ASSET_TRANSITIONS = {
    "in_service": frozenset({"in_maintenance", "retired"}),
    "in_maintenance": frozenset({"in_service", "retired"}),
    "retired": frozenset(),
}
WORK_TRANSITIONS = {
    "open": frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset({"completed", "open", "cancelled"}),
    "completed": frozenset({"closed", "in_progress"}),
    "closed": frozenset(),
    "cancelled": frozenset(),
}
NON_OVERDUE_STATUSES = frozenset({"completed", "closed", "cancelled"})


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


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


class OpsStore:
    """In-memory store for the operations-management service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._persons = {}
        self._organizations = {}
        self._projects = {}
        self._assets = {}
        self._work_orders = {}
        self._inspections = {}
        self._usage = {}
        self._workflows = {}
        self._counters = {
            "per": 0, "org": 0, "proj": 0, "ast": 0,
            "wo": 0, "insp": 0, "use": 0, "wf": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _get_person_record(self, person_id):
        record = self._persons.get(person_id)
        if record is None:
            raise NotFoundError("person not found: %r" % (person_id,))
        return record

    def _get_organization_record(self, organization_id):
        record = self._organizations.get(organization_id)
        if record is None:
            raise NotFoundError("organization not found: %r" % (organization_id,))
        return record

    def _get_project_record(self, project_id):
        record = self._projects.get(project_id)
        if record is None:
            raise NotFoundError("project not found: %r" % (project_id,))
        return record

    def _get_asset_record(self, asset_id):
        record = self._assets.get(asset_id)
        if record is None:
            raise NotFoundError("asset not found: %r" % (asset_id,))
        return record

    def _get_work_order_record(self, work_order_id):
        record = self._work_orders.get(work_order_id)
        if record is None:
            raise NotFoundError("work order not found: %r" % (work_order_id,))
        return record

    def _get_inspection_record(self, inspection_id):
        record = self._inspections.get(inspection_id)
        if record is None:
            raise NotFoundError("inspection not found: %r" % (inspection_id,))
        return record

    def _get_workflow_record(self, workflow_id):
        record = self._workflows.get(workflow_id)
        if record is None:
            raise NotFoundError("workflow not found: %r" % (workflow_id,))
        return record

    @staticmethod
    def _copy_person(person):
        copied = dict(person)
        copied["attributes"] = copy.deepcopy(person["attributes"])
        return copied

    @staticmethod
    def _copy_organization(organization):
        copied = dict(organization)
        copied["attributes"] = copy.deepcopy(organization["attributes"])
        return copied

    @staticmethod
    def _copy_project(project):
        copied = dict(project)
        copied["members"] = list(project["members"])
        copied["attributes"] = copy.deepcopy(project["attributes"])
        return copied

    @staticmethod
    def _copy_asset(asset):
        copied = dict(asset)
        copied["attributes"] = copy.deepcopy(asset["attributes"])
        return copied

    @staticmethod
    def _copy_workflow(workflow):
        copied = dict(workflow)
        copied["versions"] = copy.deepcopy(workflow["versions"])
        return copied

    # -- derivation (single point; see module docstring) -------------

    def _is_overdue(self, work_order, now_dt):
        """True iff the work order is past due and not in a
        completed / closed / cancelled status.

        MUTATION DRILL NOTE: this method
        (``OpsStore._is_overdue`` in ``src/opsmgmt/store.py``)
        is the load-bearing derivation point for the
        negative-control drill: an overdue open work order must read
        ``overdue=True``.
        """
        if work_order.get("due_at") is None:
            return False
        if work_order["status"] in NON_OVERDUE_STATUSES:
            return False
        due_dt = _parse_iso_datetime(work_order["due_at"], "due_at")
        return now_dt > due_dt

    def _work_order_view(self, work_order, now_dt):
        view = dict(work_order)
        view["overdue"] = self._is_overdue(work_order, now_dt)
        return view

    # -- directory: persons ---------------------------------------------

    def create_person(self, name, actor, reference=None, attributes=None):
        """Create a person. Action: directory_write. Id prefix: per-.

        ``reference`` is an opaque external reference string -- never
        a real personal identifier (stated design constraint).
        """
        _require_actor(actor, "directory_write")
        _validate_non_empty(name, "person name")
        if reference is not None and not isinstance(reference, str):
            raise ValidationError("reference must be a string or None")
        attributes = _validate_attributes(attributes)
        with self._lock:
            person_id = self._next_id("per")
            person = {
                "id": person_id,
                "name": name,
                "reference": reference,
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._persons[person_id] = person
            self._audit(actor, "person_create", person_id, details={"name": name})
            return self._copy_person(person)

    def get_person(self, person_id, actor=None):
        """Return one person. Action: directory_read."""
        _maybe_require(actor, "directory_read")
        with self._lock:
            return self._copy_person(self._get_person_record(person_id))

    def list_persons(self, actor=None):
        """Return persons sorted by id. Action: directory_read."""
        _maybe_require(actor, "directory_read")
        with self._lock:
            persons = sorted(self._persons.values(), key=lambda p: _id_num(p["id"]))
            return [self._copy_person(p) for p in persons]

    # -- directory: organizations --------------------------------------------

    def create_organization(self, name, actor, reference=None, attributes=None):
        """Create an organization. Action: directory_write. Id prefix: org-.

        ``reference`` is an opaque external reference string.
        Contractor/vendor organizations ride as organization records.
        """
        _require_actor(actor, "directory_write")
        _validate_non_empty(name, "organization name")
        if reference is not None and not isinstance(reference, str):
            raise ValidationError("reference must be a string or None")
        attributes = _validate_attributes(attributes)
        with self._lock:
            organization_id = self._next_id("org")
            organization = {
                "id": organization_id,
                "name": name,
                "reference": reference,
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._organizations[organization_id] = organization
            self._audit(actor, "organization_create", organization_id, details={"name": name})
            return self._copy_organization(organization)

    def get_organization(self, organization_id, actor=None):
        """Return one organization. Action: directory_read."""
        _maybe_require(actor, "directory_read")
        with self._lock:
            return self._copy_organization(self._get_organization_record(organization_id))

    def list_organizations(self, actor=None):
        """Return organizations sorted by id. Action: directory_read."""
        _maybe_require(actor, "directory_read")
        with self._lock:
            organizations = sorted(
                self._organizations.values(), key=lambda o: _id_num(o["id"])
            )
            return [self._copy_organization(o) for o in organizations]

    # -- projects -----------------------------------------------------------

    def create_project(self, name, actor, org_id=None, attributes=None):
        """Create a project. Action: project_write. Id prefix: proj-.

        ``org_id``, when given, must reference an existing
        organization.
        """
        _require_actor(actor, "project_write")
        _validate_non_empty(name, "project name")
        attributes = _validate_attributes(attributes)
        with self._lock:
            if org_id is not None:
                self._get_organization_record(org_id)
            project_id = self._next_id("proj")
            project = {
                "id": project_id,
                "name": name,
                "org_id": org_id,
                "members": [],
                "attributes": attributes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._projects[project_id] = project
            self._audit(actor, "project_create", project_id, details={"name": name})
            return self._copy_project(project)

    def add_person_to_project(self, project_id, person_id, actor):
        """Add a person to a project. Action: project_write.

        Duplicate membership -> ValidationError; unknown ids ->
        NotFoundError.
        """
        _require_actor(actor, "project_write")
        with self._lock:
            project = self._get_project_record(project_id)
            self._get_person_record(person_id)
            if person_id in project["members"]:
                raise ValidationError(
                    "person %r is already a member of project %r" % (person_id, project_id)
                )
            project["members"].append(person_id)
            self._audit(actor, "project_add_person", project_id, details={"person_id": person_id})
            return self._copy_project(project)

    def get_project(self, project_id, actor=None):
        """Return one project. Action: project_read."""
        _maybe_require(actor, "project_read")
        with self._lock:
            return self._copy_project(self._get_project_record(project_id))

    def list_projects(self, actor=None):
        """Return projects in creation order. Action: project_read."""
        _maybe_require(actor, "project_read")
        with self._lock:
            return [self._copy_project(p) for p in self._projects.values()]

    def list_project_members(self, project_id, actor=None):
        """Return the project's member person dicts. Action: project_read."""
        _maybe_require(actor, "project_read")
        with self._lock:
            project = self._get_project_record(project_id)
            return [self._copy_person(self._persons[pid]) for pid in project["members"]]

    # -- assets ---------------------------------------------------------------

    def create_asset(self, name, actor, kind="equipment", project_id=None, attributes=None):
        """Create an asset with status ``in_service``.

        Action: asset_write. Id prefix: ast-. ``project_id``, when
        given, must reference an existing project.
        """
        _require_actor(actor, "asset_write")
        _validate_non_empty(name, "asset name")
        _validate_non_empty(kind, "asset kind")
        attributes = _validate_attributes(attributes)
        with self._lock:
            if project_id is not None:
                self._get_project_record(project_id)
            asset_id = self._next_id("ast")
            asset = {
                "id": asset_id,
                "name": name,
                "kind": kind,
                "project_id": project_id,
                "attributes": attributes,
                "status": "in_service",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "updated_utc": _utc_now(),
            }
            self._assets[asset_id] = asset
            self._audit(actor, "asset_create", asset_id, details={"name": name})
            return self._copy_asset(asset)

    def transition_asset(self, asset_id, actor, to_status):
        """Transition an asset's status along the lifecycle.

        Action: asset_write. Lifecycle: in_service->{in_maintenance,
        retired}, in_maintenance->{in_service, retired},
        retired->{}. Any other transition -> ValidationError.
        """
        _require_actor(actor, "asset_write")
        with self._lock:
            asset = self._get_asset_record(asset_id)
            allowed = ASSET_TRANSITIONS[asset["status"]]
            if to_status not in allowed:
                raise ValidationError(
                    "asset %r cannot transition from %r to %r"
                    % (asset_id, asset["status"], to_status)
                )
            asset["status"] = to_status
            asset["updated_utc"] = _utc_now()
            self._audit(actor, "asset_transition", asset_id,
                        details={"to_status": to_status})
            return self._copy_asset(asset)

    def get_asset(self, asset_id, actor=None):
        """Return one asset. Action: asset_read."""
        _maybe_require(actor, "asset_read")
        with self._lock:
            return self._copy_asset(self._get_asset_record(asset_id))

    def list_assets(self, actor=None, status=None, project_id=None):
        """Return assets, optionally filtered. Action: asset_read."""
        _maybe_require(actor, "asset_read")
        with self._lock:
            assets = list(self._assets.values())
            if status is not None:
                assets = [a for a in assets if a["status"] == status]
            if project_id is not None:
                assets = [a for a in assets if a["project_id"] == project_id]
            return [self._copy_asset(a) for a in assets]

    # -- work orders ---------------------------------------------------------------

    def create_work_order(self, actor, work_type, subject, project_id=None, asset_id=None,
                          person_id=None, priority="normal", due_at=None):
        """Create a work order with status ``open``. Action: work_write.

        Id prefix: wo-. Referenced ids must exist; ``due_at`` must
        be a valid ISO-8601 datetime string when given.
        """
        _require_actor(actor, "work_write")
        if work_type not in KNOWN_WORK_TYPES:
            raise ValidationError("work_type must be one of %s" % (", ".join(WORK_TYPES),))
        _validate_non_empty(subject, "work order subject")
        if priority not in KNOWN_PRIORITIES:
            raise ValidationError("priority must be one of %s" % (", ".join(PRIORITIES),))
        if due_at is not None:
            _parse_iso_datetime(due_at, "due_at")
        with self._lock:
            if project_id is not None:
                self._get_project_record(project_id)
            if asset_id is not None:
                self._get_asset_record(asset_id)
            if person_id is not None:
                self._get_person_record(person_id)
            work_order_id = self._next_id("wo")
            work_order = {
                "id": work_order_id,
                "work_type": work_type,
                "subject": subject,
                "project_id": project_id,
                "asset_id": asset_id,
                "person_id": person_id,
                "priority": priority,
                "status": "open",
                "due_at": due_at,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "updated_utc": _utc_now(),
            }
            self._work_orders[work_order_id] = work_order
            self._audit(actor, "work_order_create", work_order_id,
                        details={"work_type": work_type, "subject": subject})
            return self._work_order_view(work_order, _coerce_now(None))

    def assign_work_order(self, work_order_id, actor, person_id=None, project_id=None):
        """Assign a work order to a person and/or a project.

        Action: work_write. At least one of ``person_id`` /
        ``project_id`` is required.
        """
        _require_actor(actor, "work_write")
        if person_id is None and project_id is None:
            raise ValidationError(
                "assign_work_order requires at least one of person_id, project_id"
            )
        with self._lock:
            work_order = self._get_work_order_record(work_order_id)
            if person_id is not None:
                self._get_person_record(person_id)
            if project_id is not None:
                self._get_project_record(project_id)
            if person_id is not None:
                work_order["person_id"] = person_id
            if project_id is not None:
                work_order["project_id"] = project_id
            work_order["updated_utc"] = _utc_now()
            self._audit(actor, "work_order_assign", work_order_id,
                        details={"person_id": person_id, "project_id": project_id})
            return self._work_order_view(work_order, _coerce_now(None))

    def transition_work_order(self, work_order_id, actor, to_status):
        """Transition a work order's status along the lifecycle.

        Action: work_write. Lifecycle: open->{in_progress, cancelled},
        in_progress->{completed, open, cancelled},
        completed->{closed, in_progress}, closed->{}, cancelled->{}.
        Any other transition -> ValidationError.
        """
        _require_actor(actor, "work_write")
        with self._lock:
            work_order = self._get_work_order_record(work_order_id)
            allowed = WORK_TRANSITIONS[work_order["status"]]
            if to_status not in allowed:
                raise ValidationError(
                    "work order %r cannot transition from %r to %r"
                    % (work_order_id, work_order["status"], to_status)
                )
            work_order["status"] = to_status
            work_order["updated_utc"] = _utc_now()
            self._audit(actor, "work_order_transition", work_order_id,
                        details={"to_status": to_status})
            return self._work_order_view(work_order, _coerce_now(None))

    def get_work_order(self, work_order_id, actor=None, now=None):
        """Return one work order with derived ``overdue``. Action: work_read."""
        _maybe_require(actor, "work_read")
        now_dt = _coerce_now(now)
        with self._lock:
            return self._work_order_view(self._get_work_order_record(work_order_id), now_dt)

    def list_work_orders(self, actor=None, now=None, status=None, project_id=None,
                         work_type=None):
        """Return work orders with derived ``overdue``, optionally filtered.

        Action: work_read. ``status`` filters on the stored status.
        """
        _maybe_require(actor, "work_read")
        now_dt = _coerce_now(now)
        with self._lock:
            work_orders = list(self._work_orders.values())
            if status is not None:
                work_orders = [w for w in work_orders if w["status"] == status]
            if project_id is not None:
                work_orders = [w for w in work_orders if w["project_id"] == project_id]
            if work_type is not None:
                work_orders = [w for w in work_orders if w["work_type"] == work_type]
            return [self._work_order_view(w, now_dt) for w in work_orders]

    # -- inspections --------------------------------------------------------------

    def record_inspection(self, actor, summary, asset_id=None, work_order_id=None,
                          inspector_id=None, outcome="not_recorded"):
        """Record an inspection. Action: inspection_write. Id prefix: insp-.

        At least one of ``asset_id`` / ``work_order_id`` is required;
        referenced ids must exist. The ``outcome`` is recorded
        verbatim. Inspections are IMMUTABLE records: there is
        deliberately no update or delete API for them.
        """
        _require_actor(actor, "inspection_write")
        _validate_non_empty(summary, "inspection summary")
        if asset_id is None and work_order_id is None:
            raise ValidationError(
                "record_inspection requires at least one of asset_id, work_order_id"
            )
        if outcome not in KNOWN_INSPECTION_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %s" % (", ".join(INSPECTION_OUTCOMES),)
            )
        with self._lock:
            if asset_id is not None:
                self._get_asset_record(asset_id)
            if work_order_id is not None:
                self._get_work_order_record(work_order_id)
            if inspector_id is not None:
                self._get_person_record(inspector_id)
            inspection_id = self._next_id("insp")
            inspection = {
                "id": inspection_id,
                "summary": summary,
                "asset_id": asset_id,
                "work_order_id": work_order_id,
                "inspector_id": inspector_id,
                "outcome": outcome,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._inspections[inspection_id] = inspection
            self._audit(actor, "inspection_record", inspection_id,
                        details={"outcome": outcome})
            return dict(inspection)

    def get_inspection(self, inspection_id, actor=None):
        """Return one inspection. Action: inspection_read."""
        _maybe_require(actor, "inspection_read")
        with self._lock:
            return dict(self._get_inspection_record(inspection_id))

    def list_inspections(self, actor=None, asset_id=None, work_order_id=None):
        """Return inspections, optionally filtered.

        Action: inspection_read.
        """
        _maybe_require(actor, "inspection_read")
        with self._lock:
            inspections = list(self._inspections.values())
            if asset_id is not None:
                inspections = [i for i in inspections if i["asset_id"] == asset_id]
            if work_order_id is not None:
                inspections = [i for i in inspections if i["work_order_id"] == work_order_id]
            return [dict(i) for i in inspections]

    # -- usage records --------------------------------------------------------------

    def record_usage(self, actor, project_id, metric, quantity, period):
        """Record a usage record. Action: usage_write. Id prefix: use-.

        The project must exist. ``quantity`` must be an int --
        booleans and floats are rejected. Usage records are IMMUTABLE
        records: there is deliberately no update or delete API.
        """
        _require_actor(actor, "usage_write")
        _validate_non_empty(metric, "usage metric")
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValidationError("quantity must be an int")
        _validate_non_empty(period, "usage period")
        with self._lock:
            self._get_project_record(project_id)
            usage_id = self._next_id("use")
            usage = {
                "id": usage_id,
                "project_id": project_id,
                "metric": metric,
                "quantity": quantity,
                "period": period,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._usage[usage_id] = usage
            self._audit(actor, "usage_record", usage_id,
                        details={"project_id": project_id, "metric": metric})
            return dict(usage)

    def list_usage(self, actor=None, project_id=None, metric=None):
        """Return usage records, optionally filtered. Action: usage_read."""
        _maybe_require(actor, "usage_read")
        with self._lock:
            usage = list(self._usage.values())
            if project_id is not None:
                usage = [u for u in usage if u["project_id"] == project_id]
            if metric is not None:
                usage = [u for u in usage if u["metric"] == metric]
            return [dict(u) for u in usage]

    # -- workflow registry ----------------------------------------------------------------------

    def create_workflow(self, actor, name, work_type, trigger_text, action_text):
        """Create a workflow at version 1. Action: workflow_write (admin only).

        Id prefix: wf-. ``work_type`` must be a known work type or
        ``"all"``. The workflow carries a ``versions`` list; each
        version is ``{version, trigger_text, action_text, enabled,
        ts}``. Registry only: creating a workflow never changes any
        work order.
        """
        _require_actor(actor, "workflow_write")
        _validate_non_empty(name, "workflow name")
        if work_type != "all" and work_type not in KNOWN_WORK_TYPES:
            raise ValidationError(
                "work_type must be one of %s or 'all'" % (", ".join(WORK_TYPES),)
            )
        _validate_non_empty(trigger_text, "workflow trigger_text")
        _validate_non_empty(action_text, "workflow action_text")
        with self._lock:
            workflow_id = self._next_id("wf")
            now = _utc_now()
            first = {
                "version": 1,
                "trigger_text": trigger_text,
                "action_text": action_text,
                "enabled": True,
                "ts": now,
            }
            workflow = {
                "id": workflow_id,
                "name": name,
                "work_type": work_type,
                "trigger_text": trigger_text,
                "action_text": action_text,
                "enabled": True,
                "version": 1,
                "versions": [first],
                "created_by": actor_name(actor),
                "created_utc": now,
                "updated_utc": now,
            }
            self._workflows[workflow_id] = workflow
            self._audit(actor, "workflow_create", workflow_id, details={"name": name})
            return self._copy_workflow(workflow)

    def update_workflow(self, workflow_id, actor, trigger_text=None, action_text=None,
                        enabled=None):
        """Append a new version to a workflow.

        Action: workflow_write (admin only). Unchanged fields are
        carried forward from the current version; the version counter
        is bumped by one. Registry only: updating a workflow never
        changes any work order.
        """
        _require_actor(actor, "workflow_write")
        if trigger_text is not None:
            _validate_non_empty(trigger_text, "workflow trigger_text")
        if action_text is not None:
            _validate_non_empty(action_text, "workflow action_text")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        with self._lock:
            workflow = self._get_workflow_record(workflow_id)
            new_version = {
                "version": workflow["version"] + 1,
                "trigger_text": trigger_text if trigger_text is not None else workflow["trigger_text"],
                "action_text": action_text if action_text is not None else workflow["action_text"],
                "enabled": enabled if enabled is not None else workflow["enabled"],
                "ts": _utc_now(),
            }
            workflow["versions"].append(new_version)
            workflow["version"] = new_version["version"]
            workflow["trigger_text"] = new_version["trigger_text"]
            workflow["action_text"] = new_version["action_text"]
            workflow["enabled"] = new_version["enabled"]
            workflow["updated_utc"] = new_version["ts"]
            self._audit(actor, "workflow_update", workflow_id,
                        details={"version": new_version["version"]})
            return self._copy_workflow(workflow)

    def get_workflow(self, workflow_id, actor=None):
        """Return one workflow. Action: workflow_read."""
        _maybe_require(actor, "workflow_read")
        with self._lock:
            return self._copy_workflow(self._get_workflow_record(workflow_id))

    def list_workflows(self, actor=None):
        """Return workflows in creation order. Action: workflow_read."""
        _maybe_require(actor, "workflow_read")
        with self._lock:
            return [self._copy_workflow(w) for w in self._workflows.values()]

    # -- reports ----------------------------------------------------------------------------

    def report(self, actor=None, now=None):
        """Deterministic aggregate report at ``now``. Action: report_read.

        All counts are derived at call time; the work-order overdue
        count uses the same derivation point as the read views. A
        work order with no project counts under ``"unassigned"``.
        Usage ``by_metric`` sums quantities (it does not count
        records).
        """
        _maybe_require(actor, "report_read")
        now_dt = _coerce_now(now)
        with self._lock:
            by_status = {}
            by_type = {}
            by_project = {}
            overdue = 0
            for work_order in self._work_orders.values():
                by_status[work_order["status"]] = by_status.get(work_order["status"], 0) + 1
                by_type[work_order["work_type"]] = by_type.get(work_order["work_type"], 0) + 1
                project_key = (
                    work_order["project_id"]
                    if work_order["project_id"] is not None else "unassigned"
                )
                by_project[project_key] = by_project.get(project_key, 0) + 1
                if self._is_overdue(work_order, now_dt):
                    overdue += 1
            by_asset_status = {}
            for asset in self._assets.values():
                by_asset_status[asset["status"]] = by_asset_status.get(asset["status"], 0) + 1
            by_outcome = {}
            for inspection in self._inspections.values():
                by_outcome[inspection["outcome"]] = by_outcome.get(inspection["outcome"], 0) + 1
            by_metric = {}
            for usage in self._usage.values():
                by_metric[usage["metric"]] = by_metric.get(usage["metric"], 0) + usage["quantity"]
            return {
                "work_orders": {
                    "total": len(self._work_orders),
                    "by_status": by_status,
                    "by_type": by_type,
                    "by_project": by_project,
                    "overdue": overdue,
                },
                "assets": {
                    "total": len(self._assets),
                    "by_status": by_asset_status,
                },
                "inspections": {
                    "total": len(self._inspections),
                    "by_outcome": by_outcome,
                },
                "usage": {
                    "total": len(self._usage),
                    "by_metric": by_metric,
                },
            }

    # -- search ---------------------------------------------------------------------------------

    def search(self, query, actor):
        """Literal case-insensitive substring search.

        Over people/organizations (name, plus reference), projects
        (name), work orders (subject), assets (name), and inspections
        (summary). Returns {people, organizations, projects,
        work_orders, assets, inspections}; work-order views carry
        derived ``overdue`` at the current time.
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
                "people": [
                    self._copy_person(p)
                    for p in self._persons.values()
                    if needle in p["name"].lower()
                    or (p["reference"] is not None and needle in p["reference"].lower())
                ],
                "organizations": [
                    self._copy_organization(o)
                    for o in self._organizations.values()
                    if needle in o["name"].lower()
                    or (o["reference"] is not None and needle in o["reference"].lower())
                ],
                "projects": [
                    self._copy_project(p)
                    for p in self._projects.values()
                    if needle in p["name"].lower()
                ],
                "work_orders": [
                    self._work_order_view(w, now_dt)
                    for w in self._work_orders.values()
                    if needle in w["subject"].lower()
                ],
                "assets": [
                    self._copy_asset(a)
                    for a in self._assets.values()
                    if needle in a["name"].lower()
                ],
                "inspections": [
                    dict(i)
                    for i in self._inspections.values()
                    if needle in i["summary"].lower()
                ],
            }
            self._audit(actor, "search", "search", details={"query": query})
            return result
