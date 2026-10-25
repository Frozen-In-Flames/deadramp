"""The legal research records substrate.

Clean-room implementation of the Group 34 union spec's core: matter
registry & members, source registry, document registry (metadata +
SHA-256 checksums, never content), verify-by-content, saved-search
records (query stored as a SHA-256 digest only), annotation records
(note stored as a SHA-256 digest only), citation-check records
(treatment recorded verbatim), registry reporting, and registry
search — over an append-only audit log.

Privacy discipline (hard rule): every entity is keyed by an opaque
caller-supplied reference and carries only the fields in the contract.
There is no field anywhere that can hold a real name, a case subject,
or any content. Validation always precedes mutation: a failed
operation changes nothing, consumes no id, and records nothing.
"""

import hashlib
import re
from datetime import datetime, timezone

from .access import User, require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

SOURCE_KINDS = (
    "statute",
    "case_law",
    "regulation",
    "secondary",
    "guidance",
    "standard_document",
)

DOCUMENT_STATUSES = ("registered", "in_review", "reviewed")

# document lifecycle: current status -> set of allowed next statuses
_DOCUMENT_TRANSITIONS = {
    "registered": {"in_review"},
    "in_review": {"reviewed"},
    "reviewed": set(),
}

ANNOTATION_TARGET_KINDS = ("document", "search", "source")

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_sha256(value, what):
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise ValidationError(
            "%s must be exactly 64 lowercase hex characters" % (what,)
        )
    return value


def _validate_count(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be an integer >= 0" % (what,))
    return value


class LawEnfStore:
    """In-memory store for the legal research records substrate."""

    def __init__(self, audit=None):
        self.audit = audit
        self._matters = {}
        self._sources = {}
        self._documents = {}
        self._searches = {}
        self._annotations = {}
        self._citation_checks = {}
        self._counters = {"mat": 0, "src": 0, "doc": 0, "sea": 0, "ann": 0, "cit": 0}

    # -- internals ----------------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details=details)

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

    def _require_matter_access(self, matter, actor):
        """Membership guard: the actor must be a member of the matter,
        or hold the platform admin role. (This is the guard the
        negative control mutates.)"""
        if self._is_admin(actor):
            return
        if self._name(actor) not in matter["members"]:
            raise PermissionDenied(
                "actor %r is not a member of matter %s"
                % (self._name(actor), matter["id"])
            )

    def _get_matter_record(self, matter_id):
        matter = self._matters.get(matter_id)
        if matter is None:
            raise NotFoundError("matter not found: %r" % (matter_id,))
        return matter

    def _scoped_matter(self, matter_id, actor, action, need_open=False):
        matter = self._get_matter_record(matter_id)
        self._require_role(actor, action)
        self._require_matter_access(matter, actor)
        if need_open and matter["status"] != "open":
            raise ValidationError(
                "matter %s is closed; no new records may be added" % (matter_id,)
            )
        return matter

    @staticmethod
    def _matter_view(matter):
        view = dict(matter)
        view["members"] = list(matter["members"])
        return view

    def _child_or_404(self, table, matter_id, child_id, what):
        child = table.get(child_id)
        if child is None or child["matter_id"] != matter_id:
            raise NotFoundError("%s not found: %r" % (what, child_id))
        return child

    def _check_ref_unique(self, table, matter_id, ref_field, ref, what):
        for child in table.values():
            if child["matter_id"] == matter_id and child[ref_field] == ref:
                raise ValidationError(
                    "%s %r already exists in matter %s" % (what, ref, matter_id)
                )

    # -- matters ------------------------------------------------------

    def create_matter(self, matter_ref, actor):
        self._require_role(actor, "matter_write")
        _validate_non_empty(matter_ref, "matter_ref")
        for matter in self._matters.values():
            if matter["matter_ref"] == matter_ref:
                raise ValidationError("matter_ref %r already exists" % (matter_ref,))
        matter_id = self._next_id("mat")
        matter = {
            "id": matter_id,
            "matter_ref": matter_ref,
            "status": "open",
            "members": [self._name(actor)],
            "created_by": self._name(actor),
            "created_utc": _utc_now(),
        }
        self._matters[matter_id] = matter
        self._audit(actor, "matter_create", matter_id)
        return self._matter_view(matter)

    def list_matters(self, actor):
        self._require_role(actor, "matter_read")
        out = []
        for matter in self._matters.values():
            if self._is_admin(actor) or self._name(actor) in matter["members"]:
                out.append(self._matter_view(matter))
        return out

    def get_matter(self, matter_id, actor):
        matter = self._scoped_matter(matter_id, actor, "matter_read")
        return self._matter_view(matter)

    def add_member(self, matter_id, username, actor):
        matter = self._scoped_matter(matter_id, actor, "matter_write")
        if not (self._is_admin(actor) or matter["created_by"] == self._name(actor)):
            raise PermissionDenied(
                "only the matter creator or a platform admin may add members"
            )
        _validate_non_empty(username, "username")
        if username in matter["members"]:
            raise ValidationError(
                "%r is already a member of matter %s" % (username, matter_id)
            )
        matter["members"].append(username)
        self._audit(actor, "member_add", matter_id, details={"username": username})
        return self._matter_view(matter)

    def close_matter(self, matter_id, actor):
        matter = self._scoped_matter(matter_id, actor, "matter_write")
        if matter["status"] != "open":
            raise ValidationError("matter %s is not open" % (matter_id,))
        matter["status"] = "closed"
        self._audit(actor, "matter_close", matter_id)
        return self._matter_view(matter)

    def reopen_matter(self, matter_id, actor):
        matter = self._scoped_matter(matter_id, actor, "matter_write")
        if matter["status"] != "closed":
            raise ValidationError("matter %s is not closed" % (matter_id,))
        matter["status"] = "open"
        self._audit(actor, "matter_reopen", matter_id)
        return self._matter_view(matter)

    # -- sources --------------------------------------------------------

    def create_source(self, matter_id, source_ref, kind, actor,
                      jurisdiction_ref=None, citation_ref=None):
        self._scoped_matter(matter_id, actor, "source_write", need_open=True)
        _validate_non_empty(source_ref, "source_ref")
        if kind not in SOURCE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(SOURCE_KINDS),)
            )
        if jurisdiction_ref is not None:
            _validate_non_empty(jurisdiction_ref, "jurisdiction_ref")
        if citation_ref is not None:
            _validate_non_empty(citation_ref, "citation_ref")
        self._check_ref_unique(self._sources, matter_id, "source_ref",
                               source_ref, "source_ref")
        source_id = self._next_id("src")
        source = {
            "id": source_id,
            "matter_id": matter_id,
            "source_ref": source_ref,
            "kind": kind,
            "jurisdiction_ref": jurisdiction_ref,
            "citation_ref": citation_ref,
            "created_by": self._name(actor),
            "created_utc": _utc_now(),
        }
        self._sources[source_id] = source
        self._audit(actor, "source_create", source_id)
        return dict(source)

    def list_sources(self, matter_id, actor, kind=None):
        self._scoped_matter(matter_id, actor, "matter_read")
        if kind is not None and kind not in SOURCE_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(SOURCE_KINDS),)
            )
        return [
            dict(s) for s in self._sources.values()
            if s["matter_id"] == matter_id and (kind is None or s["kind"] == kind)
        ]

    def get_source(self, matter_id, source_id, actor):
        self._scoped_matter(matter_id, actor, "matter_read")
        return dict(self._child_or_404(self._sources, matter_id, source_id, "source"))

    # -- documents ------------------------------------------------------

    def register_document(self, matter_id, doc_ref, sha256, size_bytes, actor):
        self._scoped_matter(matter_id, actor, "document_write", need_open=True)
        _validate_non_empty(doc_ref, "doc_ref")
        _validate_sha256(sha256, "sha256")
        _validate_count(size_bytes, "size_bytes")
        self._check_ref_unique(self._documents, matter_id, "doc_ref",
                               doc_ref, "doc_ref")
        doc_id = self._next_id("doc")
        doc = {
            "id": doc_id,
            "matter_id": matter_id,
            "doc_ref": doc_ref,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "status": "registered",
            "created_by": self._name(actor),
            "created_utc": _utc_now(),
        }
        self._documents[doc_id] = doc
        self._audit(actor, "document_register", doc_id)
        return dict(doc)

    def get_document(self, matter_id, doc_id, actor):
        self._scoped_matter(matter_id, actor, "matter_read")
        return dict(self._child_or_404(self._documents, matter_id, doc_id, "document"))

    def list_documents(self, matter_id, actor, status=None):
        self._scoped_matter(matter_id, actor, "matter_read")
        if status is not None and status not in DOCUMENT_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(DOCUMENT_STATUSES),)
            )
        return [
            dict(d) for d in self._documents.values()
            if d["matter_id"] == matter_id
            and (status is None or d["status"] == status)
        ]

    def _transition_document(self, matter_id, doc_id, actor, target, action_name):
        self._scoped_matter(matter_id, actor, "document_write", need_open=True)
        doc = self._child_or_404(self._documents, matter_id, doc_id, "document")
        if target not in _DOCUMENT_TRANSITIONS[doc["status"]]:
            raise ValidationError(
                "document %s cannot move from %s to %s"
                % (doc_id, doc["status"], target)
            )
        doc["status"] = target
        self._audit(actor, action_name, doc_id)
        return dict(doc)

    def begin_review(self, matter_id, doc_id, actor):
        return self._transition_document(
            matter_id, doc_id, actor, "in_review", "document_begin_review")

    def complete_review(self, matter_id, doc_id, actor):
        return self._transition_document(
            matter_id, doc_id, actor, "reviewed", "document_complete_review")

    def verify_document(self, matter_id, doc_id, content, actor):
        self._scoped_matter(matter_id, actor, "matter_read")
        doc = self._child_or_404(self._documents, matter_id, doc_id, "document")
        if isinstance(content, str):
            content = content.encode("utf-8")
        if not isinstance(content, (bytes, bytearray)):
            raise ValidationError("content must be bytes")
        computed = hashlib.sha256(bytes(content)).hexdigest()
        return {
            "document_id": doc_id,
            "sha256": doc["sha256"],
            "computed_sha256": computed,
            "matches": computed == doc["sha256"],
        }

    # -- saved searches ---------------------------------------------------

    def save_search(self, matter_id, search_ref, query_sha256, result_count, actor):
        self._scoped_matter(matter_id, actor, "search_write", need_open=True)
        _validate_non_empty(search_ref, "search_ref")
        _validate_sha256(query_sha256, "query_sha256")
        _validate_count(result_count, "result_count")
        self._check_ref_unique(self._searches, matter_id, "search_ref",
                               search_ref, "search_ref")
        search_id = self._next_id("sea")
        search = {
            "id": search_id,
            "matter_id": matter_id,
            "search_ref": search_ref,
            "query_sha256": query_sha256,
            "result_count": result_count,
            "created_by": self._name(actor),
            "created_utc": _utc_now(),
        }
        self._searches[search_id] = search
        self._audit(actor, "search_save", search_id)
        return dict(search)

    def list_searches(self, matter_id, actor):
        self._scoped_matter(matter_id, actor, "matter_read")
        return [dict(s) for s in self._searches.values()
                if s["matter_id"] == matter_id]

    def get_search(self, matter_id, search_id, actor):
        self._scoped_matter(matter_id, actor, "matter_read")
        return dict(self._child_or_404(self._searches, matter_id, search_id, "search"))

    # -- annotations ------------------------------------------------------

    def add_annotation(self, matter_id, target_kind, target_id,
                       annotation_ref, note_sha256, actor):
        self._scoped_matter(matter_id, actor, "annotation_write", need_open=True)
        _validate_non_empty(annotation_ref, "annotation_ref")
        _validate_sha256(note_sha256, "note_sha256")
        if target_kind not in ANNOTATION_TARGET_KINDS:
            raise ValidationError(
                "target_kind must be one of %s"
                % (", ".join(ANNOTATION_TARGET_KINDS),)
            )
        table = {"document": self._documents, "search": self._searches,
                 "source": self._sources}[target_kind]
        self._child_or_404(table, matter_id, target_id, target_kind)
        self._check_ref_unique(self._annotations, matter_id, "annotation_ref",
                               annotation_ref, "annotation_ref")
        ann_id = self._next_id("ann")
        ann = {
            "id": ann_id,
            "matter_id": matter_id,
            "target_kind": target_kind,
            "target_id": target_id,
            "annotation_ref": annotation_ref,
            "note_sha256": note_sha256,
            "created_by": self._name(actor),
            "created_utc": _utc_now(),
        }
        self._annotations[ann_id] = ann
        self._audit(actor, "annotation_add", ann_id)
        return dict(ann)

    def list_annotations(self, matter_id, actor, target_id=None):
        self._scoped_matter(matter_id, actor, "matter_read")
        return [
            dict(a) for a in self._annotations.values()
            if a["matter_id"] == matter_id
            and (target_id is None or a["target_id"] == target_id)
        ]

    # -- citation checks ----------------------------------------------------

    def record_citation_check(self, matter_id, citation_ref, treatment,
                              actor, source_id=None):
        self._scoped_matter(matter_id, actor, "citation_write", need_open=True)
        _validate_non_empty(citation_ref, "citation_ref")
        _validate_non_empty(treatment, "treatment")
        if source_id is not None:
            self._child_or_404(self._sources, matter_id, source_id, "source")
        check_id = self._next_id("cit")
        check = {
            "id": check_id,
            "matter_id": matter_id,
            "citation_ref": citation_ref,
            "source_id": source_id,
            "treatment": treatment,
            "created_by": self._name(actor),
            "created_utc": _utc_now(),
        }
        self._citation_checks[check_id] = check
        self._audit(actor, "citation_check_record", check_id)
        return dict(check)

    def list_citation_checks(self, matter_id, actor):
        self._scoped_matter(matter_id, actor, "matter_read")
        return [dict(c) for c in self._citation_checks.values()
                if c["matter_id"] == matter_id]

    # -- reporting & registry search -----------------------------------------

    def matter_report(self, matter_id, actor):
        matter = self._scoped_matter(matter_id, actor, "report_read")
        sources_by_kind = {}
        for s in self._sources.values():
            if s["matter_id"] == matter_id:
                sources_by_kind[s["kind"]] = sources_by_kind.get(s["kind"], 0) + 1
        documents_by_status = {}
        for d in self._documents.values():
            if d["matter_id"] == matter_id:
                documents_by_status[d["status"]] = \
                    documents_by_status.get(d["status"], 0) + 1
        checks_by_treatment = {}
        check_count = 0
        for c in self._citation_checks.values():
            if c["matter_id"] == matter_id:
                check_count += 1
                checks_by_treatment[c["treatment"]] = \
                    checks_by_treatment.get(c["treatment"], 0) + 1
        return {
            "matter_id": matter_id,
            "status": matter["status"],
            "member_count": len(matter["members"]),
            "sources_by_kind": sources_by_kind,
            "documents_by_status": documents_by_status,
            "search_count": sum(1 for s in self._searches.values()
                                if s["matter_id"] == matter_id),
            "annotation_count": sum(1 for a in self._annotations.values()
                                    if a["matter_id"] == matter_id),
            "citation_check_count": check_count,
            "citation_checks_by_treatment": checks_by_treatment,
        }

    def search_registry(self, actor, query):
        self._require_role(actor, "matter_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.strip().lower()

        def hit(*fields):
            return any(f is not None and needle in str(f).lower() for f in fields)

        visible = {
            m["id"] for m in self._matters.values()
            if self._is_admin(actor) or self._name(actor) in m["members"]
        }
        return {
            "matters": [self._matter_view(m) for m in self._matters.values()
                        if m["id"] in visible
                        and hit(m["matter_ref"], m["status"])],
            "sources": [dict(s) for s in self._sources.values()
                        if s["matter_id"] in visible
                        and hit(s["source_ref"], s["kind"],
                                s["jurisdiction_ref"], s["citation_ref"])],
            "documents": [dict(d) for d in self._documents.values()
                          if d["matter_id"] in visible
                          and hit(d["doc_ref"], d["status"])],
            "searches": [dict(s) for s in self._searches.values()
                         if s["matter_id"] in visible
                         and hit(s["search_ref"])],
            "citation_checks": [dict(c) for c in self._citation_checks.values()
                                if c["matter_id"] in visible
                                and hit(c["citation_ref"], c["treatment"])],
        }
