"""Final GAPS batch extensions for the Learning Management untiered set.

Clean-room, standard-library-only extensions for the 6 open entries
of Untiered Set 25 (see ``BATCH.md`` in the group directory for the
per-entry disposition). This module is a wrapper around
:class:`LmsStore`; every core module is untouched.

Tier discipline: this set is untiered — the member fork's FedRAMP
impact level is "Unknown" and its CMMC tier is null. Nothing in
this surface asserts a baseline, assigns a tier, or draws an
equivalence; no record here carries a tier-shaped key at all,
pinned by a recursive key scan in the tests.

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records plus deterministic derivations over
the group's OWN records.

- The virtual classroom is classroom-session administration
  records bound to core courses/events, with outcome records
  holding caller-reported labels verbatim. No classroom is
  delivered: ``delivered_here`` is False on every session record.
- Real-time collaboration and session recording are re-judged to
  labeled reference records (see BATCH.md): their substance is
  synchronous media transport and media capture, which have no
  records decomposition beyond session metadata. The records
  carry ``reference_stub: True`` and ``reference_transport: True``;
  no content is held and no recording is captured here.
- The authoring workspace ships as the house stub form: draft
  records with append-only revisions, ``reference_stub: True``.
- The media repository is a metadata registry: items are named by
  opaque reference with an optional caller-supplied SHA-256
  checksum; content is never held (``content_held: False``).
- Assignments, evaluations and "grading" are records only, in
  the entry's own bounded form ("the build still computes no
  score"): evaluation outcomes are caller-supplied text recorded
  verbatim, ``computed_here: False``, and no key anywhere in this
  surface is a score or grade key — pinned by the same recursive
  scan the core uses, extended to grade-shaped keys.
- User administration is administration ACTION records over the
  core learner registry: the learner's current administrative
  state is DERIVED at read from the latest recorded action, never
  stored. This surface is not an identity provider (PLATFORM-
  LAYER.md decision 1): records carry ``identity_provider:
  False``, no credential-shaped parameter exists anywhere, and
  no core learner record is ever modified by an admin action.

Doctrines carried from the core: opaque ``*_ref`` strings only;
derived-never-stored for every computed value (session outcome
labels, media share counts, coursework counts, current admin
state); append-only audit on the core store's log with ``ext_``-
prefixed actions for every successful mutation; RBAC via
:mod:`lms.access` with the core's existing actions, enforced
before any state change or id allocation, so a failed operation
consumes no id and changes nothing; learner scope mirrors the
store's — a learner-role actor may only read records whose
``learner_ref`` is their own name (for participant lists: only
sessions they participate in).
"""

import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

MEDIA_KINDS = ("video", "audio", "document", "image", "slides", "other")
ADMIN_ACTION_LABELS = ("provisioned", "suspended", "reinstated", "deprovisioned")
NO_RECORDED_ACTION = "no_recorded_action"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _ref_list(value, what):
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValidationError("%s must be a list of opaque references" % (what,))
    items = list(value)
    for item in items:
        _non_empty(item, what)
    return items


def _validate_sha256(value, what="sha256"):
    if value is None:
        return None
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value.lower())):
        raise ValidationError("%s must be a 64-character hex SHA-256 digest"
                              % (what,))
    return value.lower()


def _non_negative_int(value, what):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % (what,))
    return value


def _validate_datetime(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO-8601 datetime: %r"
                              % (what, value)) from exc


def _validate_date(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO date string (YYYY-MM-DD)"
                              % (what,))
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValidationError("%s is not a valid ISO date: %r" % (what, value)) from exc


class LmsExtensions:
    """Extension surface wrapping one :class:`LmsStore`."""

    def __init__(self, store):
        self.store = store
        self._classroom_sessions = {}
        self._classroom_outcomes = {}
        self._collaboration_records = {}
        self._recording_records = {}
        self._authoring_drafts = {}
        self._media_items = {}
        self._media_shares = {}
        self._coursework_assignments = {}
        self._submissions = {}
        self._evaluations = {}
        self._user_admin_actions = {}
        self._counters = {
            "vcs": 0, "vco": 0, "col": 0, "rcd": 0, "dft": 0, "med": 0,
            "shr": 0, "asn": 0, "sub": 0, "evl": 0, "uad": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    @staticmethod
    def _require_actor(actor, action):
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            require(actor, action)

    @staticmethod
    def _scope_check(actor, learner_ref):
        if (actor is not None and getattr(actor, "role", None) == "learner"
                and getattr(actor, "name", None) != learner_ref):
            raise PermissionDenied(
                "permission denied: learner %r may not access records of "
                "learner %r" % (getattr(actor, "name", None), learner_ref)
            )

    @staticmethod
    def _is_learner(actor):
        return actor is not None and getattr(actor, "role", None) == "learner"

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _learner_exists(self, learner_ref):
        learners = self.store.list_learners()
        return learner_ref in {learner["ref"] for learner in learners}

    def _require_learner(self, learner_ref):
        if not self._learner_exists(learner_ref):
            raise NotFoundError("learner not found: %r" % (learner_ref,))

    # -- Virtual classroom delivery runtime (records form) --------------
    # Classroom sessions are administration records: a schedule bound
    # to a core course (and optionally one of its core events), with
    # participant learner references. Outcomes are caller-reported
    # labels recorded verbatim. No audio/video is delivered here.

    def create_classroom_session(self, course_id, title, starts_at, actor,
                                 event_id=None, ends_at=None,
                                 participant_refs=None):
        """Record a virtual classroom session. Action: registration_write."""
        self._require_actor(actor, "registration_write")
        _non_empty(title, "session title")
        start_dt = _validate_datetime(starts_at, "starts_at")
        end_dt = None
        if ends_at is not None:
            end_dt = _validate_datetime(ends_at, "ends_at")
            if (end_dt.tzinfo is None) != (start_dt.tzinfo is None):
                raise ValidationError(
                    "starts_at and ends_at must both carry, or both omit, "
                    "a UTC offset")
            if end_dt < start_dt:
                raise ValidationError("ends_at must not be before starts_at")
        participant_refs = _ref_list(participant_refs, "participant_refs")
        with self._lock:
            self.store.get_course(course_id, actor=None)
            if event_id is not None:
                event = self.store.get_event(event_id, actor=None)
                if (event["course_id"] is not None
                        and event["course_id"] != course_id):
                    raise ValidationError(
                        "event %r does not belong to course %r"
                        % (event_id, course_id))
            for ref in participant_refs:
                self._require_learner(ref)
            session_id = self._next_id("vcs")
            record = {
                "id": session_id,
                "course_id": course_id,
                "event_id": event_id,
                "title": title,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "participant_refs": list(participant_refs),
                "delivered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._classroom_sessions[session_id] = record
            self._audit(actor, "ext_classroom_session_create", session_id,
                        details={"course_id": course_id, "event_id": event_id,
                                 "title": title})
            return self._copy_session(record)

    @staticmethod
    def _copy_session(record):
        copied = dict(record)
        copied["participant_refs"] = list(record["participant_refs"])
        return copied

    def record_classroom_outcome(self, session_id, outcome_label, actor,
                                 note=""):
        """Record a caller-reported outcome for a session.

        Action: registration_write. The label is stored verbatim;
        ``outcome_basis`` records that it is caller-reported.
        """
        self._require_actor(actor, "registration_write")
        _non_empty(outcome_label, "outcome_label")
        _string(note, "note")
        with self._lock:
            self._get(self._classroom_sessions, session_id, "classroom session")
            outcome_id = self._next_id("vco")
            record = {
                "id": outcome_id,
                "session_id": session_id,
                "outcome_label": outcome_label,
                "outcome_basis": "caller_reported",
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._classroom_outcomes[outcome_id] = record
            self._audit(actor, "ext_classroom_outcome_record", outcome_id,
                        details={"session_id": session_id,
                                 "outcome_label": outcome_label})
            return dict(record)

    def _session_view(self, record):
        view = self._copy_session(record)
        outcomes = [o for o in self._classroom_outcomes.values()
                    if o["session_id"] == record["id"]]
        view["outcome_count"] = len(outcomes)
        view["latest_outcome_label"] = (
            outcomes[-1]["outcome_label"] if outcomes else None)
        return view

    def _session_visible(self, actor, record):
        if self._is_learner(actor):
            return getattr(actor, "name", None) in record["participant_refs"]
        return True

    def get_classroom_session(self, session_id, actor=None):
        """Return one session view. Action: registration_read."""
        if actor is not None:
            self._require_actor(actor, "registration_read")
        with self._lock:
            record = self._get(self._classroom_sessions, session_id,
                               "classroom session")
            if not self._session_visible(actor, record):
                raise PermissionDenied(
                    "permission denied: learner %r is not a participant of "
                    "session %r" % (getattr(actor, "name", None), session_id))
            return self._session_view(record)

    def list_classroom_sessions(self, actor=None, course_id=None):
        """Return session views. Action: registration_read."""
        if actor is not None:
            self._require_actor(actor, "registration_read")
        with self._lock:
            records = list(self._classroom_sessions.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            records = [r for r in records if self._session_visible(actor, r)]
            return [self._session_view(r) for r in records]

    def list_classroom_outcomes(self, actor=None, session_id=None):
        """Return classroom outcome records. Action: registration_read."""
        if actor is not None:
            self._require_actor(actor, "registration_read")
        with self._lock:
            records = list(self._classroom_outcomes.values())
            if session_id is not None:
                records = [r for r in records if r["session_id"] == session_id]
            if self._is_learner(actor):
                name = getattr(actor, "name", None)
                visible = {
                    s["id"] for s in self._classroom_sessions.values()
                    if name in s["participant_refs"]}
                records = [r for r in records if r["session_id"] in visible]
            return [dict(r) for r in records]

    def classroom_summary(self, actor):
        """Deterministic counts over the classroom records.

        Action: report_read. Counts of records only — derived at
        read, labeled with its method.
        """
        self._require_actor(actor, "report_read")
        with self._lock:
            with_outcomes = {o["session_id"]
                             for o in self._classroom_outcomes.values()}
            return {
                "method": "deterministic_counts",
                "classroom_sessions": len(self._classroom_sessions),
                "classroom_outcomes": len(self._classroom_outcomes),
                "sessions_with_outcomes": len(with_outcomes),
            }

    # -- Real-time collaboration & session recording (reference form) ---
    # Re-judged from the drafted build-extension to a labeled
    # reference implementation (see BATCH.md): the service's
    # substance is synchronous media transport and media capture.
    # These records are session/recording METADATA only — shared
    # content is named by opaque reference, recordings by opaque
    # reference plus an optional caller-supplied checksum.

    def create_collaboration_record(self, actor, course_id=None,
                                    session_id=None, participant_refs=None,
                                    shared_content_refs=None):
        """Record a collaboration session reference. Action: registration_write."""
        self._require_actor(actor, "registration_write")
        participant_refs = _ref_list(participant_refs, "participant_refs")
        shared_content_refs = _ref_list(shared_content_refs,
                                        "shared_content_refs")
        with self._lock:
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            if session_id is not None:
                self._get(self._classroom_sessions, session_id,
                          "classroom session")
            for ref in participant_refs:
                self._require_learner(ref)
            record_id = self._next_id("col")
            record = {
                "id": record_id,
                "course_id": course_id,
                "session_id": session_id,
                "participant_refs": list(participant_refs),
                "shared_content_refs": list(shared_content_refs),
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "collaborated_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._collaboration_records[record_id] = record
            self._audit(actor, "ext_collaboration_record", record_id,
                        details={"course_id": course_id,
                                 "session_id": session_id,
                                 "reference_stub": True})
            return self._copy_collaboration(record)

    @staticmethod
    def _copy_collaboration(record):
        copied = dict(record)
        copied["participant_refs"] = list(record["participant_refs"])
        copied["shared_content_refs"] = list(record["shared_content_refs"])
        return copied

    def get_collaboration_record(self, record_id, actor=None):
        """Return one collaboration reference record. Action: registration_read."""
        if actor is not None:
            self._require_actor(actor, "registration_read")
        with self._lock:
            record = self._get(self._collaboration_records, record_id,
                               "collaboration record")
            if (self._is_learner(actor)
                    and getattr(actor, "name", None)
                    not in record["participant_refs"]):
                raise PermissionDenied(
                    "permission denied: learner %r is not a participant of "
                    "collaboration record %r"
                    % (getattr(actor, "name", None), record_id))
            return self._copy_collaboration(record)

    def list_collaboration_records(self, actor=None, course_id=None):
        """Return collaboration reference records. Action: registration_read."""
        if actor is not None:
            self._require_actor(actor, "registration_read")
        with self._lock:
            records = list(self._collaboration_records.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            if self._is_learner(actor):
                name = getattr(actor, "name", None)
                records = [r for r in records if name in r["participant_refs"]]
            return [self._copy_collaboration(r) for r in records]

    def record_recording_record(self, collaboration_id, media_ref, actor,
                                sha256=None, duration_seconds=None, note=""):
        """Record a session-recording reference. Action: registration_write.

        The recording itself was captured elsewhere, or not at all:
        this record holds metadata only — an opaque media reference,
        an optional caller-supplied checksum, and a caller-reported
        duration carried as reported data.
        """
        self._require_actor(actor, "registration_write")
        _non_empty(media_ref, "media_ref")
        sha256 = _validate_sha256(sha256)
        duration_seconds = _non_negative_int(duration_seconds,
                                             "duration_seconds")
        _string(note, "note")
        with self._lock:
            self._get(self._collaboration_records, collaboration_id,
                      "collaboration record")
            record_id = self._next_id("rcd")
            record = {
                "id": record_id,
                "collaboration_id": collaboration_id,
                "media_ref": media_ref,
                "sha256": sha256,
                "duration_seconds": duration_seconds,
                "note": note,
                "reference_stub": True,
                "reference_transport": True,
                "state": "recorded_reference_only",
                "content_held": False,
                "recorded_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._recording_records[record_id] = record
            self._audit(actor, "ext_recording_record", record_id,
                        details={"collaboration_id": collaboration_id,
                                 "media_ref": media_ref,
                                 "reference_stub": True})
            return dict(record)

    def list_recording_records(self, actor=None, collaboration_id=None):
        """Return recording reference records. Action: registration_read."""
        if actor is not None:
            self._require_actor(actor, "registration_read")
        with self._lock:
            records = list(self._recording_records.values())
            if collaboration_id is not None:
                records = [r for r in records
                           if r["collaboration_id"] == collaboration_id]
            if self._is_learner(actor):
                name = getattr(actor, "name", None)
                visible = {
                    c["id"] for c in self._collaboration_records.values()
                    if name in c["participant_refs"]}
                records = [r for r in records
                           if r["collaboration_id"] in visible]
            return [dict(r) for r in records]

    # -- Course material authoring workspace (reference form) -----------
    # Stub-engine per triage: draft records with append-only
    # revisions. The workspace itself — building and editing course
    # materials — executes outside this substrate; the core records
    # a draft names are never changed by this surface (pinned).

    def create_authoring_draft(self, title, actor, course_id=None,
                               content_id=None, lesson_plan_id=None,
                               body=""):
        """Record an authoring draft (version 1). Action: catalog_write."""
        self._require_actor(actor, "catalog_write")
        _non_empty(title, "draft title")
        _string(body, "body")
        with self._lock:
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            if content_id is not None:
                item = self.store.get_content_item(content_id, actor=None)
                if (item["course_id"] is not None and course_id is not None
                        and item["course_id"] != course_id):
                    raise ValidationError(
                        "content item %r does not belong to course %r"
                        % (content_id, course_id))
            if lesson_plan_id is not None:
                plan = self.store.get_lesson_plan(lesson_plan_id, actor=None)
                if course_id is not None and plan["course_id"] != course_id:
                    raise ValidationError(
                        "lesson plan %r does not belong to course %r"
                        % (lesson_plan_id, course_id))
            draft_id = self._next_id("dft")
            record = {
                "id": draft_id,
                "title": title,
                "course_id": course_id,
                "content_id": content_id,
                "lesson_plan_id": lesson_plan_id,
                "revisions": [{"body": body, "recorded_by": actor_name(actor),
                               "recorded_utc": _utc_now()}],
                "reference_stub": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._authoring_drafts[draft_id] = record
            self._audit(actor, "ext_authoring_draft_create", draft_id,
                        details={"title": title, "reference_stub": True})
            return self._draft_view(record)

    @staticmethod
    def _draft_view(record):
        return {
            "id": record["id"],
            "title": record["title"],
            "course_id": record["course_id"],
            "content_id": record["content_id"],
            "lesson_plan_id": record["lesson_plan_id"],
            "body": record["revisions"][-1]["body"],
            "version_count": len(record["revisions"]),
            "reference_stub": True,
            "state": "recorded_reference_only",
            "created_by": record["created_by"],
            "created_utc": record["created_utc"],
        }

    def revise_authoring_draft(self, draft_id, body, actor):
        """Append a draft revision. Action: catalog_write. Append-only."""
        self._require_actor(actor, "catalog_write")
        _string(body, "body")
        with self._lock:
            record = self._get(self._authoring_drafts, draft_id,
                               "authoring draft")
            record["revisions"].append({
                "body": body, "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now()})
            self._audit(actor, "ext_authoring_draft_revise", draft_id,
                        details={"version": len(record["revisions"])})
            return self._draft_view(record)

    def get_authoring_draft(self, draft_id, actor=None):
        """Return one draft view. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            return self._draft_view(
                self._get(self._authoring_drafts, draft_id, "authoring draft"))

    def list_authoring_drafts(self, actor=None, course_id=None):
        """Return draft views. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._authoring_drafts.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._draft_view(r) for r in records]

    # -- Media & shared-materials repository (records form) -------------
    # A metadata registry over the repository the fork's description
    # asserts: items are named by opaque reference with optional
    # caller-supplied checksum and reported size. Content bytes are
    # never accepted, stored, or served here.

    def create_media_item(self, title, media_ref, kind, actor, course_id=None,
                          sha256=None, size_bytes=None):
        """Register a media item's metadata. Action: catalog_write."""
        self._require_actor(actor, "catalog_write")
        _non_empty(title, "media title")
        _non_empty(media_ref, "media_ref")
        if kind not in MEDIA_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(MEDIA_KINDS),))
        sha256 = _validate_sha256(sha256)
        size_bytes = _non_negative_int(size_bytes, "size_bytes")
        with self._lock:
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            item_id = self._next_id("med")
            record = {
                "id": item_id,
                "title": title,
                "media_ref": media_ref,
                "kind": kind,
                "course_id": course_id,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "content_held": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._media_items[item_id] = record
            self._audit(actor, "ext_media_item_create", item_id,
                        details={"title": title, "kind": kind,
                                 "media_ref": media_ref})
            return self._media_view(record, actor=None)

    def _media_view(self, record, actor):
        view = dict(record)
        shares = [s for s in self._media_shares.values()
                  if s["media_id"] == record["id"]]
        view["share_count"] = len(shares)
        learner_refs = [s["learner_ref"] for s in shares
                        if s["learner_ref"] is not None]
        if self._is_learner(actor):
            name = getattr(actor, "name", None)
            learner_refs = [ref for ref in learner_refs if ref == name]
        view["shared_learner_refs"] = learner_refs
        view["shared_course_ids"] = [s["course_id"] for s in shares
                                     if s["course_id"] is not None]
        return view

    def get_media_item(self, item_id, actor=None):
        """Return one media item view. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            record = self._get(self._media_items, item_id, "media item")
            return self._media_view(record, actor)

    def list_media_items(self, actor=None, course_id=None):
        """Return media item views. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._media_items.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._media_view(r, actor) for r in records]

    def record_media_share(self, media_id, actor, learner_ref=None,
                           course_id=None):
        """Record a share of a media item. Action: catalog_write.

        Exactly one target: a learner reference or a course, each of
        which must resolve. The share is a record; nothing is
        distributed by this call.
        """
        self._require_actor(actor, "catalog_write")
        if (learner_ref is None) == (course_id is None):
            raise ValidationError(
                "exactly one of learner_ref / course_id must be given")
        with self._lock:
            self._get(self._media_items, media_id, "media item")
            if learner_ref is not None:
                self._require_learner(learner_ref)
            if course_id is not None:
                self.store.get_course(course_id, actor=None)
            share_id = self._next_id("shr")
            record = {
                "id": share_id,
                "media_id": media_id,
                "learner_ref": learner_ref,
                "course_id": course_id,
                "state": "recorded",
                "distributed_here": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._media_shares[share_id] = record
            self._audit(actor, "ext_media_share_record", share_id,
                        details={"media_id": media_id,
                                 "learner_ref": learner_ref,
                                 "course_id": course_id})
            return dict(record)

    def list_media_shares(self, actor=None, media_id=None):
        """Return media share records. Action: catalog_read."""
        if actor is not None:
            self._require_actor(actor, "catalog_read")
        with self._lock:
            records = list(self._media_shares.values())
            if media_id is not None:
                records = [r for r in records if r["media_id"] == media_id]
            if self._is_learner(actor):
                name = getattr(actor, "name", None)
                records = [r for r in records if r["learner_ref"] == name]
            return [dict(r) for r in records]

    # -- Assignments, evaluations & grading (records form) --------------
    # The fork asserts "assignments, evaluations, and grading" in
    # its own words; the entry's own text bounds the build: "the
    # build still computes no score". So: assignment records bound
    # to core courses, submission records naming the submitted work
    # by opaque reference, and evaluation records holding the
    # outcome as caller-supplied TEXT recorded verbatim — never
    # parsed, never numeric, never computed here. Separation of
    # duties mirrors the core SF-182 rule: whoever recorded a
    # submission may not record its evaluation.

    def create_coursework_assignment(self, course_id, title, actor,
                                     instructions_ref=None, due_date=None):
        """Record a coursework assignment. Action: progress_write.

        The stored record carries no status and no outcome field.
        """
        self._require_actor(actor, "progress_write")
        _non_empty(title, "assignment title")
        if instructions_ref is not None:
            _non_empty(instructions_ref, "instructions_ref")
        if due_date is not None:
            _validate_date(due_date, "due_date")
        with self._lock:
            self.store.get_course(course_id, actor=None)
            assignment_id = self._next_id("asn")
            record = {
                "id": assignment_id,
                "course_id": course_id,
                "title": title,
                "instructions_ref": instructions_ref,
                "due_date": due_date,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._coursework_assignments[assignment_id] = record
            self._audit(actor, "ext_coursework_assignment_create",
                        assignment_id,
                        details={"course_id": course_id, "title": title})
            return self._assignment_view(record)

    def _assignment_view(self, record):
        view = dict(record)
        submissions = [s for s in self._submissions.values()
                       if s["assignment_id"] == record["id"]]
        submission_ids = {s["id"] for s in submissions}
        view["submission_count"] = len(submissions)
        view["evaluation_count"] = sum(
            1 for e in self._evaluations.values()
            if e["submission_id"] in submission_ids)
        return view

    def get_coursework_assignment(self, assignment_id, actor=None):
        """Return one assignment view. Action: progress_read."""
        if actor is not None:
            self._require_actor(actor, "progress_read")
        with self._lock:
            return self._assignment_view(self._get(
                self._coursework_assignments, assignment_id,
                "coursework assignment"))

    def list_coursework_assignments(self, actor=None, course_id=None):
        """Return assignment views. Action: progress_read."""
        if actor is not None:
            self._require_actor(actor, "progress_read")
        with self._lock:
            records = list(self._coursework_assignments.values())
            if course_id is not None:
                records = [r for r in records if r["course_id"] == course_id]
            return [self._assignment_view(r) for r in records]

    def record_submission(self, assignment_id, learner_ref, submission_ref,
                          actor, sha256=None):
        """Record a submission. Action: progress_write.

        The submitted work is named by opaque reference with an
        optional caller-supplied checksum; its content is never
        held here.
        """
        self._require_actor(actor, "progress_write")
        _non_empty(learner_ref, "learner_ref")
        _non_empty(submission_ref, "submission_ref")
        sha256 = _validate_sha256(sha256)
        with self._lock:
            self._get(self._coursework_assignments, assignment_id,
                      "coursework assignment")
            self._require_learner(learner_ref)
            submission_id = self._next_id("sub")
            record = {
                "id": submission_id,
                "assignment_id": assignment_id,
                "learner_ref": learner_ref,
                "submission_ref": submission_ref,
                "sha256": sha256,
                "content_held": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._submissions[submission_id] = record
            self._audit(actor, "ext_submission_record", submission_id,
                        details={"assignment_id": assignment_id,
                                 "learner_ref": learner_ref})
            return dict(record)

    def get_submission(self, submission_id, actor=None):
        """Return one submission record. Action: progress_read."""
        if actor is not None:
            self._require_actor(actor, "progress_read")
        with self._lock:
            record = self._get(self._submissions, submission_id, "submission")
            self._scope_check(actor, record["learner_ref"])
            return dict(record)

    def list_submissions(self, actor=None, assignment_id=None,
                         learner_ref=None):
        """Return submission records. Action: progress_read."""
        if actor is not None:
            self._require_actor(actor, "progress_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._submissions.values())
            if assignment_id is not None:
                records = [r for r in records
                           if r["assignment_id"] == assignment_id]
            if learner_ref is not None:
                records = [r for r in records
                           if r["learner_ref"] == learner_ref]
            if self._is_learner(actor):
                name = getattr(actor, "name", None)
                records = [r for r in records if r["learner_ref"] == name]
            return [dict(r) for r in records]

    def record_evaluation(self, submission_id, outcome_text, actor, note=""):
        """Record an evaluation outcome. Action: progress_write.

        ``outcome_text`` is the evaluator's outcome as caller-
        supplied text, recorded verbatim and never parsed or
        converted; ``computed_here`` is False on the record. One
        evaluation per submission. Separation of duties: the actor
        who recorded the submission may not record its evaluation.
        """
        self._require_actor(actor, "progress_write")
        _non_empty(outcome_text, "outcome_text")
        _string(note, "note")
        with self._lock:
            submission = self._get(self._submissions, submission_id,
                                   "submission")
            if actor_name(actor) == submission["recorded_by"]:
                raise PermissionDenied(
                    "permission denied: the recorder of a submission may "
                    "not record its evaluation")
            for existing in self._evaluations.values():
                if existing["submission_id"] == submission_id:
                    raise ValidationError(
                        "submission %r already has an evaluation"
                        % (submission_id,))
            evaluation_id = self._next_id("evl")
            record = {
                "id": evaluation_id,
                "submission_id": submission_id,
                "outcome_text": outcome_text,
                "outcome_basis": "caller_reported",
                "computed_here": False,
                "note": note,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._evaluations[evaluation_id] = record
            self._audit(actor, "ext_evaluation_record", evaluation_id,
                        details={"submission_id": submission_id})
            return dict(record)

    def list_evaluations(self, actor=None, submission_id=None):
        """Return evaluation records. Action: progress_read."""
        if actor is not None:
            self._require_actor(actor, "progress_read")
        with self._lock:
            records = list(self._evaluations.values())
            if submission_id is not None:
                records = [r for r in records
                           if r["submission_id"] == submission_id]
            if self._is_learner(actor):
                name = getattr(actor, "name", None)
                own = {s["id"] for s in self._submissions.values()
                       if s["learner_ref"] == name}
                records = [r for r in records if r["submission_id"] in own]
            return [dict(r) for r in records]

    def coursework_summary(self, actor):
        """Deterministic counts over the coursework records.

        Action: report_read. Counts of records only; no outcome is
        aggregated and no per-learner value is computed.
        """
        self._require_actor(actor, "report_read")
        with self._lock:
            return {
                "method": "deterministic_counts",
                "coursework_assignments": len(self._coursework_assignments),
                "submissions": len(self._submissions),
                "evaluations": len(self._evaluations),
            }

    # -- User administration service (records form) ---------------------
    # Administration ACTION records over the core learner registry.
    # The union spec registers this as the product's own user
    # management, distinct from the build's RBAC hooks and from the
    # IdP gap: this surface administers THIS substrate's registry
    # records, holds no credential, performs no authentication, and
    # never modifies a core learner record (pinned). The learner's
    # current administrative state is derived at read from the
    # latest recorded action — the records are the state.

    def record_user_admin_action(self, learner_ref, action_label, actor,
                                 note=""):
        """Record a user administration action. Action: learner_write."""
        self._require_actor(actor, "learner_write")
        _non_empty(learner_ref, "learner_ref")
        if action_label not in ADMIN_ACTION_LABELS:
            raise ValidationError(
                "action_label must be one of %s"
                % (", ".join(ADMIN_ACTION_LABELS),))
        _string(note, "note")
        with self._lock:
            self._require_learner(learner_ref)
            record_id = self._next_id("uad")
            record = {
                "id": record_id,
                "learner_ref": learner_ref,
                "action_label": action_label,
                "note": note,
                "identity_provider": False,
                "recorded_by": actor_name(actor),
                "recorded_utc": _utc_now(),
            }
            self._user_admin_actions[record_id] = record
            self._audit(actor, "ext_user_admin_action_record", record_id,
                        details={"learner_ref": learner_ref,
                                 "action_label": action_label})
            return dict(record)

    @staticmethod
    def _current_admin_state(actions):
        """Derive the current administrative state from action records.

        The state is the LATEST recorded action's label — actions
        are append-only and ordered, so the last one is the current
        administrative fact. Never stored.

        MUTATION DRILL NOTE: this latest-wins rule is the batch
        negative control's load-bearing invariant — reading the
        earliest action instead must fail the suite (see
        tests/README.md).
        """
        if not actions:
            return NO_RECORDED_ACTION
        return actions[-1]["action_label"]

    def user_admin_view(self, learner_ref, actor=None):
        """Return one learner's derived administration view.

        Action: learner_read (+ learner scope). The current state
        is derived at read from the recorded actions, never stored.
        """
        if actor is not None:
            self._require_actor(actor, "learner_read")
        self._scope_check(actor, learner_ref)
        with self._lock:
            self._require_learner(learner_ref)
            actions = [a for a in self._user_admin_actions.values()
                       if a["learner_ref"] == learner_ref]
            return {
                "learner_ref": learner_ref,
                "current_admin_state": self._current_admin_state(actions),
                "action_count": len(actions),
                "identity_provider": False,
                "method": "derived_from_recorded_actions",
            }

    def list_user_admin_actions(self, actor=None, learner_ref=None):
        """Return user administration action records. Action: learner_read."""
        if actor is not None:
            self._require_actor(actor, "learner_read")
        if learner_ref is not None:
            self._scope_check(actor, learner_ref)
        with self._lock:
            records = list(self._user_admin_actions.values())
            if learner_ref is not None:
                records = [r for r in records
                           if r["learner_ref"] == learner_ref]
            if self._is_learner(actor):
                name = getattr(actor, "name", None)
                records = [r for r in records if r["learner_ref"] == name]
            return [dict(r) for r in records]
