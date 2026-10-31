"""The Legal & Policy records substrate.

Clean-room implementation of the Group 49 union spec's core: agency
registry & membership, workspace registry, agent session records,
execution records, library source registry, saved-search records
(query stored as a SHA-256 digest only), document registry (metadata
+ SHA-256 checksums, never content), verify-by-content, usage
records, usage export manifests, registry reporting, and registry
search — over an append-only audit log.

Privacy discipline (hard rule): every entity is keyed by an opaque
caller-supplied reference and carries only the fields in the
contract. There is no field anywhere that can hold content, a query,
or any real identifier of a person or a matter's substance. Search
queries are stored as SHA-256 digests only: this store has no
parameter that can accept query text. Validation always precedes
mutation: a failed operation changes nothing, consumes no id, and
records nothing.

Two boundaries are enforced on every agency-scoped operation:

1. Membership -- the actor must be a member of the agency, or hold
   the platform ``admin`` role, else :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be in
   the actor's role permission set (see :mod:`legalpol.access`) when
   the actor is a :class:`~legalpol.access.User`. A plain string
   actor carries identity (for provenance) but no role, so role
   enforcement for those happens in the service layer.

The platform library (sources) is not agency-scoped: writes require
``library_write``; reads are open to any actor.

Derivation discipline: a session's ``expired`` flag (from its
``expires_at`` against the read clock) and a sandbox session's
``sandbox_consumed`` flag (from whether an execution record exists
for it) are derived at read time and never stored. The stored
session record carries neither key. The session lifecycle itself
(``active`` -> ``closed``) is a guarded transition, not a date
derivation, so ``status`` is stored.

Single-use seam: a sandbox session accepts exactly one execution
record. :meth:`LegalPolStore._check_sandbox_unused` runs before an
execution against a sandbox session is stored and raises
:class:`ValidationError` when one already exists. This is the
group's negative control.

Quantity discipline: usage quantities are positive Python ``int``
values. Booleans, floats, and strings are rejected at the boundary.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.
"""

import hashlib
import json
import re
import threading
from datetime import datetime, timezone

from .access import User, require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

LIBRARY_KINDS = ("statute", "regulation", "guidance", "dataset")
EXECUTION_KINDS = ("code", "document")
DOCUMENT_KINDS = ("generated", "uploaded")
USAGE_KINDS = ("search", "session", "execution", "document", "inference", "export")
SESSION_STATUSES = ("active", "closed")

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _sha256(value, field):
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ValidationError("%s must be exactly 64 lowercase hex characters" % field)
    return value


def _count_nonneg(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be an integer >= 0" % field)
    return value


def _quantity(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("quantity must be a positive integer")
    return value


def _export_checksum(records):
    """SHA-256 of the canonical exported set: records sorted by id,
    each reduced to {id, kind, quantity, created_utc}, serialized as
    JSON with sorted keys and compact separators."""
    ordered = sorted(records, key=lambda r: int(r["id"].split("-", 1)[1]))
    canonical = [
        {
            "id": r["id"],
            "kind": r["kind"],
            "quantity": r["quantity"],
            "created_utc": r["created_utc"],
        }
        for r in ordered
    ]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LegalPolStore:
    """In-memory Legal & Policy records store with an optional audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._agencies = {}
        self._workspaces = {}
        self._sessions = {}
        self._executions = {}
        self._library_sources = {}
        self._searches = {}
        self._documents = {}
        self._usage = {}
        self._exports = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _name(actor):
        return actor_name(actor)

    @staticmethod
    def _require_role(actor, action):
        # A User carries a role and is enforced here; a plain string
        # carries identity only (the service layer enforces its role).
        if isinstance(actor, User):
            require(actor, action)

    @staticmethod
    def _is_admin(actor):
        return isinstance(actor, User) and actor.role == "admin"

    def _agency(self, agency_id):
        agency = self._agencies.get(agency_id)
        if agency is None:
            raise NotFoundError("no such agency: %r" % (agency_id,))
        return agency

    def _require_agency_access(self, agency, actor):
        if self._is_admin(actor):
            return
        if self._name(actor) not in agency["members"]:
            raise PermissionDenied(
                "actor %r is not a member of agency %s"
                % (self._name(actor), agency["id"])
            )

    def _scoped_agency(self, agency_id, actor, action):
        agency = self._agency(agency_id)
        self._require_role(actor, action)
        self._require_agency_access(agency, actor)
        return agency

    @staticmethod
    def _agency_view(agency):
        view = dict(agency)
        view["members"] = list(agency["members"])
        return view

    def _workspace_in(self, agency_id, workspace_id):
        workspace = self._workspaces.get(workspace_id)
        if workspace is None or workspace["agency_id"] != agency_id:
            raise NotFoundError(
                "no such workspace in agency %s: %r" % (agency_id, workspace_id)
            )
        return workspace

    def _session_in(self, agency_id, session_id):
        session = self._sessions.get(session_id)
        if session is None or session["agency_id"] != agency_id:
            raise NotFoundError(
                "no such session in agency %s: %r" % (agency_id, session_id)
            )
        return session

    # -- agencies -----------------------------------------------------------

    def create_agency(self, agency_ref, label, actor):
        """Create an agency. The creator is the first member."""
        self._require_role(actor, "agency_write")
        _text(agency_ref, "agency_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._agencies.values():
                if existing["agency_ref"] == agency_ref:
                    raise ValidationError(
                        "agency_ref already exists: %r" % (agency_ref,)
                    )
            agency = {
                "id": self._mint("agy-"),
                "agency_ref": agency_ref,
                "label": label,
                "members": [self._name(actor)],
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._agencies[agency["id"]] = agency
        self._record(actor, "agency_create", agency["id"], {"agency_ref": agency_ref})
        return self._agency_view(agency)

    def list_agencies(self, actor):
        """Agencies the actor is a member of, or all for a platform admin."""
        self._require_role(actor, "agency_read")
        result = []
        for agency in self._agencies.values():
            if self._is_admin(actor) or self._name(actor) in agency["members"]:
                result.append(self._agency_view(agency))
        return result

    def get_agency(self, agency_id, actor):
        agency = self._scoped_agency(agency_id, actor, "agency_read")
        return self._agency_view(agency)

    def add_member(self, agency_id, username, actor):
        """Add a member to an agency. Only the agency's creator or a
        platform admin may add; the gate is creator-or-admin (the
        service layer's route states the same), layered on the
        membership boundary."""
        agency = self._agency(agency_id)
        self._require_agency_access(agency, actor)
        if not (self._is_admin(actor) or agency["created_by"] == self._name(actor)):
            raise PermissionDenied(
                "only the agency creator or a platform admin may add members"
            )
        _text(username, "username")
        with self._lock:
            if username in agency["members"]:
                raise ValidationError(
                    "%r is already a member of agency %s" % (username, agency_id)
                )
            agency["members"].append(username)
        self._record(actor, "member_add", agency_id, {"username": username})
        return self._agency_view(agency)

    # -- workspaces -----------------------------------------------------------

    def create_workspace(self, agency_id, workspace_ref, title, actor):
        self._scoped_agency(agency_id, actor, "workspace_write")
        _text(workspace_ref, "workspace_ref")
        _text(title, "title")
        with self._lock:
            for existing in self._workspaces.values():
                if (
                    existing["agency_id"] == agency_id
                    and existing["workspace_ref"] == workspace_ref
                ):
                    raise ValidationError(
                        "workspace_ref %r already exists in agency %s"
                        % (workspace_ref, agency_id)
                    )
            workspace = {
                "id": self._mint("wsp-"),
                "agency_id": agency_id,
                "workspace_ref": workspace_ref,
                "title": title,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._workspaces[workspace["id"]] = workspace
        self._record(actor, "workspace_create", workspace["id"],
                     {"agency_id": agency_id})
        return dict(workspace)

    def list_workspaces(self, agency_id, actor):
        self._scoped_agency(agency_id, actor, "agency_read")
        return [
            dict(w) for w in self._workspaces.values()
            if w["agency_id"] == agency_id
        ]

    def get_workspace(self, agency_id, workspace_id, actor):
        self._scoped_agency(agency_id, actor, "agency_read")
        return dict(self._workspace_in(agency_id, workspace_id))

    # -- sessions ---------------------------------------------------------------

    def _session_view(self, session, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        expired = False
        if session["expires_at"] is not None:
            expired = moment > _parse_moment(session["expires_at"], "expires_at")
        consumed = bool(session["sandbox"]) and any(
            e["session_id"] == session["id"] for e in self._executions.values()
        )
        view = dict(session)
        view["expired"] = expired
        view["sandbox_consumed"] = consumed
        return view

    def create_session(self, agency_id, workspace_id, session_ref, actor,
                       purpose=None, sandbox=False, expires_at=None):
        self._scoped_agency(agency_id, actor, "session_write")
        self._workspace_in(agency_id, workspace_id)
        _text(session_ref, "session_ref")
        if purpose is not None and not isinstance(purpose, str):
            raise ValidationError("purpose must be a string")
        if not isinstance(sandbox, bool):
            raise ValidationError("sandbox must be a boolean")
        stored_expires = None
        if expires_at is not None:
            moment = _parse_moment(expires_at, "expires_at")
            stored_expires = (
                expires_at if isinstance(expires_at, str) else moment.isoformat()
            )
        with self._lock:
            for existing in self._sessions.values():
                if (
                    existing["workspace_id"] == workspace_id
                    and existing["session_ref"] == session_ref
                ):
                    raise ValidationError(
                        "session_ref %r already exists in workspace %s"
                        % (session_ref, workspace_id)
                    )
            session = {
                "id": self._mint("ses-"),
                "agency_id": agency_id,
                "workspace_id": workspace_id,
                "session_ref": session_ref,
                "purpose": purpose,
                "sandbox": sandbox,
                "status": "active",
                "expires_at": stored_expires,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._sessions[session["id"]] = session
        self._record(actor, "session_create", session["id"], {"agency_id": agency_id})
        return dict(session)

    def get_session(self, agency_id, session_id, actor, now=None):
        self._scoped_agency(agency_id, actor, "agency_read")
        session = self._session_in(agency_id, session_id)
        return self._session_view(session, now=now)

    def list_sessions(self, agency_id, actor, workspace_id=None, now=None):
        self._scoped_agency(agency_id, actor, "agency_read")
        if workspace_id is not None:
            self._workspace_in(agency_id, workspace_id)
        return [
            self._session_view(s, now=now) for s in self._sessions.values()
            if s["agency_id"] == agency_id
            and (workspace_id is None or s["workspace_id"] == workspace_id)
        ]

    def close_session(self, agency_id, session_id, actor):
        self._scoped_agency(agency_id, actor, "session_write")
        session = self._session_in(agency_id, session_id)
        with self._lock:
            if session["status"] != "active":
                raise ValidationError(
                    "session %s is %r; only an active session can be closed"
                    % (session_id, session["status"])
                )
            session["status"] = "closed"
        self._record(actor, "session_close", session_id, {"agency_id": agency_id})
        return dict(session)

    # -- executions ---------------------------------------------------------------

    def _check_sandbox_unused(self, session_id):
        """Single-use seam: a sandbox session accepts exactly one
        execution. Raises ValidationError if an execution already
        exists for the session. (This is the seam the negative
        control mutates.)"""
        for execution in self._executions.values():
            if execution["session_id"] == session_id:
                raise ValidationError(
                    "sandbox session %s has already been used: "
                    "a sandbox session accepts exactly one execution"
                    % (session_id,)
                )

    def record_execution(self, agency_id, session_id, execution_ref, actor,
                         kind="code", language=None):
        self._scoped_agency(agency_id, actor, "session_write")
        session = self._session_in(agency_id, session_id)
        _text(execution_ref, "execution_ref")
        if kind not in EXECUTION_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(EXECUTION_KINDS),)
            )
        if language is not None and not isinstance(language, str):
            raise ValidationError("language must be a string")
        with self._lock:
            if session["status"] != "active":
                raise ValidationError(
                    "session %s is %r; executions are recorded against "
                    "active sessions only" % (session_id, session["status"])
                )
            for existing in self._executions.values():
                if (
                    existing["session_id"] == session_id
                    and existing["execution_ref"] == execution_ref
                ):
                    raise ValidationError(
                        "execution_ref %r already exists in session %s"
                        % (execution_ref, session_id)
                    )
            if session["sandbox"]:
                self._check_sandbox_unused(session_id)
            execution = {
                "id": self._mint("exe-"),
                "agency_id": agency_id,
                "session_id": session_id,
                "execution_ref": execution_ref,
                "kind": kind,
                "language": language,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._executions[execution["id"]] = execution
        self._record(actor, "execution_record", execution["id"],
                     {"agency_id": agency_id, "session_id": session_id})
        return dict(execution)

    def list_executions(self, agency_id, session_id, actor):
        self._scoped_agency(agency_id, actor, "agency_read")
        self._session_in(agency_id, session_id)
        return [
            dict(e) for e in self._executions.values()
            if e["agency_id"] == agency_id and e["session_id"] == session_id
        ]

    # -- library sources ------------------------------------------------------------

    def register_library_source(self, source_ref, kind, actor,
                                title=None, jurisdiction_ref=None):
        self._require_role(actor, "library_write")
        _text(source_ref, "source_ref")
        if kind not in LIBRARY_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(LIBRARY_KINDS),)
            )
        if title is not None and not isinstance(title, str):
            raise ValidationError("title must be a string")
        if jurisdiction_ref is not None:
            _text(jurisdiction_ref, "jurisdiction_ref")
        with self._lock:
            for existing in self._library_sources.values():
                if existing["source_ref"] == source_ref:
                    raise ValidationError(
                        "source_ref already exists: %r" % (source_ref,)
                    )
            source = {
                "id": self._mint("lib-"),
                "source_ref": source_ref,
                "kind": kind,
                "title": title,
                "jurisdiction_ref": jurisdiction_ref,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._library_sources[source["id"]] = source
        self._record(actor, "library_register", source["id"], {"source_ref": source_ref})
        return dict(source)

    def list_library_sources(self, actor, kind=None):
        # Platform library: reads are open to any actor.
        if kind is not None and kind not in LIBRARY_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(LIBRARY_KINDS),)
            )
        return [
            dict(s) for s in self._library_sources.values()
            if kind is None or s["kind"] == kind
        ]

    def get_library_source(self, source_id, actor):
        # Platform library: reads are open to any actor.
        source = self._library_sources.get(source_id)
        if source is None:
            raise NotFoundError("no such library source: %r" % (source_id,))
        return dict(source)

    # -- saved searches ---------------------------------------------------------------

    def save_search(self, agency_id, search_ref, query_sha256, result_count,
                    actor, workspace_id=None):
        """Record a saved search. There is deliberately no parameter
        for query text: the caller supplies the query's SHA-256
        digest, and only the digest is stored."""
        self._scoped_agency(agency_id, actor, "search_write")
        if workspace_id is not None:
            self._workspace_in(agency_id, workspace_id)
        _text(search_ref, "search_ref")
        _sha256(query_sha256, "query_sha256")
        _count_nonneg(result_count, "result_count")
        with self._lock:
            for existing in self._searches.values():
                if (
                    existing["agency_id"] == agency_id
                    and existing["search_ref"] == search_ref
                ):
                    raise ValidationError(
                        "search_ref %r already exists in agency %s"
                        % (search_ref, agency_id)
                    )
            search = {
                "id": self._mint("sea-"),
                "agency_id": agency_id,
                "workspace_id": workspace_id,
                "search_ref": search_ref,
                "query_sha256": query_sha256,
                "result_count": result_count,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._searches[search["id"]] = search
        self._record(actor, "search_save", search["id"], {"agency_id": agency_id})
        return dict(search)

    def list_searches(self, agency_id, actor, workspace_id=None):
        self._scoped_agency(agency_id, actor, "agency_read")
        if workspace_id is not None:
            self._workspace_in(agency_id, workspace_id)
        return [
            dict(s) for s in self._searches.values()
            if s["agency_id"] == agency_id
            and (workspace_id is None or s["workspace_id"] == workspace_id)
        ]

    def get_search(self, agency_id, search_id, actor):
        self._scoped_agency(agency_id, actor, "agency_read")
        search = self._searches.get(search_id)
        if search is None or search["agency_id"] != agency_id:
            raise NotFoundError(
                "no such search in agency %s: %r" % (agency_id, search_id)
            )
        return dict(search)

    # -- documents ---------------------------------------------------------------

    def register_document(self, agency_id, workspace_id, doc_ref, sha256,
                          size_bytes, actor, kind="generated", session_id=None):
        """Record a document's metadata and checksum. Content is
        never stored here; the generation/storage engines are
        Extended."""
        self._scoped_agency(agency_id, actor, "document_write")
        self._workspace_in(agency_id, workspace_id)
        _text(doc_ref, "doc_ref")
        if kind not in DOCUMENT_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(DOCUMENT_KINDS),)
            )
        _sha256(sha256, "sha256")
        _count_nonneg(size_bytes, "size_bytes")
        if session_id is not None:
            session = self._session_in(agency_id, session_id)
            if session["workspace_id"] != workspace_id:
                raise NotFoundError(
                    "no such session in workspace %s: %r" % (workspace_id, session_id)
                )
        with self._lock:
            for existing in self._documents.values():
                if (
                    existing["workspace_id"] == workspace_id
                    and existing["doc_ref"] == doc_ref
                ):
                    raise ValidationError(
                        "doc_ref %r already exists in workspace %s"
                        % (doc_ref, workspace_id)
                    )
            document = {
                "id": self._mint("doc-"),
                "agency_id": agency_id,
                "workspace_id": workspace_id,
                "session_id": session_id,
                "doc_ref": doc_ref,
                "kind": kind,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._documents[document["id"]] = document
        self._record(actor, "document_register", document["id"],
                     {"agency_id": agency_id})
        return dict(document)

    def get_document(self, agency_id, doc_id, actor):
        self._scoped_agency(agency_id, actor, "agency_read")
        document = self._documents.get(doc_id)
        if document is None or document["agency_id"] != agency_id:
            raise NotFoundError(
                "no such document in agency %s: %r" % (agency_id, doc_id)
            )
        return dict(document)

    def list_documents(self, agency_id, actor, workspace_id=None):
        self._scoped_agency(agency_id, actor, "agency_read")
        if workspace_id is not None:
            self._workspace_in(agency_id, workspace_id)
        return [
            dict(d) for d in self._documents.values()
            if d["agency_id"] == agency_id
            and (workspace_id is None or d["workspace_id"] == workspace_id)
        ]

    def verify_document(self, agency_id, doc_id, content, actor):
        """Recompute the SHA-256 of caller-supplied bytes and compare
        it to the registered checksum. Stores nothing."""
        self._scoped_agency(agency_id, actor, "agency_read")
        document = self._documents.get(doc_id)
        if document is None or document["agency_id"] != agency_id:
            raise NotFoundError(
                "no such document in agency %s: %r" % (agency_id, doc_id)
            )
        if isinstance(content, str):
            content = content.encode("utf-8")
        if not isinstance(content, (bytes, bytearray)):
            raise ValidationError("content must be bytes")
        computed = hashlib.sha256(bytes(content)).hexdigest()
        return {
            "document_id": doc_id,
            "sha256": document["sha256"],
            "computed_sha256": computed,
            "matches": computed == document["sha256"],
        }

    # -- usage records ---------------------------------------------------------------

    def record_usage(self, agency_id, usage_ref, kind, quantity, actor,
                     session_id=None, workspace_id=None):
        self._scoped_agency(agency_id, actor, "usage_write")
        _text(usage_ref, "usage_ref")
        if kind not in USAGE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(USAGE_KINDS),)
            )
        _quantity(quantity)
        if workspace_id is not None:
            self._workspace_in(agency_id, workspace_id)
        if session_id is not None:
            self._session_in(agency_id, session_id)
        with self._lock:
            for existing in self._usage.values():
                if (
                    existing["agency_id"] == agency_id
                    and existing["usage_ref"] == usage_ref
                ):
                    raise ValidationError(
                        "usage_ref %r already exists in agency %s"
                        % (usage_ref, agency_id)
                    )
            usage = {
                "id": self._mint("use-"),
                "agency_id": agency_id,
                "workspace_id": workspace_id,
                "session_id": session_id,
                "usage_ref": usage_ref,
                "kind": kind,
                "quantity": quantity,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._usage[usage["id"]] = usage
        self._record(actor, "usage_record", usage["id"], {"agency_id": agency_id})
        return dict(usage)

    def list_usage(self, agency_id, actor, kind=None):
        self._scoped_agency(agency_id, actor, "agency_read")
        if kind is not None and kind not in USAGE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(USAGE_KINDS),)
            )
        return [
            dict(u) for u in self._usage.values()
            if u["agency_id"] == agency_id and (kind is None or u["kind"] == kind)
        ]

    # -- usage exports ---------------------------------------------------------------

    def export_usage(self, agency_id, export_ref, actor, since=None, until=None):
        """Export the agency's usage records in an optional time
        window as a manifest: record count, total quantity, and a
        SHA-256 checksum of the canonical exported set, computed at
        export time from the records."""
        self._scoped_agency(agency_id, actor, "export")
        _text(export_ref, "export_ref")
        since_moment = _parse_moment(since, "since") if since is not None else None
        until_moment = _parse_moment(until, "until") if until is not None else None
        if (
            since_moment is not None
            and until_moment is not None
            and until_moment < since_moment
        ):
            raise ValidationError("until must not precede since")
        with self._lock:
            for existing in self._exports.values():
                if (
                    existing["agency_id"] == agency_id
                    and existing["export_ref"] == export_ref
                ):
                    raise ValidationError(
                        "export_ref %r already exists in agency %s"
                        % (export_ref, agency_id)
                    )
            selected = []
            for usage in self._usage.values():
                if usage["agency_id"] != agency_id:
                    continue
                created = _parse_moment(usage["created_utc"], "created_utc")
                if since_moment is not None and created < since_moment:
                    continue
                if until_moment is not None and created > until_moment:
                    continue
                selected.append(usage)
            export = {
                "id": self._mint("exp-"),
                "agency_id": agency_id,
                "export_ref": export_ref,
                "since": since,
                "until": until,
                "record_count": len(selected),
                "total_quantity": sum(u["quantity"] for u in selected),
                "checksum": _export_checksum(selected),
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._exports[export["id"]] = export
        self._record(actor, "usage_export", export["id"], {"agency_id": agency_id})
        return dict(export)

    def list_exports(self, agency_id, actor):
        self._scoped_agency(agency_id, actor, "agency_read")
        return [dict(e) for e in self._exports.values() if e["agency_id"] == agency_id]

    # -- reporting & registry search ---------------------------------------------------

    def agency_report(self, agency_id, actor, now=None):
        """Counts and quantity sums for one agency, computed on read.
        ``sandbox_sessions_consumed`` is the derived count (sandbox
        sessions with an execution recorded); nothing is scored."""
        self._scoped_agency(agency_id, actor, "report_read")
        sessions = [s for s in self._sessions.values() if s["agency_id"] == agency_id]
        by_status = {status: 0 for status in SESSION_STATUSES}
        for session in sessions:
            by_status[session["status"]] += 1
        sandbox_sessions = [s for s in sessions if s["sandbox"]]
        consumed = sum(
            1 for s in sandbox_sessions
            if any(e["session_id"] == s["id"] for e in self._executions.values())
        )
        usage_by_kind = {}
        for usage in self._usage.values():
            if usage["agency_id"] == agency_id:
                usage_by_kind[usage["kind"]] = (
                    usage_by_kind.get(usage["kind"], 0) + usage["quantity"]
                )
        return {
            "agency_id": agency_id,
            "workspace_count": sum(
                1 for w in self._workspaces.values() if w["agency_id"] == agency_id
            ),
            "session_count": len(sessions),
            "sessions_by_status": by_status,
            "sandbox_sessions": len(sandbox_sessions),
            "sandbox_sessions_consumed": consumed,
            "execution_count": sum(
                1 for e in self._executions.values() if e["agency_id"] == agency_id
            ),
            "search_count": sum(
                1 for s in self._searches.values() if s["agency_id"] == agency_id
            ),
            "document_count": sum(
                1 for d in self._documents.values() if d["agency_id"] == agency_id
            ),
            "export_count": sum(
                1 for e in self._exports.values() if e["agency_id"] == agency_id
            ),
            "usage_by_kind": usage_by_kind,
        }

    def search_registry(self, actor, query):
        """Literal case-insensitive substring search over registry
        metadata (references, titles, labels, kinds), scoped to
        agencies the actor belongs to (or all for a platform admin),
        plus the platform library. Digests and checksums are never
        matched."""
        self._require_role(actor, "agency_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.strip().lower()

        def hit(*fields):
            return any(
                f is not None and needle in str(f).lower() for f in fields
            )

        visible = {
            a["id"] for a in self._agencies.values()
            if self._is_admin(actor) or self._name(actor) in a["members"]
        }
        return {
            "agencies": [
                self._agency_view(a) for a in self._agencies.values()
                if a["id"] in visible and hit(a["agency_ref"], a["label"])
            ],
            "workspaces": [
                dict(w) for w in self._workspaces.values()
                if w["agency_id"] in visible
                and hit(w["workspace_ref"], w["title"])
            ],
            "sessions": [
                self._session_view(s) for s in self._sessions.values()
                if s["agency_id"] in visible
                and hit(s["session_ref"], s["purpose"])
            ],
            "library_sources": [
                dict(s) for s in self._library_sources.values()
                if hit(s["source_ref"], s["kind"], s["title"],
                       s["jurisdiction_ref"])
            ],
            "documents": [
                dict(d) for d in self._documents.values()
                if d["agency_id"] in visible and hit(d["doc_ref"], d["kind"])
            ],
        }
