"""System administration store: customer organizations, managed
system registry, application registry, service request records,
change records, and control inheritance records.

Clean-room implementation of the union spec's implementation
contract. The single fork in this category is a managed platform
services offering: a General Support System of operating systems
and services, run on third-party cloud hosting, whose operator
maintains the full management of the OS and services for
contracting customer organizations. This store implements the
records substrate its description actually claims, and nothing
else. It administers no live system, patches nothing, provisions
nothing, and responds to nothing: the management work itself is
performed by the operator and is Extended.

Two boundaries are enforced on every organization-scoped
operation:

1. Membership -- the actor must be a member of the organization,
   or hold the platform ``admin`` role, else
   :class:`PermissionDenied`. (The fork's own prose restricts
   access to contracting organizations; membership is that
   restriction's records form.)
2. Role permission -- the action named for the operation must be
   in the actor's role permission set (see
   :mod:`sysadmin.access`) when the actor is a User-like object.
   A plain string actor carries identity (for provenance) but no
   role, so role enforcement for those happens in the service
   layer.

Role actions: ``enter`` for creates / registrations / retires /
request starts and cancels, ``decide`` for change decisions,
``record`` for request resolutions and change closes, ``read``
for reads, ``manage_members`` for membership changes, and
``create_org`` for organization creation.

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``sys-``, ``app-``, ``req-``, ``chg-``, ``ctl-``).

Derivation discipline: a service request's ``overdue`` flag is
computed at read from its due date and lifecycle status against
the read clock and is never stored -- the stored request record
carries no such key. A request's lifecycle ``status``
(``open`` / ``in_progress`` / ``resolved`` / ``cancelled``), a
managed system's ``state`` (``registered`` / ``retired``), and a
change's ``status`` are event-driven, so those are stored.

Change discipline: closing an approved change record records the
intent only; it modifies no managed system and no application
record. The work that would carry a change out is the operator's
management service: Extended, never part of this store.

Scoring discipline: nothing in this store computes a score, a
rating, or any health or compliance value, and no record shape
carries a field for one. Summaries are counts only. Control
records carry the operator's own recorded source for a control
(``inherited`` / ``local`` / ``shared``) verbatim; the store
derives no posture from them.

Privacy discipline: organizations, managed systems, and
applications are known only by caller-supplied opaque references
and labels. The managed system and application record shapes are
pinned -- neither has a field that could hold a hostname, an IP
address, a credential, or any other identifier of a live system
-- and the pins are enforced by tests.

The store records every successful mutation to its audit log
(when one is attached). Reads are not audited here; denied
attempts and audit reads are the HTTP layer's responsibility, so
nothing is recorded twice.
"""

import re
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

SYSTEM_KINDS = ("operating_system", "platform_service")
SYSTEM_STATES = ("registered", "retired")
APPLICATION_STATES = ("registered", "retired")
REQUEST_KINDS = ("support", "maintenance", "access", "other")
REQUEST_STATUSES = ("open", "in_progress", "resolved", "cancelled")
CHANGE_KINDS = ("patch", "configure", "provision", "decommission")
CHANGE_STATUSES = ("requested", "approved", "rejected", "closed", "cancelled")
CONTROL_SOURCES = ("inherited", "local", "shared")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _utc_now():
    return datetime.now(timezone.utc)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _parse_date(value, field):
    """Parse a ``YYYY-MM-DD`` calendar date.

    Returns a :class:`datetime.date`. Anything else -- another
    format, a datetime, an impossible date -- raises
    :class:`ValidationError`.
    """
    if isinstance(value, datetime):
        raise ValidationError("%s must be a YYYY-MM-DD date: %r" % (field, value))
    if isinstance(value, date):
        return value
    if isinstance(value, str) and _DATE_RE.match(value.strip()):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise ValidationError("%s must be a YYYY-MM-DD date: %r" % (field, value))


def _as_date(value):
    """Normalize an as_of value (date, datetime, or ISO string) to a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if _DATE_RE.match(text):
            return _parse_date(text, "as_of")
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise ValidationError("as_of must be a date or timestamp: %r" % (value,))
        return parsed.date()
    raise ValidationError("as_of must be a date or timestamp: %r" % (value,))


class SysadminStore:
    """In-memory system-administration records store."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._systems = {}
        self._applications = {}
        self._requests = {}
        self._changes = {}
        self._controls = {}
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

    # -- managed system registry ------------------------------------------

    def create_system(self, actor, org_id, ref, label, kind, platform_ref):
        """Register one managed system in an organization.

        ``ref`` is the caller-supplied opaque system reference; it
        is unique within the organization. ``platform_ref`` is the
        caller-supplied opaque reference of the third-party
        hosting platform the system runs on. The record shape is
        pinned (see the module docstring's privacy discipline);
        the system starts in the ``registered`` state.
        """
        self._scoped(actor, org_id, "enter")
        _text(ref, "ref")
        _text(label, "label")
        if kind not in SYSTEM_KINDS:
            raise ValidationError("kind must be one of %r" % (SYSTEM_KINDS,))
        _text(platform_ref, "platform_ref")
        with self._lock:
            for existing in self._systems.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "system ref already exists in this organization: %r" % (ref,))
            system = {
                "id": self._mint("sys-"),
                "org_id": org_id,
                "ref": ref,
                "label": label,
                "kind": kind,
                "platform_ref": platform_ref,
                "state": "registered",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._systems[system["id"]] = system
        self._record(actor, "system_create", system["id"], {"ref": ref})
        return dict(system)

    def _system(self, system_id):
        system = self._systems.get(system_id)
        if system is None:
            raise NotFoundError("no such system: %r" % (system_id,))
        return system

    def get_system(self, actor, system_id):
        self._check_role(actor, "read")
        system = self._system(system_id)
        self._check_org_access(actor, self._organizations[system["org_id"]])
        return dict(system)

    def list_systems(self, actor, org_id, kind=None, state=None):
        self._scoped(actor, org_id, "read")
        return [
            dict(s) for s in self._systems.values()
            if s["org_id"] == org_id
            and (kind is None or s["kind"] == kind)
            and (state is None or s["state"] == state)
        ]

    def retire_system(self, actor, system_id):
        """Retire a registered managed system. Retiring twice is an error."""
        system = self._system(system_id)
        self._scoped(actor, system["org_id"], "enter")
        if system["state"] == "retired":
            raise ValidationError("system is already retired")
        with self._lock:
            system["state"] = "retired"
        self._record(actor, "system_retire", system_id, {})
        return dict(system)

    # -- application registry ---------------------------------------------

    def create_application(self, actor, org_id, system_id, ref, label):
        """Register one application hosted on a managed system.

        ``ref`` is unique within the organization. The record
        shape is pinned (see the module docstring's privacy
        discipline); the application starts in the ``registered``
        state.
        """
        self._scoped(actor, org_id, "enter")
        system = self._system(system_id)
        if system["org_id"] != org_id:
            raise ValidationError("system belongs to another organization")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._applications.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "application ref already exists in this organization: %r"
                        % (ref,))
            application = {
                "id": self._mint("app-"),
                "org_id": org_id,
                "system_id": system_id,
                "ref": ref,
                "label": label,
                "state": "registered",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._applications[application["id"]] = application
        self._record(actor, "application_create", application["id"], {"ref": ref})
        return dict(application)

    def _application(self, application_id):
        application = self._applications.get(application_id)
        if application is None:
            raise NotFoundError("no such application: %r" % (application_id,))
        return application

    def get_application(self, actor, application_id):
        self._check_role(actor, "read")
        application = self._application(application_id)
        self._check_org_access(actor, self._organizations[application["org_id"]])
        return dict(application)

    def list_applications(self, actor, org_id, system_id=None, state=None):
        self._scoped(actor, org_id, "read")
        return [
            dict(a) for a in self._applications.values()
            if a["org_id"] == org_id
            and (system_id is None or a["system_id"] == system_id)
            and (state is None or a["state"] == state)
        ]

    def retire_application(self, actor, application_id):
        """Retire a registered application. Retiring twice is an error."""
        application = self._application(application_id)
        self._scoped(actor, application["org_id"], "enter")
        if application["state"] == "retired":
            raise ValidationError("application is already retired")
        with self._lock:
            application["state"] = "retired"
        self._record(actor, "application_retire", application_id, {})
        return dict(application)

    # -- service request records ------------------------------------------

    def create_request(self, actor, org_id, system_id, request_kind, summary,
                       due_date, application_id=None):
        """Record a service request against a managed system.

        The request optionally targets an application, which must
        be hosted on that system. ``due_date`` is a YYYY-MM-DD
        calendar date. Recording a request performs no work: the
        work is the operator's management service, Extended.
        """
        self._scoped(actor, org_id, "enter")
        system = self._system(system_id)
        if system["org_id"] != org_id:
            raise ValidationError("system belongs to another organization")
        if request_kind not in REQUEST_KINDS:
            raise ValidationError(
                "request_kind must be one of %r" % (REQUEST_KINDS,))
        _text(summary, "summary")
        _parse_date(due_date, "due_date")
        if not isinstance(due_date, str):
            raise ValidationError("due_date must be a YYYY-MM-DD string")
        if application_id is not None:
            application = self._application(application_id)
            if application["org_id"] != org_id:
                raise ValidationError(
                    "application belongs to another organization")
            if application["system_id"] != system_id:
                raise ValidationError("application is not hosted on that system")
        with self._lock:
            request = {
                "id": self._mint("req-"),
                "org_id": org_id,
                "system_id": system_id,
                "application_id": application_id,
                "request_kind": request_kind,
                "summary": summary,
                "status": "open",
                "due_date": due_date,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._requests[request["id"]] = request
        self._record(actor, "request_create", request["id"],
                     {"request_kind": request_kind})
        return self._request_view(request)

    def _request(self, request_id):
        request = self._requests.get(request_id)
        if request is None:
            raise NotFoundError("no such request: %r" % (request_id,))
        return request

    def _is_overdue(self, request, as_of_dt):
        """Derive whether a request is overdue at ``as_of_dt``.

        A request is overdue when it is still open or in progress
        and its due date is before the read date. Resolved and
        cancelled requests are never overdue. This is the group's
        signature derivation (see the negative control in
        tests/test_negative_control.py).
        """
        if request["status"] not in ("open", "in_progress"):
            return False
        as_of = _as_date(as_of_dt) if as_of_dt is not None else _utc_now().date()
        return _parse_date(request["due_date"], "due_date") < as_of

    def _request_view(self, request, as_of=None):
        view = dict(request)
        view["overdue"] = self._is_overdue(request, as_of)
        return view

    def get_request(self, actor, request_id, as_of=None):
        self._check_role(actor, "read")
        request = self._request(request_id)
        self._check_org_access(actor, self._organizations[request["org_id"]])
        if as_of is not None:
            _as_date(as_of)
        return self._request_view(request, as_of=as_of)

    def list_requests(self, actor, org_id, as_of=None, status=None,
                      system_id=None):
        self._scoped(actor, org_id, "read")
        if as_of is not None:
            _as_date(as_of)
        return [
            self._request_view(r, as_of=as_of)
            for r in self._requests.values()
            if r["org_id"] == org_id
            and (status is None or r["status"] == status)
            and (system_id is None or r["system_id"] == system_id)
        ]

    def start_request(self, actor, request_id):
        """Move an open request to in progress."""
        request = self._request(request_id)
        self._scoped(actor, request["org_id"], "enter")
        if request["status"] != "open":
            raise ValidationError(
                "only an open request can be started: %r" % (request["status"],))
        with self._lock:
            request["status"] = "in_progress"
        self._record(actor, "request_start", request_id, {})
        return self._request_view(request)

    def resolve_request(self, actor, request_id):
        """Resolve an open or in-progress request.

        Resolving records that the work was completed; the work
        itself is the operator's management service, Extended.
        """
        request = self._request(request_id)
        self._scoped(actor, request["org_id"], "record")
        if request["status"] not in ("open", "in_progress"):
            raise ValidationError(
                "request cannot be resolved from %r" % (request["status"],))
        with self._lock:
            request["status"] = "resolved"
            request["resolved_by"] = actor_name(actor)
            request["resolved_utc"] = _utc_now().isoformat()
        self._record(actor, "request_resolve", request_id, {})
        return self._request_view(request)

    def cancel_request(self, actor, request_id):
        """Cancel an open or in-progress request.

        Only the requester, or a platform admin, may cancel.
        """
        request = self._request(request_id)
        self._scoped(actor, request["org_id"], "enter")
        if request["status"] not in ("open", "in_progress"):
            raise ValidationError(
                "request cannot be cancelled from %r" % (request["status"],))
        role = getattr(actor, "role", None)
        if actor_name(actor) != request["created_by"] and role != "admin":
            raise PermissionDenied(
                "only the requester or a platform admin may cancel a request")
        with self._lock:
            request["status"] = "cancelled"
        self._record(actor, "request_cancel", request_id, {})
        return self._request_view(request)

    # -- change records -----------------------------------------------------

    def create_change(self, actor, org_id, system_id, change_kind, summary,
                      application_id=None):
        """Record a change request against a managed system.

        The change optionally targets an application, which must
        be hosted on that system. Recording a change never
        modifies any system or application record.
        """
        self._scoped(actor, org_id, "enter")
        system = self._system(system_id)
        if system["org_id"] != org_id:
            raise ValidationError("system belongs to another organization")
        if change_kind not in CHANGE_KINDS:
            raise ValidationError("change_kind must be one of %r" % (CHANGE_KINDS,))
        _text(summary, "summary")
        if application_id is not None:
            application = self._application(application_id)
            if application["org_id"] != org_id:
                raise ValidationError(
                    "application belongs to another organization")
            if application["system_id"] != system_id:
                raise ValidationError("application is not hosted on that system")
        with self._lock:
            change = {
                "id": self._mint("chg-"),
                "org_id": org_id,
                "system_id": system_id,
                "application_id": application_id,
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

        Closing records the intent only: it modifies no managed
        system and no application record -- the work that would
        carry the change out is Extended.
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

    # -- control inheritance records -----------------------------------------

    def create_control(self, actor, org_id, system_id, control_ref, source,
                       note=""):
        """Record a control's source for one managed system.

        ``source`` is the recorded disposition of the control:
        ``inherited`` (satisfied by the underlying hosting
        platform), ``local`` (implemented on the managed platform
        itself), or ``shared``. The record carries the
        disposition verbatim; the store derives no posture, score,
        or compliance value from control records.
        """
        self._scoped(actor, org_id, "enter")
        system = self._system(system_id)
        if system["org_id"] != org_id:
            raise ValidationError("system belongs to another organization")
        _text(control_ref, "control_ref")
        if source not in CONTROL_SOURCES:
            raise ValidationError("source must be one of %r" % (CONTROL_SOURCES,))
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            for existing in self._controls.values():
                if (existing["system_id"] == system_id
                        and existing["control_ref"] == control_ref):
                    raise ValidationError(
                        "control already recorded for this system: %r"
                        % (control_ref,))
            control = {
                "id": self._mint("ctl-"),
                "org_id": org_id,
                "system_id": system_id,
                "control_ref": control_ref,
                "source": source,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._controls[control["id"]] = control
        self._record(actor, "control_create", control["id"],
                     {"control_ref": control_ref, "source": source})
        return dict(control)

    def _control(self, control_id):
        control = self._controls.get(control_id)
        if control is None:
            raise NotFoundError("no such control record: %r" % (control_id,))
        return control

    def get_control(self, actor, control_id):
        self._check_role(actor, "read")
        control = self._control(control_id)
        self._check_org_access(actor, self._organizations[control["org_id"]])
        return dict(control)

    def list_controls(self, actor, org_id, system_id=None, source=None):
        self._scoped(actor, org_id, "read")
        return [
            dict(c) for c in self._controls.values()
            if c["org_id"] == org_id
            and (system_id is None or c["system_id"] == system_id)
            and (source is None or c["source"] == source)
        ]

    # -- search & summary ------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over accessible records."""
        self._check_role(actor, "read")
        needle = (query or "").strip().lower()
        orgs = self.list_organizations(actor)
        org_ids = {org["id"] for org in orgs}
        result = {"systems": [], "applications": [], "requests": [], "changes": []}
        if not needle:
            return result
        for system in self._systems.values():
            if system["org_id"] in org_ids and (
                    needle in system["ref"].lower()
                    or needle in system["label"].lower()):
                result["systems"].append(dict(system))
        for application in self._applications.values():
            if application["org_id"] in org_ids and (
                    needle in application["ref"].lower()
                    or needle in application["label"].lower()):
                result["applications"].append(dict(application))
        for request in self._requests.values():
            if request["org_id"] in org_ids and needle in request["summary"].lower():
                result["requests"].append(self._request_view(request))
        for change in self._changes.values():
            if change["org_id"] in org_ids and needle in change["summary"].lower():
                result["changes"].append(dict(change))
        return result

    def organization_summary(self, actor, org_id):
        """Counts for one organization, computed on read. Counts only."""
        self._scoped(actor, org_id, "read")
        systems = [s for s in self._systems.values() if s["org_id"] == org_id]
        systems_by_kind = {kind: 0 for kind in SYSTEM_KINDS}
        systems_by_state = {state: 0 for state in SYSTEM_STATES}
        for system in systems:
            systems_by_kind[system["kind"]] += 1
            systems_by_state[system["state"]] += 1
        requests = [r for r in self._requests.values() if r["org_id"] == org_id]
        requests_by_status = {status: 0 for status in REQUEST_STATUSES}
        requests_overdue = 0
        now = _utc_now()
        for request in requests:
            requests_by_status[request["status"]] += 1
            if self._is_overdue(request, now):
                requests_overdue += 1
        changes = [c for c in self._changes.values() if c["org_id"] == org_id]
        changes_by_status = {status: 0 for status in CHANGE_STATUSES}
        for change in changes:
            changes_by_status[change["status"]] += 1
        controls = [c for c in self._controls.values() if c["org_id"] == org_id]
        controls_by_source = {source: 0 for source in CONTROL_SOURCES}
        for control in controls:
            controls_by_source[control["source"]] += 1
        return {
            "org_id": org_id,
            "systems": len(systems),
            "systems_by_kind": systems_by_kind,
            "systems_by_state": systems_by_state,
            "applications": sum(1 for a in self._applications.values()
                                if a["org_id"] == org_id),
            "requests": len(requests),
            "requests_by_status": requests_by_status,
            "requests_overdue": requests_overdue,
            "changes": len(changes),
            "changes_by_status": changes_by_status,
            "controls": len(controls),
            "controls_by_source": controls_by_source,
        }
