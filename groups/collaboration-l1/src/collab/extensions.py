"""Final GAPS batch extensions for the Collaboration L1 core.

This module closes the nine Extended families registered for
Group 10 in the repo's gap registry (see ``../../BATCH.md`` for the
per-entry dispositions). It adds one class, :class:`CollabExtensions`,
wrapping the core :class:`~collab.store.CollabStore`; every core
module is untouched, and every record this surface creates lives in
the extension's own tables beside the core.

Discipline, per the batch decision and this group's spec:

- Records and derivations only. Derived values (article current
  text, milestone state counts, disposition eligibility, workspace
  analytics) are computed at read and never stored; stored records
  carry no derived key, and tests pin that.
- The stub-engine families ship as labeled reference
  implementations: every record they create carries
  ``reference_stub: True``, and nothing here executes a workflow,
  infers, transcribes, connects a call, transports media, or signs.
- RBAC is enforced through the core ``collab.access`` matrix. The
  core action set is fixed, so each extension write maps onto an
  existing core action (documented per method below); the guard
  also enforces workspace membership through the core store itself.
  Denied attempts are recorded on the core audit log as
  ``ext_<action>:denied`` and every successful mutation as
  ``ext_<action>``. If an audit write fails, the record insertion
  and its id roll back before the error propagates — no extension
  record exists whose audit entry does not.
- Validation always precedes mutation: a failed operation consumes
  no id and changes nothing.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _utc_now_dt():
    return datetime.now(timezone.utc)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_tags(tags):
    if tags is None:
        return []
    if not isinstance(tags, (list, tuple)) or any(
        not isinstance(tag, str) for tag in tags
    ):
        raise ValidationError("tags must be a list of strings")
    return list(tags)


def _parse_iso_datetime(value, what):
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be an ISO-8601 datetime string" % (what,))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        return datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid ISO-8601 datetime: %r" % (what, value)
        ) from exc


class CollabExtensions:
    """Records-layer extensions over a core :class:`CollabStore`."""

    def __init__(self, store):
        self.store = store
        self._courses = {}
        self._enrollments = {}
        self._completions = {}
        self._articles = {}
        self._article_revisions = {}
        self._milestones = {}
        self._milestone_links = {}
        self._card_states = {}
        self._retention_policies = {}
        self._holds = {}
        self._hold_releases = {}
        self._disposition_decisions = {}
        self._assistants = {}
        self._assistant_reports = {}
        self._transcription_jobs = {}
        self._transcription_reports = {}
        self._workflow_definitions = {}
        self._voice_channels = {}
        self._voice_sessions = {}
        self._meeting_sessions = {}
        self._envelopes = {}
        self._ceremony_events = {}
        self._counters = {
            "crs": 0,
            "enr": 0,
            "cmp": 0,
            "kb": 0,
            "kbrev": 0,
            "ms": 0,
            "msl": 0,
            "cst": 0,
            "pol": 0,
            "hld": 0,
            "hlr": 0,
            "dsp": 0,
            "ai": 0,
            "air": 0,
            "trn": 0,
            "trnr": 0,
            "wfd": 0,
            "vch": 0,
            "vcs": 0,
            "mtg": 0,
            "env": 0,
            "sgn": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, workspace_id, actor, action, audit_action):
        """Enforce workspace membership (via the core store) and the
        mapped core role permission. A PermissionDenied is audited as
        ``ext_<audit_action>:denied`` before it propagates."""
        try:
            workspace = self.store.get_workspace(workspace_id, actor)
            if actor is not None and hasattr(actor, "role"):
                require(actor, action)
        except PermissionDenied:
            try:
                self._audit(actor, "ext_%s:denied" % audit_action, workspace_id)
            except Exception:
                pass
            raise
        return workspace

    def _insert(self, table, prefix, record, actor, audit_action, details=None):
        """Insert ``record`` and audit the mutation, rolling both the
        record and its id back if the audit write fails."""
        with self._lock:
            table[record["id"]] = record
            try:
                self._audit(actor, "ext_%s" % audit_action, record["id"],
                            details=details)
            except Exception:
                del table[record["id"]]
                self._counters[prefix] -= 1
                raise
            return dict(record)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _get_in_workspace(self, table, record_id, workspace_id, what):
        record = self._get(table, record_id, what)
        if record["workspace_id"] != workspace_id:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    # -- learning / training / mentoring (build) -----------------------

    def create_course(self, workspace_id, title, actor):
        """Create a course record in a workspace. Core action: post.

        A course is a records-layer container for enrollments and
        verbatim completion records; nothing is taught or assessed
        here (see :meth:`record_completion`).
        """
        _validate_non_empty(title, "course title")
        with self._lock:
            self._guard(workspace_id, actor, "post", "course_create")
            record = {
                "id": self._next_id("crs"),
                "workspace_id": workspace_id,
                "title": title,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._courses, "crs", record, actor,
                                "course_create", details={"title": title})

    def enroll_learner(self, workspace_id, course_id, learner, actor):
        """Enroll a workspace member in a course. Core action: post.

        ``learner`` must already be a member of the workspace — the
        same membership boundary the core enforces everywhere else.
        """
        _validate_non_empty(learner, "learner")
        with self._lock:
            workspace = self._guard(workspace_id, actor, "post",
                                    "course_enroll")
            self._get_in_workspace(self._courses, course_id, workspace_id,
                                   "course")
            if learner not in workspace["members"]:
                raise ValidationError(
                    "learner %r is not a member of workspace %r"
                    % (learner, workspace_id)
                )
            for enrollment in self._enrollments.values():
                if (
                    enrollment["course_id"] == course_id
                    and enrollment["learner"] == learner
                ):
                    raise ValidationError(
                        "learner %r is already enrolled in course %r"
                        % (learner, course_id)
                    )
            record = {
                "id": self._next_id("enr"),
                "workspace_id": workspace_id,
                "course_id": course_id,
                "learner": learner,
                "enrolled_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._enrollments, "enr", record, actor,
                                "course_enroll", details={"course_id": course_id})

    def record_completion(self, workspace_id, enrollment_id, outcome, actor):
        """Record a completion outcome for an enrollment, verbatim.

        Core action: post. The outcome label is stored exactly as
        reported by whoever ran the course; this build assesses
        nothing, so the record carries ``assessed_here: False``.
        """
        _validate_non_empty(outcome, "completion outcome")
        with self._lock:
            self._guard(workspace_id, actor, "post", "completion_record")
            self._get_in_workspace(self._enrollments, enrollment_id,
                                   workspace_id, "enrollment")
            record = {
                "id": self._next_id("cmp"),
                "workspace_id": workspace_id,
                "enrollment_id": enrollment_id,
                "outcome": outcome,
                "assessed_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._completions, "cmp", record, actor,
                                "completion_record",
                                details={"enrollment_id": enrollment_id})

    def get_course(self, workspace_id, course_id, actor):
        """Return one stored course record."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "course_read")
            return dict(self._get_in_workspace(
                self._courses, course_id, workspace_id, "course"))

    def list_courses(self, workspace_id, actor):
        """Return a workspace's course records, in creation order."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "course_read")
            return [
                dict(course)
                for course in self._courses.values()
                if course["workspace_id"] == workspace_id
            ]

    def list_enrollments(self, workspace_id, actor, course_id=None):
        """Return enrollment records, optionally for one course."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "course_read")
            return [
                dict(enrollment)
                for enrollment in self._enrollments.values()
                if enrollment["workspace_id"] == workspace_id
                and (course_id is None or enrollment["course_id"] == course_id)
            ]

    def list_completions(self, workspace_id, actor, enrollment_id=None):
        """Return completion records, optionally for one enrollment."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "course_read")
            return [
                dict(completion)
                for completion in self._completions.values()
                if completion["workspace_id"] == workspace_id
                and (
                    enrollment_id is None
                    or completion["enrollment_id"] == enrollment_id
                )
            ]

    def course_view(self, workspace_id, course_id, actor):
        """A course record plus counts derived at read: enrollments
        and recorded completions. Nothing derived is stored."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "course_read")
            course = dict(self._get_in_workspace(
                self._courses, course_id, workspace_id, "course"))
            enrollment_ids = {
                enrollment["id"]
                for enrollment in self._enrollments.values()
                if enrollment["course_id"] == course_id
            }
            course["enrollment_count"] = len(enrollment_ids)
            course["completion_count"] = sum(
                1
                for completion in self._completions.values()
                if completion["enrollment_id"] in enrollment_ids
            )
            course["derived"] = True
            return course

    # -- knowledge management (build) -----------------------------------

    def create_article(self, workspace_id, title, body, actor, tags=None):
        """Create a knowledge-base article. Core action: share.

        The stored article record holds only tags and provenance
        (pinned by an exact key-set test); the title and body live
        in the first append-only revision record.
        """
        _validate_non_empty(title, "article title")
        if not isinstance(body, str):
            raise ValidationError("article body must be a string")
        tags = _validate_tags(tags)
        with self._lock:
            self._guard(workspace_id, actor, "share", "article_create")
            article = {
                "id": self._next_id("kb"),
                "workspace_id": workspace_id,
                "tags": tags,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            revision = {
                "id": self._next_id("kbrev"),
                "workspace_id": workspace_id,
                "article_id": article["id"],
                "revision": 1,
                "title": title,
                "body": body,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._article_revisions[revision["id"]] = revision
            try:
                return self._insert(self._articles, "kb", article, actor,
                                    "article_create", details={"title": title})
            except Exception:
                del self._article_revisions[revision["id"]]
                self._counters["kbrev"] -= 1
                raise

    def revise_article(self, workspace_id, article_id, title, body, actor):
        """Append a revision to an article. Core action: share.

        Revisions are append-only: earlier revisions never change
        and there is no update or delete API.
        """
        _validate_non_empty(title, "article title")
        if not isinstance(body, str):
            raise ValidationError("article body must be a string")
        with self._lock:
            self._guard(workspace_id, actor, "share", "article_revise")
            self._get_in_workspace(self._articles, article_id, workspace_id,
                                   "article")
            number = 1 + sum(
                1
                for revision in self._article_revisions.values()
                if revision["article_id"] == article_id
            )
            record = {
                "id": self._next_id("kbrev"),
                "workspace_id": workspace_id,
                "article_id": article_id,
                "revision": number,
                "title": title,
                "body": body,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._article_revisions, "kbrev", record,
                                actor, "article_revise",
                                details={"article_id": article_id})

    def _article_revisions_of(self, article_id):
        return sorted(
            (
                revision
                for revision in self._article_revisions.values()
                if revision["article_id"] == article_id
            ),
            key=lambda revision: revision["revision"],
        )

    def get_article(self, workspace_id, article_id, actor):
        """An article view: the stored record's tags and provenance
        plus the current title/body and the revision count, derived
        at read from the latest revision."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "article_read")
            article = dict(self._get_in_workspace(
                self._articles, article_id, workspace_id, "article"))
            revisions = self._article_revisions_of(article_id)
            latest = revisions[-1]
            article["title"] = latest["title"]
            article["body"] = latest["body"]
            article["revision_count"] = len(revisions)
            article["derived"] = True
            return article

    def list_articles(self, workspace_id, actor):
        """Return a workspace's article views, in creation order."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "article_read")
            return [
                self.get_article(workspace_id, article["id"], actor)
                for article in self._articles.values()
                if article["workspace_id"] == workspace_id
            ]

    def list_article_revisions(self, workspace_id, article_id, actor):
        """Return an article's full append-only revision history."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "article_read")
            self._get_in_workspace(self._articles, article_id, workspace_id,
                                   "article")
            return [dict(r) for r in self._article_revisions_of(article_id)]

    def search_articles(self, workspace_id, query_text, actor):
        """Literal case-insensitive substring search over articles'
        current title/body — the registry pattern, not a search
        engine."""
        if not isinstance(query_text, str):
            raise ValidationError("query text must be a string")
        needle = query_text.lower()
        with self._lock:
            return [
                article
                for article in self.list_articles(workspace_id, actor)
                if needle in article["title"].lower()
                or needle in article["body"].lower()
            ]

    # -- task & project management beyond board cards (build) -----------

    def create_milestone(self, workspace_id, board_id, title, actor):
        """Create a milestone record over a core board.

        Core action: board_edit. The board must exist in the
        workspace."""
        _validate_non_empty(title, "milestone title")
        with self._lock:
            self._guard(workspace_id, actor, "board_edit", "milestone_create")
            boards = self.store.list_boards(workspace_id, actor)
            if board_id not in {board["id"] for board in boards}:
                raise NotFoundError("board not found: %r" % (board_id,))
            record = {
                "id": self._next_id("ms"),
                "workspace_id": workspace_id,
                "board_id": board_id,
                "title": title,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._milestones, "ms", record, actor,
                                "milestone_create", details={"board_id": board_id})

    def link_card_to_milestone(self, workspace_id, milestone_id, card_id,
                               actor):
        """Link a core board card to a milestone. Core action:
        board_edit. The card must be on the milestone's board."""
        with self._lock:
            self._guard(workspace_id, actor, "board_edit", "milestone_link")
            milestone = self._get_in_workspace(
                self._milestones, milestone_id, workspace_id, "milestone")
            cards = self.store.list_cards(
                workspace_id, milestone["board_id"], actor)
            if card_id not in {card["id"] for card in cards}:
                raise NotFoundError("card not found: %r" % (card_id,))
            for link in self._milestone_links.values():
                if (
                    link["milestone_id"] == milestone_id
                    and link["card_id"] == card_id
                ):
                    raise ValidationError(
                        "card %r is already linked to milestone %r"
                        % (card_id, milestone_id)
                    )
            record = {
                "id": self._next_id("msl"),
                "workspace_id": workspace_id,
                "milestone_id": milestone_id,
                "card_id": card_id,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._milestone_links, "msl", record, actor,
                                "milestone_link",
                                details={"milestone_id": milestone_id})

    def record_card_state(self, workspace_id, milestone_id, card_id, state,
                          actor):
        """Record a task state label for a milestone-linked card,
        verbatim. Core action: board_edit.

        States are the caller's labels (for example ``done``),
        stored exactly as reported; the milestone view derives
        counts over the latest label per card. Recording a state
        changes no core card.
        """
        _validate_non_empty(state, "card state")
        with self._lock:
            self._guard(workspace_id, actor, "board_edit", "card_state_record")
            self._get_in_workspace(self._milestones, milestone_id,
                                   workspace_id, "milestone")
            linked = {
                link["card_id"]
                for link in self._milestone_links.values()
                if link["milestone_id"] == milestone_id
            }
            if card_id not in linked:
                raise ValidationError(
                    "card %r is not linked to milestone %r"
                    % (card_id, milestone_id)
                )
            record = {
                "id": self._next_id("cst"),
                "workspace_id": workspace_id,
                "milestone_id": milestone_id,
                "card_id": card_id,
                "state": state,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._card_states, "cst", record, actor,
                                "card_state_record",
                                details={"milestone_id": milestone_id})

    def get_milestone(self, workspace_id, milestone_id, actor):
        """Return one stored milestone record."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "milestone_read")
            return dict(self._get_in_workspace(
                self._milestones, milestone_id, workspace_id, "milestone"))

    def list_milestones(self, workspace_id, actor):
        """Return a workspace's milestone records, in creation order."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "milestone_read")
            return [
                dict(milestone)
                for milestone in self._milestones.values()
                if milestone["workspace_id"] == workspace_id
            ]

    def milestone_view(self, workspace_id, milestone_id, actor):
        """A milestone record plus state counts derived at read:
        linked-card count, how many linked cards carry any recorded
        state, and the count of linked cards per latest recorded
        state label. Counts and states only — no progress score or
        percentage is computed or stored."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "milestone_read")
            milestone = dict(self._get_in_workspace(
                self._milestones, milestone_id, workspace_id, "milestone"))
            linked = [
                link["card_id"]
                for link in self._milestone_links.values()
                if link["milestone_id"] == milestone_id
            ]
            latest = {}
            for record in self._card_states.values():
                if record["milestone_id"] == milestone_id:
                    latest[record["card_id"]] = record["state"]
            state_counts = {}
            for card_id in linked:
                if card_id in latest:
                    label = latest[card_id]
                    state_counts[label] = state_counts.get(label, 0) + 1
            milestone["linked_card_count"] = len(linked)
            milestone["cards_with_state"] = sum(state_counts.values())
            milestone["cards_without_state"] = len(linked) - sum(
                state_counts.values())
            milestone["state_counts"] = state_counts
            milestone["derived"] = True
            return milestone

    # -- records & governance beyond the versioning/audit seed (build) --

    def create_retention_policy(self, workspace_id, name, retention_days,
                                actor):
        """Record a retention policy as data. Core action:
        manage_members.

        The policy is the operator's recorded schedule. Per
        PLATFORM-LAYER.md decision 4, retention enforcement and
        eventual disposition are the embedding organization's
        records schedule executed at the deployment layer; this
        build records the policy and derives eligibility against
        it, and enforces and disposes of nothing.
        """
        _validate_non_empty(name, "policy name")
        if (
            isinstance(retention_days, bool)
            or not isinstance(retention_days, int)
            or retention_days < 0
        ):
            raise ValidationError("retention_days must be a non-negative int")
        with self._lock:
            self._guard(workspace_id, actor, "manage_members", "policy_create")
            record = {
                "id": self._next_id("pol"),
                "workspace_id": workspace_id,
                "name": name,
                "retention_days": retention_days,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._retention_policies, "pol", record, actor,
                                "policy_create", details={"name": name})

    def _file_record(self, workspace_id, file_id, actor):
        files = self.store.list_files(workspace_id, actor)
        for record in files:
            if record["id"] == file_id:
                return record
        raise NotFoundError("file not found: %r" % (file_id,))

    def place_hold(self, workspace_id, file_id, reason, actor):
        """Place a legal-hold record over a core file.

        Core action: manage_members. The hold is a record; placing
        one changes no core file record (pinned by test), and it
        gates disposition decisions while active (see
        :meth:`record_disposition_decision`).
        """
        _validate_non_empty(reason, "hold reason")
        with self._lock:
            self._guard(workspace_id, actor, "manage_members", "hold_place")
            self._file_record(workspace_id, file_id, actor)
            record = {
                "id": self._next_id("hld"),
                "workspace_id": workspace_id,
                "file_id": file_id,
                "reason": reason,
                "executed_here": False,
                "placed_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._holds, "hld", record, actor, "hold_place",
                                details={"file_id": file_id})

    def release_hold(self, workspace_id, hold_id, actor):
        """Record the release of a hold. Core action: manage_members.

        Hold currency is derived at read from the presence of a
        release record; the hold record itself never changes.
        Releasing an already-released hold is refused.
        """
        with self._lock:
            self._guard(workspace_id, actor, "manage_members", "hold_release")
            self._get_in_workspace(self._holds, hold_id, workspace_id, "hold")
            if any(
                release["hold_id"] == hold_id
                for release in self._hold_releases.values()
            ):
                raise ValidationError("hold %r is already released" % (hold_id,))
            record = {
                "id": self._next_id("hlr"),
                "workspace_id": workspace_id,
                "hold_id": hold_id,
                "released_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._hold_releases, "hlr", record, actor,
                                "hold_release", details={"hold_id": hold_id})

    def _active_hold_ids(self, workspace_id, file_id):
        released = {
            release["hold_id"] for release in self._hold_releases.values()
        }
        return [
            hold["id"]
            for hold in self._holds.values()
            if hold["workspace_id"] == workspace_id
            and hold["file_id"] == file_id
            and hold["id"] not in released
        ]

    def hold_view(self, workspace_id, hold_id, actor):
        """A hold record plus its derived currency: ``active`` is
        derived at read (no release record exists); nothing derived
        is stored on the hold record."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "hold_read")
            hold = dict(self._get_in_workspace(
                self._holds, hold_id, workspace_id, "hold"))
            hold["active"] = not any(
                release["hold_id"] == hold_id
                for release in self._hold_releases.values()
            )
            hold["derived"] = True
            return hold

    def list_holds(self, workspace_id, actor, file_id=None):
        """Return hold views, optionally for one file."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "hold_read")
            return [
                self.hold_view(workspace_id, hold["id"], actor)
                for hold in self._holds.values()
                if hold["workspace_id"] == workspace_id
                and (file_id is None or hold["file_id"] == file_id)
            ]

    def _disposition_eligible(self, file_record, policy, holds_active, at_dt):
        """The disposition-eligibility seam.

        True iff the file's age at ``at_dt`` meets the policy's
        recorded retention period AND no hold is active over the
        file. This is the single derivation point for disposition
        eligibility — the batch's fresh negative control mutates it
        (see tests/README.md).
        """
        if holds_active:
            return False
        created_dt = _parse_iso_datetime(file_record["created_utc"],
                                         "file created_utc")
        age_days = (at_dt - created_dt).total_seconds() / 86400.0
        return age_days >= policy["retention_days"]

    def disposition_eligibility(self, workspace_id, file_id, policy_id,
                                actor, at=None):
        """Derive a file's disposition eligibility under a recorded
        policy, at read: retention met, active holds, and the
        eligibility itself. Stored nowhere."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "disposition_read")
            file_record = self._file_record(workspace_id, file_id, actor)
            policy = self._get_in_workspace(
                self._retention_policies, policy_id, workspace_id, "policy")
            at_dt = _parse_iso_datetime(at, "at") if at is not None \
                else _utc_now_dt()
            active_holds = self._active_hold_ids(workspace_id, file_id)
            created_dt = _parse_iso_datetime(file_record["created_utc"],
                                             "file created_utc")
            age_days = (at_dt - created_dt).total_seconds() / 86400.0
            return {
                "workspace_id": workspace_id,
                "file_id": file_id,
                "policy_id": policy_id,
                "retention_days": policy["retention_days"],
                "age_days": age_days,
                "retention_met": age_days >= policy["retention_days"],
                "active_hold_ids": active_holds,
                "eligible": self._disposition_eligible(
                    file_record, policy, bool(active_holds), at_dt),
                "derived": True,
            }

    def record_disposition_decision(self, workspace_id, file_id, policy_id,
                                    actor, at=None):
        """Record a disposition decision for a file under a policy.

        Core action: manage_members. The decision is **gated**: it
        is recorded only when the file is eligible at the decision
        moment (retention met under the recorded policy, no active
        hold), derived through :meth:`_disposition_eligible`;
        otherwise the request is refused whole and nothing is
        stored. The record states that a decision was recorded;
        executing the disposition is the deployment layer's work
        (PLATFORM-LAYER.md decision 4), so the record carries
        ``executed_here: False`` and recording one changes no core
        file record.
        """
        with self._lock:
            self._guard(workspace_id, actor, "manage_members",
                        "disposition_decision")
            file_record = self._file_record(workspace_id, file_id, actor)
            policy = self._get_in_workspace(
                self._retention_policies, policy_id, workspace_id, "policy")
            at_dt = _parse_iso_datetime(at, "at") if at is not None \
                else _utc_now_dt()
            active_holds = self._active_hold_ids(workspace_id, file_id)
            if not self._disposition_eligible(
                file_record, policy, bool(active_holds), at_dt
            ):
                raise ValidationError(
                    "file %r is not eligible for disposition under policy "
                    "%r (retention unmet or an active hold applies)"
                    % (file_id, policy_id)
                )
            record = {
                "id": self._next_id("dsp"),
                "workspace_id": workspace_id,
                "file_id": file_id,
                "policy_id": policy_id,
                "executed_here": False,
                "decided_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._disposition_decisions, "dsp", record,
                                actor, "disposition_decision",
                                details={"file_id": file_id,
                                         "policy_id": policy_id})

    def list_disposition_decisions(self, workspace_id, actor, file_id=None):
        """Return disposition decision records, optionally for a file."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "disposition_read")
            return [
                dict(decision)
                for decision in self._disposition_decisions.values()
                if decision["workspace_id"] == workspace_id
                and (file_id is None or decision["file_id"] == file_id)
            ]

    # -- AI assistance / speech / analytics (reference) ------------------

    def register_assistant(self, workspace_id, name, actor):
        """Register an AI assistant as a labeled reference record.

        Core action: post. The assistant is the siblings' own
        product AI; this build ships none, so the record is a
        declaration only (``reference_stub: True``,
        ``inference_here: False``).
        """
        _validate_non_empty(name, "assistant name")
        with self._lock:
            self._guard(workspace_id, actor, "post", "assistant_register")
            record = {
                "id": self._next_id("ai"),
                "workspace_id": workspace_id,
                "name": name,
                "reference_stub": True,
                "inference_here": False,
                "method": "recorded_declaration_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._assistants, "ai", record, actor,
                                "assistant_register", details={"name": name})

    def record_assistant_report(self, workspace_id, assistant_id, outcome,
                                actor, message_id=None):
        """Record an assistant's reported outcome, verbatim.

        Core action: post. May reference an existing core message;
        a test pins that the referenced message is untouched — the
        build infers nothing, answers nothing, and decides nothing.
        """
        _validate_non_empty(outcome, "assistant outcome")
        with self._lock:
            self._guard(workspace_id, actor, "post", "assistant_report")
            self._get_in_workspace(self._assistants, assistant_id,
                                   workspace_id, "assistant")
            if message_id is not None:
                self.store.get_message(workspace_id, message_id, actor)
            record = {
                "id": self._next_id("air"),
                "workspace_id": workspace_id,
                "assistant_id": assistant_id,
                "message_id": message_id,
                "outcome": outcome,
                "reference_stub": True,
                "decided_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._assistant_reports, "air", record, actor,
                                "assistant_report",
                                details={"assistant_id": assistant_id})

    def register_transcription_job(self, workspace_id, source_ref, actor):
        """Register a speech-transcription job as a reference record.

        Core action: post. ``source_ref`` is an opaque reference to
        audio held elsewhere; no audio and no transcript exists in
        this build.
        """
        _validate_non_empty(source_ref, "source_ref")
        with self._lock:
            self._guard(workspace_id, actor, "post", "transcription_register")
            record = {
                "id": self._next_id("trn"),
                "workspace_id": workspace_id,
                "source_ref": source_ref,
                "reference_stub": True,
                "transcribed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._transcription_jobs, "trn", record, actor,
                                "transcription_register",
                                details={"source_ref": source_ref})

    def record_transcription_report(self, workspace_id, job_id, outcome,
                                    actor, result_ref=None):
        """Record a transcription job's reported outcome, verbatim.

        Core action: post. The result is an opaque ``result_ref``
        only — the record's exact shape is pinned by test, and no
        field can hold transcript text.
        """
        _validate_non_empty(outcome, "transcription outcome")
        if result_ref is not None:
            _validate_non_empty(result_ref, "result_ref")
        with self._lock:
            self._guard(workspace_id, actor, "post", "transcription_report")
            self._get_in_workspace(self._transcription_jobs, job_id,
                                   workspace_id, "transcription job")
            record = {
                "id": self._next_id("trnr"),
                "workspace_id": workspace_id,
                "job_id": job_id,
                "outcome": outcome,
                "result_ref": result_ref,
                "reference_stub": True,
                "transcribed_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._transcription_reports, "trnr", record,
                                actor, "transcription_report",
                                details={"job_id": job_id})

    def list_assistants(self, workspace_id, actor):
        """Return a workspace's assistant reference records."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "assistant_read")
            return [
                dict(assistant)
                for assistant in self._assistants.values()
                if assistant["workspace_id"] == workspace_id
            ]

    def list_transcription_jobs(self, workspace_id, actor):
        """Return a workspace's transcription job records."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "transcription_read")
            return [
                dict(job)
                for job in self._transcription_jobs.values()
                if job["workspace_id"] == workspace_id
            ]

    def workspace_analytics(self, workspace_id, actor):
        """Deterministic counts over core records, derived at read:
        members, channels, messages, files, events, boards, and
        cards. ``method: deterministic_counts_over_core_records``;
        stored nowhere, and a derivation, not a snapshot — it moves
        as records are added."""
        with self._lock:
            workspace = self._guard(workspace_id, actor, "read",
                                    "analytics_read")
            channels = self.store.list_channels(workspace_id, actor)
            files = self.store.list_files(workspace_id, actor)
            events = self.store.list_events(workspace_id, actor)
            boards = self.store.list_boards(workspace_id, actor)
            message_count = 0
            for channel in channels:
                message_count += len(
                    self.store.list_messages(workspace_id, channel["id"],
                                             actor))
            card_count = 0
            for board in boards:
                card_count += len(
                    self.store.list_cards(workspace_id, board["id"], actor))
            return {
                "workspace_id": workspace_id,
                "members": len(workspace["members"]),
                "channels": len(channels),
                "messages": message_count,
                "files": len(files),
                "events": len(events),
                "boards": len(boards),
                "cards": card_count,
                "method": "deterministic_counts_over_core_records",
                "derived": True,
            }

    # -- workflow / process automation (reference) ------------------------

    def register_workflow_definition(self, workspace_id, name, steps, actor):
        """Register a workflow definition as data. Core action: post.

        Definitions are held as an ordered list of step labels and
        are **never run**: per the house registry-never-executes
        doctrine, registering one changes no core record (pinned
        behaviorally by test).
        """
        _validate_non_empty(name, "workflow name")
        if (
            not isinstance(steps, (list, tuple))
            or not steps
            or any(not isinstance(step, str) or not step.strip()
                   for step in steps)
        ):
            raise ValidationError(
                "steps must be a non-empty list of step labels")
        with self._lock:
            self._guard(workspace_id, actor, "post", "workflow_register")
            record = {
                "id": self._next_id("wfd"),
                "workspace_id": workspace_id,
                "name": name,
                "steps": list(steps),
                "reference_stub": True,
                "state": "recorded_reference_only",
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._workflow_definitions, "wfd", record,
                                actor, "workflow_register",
                                details={"name": name})

    def list_workflow_definitions(self, workspace_id, actor):
        """Return a workspace's workflow definition records."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "workflow_read")
            return [
                dict(definition)
                for definition in self._workflow_definitions.values()
                if definition["workspace_id"] == workspace_id
            ]

    # -- voice / telephony / contact center (reference) -------------------

    def register_voice_channel(self, workspace_id, label, actor):
        """Register a voice/telephony channel as a reference record.

        Core action: post. Real-time media transport is outside
        this build; nothing connects (``connected_here: False``,
        ``media_here: False``).
        """
        _validate_non_empty(label, "channel label")
        with self._lock:
            self._guard(workspace_id, actor, "post", "voice_channel_register")
            record = {
                "id": self._next_id("vch"),
                "workspace_id": workspace_id,
                "label": label,
                "reference_stub": True,
                "connected_here": False,
                "media_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._voice_channels, "vch", record, actor,
                                "voice_channel_register",
                                details={"label": label})

    def record_voice_session(self, workspace_id, channel_id, outcome, actor):
        """Record a voice channel's reported session outcome,
        verbatim. Core action: post."""
        _validate_non_empty(outcome, "session outcome")
        with self._lock:
            self._guard(workspace_id, actor, "post", "voice_session_record")
            self._get_in_workspace(self._voice_channels, channel_id,
                                   workspace_id, "voice channel")
            record = {
                "id": self._next_id("vcs"),
                "workspace_id": workspace_id,
                "channel_id": channel_id,
                "outcome": outcome,
                "reference_stub": True,
                "connected_here": False,
                "media_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._voice_sessions, "vcs", record, actor,
                                "voice_session_record",
                                details={"channel_id": channel_id})

    def list_voice_channels(self, workspace_id, actor):
        """Return a workspace's voice channel reference records."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "voice_read")
            return [
                dict(channel)
                for channel in self._voice_channels.values()
                if channel["workspace_id"] == workspace_id
            ]

    # -- meetings / video media transport (reference) -----------------------

    def record_meeting_session(self, workspace_id, title, actor,
                               event_id=None):
        """Record a meeting session as a coordination record only.

        Core action: schedule. May reference an existing core
        calendar event (the coordination surface around meetings is
        Core); the session itself transports no audio or video
        (``media_here: False``).
        """
        _validate_non_empty(title, "meeting title")
        with self._lock:
            self._guard(workspace_id, actor, "schedule", "meeting_record")
            if event_id is not None:
                events = self.store.list_events(workspace_id, actor)
                if event_id not in {event["id"] for event in events}:
                    raise NotFoundError("event not found: %r" % (event_id,))
            record = {
                "id": self._next_id("mtg"),
                "workspace_id": workspace_id,
                "event_id": event_id,
                "title": title,
                "reference_stub": True,
                "media_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._meeting_sessions, "mtg", record, actor,
                                "meeting_record", details={"title": title})

    def list_meeting_sessions(self, workspace_id, actor):
        """Return a workspace's meeting session records."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "meeting_read")
            return [
                dict(session)
                for session in self._meeting_sessions.values()
                if session["workspace_id"] == workspace_id
            ]

    # -- e-signature (reference) ---------------------------------------------

    def create_envelope(self, workspace_id, file_id, actor):
        """Create a signature envelope record over a core file.

        Core action: share. Follows the Legal & Policy house form:
        a labeled reference record (``reference_stub: True``,
        ``signed_here: False``) whose exact shape is pinned by
        test — no field can hold a signature value, a certificate,
        or a credential. Nothing is signed here.
        """
        with self._lock:
            self._guard(workspace_id, actor, "share", "envelope_create")
            self._file_record(workspace_id, file_id, actor)
            record = {
                "id": self._next_id("env"),
                "workspace_id": workspace_id,
                "file_id": file_id,
                "reference_stub": True,
                "state": "recorded_reference_only",
                "signed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._envelopes, "env", record, actor,
                                "envelope_create", details={"file_id": file_id})

    def record_ceremony_event(self, workspace_id, envelope_id, signer,
                              event, actor):
        """Record a signing-ceremony event, verbatim. Core action:
        share. ``signer`` must be a workspace member, named by
        opaque username; the reported ceremony label is stored
        exactly as reported and effects no binding or validity."""
        _validate_non_empty(event, "ceremony event")
        _validate_non_empty(signer, "signer")
        with self._lock:
            workspace = self._guard(workspace_id, actor, "share",
                                    "ceremony_record")
            self._get_in_workspace(self._envelopes, envelope_id, workspace_id,
                                   "envelope")
            if signer not in workspace["members"]:
                raise ValidationError(
                    "signer %r is not a member of workspace %r"
                    % (signer, workspace_id)
                )
            record = {
                "id": self._next_id("sgn"),
                "workspace_id": workspace_id,
                "envelope_id": envelope_id,
                "signer": signer,
                "event": event,
                "reference_stub": True,
                "signed_here": False,
                "recorded_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            return self._insert(self._ceremony_events, "sgn", record, actor,
                                "ceremony_record",
                                details={"envelope_id": envelope_id})

    def list_envelopes(self, workspace_id, actor):
        """Return a workspace's envelope reference records."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "envelope_read")
            return [
                dict(envelope)
                for envelope in self._envelopes.values()
                if envelope["workspace_id"] == workspace_id
            ]

    def list_ceremony_events(self, workspace_id, actor, envelope_id=None):
        """Return ceremony event records, optionally for one envelope."""
        with self._lock:
            self._guard(workspace_id, actor, "read", "envelope_read")
            return [
                dict(event)
                for event in self._ceremony_events.values()
                if event["workspace_id"] == workspace_id
                and (envelope_id is None or event["envelope_id"] == envelope_id)
            ]
