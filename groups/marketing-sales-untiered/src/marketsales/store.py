"""Marketing & Sales store: organization registry; opportunity,
evaluation, capture-pipeline, proposal-content, and workflow
records (business-development side); contact-list, audience-
segment, campaign, delivery, suppression, and engagement records
(outbound-email side).

Clean-room implementation of the union spec's implementation
contract. This category is new — no tiered group exists — and the
core is claim-driven: every record type traces to a claim in the
set's spec sheets (see UNION-SPEC.md), except the organization
registry, search/summary, and API/access/audit substrate every
DeadRamp build carries, whose reason is stated in the spec.

Role permission is enforced on every operation when the actor is
a User-like object: the action named for the operation must be in
the actor's role permission set (see :mod:`marketsales.access`).
A plain string actor carries identity (for provenance) but no
role, so role enforcement for those happens in the service layer
(the sibling builds' convention).

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``opp-``, ``evl-``, ``pip-``, ``pro-``, ``wfl-``, ``lst-``,
``seg-``, ``cam-``, ``dlv-``, ``sup-``, ``eng-``).

Reference discipline: records name people and contacts only by
**opaque references** supplied by the caller. A contact reference
is validated to be incapable of holding an email address (no
``@``, no whitespace) or any free-form identifier text the caller
did not choose as a reference; this store holds no real names, no
email addresses, and no CUI. Proposal-content records are
metadata — an item label, a kind label, a version, a recorded
size — and hold no proposal text: there is no field on any shape
that could hold content, and the shapes are pinned by test.

Derivation discipline: a campaign's status is derived at read
time and never stored. The single seam
:func:`_derive_campaign_status` computes ``draft`` /
``scheduled`` / ``delivered`` / ``reported`` from the campaign
record (its optional scheduled moment) and the presence of
delivery and engagement records. The stored campaign record
carries no status key. Event-driven lifecycle state, by contrast,
is stored, as in the sibling builds' record lifecycles: a
pipeline entry's stage, changed only through the recorded
transition map; a workflow's active flag; a suppression's
active / released state.

Suppression gate (the signature invariant): a delivery outcome of
``delivered`` may not be recorded for a contact under an active
suppression on the campaign's contact list. The gate is the
single seam :func:`_check_delivery_allowed`, read by the delivery
operation only; ``bounced`` and ``deferred`` outcomes remain
recordable for a suppressed contact, as facts about the attempt,
and a suppression recorded after a delivery does not rewrite that
delivery — records are facts, the gate binds at recording time.

Scoring discipline: nothing in this store computes a score, a
rating, a ranking, or a rate. Evaluations record a decision from
a fixed vocabulary; they do not grade the opportunity. The
engagement report and the summary return counts and recorded
values only — counts of deliveries by outcome and engagements by
kind, never percentages.

Registry discipline: workflow records describe recurring
business-development workflows; the registry never executes one.
Registering or toggling a workflow runs nothing, sends nothing,
and changes no other record; there is deliberately no execution
entry point anywhere in this package (pinned by test).

Money discipline: no record in this store carries money. Neither
description in this set states a price, a budget, a spend figure,
or an award value, so no money shape was built — the same
deliberate omission the Event Management build recorded.

The store records every successful mutation to its audit log
(when one is attached). Reads are not audited here; denied
attempts and audit reads are the HTTP layer's responsibility, so
nothing is recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, ValidationError

EVALUATION_DECISIONS = ("pursue", "watch", "no_pursue")
PIPELINE_STAGES = (
    "identified",
    "qualified",
    "capture",
    "proposal",
    "submitted",
    "awarded",
    "not_awarded",
    "no_bid",
)
PIPELINE_TRANSITIONS = {
    "identified": ("qualified", "no_bid"),
    "qualified": ("capture", "no_bid"),
    "capture": ("proposal", "no_bid"),
    "proposal": ("submitted", "no_bid"),
    "submitted": ("awarded", "not_awarded"),
    "awarded": (),
    "not_awarded": (),
    "no_bid": (),
}
DELIVERY_OUTCOMES = ("delivered", "bounced", "deferred")
ENGAGEMENT_KINDS = ("open", "click", "reply", "unsubscribe")
SUPPRESSION_REASONS = ("unsubscribe", "bounce", "complaint", "agency_request")
SUPPRESSION_STATES = ("active", "released")
CAMPAIGN_STATES = ("draft", "scheduled", "delivered", "reported")


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


def _optional_text(value, field):
    if value is None:
        return None
    return _text(value, field)


def _count(value, field):
    """A non-negative integer count. Booleans, floats, and strings
    are rejected at the boundary."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer" % field)
    if value < 0:
        raise ValidationError("%s must be zero or greater" % field)
    return value


def _contact_ref(value, field="contact_ref"):
    """An opaque contact reference. It must be a non-empty string
    with no whitespace and no ``@`` — a value of that shape cannot
    be an email address, so no record keyed by it can hold one."""
    _text(value, field)
    if "@" in value or any(ch.isspace() for ch in value):
        raise ValidationError(
            "%s must be an opaque reference (no whitespace, no '@')" % field)
    return value


def _derive_campaign_status(campaign, delivery_count, engagement_count):
    """Campaign status derivation seam: a campaign's status,
    computed from its record and the counts of its delivery and
    engagement records.

    - ``reported`` once any engagement record exists;
    - ``delivered`` once any delivery record exists;
    - ``scheduled`` when a scheduled moment is recorded and
      neither of the above holds;
    - ``draft`` otherwise.

    Pure function over recorded values. Nothing about the status
    is stored anywhere; the campaign view, the status filter, and
    the summary all compute it through this seam, so they can
    never disagree.
    """
    if engagement_count > 0:
        return "reported"
    if delivery_count > 0:
        return "delivered"
    if campaign.get("scheduled_for") is not None:
        return "scheduled"
    return "draft"


def _check_delivery_allowed(active_suppression, outcome):
    """Suppression gate seam: the single check the delivery
    operation reads before recording an outcome.

    An outcome of ``delivered`` is refused while an active
    suppression covers the contact on the campaign's list — that
    refusal is the entire function suppression records exist to
    perform. Any other outcome, and any delivery to an
    unsuppressed contact, is allowed.
    """
    if outcome == "delivered" and active_suppression is not None:
        raise ValidationError(
            "contact %r is under an active suppression (%s) on this "
            "list; a 'delivered' outcome may not be recorded"
            % (active_suppression["contact_ref"],
               active_suppression["id"]))


class MarketSalesStore:
    """In-memory Marketing & Sales records store with an optional
    audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._opportunities = {}
        self._evaluations = {}
        self._pipeline = {}
        self._content = {}
        self._workflows = {}
        self._lists = {}
        self._segments = {}
        self._campaigns = {}
        self._deliveries = {}
        self._suppressions = {}
        self._engagements = {}
        self._counters = {}

    # -- internal helpers ---------------------------------------------------

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

    def _organization(self, org_id):
        organization = self._organizations.get(org_id)
        if organization is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return organization

    def _opportunity(self, opportunity_id):
        opportunity = self._opportunities.get(opportunity_id)
        if opportunity is None:
            raise NotFoundError("no such opportunity: %r" % (opportunity_id,))
        return opportunity

    def _pipeline_entry(self, entry_id):
        entry = self._pipeline.get(entry_id)
        if entry is None:
            raise NotFoundError("no such pipeline entry: %r" % (entry_id,))
        return entry

    def _workflow(self, workflow_id):
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise NotFoundError("no such workflow: %r" % (workflow_id,))
        return workflow

    def _contact_list(self, list_id):
        contact_list = self._lists.get(list_id)
        if contact_list is None:
            raise NotFoundError("no such contact list: %r" % (list_id,))
        return contact_list

    def _segment(self, segment_id):
        segment = self._segments.get(segment_id)
        if segment is None:
            raise NotFoundError("no such audience segment: %r" % (segment_id,))
        return segment

    def _campaign(self, campaign_id):
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            raise NotFoundError("no such campaign: %r" % (campaign_id,))
        return campaign

    def _suppression(self, suppression_id):
        suppression = self._suppressions.get(suppression_id)
        if suppression is None:
            raise NotFoundError("no such suppression: %r" % (suppression_id,))
        return suppression

    # -- organizations ---------------------------------------------------------

    def create_organization(self, actor, ref, label):
        """Register an organization by opaque reference."""
        self._check_role(actor, "register")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["ref"] == ref:
                    raise ValidationError(
                        "organization ref already registered: %r" % (ref,))
            record = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[record["id"]] = record
        self._record(actor, "create_organization", record["id"],
                     {"ref": ref})
        return dict(record)

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        return dict(self._organization(org_id))

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        return [dict(o) for o in self._organizations.values()]

    # -- opportunities ---------------------------------------------------------

    def create_opportunity(self, actor, org_id, ref, agency_label,
                           title_label, posted_at, due_at=None,
                           kind_label=None):
        """Record a discovered federal contracting opportunity.

        This is the records form of discovery: the record of an
        opportunity a user found and chose to track. The live
        discovery feed itself is Extended (see UNION-SPEC.md).
        """
        self._check_role(actor, "register")
        _text(ref, "ref")
        _text(agency_label, "agency_label")
        _text(title_label, "title_label")
        posted = _parse_moment(posted_at, "posted_at")
        due = None
        if due_at is not None:
            due = _parse_moment(due_at, "due_at")
        _optional_text(kind_label, "kind_label")
        with self._lock:
            self._organization(org_id)
            for existing in self._opportunities.values():
                if existing["org_id"] == org_id and existing["ref"] == ref:
                    raise ValidationError(
                        "opportunity ref already recorded for this "
                        "organization: %r" % (ref,))
            record = {
                "id": self._mint("opp-"),
                "org_id": org_id,
                "ref": ref,
                "agency_label": agency_label,
                "title_label": title_label,
                "posted_at": posted.isoformat(),
                "due_at": due.isoformat() if due is not None else None,
                "kind_label": kind_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._opportunities[record["id"]] = record
        self._record(actor, "create_opportunity", record["id"],
                     {"org_id": org_id, "ref": ref})
        return dict(record)

    def get_opportunity(self, actor, opportunity_id):
        self._check_role(actor, "read")
        return dict(self._opportunity(opportunity_id))

    def list_opportunities(self, actor, org_id=None):
        self._check_role(actor, "read")
        result = [dict(o) for o in self._opportunities.values()
                  if org_id is None or o["org_id"] == org_id]
        return result

    # -- evaluations -----------------------------------------------------------

    def record_evaluation(self, actor, opportunity_id, evaluator_ref,
                          decision, note=None):
        """Record an evaluation decision on an opportunity.

        The decision is a recorded value from a fixed vocabulary
        (``pursue`` / ``watch`` / ``no_pursue``) with an optional
        verbatim note. No score, grade, or fit value is computed
        or stored — the record shape carries no field for one.
        """
        self._check_role(actor, "evaluate")
        _text(evaluator_ref, "evaluator_ref")
        if decision not in EVALUATION_DECISIONS:
            raise ValidationError(
                "decision must be one of %r" % (EVALUATION_DECISIONS,))
        _optional_text(note, "note")
        with self._lock:
            self._opportunity(opportunity_id)
            record = {
                "id": self._mint("evl-"),
                "opportunity_id": opportunity_id,
                "evaluator_ref": evaluator_ref,
                "decision": decision,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._evaluations[record["id"]] = record
        self._record(actor, "record_evaluation", record["id"],
                     {"opportunity_id": opportunity_id,
                      "decision": decision})
        return dict(record)

    def list_evaluations(self, actor, opportunity_id=None):
        self._check_role(actor, "read")
        return [dict(e) for e in self._evaluations.values()
                if opportunity_id is None
                or e["opportunity_id"] == opportunity_id]

    # -- capture pipeline ------------------------------------------------------

    def create_pipeline_entry(self, actor, opportunity_id, stage="identified"):
        """Open a capture-pipeline entry for an opportunity at a
        stage (default ``identified``, the head of the stage map)."""
        self._check_role(actor, "pipeline")
        if stage not in PIPELINE_STAGES:
            raise ValidationError(
                "stage must be one of %r" % (PIPELINE_STAGES,))
        with self._lock:
            self._opportunity(opportunity_id)
            record = {
                "id": self._mint("pip-"),
                "opportunity_id": opportunity_id,
                "stage": stage,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
                "updated_utc": _utc_now().isoformat(),
            }
            self._pipeline[record["id"]] = record
        self._record(actor, "create_pipeline_entry", record["id"],
                     {"opportunity_id": opportunity_id, "stage": stage})
        return dict(record)

    def transition_pipeline(self, actor, entry_id, stage):
        """Move a pipeline entry along the recorded transition map.

        A transition outside the map (skipping a stage, leaving a
        terminal stage, or naming an unknown stage) is rejected
        and changes nothing.
        """
        self._check_role(actor, "pipeline")
        if stage not in PIPELINE_STAGES:
            raise ValidationError(
                "stage must be one of %r" % (PIPELINE_STAGES,))
        with self._lock:
            entry = self._pipeline_entry(entry_id)
            allowed = PIPELINE_TRANSITIONS[entry["stage"]]
            if stage not in allowed:
                raise ValidationError(
                    "pipeline stage %r may not move to %r (allowed: %r)"
                    % (entry["stage"], stage, allowed))
            entry["stage"] = stage
            entry["updated_utc"] = _utc_now().isoformat()
            result = dict(entry)
        self._record(actor, "transition_pipeline", entry_id,
                     {"stage": stage})
        return result

    def get_pipeline_entry(self, actor, entry_id):
        self._check_role(actor, "read")
        return dict(self._pipeline_entry(entry_id))

    def list_pipeline(self, actor, opportunity_id=None, stage=None):
        self._check_role(actor, "read")
        return [dict(e) for e in self._pipeline.values()
                if (opportunity_id is None
                    or e["opportunity_id"] == opportunity_id)
                and (stage is None or e["stage"] == stage)]

    # -- proposal content --------------------------------------------------------

    def create_content_version(self, actor, opportunity_id, item_label,
                               kind_label, version, size_bytes,
                               pipeline_id=None):
        """Record one version of a proposal content item.

        Metadata only: an item label, a kind label, a version
        number, and a recorded size in bytes. The content itself
        is never accepted or stored — generation and refinement
        of content are Extended (see UNION-SPEC.md); this registry
        is the records those operations presuppose. ``version``
        must be unique per (opportunity, item label).
        """
        self._check_role(actor, "propose")
        _text(item_label, "item_label")
        _text(kind_label, "kind_label")
        if isinstance(version, bool) or not isinstance(version, int):
            raise ValidationError("version must be an integer")
        if version < 1:
            raise ValidationError("version must be at least 1")
        size = _count(size_bytes, "size_bytes")
        with self._lock:
            self._opportunity(opportunity_id)
            if pipeline_id is not None:
                entry = self._pipeline_entry(pipeline_id)
                if entry["opportunity_id"] != opportunity_id:
                    raise ValidationError(
                        "pipeline entry %r does not belong to "
                        "opportunity %r" % (pipeline_id, opportunity_id))
            for existing in self._content.values():
                if (existing["opportunity_id"] == opportunity_id
                        and existing["item_label"] == item_label
                        and existing["version"] == version):
                    raise ValidationError(
                        "content item %r already has a version %d for "
                        "this opportunity" % (item_label, version))
            record = {
                "id": self._mint("pro-"),
                "opportunity_id": opportunity_id,
                "pipeline_id": pipeline_id,
                "item_label": item_label,
                "kind_label": kind_label,
                "version": version,
                "size_bytes": size,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._content[record["id"]] = record
        self._record(actor, "create_content_version", record["id"],
                     {"opportunity_id": opportunity_id,
                      "item_label": item_label, "version": version})
        return dict(record)

    def list_content(self, actor, opportunity_id=None):
        self._check_role(actor, "read")
        return [dict(c) for c in self._content.values()
                if opportunity_id is None
                or c["opportunity_id"] == opportunity_id]

    # -- workflow registry (records only; never executes) ------------------------

    def create_workflow(self, actor, org_id, label, trigger_label,
                        cadence_label=None):
        """Register a recurring business-development workflow.

        A record only: registering a workflow runs nothing. This
        registry exists so the workflows an organization relies on
        are named, owned, and auditable; executing one is the
        Extended automation engine's work, and this build has no
        execution entry point at all.
        """
        self._check_role(actor, "workflow")
        _text(label, "label")
        _text(trigger_label, "trigger_label")
        _optional_text(cadence_label, "cadence_label")
        with self._lock:
            self._organization(org_id)
            record = {
                "id": self._mint("wfl-"),
                "org_id": org_id,
                "label": label,
                "trigger_label": trigger_label,
                "cadence_label": cadence_label,
                "active": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._workflows[record["id"]] = record
        self._record(actor, "create_workflow", record["id"],
                     {"org_id": org_id, "label": label})
        return dict(record)

    def set_workflow_active(self, actor, workflow_id, active):
        """Record a workflow's active flag. Toggling the flag runs
        nothing either; it is a recorded state, not a switch wired
        to an engine."""
        self._check_role(actor, "workflow")
        if not isinstance(active, bool):
            raise ValidationError("active must be a boolean")
        with self._lock:
            workflow = self._workflow(workflow_id)
            workflow["active"] = active
            result = dict(workflow)
        self._record(actor, "set_workflow_active", workflow_id,
                     {"active": active})
        return result

    def list_workflows(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(w) for w in self._workflows.values()
                if org_id is None or w["org_id"] == org_id]

    # -- contact lists -----------------------------------------------------------

    def create_contact_list(self, actor, org_id, label, contact_count,
                            loaded_at=None):
        """Record a contact list an agency loaded.

        Counts only: the list's contacts are never uploaded here.
        Individual contacts enter this store only as opaque
        references on suppression, delivery, and engagement
        records — references whose shape cannot be an email
        address (see :func:`_contact_ref`).
        """
        self._check_role(actor, "lists")
        _text(label, "label")
        count = _count(contact_count, "contact_count")
        loaded = None
        if loaded_at is not None:
            loaded = _parse_moment(loaded_at, "loaded_at")
        with self._lock:
            self._organization(org_id)
            record = {
                "id": self._mint("lst-"),
                "org_id": org_id,
                "label": label,
                "contact_count": count,
                "loaded_at": (loaded.isoformat() if loaded is not None
                              else _utc_now().isoformat()),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._lists[record["id"]] = record
        self._record(actor, "create_contact_list", record["id"],
                     {"org_id": org_id, "label": label})
        return dict(record)

    def get_contact_list(self, actor, list_id):
        self._check_role(actor, "read")
        return dict(self._contact_list(list_id))

    def list_contact_lists(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(lst) for lst in self._lists.values()
                if org_id is None or lst["org_id"] == org_id]

    # -- audience segments ---------------------------------------------------------

    def create_segment(self, actor, org_id, label, basis_label, member_count):
        """Record an audience segment: a label, the basis on which
        it was formed (a caller-stated label), and a recorded
        member count. Computing membership from contact data is
        the Extended segmentation engine's work; this is its
        record."""
        self._check_role(actor, "segments")
        _text(label, "label")
        _text(basis_label, "basis_label")
        count = _count(member_count, "member_count")
        with self._lock:
            self._organization(org_id)
            record = {
                "id": self._mint("seg-"),
                "org_id": org_id,
                "label": label,
                "basis_label": basis_label,
                "member_count": count,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._segments[record["id"]] = record
        self._record(actor, "create_segment", record["id"],
                     {"org_id": org_id, "label": label})
        return dict(record)

    def list_segments(self, actor, org_id=None):
        self._check_role(actor, "read")
        return [dict(s) for s in self._segments.values()
                if org_id is None or s["org_id"] == org_id]

    # -- campaigns -----------------------------------------------------------

    def create_campaign(self, actor, org_id, label, segment_id, list_id,
                        scheduled_for=None):
        """Record an authored campaign against a segment and a
        contact list of the same organization, with an optional
        scheduled moment. The stored record carries no status
        key: status is derived at read (see
        :func:`_derive_campaign_status`)."""
        self._check_role(actor, "campaigns")
        _text(label, "label")
        scheduled = None
        if scheduled_for is not None:
            scheduled = _parse_moment(scheduled_for, "scheduled_for")
        with self._lock:
            self._organization(org_id)
            segment = self._segment(segment_id)
            contact_list = self._contact_list(list_id)
            if segment["org_id"] != org_id or contact_list["org_id"] != org_id:
                raise ValidationError(
                    "segment and contact list must belong to the "
                    "campaign's organization")
            record = {
                "id": self._mint("cam-"),
                "org_id": org_id,
                "label": label,
                "segment_id": segment_id,
                "list_id": list_id,
                "scheduled_for": (scheduled.isoformat()
                                  if scheduled is not None else None),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._campaigns[record["id"]] = record
        self._record(actor, "create_campaign", record["id"],
                     {"org_id": org_id, "label": label})
        return self._campaign_view(record)

    def _campaign_counts(self, campaign_id):
        deliveries = sum(1 for d in self._deliveries.values()
                         if d["campaign_id"] == campaign_id)
        engagements = sum(1 for e in self._engagements.values()
                          if e["campaign_id"] == campaign_id)
        return deliveries, engagements

    def _campaign_view(self, campaign):
        view = dict(campaign)
        deliveries, engagements = self._campaign_counts(campaign["id"])
        view["status"] = _derive_campaign_status(
            campaign, deliveries, engagements)
        return view

    def get_campaign(self, actor, campaign_id):
        self._check_role(actor, "read")
        return self._campaign_view(self._campaign(campaign_id))

    def list_campaigns(self, actor, org_id=None, status=None):
        self._check_role(actor, "read")
        if status is not None and status not in CAMPAIGN_STATES:
            raise ValidationError(
                "status must be one of %r" % (CAMPAIGN_STATES,))
        result = []
        for campaign in self._campaigns.values():
            if org_id is not None and campaign["org_id"] != org_id:
                continue
            view = self._campaign_view(campaign)
            if status is not None and view["status"] != status:
                continue
            result.append(view)
        return result

    # -- suppressions -----------------------------------------------------------

    def _active_suppression(self, list_id, contact_ref):
        for suppression in self._suppressions.values():
            if (suppression["list_id"] == list_id
                    and suppression["contact_ref"] == contact_ref
                    and suppression["state"] == "active"):
                return suppression
        return None

    def record_suppression(self, actor, list_id, contact_ref, reason,
                           at=None):
        """Record a suppression of one contact on one list.

        At most one active suppression per (list, contact): a
        second active record for the same pair is refused. A
        released suppression may be followed by a new one.
        """
        self._check_role(actor, "suppress")
        _contact_ref(contact_ref)
        if reason not in SUPPRESSION_REASONS:
            raise ValidationError(
                "reason must be one of %r" % (SUPPRESSION_REASONS,))
        moment = None
        if at is not None:
            moment = _parse_moment(at, "at")
        with self._lock:
            self._contact_list(list_id)
            if self._active_suppression(list_id, contact_ref) is not None:
                raise ValidationError(
                    "an active suppression already covers contact %r "
                    "on list %r" % (contact_ref, list_id))
            record = {
                "id": self._mint("sup-"),
                "list_id": list_id,
                "contact_ref": contact_ref,
                "reason": reason,
                "state": "active",
                "recorded_at": (moment.isoformat() if moment is not None
                                else _utc_now().isoformat()),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._suppressions[record["id"]] = record
        self._record(actor, "record_suppression", record["id"],
                     {"list_id": list_id, "contact_ref": contact_ref,
                      "reason": reason})
        return dict(record)

    def release_suppression(self, actor, suppression_id):
        """Release an active suppression (a recorded action; the
        record stays, its state changes). Releasing an already
        released suppression is refused."""
        self._check_role(actor, "suppress")
        with self._lock:
            suppression = self._suppression(suppression_id)
            if suppression["state"] != "active":
                raise ValidationError(
                    "suppression %r is not active" % (suppression_id,))
            suppression["state"] = "released"
            result = dict(suppression)
        self._record(actor, "release_suppression", suppression_id, {})
        return result

    def list_suppressions(self, actor, list_id=None, state=None):
        self._check_role(actor, "read")
        if state is not None and state not in SUPPRESSION_STATES:
            raise ValidationError(
                "state must be one of %r" % (SUPPRESSION_STATES,))
        return [dict(s) for s in self._suppressions.values()
                if (list_id is None or s["list_id"] == list_id)
                and (state is None or s["state"] == state)]

    def is_suppressed(self, actor, list_id, contact_ref):
        """Whether an active suppression covers the contact on the
        list — the same fact the delivery gate reads."""
        self._check_role(actor, "read")
        _contact_ref(contact_ref)
        with self._lock:
            self._contact_list(list_id)
            return self._active_suppression(list_id, contact_ref) is not None

    # -- deliveries -----------------------------------------------------------

    def record_delivery(self, actor, campaign_id, contact_ref, outcome,
                        occurred_at):
        """Record one contact's delivery outcome for a campaign.

        The suppression gate binds here: an outcome of
        ``delivered`` for a contact under an active suppression
        on the campaign's list is refused and changes nothing
        (see :func:`_check_delivery_allowed`). The actual sending
        of email is Extended; this is the delivery record the
        sending produces.
        """
        self._check_role(actor, "deliver")
        _contact_ref(contact_ref)
        if outcome not in DELIVERY_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %r" % (DELIVERY_OUTCOMES,))
        occurred = _parse_moment(occurred_at, "occurred_at")
        with self._lock:
            campaign = self._campaign(campaign_id)
            active = self._active_suppression(campaign["list_id"],
                                              contact_ref)
            _check_delivery_allowed(active, outcome)
            record = {
                "id": self._mint("dlv-"),
                "campaign_id": campaign_id,
                "contact_ref": contact_ref,
                "outcome": outcome,
                "occurred_at": occurred.isoformat(),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._deliveries[record["id"]] = record
        self._record(actor, "record_delivery", record["id"],
                     {"campaign_id": campaign_id, "outcome": outcome})
        return dict(record)

    def list_deliveries(self, actor, campaign_id=None, outcome=None):
        self._check_role(actor, "read")
        if outcome is not None and outcome not in DELIVERY_OUTCOMES:
            raise ValidationError(
                "outcome must be one of %r" % (DELIVERY_OUTCOMES,))
        return [dict(d) for d in self._deliveries.values()
                if (campaign_id is None or d["campaign_id"] == campaign_id)
                and (outcome is None or d["outcome"] == outcome)]

    # -- engagements -----------------------------------------------------------

    def record_engagement(self, actor, campaign_id, contact_ref, kind,
                          occurred_at):
        """Record one engagement event (open / click / reply /
        unsubscribe) for a contact on a campaign."""
        self._check_role(actor, "engage")
        _contact_ref(contact_ref)
        if kind not in ENGAGEMENT_KINDS:
            raise ValidationError(
                "kind must be one of %r" % (ENGAGEMENT_KINDS,))
        occurred = _parse_moment(occurred_at, "occurred_at")
        with self._lock:
            self._campaign(campaign_id)
            record = {
                "id": self._mint("eng-"),
                "campaign_id": campaign_id,
                "contact_ref": contact_ref,
                "kind": kind,
                "occurred_at": occurred.isoformat(),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._engagements[record["id"]] = record
        self._record(actor, "record_engagement", record["id"],
                     {"campaign_id": campaign_id, "kind": kind})
        return dict(record)

    def list_engagements(self, actor, campaign_id=None, kind=None):
        self._check_role(actor, "read")
        if kind is not None and kind not in ENGAGEMENT_KINDS:
            raise ValidationError(
                "kind must be one of %r" % (ENGAGEMENT_KINDS,))
        return [dict(e) for e in self._engagements.values()
                if (campaign_id is None or e["campaign_id"] == campaign_id)
                and (kind is None or e["kind"] == kind)]

    def engagement_report(self, actor, campaign_id):
        """The engagement report for one campaign: counts derived
        from its delivery and engagement records, plus the count
        of active suppressions on its list. Counts and recorded
        values only — no rates, no percentages, no scores."""
        self._check_role(actor, "read")
        with self._lock:
            campaign = self._campaign(campaign_id)
            deliveries = [d for d in self._deliveries.values()
                          if d["campaign_id"] == campaign_id]
            engagements = [e for e in self._engagements.values()
                           if e["campaign_id"] == campaign_id]
            by_outcome = {o: 0 for o in DELIVERY_OUTCOMES}
            delivered_contacts = set()
            for delivery in deliveries:
                by_outcome[delivery["outcome"]] += 1
                if delivery["outcome"] == "delivered":
                    delivered_contacts.add(delivery["contact_ref"])
            by_kind = {k: 0 for k in ENGAGEMENT_KINDS}
            for engagement in engagements:
                by_kind[engagement["kind"]] += 1
            suppressed = sum(
                1 for s in self._suppressions.values()
                if s["list_id"] == campaign["list_id"]
                and s["state"] == "active")
            return {
                "campaign_id": campaign_id,
                "status": _derive_campaign_status(
                    campaign, len(deliveries), len(engagements)),
                "deliveries_by_outcome": by_outcome,
                "deliveries_total": len(deliveries),
                "delivered_contacts": len(delivered_contacts),
                "engagements_by_kind": by_kind,
                "engagements_total": len(engagements),
                "active_suppressions_on_list": suppressed,
            }

    # -- search, summary, audit ---------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over the
        registered metadata: organizations, opportunities, contact
        lists, segments, and campaigns."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()

        def hit(*fields):
            return any(needle in (f or "").lower() for f in fields)

        return {
            "organizations": [dict(o) for o in self._organizations.values()
                              if hit(o["ref"], o["label"])],
            "opportunities": [dict(o) for o in self._opportunities.values()
                              if hit(o["ref"], o["agency_label"],
                                     o["title_label"])],
            "contact_lists": [dict(lst) for lst in self._lists.values()
                              if hit(lst["label"])],
            "segments": [dict(s) for s in self._segments.values()
                         if hit(s["label"], s["basis_label"])],
            "campaigns": [self._campaign_view(c)
                          for c in self._campaigns.values()
                          if hit(c["label"])],
        }

    def summary(self, actor):
        """Counts computed on read from the records. Counts only:
        no scores, no rates, no rankings."""
        self._check_role(actor, "read")
        evaluations_by_decision = {d: 0 for d in EVALUATION_DECISIONS}
        for evaluation in self._evaluations.values():
            evaluations_by_decision[evaluation["decision"]] += 1
        pipeline_by_stage = {s: 0 for s in PIPELINE_STAGES}
        for entry in self._pipeline.values():
            pipeline_by_stage[entry["stage"]] += 1
        campaigns_by_status = {s: 0 for s in CAMPAIGN_STATES}
        for campaign in self._campaigns.values():
            campaigns_by_status[self._campaign_view(campaign)["status"]] += 1
        deliveries_by_outcome = {o: 0 for o in DELIVERY_OUTCOMES}
        for delivery in self._deliveries.values():
            deliveries_by_outcome[delivery["outcome"]] += 1
        engagements_by_kind = {k: 0 for k in ENGAGEMENT_KINDS}
        for engagement in self._engagements.values():
            engagements_by_kind[engagement["kind"]] += 1
        suppressions_by_state = {s: 0 for s in SUPPRESSION_STATES}
        for suppression in self._suppressions.values():
            suppressions_by_state[suppression["state"]] += 1
        return {
            "organizations": len(self._organizations),
            "opportunities": len(self._opportunities),
            "evaluations": len(self._evaluations),
            "evaluations_by_decision": evaluations_by_decision,
            "pipeline_entries": len(self._pipeline),
            "pipeline_by_stage": pipeline_by_stage,
            "content_versions": len(self._content),
            "workflows": len(self._workflows),
            "workflows_active": sum(1 for w in self._workflows.values()
                                    if w["active"]),
            "contact_lists": len(self._lists),
            "segments": len(self._segments),
            "campaigns": len(self._campaigns),
            "campaigns_by_status": campaigns_by_status,
            "deliveries": len(self._deliveries),
            "deliveries_by_outcome": deliveries_by_outcome,
            "engagements": len(self._engagements),
            "engagements_by_kind": engagements_by_kind,
            "suppressions": len(self._suppressions),
            "suppressions_by_state": suppressions_by_state,
        }

    def audit_read(self, actor):
        """Return the audit entries (requires ``audit_read``)."""
        self._check_role(actor, "audit_read")
        entries = self.audit.entries() if self.audit is not None else []
        return {"count": len(entries), "entries": entries}
