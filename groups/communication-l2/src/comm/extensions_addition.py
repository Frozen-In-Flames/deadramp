"""Final GAPS batch, second unit: Remainder Addition extensions
for the Communication L2 merged build (Group 11).

Covers the 1 OPEN entry of the GAPS.md section "Remainder
Addition -- Communication L2 (+1 fork)" (inventory idx 657),
the gap registered by the Granicus / GovDelivery addition
(ADDENDUM.md section 5):

- idx 657 (drafted build-extension, re-judged reference): a
  marketing automation & citizen-engagement campaign engine --
  audience targeting / segmentation and automated campaign
  execution. Marketing automation is an operated engine: it
  selects an audience from the directory and executes campaign
  sends against it. Neither half executes here. What ships is
  the engine's honest records form, following this group's own
  workflow-definition precedent (idx 124: definitions copied as
  data, never executed) and the sibling Communication L3
  addition's connector form: campaign definitions and audience
  segment definitions held as data, plus campaign outcome
  records whose figures are reported verbatim by the external
  platform. Every record is labeled ``reference_stub: True``
  with ``executed_here: False``; nothing is targeted, segmented,
  sent, or transmitted.

Design follows the first batch unit (``comm.extensions``) and
the core's doctrines:

- Wrapper around :class:`CommStore`; all existing modules,
  including ``extensions.py``, are byte-identical. Core records
  (groups, templates) are validated and read through the core
  store's public API only; their content is never copied onto
  this surface (a template is bound by id only).
- RBAC through :mod:`comm.access`, checked before any state
  change or id allocation; denied attempts audited with a
  ``:denied`` suffix; successful mutations audited with an
  ``exta_`` prefix. A failed operation consumes no id.
- Opaque ``*_ref`` strings and core record ids only. No record
  shape can hold message content: the signatures accept no
  content-shaped parameter (a ``content=`` / ``body=`` /
  ``subject=`` / ``payload=`` call raises ``TypeError``), and
  tests pin exact key sets plus a recursive no-content scan.
- An audience segment definition records the group ids and
  criterion refs it was defined with, as data. It is never
  resolved against the directory: no member list, audience
  count, or targeted-contact set is computed anywhere on this
  surface (``targeted_here`` / ``segmented_here`` /
  ``audience_computed`` are False on every record and view).
- Derived values are derived at read and never stored: a
  campaign's current reported outcome and its totals of
  reported figures (sums of the platform's reported counts,
  stated as such -- never measured deliveries). Stored records
  carry no derived key; tests pin that.
- Nothing is sent or transmitted: ``sent_here`` /
  ``transmitted_here`` are False on every record, and recording
  on this surface is pinned to change no core message or
  delivery record and to dispatch nothing.
"""

import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import CHANNEL_KINDS

# Outcome labels are reported verbatim by the external platform;
# the surface holds no fixed vocabulary for them (the sibling
# connector form). The labels below are examples used by tests.
def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % what)
    return value


def _check_reported_count(value, what):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer count as reported" % what)
    if value < 0:
        raise ValidationError("%s must be >= 0" % what)
    return value


def _latest_label(records, key):
    """THE addition seam (fresh negative control): the current
    reported label of an append-only record stream is its LATEST
    record's label. Reading the earliest record instead would
    silently resurrect superseded campaign outcomes on every
    derived view while leaving the stored shapes intact.
    Mutating this seam must fail the suite."""
    if not records:
        return None
    return records[-1][key]


class CommExtensionsAddition:
    """Second batch extension surface wrapping a CommStore."""

    def __init__(self, store):
        self.store = store
        self.audit = store.audit
        self._lock = threading.RLock()
        self._counters = {}
        self._campaigns = {}
        self._segments = {}
        self._outcomes = {}

    # -- plumbing ---------------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _require(self, actor, action):
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
        if hasattr(actor, "role"):
            try:
                require(actor, action)
            except PermissionDenied:
                if self.audit is not None:
                    self.audit.record(actor_name(actor), "exta_%s:denied" % action,
                                      "extensions_addition")
                raise

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), "exta_" + action, target, details=details)

    def _get(self, table, obj_id, what):
        rec = table.get(obj_id)
        if rec is None:
            raise NotFoundError("%s not found: %r" % (what, obj_id))
        return rec

    def _base(self, actor):
        return {"created_by": actor_name(actor), "created_utc": _utc_now()}

    # -- 657 MARKETING AUTOMATION & CAMPAIGN ENGINE (reference) -----

    def define_campaign(self, campaign_ref, label, actor, channel_kinds=None,
                        template_id=None):
        """Campaign definition record: the campaign as data.

        The definition names the campaign by an opaque ref and a
        verbatim label, records the channel kinds it declares and
        (optionally) a core template bound by id only -- the
        template is validated through the core store and its
        subject/body are never copied here. The definition is
        never executed: no audience is selected, no message is
        composed, nothing is sent."""
        self._require(actor, "message_compose")
        _non_empty(campaign_ref, "campaign_ref")
        _non_empty(label, "label")
        kinds = []
        if channel_kinds is not None:
            if not isinstance(channel_kinds, (list, tuple)) or not channel_kinds:
                raise ValidationError("channel_kinds must be a non-empty list")
            for kind in channel_kinds:
                if kind not in CHANNEL_KINDS:
                    raise ValidationError("unknown channel kind: %r" % (kind,))
                if kind not in kinds:
                    kinds.append(kind)
        with self._lock:
            for existing in self._campaigns.values():
                if existing["campaign_ref"] == campaign_ref:
                    raise ValidationError(
                        "campaign_ref %r is already registered" % (campaign_ref,))
            if template_id is not None:
                self.store.get_template(template_id, actor)
            cid = self._next_id("mcam")
            rec = {"id": cid, "campaign_ref": campaign_ref, "label": label,
                   "channel_kinds": kinds, "template_id": template_id,
                   "reference_stub": True, "reference_transport": True,
                   "executed_here": False, "targeted_here": False,
                   "segmented_here": False, "sent_here": False,
                   "transmitted_here": False, "content_held": False}
            rec.update(self._base(actor))
            self._campaigns[cid] = rec
            self._audit(actor, "campaign_definition_record", cid)
            return dict(rec, channel_kinds=list(rec["channel_kinds"]))

    def define_audience_segment(self, segment_ref, label, actor, group_ids=None,
                                criterion_refs=None):
        """Audience segment definition record: targeting as data.

        The definition records the core group ids and opaque
        criterion refs it was defined with. The groups are
        validated through the core store; their membership is
        never resolved -- no audience is computed, counted, or
        listed, here or in any view."""
        self._require(actor, "message_compose")
        _non_empty(segment_ref, "segment_ref")
        _non_empty(label, "label")
        groups = []
        if group_ids is not None:
            if not isinstance(group_ids, (list, tuple)):
                raise ValidationError("group_ids must be a list")
            for gid in group_ids:
                _non_empty(gid, "group_id")
                if gid not in groups:
                    groups.append(gid)
        criteria = []
        if criterion_refs is not None:
            if not isinstance(criterion_refs, (list, tuple)):
                raise ValidationError("criterion_refs must be a list")
            for ref in criterion_refs:
                _non_empty(ref, "criterion_ref")
                if ref not in criteria:
                    criteria.append(ref)
        with self._lock:
            for existing in self._segments.values():
                if existing["segment_ref"] == segment_ref:
                    raise ValidationError(
                        "segment_ref %r is already registered" % (segment_ref,))
            for gid in groups:
                self.store.get_group(gid, actor)
            sid = self._next_id("mseg")
            rec = {"id": sid, "segment_ref": segment_ref, "label": label,
                   "group_ids": list(groups), "criterion_refs": list(criteria),
                   "reference_stub": True,
                   "executed_here": False, "targeted_here": False,
                   "segmented_here": False, "audience_computed": False,
                   "content_held": False}
            rec.update(self._base(actor))
            self._segments[sid] = rec
            self._audit(actor, "audience_segment_definition_record", sid)
            return dict(rec, group_ids=list(rec["group_ids"]),
                        criterion_refs=list(rec["criterion_refs"]))

    def record_campaign_outcome(self, campaign_id, outcome_label, actor,
                                messages_reported=None, deliveries_reported=None):
        """Reported campaign outcome record: an outcome label and
        optional delivery/message counts exactly as reported by
        the external platform. The figures are the platform's
        reports, held verbatim; nothing here measures, sends, or
        verifies a delivery."""
        self._require(actor, "message_compose")
        _non_empty(outcome_label, "outcome_label")
        messages_reported = _check_reported_count(messages_reported, "messages_reported")
        deliveries_reported = _check_reported_count(deliveries_reported,
                                                    "deliveries_reported")
        with self._lock:
            self._get(self._campaigns, campaign_id, "campaign definition")
            rid = self._next_id("mrep")
            rec = {"id": rid, "campaign_id": campaign_id,
                   "outcome_label": outcome_label,
                   "messages_reported": messages_reported,
                   "deliveries_reported": deliveries_reported,
                   "figures_basis": "reported_by_platform",
                   "reference_stub": True, "reference_transport": True,
                   "executed_here": False, "sent_here": False,
                   "transmitted_here": False, "measured_here": False}
            rec.update(self._base(actor))
            self._outcomes[rid] = rec
            self._audit(actor, "campaign_outcome_record", rid)
            return dict(rec)

    def campaign_view(self, campaign_id, actor):
        """Derived view: the definition plus its reported outcomes.

        ``current_outcome`` is the LATEST outcome record's label
        (the addition seam); the totals are sums of the figures
        the platform reported, stated as such. No total is stored
        on the definition record."""
        self._require(actor, "records_read")
        with self._lock:
            definition = dict(self._get(self._campaigns, campaign_id,
                                        "campaign definition"))
            definition["channel_kinds"] = list(definition["channel_kinds"])
            outcomes = [dict(r) for r in self._outcomes.values()
                        if r["campaign_id"] == campaign_id]
            current = _latest_label(outcomes, "outcome_label")
            total_messages = sum(r["messages_reported"] for r in outcomes
                                 if r["messages_reported"] is not None)
            total_deliveries = sum(r["deliveries_reported"] for r in outcomes
                                   if r["deliveries_reported"] is not None)
            uncounted = sum(1 for r in outcomes
                            if r["messages_reported"] is None
                            and r["deliveries_reported"] is None)
            return {"definition": definition, "outcomes": outcomes,
                    "outcome_count": len(outcomes),
                    "current_outcome": current if current is not None else "unreported",
                    "total_messages_reported": total_messages,
                    "total_deliveries_reported": total_deliveries,
                    "outcomes_without_counts": uncounted,
                    "totals_basis": "sum_of_reported_counts"}

    def segment_view(self, segment_id, actor):
        """The segment definition as recorded. The audience is
        never resolved: the view carries the definition's group
        ids and criterion refs as data and no member, count, or
        targeted-contact field of any shape."""
        self._require(actor, "records_read")
        with self._lock:
            definition = dict(self._get(self._segments, segment_id,
                                        "audience segment definition"))
            definition["group_ids"] = list(definition["group_ids"])
            definition["criterion_refs"] = list(definition["criterion_refs"])
            return {"definition": definition, "audience_computed": False,
                    "targeted_here": False, "segmented_here": False}

    def addition_campaign_summary(self, actor):
        """Deterministic counts over the addition surface,
        computed at read on every call; nothing stored, no score,
        no audience figure."""
        self._require(actor, "records_read")
        with self._lock:
            return {"method": "deterministic_counts",
                    "campaigns": len(self._campaigns),
                    "audience_segments": len(self._segments),
                    "campaign_outcomes": len(self._outcomes)}
