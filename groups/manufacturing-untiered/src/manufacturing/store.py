"""Manufacturing store: organization registry; engineering intent
records; structured, manufacturable decision records.

Clean-room implementation of the union spec's implementation
contract. This category is new — no tiered group exists anywhere
in the repo — and the core is claim-driven: every record type
traces to a claim in the set's spec sheet (see UNION-SPEC.md),
except the organization registry, search/summary, and
API/access/audit substrate every DeadRamp build carries, whose
reason is stated in the spec.

Role permission is enforced on every operation when the actor is
a User-like object: the action named for the operation must be in
the actor's role permission set (see
:mod:`manufacturing.access`). A plain string actor carries
identity (for provenance) but no role, so role enforcement for
those happens in the service layer (the sibling builds'
convention).

Every operation validates fully before it mutates anything: a
failed operation consumes no id and changes nothing. Ids are
sequential per object type with fixed prefixes (``org-``,
``int-``, ``dec-``).

Reference discipline: records name people only by **opaque
references** supplied by the caller. A person reference is
validated to be incapable of holding an email address (no ``@``,
no whitespace); this store holds no real names and no email
addresses. Intent and decision *statements* are caller-supplied
engineering text stored verbatim — the record of what the
organization stated — exactly as the sibling builds store
finding detail and settings text verbatim.

Derivation discipline: an intent record's status is derived at
read time and never stored. The single seam
:func:`_derive_intent_status` computes ``open`` / ``transformed``
from whether any decision record cites the intent in its basis.
The stored intent record carries no status key. The derivation is
the records form of the fork's own sentence: intent is
*transformed* when a decision rests on it.

Decision-basis guard (the signature invariant): a decision record
may not be recorded without a basis of at least one engineering
intent record that exists and belongs to the same organization.
The fork's whole function, in its own words, is that it
"transforms engineering intent into structured, manufacturable
decisions" — a decision resting on no intent transforms nothing
and is not a record of that function. The gate is the single seam
:func:`_check_decision_basis`, read by the decision operation
only; a refusal records nothing and consumes no id. The guard is
this build's records-form rule for the claimed transformation; it
is not a claim that the fork implements this exact check.

Scoring discipline: nothing in this store computes a score, a
rating, a ranking, or a rate. The description's "high-precision"
is the fork's adjective about manufacturing, not a computed
quantity, and no scoring vocabulary appears anywhere in it. A
decision record states the decision as the organization recorded
it; the build judges neither the decision nor its
manufacturability — "manufacturable" is the fork's word for the
kind of decision its software produces, carried in the family
name, not a verdict this build renders.

Money discipline: no record in this store carries money. The
description states no price, fee, cost, or budget figure, so no
money shape was built — the same deliberate omission the Event
Management, Marketing & Sales, and Talent Development builds
recorded.

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

INTENT_STATES = ("open", "transformed")


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


def _person_ref(value, field="person_ref"):
    """An opaque person reference. It must be a non-empty string
    with no whitespace and no ``@`` — a value of that shape cannot
    be an email address, so no record keyed by it can hold one."""
    _text(value, field)
    if "@" in value or any(ch.isspace() for ch in value):
        raise ValidationError(
            "%s must be an opaque reference (no whitespace, no '@')" % field)
    return value


def _derive_intent_status(intent_id, cited_intent_ids):
    """Intent status derivation seam: ``transformed`` once at
    least one decision record cites the intent in its basis,
    ``open`` otherwise. Pure function over the recorded links;
    nothing about the status is stored anywhere."""
    if intent_id in cited_intent_ids:
        return "transformed"
    return "open"


def _check_decision_basis(intents_by_id, org_id, basis_intent_ids):
    """Decision-basis guard seam: the single check the decision
    operation reads before recording a decision.

    The basis must be a non-empty list of distinct intent record
    ids, every one of which exists and belongs to the deciding
    organization. A decision resting on no engineering intent
    transforms nothing — it is not a record of the transformation
    function this set claims — and a decision resting on another
    organization's intent is not that organization's
    transformation either.
    """
    if not basis_intent_ids:
        raise ValidationError(
            "a decision record must rest on at least one engineering "
            "intent record: the transformation this set records is of "
            "engineering intent into decisions, and a decision with no "
            "basis intent transforms nothing")
    if len(set(basis_intent_ids)) != len(basis_intent_ids):
        raise ValidationError("basis_intent_ids contains duplicates")
    for intent_id in basis_intent_ids:
        intent = intents_by_id.get(intent_id)
        if intent is None:
            raise ValidationError(
                "basis intent %r does not exist" % (intent_id,))
        if intent["org_id"] != org_id:
            raise ValidationError(
                "basis intent %r does not belong to organization %r"
                % (intent_id, org_id))


class ManufacturingStore:
    """In-memory Manufacturing records store with an optional
    audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._intents = {}
        self._decisions = {}
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

    def _intent(self, intent_id):
        intent = self._intents.get(intent_id)
        if intent is None:
            raise NotFoundError("no such intent record: %r" % (intent_id,))
        return intent

    def _decision(self, decision_id):
        decision = self._decisions.get(decision_id)
        if decision is None:
            raise NotFoundError("no such decision record: %r" % (decision_id,))
        return decision

    def _cited_intent_ids(self):
        cited = set()
        for decision in self._decisions.values():
            cited.update(decision["basis_intent_ids"])
        return cited

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

    # -- engineering intent records ------------------------------------------------

    def record_intent(self, actor, org_id, label, statement, author_ref):
        """Record one statement of engineering intent.

        ``statement`` is the intent as the organization states it,
        stored verbatim. ``author_ref`` is the author's opaque
        reference. The stored record carries no status key:
        status is derived at read (see
        :func:`_derive_intent_status`).
        """
        self._check_role(actor, "intents")
        _text(label, "label")
        _text(statement, "statement")
        _person_ref(author_ref, "author_ref")
        with self._lock:
            self._organization(org_id)
            record = {
                "id": self._mint("int-"),
                "org_id": org_id,
                "label": label,
                "statement": statement,
                "author_ref": author_ref,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._intents[record["id"]] = record
        self._record(actor, "record_intent", record["id"],
                     {"org_id": org_id})
        return self._intent_view(record)

    def _intent_view(self, intent):
        view = dict(intent)
        view["status"] = _derive_intent_status(
            intent["id"], self._cited_intent_ids())
        return view

    def get_intent(self, actor, intent_id):
        self._check_role(actor, "read")
        return self._intent_view(self._intent(intent_id))

    def list_intents(self, actor, org_id=None, status=None):
        self._check_role(actor, "read")
        if status is not None and status not in INTENT_STATES:
            raise ValidationError(
                "status must be one of %r" % (INTENT_STATES,))
        result = []
        for intent in self._intents.values():
            if org_id is not None and intent["org_id"] != org_id:
                continue
            view = self._intent_view(intent)
            if status is not None and view["status"] != status:
                continue
            result.append(view)
        return result

    # -- manufacturable decision records --------------------------------------------

    def record_decision(self, actor, org_id, label, statement,
                        basis_intent_ids, decided_by_ref, decided_at=None):
        """Record one structured, manufacturable decision and the
        engineering intent it transforms.

        ``statement`` is the decision as the organization states
        it, stored verbatim; the build renders no judgment on it
        and none on its manufacturability. ``basis_intent_ids``
        names the intent records the decision rests on — the
        recorded transformation — and must satisfy the
        decision-basis guard (see :func:`_check_decision_basis`):
        non-empty, distinct, existing, and of the same
        organization. ``decided_by_ref`` is the decider's opaque
        reference.
        """
        self._check_role(actor, "decisions")
        _text(label, "label")
        _text(statement, "statement")
        _person_ref(decided_by_ref, "decided_by_ref")
        decided = None
        if decided_at is not None:
            decided = _parse_moment(decided_at, "decided_at")
        basis = list(basis_intent_ids) if basis_intent_ids is not None else []
        for basis_id in basis:
            _text(basis_id, "basis intent id")
        with self._lock:
            self._organization(org_id)
            _check_decision_basis(self._intents, org_id, basis)
            record = {
                "id": self._mint("dec-"),
                "org_id": org_id,
                "label": label,
                "statement": statement,
                "basis_intent_ids": basis,
                "decided_by_ref": decided_by_ref,
                "decided_at": (decided.isoformat() if decided is not None
                               else _utc_now().isoformat()),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._decisions[record["id"]] = record
        self._record(actor, "record_decision", record["id"],
                     {"org_id": org_id,
                      "basis_intent_ids": list(basis)})
        return dict(record)

    def get_decision(self, actor, decision_id):
        self._check_role(actor, "read")
        return dict(self._decision(decision_id))

    def list_decisions(self, actor, org_id=None, intent_id=None):
        self._check_role(actor, "read")
        return [dict(d) for d in self._decisions.values()
                if (org_id is None or d["org_id"] == org_id)
                and (intent_id is None
                     or intent_id in d["basis_intent_ids"])]

    # -- search, summary, audit ---------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over the
        registered metadata: organizations, intent records, and
        decision records."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()

        def hit(*fields):
            return any(needle in (f or "").lower() for f in fields)

        return {
            "organizations": [dict(o) for o in self._organizations.values()
                              if hit(o["ref"], o["label"])],
            "intents": [self._intent_view(i) for i in self._intents.values()
                        if hit(i["label"], i["statement"])],
            "decisions": [dict(d) for d in self._decisions.values()
                          if hit(d["label"], d["statement"])],
        }

    def summary(self, actor):
        """Counts computed on read from the records. Counts only:
        no scores, no rates, no rankings."""
        self._check_role(actor, "read")
        cited = self._cited_intent_ids()
        intents_by_status = {s: 0 for s in INTENT_STATES}
        for intent in self._intents.values():
            intents_by_status[
                _derive_intent_status(intent["id"], cited)] += 1
        return {
            "organizations": len(self._organizations),
            "intents": len(self._intents),
            "intents_by_status": intents_by_status,
            "decisions": len(self._decisions),
        }

    def audit_read(self, actor):
        """Return the audit entries (requires ``audit_read``)."""
        self._check_role(actor, "audit_read")
        entries = self.audit.entries() if self.audit is not None else []
        return {"count": len(entries), "entries": entries}
