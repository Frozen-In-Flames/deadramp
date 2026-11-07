"""Final GAPS batch extensions for the CRM L2 merged build
(Group 25).

Clean-room, standard-library-only records/derivation extensions for
the 8 open Extended entries this group's GAPS.md section carries:
3 drafted ``build-extension`` and 5 drafted ``stub-engine`` in
``../../gaps-batch/inventory.json`` (idx 268-275). See ``BATCH.md``
in the group directory for the per-entry disposition, including
one re-judgment recorded there under DECISION.md qualification 1.

Design, following the core's doctrines:

- This module is a wrapper around :class:`CrmStore`; the core
  modules are untouched (byte-identical). Core state (accounts,
  contacts, cases, guides, findings, modules) is read through the
  core store's public API, never re-implemented, and no extension
  operation writes core state. Existence checks against the core
  pass ``actor=None`` internally: the extension's own guard has
  already enforced the mapped action before the check runs.
- RBAC goes through :mod:`crm.access` exactly as the core enforces
  it: the extension maps each of its operations onto an existing
  core action (the core action set is fixed), checks it *before*
  any state change or id allocation for User-like actors, and
  records denied attempts on the core audit log with the extension
  action name suffixed ``:denied``. Plain-string actors carry
  identity but no role, mirroring the core convention. The mapping
  is:

  - knowledge base articles, agent desktops, self-service topics
    -> ``guide_write`` / ``guide_read`` (guidance-content genus);
  - chat session records -> ``interaction_write`` /
    ``interaction_read``;
  - guidance sessions and authoring definitions -> ``guide_write``
    / ``guide_read`` (they bind guide records);
  - telemetry and detection reports -> ``finding_write`` /
    ``finding_read`` (finding-genus reported records);
  - engagement metrics -> ``report_read``;
  - module execution requests/reports and runtime parameter sets
    -> ``config_write`` / ``config_read`` (they bind module
    configuration records; ``config_write`` is admin-only, as in
    the core);
  - marketing segments, flow definitions and flow outcomes ->
    ``guide_write`` / ``guide_read`` (campaign-shaped content
    records ride the content genus);
  - AI request/report/evaluation records -> ``case_write`` /
    ``case_read`` (they bind cases; case-adjacent operational
    records);
  - connector sync records and the connector catalog ->
    ``config_write`` / ``config_read`` (integration configuration
    genus);
  - the extension summary -> ``report_read``.

- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. If the
  audit write raises, the record insertion and its id roll back
  before the error propagates: no extension record exists whose
  audit entry does not.
- All references to people, systems, and domains are opaque
  ``*_ref`` strings, exactly as in the core. Where a record binds
  a person it names a core contact by id or an opaque
  ``contact_ref`` string; no record shape in this module can hold
  a real name, email, phone number, or any other identifier, and
  none can hold money in motion or a computed score.
- Derived values are derived at read and never stored: knowledge
  base current text and revision counts, engagement metrics,
  connector catalog rollups, the extension summary. Stored records
  carry no derived key; tests pin that.
- Nothing here executes against an external system. The
  stub-engine families ship as labeled reference implementations:
  every record they create carries ``reference_stub: True``
  (connector sync receipts additionally carry
  ``reference_transport: True``), and no guidance is rendered, no
  telemetry is collected, no gap is detected, no message is sent,
  no model is run, and nothing is synced. The customization /
  module-engine entry is re-judged to the same labeled reference
  form; the grounds are in ``BATCH.md``.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import KNOWN_SEVERITIES, SEVERITIES

EXECUTION_REPORT_OUTCOMES = (
    "reported_completed",
    "reported_failed",
    "reported_noop",
)
KNOWN_EXECUTION_REPORT_OUTCOMES = frozenset(EXECUTION_REPORT_OUTCOMES)
CONNECTOR_DIRECTIONS = ("inbound", "outbound")
KNOWN_CONNECTOR_DIRECTIONS = frozenset(CONNECTOR_DIRECTIONS)
CONNECTOR_TARGET_KINDS = ("account", "case", "guide", "finding", "module")
KNOWN_CONNECTOR_TARGET_KINDS = frozenset(CONNECTOR_TARGET_KINDS)

# Keys that would make a record carry a computed score. The core
# forbids scores by design; the extension refuses them as parameter
# names and result labels alike (tests pin the refusal and scan
# every stored record for these keys).
SCORE_KEYS = frozenset({
    "score", "rating", "rank", "probability", "confidence",
    "likelihood", "propensity",
})


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _nonneg_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % (what,))
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(names)))
    return value


def _string_list(value, what):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(
            "%s must be a list of non-empty strings" % (what,))
    if len(value) > 50:
        raise ValidationError("%s may hold at most 50 entries" % (what,))
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                "each entry in %s must be a non-empty string" % (what,))
        result.append(item)
    return result


def _validate_parameters(parameters, what="parameters", required=False):
    """Validate a configuration-parameter mapping held as data.

    Keys are parameter names (non-empty strings, never score-shaped);
    values are strings, integers, or booleans -- the scalar shapes a
    configuration record can state. Floats are rejected (house
    rule: recorded values are exact), as are nested structures:
    parameters are data, not a program.
    """
    if parameters is None:
        if required:
            raise ValidationError("%s are required" % (what,))
        return None
    if not isinstance(parameters, dict):
        raise ValidationError("%s must be a dict" % (what,))
    if required and not parameters:
        raise ValidationError("%s must not be empty" % (what,))
    for key, value in parameters.items():
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(
                "each key in %s must be a non-empty string" % (what,))
        if key.strip().lower() in SCORE_KEYS:
            raise ValidationError(
                "%s may not carry a score-shaped key: %r" % (what, key))
        if isinstance(value, bool) or isinstance(value, (str, int)):
            continue
        raise ValidationError(
            "each value in %s must be a string, integer, or boolean"
            % (what,))
    return copy.deepcopy(parameters)


def _validate_flow_steps(steps):
    """Validate marketing-flow step records: {step, channel} data."""
    if steps is None:
        return []
    if not isinstance(steps, list):
        raise ValidationError("steps must be a list of step records")
    if len(steps) > 50:
        raise ValidationError("steps may hold at most 50 entries")
    result = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValidationError("each step must be a record")
        name = step.get("step")
        channel = step.get("channel")
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("each step needs a non-empty 'step'")
        if not isinstance(channel, str) or not channel.strip():
            raise ValidationError("each step needs a non-empty 'channel'")
        result.append({"step": name, "channel": channel})
    return result


class CrmExtensions:
    """GAPS-batch extension surface over a core CrmStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
        """Enforce a write permission, auditing a denial.

        Mirrors the core store: an actor must be present; User-like
        actors are checked against the core permission matrix before
        anything changes; plain strings carry identity only.
        """
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r"
                    % (core_action,)
                )
            if hasattr(actor, "role"):
                require(actor, core_action)
        except PermissionDenied:
            self._audit(actor, audit_action + ":denied", target)
            raise

    def _guard_read(self, actor, core_action, audit_action, target=None):
        """Enforce a read permission when the actor carries a role."""
        if actor is not None and hasattr(actor, "role"):
            try:
                require(actor, core_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", target)
                raise

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(copy.deepcopy(fields))
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed, mirroring the batch pattern: an
                # operation whose audit write fails does not proceed
                # -- the insertion and the id roll back before the
                # error propagates.
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
                raise
            return copy.deepcopy(record)

    def _update(self, kind, record_id, changes, actor, audit_action):
        with self._lock:
            record = self._get(kind, record_id)
            snapshot = copy.deepcopy(record)
            record.update(copy.deepcopy(changes))
            record["updated_utc"] = _utc_now()
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                self._records[(kind, record_id)] = snapshot
                raise
            return copy.deepcopy(record)

    def _get(self, kind, record_id):
        record = self._records.get((kind, record_id))
        if record is None:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id):
        return copy.deepcopy(self._get(kind, record_id))

    def _list(self, kind, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if all(record.get(f) == v for f, v in filters.items()):
                result.append(copy.deepcopy(record))
        return result

    # -- core existence checks (internal; see module docstring) -------

    def _core_account(self, account_id):
        return self.store.get_account(account_id)

    def _core_contact(self, contact_id):
        return self.store.get_contact(contact_id)

    def _core_case(self, case_id):
        return self.store.get_case(case_id)

    def _core_guide(self, guide_id):
        return self.store.get_guide(guide_id)

    def _core_module(self, module_id):
        return self.store.get_module(module_id)

    # ================================================================
    # Knowledge base articles (entries: casework depth; knowledge
    # base & self-service content)
    #
    # The stored article record holds only tags and provenance; the
    # text lives in append-only revision records, and the current
    # title/body and the revision count are derived at read. There
    # is no update or delete API for revisions.
    # ================================================================

    def create_kb_article(self, actor, title, body, tags=None):
        """Create a knowledge base article at revision 1.

        Action: guide_write. Ids: kb- (article), kbrev- (revision).
        """
        self._guard(actor, "guide_write", "ext_kb_article_create")
        _non_empty(title, "article title")
        _non_empty(body, "article body")
        tags = _string_list(tags, "tags")
        article = self._create(
            "kb_article", "kb", {"tags": tags}, actor,
            "ext_kb_article_create")
        try:
            self._create(
                "kb_revision", "kbrev",
                {"article_id": article["id"], "revision": 1,
                 "title": title, "body": body},
                actor, "ext_kb_article_create")
        except Exception:
            # The article and its first revision land together or
            # not at all.
            with self._lock:
                del self._records[("kb_article", article["id"])]
                self._order.remove(("kb_article", article["id"]))
                self._counters["kb"] -= 1
            raise
        return self._kb_view(article["id"])

    def revise_kb_article(self, actor, article_id, title=None, body=None):
        """Append a revision to an article. Action: guide_write.

        Unchanged fields carry forward from the current revision;
        earlier revisions never change.
        """
        self._guard(actor, "guide_write", "ext_kb_article_revise",
                    target=article_id)
        if title is not None:
            _non_empty(title, "article title")
        if body is not None:
            _non_empty(body, "article body")
        if title is None and body is None:
            raise ValidationError(
                "a revision must change the title or the body")
        with self._lock:
            self._get("kb_article", article_id)
            current = self._current_revision(article_id)
            self._create(
                "kb_revision", "kbrev",
                {"article_id": article_id,
                 "revision": current["revision"] + 1,
                 "title": title if title is not None else current["title"],
                 "body": body if body is not None else current["body"]},
                actor, "ext_kb_article_revise")
            return self._kb_view(article_id)

    def _revisions_of(self, article_id):
        return self._list("kb_revision", article_id=article_id)

    def _current_revision(self, article_id):
        revisions = self._revisions_of(article_id)
        if not revisions:
            raise NotFoundError(
                "kb_article has no revisions: %r" % (article_id,))
        return revisions[-1]

    def _kb_view(self, article_id):
        article = self._fetch("kb_article", article_id)
        revisions = self._revisions_of(article_id)
        current = revisions[-1]
        return {
            "id": article["id"],
            "tags": article["tags"],
            "title": current["title"],
            "body": current["body"],
            "revision": current["revision"],
            "revision_count": len(revisions),
            "created_by": article["created_by"],
            "created_utc": article["created_utc"],
        }

    def get_kb_article(self, article_id, actor=None):
        """One article with its current text derived. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_kb_article_read",
                         target=article_id)
        with self._lock:
            return self._kb_view(article_id)

    def list_kb_articles(self, actor=None):
        """All articles with current text derived. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_kb_article_read")
        with self._lock:
            return [self._kb_view(key[1]) for key in self._order
                    if key[0] == "kb_article"]

    def list_kb_revisions(self, article_id, actor=None):
        """The full append-only revision history. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_kb_article_read",
                         target=article_id)
        with self._lock:
            self._get("kb_article", article_id)
            return self._revisions_of(article_id)

    def search_kb_articles(self, query, actor):
        """Literal substring search over current article text.

        Action: guide_read. Registry mechanics, not a search
        engine: matches the current title/body only.
        """
        self._guard(actor, "guide_read", "ext_kb_article_search")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.lower()
        with self._lock:
            return [
                view for view in self.list_kb_articles(actor=None)
                if needle in view["title"].lower()
                or needle in view["body"].lower()
            ]

    # ================================================================
    # Casework depth: agent desktops and self-service topics
    # (entry: customer-service casework depth)
    # ================================================================

    def create_agent_desktop(self, actor, name, case_queue_ref=None,
                             kb_article_ids=None, topic_ids=None):
        """Record an agent-desktop composition. Action: guide_write.

        Id prefix: desk-. A desktop record names the case queue
        (opaque ref) and the knowledge/topic records an agent
        desktop would compose; the desktop itself -- a live agent
        workspace -- is not built, and the record says so
        (``composed_here: False``).
        """
        self._guard(actor, "guide_write", "ext_desktop_create")
        _non_empty(name, "desktop name")
        _string_or_none(case_queue_ref, "case_queue_ref")
        kb_article_ids = _string_list(kb_article_ids, "kb_article_ids")
        topic_ids = _string_list(topic_ids, "topic_ids")
        with self._lock:
            for article_id in kb_article_ids:
                self._get("kb_article", article_id)
            for topic_id in topic_ids:
                self._get("topic", topic_id)
            return self._create(
                "desktop", "desk",
                {"name": name, "case_queue_ref": case_queue_ref,
                 "kb_article_ids": kb_article_ids,
                 "topic_ids": topic_ids, "composed_here": False},
                actor, "ext_desktop_create")

    def get_agent_desktop(self, desktop_id, actor=None):
        """One desktop record. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_desktop_read",
                         target=desktop_id)
        return self._fetch("desktop", desktop_id)

    def list_agent_desktops(self, actor=None):
        """All desktop records. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_desktop_read")
        return self._list("desktop")

    def create_self_service_topic(self, actor, title, body,
                                  kb_article_id=None):
        """Record a self-service portal topic. Action: guide_write.

        Id prefix: topic-. The topic is content data a portal
        would present; no portal is hosted (``hosted_here:
        False``).
        """
        self._guard(actor, "guide_write", "ext_topic_create")
        _non_empty(title, "topic title")
        _non_empty(body, "topic body")
        with self._lock:
            if kb_article_id is not None:
                self._get("kb_article", kb_article_id)
            return self._create(
                "topic", "topic",
                {"title": title, "body": body,
                 "kb_article_id": kb_article_id, "enabled": True,
                 "hosted_here": False},
                actor, "ext_topic_create")

    def set_self_service_topic_enabled(self, actor, topic_id, enabled):
        """Enable or disable a topic record. Action: guide_write."""
        self._guard(actor, "guide_write", "ext_topic_update",
                    target=topic_id)
        if not isinstance(enabled, bool):
            raise ValidationError("enabled must be a bool")
        return self._update("topic", topic_id, {"enabled": enabled},
                            actor, "ext_topic_update")

    def get_self_service_topic(self, topic_id, actor=None):
        """One topic record. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_topic_read",
                         target=topic_id)
        return self._fetch("topic", topic_id)

    def list_self_service_topics(self, actor=None):
        """All topic records. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_topic_read")
        return self._list("topic")

    # ================================================================
    # Casework depth: chat / chatbot channel records
    # (entry: customer-service casework depth; stub form -- no
    # channel connects, reference_stub: True throughout)
    # ================================================================

    def register_chat_session(self, actor, case_id, channel_ref=None,
                              agent_ref=None):
        """Record a chat session against an existing core case.

        Action: interaction_write. Id prefix: chats-. Reference
        implementation: the session is a reported record; no chat
        channel connects and no transcript is held
        (``connected_here: False``).
        """
        self._guard(actor, "interaction_write", "ext_chat_session_register",
                    target=case_id)
        _string_or_none(channel_ref, "channel_ref")
        _string_or_none(agent_ref, "agent_ref")
        with self._lock:
            self._core_case(case_id)
            return self._create(
                "chat_session", "chats",
                {"case_id": case_id, "channel_ref": channel_ref,
                 "agent_ref": agent_ref, "reference_stub": True,
                 "connected_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_chat_session_register")

    def record_chat_outcome(self, actor, session_id, outcome):
        """Record a chat session's outcome, verbatim as reported.

        Action: interaction_write. Id prefix: chatr-. The outcome
        is the channel system's report, stored as supplied; no
        transcript exists in this build to summarize.
        """
        self._guard(actor, "interaction_write", "ext_chat_outcome_record",
                    target=session_id)
        _non_empty(outcome, "outcome")
        with self._lock:
            self._get("chat_session", session_id)
            return self._create(
                "chat_outcome", "chatr",
                {"session_id": session_id, "outcome": outcome,
                 "reference_stub": True, "held_here": False},
                actor, "ext_chat_outcome_record")

    def get_chat_session(self, session_id, actor=None):
        """One chat session record. Action: interaction_read."""
        self._guard_read(actor, "interaction_read", "ext_chat_session_read",
                         target=session_id)
        return self._fetch("chat_session", session_id)

    def list_chat_sessions(self, actor=None, case_id=None):
        """Chat session records, optionally for one case.

        Action: interaction_read.
        """
        self._guard_read(actor, "interaction_read", "ext_chat_session_read")
        if case_id is not None:
            return self._list("chat_session", case_id=case_id)
        return self._list("chat_session")

    def list_chat_outcomes(self, session_id, actor=None):
        """Outcome records for one chat session.

        Action: interaction_read.
        """
        self._guard_read(actor, "interaction_read", "ext_chat_session_read",
                         target=session_id)
        with self._lock:
            self._get("chat_session", session_id)
            return self._list("chat_outcome", session_id=session_id)

    # ================================================================
    # Guidance delivery runtime (stub-engine entry; reference
    # form throughout -- nothing is rendered or delivered)
    # ================================================================

    def register_guidance_session(self, actor, guide_id, contact_ref=None,
                                  account_id=None):
        """Record a guidance session against an existing core guide.

        Action: guide_write. Id prefix: gses-. Reference
        implementation: the session records that guidance was
        presented to a contact (opaque ``contact_ref``) as
        reported; the overlay runtime that would render it inside
        a host application is not built (``rendered_here: False``,
        ``delivered_here: False``). The guide's current version is
        snapshotted as data. When an account is named it must
        exist, and a ``contact_ref`` naming a core contact id must
        name a contact of that account -- the core's linkage
        discipline.
        """
        self._guard(actor, "guide_write", "ext_guidance_session_register",
                    target=guide_id)
        _string_or_none(contact_ref, "contact_ref")
        with self._lock:
            guide = self._core_guide(guide_id)
            if account_id is not None:
                self._core_account(account_id)
                if contact_ref is not None:
                    try:
                        contact = self._core_contact(contact_ref)
                    except NotFoundError:
                        contact = None
                    if (contact is not None
                            and contact["account_id"] != account_id):
                        raise ValidationError(
                            "contact %r does not belong to account %r"
                            % (contact_ref, account_id)
                        )
            return self._create(
                "guidance_session", "gses",
                {"guide_id": guide_id, "guide_version": guide["version"],
                 "contact_ref": contact_ref, "account_id": account_id,
                 "reference_stub": True, "rendered_here": False,
                 "delivered_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_guidance_session_register")

    def record_guidance_outcome(self, actor, session_id, outcome_label):
        """Record a guidance session outcome, verbatim as reported.

        Action: guide_write. Id prefix: gsout-. The label is the
        host application's report; nothing here observed the
        session (``observed_here: False``). A score-shaped label is
        refused: outcomes are labels, never measurements this
        build computes.
        """
        self._guard(actor, "guide_write", "ext_guidance_outcome_record",
                    target=session_id)
        _non_empty(outcome_label, "outcome_label")
        if outcome_label.strip().lower() in SCORE_KEYS:
            raise ValidationError(
                "outcome_label may not be a score-shaped label: %r"
                % (outcome_label,))
        with self._lock:
            self._get("guidance_session", session_id)
            return self._create(
                "guidance_outcome", "gsout",
                {"session_id": session_id, "outcome_label": outcome_label,
                 "reference_stub": True, "observed_here": False},
                actor, "ext_guidance_outcome_record")

    def get_guidance_session(self, session_id, actor=None):
        """One guidance session record. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_guidance_session_read",
                         target=session_id)
        return self._fetch("guidance_session", session_id)

    def list_guidance_sessions(self, actor=None, guide_id=None):
        """Guidance session records, optionally for one guide.

        Action: guide_read.
        """
        self._guard_read(actor, "guide_read", "ext_guidance_session_read")
        if guide_id is not None:
            return self._list("guidance_session", guide_id=guide_id)
        return self._list("guidance_session")

    def list_guidance_outcomes(self, session_id, actor=None):
        """Outcome records for one guidance session.

        Action: guide_read.
        """
        self._guard_read(actor, "guide_read", "ext_guidance_session_read",
                         target=session_id)
        with self._lock:
            self._get("guidance_session", session_id)
            return self._list("guidance_outcome", session_id=session_id)

    def register_authoring_definition(self, actor, name, guide_id=None,
                                      definition_text=None):
        """Record a codeless-authoring definition as data.

        Action: guide_write. Id prefix: authd-. Reference
        implementation: the definition text is held verbatim,
        exactly as the core holds module ``settings_text``; no
        authoring tool runs and no overlay is produced
        (``authored_here: False``).
        """
        self._guard(actor, "guide_write",
                    "ext_authoring_definition_register")
        _non_empty(name, "definition name")
        _string_or_none(definition_text, "definition_text")
        with self._lock:
            if guide_id is not None:
                self._core_guide(guide_id)
            return self._create(
                "authoring_definition", "authd",
                {"name": name, "guide_id": guide_id,
                 "definition_text": definition_text,
                 "reference_stub": True, "authored_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_authoring_definition_register")

    def get_authoring_definition(self, definition_id, actor=None):
        """One authoring definition record. Action: guide_read."""
        self._guard_read(actor, "guide_read",
                         "ext_authoring_definition_read",
                         target=definition_id)
        return self._fetch("authoring_definition", definition_id)

    def list_authoring_definitions(self, actor=None):
        """All authoring definition records. Action: guide_read."""
        self._guard_read(actor, "guide_read",
                         "ext_authoring_definition_read")
        return self._list("authoring_definition")

    # ================================================================
    # Gap-identification & adoption-analytics engines (stub-engine
    # entry; reference form -- nothing is collected or detected;
    # the analytics half lands as deterministic counts over
    # recorded records)
    # ================================================================

    def record_telemetry_report(self, actor, source_ref, period_label,
                                events_reported):
        """Record a telemetry report as reported by its source.

        Action: finding_write. Id prefix: telr-. Reference
        implementation: ``events_reported`` is the source system's
        own count, stored as data; no event was collected here
        (``collected_here: False``).
        """
        self._guard(actor, "finding_write", "ext_telemetry_report_record")
        _non_empty(source_ref, "source_ref")
        _non_empty(period_label, "period_label")
        _nonneg_int(events_reported, "events_reported")
        return self._create(
            "telemetry_report", "telr",
            {"source_ref": source_ref, "period_label": period_label,
             "events_reported": events_reported,
             "reference_stub": True, "collected_here": False},
            actor, "ext_telemetry_report_record")

    def list_telemetry_reports(self, actor=None, source_ref=None):
        """Telemetry report records. Action: finding_read."""
        self._guard_read(actor, "finding_read", "ext_telemetry_report_read")
        if source_ref is not None:
            return self._list("telemetry_report", source_ref=source_ref)
        return self._list("telemetry_report")

    def record_detection_report(self, actor, source_ref, title, detail=None,
                                severity="info", account_id=None):
        """Record a gap detection as reported by a source system.

        Action: finding_write. Id prefix: detr-. Reference
        implementation: the detection happened in the source
        system, elsewhere (``detected_here: False``); the report
        is finding-shaped data -- title, verbatim detail, severity
        from the core's vocabulary -- and it is NOT a core finding:
        recording one creates no core record of any kind. The
        core's finding registry remains the only path by which a
        finding comes to exist, and it is a human's record.
        """
        self._guard(actor, "finding_write", "ext_detection_report_record")
        _non_empty(source_ref, "source_ref")
        _non_empty(title, "detection title")
        _string_or_none(detail, "detection detail")
        _one_of(severity, KNOWN_SEVERITIES, SEVERITIES, "severity")
        with self._lock:
            if account_id is not None:
                self._core_account(account_id)
            return self._create(
                "detection_report", "detr",
                {"source_ref": source_ref, "title": title,
                 "detail": detail, "severity": severity,
                 "account_id": account_id, "reference_stub": True,
                 "detected_here": False},
                actor, "ext_detection_report_record")

    def list_detection_reports(self, actor=None, account_id=None):
        """Detection report records. Action: finding_read."""
        self._guard_read(actor, "finding_read", "ext_detection_report_read")
        if account_id is not None:
            return self._list("detection_report", account_id=account_id)
        return self._list("detection_report")

    def _guidance_outcome_counts(self, outcome_records):
        """Count recorded guidance outcomes by verbatim label.

        MUTATION DRILL NOTE: this is the single derivation point
        for the engagement report's guidance outcome distribution
        -- the batch's fresh negative control mutates it (an
        implementation that never counts must not produce the
        canonical distribution).
        """
        counts = {}
        for record in outcome_records:
            label = record["outcome_label"]
            counts[label] = counts.get(label, 0) + 1
        return counts

    def engagement_metrics(self, actor=None):
        """Deterministic engagement counts over recorded records.

        Action: report_read. Derived at read, stored nowhere:
        core interaction counts by channel and outcome, recorded
        guidance session/outcome counts (outcomes by their
        verbatim reported labels), and core finding counts by
        severity and status. Counts of records only -- no rate,
        average, or score is computed, mirroring the core report.
        """
        self._guard_read(actor, "report_read", "ext_engagement_metrics")
        with self._lock:
            interactions = self.store.list_interactions()
            by_channel = {}
            by_outcome = {}
            for interaction in interactions:
                channel = interaction["channel"]
                by_channel[channel] = by_channel.get(channel, 0) + 1
                outcome = interaction["outcome"]
                if outcome is None:
                    outcome = "none"
                by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
            sessions = self._list("guidance_session")
            outcomes = self._list("guidance_outcome")
            findings = self.store.list_findings()
            by_severity = {}
            by_finding_status = {}
            for finding in findings:
                severity = finding["severity"]
                by_severity[severity] = by_severity.get(severity, 0) + 1
                status = finding["status"]
                by_finding_status[status] = (
                    by_finding_status.get(status, 0) + 1)
            return {
                "method": "deterministic_counts_over_recorded_records",
                "derived": True,
                "interactions": {
                    "total": len(interactions),
                    "by_channel": by_channel,
                    "by_outcome": by_outcome,
                },
                "guidance": {
                    "sessions_recorded": len(sessions),
                    "outcomes_recorded": len(outcomes),
                    "by_outcome": self._guidance_outcome_counts(outcomes),
                },
                "findings": {
                    "total": len(findings),
                    "by_severity": by_severity,
                    "by_status": by_finding_status,
                },
            }

    # ================================================================
    # Customization & module engines (build-extension entry,
    # RE-JUDGED to reference form -- grounds in BATCH.md: the core
    # holds module settings verbatim and never executes them, and
    # an execution engine would have to break that invariant, so
    # the entry lands as execution-request records plus reported
    # outcomes and runtime parameter sets held as data, every
    # record labeled reference_stub: True)
    # ================================================================

    def request_module_execution(self, actor, module_id, parameters=None):
        """Record a request to execute a core module elsewhere.

        Action: config_write (admin, as module writes are). Id
        prefix: mexec-. Reference implementation: the request
        snapshots the module's label and version and holds its
        parameters as data; the module record itself is never
        touched and nothing executes (``executed_here: False``).
        The core's doctrine stands: module settings are stored
        verbatim, never run.
        """
        self._guard(actor, "config_write", "ext_module_execution_request",
                    target=module_id)
        parameters = _validate_parameters(parameters)
        with self._lock:
            module = self._core_module(module_id)
            return self._create(
                "module_execution", "mexec",
                {"module_id": module_id, "module_label": module["label"],
                 "module_version": module["version"],
                 "parameters": parameters, "reference_stub": True,
                 "executed_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_module_execution_request")

    def record_module_execution_report(self, actor, execution_id,
                                       outcome):
        """Record an execution outcome, verbatim as reported.

        Action: config_write. Id prefix: mexecr-. The outcome is
        the external runtime's report from the fixed vocabulary;
        the execution happened there, not here
        (``executed_here: False``).
        """
        self._guard(actor, "config_write",
                    "ext_module_execution_report", target=execution_id)
        _one_of(outcome, KNOWN_EXECUTION_REPORT_OUTCOMES,
                EXECUTION_REPORT_OUTCOMES, "outcome")
        with self._lock:
            self._get("module_execution", execution_id)
            return self._create(
                "module_execution_report", "mexecr",
                {"execution_id": execution_id, "outcome": outcome,
                 "reference_stub": True, "executed_here": False},
                actor, "ext_module_execution_report")

    def get_module_execution(self, execution_id, actor=None):
        """One module execution request record. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_module_execution_read",
                         target=execution_id)
        return self._fetch("module_execution", execution_id)

    def list_module_executions(self, actor=None, module_id=None):
        """Module execution request records. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_module_execution_read")
        if module_id is not None:
            return self._list("module_execution", module_id=module_id)
        return self._list("module_execution")

    def list_module_execution_reports(self, execution_id, actor=None):
        """Execution report records for one request.

        Action: config_read.
        """
        self._guard_read(actor, "config_read", "ext_module_execution_read",
                         target=execution_id)
        with self._lock:
            self._get("module_execution", execution_id)
            return self._list("module_execution_report",
                              execution_id=execution_id)

    def register_runtime_parameter_set(self, actor, module_id, parameters):
        """Record a codeless-configuration parameter set as data.

        Action: config_write (admin). Id prefix: rtps-. Reference
        implementation: the parameters a configuration runtime
        would apply are held as data beside the module record they
        name; nothing is applied (``applied_here: False``) and the
        core module record is never modified.
        """
        self._guard(actor, "config_write",
                    "ext_runtime_parameter_set_register", target=module_id)
        parameters = _validate_parameters(parameters, required=True)
        with self._lock:
            self._core_module(module_id)
            return self._create(
                "runtime_parameter_set", "rtps",
                {"module_id": module_id, "parameters": parameters,
                 "reference_stub": True, "applied_here": False,
                 "state": "recorded_reference_only"},
                actor, "ext_runtime_parameter_set_register")

    def get_runtime_parameter_set(self, set_id, actor=None):
        """One runtime parameter set record. Action: config_read."""
        self._guard_read(actor, "config_read",
                         "ext_runtime_parameter_set_read", target=set_id)
        return self._fetch("runtime_parameter_set", set_id)

    def list_runtime_parameter_sets(self, actor=None, module_id=None):
        """Runtime parameter set records. Action: config_read."""
        self._guard_read(actor, "config_read",
                         "ext_runtime_parameter_set_read")
        if module_id is not None:
            return self._list("runtime_parameter_set", module_id=module_id)
        return self._list("runtime_parameter_set")

    # ================================================================
    # Marketing-automation engines & email delivery (stub-engine
    # entry; reference form -- definitions held as data, outcomes
    # as reported; the registry never executes a flow and no
    # message is sent). Segments and flows are separate record
    # kinds: their ids never collide.
    # ================================================================

    def create_segment(self, actor, name, account_refs=None):
        """Record an audience segment as data. Action: guide_write.

        Id prefix: seg-. Reference implementation: the segment is
        a recorded list of opaque account references; no audience
        is targeted and no list is exported
        (``targeted_here: False``).
        """
        self._guard(actor, "guide_write", "ext_segment_create")
        _non_empty(name, "segment name")
        account_refs = _string_list(account_refs, "account_refs")
        return self._create(
            "segment", "seg",
            {"name": name, "account_refs": account_refs,
             "reference_stub": True, "targeted_here": False},
            actor, "ext_segment_create")

    def get_segment(self, segment_id, actor=None):
        """One segment record. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_segment_read",
                         target=segment_id)
        return self._fetch("segment", segment_id)

    def list_segments(self, actor=None):
        """All segment records. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_segment_read")
        return self._list("segment")

    def define_marketing_flow(self, actor, name, segment_id=None,
                              steps=None):
        """Record a marketing-flow definition as data.

        Action: guide_write. Id prefix: mflow-. Reference
        implementation: ``kind`` is the constant ``marketing_flow``
        and the steps are ``{step, channel}`` records held as
        data; the registry never executes a flow
        (``executed_here: False``), pinned by test: defining a
        flow and recording its outcome changes no core record and
        creates no segment.
        """
        self._guard(actor, "guide_write", "ext_marketing_flow_define")
        _non_empty(name, "flow name")
        steps = _validate_flow_steps(steps)
        with self._lock:
            if segment_id is not None:
                self._get("segment", segment_id)
            return self._create(
                "flow", "mflow",
                {"kind": "marketing_flow", "name": name,
                 "segment_id": segment_id, "steps": steps,
                 "reference_stub": True, "executed_here": False,
                 "state": "recorded_definition_only"},
                actor, "ext_marketing_flow_define")

    def record_flow_outcome(self, actor, flow_id, outcome_label,
                            delivered_count=None):
        """Record a flow outcome, verbatim as reported.

        Action: guide_write. Id prefix: mout-. ``delivered_count``
        is the delivery system's own reported count, stored as
        data; no message was sent here (``sent_here: False``).
        """
        self._guard(actor, "guide_write", "ext_flow_outcome_record",
                    target=flow_id)
        _non_empty(outcome_label, "outcome_label")
        if delivered_count is not None:
            _nonneg_int(delivered_count, "delivered_count")
        with self._lock:
            self._get("flow", flow_id)
            return self._create(
                "flow_outcome", "mout",
                {"flow_id": flow_id, "outcome_label": outcome_label,
                 "delivered_count": delivered_count,
                 "reference_stub": True, "sent_here": False},
                actor, "ext_flow_outcome_record")

    def get_marketing_flow(self, flow_id, actor=None):
        """One flow definition record. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_marketing_flow_read",
                         target=flow_id)
        return self._fetch("flow", flow_id)

    def list_marketing_flows(self, actor=None):
        """All flow definition records. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_marketing_flow_read")
        return self._list("flow")

    def list_flow_outcomes(self, flow_id, actor=None):
        """Outcome records for one flow. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_marketing_flow_read",
                         target=flow_id)
        with self._lock:
            self._get("flow", flow_id)
            return self._list("flow_outcome", flow_id=flow_id)

    # ================================================================
    # AI/ML models & scoring (stub-engine entry; reference form --
    # requests and reported results only; no model runs and no
    # score is computed, mirroring the core's by-design absence of
    # scores)
    # ================================================================

    def register_ai_request(self, actor, model_ref, purpose, case_id=None):
        """Record a request to an external model. Action: case_write.

        Id prefix: aireq-. Reference implementation: the request
        names the model by opaque ``model_ref`` and may bind an
        existing core case; there is deliberately no result or
        score parameter -- a result enters this build only as a
        reported record (``record_ai_report``), never as a value
        this build produces (``inference_here: False``).
        """
        self._guard(actor, "case_write", "ext_ai_request_register")
        _non_empty(model_ref, "model_ref")
        _non_empty(purpose, "purpose")
        with self._lock:
            if case_id is not None:
                self._core_case(case_id)
            return self._create(
                "ai_request", "aireq",
                {"model_ref": model_ref, "purpose": purpose,
                 "case_id": case_id, "reference_stub": True,
                 "inference_here": False,
                 "state": "recorded_request_only"},
                actor, "ext_ai_request_register")

    def record_ai_report(self, actor, request_id, outcome_label,
                         result_ref=None):
        """Record a model's reported outcome for a request.

        Action: case_write. Id prefix: air-. The outcome label is
        stored verbatim as the model's operator reported it; the
        result itself is named only by an opaque ``result_ref``
        and is never held here (``result_held_here: False``). A
        score-shaped outcome label is refused: reported outcomes
        are labels, and no scoring enters through this surface.
        """
        self._guard(actor, "case_write", "ext_ai_report_record",
                    target=request_id)
        _non_empty(outcome_label, "outcome_label")
        if outcome_label.strip().lower() in SCORE_KEYS:
            raise ValidationError(
                "outcome_label may not be a score-shaped label: %r"
                % (outcome_label,))
        _string_or_none(result_ref, "result_ref")
        with self._lock:
            self._get("ai_request", request_id)
            return self._create(
                "ai_report", "air",
                {"request_id": request_id, "outcome_label": outcome_label,
                 "result_ref": result_ref, "reference_stub": True,
                 "result_held_here": False},
                actor, "ext_ai_report_record")

    def record_ai_evaluation(self, actor, model_ref, metric_label,
                             metric_value):
        """Record a model evaluation figure as reported.

        Action: case_write. Id prefix: aieval-. Reference
        implementation: evaluations of a model happen in its own
        harness, elsewhere; the figure arrives here as reported
        data -- a number stored exactly as supplied, or a verbatim
        label string -- and nothing is computed from it
        (``computed_here: False``). Booleans and floats are
        rejected for numeric values, mirroring the house rule that
        recorded values are exact.
        """
        self._guard(actor, "case_write", "ext_ai_evaluation_record")
        _non_empty(model_ref, "model_ref")
        _non_empty(metric_label, "metric_label")
        if isinstance(metric_value, bool) or not isinstance(
                metric_value, (int, str)):
            raise ValidationError(
                "metric_value must be an integer or a verbatim label "
                "string")
        if isinstance(metric_value, str) and not metric_value.strip():
            raise ValidationError("metric_value must not be empty")
        return self._create(
            "ai_evaluation", "aieval",
            {"model_ref": model_ref, "metric_label": metric_label,
             "metric_value": metric_value, "reference_stub": True,
             "computed_here": False},
            actor, "ext_ai_evaluation_record")

    def get_ai_request(self, request_id, actor=None):
        """One AI request record. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_ai_request_read",
                         target=request_id)
        return self._fetch("ai_request", request_id)

    def list_ai_requests(self, actor=None, case_id=None):
        """AI request records, optionally for one case.

        Action: case_read.
        """
        self._guard_read(actor, "case_read", "ext_ai_request_read")
        if case_id is not None:
            return self._list("ai_request", case_id=case_id)
        return self._list("ai_request")

    def list_ai_reports(self, request_id, actor=None):
        """Report records for one AI request. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_ai_request_read",
                         target=request_id)
        with self._lock:
            self._get("ai_request", request_id)
            return self._list("ai_report", request_id=request_id)

    def list_ai_evaluations(self, actor=None, model_ref=None):
        """AI evaluation records. Action: case_read."""
        self._guard_read(actor, "case_read", "ext_ai_evaluation_read")
        if model_ref is not None:
            return self._list("ai_evaluation", model_ref=model_ref)
        return self._list("ai_evaluation")

    # ================================================================
    # Integration connector engines (stub-engine entry; reference
    # form -- sync receipts bound to core records, labeled
    # reference_transport: True; nothing is transmitted or synced.
    # The unions's recorded near-miss stands: the build asserts no
    # integration function of its own)
    # ================================================================

    def record_connector_sync(self, actor, connector_ref, direction,
                              records_reported, target_kind=None,
                              target_id=None):
        """Record a connector sync as reported by the connector.

        Action: config_write (admin, as configuration writes are).
        Id prefix: csync-. Reference implementation: the receipt
        may bind one existing core record (account, case, guide,
        finding, or module) as its target; ``records_reported``
        is the connector's own count, stored as data. Nothing was
        transmitted or synced here (``transmitted_here: False``,
        ``synced_here: False``), and the target record is never
        modified.
        """
        self._guard(actor, "config_write", "ext_connector_sync_record")
        _non_empty(connector_ref, "connector_ref")
        _one_of(direction, KNOWN_CONNECTOR_DIRECTIONS,
                CONNECTOR_DIRECTIONS, "direction")
        _nonneg_int(records_reported, "records_reported")
        if (target_kind is None) != (target_id is None):
            raise ValidationError(
                "target_kind and target_id must be given together")
        with self._lock:
            if target_kind is not None:
                _one_of(target_kind, KNOWN_CONNECTOR_TARGET_KINDS,
                        CONNECTOR_TARGET_KINDS, "target_kind")
                getter = {
                    "account": self.store.get_account,
                    "case": self.store.get_case,
                    "guide": self.store.get_guide,
                    "finding": self.store.get_finding,
                    "module": self.store.get_module,
                }[target_kind]
                getter(target_id)
            return self._create(
                "connector_sync", "csync",
                {"connector_ref": connector_ref, "direction": direction,
                 "records_reported": records_reported,
                 "target_kind": target_kind, "target_id": target_id,
                 "reference_stub": True, "reference_transport": True,
                 "transmitted_here": False, "synced_here": False},
                actor, "ext_connector_sync_record")

    def get_connector_sync(self, sync_id, actor=None):
        """One connector sync record. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_connector_sync_read",
                         target=sync_id)
        return self._fetch("connector_sync", sync_id)

    def list_connector_syncs(self, actor=None, connector_ref=None):
        """Connector sync records. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_connector_sync_read")
        if connector_ref is not None:
            return self._list("connector_sync", connector_ref=connector_ref)
        return self._list("connector_sync")

    def connector_catalog(self, actor=None):
        """Per-connector rollup of recorded sync receipts.

        Action: config_read. Derived at read, stored nowhere:
        sync counts and sums of the connectors' own reported
        record counts, by connector and direction. Sums of
        recorded values only -- nothing here measures a real
        integration.
        """
        self._guard_read(actor, "config_read", "ext_connector_catalog")
        with self._lock:
            syncs = self._list("connector_sync")
            by_ref = {}
            for sync in syncs:
                entry = by_ref.setdefault(
                    sync["connector_ref"],
                    {"connector_ref": sync["connector_ref"], "syncs": 0,
                     "records_reported_total": 0, "by_direction": {}})
                entry["syncs"] += 1
                entry["records_reported_total"] += sync["records_reported"]
                direction = sync["direction"]
                entry["by_direction"][direction] = (
                    entry["by_direction"].get(direction, 0) + 1)
            connectors = [by_ref[ref] for ref in sorted(by_ref)]
            return {
                "method": "recorded_sync_counts",
                "derived": True,
                "connectors": connectors,
                "total_syncs": len(syncs),
                "total_records_reported": sum(
                    s["records_reported"] for s in syncs),
            }

    # ================================================================
    # Extension summary (derived)
    # ================================================================

    def extension_summary(self, actor=None):
        """Counts of extension records by kind. Action: report_read.

        Derived at read, stored nowhere. Counts of records only.
        """
        self._guard_read(actor, "report_read", "ext_summary")
        with self._lock:
            counts = {}
            for kind, _record_id in self._order:
                counts[kind] = counts.get(kind, 0) + 1
            return {
                "method": "extension_record_counts",
                "derived": True,
                "by_kind": counts,
                "total": len(self._order),
            }
