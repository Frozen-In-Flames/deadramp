"""Final GAPS batch extensions for the CRM L1 singleton build
(Remainder Singleton 56).

Clean-room, standard-library-only records/derivation extensions for
the 8 open Extended entries this singleton's GAPS.md section
carries: 6 drafted ``build-extension`` and 2 drafted ``stub-engine``
in ``../../gaps-batch/inventory.json`` (idx 683-690). See
``BATCH.md`` in the group directory for the per-entry disposition,
including four re-judgments recorded there under DECISION.md
qualification 1.

The forms are the CRM L2 batch unit's adjudicated forms
(``groups/crm-l2/BATCH.md``), mirrored at this tier: the substrate
code is byte-identical across the category's tiers, and the same
records form carries the same closure token here as at Moderate.
The baseline claimed is this tier's own (Low / LI-SaaS; audit on
the FedRAMP Low side only, AU-2/AU-3) -- nothing in this module
imports a Moderate or High apparatus.

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

  - channel surfaces -> ``config_write`` / ``config_read``
    (platform configuration records);
  - the experience overview, the listening summary, and the
    extension summary -> ``report_read``;
  - agent desktops and self-service topics -> ``guide_write`` /
    ``guide_read`` (guidance-content genus);
  - care chat session records -> ``interaction_write`` /
    ``interaction_read``;
  - social content items, publication schedules and outcomes,
    advertising campaign definitions and outcomes, orchestration
    flow definitions and outcomes, marketing segments, flow
    definitions and flow outcomes -> ``guide_write`` /
    ``guide_read`` (content / campaign-shaped records ride the
    content genus, as in the L2 unit);
  - listening topic definitions and listening reports ->
    ``finding_write`` / ``finding_read`` (finding-genus reported
    records, as in the L2 unit);
  - AI request/report/evaluation records -> ``case_write`` /
    ``case_read`` (they bind cases; case-adjacent operational
    records, as in the L2 unit).

- Every successful extension mutation is recorded on the core
  store's audit log with an action name prefixed ``ext_``. If the
  audit write raises, the record insertion and its id roll back
  before the error propagates: no extension record exists whose
  audit entry does not.
- All references to people, systems, and domains are opaque
  ``*_ref`` strings, exactly as in the core. Where a record binds
  a person it names a core contact by id or carries an opaque
  ``*_ref`` string; no record shape in this module can hold a real
  name, email, phone number, social handle, or any other
  identifier, and none can hold message or post content, money in
  motion, or a computed score.
- Derived values are derived at read and never stored: the
  experience overview's channel/outcome counts, the listening
  summary's reported-mention totals, the extension summary.
  Stored records carry no derived key; tests pin that.
- Nothing here executes against an external system. The engine
  families ship as labeled reference implementations: every record
  they create carries ``reference_stub: True`` (publication and
  advertising outcome receipts additionally carry
  ``reference_transport: True``), and no post is published, no
  conversation is listened to, no campaign executes or is
  optimized, no flow executes, no message is sent, and no model
  is run. Two surfaces close ``built`` in the records form: the
  CXM platform entry, whose own text bounds the deliverable to
  the platform "over the records substrate" (channel-surface
  definition records plus a derived cross-channel overview; the
  operating platform itself is not built), and care engagement
  depth (desktop compositions, self-service topics, and labeled
  chat session records bound to core cases, the L2 casework
  form). The grounds for each disposition are in ``BATCH.md``.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import CHANNELS

# Channel labels a surface or content record may name: the core
# interaction channels plus the fork's own channel words from its
# description (social, messaging, email and web channels; email is
# already a core channel). Labels are data; naming a channel here
# connects nothing.
SURFACE_CHANNELS = tuple(dict.fromkeys(
    list(CHANNELS) + ["social", "web", "messaging", "advertising"]))
KNOWN_SURFACE_CHANNELS = frozenset(SURFACE_CHANNELS)

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


def _validate_flow_steps(steps):
    """Validate flow step records: {step, channel} data."""
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


def _check_outcome_label(outcome_label):
    """Outcome labels are verbatim reports, never score-shaped."""
    _non_empty(outcome_label, "outcome_label")
    if outcome_label.strip().lower() in SCORE_KEYS:
        raise ValidationError(
            "outcome_label may not be a score-shaped label: %r"
            % (outcome_label,))
    return outcome_label


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

    def _core_case(self, case_id):
        return self.store.get_case(case_id)

    def _core_guide(self, guide_id):
        return self.store.get_guide(guide_id)

    # ================================================================
    # Unified CXM platform (build-extension entry, closed built in
    # the records form its own text bounds: "the unified platform
    # itself, over the records substrate" -- channel-surface
    # definition records plus a cross-channel overview derived at
    # read over the substrate's own records. The operating /
    # hosted platform itself is not built; PLATFORM-LAYER.md
    # decision 6 stands beside this closure.)
    # ================================================================

    def register_channel_surface(self, actor, name, channel,
                                 surface_ref=None):
        """Record a channel surface the platform operates over.

        Action: config_write. Id prefix: surface-. A definition
        record: the surface is named as data (an opaque
        ``surface_ref`` and a channel label); nothing is hosted
        or operated here (``operated_here: False``,
        ``hosted_here: False``).
        """
        self._guard(actor, "config_write", "ext_channel_surface_register")
        _non_empty(name, "surface name")
        _one_of(channel, KNOWN_SURFACE_CHANNELS, SURFACE_CHANNELS,
                "channel")
        _string_or_none(surface_ref, "surface_ref")
        return self._create(
            "channel_surface", "surface",
            {"name": name, "channel": channel,
             "surface_ref": surface_ref, "operated_here": False,
             "hosted_here": False},
            actor, "ext_channel_surface_register")

    def get_channel_surface(self, surface_id, actor=None):
        """One channel surface record. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_channel_surface_read",
                         target=surface_id)
        return self._fetch("channel_surface", surface_id)

    def list_channel_surfaces(self, actor=None):
        """All channel surface records. Action: config_read."""
        self._guard_read(actor, "config_read", "ext_channel_surface_read")
        return self._list("channel_surface")

    def _channel_counts(self, interactions):
        """Count core interactions by their recorded channel.

        MUTATION DRILL NOTE: this is the single derivation point
        for the experience overview's by-channel distribution --
        the batch's fresh negative control mutates it (an
        implementation that never counts must not produce the
        canonical distribution).
        """
        counts = {}
        for interaction in interactions:
            channel = interaction["channel"]
            counts[channel] = counts.get(channel, 0) + 1
        return counts

    def experience_overview(self, actor=None):
        """The unified cross-channel view, derived at read.

        Action: report_read. Deterministic counts over the
        substrate's own records only: core interactions by channel
        and by verbatim outcome, core case and registry totals,
        registered channel surfaces, and extension record totals.
        Counts of records only -- no rate, average, engagement
        measure, or score is computed, and nothing about a real
        platform is operated or observed here
        (``platform_operated_here: False``).
        """
        self._guard_read(actor, "report_read", "ext_experience_overview")
        with self._lock:
            interactions = self.store.list_interactions()
            outcome_counts = {}
            for interaction in interactions:
                outcome = interaction["outcome"]
                if outcome is None:
                    outcome = "none"
                outcome_counts[outcome] = (
                    outcome_counts.get(outcome, 0) + 1)
            return {
                "method": "deterministic_counts_over_recorded_records",
                "derived": True,
                "platform_operated_here": False,
                "interactions": {
                    "total": len(interactions),
                    "by_channel": self._channel_counts(interactions),
                    "by_outcome": outcome_counts,
                },
                "cases": {"total": len(self.store.list_cases())},
                "accounts": {"total": len(self.store.list_accounts())},
                "channel_surfaces": {
                    "total": len(self._list("channel_surface"))},
                "extension_records": {"total": len(self._order)},
            }

    # ================================================================
    # Social media management & publishing engine (build-extension
    # entry, RE-JUDGED to reference form -- grounds in BATCH.md:
    # publishing is execution against external social networks,
    # and post content cannot be held under the privacy rule, so
    # the entry lands as content records naming posts by opaque
    # reference, schedule definitions held as data, and reported
    # publication outcomes; nothing is published)
    # ================================================================

    def register_content_item(self, actor, channel, content_ref,
                              label=None):
        """Record a social content item by opaque reference.

        Action: guide_write. Id prefix: post-. Reference
        implementation: the item names a post held elsewhere by
        ``content_ref``; the content itself is never held here
        (``content_held_here: False``) -- there is no parameter
        that could carry it -- and nothing is published
        (``published_here: False``).
        """
        self._guard(actor, "guide_write", "ext_content_item_register")
        _one_of(channel, KNOWN_SURFACE_CHANNELS, SURFACE_CHANNELS,
                "channel")
        _non_empty(content_ref, "content_ref")
        _string_or_none(label, "label")
        return self._create(
            "content_item", "post",
            {"channel": channel, "content_ref": content_ref,
             "label": label, "reference_stub": True,
             "content_held_here": False, "published_here": False,
             "state": "recorded_reference_only"},
            actor, "ext_content_item_register")

    def get_content_item(self, item_id, actor=None):
        """One content item record. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_content_item_read",
                         target=item_id)
        return self._fetch("content_item", item_id)

    def list_content_items(self, actor=None, channel=None):
        """Content item records. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_content_item_read")
        if channel is not None:
            return self._list("content_item", channel=channel)
        return self._list("content_item")

    def define_publication_schedule(self, actor, name, item_ids=None,
                                    cadence_label=None):
        """Record a publication schedule definition as data.

        Action: guide_write. Id prefix: sched-. Reference
        implementation: the schedule names existing content item
        records and a verbatim cadence label; the registry never
        fires it (``executed_here: False``) and no post is
        published by recording one.
        """
        self._guard(actor, "guide_write",
                    "ext_publication_schedule_define")
        _non_empty(name, "schedule name")
        item_ids = _string_list(item_ids, "item_ids")
        _string_or_none(cadence_label, "cadence_label")
        with self._lock:
            for item_id in item_ids:
                self._get("content_item", item_id)
            return self._create(
                "publication_schedule", "sched",
                {"name": name, "item_ids": item_ids,
                 "cadence_label": cadence_label,
                 "reference_stub": True, "executed_here": False,
                 "state": "recorded_definition_only"},
                actor, "ext_publication_schedule_define")

    def get_publication_schedule(self, schedule_id, actor=None):
        """One schedule definition record. Action: guide_read."""
        self._guard_read(actor, "guide_read",
                         "ext_publication_schedule_read",
                         target=schedule_id)
        return self._fetch("publication_schedule", schedule_id)

    def list_publication_schedules(self, actor=None):
        """All schedule definition records. Action: guide_read."""
        self._guard_read(actor, "guide_read",
                         "ext_publication_schedule_read")
        return self._list("publication_schedule")

    def record_publication_outcome(self, actor, item_id, outcome_label,
                                   reach_reported=None):
        """Record a publication outcome, verbatim as reported.

        Action: guide_write. Id prefix: pubr-. ``reach_reported``
        is the channel's own reported figure, stored as data; the
        publication happened on the channel, not here
        (``published_here: False``).
        """
        self._guard(actor, "guide_write", "ext_publication_outcome_record",
                    target=item_id)
        _check_outcome_label(outcome_label)
        if reach_reported is not None:
            _nonneg_int(reach_reported, "reach_reported")
        with self._lock:
            self._get("content_item", item_id)
            return self._create(
                "publication_outcome", "pubr",
                {"item_id": item_id, "outcome_label": outcome_label,
                 "reach_reported": reach_reported,
                 "reference_stub": True, "reference_transport": True,
                 "published_here": False},
                actor, "ext_publication_outcome_record")

    def list_publication_outcomes(self, item_id, actor=None):
        """Outcome records for one content item. Action: guide_read."""
        self._guard_read(actor, "guide_read",
                         "ext_publication_outcome_read", target=item_id)
        with self._lock:
            self._get("content_item", item_id)
            return self._list("publication_outcome", item_id=item_id)

    # ================================================================
    # Social listening & research analytics engine (stub-engine
    # entry, as drafted; reference form -- nothing is listened
    # to, and the analytics half lands as deterministic counts
    # and sums of reported figures over recorded records)
    # ================================================================

    def define_listening_topic(self, actor, name, topic_ref=None,
                               definition_text=None):
        """Record a listening topic definition as data.

        Action: finding_write. Id prefix: ltopic-. Reference
        implementation: the definition is held verbatim as data,
        exactly as the core holds configuration text; no
        conversation is monitored (``listened_here: False``).
        """
        self._guard(actor, "finding_write", "ext_listening_topic_define")
        _non_empty(name, "topic name")
        _string_or_none(topic_ref, "topic_ref")
        _string_or_none(definition_text, "definition_text")
        return self._create(
            "listening_topic", "ltopic",
            {"name": name, "topic_ref": topic_ref,
             "definition_text": definition_text,
             "reference_stub": True, "listened_here": False,
             "state": "recorded_definition_only"},
            actor, "ext_listening_topic_define")

    def get_listening_topic(self, topic_id, actor=None):
        """One listening topic record. Action: finding_read."""
        self._guard_read(actor, "finding_read", "ext_listening_topic_read",
                         target=topic_id)
        return self._fetch("listening_topic", topic_id)

    def list_listening_topics(self, actor=None):
        """All listening topic records. Action: finding_read."""
        self._guard_read(actor, "finding_read", "ext_listening_topic_read")
        return self._list("listening_topic")

    def record_listening_report(self, actor, topic_id, title, detail=None,
                                mentions_reported=None):
        """Record a listening insight as reported by its source.

        Action: finding_write. Id prefix: lrep-. Reference
        implementation: the listening happened in the source
        system, elsewhere (``collected_here: False``); the report
        is verbatim reported data and it is NOT a core finding:
        recording one creates no core record of any kind. The
        core's finding registry remains the only path by which a
        finding comes to exist, and it is a human's record.
        ``mentions_reported`` is the source's own count, stored
        as data.
        """
        self._guard(actor, "finding_write", "ext_listening_report_record",
                    target=topic_id)
        _non_empty(title, "report title")
        _string_or_none(detail, "report detail")
        if mentions_reported is not None:
            _nonneg_int(mentions_reported, "mentions_reported")
        with self._lock:
            self._get("listening_topic", topic_id)
            return self._create(
                "listening_report", "lrep",
                {"topic_id": topic_id, "title": title,
                 "detail": detail,
                 "mentions_reported": mentions_reported,
                 "reference_stub": True, "collected_here": False},
                actor, "ext_listening_report_record")

    def list_listening_reports(self, actor=None, topic_id=None):
        """Listening report records. Action: finding_read."""
        self._guard_read(actor, "finding_read", "ext_listening_report_read")
        if topic_id is not None:
            return self._list("listening_report", topic_id=topic_id)
        return self._list("listening_report")

    def listening_summary(self, actor=None):
        """Deterministic listening rollup, derived at read.

        Action: report_read. Counts of recorded topics and
        reports, and the sum of the sources' own reported mention
        figures. Sums of recorded values only -- no sentiment,
        trend, or insight is computed here; research analytics
        beyond this ceiling is the engine this entry names, and
        it is not built.
        """
        self._guard_read(actor, "report_read", "ext_listening_summary")
        with self._lock:
            topics = self._list("listening_topic")
            reports = self._list("listening_report")
            mentions_total = 0
            for report in reports:
                if report["mentions_reported"] is not None:
                    mentions_total += report["mentions_reported"]
            return {
                "method": "recorded_report_counts",
                "derived": True,
                "topics": len(topics),
                "reports": len(reports),
                "mentions_reported_total": mentions_total,
            }

    # ================================================================
    # Advertising campaign management engine (build-extension
    # entry, RE-JUDGED to reference form -- grounds in BATCH.md:
    # paid campaign execution and optimization run against
    # external advertising networks; the entry lands as campaign
    # definitions held as data plus reported outcomes)
    # ================================================================

    def define_ad_campaign(self, actor, name, channels=None,
                           budget_cents=None, segment_id=None):
        """Record an advertising campaign definition as data.

        Action: guide_write. Id prefix: adcamp-. Reference
        implementation: ``budget_cents`` is the campaign's
        recorded planned figure (integer cents, stored as data;
        floats are rejected -- recorded values are exact); no
        money moves (``spent_here: False``), no campaign executes
        (``executed_here: False``), and nothing is optimized
        (``optimized_here: False``). May name a recorded segment.
        """
        self._guard(actor, "guide_write", "ext_ad_campaign_define")
        _non_empty(name, "campaign name")
        channels = _string_list(channels, "channels")
        for channel in channels:
            _one_of(channel, KNOWN_SURFACE_CHANNELS, SURFACE_CHANNELS,
                    "channel")
        if budget_cents is not None:
            _nonneg_int(budget_cents, "budget_cents")
        with self._lock:
            if segment_id is not None:
                self._get("segment", segment_id)
            return self._create(
                "ad_campaign", "adcamp",
                {"name": name, "channels": channels,
                 "budget_cents": budget_cents, "segment_id": segment_id,
                 "reference_stub": True, "executed_here": False,
                 "optimized_here": False, "spent_here": False,
                 "state": "recorded_definition_only"},
                actor, "ext_ad_campaign_define")

    def get_ad_campaign(self, campaign_id, actor=None):
        """One ad campaign definition record. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_ad_campaign_read",
                         target=campaign_id)
        return self._fetch("ad_campaign", campaign_id)

    def list_ad_campaigns(self, actor=None):
        """All ad campaign definition records. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_ad_campaign_read")
        return self._list("ad_campaign")

    def record_ad_outcome(self, actor, campaign_id, outcome_label,
                          impressions_reported=None,
                          clicks_reported=None):
        """Record an ad campaign outcome, verbatim as reported.

        Action: guide_write. Id prefix: adout-. The reported
        figures are the advertising network's own counts, stored
        as data; the campaign ran there, not here
        (``executed_here: False``).
        """
        self._guard(actor, "guide_write", "ext_ad_outcome_record",
                    target=campaign_id)
        _check_outcome_label(outcome_label)
        if impressions_reported is not None:
            _nonneg_int(impressions_reported, "impressions_reported")
        if clicks_reported is not None:
            _nonneg_int(clicks_reported, "clicks_reported")
        with self._lock:
            self._get("ad_campaign", campaign_id)
            return self._create(
                "ad_outcome", "adout",
                {"campaign_id": campaign_id,
                 "outcome_label": outcome_label,
                 "impressions_reported": impressions_reported,
                 "clicks_reported": clicks_reported,
                 "reference_stub": True, "reference_transport": True,
                 "executed_here": False},
                actor, "ext_ad_outcome_record")

    def list_ad_outcomes(self, campaign_id, actor=None):
        """Outcome records for one ad campaign. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_ad_outcome_read",
                         target=campaign_id)
        with self._lock:
            self._get("ad_campaign", campaign_id)
            return self._list("ad_outcome", campaign_id=campaign_id)

    # ================================================================
    # Care engagement depth (build-extension entry, as drafted;
    # the L2 casework form -- agent desktop compositions and
    # self-service topics as records, chat sessions as labeled
    # reference records bound to core cases)
    # ================================================================

    def create_self_service_topic(self, actor, title, body,
                                  guide_id=None):
        """Record a self-service portal topic. Action: guide_write.

        Id prefix: topic-. The topic is content data a portal
        would present, optionally bound to an existing core
        guide; no portal is hosted (``hosted_here: False``).
        """
        self._guard(actor, "guide_write", "ext_topic_create")
        _non_empty(title, "topic title")
        _non_empty(body, "topic body")
        with self._lock:
            if guide_id is not None:
                self._core_guide(guide_id)
            return self._create(
                "topic", "topic",
                {"title": title, "body": body, "guide_id": guide_id,
                 "enabled": True, "hosted_here": False},
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

    def create_agent_desktop(self, actor, name, case_queue_ref=None,
                             guide_ids=None, topic_ids=None):
        """Record a care agent-desktop composition.

        Action: guide_write. Id prefix: desk-. A desktop record
        names the case queue (opaque ref) and the guide/topic
        records a care desktop would compose; referenced records
        must exist. The desktop itself -- a live agent workspace
        -- is not built, and the record says so
        (``composed_here: False``).
        """
        self._guard(actor, "guide_write", "ext_desktop_create")
        _non_empty(name, "desktop name")
        _string_or_none(case_queue_ref, "case_queue_ref")
        guide_ids = _string_list(guide_ids, "guide_ids")
        topic_ids = _string_list(topic_ids, "topic_ids")
        with self._lock:
            for guide_id in guide_ids:
                self._core_guide(guide_id)
            for topic_id in topic_ids:
                self._get("topic", topic_id)
            return self._create(
                "desktop", "desk",
                {"name": name, "case_queue_ref": case_queue_ref,
                 "guide_ids": guide_ids, "topic_ids": topic_ids,
                 "composed_here": False},
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

    def register_chat_session(self, actor, case_id, channel_ref=None,
                              agent_ref=None):
        """Record a care chat session against an existing core case.

        Action: interaction_write. Id prefix: chats-. Reference
        record inside the built entry (the L2 casework form): the
        session is a reported record; no chat channel connects and
        no transcript is held (``connected_here: False``).
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
        """Record a care chat session's outcome, verbatim as reported.

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
    # Engagement & messaging orchestration engine (stub-engine
    # entry, as drafted; reference form -- definitions held as
    # data, outcomes as reported; the registry never executes a
    # flow and no message is sent). Orchestration flows and
    # marketing flows are separate record kinds: their ids never
    # collide.
    # ================================================================

    def define_orchestration_flow(self, actor, name, segment_id=None,
                                  steps=None):
        """Record an orchestration-flow definition as data.

        Action: guide_write. Id prefix: oflow-. Reference
        implementation: ``kind`` is the constant
        ``orchestration_flow`` and the steps are ``{step,
        channel}`` records held as data; the registry never
        executes a flow (``executed_here: False``).
        """
        self._guard(actor, "guide_write", "ext_orchestration_flow_define")
        _non_empty(name, "flow name")
        steps = _validate_flow_steps(steps)
        with self._lock:
            if segment_id is not None:
                self._get("segment", segment_id)
            return self._create(
                "orchestration_flow", "oflow",
                {"kind": "orchestration_flow", "name": name,
                 "segment_id": segment_id, "steps": steps,
                 "reference_stub": True, "executed_here": False,
                 "state": "recorded_definition_only"},
                actor, "ext_orchestration_flow_define")

    def record_orchestration_outcome(self, actor, flow_id, outcome_label,
                                     delivered_count=None):
        """Record an orchestration outcome, verbatim as reported.

        Action: guide_write. Id prefix: oout-. ``delivered_count``
        is the messaging system's own reported count, stored as
        data; no message was sent here (``sent_here: False``).
        """
        self._guard(actor, "guide_write",
                    "ext_orchestration_outcome_record", target=flow_id)
        _check_outcome_label(outcome_label)
        if delivered_count is not None:
            _nonneg_int(delivered_count, "delivered_count")
        with self._lock:
            self._get("orchestration_flow", flow_id)
            return self._create(
                "orchestration_outcome", "oout",
                {"flow_id": flow_id, "outcome_label": outcome_label,
                 "delivered_count": delivered_count,
                 "reference_stub": True, "sent_here": False},
                actor, "ext_orchestration_outcome_record")

    def get_orchestration_flow(self, flow_id, actor=None):
        """One orchestration flow record. Action: guide_read."""
        self._guard_read(actor, "guide_read", "ext_orchestration_flow_read",
                         target=flow_id)
        return self._fetch("orchestration_flow", flow_id)

    def list_orchestration_flows(self, actor=None):
        """All orchestration flow records. Action: guide_read."""
        self._guard_read(actor, "guide_read",
                         "ext_orchestration_flow_read")
        return self._list("orchestration_flow")

    def list_orchestration_outcomes(self, flow_id, actor=None):
        """Outcome records for one orchestration flow.

        Action: guide_read.
        """
        self._guard_read(actor, "guide_read",
                         "ext_orchestration_flow_read", target=flow_id)
        with self._lock:
            self._get("orchestration_flow", flow_id)
            return self._list("orchestration_outcome", flow_id=flow_id)

    # ================================================================
    # Marketing platform functions (build-extension entry,
    # RE-JUDGED to reference form -- grounds in BATCH.md: the
    # fork's marketing product as an engine; the identical
    # records form closed reference in the L2 unit's
    # marketing-automation entry, and the same substrate cannot
    # carry a different token for the same form. Segments and
    # flows are separate record kinds: their ids never collide.)
    # ================================================================

    def create_segment(self, actor, name, account_refs=None):
        """Record an audience segment as data. Action: guide_write.

        Id prefix: seg-. Reference implementation: the segment is
        a recorded list of opaque account references; no audience
        is targeted and no list is exported
        (``targeted_here: False``). Segment records retire no part
        of the category's claim-level campaigns/audience absence,
        which stands as the spec records it.
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
        _check_outcome_label(outcome_label)
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
    # AI-backed core platform (build-extension entry, RE-JUDGED
    # to reference form -- grounds in BATCH.md: the entry's own
    # text records that the family is Extended in this category
    # and stays Extended and that the build implements no AI;
    # the fork's one claim asserts an AI-backed platform and
    # describes no scoring, model, or ML function. The entry
    # lands in the L2 unit's AI form: requests and reported
    # results only; no model runs and no score is computed,
    # mirroring the core's by-design absence of scores)
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
        _check_outcome_label(outcome_label)
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
