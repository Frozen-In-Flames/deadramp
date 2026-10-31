"""Content management store: sites & sections, content types, content
items & revisions, editorial lifecycle, publishing, assets, tags,
search, and reporting.

Clean-room implementation of the contract.

Permission convention (mirrors the data-management group): store
methods take an ``actor``. When the actor is a User-like object (it
has a ``role`` attribute) the store enforces
:func:`cms.access.require` for the method's action *before* any state
change or id allocation, so a denied operation consumes no id and
changes nothing -- and the denied attempt is audited as
``"<action>:denied"``. Where a plain string is passed it carries
identity (for provenance) but no role, so there is nothing to enforce
against at this layer; the service layer, which knows the role
registry, is responsible for enforcement in that case -- and it
always passes User objects.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``site-``, ``sec-``, ``ct-`` for
custom types, ``ci-``, ``rev-``, ``pub-``, ``asset-``, ``tag-``). The
built-in content types use fixed readable ids -- ``ct-page``,
``ct-article``, ``ct-document``, ``ct-collection`` -- pre-registered
at store init with ``created_by == "system"``; they do not consume
the custom-type counter, so the first custom type is ``ct-1``.

Editing rule (documented, kept simple): an item may be edited while
its status is ``draft`` by any role holding ``item_edit`` (an author
only on their own items); while ``in_review`` only admin, publisher
and editor may edit. Editing an item in any other status raises
:class:`ValidationError`. Each edit mints a new revision record.
"""

import hashlib
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

ASSET_KINDS = ("document", "image", "video", "audio", "dataset", "other")
KNOWN_ASSET_KINDS = frozenset(ASSET_KINDS)
ITEM_STATUSES = ("draft", "in_review", "approved", "published", "archived")
KNOWN_ITEM_STATUSES = frozenset(ITEM_STATUSES)
BUILTIN_TYPES = (
    ("ct-page", "page"),
    ("ct-article", "article"),
    ("ct-document", "document"),
    ("ct-collection", "collection"),
)
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


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


def _id_num(obj_id):
    try:
        return int(str(obj_id).rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_slug(value, what="slug"):
    if not isinstance(value, str) or not _SLUG_RE.match(value or ""):
        raise ValidationError(
            "%s must be non-empty, lowercase alphanumerics and hyphens only: %r" % (what, value)
        )
    return value


def _validate_metadata(metadata):
    if metadata is None:
        return {}
    if not isinstance(metadata, dict):
        raise ValidationError("metadata must be a dict")
    return dict(metadata)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def window_state(item, publish_record, now=None):
    """Derived publishing window state, computed from stored facts only.

    Returns ``None`` when the item is not published (or has no publish
    record), ``"scheduled"`` when ``now`` is before the effective
    publish instant, ``"expired"`` when ``now`` is at or after
    ``expire_at``, and ``"live"`` otherwise. The effective publish
    instant is the record's ``publish_at`` when given, else its
    ``published_utc``. ``now`` may be an ISO string or a datetime;
    ``None`` means the current UTC instant.
    """
    if not item or item.get("status") != "published" or not publish_record:
        return None
    now_dt = _coerce_now(now)
    publish_raw = publish_record.get("publish_at") or publish_record.get("published_utc")
    if publish_raw:
        publish_dt = _parse_iso_datetime(publish_raw, "publish_at")
        if now_dt < publish_dt:
            return "scheduled"
    expire_raw = publish_record.get("expire_at")
    if expire_raw:
        expire_dt = _parse_iso_datetime(expire_raw, "expire_at")
        if now_dt >= expire_dt:
            return "expired"
    return "live"


class CmsStore:
    """In-memory store for the content management service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._sites = {}
        self._sections = {}
        self._types = {}
        self._items = {}
        self._revisions = {}
        self._publishes = {}
        self._assets = {}
        self._tags = {}
        self._counters = {
            "site": 0, "sec": 0, "ct": 0, "ci": 0,
            "rev": 0, "pub": 0, "asset": 0, "tag": 0,
        }
        self._lock = threading.RLock()
        now = _utc_now()
        for type_id, name in BUILTIN_TYPES:
            self._types[type_id] = {
                "id": type_id,
                "name": name,
                "description": "Built-in content type: %s" % name,
                "builtin": True,
                "created_by": "system",
                "created_utc": now,
            }

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _audit_denied(self, actor, action, target):
        self._audit(actor, "%s:denied" % (action,), target)

    def _require(self, actor, action, target=None):
        """Enforce ``action`` for User-like actors; audit denials.

        Plain-string actors carry identity but no role (see module
        docstring): nothing to enforce at this layer.
        """
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit_denied(actor, action, target)
                raise

    def _get_site_record(self, site_id):
        rec = self._sites.get(site_id)
        if rec is None:
            raise NotFoundError("site not found: %r" % (site_id,))
        return rec

    def _get_section_record(self, section_id):
        rec = self._sections.get(section_id)
        if rec is None:
            raise NotFoundError("section not found: %r" % (section_id,))
        return rec

    def _get_type_record(self, type_id):
        rec = self._types.get(type_id)
        if rec is None:
            raise NotFoundError("content type not found: %r" % (type_id,))
        return rec

    def _get_item_record(self, item_id):
        rec = self._items.get(item_id)
        if rec is None:
            raise NotFoundError("content item not found: %r" % (item_id,))
        return rec

    def _get_asset_record(self, asset_id):
        rec = self._assets.get(asset_id)
        if rec is None:
            raise NotFoundError("asset not found: %r" % (asset_id,))
        return rec

    def _get_tag_record(self, tag_id):
        rec = self._tags.get(tag_id)
        if rec is None:
            raise NotFoundError("tag not found: %r" % (tag_id,))
        return rec

    def _validate_tag_ids(self, tag_ids):
        if tag_ids is None:
            return []
        if not isinstance(tag_ids, list):
            raise ValidationError("tag_ids must be a list of tag ids")
        result = []
        for tag_id in tag_ids:
            self._get_tag_record(tag_id)
            result.append(tag_id)
        return result

    def _latest_publish(self, item_id):
        records = [p for p in self._publishes.values() if p["item_id"] == item_id]
        if not records:
            return None
        records.sort(key=lambda p: _id_num(p["id"]))
        return records[-1]

    def _copy_item(self, item, now=None):
        copied = dict(item)
        copied["metadata"] = dict(item["metadata"])
        copied["tag_ids"] = list(item["tag_ids"])
        record = self._latest_publish(item["id"])
        state = window_state(copied, record, now=now)
        copied["window_state"] = state
        copied["is_live"] = state == "live"
        return copied

    @staticmethod
    def _copy_revision(rev):
        copied = dict(rev)
        copied["metadata"] = dict(rev["metadata"])
        copied["tag_ids"] = list(rev["tag_ids"])
        return copied

    def _mint_revision(self, item, actor):
        revision_id = self._next_id("rev")
        number = sum(1 for r in self._revisions.values() if r["item_id"] == item["id"]) + 1
        rev = {
            "id": revision_id,
            "item_id": item["id"],
            "revision": number,
            "title": item["title"],
            "slug": item["slug"],
            "body": item["body"],
            "metadata": dict(item["metadata"]),
            "tag_ids": list(item["tag_ids"]),
            "edited_by": actor_name(actor),
            "created_utc": _utc_now(),
        }
        self._revisions[revision_id] = rev
        item["revision"] = number
        item["latest_revision_id"] = revision_id
        return rev

    def _check_author_owns(self, actor, item, action):
        """Author-role actors may act only on their own items."""
        if getattr(actor, "role", None) == "author" and item["author"] != actor_name(actor):
            self._audit_denied(actor, action, item["id"])
            raise PermissionDenied(
                "permission denied: author %r may only act on their own items"
                % (actor_name(actor),)
            )

    # -- 1. sites & sections ------------------------------------------

    def create_site(self, actor, name, slug, description=""):
        """Create a site. Action: site_write. Ids: site-{n}."""
        self._require(actor, "site_write")
        _validate_non_empty(name, "site name")
        _validate_slug(slug, "site slug")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        with self._lock:
            for existing in self._sites.values():
                if existing["slug"] == slug:
                    raise ValidationError("duplicate site slug: %r" % (slug,))
            site_id = self._next_id("site")
            now = _utc_now()
            site = {
                "id": site_id, "name": name, "slug": slug,
                "description": description,
                "created_by": actor_name(actor),
                "created_utc": now, "updated_utc": now,
            }
            self._sites[site_id] = site
            self._audit(actor, "site_create", site_id, details={"slug": slug})
            return dict(site)

    def get_site(self, site_id, actor=None):
        """Return one site. Action: site_read."""
        self._require_read(actor, "site_read")
        with self._lock:
            return dict(self._get_site_record(site_id))

    def list_sites(self, actor=None):
        """Return sites sorted by id. Action: site_read."""
        self._require_read(actor, "site_read")
        with self._lock:
            sites = sorted(self._sites.values(), key=lambda s: _id_num(s["id"]))
            return [dict(s) for s in sites]

    def _require_read(self, actor, action):
        """Reads: enforce only when a User-like actor is supplied."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                self._audit_denied(actor, action, None)
                raise

    def create_section(self, actor, site_id, name, slug, parent_id=None):
        """Create a section in a site. Action: section_write. Ids: sec-{n}.

        A parent section, when given, must belong to the same site.
        Section slugs are unique per site.
        """
        self._require(actor, "section_write")
        _validate_non_empty(name, "section name")
        _validate_slug(slug, "section slug")
        with self._lock:
            self._get_site_record(site_id)
            if parent_id is not None:
                parent = self._get_section_record(parent_id)
                if parent["site_id"] != site_id:
                    raise ValidationError(
                        "parent section %r does not belong to site %r" % (parent_id, site_id)
                    )
            for existing in self._sections.values():
                if existing["site_id"] == site_id and existing["slug"] == slug:
                    raise ValidationError(
                        "duplicate section slug %r in site %r" % (slug, site_id)
                    )
            section_id = self._next_id("sec")
            section = {
                "id": section_id, "site_id": site_id, "name": name,
                "slug": slug, "parent_id": parent_id,
                "created_by": actor_name(actor), "created_utc": _utc_now(),
            }
            self._sections[section_id] = section
            self._audit(actor, "section_create", section_id, details={"site_id": site_id})
            return dict(section)

    def list_sections(self, site_id, actor=None):
        """Return a site's sections sorted by id. Action: section_read."""
        self._require_read(actor, "section_read")
        with self._lock:
            self._get_site_record(site_id)
            sections = sorted(self._sections.values(), key=lambda s: _id_num(s["id"]))
            return [dict(s) for s in sections if s["site_id"] == site_id]

    def get_section(self, section_id, actor=None):
        """Return one section. Action: section_read."""
        self._require_read(actor, "section_read")
        with self._lock:
            return dict(self._get_section_record(section_id))

    # -- 2. content types ----------------------------------------------

    def create_type(self, actor, name, description=""):
        """Create a custom content type. Action: type_write. Ids: ct-{n}."""
        self._require(actor, "type_write")
        _validate_non_empty(name, "content type name")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise ValidationError("description must be a string")
        with self._lock:
            type_id = self._next_id("ct")
            ctype = {
                "id": type_id, "name": name, "description": description,
                "builtin": False, "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._types[type_id] = ctype
            self._audit(actor, "type_create", type_id, details={"name": name})
            return dict(ctype)

    def get_type(self, type_id, actor=None):
        """Return one content type. Action: type_read."""
        self._require_read(actor, "type_read")
        with self._lock:
            return dict(self._get_type_record(type_id))

    def list_types(self, actor=None):
        """Return content types: built-ins first, then custom by id. Action: type_read."""
        self._require_read(actor, "type_read")
        with self._lock:
            builtins = [self._types[tid] for tid, _ in BUILTIN_TYPES]
            customs = sorted(
                (t for t in self._types.values() if not t["builtin"]),
                key=lambda t: _id_num(t["id"]),
            )
            return [dict(t) for t in builtins + customs]

    # -- 3. content items & authoring -----------------------------------

    def create_item(self, actor, site_id, type_id, title, slug, body="",
                    section_id=None, metadata=None, tag_ids=None):
        """Create a draft content item. Action: item_create. Ids: ci-{n}.

        Mints revision 1 (rev-{n}) capturing the title/body/metadata
        snapshot. Item slugs are unique per site.
        """
        self._require(actor, "item_create")
        _validate_non_empty(title, "item title")
        _validate_slug(slug, "item slug")
        if body is None:
            body = ""
        if not isinstance(body, str):
            raise ValidationError("body must be a string")
        clean_metadata = _validate_metadata(metadata)
        with self._lock:
            self._get_site_record(site_id)
            self._get_type_record(type_id)
            if section_id is not None:
                section = self._get_section_record(section_id)
                if section["site_id"] != site_id:
                    raise ValidationError(
                        "section %r does not belong to site %r" % (section_id, site_id)
                    )
            clean_tags = self._validate_tag_ids(tag_ids)
            for existing in self._items.values():
                if existing["site_id"] == site_id and existing["slug"] == slug:
                    raise ValidationError(
                        "duplicate item slug %r in site %r" % (slug, site_id)
                    )
            item_id = self._next_id("ci")
            now = _utc_now()
            item = {
                "id": item_id, "site_id": site_id, "type_id": type_id,
                "section_id": section_id, "title": title, "slug": slug,
                "body": body, "metadata": clean_metadata, "tag_ids": clean_tags,
                "status": "draft", "author": actor_name(actor),
                "created_by": actor_name(actor),
                "created_utc": now, "updated_utc": now,
                "revision": 0, "latest_revision_id": None,
                "return_note": None,
            }
            self._items[item_id] = item
            self._mint_revision(item, actor)
            self._audit(actor, "item_create", item_id, details={"site_id": site_id, "slug": slug})
            return self._copy_item(item)

    def update_item(self, actor, item_id, title=None, body=None, metadata=None, tag_ids=None):
        """Edit an item, minting a new revision. Action: item_edit.

        Author-role actors may edit only their own items. Edits are
        allowed in draft (any permitted role, subject to ownership),
        and in in_review only for admin / publisher / editor.
        """
        self._require(actor, "item_edit", target=item_id)
        if title is not None:
            _validate_non_empty(title, "item title")
        if body is not None and not isinstance(body, str):
            raise ValidationError("body must be a string")
        clean_metadata = _validate_metadata(metadata) if metadata is not None else None
        with self._lock:
            item = self._get_item_record(item_id)
            self._check_author_owns(actor, item, "item_edit")
            if item["status"] == "in_review":
                if getattr(actor, "role", None) not in (None, "admin", "publisher", "editor") \
                        and hasattr(actor, "role"):
                    self._audit_denied(actor, "item_edit", item_id)
                    raise PermissionDenied(
                        "permission denied: only admin, publisher or editor may edit an in_review item"
                    )
                # Plain-string actors carry no role; the service layer enforces.
                if hasattr(actor, "role") and actor.role == "author":
                    self._audit_denied(actor, "item_edit", item_id)
                    raise PermissionDenied(
                        "permission denied: authors may not edit an in_review item"
                    )
            elif item["status"] != "draft":
                raise ValidationError(
                    "item %r cannot be edited while status is %r" % (item_id, item["status"])
                )
            clean_tags = self._validate_tag_ids(tag_ids) if tag_ids is not None else None
            if title is not None:
                item["title"] = title
            if body is not None:
                item["body"] = body
            if clean_metadata is not None:
                item["metadata"] = clean_metadata
            if clean_tags is not None:
                item["tag_ids"] = clean_tags
            item["updated_utc"] = _utc_now()
            self._mint_revision(item, actor)
            self._audit(actor, "item_update", item_id, details={"revision": item["revision"]})
            return self._copy_item(item)

    def get_item(self, item_id, actor=None, now=None):
        """Return one item with derived window fields. Action: item_read."""
        self._require_read(actor, "item_read")
        with self._lock:
            return self._copy_item(self._get_item_record(item_id), now=now)

    def list_items(self, site_id=None, status=None, actor=None, now=None):
        """Return items sorted by id, optionally filtered. Action: item_read."""
        self._require_read(actor, "item_read")
        if status is not None and status not in KNOWN_ITEM_STATUSES:
            raise ValidationError("status must be one of %s" % (", ".join(ITEM_STATUSES),))
        with self._lock:
            if site_id is not None:
                self._get_site_record(site_id)
            items = sorted(self._items.values(), key=lambda i: _id_num(i["id"]))
            return [
                self._copy_item(i, now=now) for i in items
                if (site_id is None or i["site_id"] == site_id)
                and (status is None or i["status"] == status)
            ]

    def list_revisions(self, item_id, actor=None):
        """Return an item's revisions in revision order. Action: item_read."""
        self._require_read(actor, "item_read")
        with self._lock:
            self._get_item_record(item_id)
            revs = [r for r in self._revisions.values() if r["item_id"] == item_id]
            revs.sort(key=lambda r: r["revision"])
            return [self._copy_revision(r) for r in revs]

    # -- 4. editorial lifecycle ------------------------------------------

    def submit_item(self, actor, item_id):
        """draft -> in_review. Action: item_submit (author: own only)."""
        self._require(actor, "item_submit", target=item_id)
        with self._lock:
            item = self._get_item_record(item_id)
            self._check_author_owns(actor, item, "item_submit")
            if item["status"] != "draft":
                raise ValidationError(
                    "item %r cannot be submitted from status %r" % (item_id, item["status"])
                )
            item["status"] = "in_review"
            item["updated_utc"] = _utc_now()
            self._audit(actor, "item_submit", item_id)
            return self._copy_item(item)

    def _check_approver_not_author(self, item, actor):
        """Separation of duties: approver/returner is never the author.

        This is the negative-control seam: patching this method to a
        no-op must make the suite fail.
        """
        if actor_name(actor) == item["author"]:
            raise PermissionDenied("approver may not be the item's author")

    def approve_item(self, actor, item_id):
        """in_review -> approved. Action: item_review."""
        self._require(actor, "item_review", target=item_id)
        with self._lock:
            item = self._get_item_record(item_id)
            if item["status"] != "in_review":
                raise ValidationError(
                    "item %r cannot be approved from status %r" % (item_id, item["status"])
                )
            try:
                self._check_approver_not_author(item, actor)
            except PermissionDenied:
                self._audit_denied(actor, "item_review", item_id)
                raise
            item["status"] = "approved"
            item["approved_by"] = actor_name(actor)
            item["updated_utc"] = _utc_now()
            self._audit(actor, "item_approve", item_id)
            return self._copy_item(item)

    def return_item(self, actor, item_id, note=""):
        """in_review -> draft, with an optional note. Action: item_review."""
        self._require(actor, "item_review", target=item_id)
        if note is None:
            note = ""
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            item = self._get_item_record(item_id)
            if item["status"] != "in_review":
                raise ValidationError(
                    "item %r cannot be returned from status %r" % (item_id, item["status"])
                )
            try:
                self._check_approver_not_author(item, actor)
            except PermissionDenied:
                self._audit_denied(actor, "item_review", item_id)
                raise
            item["status"] = "draft"
            item["return_note"] = note
            item["returned_by"] = actor_name(actor)
            item["updated_utc"] = _utc_now()
            self._audit(actor, "item_return", item_id, details={"note": note})
            return self._copy_item(item)

    # -- 5. publishing ------------------------------------------------------

    def publish_item(self, actor, item_id, publish_at=None, expire_at=None):
        """approved -> published; mints a publish record pub-{n}.

        Action: item_publish. ``publish_at`` / ``expire_at`` are
        ISO-8601 UTC strings; when both are given, ``expire_at`` must
        be after ``publish_at``.
        """
        self._require(actor, "item_publish", target=item_id)
        publish_dt = _parse_iso_datetime(publish_at, "publish_at") if publish_at is not None else None
        expire_dt = _parse_iso_datetime(expire_at, "expire_at") if expire_at is not None else None
        if publish_dt is not None and expire_dt is not None and expire_dt <= publish_dt:
            raise ValidationError("expire_at must be after publish_at")
        with self._lock:
            item = self._get_item_record(item_id)
            if item["status"] != "approved":
                raise ValidationError(
                    "item %r cannot be published from status %r" % (item_id, item["status"])
                )
            pub_id = self._next_id("pub")
            now = _utc_now()
            record = {
                "id": pub_id, "item_id": item_id,
                "published_by": actor_name(actor), "published_utc": now,
                "publish_at": publish_at, "expire_at": expire_at,
            }
            self._publishes[pub_id] = record
            item["status"] = "published"
            item["updated_utc"] = now
            self._audit(actor, "item_publish", item_id, details={"publish_id": pub_id})
            return self._copy_item(item, now=now)

    def archive_item(self, actor, item_id):
        """published -> archived. Action: item_archive."""
        self._require(actor, "item_archive", target=item_id)
        with self._lock:
            item = self._get_item_record(item_id)
            if item["status"] != "published":
                raise ValidationError(
                    "item %r cannot be archived from status %r" % (item_id, item["status"])
                )
            item["status"] = "archived"
            item["archived_by"] = actor_name(actor)
            item["updated_utc"] = _utc_now()
            self._audit(actor, "item_archive", item_id)
            return self._copy_item(item)

    def window_state(self, item, publish_record, now=None):
        """Store-method wrapper over the module-level window_state()."""
        return window_state(item, publish_record, now=now)

    def get_publish_record(self, publish_id, actor=None):
        """Return one publish record. Action: item_read."""
        self._require_read(actor, "item_read")
        with self._lock:
            rec = self._publishes.get(publish_id)
            if rec is None:
                raise NotFoundError("publish record not found: %r" % (publish_id,))
            return dict(rec)

    def list_publish_records(self, item_id=None, actor=None):
        """Return publish records sorted by id. Action: item_read."""
        self._require_read(actor, "item_read")
        with self._lock:
            if item_id is not None:
                self._get_item_record(item_id)
            records = sorted(self._publishes.values(), key=lambda p: _id_num(p["id"]))
            return [dict(p) for p in records if item_id is None or p["item_id"] == item_id]

    # -- 6. assets ------------------------------------------------------------

    def register_asset(self, actor, site_id, filename, kind, byte_size,
                       mime_type="", content_sha256=None, data=None):
        """Register an asset (doubles as its ingestion record).

        Action: asset_write. Ids: asset-{n}. Only the checksum and
        metadata are stored -- never the bytes. When ``data`` (bytes)
        is supplied its SHA-256 is computed, and must match
        ``content_sha256`` when both are given.
        """
        self._require(actor, "asset_write")
        _validate_non_empty(filename, "filename")
        if kind not in KNOWN_ASSET_KINDS:
            raise ValidationError("kind must be one of %s" % (", ".join(ASSET_KINDS),))
        if not _is_int(byte_size) or byte_size < 0:
            raise ValidationError("byte_size must be an integer >= 0")
        if mime_type is None:
            mime_type = ""
        if not isinstance(mime_type, str):
            raise ValidationError("mime_type must be a string")
        computed = None
        if data is not None:
            if not isinstance(data, (bytes, bytearray)):
                raise ValidationError("data must be bytes")
            computed = hashlib.sha256(bytes(data)).hexdigest()
        if content_sha256 is not None:
            if not isinstance(content_sha256, str) or not _SHA256_RE.match(content_sha256):
                raise ValidationError("content_sha256 must be a 64-character hex SHA-256")
            content_sha256 = content_sha256.lower()
        if computed is not None and content_sha256 is not None and computed != content_sha256:
            raise ValidationError("content_sha256 does not match the SHA-256 of data")
        checksum = computed if computed is not None else content_sha256
        with self._lock:
            self._get_site_record(site_id)
            asset_id = self._next_id("asset")
            asset = {
                "id": asset_id, "site_id": site_id, "filename": filename,
                "kind": kind, "byte_size": byte_size, "mime_type": mime_type,
                "content_sha256": checksum,
                "created_by": actor_name(actor), "created_utc": _utc_now(),
            }
            self._assets[asset_id] = asset
            self._audit(actor, "asset_register", asset_id,
                        details={"site_id": site_id, "kind": kind})
            return dict(asset)

    def get_asset(self, asset_id, actor=None):
        """Return one asset. Action: asset_read."""
        self._require_read(actor, "asset_read")
        with self._lock:
            return dict(self._get_asset_record(asset_id))

    def list_assets(self, site_id=None, actor=None):
        """Return assets sorted by id. Action: asset_read."""
        self._require_read(actor, "asset_read")
        with self._lock:
            if site_id is not None:
                self._get_site_record(site_id)
            assets = sorted(self._assets.values(), key=lambda a: _id_num(a["id"]))
            return [dict(a) for a in assets if site_id is None or a["site_id"] == site_id]

    # -- 7. tags ---------------------------------------------------------------

    def create_tag(self, actor, name, slug):
        """Create a tag. Action: tag_write. Ids: tag-{n}. Slugs are global."""
        self._require(actor, "tag_write")
        _validate_non_empty(name, "tag name")
        _validate_slug(slug, "tag slug")
        with self._lock:
            for existing in self._tags.values():
                if existing["slug"] == slug:
                    raise ValidationError("duplicate tag slug: %r" % (slug,))
            tag_id = self._next_id("tag")
            tag = {
                "id": tag_id, "name": name, "slug": slug,
                "created_by": actor_name(actor), "created_utc": _utc_now(),
            }
            self._tags[tag_id] = tag
            self._audit(actor, "tag_create", tag_id, details={"slug": slug})
            return dict(tag)

    def get_tag(self, tag_id, actor=None):
        """Return one tag. Action: tag_read."""
        self._require_read(actor, "tag_read")
        with self._lock:
            return dict(self._get_tag_record(tag_id))

    def list_tags(self, actor=None):
        """Return tags sorted by id. Action: tag_read."""
        self._require_read(actor, "tag_read")
        with self._lock:
            tags = sorted(self._tags.values(), key=lambda t: _id_num(t["id"]))
            return [dict(t) for t in tags]

    # -- 8. search ---------------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search. Action: search.

        Over items (title, slug, body, metadata values), assets
        (filename, kind), sites (name, slug) and tags (name, slug).
        Returns {"items": [...], "assets": [...], "sites": [...],
        "tags": [...]}. Audited as action "search".
        """
        self._require_read(actor, "search")
        if not isinstance(query, str):
            raise ValidationError("query must be a string")
        stripped = query.strip()
        needle = stripped.lower()
        with self._lock:
            if not stripped:
                result = {"items": [], "assets": [], "sites": [], "tags": []}
            else:
                items = []
                for item in self._items.values():
                    haystacks = [item["title"].lower(), item["slug"].lower(), item["body"].lower()]
                    haystacks.extend(str(v).lower() for v in item["metadata"].values())
                    if any(needle in h for h in haystacks):
                        items.append(item)
                items.sort(key=lambda i: _id_num(i["id"]))
                assets = []
                for asset in self._assets.values():
                    if needle in asset["filename"].lower() or needle in asset["kind"].lower():
                        assets.append(asset)
                assets.sort(key=lambda a: _id_num(a["id"]))
                sites = []
                for site in self._sites.values():
                    if needle in site["name"].lower() or needle in site["slug"].lower():
                        sites.append(site)
                sites.sort(key=lambda s: _id_num(s["id"]))
                tags = []
                for tag in self._tags.values():
                    if needle in tag["name"].lower() or needle in tag["slug"].lower():
                        tags.append(tag)
                tags.sort(key=lambda t: _id_num(t["id"]))
                result = {
                    "items": [self._copy_item(i) for i in items],
                    "assets": [dict(a) for a in assets],
                    "sites": [dict(s) for s in sites],
                    "tags": [dict(t) for t in tags],
                }
            self._audit(actor, "search", query, details={"query": query})
            return result

    # -- 9. reporting --------------------------------------------------------------

    def registry_report(self, actor=None):
        """Computed registry report, deterministic from registry state.

        Action: report_read.
        """
        self._require_read(actor, "report_read")
        with self._lock:
            items_by_status = {status: 0 for status in ITEM_STATUSES}
            items_by_site = {}
            items_by_type = {}
            for item in self._items.values():
                items_by_status[item["status"]] += 1
                items_by_site[item["site_id"]] = items_by_site.get(item["site_id"], 0) + 1
                items_by_type[item["type_id"]] = items_by_type.get(item["type_id"], 0) + 1
            assets_by_kind = {kind: 0 for kind in ASSET_KINDS}
            for asset in self._assets.values():
                assets_by_kind[asset["kind"]] += 1
            publish_count = len(self._publishes)
            totals = {
                "sites": len(self._sites),
                "sections": len(self._sections),
                "types": len(self._types),
                "items": len(self._items),
                "revisions": len(self._revisions),
                "publish_records": publish_count,
                "assets": len(self._assets),
                "tags": len(self._tags),
            }
            return {
                "items_by_status": items_by_status,
                "items_by_site": items_by_site,
                "items_by_type": items_by_type,
                "publish_records": publish_count,
                "assets_by_kind": assets_by_kind,
                "totals": totals,
                "total_sites": totals["sites"],
                "total_items": totals["items"],
                "total_assets": totals["assets"],
                "total_tags": totals["tags"],
            }
