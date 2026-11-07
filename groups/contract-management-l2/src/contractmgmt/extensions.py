"""Final GAPS batch extensions for Contract Management L2
(Remainder Group 1 — Contract Management L2, new category).

Clean-room, standard-library-only extensions for the 9 open
entries of the "Remainder Group 1 — Contract Management L2"
section of GAPS.md (see ``BATCH.md`` in the group directory for
the per-entry disposition). This module wraps
:class:`ContractMgmtStore`; every core module is untouched and
byte-identical to the shipped build.

**The founding discipline binds absolutely, here as in the
core:** this build is the contract lifecycle system of record.
It holds no regulation text, executes no workflow, runs no
auction, discovers no price, transports nothing, connects to
nothing, and moves no money. Every entity shape in this module
carries metadata and opaque caller-supplied references only,
plus figures and outcomes stored exactly as reported by the
external systems and people who actually did the work. Methods
accept only their named parameters, so a caller cannot smuggle
an unlisted field into a record (pinned by tests: an unexpected
keyword raises ``TypeError``).

Honesty of form, per the batch brief: an "engine" here is its
in-substrate form — records over the group's OWN records (core
records and extension records), plus deterministic derivations
at read:

- Regulatory content is corpus records: clause and supplement
  records held as metadata + SHA-256 digests + citation
  references. The regulation text itself is never held, and
  interpretation is recorded as reported guidance records
  (``interpreted_here`` is False).
- Analytics is deterministic derivation at read over the core
  records: PALT as exact day/second arithmetic between the
  recorded opportunity and award timestamps, bottleneck counts
  from the core's own derived flags, and spend as sums of
  recorded integer cents grouped by the records' own kinds. No
  metric beyond what the records state; nothing is estimated,
  scored, ranked, or evaluated.
- The portal front-end is portal and page *definition* records
  held as data (``rendered_here`` / ``served_here`` False).
- The reverse auction is reported bid and outcome records held
  as data against a core reverse-auction opportunity. Nothing
  here orders, ranks, or compares bids, and no winner or price
  is derived: ``discovered_here`` and ``conducted_here`` are
  False, and recording bids or outcomes is pinned to leave
  every core record byte-identical.
- The three transports (submission intake, communication,
  integration) are receipt / transport / exchange records in
  the Communication line's adjudicated form: every record
  carries ``reference_transport: True`` and
  ``transmitted_here: False`` — the records surface is built;
  the transport itself is the labeled reference.
- Payment rails are settlement records over core payment
  records, capped cumulatively by the linked payment's
  recorded amount; ``settled_here`` and ``moved_here`` are
  False — the core records payments and moves no money, and
  this surface inherits that exactly.
- The workflow execution engine ships as its drafted labeled
  reference implementation: run-request and reported-outcome
  records carrying ``reference_stub: True`` and
  ``executed_here: False``. The core registry never executes,
  and neither does this surface.

Doctrines carried from the core: derived-never-stored for every
computed value (a clause's current digest, transports' and
settlements' current outcome, settlement committed/remaining
amounts, every analytics figure); money is integer cents with
booleans, floats, and strings rejected at the boundary;
append-only audit on the core store's log with ``ext_``-prefixed
actions for every successful mutation and denied write attempts
recorded with a ``:denied`` suffix; RBAC via
:mod:`contractmgmt.access` with the core's existing actions,
enforced before any state change or id allocation, so a failed
operation consumes no id and changes nothing. Organization
membership — the core's second boundary — is enforced on every
operation by validating the organization through the core store.
"""

import copy
import re
import threading
from datetime import datetime, timezone
from fractions import Fraction

from .access import User, require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError
from .store import DIRECTIONS

AUCTION_OUTCOME_LABELS = (
    "reported_completed",
    "reported_no_award",
    "reported_cancelled",
)
SETTLEMENT_REPORT_LABELS = (
    "reported_settled",
    "reported_partial",
    "reported_failed",
)
MESSAGE_REPORT_LABELS = (
    "reported_delivered",
    "reported_failed",
    "reported_undeliverable",
)
WORKFLOW_REPORT_LABELS = (
    "reported_completed",
    "reported_failed",
    "reported_cancelled",
)
EXCHANGE_REPORT_LABELS = (
    "reported_received",
    "reported_rejected",
    "reported_failed",
)

_REFERENCE_STATE = "recorded_reference_only"
_DIGEST_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_moment(value, field):
    """Parse an ISO date or datetime into an aware datetime
    (mirrors the core store's moment semantics)."""
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
            raise ValidationError(
                "%s is not an ISO date or datetime: %r" % (field, value))
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
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % field)
    return value


def _digest(value, field):
    """A SHA-256 digest, held as data: the digest of text held
    elsewhere. The text itself is never accepted here."""
    if not isinstance(value, str) or not _DIGEST_RE.match(value.strip()):
        raise ValidationError(
            "%s must be a 64-character hexadecimal SHA-256 digest" % field)
    return value.strip().lower()


def _cents_nonneg(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be an integer >= 0 (cents)" % field)
    return value


def _cents_positive(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("%s must be a positive integer (cents)" % field)
    return value


def _count_nonneg(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be a non-negative integer" % field)
    return value


def _exact_out(amount):
    """Render an exact Fraction for a view: an int when whole,
    else the exact ``"numerator/denominator"`` string. Nothing
    is rounded."""
    if amount.denominator == 1:
        return amount.numerator
    return "%d/%d" % (amount.numerator, amount.denominator)


def _palt_seconds(start_iso, end_iso):
    """Procurement administrative lead time between two recorded
    timestamps, in whole seconds: exact day/second arithmetic
    over the timedelta's normalized components. Nothing is
    estimated; a span whose end precedes its start is rejected.
    This is the analytics derivation seam."""
    start = _parse_moment(start_iso, "start")
    end = _parse_moment(end_iso, "end")
    delta = end - start
    if delta.total_seconds() < 0:
        raise ValidationError("end precedes start: %r -> %r"
                              % (start_iso, end_iso))
    return delta.days * 86400 + delta.seconds


def _check_settlement_bounds(payment_amount_cents, committed_cents,
                             amount_cents):
    """Enforce the settlement bound for one settlement record.

    ``payment_amount_cents`` is the linked core payment's
    recorded amount; ``committed_cents`` is the total of this
    surface's outstanding settlement amounts against the same
    payment (a settlement whose latest outcome report is
    ``reported_failed`` no longer counts — the rail reported it
    settled nothing). A settlement that would push the committed
    total even one cent over the payment's recorded amount is
    rejected whole. This is the batch's fresh negative-control
    seam (see tests/README.md)."""
    if committed_cents + amount_cents > payment_amount_cents:
        raise ValidationError(
            "settlement exceeds the payment's recorded amount: "
            "payment %d, committed %d, requested %d"
            % (payment_amount_cents, committed_cents, amount_cents))
    return True


class ContractExtensions:
    """Extension surface wrapping one :class:`ContractMgmtStore`."""

    def __init__(self, store):
        self.store = store
        self._clauses = {}
        self._clause_updates = {}
        self._guidance = {}
        self._portals = {}
        self._pages = {}
        self._auction_bids = {}
        self._auction_outcomes = {}
        self._intake_receipts = {}
        self._settlements = {}
        self._settlement_reports = {}
        self._message_transports = {}
        self._message_reports = {}
        self._workflow_requests = {}
        self._workflow_reports = {}
        self._integration_exchanges = {}
        self._exchange_reports = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor, action, target, details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change.

        Mirrors the core convention (a User actor is checked via
        :func:`contractmgmt.access.require`; a plain string
        carries identity but no role, so its role enforcement is
        the service layer's). A denied attempt by a User is
        recorded on the audit log with a ``:denied`` suffix
        before the error propagates; a missing actor is denied
        outright."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if isinstance(actor, User):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _require_role(actor, action):
        if isinstance(actor, User):
            require(actor, action)

    def _org(self, org_id, actor):
        """Validate the organization through the core store: the
        core enforces existence, the ``org_read`` role, and the
        membership boundary."""
        return self.store.get_organization(org_id, actor)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _get_in_org(self, table, org_id, record_id, what):
        record = self._get(table, record_id, what)
        if record["org_id"] != org_id:
            raise NotFoundError(
                "no such %s in organization %s: %r" % (what, org_id, record_id))
        return record

    # -- regulatory content & interpretation ----------------------------

    def record_clause(self, org_id, clause_ref, citation, digest_sha256,
                      source_ref, actor, label=None):
        """Record a regulation-corpus clause as metadata + the
        SHA-256 digest of its text. Action: compliance_write.
        The clause text itself is never accepted or held:
        ``content_held_here`` is False."""
        self._guard(actor, "compliance_write", "ext_clause_create")
        self._org(org_id, actor)
        _text(clause_ref, "clause_ref")
        _text(citation, "citation")
        digest = _digest(digest_sha256, "digest_sha256")
        _text(source_ref, "source_ref")
        _optional_text(label, "label")
        with self._lock:
            for existing in self._clauses.values():
                if (existing["org_id"] == org_id
                        and existing["clause_ref"] == clause_ref):
                    raise ValidationError(
                        "clause_ref %r already exists in organization %s"
                        % (clause_ref, org_id))
            clause = {
                "id": self._next_id("clz-"),
                "org_id": org_id,
                "clause_ref": clause_ref,
                "citation": citation,
                "digest_sha256": digest,
                "source_ref": source_ref,
                "label": label,
                "content_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._clauses[clause["id"]] = clause
        self._audit(actor, "ext_clause_create", clause["id"],
                    {"org_id": org_id})
        return copy.deepcopy(clause)

    def record_clause_update(self, org_id, clause_id, update_ref,
                             digest_sha256, actor, label=None):
        """Record a corpus update against a clause record: the
        digest of the clause text as updated, held as data.
        Action: compliance_write. The updated text itself is
        never accepted or held."""
        self._guard(actor, "compliance_write", "ext_clause_update_record")
        self._org(org_id, actor)
        _text(update_ref, "update_ref")
        digest = _digest(digest_sha256, "digest_sha256")
        _optional_text(label, "label")
        with self._lock:
            self._get_in_org(self._clauses, org_id, clause_id, "clause")
            for existing in self._clause_updates.values():
                if (existing["clause_id"] == clause_id
                        and existing["update_ref"] == update_ref):
                    raise ValidationError(
                        "update_ref %r already exists for clause %s"
                        % (update_ref, clause_id))
            update = {
                "id": self._next_id("cup-"),
                "org_id": org_id,
                "clause_id": clause_id,
                "update_ref": update_ref,
                "digest_sha256": digest,
                "label": label,
                "content_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._clause_updates[update["id"]] = update
        self._audit(actor, "ext_clause_update_record", update["id"],
                    {"org_id": org_id, "clause_id": clause_id})
        return copy.deepcopy(update)

    def list_clauses(self, org_id, actor):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(c) for c in self._clauses.values()
                if c["org_id"] == org_id]

    def list_clause_updates(self, org_id, clause_id, actor):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        self._get_in_org(self._clauses, org_id, clause_id, "clause")
        return [copy.deepcopy(u) for u in self._clause_updates.values()
                if u["clause_id"] == clause_id]

    def clause_view(self, org_id, clause_id, actor):
        """A clause record, its update records, and the current
        digest derived at read: the latest recorded update's
        digest, or the clause's own digest before any update.
        The stored records carry no current-digest key."""
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        clause = self._get_in_org(self._clauses, org_id, clause_id, "clause")
        updates = [u for u in self._clause_updates.values()
                   if u["clause_id"] == clause_id]
        view = copy.deepcopy(clause)
        view["updates"] = copy.deepcopy(updates)
        view["current_digest_sha256"] = (
            updates[-1]["digest_sha256"] if updates
            else clause["digest_sha256"])
        return view

    def record_guidance(self, org_id, guidance_ref, reporter_ref,
                        digest_sha256, actor, clause_id=None,
                        requirement_id=None, label=None):
        """Record an interpretation / guidance report exactly as
        reported: who reported it (an opaque reference), what it
        concerns (a clause record and/or a core compliance
        requirement), and the digest of the guidance text, which
        is held elsewhere. Action: compliance_write. Nothing is
        interpreted here: ``interpreted_here`` is False, and no
        guidance text is accepted or held."""
        self._guard(actor, "compliance_write", "ext_guidance_record")
        self._org(org_id, actor)
        _text(guidance_ref, "guidance_ref")
        _text(reporter_ref, "reporter_ref")
        digest = _digest(digest_sha256, "digest_sha256")
        _optional_text(label, "label")
        with self._lock:
            if clause_id is not None:
                self._get_in_org(self._clauses, org_id, clause_id, "clause")
            if requirement_id is not None:
                self.store.get_requirement(org_id, requirement_id, actor)
            for existing in self._guidance.values():
                if (existing["org_id"] == org_id
                        and existing["guidance_ref"] == guidance_ref):
                    raise ValidationError(
                        "guidance_ref %r already exists in organization %s"
                        % (guidance_ref, org_id))
            guidance = {
                "id": self._next_id("gui-"),
                "org_id": org_id,
                "guidance_ref": guidance_ref,
                "clause_id": clause_id,
                "requirement_id": requirement_id,
                "reporter_ref": reporter_ref,
                "digest_sha256": digest,
                "label": label,
                "interpreted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._guidance[guidance["id"]] = guidance
        self._audit(actor, "ext_guidance_record", guidance["id"],
                    {"org_id": org_id})
        return copy.deepcopy(guidance)

    def list_guidance(self, org_id, actor, clause_id=None):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(g) for g in self._guidance.values()
                if g["org_id"] == org_id
                and (clause_id is None or g["clause_id"] == clause_id)]

    # -- opportunity portal front-end -----------------------------------

    def define_portal(self, org_id, portal_ref, label, actor):
        """Define an opportunity portal front-end as data: a
        portal definition record. Action: portal_write. Nothing
        is rendered or served here: ``rendered_here`` and
        ``served_here`` are False."""
        self._guard(actor, "portal_write", "ext_portal_define")
        self._org(org_id, actor)
        _text(portal_ref, "portal_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._portals.values():
                if (existing["org_id"] == org_id
                        and existing["portal_ref"] == portal_ref):
                    raise ValidationError(
                        "portal_ref %r already exists in organization %s"
                        % (portal_ref, org_id))
            portal = {
                "id": self._next_id("por-"),
                "org_id": org_id,
                "portal_ref": portal_ref,
                "label": label,
                "rendered_here": False,
                "served_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._portals[portal["id"]] = portal
        self._audit(actor, "ext_portal_define", portal["id"],
                    {"org_id": org_id})
        return copy.deepcopy(portal)

    def define_page(self, org_id, portal_id, page_ref, actor, label=None,
                    opportunity_id=None):
        """Define a portal page as data, optionally bound to a
        core opportunity record. Action: portal_write. The page
        is a definition; nothing is rendered here."""
        self._guard(actor, "portal_write", "ext_page_define")
        self._org(org_id, actor)
        _text(page_ref, "page_ref")
        _optional_text(label, "label")
        with self._lock:
            self._get_in_org(self._portals, org_id, portal_id, "portal")
            if opportunity_id is not None:
                self.store.get_opportunity(org_id, opportunity_id, actor)
            for existing in self._pages.values():
                if (existing["portal_id"] == portal_id
                        and existing["page_ref"] == page_ref):
                    raise ValidationError(
                        "page_ref %r already exists for portal %s"
                        % (page_ref, portal_id))
            page = {
                "id": self._next_id("pge-"),
                "org_id": org_id,
                "portal_id": portal_id,
                "page_ref": page_ref,
                "label": label,
                "opportunity_id": opportunity_id,
                "rendered_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._pages[page["id"]] = page
        self._audit(actor, "ext_page_define", page["id"],
                    {"org_id": org_id, "portal_id": portal_id})
        return copy.deepcopy(page)

    def list_portals(self, org_id, actor):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(p) for p in self._portals.values()
                if p["org_id"] == org_id]

    def portal_view(self, org_id, portal_id, actor):
        """A portal definition and its page definitions, in
        recording order."""
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        portal = self._get_in_org(self._portals, org_id, portal_id, "portal")
        view = copy.deepcopy(portal)
        view["pages"] = [copy.deepcopy(p) for p in self._pages.values()
                         if p["portal_id"] == portal_id]
        return view

    # -- reverse auction engine ------------------------------------------

    def _auction_opportunity(self, org_id, opportunity_id, actor):
        opportunity = self.store.get_opportunity(org_id, opportunity_id,
                                                 actor)
        if opportunity["kind"] != "reverse_auction":
            raise ValidationError(
                "opportunity %s is not a reverse auction (kind %r)"
                % (opportunity_id, opportunity["kind"]))
        return opportunity

    def _require_registered_participant(self, participant_ref, actor):
        for participant in self.store.list_participants(actor):
            if participant["participant_ref"] == participant_ref:
                return participant
        raise ValidationError(
            "participant %r is not registered" % (participant_ref,))

    def record_auction_bid(self, org_id, opportunity_id, bid_ref,
                           participant_ref, amount_cents, actor):
        """Record a bid in a reverse auction exactly as reported:
        an opaque bid reference, the bidding participant's opaque
        reference, and the bid amount in integer cents, held as
        data. Action: portal_write.

        Nothing here orders, ranks, or compares bids, and no
        winner or price is derived: ``discovered_here`` and
        ``conducted_here`` are False. Recording a bid changes no
        core record."""
        self._guard(actor, "portal_write", "ext_auction_bid_record")
        self._org(org_id, actor)
        _text(bid_ref, "bid_ref")
        _text(participant_ref, "participant_ref")
        _cents_nonneg(amount_cents, "amount_cents")
        with self._lock:
            self._auction_opportunity(org_id, opportunity_id, actor)
            self._require_registered_participant(participant_ref, actor)
            for existing in self._auction_bids.values():
                if (existing["opportunity_id"] == opportunity_id
                        and existing["bid_ref"] == bid_ref):
                    raise ValidationError(
                        "bid_ref %r already exists in opportunity %s"
                        % (bid_ref, opportunity_id))
            bid = {
                "id": self._next_id("bid-"),
                "org_id": org_id,
                "opportunity_id": opportunity_id,
                "bid_ref": bid_ref,
                "participant_ref": participant_ref,
                "amount_cents": amount_cents,
                "discovered_here": False,
                "conducted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._auction_bids[bid["id"]] = bid
        self._audit(actor, "ext_auction_bid_record", bid["id"],
                    {"org_id": org_id, "opportunity_id": opportunity_id})
        return copy.deepcopy(bid)

    def record_auction_outcome(self, org_id, opportunity_id, outcome_ref,
                               outcome_label, actor,
                               reported_winner_ref=None):
        """Record a reverse auction's outcome exactly as the
        conducting platform reported it: a reported outcome label
        and, when reported, the winner's opaque reference, held
        verbatim as reported data. Action: portal_write. The
        reported winner is not a derivation and changes nothing
        in the core: any award stays a core award record, made
        through the core."""
        self._guard(actor, "portal_write", "ext_auction_outcome_record")
        self._org(org_id, actor)
        _text(outcome_ref, "outcome_ref")
        if outcome_label not in AUCTION_OUTCOME_LABELS:
            raise ValidationError(
                "unknown auction outcome label: %r" % (outcome_label,))
        _optional_text(reported_winner_ref, "reported_winner_ref")
        with self._lock:
            self._auction_opportunity(org_id, opportunity_id, actor)
            for existing in self._auction_outcomes.values():
                if (existing["opportunity_id"] == opportunity_id
                        and existing["outcome_ref"] == outcome_ref):
                    raise ValidationError(
                        "outcome_ref %r already exists in opportunity %s"
                        % (outcome_ref, opportunity_id))
            outcome = {
                "id": self._next_id("auc-"),
                "org_id": org_id,
                "opportunity_id": opportunity_id,
                "outcome_ref": outcome_ref,
                "outcome_label": outcome_label,
                "reported_winner_ref": reported_winner_ref,
                "discovered_here": False,
                "conducted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._auction_outcomes[outcome["id"]] = outcome
        self._audit(actor, "ext_auction_outcome_record", outcome["id"],
                    {"org_id": org_id, "opportunity_id": opportunity_id})
        return copy.deepcopy(outcome)

    def list_auction_bids(self, org_id, opportunity_id, actor):
        """Bid records for an opportunity, in recording order.
        No ordering by amount is applied or implied."""
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        self._auction_opportunity(org_id, opportunity_id, actor)
        return [copy.deepcopy(b) for b in self._auction_bids.values()
                if b["opportunity_id"] == opportunity_id]

    def auction_view(self, org_id, opportunity_id, actor, now=None):
        """A reverse-auction opportunity's core view beside its
        reported bid and outcome records. The bid records are
        listed in recording order; this view derives no winner,
        no lowest bid, and no price — those keys do not exist."""
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        opportunity = self._auction_opportunity(org_id, opportunity_id,
                                                actor)
        view = {
            "opportunity": self.store.get_opportunity(
                org_id, opportunity_id, actor, now=now),
            "bids": [copy.deepcopy(b) for b in self._auction_bids.values()
                     if b["opportunity_id"] == opportunity_id],
            "outcomes": [copy.deepcopy(o)
                         for o in self._auction_outcomes.values()
                         if o["opportunity_id"] == opportunity_id],
        }
        view["bid_count"] = len(view["bids"])
        view["outcome_count"] = len(view["outcomes"])
        return view

    # -- submission intake transport --------------------------------------

    def record_intake_receipt(self, org_id, submission_id, receipt_ref,
                              channel_ref, actor,
                              reported_digest_sha256=None):
        """Record an intake receipt for a core submission: the
        electronic channel's reported receipt of a bid or
        proposal, as a record. Action: portal_write. The receipt
        carries ``reference_transport: True`` and
        ``transmitted_here: False`` — the transport is the
        channel's; what is built here is the records surface.
        A reported digest of what the channel received may be
        recorded as data; the received content itself is never
        accepted or held (``content_held_here: False``)."""
        self._guard(actor, "portal_write", "ext_intake_receipt_record")
        self._org(org_id, actor)
        _text(receipt_ref, "receipt_ref")
        _text(channel_ref, "channel_ref")
        digest = None
        if reported_digest_sha256 is not None:
            digest = _digest(reported_digest_sha256,
                             "reported_digest_sha256")
        with self._lock:
            self.store.get_submission(org_id, submission_id, actor)
            for existing in self._intake_receipts.values():
                if (existing["org_id"] == org_id
                        and existing["receipt_ref"] == receipt_ref):
                    raise ValidationError(
                        "receipt_ref %r already exists in organization %s"
                        % (receipt_ref, org_id))
            receipt = {
                "id": self._next_id("rcp-"),
                "org_id": org_id,
                "submission_id": submission_id,
                "receipt_ref": receipt_ref,
                "channel_ref": channel_ref,
                "reported_digest_sha256": digest,
                "reference_transport": True,
                "transmitted_here": False,
                "content_held_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._intake_receipts[receipt["id"]] = receipt
        self._audit(actor, "ext_intake_receipt_record", receipt["id"],
                    {"org_id": org_id, "submission_id": submission_id})
        return copy.deepcopy(receipt)

    def list_intake_receipts(self, org_id, actor, submission_id=None):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(r) for r in self._intake_receipts.values()
                if r["org_id"] == org_id
                and (submission_id is None
                     or r["submission_id"] == submission_id)]

    # -- payment processing rails ------------------------------------------

    def _core_payment(self, org_id, payment_id, actor):
        for payment in self.store.list_payments(org_id, actor):
            if payment["id"] == payment_id:
                return payment
        raise NotFoundError(
            "no such payment in organization %s: %r" % (org_id, payment_id))

    def _settlement_reports_for(self, settlement_id):
        return [r for r in self._settlement_reports.values()
                if r["settlement_id"] == settlement_id]

    def _current_settlement_outcome(self, settlement_id):
        reports = self._settlement_reports_for(settlement_id)
        if not reports:
            return "recorded"
        return reports[-1]["outcome_label"]

    def _committed_cents(self, payment_id):
        """Outstanding settlement total against one payment,
        derived from the records: every settlement counts at its
        full recorded amount, except one whose latest outcome
        report is ``reported_failed`` (the rail reported it
        settled nothing, so it no longer commits the payment)."""
        total = 0
        for settlement in self._settlements.values():
            if settlement["payment_id"] != payment_id:
                continue
            if self._current_settlement_outcome(
                    settlement["id"]) == "reported_failed":
                continue
            total += settlement["amount_cents"]
        return total

    def record_settlement(self, org_id, payment_id, settlement_ref,
                          amount_cents, actor):
        """Record a settlement against a core payment record.
        Action: payment_write. The settlement is a record over
        the payment; no money moves here (``settled_here`` and
        ``moved_here`` are False) — the core records payments
        and moves no money, and this surface inherits that
        exactly.

        Bound: the settlement total outstanding against a
        payment may never exceed the payment's recorded amount,
        enforced by the ``_check_settlement_bounds`` seam before
        anything is stored."""
        self._guard(actor, "payment_write", "ext_settlement_record")
        self._org(org_id, actor)
        _text(settlement_ref, "settlement_ref")
        _cents_positive(amount_cents, "amount_cents")
        with self._lock:
            payment = self._core_payment(org_id, payment_id, actor)
            for existing in self._settlements.values():
                if (existing["org_id"] == org_id
                        and existing["settlement_ref"] == settlement_ref):
                    raise ValidationError(
                        "settlement_ref %r already exists in organization %s"
                        % (settlement_ref, org_id))
            _check_settlement_bounds(payment["amount_cents"],
                                     self._committed_cents(payment_id),
                                     amount_cents)
            settlement = {
                "id": self._next_id("set-"),
                "org_id": org_id,
                "payment_id": payment_id,
                "settlement_ref": settlement_ref,
                "amount_cents": amount_cents,
                "settled_here": False,
                "moved_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._settlements[settlement["id"]] = settlement
        self._audit(actor, "ext_settlement_record", settlement["id"],
                    {"org_id": org_id, "payment_id": payment_id})
        return copy.deepcopy(settlement)

    def record_settlement_report(self, org_id, settlement_id, report_ref,
                                 outcome_label, actor):
        """Record a settlement outcome exactly as the rail
        reported it. Action: payment_write. The label is stored
        verbatim; nothing is settled here."""
        self._guard(actor, "payment_write", "ext_settlement_report_record")
        self._org(org_id, actor)
        _text(report_ref, "report_ref")
        if outcome_label not in SETTLEMENT_REPORT_LABELS:
            raise ValidationError(
                "unknown settlement outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get_in_org(self._settlements, org_id, settlement_id,
                             "settlement")
            for existing in self._settlement_reports.values():
                if (existing["settlement_id"] == settlement_id
                        and existing["report_ref"] == report_ref):
                    raise ValidationError(
                        "report_ref %r already exists for settlement %s"
                        % (report_ref, settlement_id))
            report = {
                "id": self._next_id("srp-"),
                "org_id": org_id,
                "settlement_id": settlement_id,
                "report_ref": report_ref,
                "outcome_label": outcome_label,
                "settled_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._settlement_reports[report["id"]] = report
        self._audit(actor, "ext_settlement_report_record", report["id"],
                    {"org_id": org_id, "settlement_id": settlement_id})
        return copy.deepcopy(report)

    def settlement_view(self, org_id, settlement_id, actor):
        """A settlement record, its outcome reports, and the
        current outcome derived at read (the latest recorded
        report label; ``recorded`` before any report). The
        stored settlement record carries no state key."""
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        settlement = self._get_in_org(self._settlements, org_id,
                                      settlement_id, "settlement")
        view = copy.deepcopy(settlement)
        view["reports"] = copy.deepcopy(
            self._settlement_reports_for(settlement_id))
        view["current_outcome"] = self._current_settlement_outcome(
            settlement_id)
        return view

    def list_settlements(self, org_id, actor, payment_id=None):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(s) for s in self._settlements.values()
                if s["org_id"] == org_id
                and (payment_id is None or s["payment_id"] == payment_id)]

    def payment_settlement_summary(self, org_id, payment_id, actor):
        """Derived at read over the settlement records for one
        core payment: the payment's recorded amount, the
        committed (outstanding) total, the remaining headroom,
        and the settlement count. Stored nowhere."""
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        payment = self._core_payment(org_id, payment_id, actor)
        committed = self._committed_cents(payment_id)
        settlements = [s for s in self._settlements.values()
                       if s["payment_id"] == payment_id]
        return {
            "payment_id": payment_id,
            "payment_amount_cents": payment["amount_cents"],
            "committed_cents": committed,
            "remaining_cents": payment["amount_cents"] - committed,
            "settlement_count": len(settlements),
        }

    # -- communication transport -------------------------------------------

    def _core_communication(self, org_id, communication_id, actor):
        for comm in self.store.list_communications(org_id, actor):
            if comm["id"] == communication_id:
                return comm
        raise NotFoundError(
            "no such communication in organization %s: %r"
            % (org_id, communication_id))

    def record_message_transport(self, org_id, communication_id,
                                 transport_ref, channel_ref, actor):
        """Record the transport of a core communication record
        over the secure messaging channel, as a record. Action:
        comm_write. The record carries ``reference_transport:
        True`` and ``transmitted_here: False`` — the channel is
        the embedding organization's; what is built here is the
        records surface. The core communication is metadata
        only, and this record adds no content field."""
        self._guard(actor, "comm_write", "ext_message_transport_record")
        self._org(org_id, actor)
        _text(transport_ref, "transport_ref")
        _text(channel_ref, "channel_ref")
        with self._lock:
            self._core_communication(org_id, communication_id, actor)
            for existing in self._message_transports.values():
                if (existing["org_id"] == org_id
                        and existing["transport_ref"] == transport_ref):
                    raise ValidationError(
                        "transport_ref %r already exists in organization %s"
                        % (transport_ref, org_id))
            transport = {
                "id": self._next_id("mtr-"),
                "org_id": org_id,
                "communication_id": communication_id,
                "transport_ref": transport_ref,
                "channel_ref": channel_ref,
                "reference_transport": True,
                "transmitted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._message_transports[transport["id"]] = transport
        self._audit(actor, "ext_message_transport_record", transport["id"],
                    {"org_id": org_id, "communication_id": communication_id})
        return copy.deepcopy(transport)

    def record_message_report(self, org_id, transport_id, report_ref,
                              outcome_label, actor):
        """Record a message-transport outcome exactly as the
        channel reported it. Action: comm_write."""
        self._guard(actor, "comm_write", "ext_message_report_record")
        self._org(org_id, actor)
        _text(report_ref, "report_ref")
        if outcome_label not in MESSAGE_REPORT_LABELS:
            raise ValidationError(
                "unknown message outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get_in_org(self._message_transports, org_id, transport_id,
                             "message transport")
            for existing in self._message_reports.values():
                if (existing["transport_id"] == transport_id
                        and existing["report_ref"] == report_ref):
                    raise ValidationError(
                        "report_ref %r already exists for transport %s"
                        % (report_ref, transport_id))
            report = {
                "id": self._next_id("mrp-"),
                "org_id": org_id,
                "transport_id": transport_id,
                "report_ref": report_ref,
                "outcome_label": outcome_label,
                "transmitted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._message_reports[report["id"]] = report
        self._audit(actor, "ext_message_report_record", report["id"],
                    {"org_id": org_id, "transport_id": transport_id})
        return copy.deepcopy(report)

    def message_transport_view(self, org_id, transport_id, actor):
        """A transport record, its outcome reports, and the
        current outcome derived at read (the latest recorded
        report label; ``recorded`` before any report). The
        stored transport record carries no state key."""
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        transport = self._get_in_org(self._message_transports, org_id,
                                     transport_id, "message transport")
        reports = [r for r in self._message_reports.values()
                   if r["transport_id"] == transport_id]
        view = copy.deepcopy(transport)
        view["reports"] = copy.deepcopy(reports)
        view["current_outcome"] = (
            reports[-1]["outcome_label"] if reports else "recorded")
        return view

    def list_message_transports(self, org_id, actor, communication_id=None):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(t) for t in self._message_transports.values()
                if t["org_id"] == org_id
                and (communication_id is None
                     or t["communication_id"] == communication_id)]

    # -- workflow execution engine (labeled reference) ----------------------

    def _core_workflow(self, org_id, workflow_id, actor):
        for workflow in self.store.list_workflows(org_id, actor):
            if workflow["id"] == workflow_id:
                return workflow
        raise NotFoundError(
            "no such workflow in organization %s: %r" % (org_id, workflow_id))

    def request_workflow_run(self, org_id, workflow_id, request_ref, actor):
        """Record a workflow execution request against a core
        workflow definition. Action: registry_write. This is a
        labeled reference implementation: the record carries
        ``reference_stub: True`` and ``executed_here: False`` —
        the core registry never executes, and neither does this
        surface. Recording a request changes no core record."""
        self._guard(actor, "registry_write", "ext_workflow_request_record")
        self._org(org_id, actor)
        _text(request_ref, "request_ref")
        with self._lock:
            self._core_workflow(org_id, workflow_id, actor)
            for existing in self._workflow_requests.values():
                if (existing["org_id"] == org_id
                        and existing["request_ref"] == request_ref):
                    raise ValidationError(
                        "request_ref %r already exists in organization %s"
                        % (request_ref, org_id))
            request = {
                "id": self._next_id("wrq-"),
                "org_id": org_id,
                "workflow_id": workflow_id,
                "request_ref": request_ref,
                "reference_stub": True,
                "executed_here": False,
                "state": _REFERENCE_STATE,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_requests[request["id"]] = request
        self._audit(actor, "ext_workflow_request_record", request["id"],
                    {"org_id": org_id, "workflow_id": workflow_id})
        return copy.deepcopy(request)

    def record_workflow_report(self, org_id, request_id, report_ref,
                               outcome_label, actor):
        """Record a workflow execution outcome exactly as the
        external engine reported it. Action: registry_write.
        Nothing executed here."""
        self._guard(actor, "registry_write", "ext_workflow_report_record")
        self._org(org_id, actor)
        _text(report_ref, "report_ref")
        if outcome_label not in WORKFLOW_REPORT_LABELS:
            raise ValidationError(
                "unknown workflow outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get_in_org(self._workflow_requests, org_id, request_id,
                             "workflow request")
            for existing in self._workflow_reports.values():
                if (existing["request_id"] == request_id
                        and existing["report_ref"] == report_ref):
                    raise ValidationError(
                        "report_ref %r already exists for request %s"
                        % (report_ref, request_id))
            report = {
                "id": self._next_id("wrp-"),
                "org_id": org_id,
                "request_id": request_id,
                "report_ref": report_ref,
                "outcome_label": outcome_label,
                "reference_stub": True,
                "executed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._workflow_reports[report["id"]] = report
        self._audit(actor, "ext_workflow_report_record", report["id"],
                    {"org_id": org_id, "request_id": request_id})
        return copy.deepcopy(report)

    def list_workflow_requests(self, org_id, actor, workflow_id=None):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(r) for r in self._workflow_requests.values()
                if r["org_id"] == org_id
                and (workflow_id is None or r["workflow_id"] == workflow_id)]

    def list_workflow_reports(self, org_id, actor, request_id=None):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(r) for r in self._workflow_reports.values()
                if r["org_id"] == org_id
                and (request_id is None or r["request_id"] == request_id)]

    # -- integration transport ----------------------------------------------

    def _core_integration(self, org_id, integration_id, actor):
        for integration in self.store.list_integrations(org_id, actor):
            if integration["id"] == integration_id:
                return integration
        raise NotFoundError(
            "no such integration in organization %s: %r"
            % (org_id, integration_id))

    def record_integration_exchange(self, org_id, integration_id,
                                    exchange_ref, direction,
                                    records_reported, actor):
        """Record a system-to-system exchange over a core
        integration record, as a record: the interface, a
        direction, and the record count exactly as the interface
        reported it. Action: registry_write. The record carries
        ``reference_transport: True``, ``transmitted_here:
        False``, and ``connected_here: False`` — the interface
        itself is the other systems'; what is built here is the
        records surface. No exchanged content is accepted or
        held."""
        self._guard(actor, "registry_write",
                    "ext_integration_exchange_record")
        self._org(org_id, actor)
        _text(exchange_ref, "exchange_ref")
        if direction not in DIRECTIONS:
            raise ValidationError("unknown direction: %r" % (direction,))
        _count_nonneg(records_reported, "records_reported")
        with self._lock:
            self._core_integration(org_id, integration_id, actor)
            for existing in self._integration_exchanges.values():
                if (existing["org_id"] == org_id
                        and existing["exchange_ref"] == exchange_ref):
                    raise ValidationError(
                        "exchange_ref %r already exists in organization %s"
                        % (exchange_ref, org_id))
            exchange = {
                "id": self._next_id("xch-"),
                "org_id": org_id,
                "integration_id": integration_id,
                "exchange_ref": exchange_ref,
                "direction": direction,
                "records_reported": records_reported,
                "reference_transport": True,
                "transmitted_here": False,
                "connected_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._integration_exchanges[exchange["id"]] = exchange
        self._audit(actor, "ext_integration_exchange_record", exchange["id"],
                    {"org_id": org_id, "integration_id": integration_id})
        return copy.deepcopy(exchange)

    def record_exchange_report(self, org_id, exchange_id, report_ref,
                               outcome_label, actor):
        """Record an exchange outcome exactly as the interface
        reported it. Action: registry_write."""
        self._guard(actor, "registry_write", "ext_exchange_report_record")
        self._org(org_id, actor)
        _text(report_ref, "report_ref")
        if outcome_label not in EXCHANGE_REPORT_LABELS:
            raise ValidationError(
                "unknown exchange outcome label: %r" % (outcome_label,))
        with self._lock:
            self._get_in_org(self._integration_exchanges, org_id, exchange_id,
                             "integration exchange")
            for existing in self._exchange_reports.values():
                if (existing["exchange_id"] == exchange_id
                        and existing["report_ref"] == report_ref):
                    raise ValidationError(
                        "report_ref %r already exists for exchange %s"
                        % (report_ref, exchange_id))
            report = {
                "id": self._next_id("xrp-"),
                "org_id": org_id,
                "exchange_id": exchange_id,
                "report_ref": report_ref,
                "outcome_label": outcome_label,
                "reference_transport": True,
                "transmitted_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._exchange_reports[report["id"]] = report
        self._audit(actor, "ext_exchange_report_record", report["id"],
                    {"org_id": org_id, "exchange_id": exchange_id})
        return copy.deepcopy(report)

    def exchange_view(self, org_id, exchange_id, actor):
        """An exchange record, its outcome reports, and the
        current outcome derived at read (the latest recorded
        report label; ``recorded`` before any report). The
        stored exchange record carries no state key."""
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        exchange = self._get_in_org(self._integration_exchanges, org_id,
                                    exchange_id, "integration exchange")
        reports = [r for r in self._exchange_reports.values()
                   if r["exchange_id"] == exchange_id]
        view = copy.deepcopy(exchange)
        view["reports"] = copy.deepcopy(reports)
        view["current_outcome"] = (
            reports[-1]["outcome_label"] if reports else "recorded")
        return view

    def list_integration_exchanges(self, org_id, actor, integration_id=None):
        self._require_role(actor, "org_read")
        self._org(org_id, actor)
        return [copy.deepcopy(x) for x in self._integration_exchanges.values()
                if x["org_id"] == org_id
                and (integration_id is None
                     or x["integration_id"] == integration_id)]

    # -- analytics engine (deterministic derivation at read) -----------------

    def palt_report(self, org_id, actor):
        """PALT measurement, derived at read: for every core
        award in the organization, the exact whole-second span
        between the recorded opportunity creation and the
        recorded award creation — the lead time this substrate's
        own records state. Action: report_read. Nothing is
        estimated: opportunities without awards contribute no
        span, and the summary is exact arithmetic over the
        recorded spans (the mean is an exact integer or an exact
        fraction string, never rounded)."""
        self._require_role(actor, "report_read")
        self._org(org_id, actor)
        entries = []
        for opportunity in self.store.list_opportunities(org_id, actor):
            for award in self.store.list_awards(org_id, opportunity["id"],
                                                actor):
                entries.append({
                    "opportunity_id": opportunity["id"],
                    "award_id": award["id"],
                    "palt_seconds": _palt_seconds(opportunity["created_utc"],
                                                  award["created_utc"]),
                })
        if entries:
            spans = [e["palt_seconds"] for e in entries]
            total = sum(spans)
            summary = {
                "award_count": len(entries),
                "total_seconds": total,
                "mean_seconds": _exact_out(Fraction(total, len(spans))),
                "min_seconds": min(spans),
                "max_seconds": max(spans),
            }
        else:
            summary = {
                "award_count": 0,
                "total_seconds": 0,
                "mean_seconds": None,
                "min_seconds": None,
                "max_seconds": None,
            }
        return {"org_id": org_id, "entries": entries, "summary": summary}

    def bottleneck_report(self, org_id, actor, now=None):
        """Bottleneck analysis, derived at read from the core's
        own records and derived flags: where recorded work is
        waiting. Action: report_read. Counts only — no stage is
        scored or ranked."""
        self._require_role(actor, "report_read")
        self._org(org_id, actor)
        opportunities = self.store.list_opportunities(org_id, actor,
                                                      now=now)
        awaiting = 0
        for opportunity in opportunities:
            for submission in self.store.list_submissions(
                    org_id, opportunity["id"], actor):
                if not submission["awarded"]:
                    awaiting += 1
        protests = self.store.list_protests(org_id, actor, now=now)
        datacalls = self.store.list_datacalls(org_id, actor, now=now)
        contracts = self.store.list_contracts(org_id, actor, now=now)
        return {
            "org_id": org_id,
            "opportunities_open_past_close": sum(
                1 for o in opportunities
                if o["status"] == "open" and o["past_close"]),
            "submissions_awaiting_award": awaiting,
            "protests_open_overdue": sum(
                1 for p in protests
                if p["status"] == "open" and p["overdue"]),
            "datacalls_open_overdue": sum(
                1 for d in datacalls
                if d["status"] == "open" and d["overdue"]),
            "contracts_active_period_elapsed": sum(
                1 for c in contracts
                if c["status"] == "active" and c["period_elapsed"]),
            "requirements_open": len(
                self.store.list_requirements(org_id, actor, status="open")),
        }

    def spend_report(self, org_id, actor):
        """Spend analysis, derived at read: recorded award cents
        summed by the opportunity kind the records themselves
        carry, award counts by kind, and the net recorded
        modification cents across the organization's contracts.
        Action: report_read. Sums of recorded quantities only."""
        self._require_role(actor, "report_read")
        self._org(org_id, actor)
        award_cents_by_kind = {}
        award_count_by_kind = {}
        for opportunity in self.store.list_opportunities(org_id, actor):
            awards = self.store.list_awards(org_id, opportunity["id"],
                                            actor)
            if not awards:
                continue
            kind = opportunity["kind"]
            award_count_by_kind[kind] = (
                award_count_by_kind.get(kind, 0) + len(awards))
            award_cents_by_kind[kind] = award_cents_by_kind.get(kind, 0) + sum(
                a["amount_cents"] for a in awards)
        net_modification_cents = 0
        for contract in self.store.list_contracts(org_id, actor):
            for modification in self.store.list_modifications(
                    org_id, contract["id"], actor):
                net_modification_cents += modification["amount_cents"]
        return {
            "org_id": org_id,
            "award_cents_by_kind": award_cents_by_kind,
            "award_count_by_kind": award_count_by_kind,
            "net_modification_cents": net_modification_cents,
        }

    def analytics_report(self, org_id, actor, now=None):
        """The analytics surface in one read: PALT measurement,
        bottleneck counts, and spend sums, each derived at read
        from the core records by the derivations above.
        ``method`` names the derivation honestly: deterministic
        arithmetic over recorded quantities — no estimation, no
        scoring, no ranking."""
        self._require_role(actor, "report_read")
        self._org(org_id, actor)
        return {
            "org_id": org_id,
            "method": "deterministic_derivation",
            "palt": self.palt_report(org_id, actor),
            "bottlenecks": self.bottleneck_report(org_id, actor, now=now),
            "spend": self.spend_report(org_id, actor),
        }
