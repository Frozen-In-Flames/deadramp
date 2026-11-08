"""Final GAPS batch — second unit: the Remainder Addition entry
for the Customer Service L1 merged build (Group 26).

One new module for the one OPEN entry of the GAPS.md section
"Remainder Addition — Customer Service L1 (+1 fork)": proactive
engagement & outreach, asserted in substance by the addition fork's
(Zendesk's) own words — "proactive engagement" — with no taxonomy
family covering outreach. See ``BATCH-ADDITION.md`` in the group
directory for the disposition.

The form follows this group's own first batch unit's adjudicated
notification precedent: outreach *sending* is transport and lands
as ``reference_transport`` records with ``sent_here: False``; what
is built here is the records layer an outreach function runs on —
campaign definitions whose trigger and audience terms are held as
data and never evaluated, suppression (opt-out) records with a
guard seam, outreach attempt records against registered core
requesters, and outcome reports stored verbatim as a transport
elsewhere reported them. Nothing in this module sends, evaluates
a campaign trigger, or computes an engagement figure: views and
summaries are counts over this surface's own records, derived at
read, and no rate, ratio, percentage, or score is representable
anywhere on it.

Tier discipline is this group's, inherited from the first unit:
the audit log is this tier's plain append-only log (no hash
chain, no lockout, no auditor role), the role matrix is this
group's (admin / agent / viewer), and RBAC goes through
:mod:`custsvc.access` exactly as the core enforces it — each
operation maps onto an existing core action, checked before any
state change or id allocation for User-like actors, with denied
attempts recorded on the core audit log as ``exta_<action>:denied``.
Every successful mutation lands on the core audit log as an
``exta_*`` action; if the audit write raises, the record insertion
and its id roll back before the error propagates.

Privacy discipline is the category's: people are named only by the
core's registered opaque requester refs (an unregistered ref is
refused everywhere on this surface, so the pinned requester shape
— which cannot hold a phone number, email address, or real
identifier — governs outreach targets too), and no signature on
this surface can accept message content: passing ``message=``,
``body=``, or ``content=`` raises ``TypeError`` before any state
change, because no such parameter exists.
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

# The three outreach forms the addition addendum names in its own
# words (campaigns, nudges, re-engagement), held as data.
CAMPAIGN_KINDS = ("campaign", "nudge", "reengagement")
KNOWN_CAMPAIGN_KINDS = frozenset(CAMPAIGN_KINDS)
OUTREACH_REPORT_OUTCOMES = (
    "reported_delivered",
    "reported_failed",
    "reported_bounced",
    "reported_engaged",
    "reported_opted_out",
)
KNOWN_OUTREACH_REPORT_OUTCOMES = frozenset(OUTREACH_REPORT_OUTCOMES)


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError("%s must be one of %s" % (what, ", ".join(names)))
    return value


class CustsvcExtensionsAddition:
    """Second GAPS-batch extension surface over a core CustsvcStore.

    An independent wrapper: its records, counters, and audit action
    names (``exta_``) are its own, and it writes no state in the
    core store or in the first batch unit's extension surface.
    """

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers (mirroring the first unit's machinery) ----

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
        """Enforce a write permission, auditing a denial."""
        try:
            if actor is None:
                raise PermissionDenied(
                    "permission denied: no user supplied for %r" % (core_action,)
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
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _iso(_utc_now())
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed, as in the first unit: an operation
                # whose audit write fails does not proceed — the
                # insertion and the id roll back before the error
                # propagates.
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
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

    def _core_case(self, case_id, actor):
        """Return the core case view (NotFoundError if absent)."""
        return self.store.get_case(case_id, actor)

    def _core_requester_ref(self, ref, actor):
        """Return the core requester for an opaque ref."""
        return self.store.get_requester_by_ref(ref, actor)

    # -- proactive engagement & outreach (Remainder Addition entry) --
    #
    # Campaign definitions, suppression records, outreach attempt
    # records, and verbatim outcome reports. A campaign's trigger
    # and audience terms are held as data and are NEVER evaluated:
    # defining a campaign creates no attempt and touches no case —
    # attempts exist only when an operator records one. Sending is
    # transport, performed elsewhere: every attempt and report
    # carries ``reference_transport: True`` and ``sent_here: False``.

    def create_campaign(self, name, kind, channel_label, trigger_label,
                        actor, segment_ref=None, note=None):
        """Create an outreach campaign definition record.

        ``kind`` is one of the outreach forms the addition
        addendum names (campaign / nudge / reengagement).
        ``channel_label`` and ``trigger_label`` are the campaign's
        recorded terms, held as data: the trigger is never
        evaluated and the channel is never connected to.
        ``segment_ref`` is an optional opaque audience-segment
        reference, held as data and never resolved.
        """
        self._guard(actor, "case_write", "exta_campaign_create")
        _non_empty(name, "name")
        _one_of(kind, KNOWN_CAMPAIGN_KINDS, CAMPAIGN_KINDS, "kind")
        _non_empty(channel_label, "channel_label")
        _non_empty(trigger_label, "trigger_label")
        _string_or_none(segment_ref, "segment_ref")
        _string_or_none(note, "note")
        return self._create(
            "campaign", "cmp",
            {"name": name, "kind": kind,
             "channel_label": channel_label,
             "trigger_label": trigger_label,
             "segment_ref": segment_ref, "note": note,
             "evaluated_here": False, "sends_here": False,
             "state": "definition_only"},
            actor, "exta_campaign_create")

    def get_campaign(self, campaign_id, actor):
        self._guard_read(actor, "case_read", "exta_campaign_get",
                         target=campaign_id)
        return self._fetch("campaign", campaign_id)

    def list_campaigns(self, actor):
        self._guard_read(actor, "case_read", "exta_campaign_list")
        return self._list("campaign")

    def record_suppression(self, requester_ref, actor, campaign_id=None,
                           note=None):
        """Record that a requester is opted out of outreach.

        The requester must already be registered in the core, by
        opaque ref; ``campaign_id`` scopes the opt-out to one
        campaign, or is None for all campaigns on this surface.
        An exact duplicate (same requester, same scope) is
        refused. A suppression is a record about future attempts;
        recording one sends nothing and changes no core state.
        """
        self._guard(actor, "case_write", "exta_suppression_record")
        _string_or_none(note, "note")
        self._core_requester_ref(requester_ref, actor)
        if campaign_id is not None:
            self._get("campaign", campaign_id)
        for existing in self._list("suppression"):
            if (existing["requester_ref"] == requester_ref
                    and existing["campaign_id"] == campaign_id):
                raise ValidationError(
                    "requester %r is already suppressed for scope %r"
                    % (requester_ref, campaign_id))
        return self._create(
            "suppression", "sup",
            {"requester_ref": requester_ref,
             "campaign_id": campaign_id, "note": note},
            actor, "exta_suppression_record")

    def list_suppressions(self, actor, requester_ref=None, campaign_id=None):
        self._guard_read(actor, "case_read", "exta_suppression_list")
        filters = {}
        if requester_ref is not None:
            filters["requester_ref"] = requester_ref
        if campaign_id is not None:
            filters["campaign_id"] = campaign_id
        return self._list("suppression", **filters)

    def _is_suppressed(self, requester_ref, campaign_id):
        """The unit's suppression seam: a requester is suppressed
        for a campaign when a suppression record names the
        requester with that campaign's scope, or with the global
        scope (``campaign_id`` None). Pure derivation over this
        surface's suppression records; stores nothing."""
        for record in self._list("suppression"):
            if record["requester_ref"] != requester_ref:
                continue
            if record["campaign_id"] is None \
                    or record["campaign_id"] == campaign_id:
                return True
        return False

    def record_outreach_attempt(self, campaign_id, requester_ref, actor,
                                case_id=None, note=None):
        """Record that an outreach contact under a campaign was
        requested of a transport for one requester.

        The campaign must exist, the requester must be a core
        requester named by opaque ref, and an optional case must
        exist in the core. A requester suppressed for this
        campaign (or globally) is refused whole — no record is
        created and no id is consumed. The attempt is a request
        record: nothing is sent here, so it carries
        ``reference_transport: True`` and ``sent_here: False``.
        """
        self._guard(actor, "case_write", "exta_outreach_attempt",
                    target=campaign_id)
        _string_or_none(note, "note")
        self._get("campaign", campaign_id)
        self._core_requester_ref(requester_ref, actor)
        if case_id is not None:
            self._core_case(case_id, actor)
        if self._is_suppressed(requester_ref, campaign_id):
            raise ValidationError(
                "requester %r is suppressed for campaign %r; "
                "outreach attempt refused" % (requester_ref, campaign_id))
        return self._create(
            "outreach_attempt", "out",
            {"campaign_id": campaign_id,
             "requester_ref": requester_ref, "case_id": case_id,
             "note": note, "reference_transport": True,
             "sent_here": False, "state": "recorded_reference_only"},
            actor, "exta_outreach_attempt")

    def get_outreach_attempt(self, attempt_id, actor):
        self._guard_read(actor, "case_read", "exta_outreach_attempt_get",
                         target=attempt_id)
        return self._fetch("outreach_attempt", attempt_id)

    def list_outreach_attempts(self, actor, campaign_id=None,
                               requester_ref=None):
        self._guard_read(actor, "case_read", "exta_outreach_attempt_list")
        filters = {}
        if campaign_id is not None:
            filters["campaign_id"] = campaign_id
        if requester_ref is not None:
            filters["requester_ref"] = requester_ref
        return self._list("outreach_attempt", **filters)

    def record_outreach_report(self, attempt_id, outcome, actor,
                               detail=None):
        """Record a transport's reported outcome for an attempt,
        verbatim. The build sent nothing, so the report itself
        also carries ``sent_here: False``."""
        self._guard(actor, "case_write", "exta_outreach_report",
                    target=attempt_id)
        _one_of(outcome, KNOWN_OUTREACH_REPORT_OUTCOMES,
                OUTREACH_REPORT_OUTCOMES, "outcome")
        _string_or_none(detail, "detail")
        self._get("outreach_attempt", attempt_id)
        return self._create(
            "outreach_report", "outr",
            {"attempt_id": attempt_id, "outcome": outcome,
             "detail": detail, "reported": True,
             "reference_transport": True, "sent_here": False},
            actor, "exta_outreach_report")

    def list_outreach_reports(self, actor, attempt_id=None):
        self._guard_read(actor, "case_read", "exta_outreach_report_list")
        filters = {}
        if attempt_id is not None:
            filters["attempt_id"] = attempt_id
        return self._list("outreach_report", **filters)

    def _latest_outcome(self, reports):
        """The latest recorded report's outcome, or None. Pure
        derivation at read; the stored records carry no latest
        key."""
        if not reports:
            return None
        return reports[-1]["outcome"]

    def campaign_view(self, campaign_id, actor):
        """Derived at read: the campaign definition plus counts
        over this surface's own attempt/report/suppression
        records for it, and the latest reported outcome. Counts
        only — no rate or engagement figure is computed — and
        nothing is stored on the campaign record."""
        self._guard_read(actor, "case_read", "exta_campaign_view",
                         target=campaign_id)
        campaign = self._fetch("campaign", campaign_id)
        attempts = self._list("outreach_attempt", campaign_id=campaign_id)
        attempt_ids = {a["id"] for a in attempts}
        reports = [r for r in self._list("outreach_report")
                   if r["attempt_id"] in attempt_ids]
        by_outcome = {o: 0 for o in OUTREACH_REPORT_OUTCOMES}
        for report in reports:
            by_outcome[report["outcome"]] += 1
        scoped = [s for s in self._list("suppression")
                  if s["campaign_id"] == campaign_id]
        view = dict(campaign)
        view["attempts"] = len(attempts)
        view["reports"] = len(reports)
        view["reports_by_outcome"] = by_outcome
        view["latest_reported_outcome"] = self._latest_outcome(reports)
        view["suppressions_scoped"] = len(scoped)
        view["derived"] = True
        view["stored"] = False
        return view

    def outreach_summary(self, actor):
        """Derived at read: counts over this surface's own
        records. ``sent_here`` stays False: reports describe
        outcomes elsewhere, they are not sends. Counts only;
        nothing is stored."""
        self._guard_read(actor, "report_read", "exta_outreach_summary")
        campaigns = self._list("campaign")
        attempts = self._list("outreach_attempt")
        reports = self._list("outreach_report")
        suppressions = self._list("suppression")
        by_kind = {k: 0 for k in CAMPAIGN_KINDS}
        for campaign in campaigns:
            by_kind[campaign["kind"]] += 1
        by_outcome = {o: 0 for o in OUTREACH_REPORT_OUTCOMES}
        for report in reports:
            by_outcome[report["outcome"]] += 1
        return {"campaigns": len(campaigns),
                "campaigns_by_kind": by_kind,
                "attempts": len(attempts),
                "reports": len(reports),
                "reports_by_outcome": by_outcome,
                "suppressions": len(suppressions),
                "sent_here": False, "derived": True,
                "method": "counts_over_outreach_records"}
