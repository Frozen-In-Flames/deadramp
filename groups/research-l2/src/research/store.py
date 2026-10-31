"""Research store: data commons, organizations, workspaces,
datasets, access requests, decisions, and access grants.

Clean-room implementation of the union spec's implementation
contract.

Two boundaries are enforced on every commons-scoped operation:

1. Membership -- the actor must be a member of the commons, or hold
   the platform ``admin`` role, else :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be in
   the actor's role permission set (see :mod:`research.access`) when
   the actor is a User-like object. A plain string actor carries
   identity (for provenance) but no role, so role enforcement for
   those happens in the service layer.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``com-``, ``org-``, ``ws-``,
``ds-``, ``ar-``, ``dec-``, ``gr-``).

Privacy discipline: dataset records are metadata plus a SHA-256
checksum only. Content is hashed transiently for verification and
never stored, and no record shape carries a field that could hold a
payload. Organizations are known only by an opaque caller-supplied
reference and a label.

Derivation discipline: a grant's status (``scheduled`` / ``active``
/ ``expired`` / ``revoked``) depends on the clock and on whether it
has been revoked, so it is derived at read time and never stored --
the stored grant record carries no ``status`` key. A commons'
lifecycle status and an access request's status, by contrast, are
event-driven (they change only through recorded lifecycle actions),
so they are stored, as in the sibling builds.

Duration discipline: durations are whole days. A duration that is
not a positive Python ``int`` (booleans, floats and strings
included) raises :class:`ValidationError`.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.
"""

import hashlib
import re
import threading
from datetime import datetime, timedelta, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

COMMONS_KINDS = ("commons", "ecosystem", "mesh")
ACCESS_TIERS = ("open", "controlled")
REQUEST_STATUSES = ("pending", "approved", "denied", "withdrawn")
GRANT_STATUSES = ("scheduled", "active", "expired", "revoked")

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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


def _duration_days(value, field="duration_days"):
    """Validate a positive whole-day duration."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be a positive integer number of days" % field)
    if value <= 0:
        raise ValidationError("%s must be a positive integer number of days" % field)
    return value


class ResearchStore:
    """In-memory research records store with an optional audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._commons = {}
        self._organizations = {}
        self._workspaces = {}
        self._datasets = {}
        self._access_requests = {}
        self._decisions = {}
        self._grants = {}
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

    def _commons_record(self, commons_id):
        commons = self._commons.get(commons_id)
        if commons is None:
            raise NotFoundError("no such commons: %r" % (commons_id,))
        return commons

    def _check_commons_access(self, actor, commons):
        name = actor_name(actor)
        role = getattr(actor, "role", None)
        if role == "admin" or name in commons["members"]:
            return
        raise PermissionDenied(
            "permission denied: user %r is not a member of commons %r"
            % (name, commons["id"])
        )

    def _organization(self, org_id):
        org = self._organizations.get(org_id)
        if org is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return org

    def _workspace(self, workspace_id):
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            raise NotFoundError("no such workspace: %r" % (workspace_id,))
        return workspace

    def _dataset(self, dataset_id):
        dataset = self._datasets.get(dataset_id)
        if dataset is None:
            raise NotFoundError("no such dataset: %r" % (dataset_id,))
        return dataset

    def _access_request(self, request_id):
        request = self._access_requests.get(request_id)
        if request is None:
            raise NotFoundError("no such access request: %r" % (request_id,))
        return request

    def _grant(self, grant_id):
        grant = self._grants.get(grant_id)
        if grant is None:
            raise NotFoundError("no such grant: %r" % (grant_id,))
        return grant

    def _commons_of(self, commons_id):
        return self._commons[commons_id]

    # -- commons ------------------------------------------------------------

    @staticmethod
    def _commons_view(commons):
        view = dict(commons)
        view["members"] = list(commons["members"])
        return view

    def create_commons(self, actor, name, title, kind, sponsor_ref):
        """Create a data commons. The creator becomes owner and
        first member. Lifecycle status starts as ``draft`` (stored,
        event-driven)."""
        self._check_role(actor, "create_commons")
        _text(name, "name")
        _text(title, "title")
        if kind not in COMMONS_KINDS:
            raise ValidationError("unknown commons kind: %r" % (kind,))
        _text(sponsor_ref, "sponsor_ref")
        with self._lock:
            for existing in self._commons.values():
                if existing["name"] == name:
                    raise ValidationError("commons name already exists: %r" % (name,))
            commons = {
                "id": self._mint("com-"),
                "name": name,
                "title": title,
                "kind": kind,
                "sponsor_ref": sponsor_ref,
                "status": "draft",
                "owner": actor_name(actor),
                "members": [actor_name(actor)],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._commons[commons["id"]] = commons
        self._record(actor, "commons_create", commons["id"], {"name": name})
        return self._commons_view(commons)

    def get_commons(self, actor, commons_id):
        self._check_role(actor, "read")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        return self._commons_view(commons)

    def list_commons(self, actor):
        self._check_role(actor, "read")
        name = actor_name(actor)
        role = getattr(actor, "role", None)
        result = []
        for commons in self._commons.values():
            if role == "admin" or name in commons["members"]:
                result.append(self._commons_view(commons))
        return result

    def add_member(self, actor, commons_id, username):
        """Add a member (by username) to a commons."""
        self._check_role(actor, "manage_members")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        _text(username, "username")
        with self._lock:
            if username not in commons["members"]:
                commons["members"].append(username)
        self._record(actor, "member_add", commons_id, {"username": username})
        return self._commons_view(commons)

    def activate_commons(self, actor, commons_id):
        """Move a commons from ``draft`` to ``active``."""
        self._check_role(actor, "record")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        with self._lock:
            if commons["status"] != "draft":
                raise ValidationError(
                    "commons %s is %r; only a draft commons can be activated"
                    % (commons_id, commons["status"])
                )
            commons["status"] = "active"
        self._record(actor, "commons_activate", commons_id, {"status": "active"})
        return self._commons_view(commons)

    def retire_commons(self, actor, commons_id):
        """Move a commons from ``draft`` or ``active`` to ``retired``."""
        self._check_role(actor, "record")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        with self._lock:
            if commons["status"] not in ("draft", "active"):
                raise ValidationError(
                    "commons %s is %r; it cannot be retired from here"
                    % (commons_id, commons["status"])
                )
            commons["status"] = "retired"
        self._record(actor, "commons_retire", commons_id, {"status": "retired"})
        return self._commons_view(commons)

    def commons_summary(self, actor, commons_id, now=None):
        """Counts for one commons, computed on read from records
        only. Grant counts use the derived grant status."""
        self._check_role(actor, "read")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        datasets_by_tier = {tier: 0 for tier in ACCESS_TIERS}
        for dataset in self._datasets.values():
            if dataset["commons_id"] == commons_id:
                datasets_by_tier[dataset["access_tier"]] += 1
        requests_by_status = {status: 0 for status in REQUEST_STATUSES}
        for request in self._access_requests.values():
            if request["commons_id"] == commons_id:
                requests_by_status[request["status"]] += 1
        grants_by_status = {status: 0 for status in GRANT_STATUSES}
        for grant in self._grants.values():
            if grant["commons_id"] == commons_id:
                grants_by_status[self._derive_grant_status(grant, moment)] += 1
        return {
            "commons_id": commons_id,
            "kind": commons["kind"],
            "status": commons["status"],
            "workspaces": sum(
                1 for w in self._workspaces.values()
                if w["commons_id"] == commons_id
            ),
            "datasets_by_tier": datasets_by_tier,
            "requests_by_status": requests_by_status,
            "grants_by_status": grants_by_status,
        }

    # -- organizations --------------------------------------------------------

    def create_organization(self, actor, ref, label):
        """Register an organization by opaque reference."""
        self._check_role(actor, "enter")
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
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[org["id"]] = org
        self._record(actor, "organization_create", org["id"], {"ref": ref})
        return dict(org)

    def update_organization(self, actor, org_id, label):
        """Update an organization's label."""
        self._check_role(actor, "enter")
        org = self._organization(org_id)
        _text(label, "label")
        with self._lock:
            org["label"] = label
        self._record(actor, "organization_update", org_id, {})
        return dict(org)

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        return dict(self._organization(org_id))

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        return [dict(o) for o in self._organizations.values()]

    # -- workspaces -------------------------------------------------------------

    def create_workspace(self, actor, commons_id, name, purpose):
        """Register a workspace inside a commons."""
        self._check_role(actor, "record")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        _text(name, "name")
        _text(purpose, "purpose")
        with self._lock:
            workspace = {
                "id": self._mint("ws-"),
                "commons_id": commons_id,
                "name": name,
                "purpose": purpose,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._workspaces[workspace["id"]] = workspace
        self._record(actor, "workspace_create", workspace["id"],
                     {"commons_id": commons_id})
        return dict(workspace)

    def get_workspace(self, actor, workspace_id):
        self._check_role(actor, "read")
        workspace = self._workspace(workspace_id)
        self._check_commons_access(actor, self._commons_of(workspace["commons_id"]))
        return dict(workspace)

    def list_workspaces(self, actor, commons_id):
        self._check_role(actor, "read")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        return [dict(w) for w in self._workspaces.values()
                if w["commons_id"] == commons_id]

    # -- datasets -----------------------------------------------------------------

    def register_dataset(self, actor, commons_id, name, description,
                         access_tier, sha256, size_bytes):
        """Register a dataset's metadata and checksum inside a
        commons. Content is never stored; no field can hold it."""
        self._check_role(actor, "record")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        _text(name, "name")
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        if access_tier not in ACCESS_TIERS:
            raise ValidationError("unknown access tier: %r" % (access_tier,))
        if not isinstance(sha256, str) or not _SHA256_RE.match(sha256):
            raise ValidationError("sha256 must be 64 hexadecimal characters")
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
            raise ValidationError("size_bytes must be a non-negative integer")
        with self._lock:
            dataset = {
                "id": self._mint("ds-"),
                "commons_id": commons_id,
                "name": name,
                "description": description,
                "access_tier": access_tier,
                "sha256": sha256.lower(),
                "size_bytes": size_bytes,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._datasets[dataset["id"]] = dataset
        self._record(actor, "dataset_create", dataset["id"],
                     {"commons_id": commons_id, "access_tier": access_tier})
        return dict(dataset)

    def get_dataset(self, actor, dataset_id):
        self._check_role(actor, "read")
        dataset = self._dataset(dataset_id)
        self._check_commons_access(actor, self._commons_of(dataset["commons_id"]))
        return dict(dataset)

    def list_datasets(self, actor, commons_id, access_tier=None):
        self._check_role(actor, "read")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        if access_tier is not None and access_tier not in ACCESS_TIERS:
            raise ValidationError("unknown access tier: %r" % (access_tier,))
        return [
            dict(d) for d in self._datasets.values()
            if d["commons_id"] == commons_id
            and (access_tier is None or d["access_tier"] == access_tier)
        ]

    def verify_dataset(self, actor, dataset_id, content):
        """Verify caller-supplied content against a dataset's stored
        checksum. The content is hashed transiently and discarded;
        it is never stored."""
        self._check_role(actor, "read")
        dataset = self._dataset(dataset_id)
        self._check_commons_access(actor, self._commons_of(dataset["commons_id"]))
        if isinstance(content, (bytes, bytearray)):
            data = bytes(content)
        else:
            raise ValidationError("content must be bytes")
        computed = hashlib.sha256(data).hexdigest()
        return {
            "dataset_id": dataset_id,
            "sha256": dataset["sha256"],
            "computed_sha256": computed,
            "matches": computed == dataset["sha256"],
        }

    # -- access requests ------------------------------------------------------------

    def create_access_request(self, actor, dataset_id, purpose, duration_days):
        """Record a request for a controlled dataset. A request
        against an open dataset is rejected: open data needs no
        request, and a request record for one would be a false gate."""
        self._check_role(actor, "enter")
        dataset = self._dataset(dataset_id)
        self._check_commons_access(actor, self._commons_of(dataset["commons_id"]))
        _text(purpose, "purpose")
        _duration_days(duration_days)
        if dataset["access_tier"] != "controlled":
            raise ValidationError(
                "access requests are only for controlled datasets; "
                "dataset %s is %r" % (dataset_id, dataset["access_tier"])
            )
        with self._lock:
            request = {
                "id": self._mint("ar-"),
                "dataset_id": dataset_id,
                "commons_id": dataset["commons_id"],
                "requester": actor_name(actor),
                "purpose": purpose,
                "duration_days": duration_days,
                "status": "pending",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._access_requests[request["id"]] = request
        self._record(actor, "access_request_create", request["id"],
                     {"dataset_id": dataset_id})
        return dict(request)

    def get_access_request(self, actor, request_id):
        self._check_role(actor, "read")
        request = self._access_request(request_id)
        self._check_commons_access(actor, self._commons_of(request["commons_id"]))
        return dict(request)

    def list_access_requests(self, actor, dataset_id):
        self._check_role(actor, "read")
        dataset = self._dataset(dataset_id)
        self._check_commons_access(actor, self._commons_of(dataset["commons_id"]))
        return [dict(r) for r in self._access_requests.values()
                if r["dataset_id"] == dataset_id]

    def withdraw_access_request(self, actor, request_id):
        """Withdraw a pending access request. The requester, or a
        commons member with the ``enter`` permission, may withdraw;
        only a ``pending`` request can be withdrawn."""
        self._check_role(actor, "enter")
        request = self._access_request(request_id)
        self._check_commons_access(actor, self._commons_of(request["commons_id"]))
        with self._lock:
            if request["status"] != "pending":
                raise ValidationError(
                    "access request %s is %r; only a pending request "
                    "can be withdrawn" % (request_id, request["status"])
                )
            request["status"] = "withdrawn"
        self._record(actor, "access_request_withdraw", request_id,
                     {"status": "withdrawn"})
        return dict(request)

    # -- decisions and grants ---------------------------------------------------------

    def _check_decider_not_requester(self, actor, request):
        """Separation of duties seam (AC-5): the decider of an access
        request is never its requester."""
        # Accept (actor, request) and (request, actor) argument orders
        # so a subclass or caller following either convention is
        # checked the same way: exactly one argument is the request
        # record (a dict with a ``requester`` key).
        if isinstance(actor, dict) and not isinstance(request, dict):
            actor, request = request, actor
        if actor_name(actor) == request["requester"]:
            raise PermissionDenied(
                "permission denied: the decider of an access request "
                "may not be its requester"
            )

    def decide_access_request(self, actor, request_id, approve, note="",
                              starts_at=None):
        """Record a decision on a pending access request.

        On approval this also mints a grant: ``starts_at`` (the
        argument, or now) and ``expires_at`` = starts_at +
        duration_days. The whole operation validates before anything
        is stored: a rejected decision consumes no id and changes
        nothing.
        """
        self._check_role(actor, "decide")
        request = self._access_request(request_id)
        commons = self._commons_of(request["commons_id"])
        self._check_commons_access(actor, commons)
        self._check_decider_not_requester(actor, request)
        if not isinstance(approve, bool):
            raise ValidationError("approve must be a boolean")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        start_moment = (
            _parse_moment(starts_at, "starts_at") if starts_at is not None
            else _utc_now()
        )
        with self._lock:
            if request["status"] != "pending":
                raise ValidationError(
                    "only a pending access request can be decided; "
                    "this one is %r" % (request["status"],)
                )
            decision = {
                "id": self._mint("dec-"),
                "request_id": request_id,
                "dataset_id": request["dataset_id"],
                "commons_id": request["commons_id"],
                "decider": actor_name(actor),
                "approve": approve,
                "note": note,
                "created_utc": _utc_now().isoformat(),
            }
            self._decisions[decision["id"]] = decision
            grant = None
            if approve:
                expires_moment = start_moment + timedelta(
                    days=request["duration_days"])
                grant = {
                    "id": self._mint("gr-"),
                    "dataset_id": request["dataset_id"],
                    "commons_id": request["commons_id"],
                    "request_id": request_id,
                    "grantee": request["requester"],
                    "starts_at": start_moment.isoformat(),
                    "expires_at": expires_moment.isoformat(),
                    "revoked_at": None,
                    "created_by": actor_name(actor),
                    "created_utc": _utc_now().isoformat(),
                }
                self._grants[grant["id"]] = grant
            request["status"] = "approved" if approve else "denied"
        self._record(actor, "access_request_decide", request_id,
                     {"approve": approve})
        result = {"decision": dict(decision), "request": dict(request)}
        if grant is not None:
            result["grant"] = self._grant_view(grant)
        return result

    def _derive_grant_status(self, grant, moment):
        """Derive a grant's status at ``moment``. The status is
        never stored: it follows from the revocation timestamp, the
        start, and the expiry, read against the read clock.

        MUTATION DRILL NOTE: this derivation is the group's
        signature invariant -- a mutant that always returns
        ``"active"`` reports an expired and a revoked grant as
        active, and the canonical expectations reject both.
        """
        if moment is None:
            moment = _utc_now()
        elif not isinstance(moment, datetime):
            moment = _parse_moment(moment, "now")
        elif moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        if grant["revoked_at"] is not None:
            return "revoked"
        if moment > _parse_moment(grant["expires_at"], "expires_at"):
            return "expired"
        if moment < _parse_moment(grant["starts_at"], "starts_at"):
            return "scheduled"
        return "active"

    def _grant_view(self, grant, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        view = dict(grant)
        view["status"] = self._derive_grant_status(grant, moment)
        return view

    def get_grant(self, actor, grant_id, now=None):
        self._check_role(actor, "read")
        grant = self._grant(grant_id)
        self._check_commons_access(actor, self._commons_of(grant["commons_id"]))
        return self._grant_view(grant, now=now)

    def list_grants(self, actor, commons_id, status=None, now=None):
        self._check_role(actor, "read")
        commons = self._commons_record(commons_id)
        self._check_commons_access(actor, commons)
        if status is not None and status not in GRANT_STATUSES:
            raise ValidationError("unknown grant status: %r" % (status,))
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        result = []
        for grant in self._grants.values():
            if grant["commons_id"] != commons_id:
                continue
            view = self._grant_view(grant, now=moment)
            if status is None or view["status"] == status:
                result.append(view)
        return result

    def revoke_grant(self, actor, grant_id):
        """Record a grant's revocation. Revoking an already-revoked
        grant raises :class:`ValidationError`."""
        self._check_role(actor, "decide")
        grant = self._grant(grant_id)
        self._check_commons_access(actor, self._commons_of(grant["commons_id"]))
        with self._lock:
            if grant["revoked_at"] is not None:
                raise ValidationError("grant %s is already revoked" % grant_id)
            grant["revoked_at"] = _utc_now().isoformat()
        self._record(actor, "grant_revoke", grant_id, {})
        return self._grant_view(grant)

    # -- search ---------------------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over commons the
        actor can access, all organizations, and datasets in
        accessible commons."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()
        name = actor_name(actor)
        role = getattr(actor, "role", None)

        def accessible(commons):
            return role == "admin" or name in commons["members"]

        commons = [
            self._commons_view(c) for c in self._commons.values()
            if accessible(c)
            and (needle in c["name"].lower() or needle in c["title"].lower())
        ]
        organizations = [
            dict(o) for o in self._organizations.values()
            if needle in o["ref"].lower() or needle in o["label"].lower()
        ]
        datasets = [
            dict(d) for d in self._datasets.values()
            if accessible(self._commons[d["commons_id"]])
            and (needle in d["name"].lower()
                 or needle in d["description"].lower())
        ]
        return {
            "commons": commons,
            "organizations": organizations,
            "datasets": datasets,
        }
