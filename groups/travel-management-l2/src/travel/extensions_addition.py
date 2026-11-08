"""Final GAPS batch extensions, second unit, for Travel
Management L2 (Singleton 55): the remainder-addition section.

Clean-room, standard-library-only extensions for the 2 open
entries of the "Remainder Addition — Travel Management L2
(+1 fork)" section of GAPS.md (see ``BATCH-ADDITION.md`` in the
group directory for the per-entry disposition). This module is
a wrapper around :class:`TravelStore`; every pre-existing
module — the core and the first batch unit's ``extensions.py``
— is untouched and byte-identical to the shipped build.

The addition fork (mLINQS Hosting Service) is a relocation
platform: its marketplace description asserts, in its own
words, processing and managing employee relocations and
automating the FTR, JTR, DSSR, and 6FAM CONUS/OCONUS relocation
policy corpus. Neither function has a family in this group's
taxonomy (defined from the founding fork's suite-list
vocabulary), so both were registered as gaps of the addition
section. Their in-substrate forms, under the founding
discipline that binds the whole group:

- **Relocation management & processing** is relocation *case
  records*: a case bound to a core organization and a core
  traveler (opaque reference only), holding origin and
  destination as labels, a move date, and an estimated cost in
  integer cents. The case lifecycle (draft → submitted →
  approved / declined) is event-driven and stored, exactly as
  in the core, with the decider never the case's creator; the
  processing itself is milestone event records whose outcomes
  and amounts are stored verbatim as reported by the people
  and systems doing the moving. No one is moved here: nobody
  is relocated, no household goods are shipped, no carrier is
  engaged (``moved_here`` / ``relocated_here`` /
  ``processed_here`` are False). A relocation is a permanent
  move, distinct from a trip: a case is never bound to a core
  trip authorization, and creating one leaves every core
  record byte-identical.
- **Relocation policy & entitlement rules automation** is
  policy *rule definitions as data* plus a deterministic
  entitlement evaluation derived at read. A rule record names
  the corpus it was recorded under (the corpora the fork names
  in its own words — FTR, JTR, DSSR, 6FAM — held as labels),
  an entitlement kind, and a cap in integer cents: recorded
  parameters, never the corpus itself (``corpus_text_held``
  False; no field can hold regulation text). Entitlement
  claims are records against an approved case and a recorded
  rule, holding the claimed figure verbatim and no
  determination. The determination — allowed and excess
  against the recorded cap — is *derived at read* by the seam
  :meth:`TravelExtensionsAddition._derive_entitlement` from
  the recorded claims and the recorded rule caps only, and the
  evaluation view states that basis on its face. Nothing is
  executed against any external system, and no per-diem is
  computed anywhere: per-diem computation remains the recorded
  absence the addendum states (the fork automates relocation
  *policy* without naming any per-diem computation), there is
  no rate-times-days shape on this surface, and
  ``per_diem_computed_here`` is False on every policy shape.

Doctrines carried from the core and the first unit:
derived-never-stored (event totals, claim totals, entitlement
determinations, case reported totals); money is integer cents,
with booleans and floats rejected at the boundary; append-only
audit on the core store's log with ``exta_``-prefixed actions
for every successful mutation of this unit, denied write
attempts recorded with a ``:denied`` suffix; RBAC via
:mod:`travel.access` (``enter`` for case and rule definitions,
``record`` for events and claims, ``decide`` for case
decisions), enforced before any state change or id allocation,
so a failed operation consumes no id and changes nothing;
organization membership enforced through the core store's own
access checks. Methods accept only their named parameters, so
no caller can smuggle an unlisted field into a record (pinned
by tests: an unexpected keyword raises ``TypeError`` — no
employee name, no document number, no per-diem rate can enter
any shape).
"""

import copy
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

RELOCATION_EVENT_KINDS = (
    "household_goods",
    "temporary_quarters",
    "travel",
    "storage",
    "closeout",
    "other",
)
RELOCATION_EVENT_OUTCOMES = (
    "reported_completed",
    "reported_in_progress",
    "reported_failed",
)
POLICY_CORPORA = ("ftr", "jtr", "dssr", "6fam", "other")
ENTITLEMENT_KINDS = (
    "household_goods",
    "temporary_quarters",
    "house_hunting",
    "real_property",
    "miscellaneous",
    "other",
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


def _money(value, field, allow_zero=True):
    """Integer cents; booleans and floats rejected (core discipline)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % field)
    if allow_zero and value < 0:
        raise ValidationError("%s must not be negative" % field)
    if not allow_zero and value <= 0:
        raise ValidationError("%s must be positive" % field)
    return value


def _date(value, field):
    _text(value, field)
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValidationError("%s must be a YYYY-MM-DD date" % field)
    return value


def _latest_outcome(reports):
    """The current outcome of a case's processing: the latest
    event's outcome label, or None. Derived at read; never
    stored on the case record."""
    if not reports:
        return None
    return reports[-1]["outcome_label"]


class TravelExtensionsAddition:
    """Second-unit extension surface wrapping one TravelStore."""

    def __init__(self, store):
        self.store = store
        self._relocation_cases = {}
        self._relocation_decisions = {}
        self._relocation_events = {}
        self._policy_rules = {}
        self._entitlement_claims = {}
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ----------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.store.audit is not None:
            self.store.audit.record(actor_name(actor), action, target,
                                    details=details)

    def _guard(self, actor, rbac_action, audit_action):
        """Enforce a write permission before any state change
        (mirrors the first unit's convention). A denied attempt
        is recorded on the audit log with a ``:denied`` suffix
        before the error propagates; a missing actor is denied
        outright."""
        if actor is None:
            raise PermissionDenied(
                "permission denied: no user supplied for %r" % (rbac_action,))
        if hasattr(actor, "role"):
            try:
                require(actor, rbac_action)
            except PermissionDenied:
                self._audit(actor, audit_action + ":denied", None,
                            details={"rbac_action": rbac_action})
                raise

    @staticmethod
    def _maybe_require(actor, rbac_action):
        if actor is not None and hasattr(actor, "role"):
            require(actor, rbac_action)

    def _get(self, table, record_id, what):
        record = table.get(record_id)
        if record is None:
            raise NotFoundError("%s not found: %r" % (what, record_id))
        return record

    def _org(self, actor, org_id):
        return self.store.get_organization(actor, org_id)

    def _case_events(self, case_id):
        return [e for e in self._relocation_events.values()
                if e["case_id"] == case_id]

    def _case_claims(self, case_id):
        return [c for c in self._entitlement_claims.values()
                if c["case_id"] == case_id]

    # -- entitlement derivation seam ------------------------------------

    @staticmethod
    def _derive_entitlement(claimed_cents, cap_cents):
        """Derive one rule's entitlement determination at read:
        the allowed figure is the claimed figure bounded by the
        recorded rule cap; the excess is what was claimed above
        the cap. Both inputs are recorded figures only — the
        claim's verbatim amount and the rule's recorded cap.
        This seam is the fresh negative control's target: a
        cap-blind derivation would allow claims the recorded
        policy does not."""
        allowed_cents = min(claimed_cents, cap_cents)
        return allowed_cents, claimed_cents - allowed_cents

    def _entitlement_rows(self, case_id):
        """Per-rule entitlement rows for a case, derived at
        read: claims grouped by their recorded rule, each row's
        claimed total summed from the case's claim records and
        its determination derived through the seam above."""
        rows = []
        for rule in self._policy_rules.values():
            claims = [c for c in self._case_claims(case_id)
                      if c["rule_id"] == rule["id"]]
            if not claims:
                continue
            claimed = sum(c["claimed_cents"] for c in claims)
            allowed, excess = self._derive_entitlement(
                claimed, rule["cap_cents"])
            rows.append({
                "rule_id": rule["id"],
                "rule_ref": rule["rule_ref"],
                "corpus_label": rule["corpus_label"],
                "entitlement_kind": rule["entitlement_kind"],
                "cap_cents": rule["cap_cents"],
                "claim_count": len(claims),
                "claimed_cents": claimed,
                "allowed_cents": allowed,
                "excess_cents": excess,
                "within_cap": excess == 0,
            })
        return rows

    # -- relocation management & processing (idx 681, built) ------------

    def create_relocation_case(self, actor, org_id, traveler_id,
                               origin_label, destination_label,
                               move_date, estimated_cost_cents):
        """Record a relocation case for a core traveler. Action:
        enter. The case is a record of a permanent move, distinct
        from a trip: it binds a core organization and traveler
        only, never a trip authorization. Origin and destination
        are labels; the traveler stays an opaque reference. No
        one is moved or relocated here and no processing occurs
        — processing is recorded through event records."""
        self._guard(actor, "enter", "exta_relocation_case_create")
        self._org(actor, org_id)
        traveler = self.store.get_traveler(actor, traveler_id)
        if traveler["org_id"] != org_id:
            raise ValidationError(
                "traveler %r does not belong to organization %r"
                % (traveler_id, org_id))
        _text(origin_label, "origin_label")
        _text(destination_label, "destination_label")
        _date(move_date, "move_date")
        _money(estimated_cost_cents, "estimated_cost_cents",
               allow_zero=False)
        with self._lock:
            case = {
                "id": self._next_id("rlc-"),
                "org_id": org_id,
                "traveler_id": traveler_id,
                "origin_label": origin_label,
                "destination_label": destination_label,
                "move_date": move_date,
                "estimated_cost_cents": estimated_cost_cents,
                "status": "draft",
                "moved_here": False,
                "relocated_here": False,
                "processed_here": False,
                "state": "recorded_case_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._relocation_cases[case["id"]] = case
        self._audit(actor, "exta_relocation_case_create", case["id"],
                    {"org_id": org_id, "traveler_id": traveler_id})
        return copy.deepcopy(case)

    def submit_relocation_case(self, actor, case_id):
        """Move a draft relocation case to submitted. Action:
        enter. Event-driven lifecycle, as in the core."""
        self._guard(actor, "enter", "exta_relocation_case_submit")
        with self._lock:
            case = self._get(self._relocation_cases, case_id,
                             "relocation case")
            if case["status"] != "draft":
                raise ValidationError(
                    "only a draft relocation case can be submitted; "
                    "status is %r" % case["status"])
            case["status"] = "submitted"
            result = copy.deepcopy(case)
        self._audit(actor, "exta_relocation_case_submit", case_id)
        return result

    def decide_relocation_case(self, actor, case_id, approve, note=""):
        """Record a decision on a submitted relocation case.
        Action: decide. The decider is never the case's creator
        (separation of duties, the core's control carried to
        this surface). The decision is its own record; the
        case's stored status follows it."""
        self._guard(actor, "decide", "exta_relocation_case_decide")
        if not isinstance(approve, bool):
            raise ValidationError("approve must be a boolean")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            case = self._get(self._relocation_cases, case_id,
                             "relocation case")
            if actor_name(actor) == case["created_by"]:
                raise PermissionDenied(
                    "the decider may not be the relocation case's "
                    "creator")
            if case["status"] != "submitted":
                raise ValidationError(
                    "only a submitted relocation case can be decided; "
                    "status is %r" % case["status"])
            decision = {
                "id": self._next_id("rlcd-"),
                "case_id": case_id,
                "approve": approve,
                "note": note,
                "decided_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._relocation_decisions[decision["id"]] = decision
            case["status"] = "approved" if approve else "declined"
        self._audit(actor, "exta_relocation_case_decide", decision["id"],
                    {"case_id": case_id, "approve": approve})
        return copy.deepcopy(decision)

    def record_relocation_event(self, actor, case_id, event_kind,
                                outcome_label, reported_amount_cents=None):
        """Record one relocation processing milestone exactly as
        reported. Action: record. The case must be approved —
        processing presupposes an approved move, as expense
        reports presuppose an approved authorization in the core.
        The outcome and amount are reported data stored verbatim;
        nothing is processed here."""
        self._guard(actor, "record", "exta_relocation_event_create")
        if event_kind not in RELOCATION_EVENT_KINDS:
            raise ValidationError(
                "event_kind must be one of %r" % (RELOCATION_EVENT_KINDS,))
        if outcome_label not in RELOCATION_EVENT_OUTCOMES:
            raise ValidationError(
                "unknown relocation outcome label: %r" % (outcome_label,))
        if reported_amount_cents is not None:
            _money(reported_amount_cents, "reported_amount_cents")
        with self._lock:
            case = self._get(self._relocation_cases, case_id,
                             "relocation case")
            if case["status"] != "approved":
                raise ValidationError(
                    "relocation events require an approved case; "
                    "status is %r" % case["status"])
            event = {
                "id": self._next_id("rle-"),
                "case_id": case_id,
                "org_id": case["org_id"],
                "event_kind": event_kind,
                "outcome_label": outcome_label,
                "reported_amount_cents": reported_amount_cents,
                "processed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._relocation_events[event["id"]] = event
        self._audit(actor, "exta_relocation_event_create", event["id"],
                    {"case_id": case_id})
        return copy.deepcopy(event)

    def get_relocation_case(self, actor, case_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._relocation_cases, case_id,
                                       "relocation case"))

    def list_relocation_cases(self, actor, org_id):
        self._maybe_require(actor, "read")
        self._org(actor, org_id)
        return [
            copy.deepcopy(c) for c in self._relocation_cases.values()
            if c["org_id"] == org_id
        ]

    def list_relocation_events(self, actor, case_id):
        self._maybe_require(actor, "read")
        return [copy.deepcopy(e) for e in self._case_events(case_id)]

    def list_relocation_decisions(self, actor, case_id):
        self._maybe_require(actor, "read")
        return [
            copy.deepcopy(d) for d in self._relocation_decisions.values()
            if d["case_id"] == case_id
        ]

    def relocation_case_view(self, actor, case_id):
        """A relocation case, its processing events and
        decisions, and the figures derived at read: event count,
        latest reported outcome, the reported event total (a sum
        of amounts reported by others, stated as such), and the
        entitlement totals derived from the case's recorded
        claims against the recorded rule caps."""
        self._maybe_require(actor, "read")
        case = self._get(self._relocation_cases, case_id,
                         "relocation case")
        view = copy.deepcopy(case)
        events = self.list_relocation_events(actor, case_id)
        view["events"] = events
        view["decisions"] = self.list_relocation_decisions(actor, case_id)
        view["event_count"] = len(events)
        view["current_outcome"] = _latest_outcome(events)
        view["reported_event_total_cents"] = sum(
            e["reported_amount_cents"] for e in events
            if e["reported_amount_cents"] is not None)
        rows = self._entitlement_rows(case_id)
        view["entitlement_claimed_cents"] = sum(
            r["claimed_cents"] for r in rows)
        view["entitlement_allowed_cents"] = sum(
            r["allowed_cents"] for r in rows)
        view["entitlement_excess_cents"] = sum(
            r["excess_cents"] for r in rows)
        return view

    # -- relocation policy & entitlement rules (idx 682, built) ---------

    def register_policy_rule(self, actor, org_id, corpus_label, rule_ref,
                             entitlement_kind, cap_cents, rule_label):
        """Register a relocation policy rule as data. Action:
        enter. The rule records the parameters an entitlement
        evaluation needs — the corpus it was recorded under (a
        label from the corpora the addition fork names in its
        own words), an entitlement kind, and a cap in integer
        cents. The corpus text itself is never held, and the
        rule is never executed against anything: rules here are
        definitions, and evaluation is a derivation over
        recorded figures at read."""
        self._guard(actor, "enter", "exta_policy_rule_create")
        self._org(actor, org_id)
        if corpus_label not in POLICY_CORPORA:
            raise ValidationError(
                "corpus_label must be one of %r" % (POLICY_CORPORA,))
        _text(rule_ref, "rule_ref")
        if entitlement_kind not in ENTITLEMENT_KINDS:
            raise ValidationError(
                "entitlement_kind must be one of %r"
                % (ENTITLEMENT_KINDS,))
        _money(cap_cents, "cap_cents")
        _text(rule_label, "rule_label")
        with self._lock:
            for existing in self._policy_rules.values():
                if existing["org_id"] == org_id \
                        and existing["rule_ref"] == rule_ref:
                    raise ValidationError(
                        "rule_ref already exists in this organization: "
                        "%r" % (rule_ref,))
            rule = {
                "id": self._next_id("rlr-"),
                "org_id": org_id,
                "corpus_label": corpus_label,
                "rule_ref": rule_ref,
                "entitlement_kind": entitlement_kind,
                "cap_cents": cap_cents,
                "rule_label": rule_label,
                "definition_only": True,
                "executed_here": False,
                "corpus_text_held": False,
                "per_diem_computed_here": False,
                "state": "recorded_definition_only",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._policy_rules[rule["id"]] = rule
        self._audit(actor, "exta_policy_rule_create", rule["id"],
                    {"org_id": org_id, "rule_ref": rule_ref})
        return copy.deepcopy(rule)

    def record_entitlement_claim(self, actor, case_id, rule_id,
                                 claimed_cents, claim_label):
        """Record an entitlement claim against an approved
        relocation case under a recorded policy rule. Action:
        record. The claimed figure is stored verbatim as the
        claimant reported it; the claim record carries NO
        determination — allowed and excess figures exist only
        as derivations at read (see
        :meth:`entitlement_evaluation`). The rule must belong
        to the case's organization."""
        self._guard(actor, "record", "exta_entitlement_claim_create")
        _money(claimed_cents, "claimed_cents", allow_zero=False)
        _text(claim_label, "claim_label")
        with self._lock:
            case = self._get(self._relocation_cases, case_id,
                             "relocation case")
            rule = self._get(self._policy_rules, rule_id, "policy rule")
            if rule["org_id"] != case["org_id"]:
                raise ValidationError(
                    "policy rule %r does not belong to the case's "
                    "organization" % (rule_id,))
            if case["status"] != "approved":
                raise ValidationError(
                    "entitlement claims require an approved relocation "
                    "case; status is %r" % case["status"])
            claim = {
                "id": self._next_id("rln-"),
                "case_id": case_id,
                "rule_id": rule_id,
                "org_id": case["org_id"],
                "claimed_cents": claimed_cents,
                "claim_label": claim_label,
                "computed_here": False,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._entitlement_claims[claim["id"]] = claim
        self._audit(actor, "exta_entitlement_claim_create", claim["id"],
                    {"case_id": case_id, "rule_id": rule_id})
        return copy.deepcopy(claim)

    def get_policy_rule(self, actor, rule_id):
        self._maybe_require(actor, "read")
        return copy.deepcopy(self._get(self._policy_rules, rule_id,
                                       "policy rule"))

    def list_policy_rules(self, actor, org_id):
        self._maybe_require(actor, "read")
        self._org(actor, org_id)
        return [
            copy.deepcopy(r) for r in self._policy_rules.values()
            if r["org_id"] == org_id
        ]

    def list_entitlement_claims(self, actor, case_id):
        self._maybe_require(actor, "read")
        return [copy.deepcopy(c) for c in self._case_claims(case_id)]

    def policy_rule_view(self, actor, rule_id):
        """A policy rule plus the claims recorded against it,
        with the claim count and claimed total derived at read.
        No determination is derived here — determinations are
        per case (see :meth:`entitlement_evaluation`)."""
        self._maybe_require(actor, "read")
        rule = self._get(self._policy_rules, rule_id, "policy rule")
        view = copy.deepcopy(rule)
        claims = [c for c in self._entitlement_claims.values()
                  if c["rule_id"] == rule_id]
        view["claims"] = [copy.deepcopy(c) for c in claims]
        view["claim_count"] = len(claims)
        view["claimed_total_cents"] = sum(
            c["claimed_cents"] for c in claims)
        return view

    def entitlement_evaluation(self, actor, case_id):
        """The entitlement determination for a relocation case,
        derived at read and stored nowhere: per recorded rule,
        the case's claimed total against the rule's recorded
        cap, with allowed and excess derived through
        :meth:`_derive_entitlement`, plus case totals. The
        basis is stated on the view: recorded claims against
        recorded rule caps, this substrate's figures only. No
        per-diem is computed — no rate or day count enters this
        surface in any shape."""
        self._maybe_require(actor, "read")
        case = self._get(self._relocation_cases, case_id,
                         "relocation case")
        rows = self._entitlement_rows(case_id)
        return {
            "case_id": case_id,
            "org_id": case["org_id"],
            "rows": rows,
            "claimed_cents": sum(r["claimed_cents"] for r in rows),
            "allowed_cents": sum(r["allowed_cents"] for r in rows),
            "excess_cents": sum(r["excess_cents"] for r in rows),
            "evaluation_basis": "recorded_claims_against_recorded_rule_caps",
            "computed_here": True,
            "per_diem_computed_here": False,
            "corpus_text_held": False,
            "executed_here": False,
        }
