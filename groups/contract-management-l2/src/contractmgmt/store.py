"""The Contract Management records substrate.

Clean-room implementation of the Contract Management L2 union
spec's core: organization registry & membership, participant
registry, contract records (the lifecycle system of record),
contract modification records, compliance requirement records,
protest records, data-call records, risk records, communication
records (metadata only), opportunity records, submission records,
award records, fee & payment records, workflow definition
registry, integration registry, registry reporting, and registry
search — over an append-only audit log.

Privacy discipline (hard rule): every entity is keyed by an opaque
caller-supplied reference and carries only the fields in the
contract. Counterparties, participants, and requesters are opaque
references. There is no field anywhere that can hold contract
text, a bid's contents, message content, or any real identifier of
a person. Communications are metadata only: this store has no
parameter that can accept message content. Validation always
precedes mutation: a failed operation changes nothing, consumes
no id, and records nothing.

Two boundaries are enforced on every organization-scoped
operation:

1. Membership -- the actor must be a member of the organization,
   or hold the platform ``admin`` role, else
   :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be
   in the actor's role permission set (see
   :mod:`contractmgmt.access`) when the actor is a
   :class:`~contractmgmt.access.User`. A plain string actor
   carries identity (for provenance) but no role, so role
   enforcement for those happens in the service layer.

The participant registry is not organization-scoped: writes
require ``registry_write``; reads are open to any actor.

Derivation discipline: a contract's ``obligated_cents`` and
``period_elapsed``, a protest's and a data call's ``overdue``, an
opportunity's ``past_close``, and a submission's ``awarded`` are
derived at read time and never stored. The stored records carry
none of those keys. Lifecycles (contract ``active`` -> ``closed``,
requirement ``open`` -> ``satisfied`` / ``waived``, cases and
opportunities ``open`` -> ``closed``) are guarded transitions, not
date derivations, so those statuses are stored.

Modification bounds seam: a contract's obligated amount — base
award plus the sum of its recorded modifications — must always
satisfy ``0 <= obligated <= ceiling_cents``.
:meth:`ContractMgmtStore._check_modification_bounds` runs before a
contract is created (with its base award as the amount under test)
and before every modification is recorded, and raises
:class:`ValidationError` on a violation. This is the group's
negative control.

Money discipline: all money values are Python ``int`` cents.
Booleans, floats, and strings are rejected at the boundary.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import User, require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

OPPORTUNITY_KINDS = ("erfx", "reverse_auction", "financial_assistance")
AUDIENCES = ("public", "directed")
PAYMENT_KINDS = ("subscription", "award_fee")
DIRECTIONS = ("inbound", "outbound")
CONTRACT_STATUSES = ("active", "closed")
REQUIREMENT_STATUSES = ("open", "satisfied", "waived")
CASE_STATUSES = ("open", "closed")
OPPORTUNITY_STATUSES = ("open", "closed")


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
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % field)
    return value


def _cents_nonneg(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError("%s must be an integer >= 0 (cents)" % field)
    return value


def _cents_positive(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("%s must be a positive integer (cents)" % field)
    return value


def _cents_any(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer (cents)" % field)
    return value


class ContractMgmtStore:
    """In-memory Contract Management records store with an optional audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._participants = {}
        self._contracts = {}
        self._modifications = {}
        self._requirements = {}
        self._protests = {}
        self._datacalls = {}
        self._risks = {}
        self._communications = {}
        self._opportunities = {}
        self._submissions = {}
        self._awards = {}
        self._payments = {}
        self._workflows = {}
        self._integrations = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    @staticmethod
    def _name(actor):
        return actor_name(actor)

    @staticmethod
    def _require_role(actor, action):
        # A User carries a role and is enforced here; a plain string
        # carries identity only (the service layer enforces its role).
        if isinstance(actor, User):
            require(actor, action)

    @staticmethod
    def _is_admin(actor):
        return isinstance(actor, User) and actor.role == "admin"

    def _organization(self, org_id):
        org = self._organizations.get(org_id)
        if org is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return org

    def _require_org_access(self, org, actor):
        if self._is_admin(actor):
            return
        if self._name(actor) not in org["members"]:
            raise PermissionDenied(
                "actor %r is not a member of organization %s"
                % (self._name(actor), org["id"])
            )

    def _scoped_org(self, org_id, actor, action):
        org = self._organization(org_id)
        self._require_role(actor, action)
        self._require_org_access(org, actor)
        return org

    @staticmethod
    def _org_view(org):
        view = dict(org)
        view["members"] = list(org["members"])
        return view

    def _contract_in(self, org_id, contract_id):
        contract = self._contracts.get(contract_id)
        if contract is None or contract["org_id"] != org_id:
            raise NotFoundError(
                "no such contract in organization %s: %r" % (org_id, contract_id)
            )
        return contract

    def _opportunity_in(self, org_id, opportunity_id):
        opportunity = self._opportunities.get(opportunity_id)
        if opportunity is None or opportunity["org_id"] != org_id:
            raise NotFoundError(
                "no such opportunity in organization %s: %r"
                % (org_id, opportunity_id)
            )
        return opportunity

    def _participant_by_ref(self, participant_ref):
        for participant in self._participants.values():
            if participant["participant_ref"] == participant_ref:
                return participant
        return None

    # -- organizations -----------------------------------------------------------

    def create_organization(self, org_ref, label, actor):
        """Create an organization. The creator is the first member."""
        self._require_role(actor, "org_write")
        _text(org_ref, "org_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["org_ref"] == org_ref:
                    raise ValidationError(
                        "org_ref already exists: %r" % (org_ref,)
                    )
            org = {
                "id": self._mint("org-"),
                "org_ref": org_ref,
                "label": label,
                "members": [self._name(actor)],
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[org["id"]] = org
        self._record(actor, "organization_create", org["id"], {"org_ref": org_ref})
        return self._org_view(org)

    def list_organizations(self, actor):
        """Organizations the actor is a member of, or all for an admin."""
        self._require_role(actor, "org_read")
        result = []
        for org in self._organizations.values():
            if self._is_admin(actor) or self._name(actor) in org["members"]:
                result.append(self._org_view(org))
        return result

    def get_organization(self, org_id, actor):
        org = self._scoped_org(org_id, actor, "org_read")
        return self._org_view(org)

    def add_member(self, org_id, username, actor):
        """Add a member to an organization. Only the organization's
        creator or a platform admin may add; the gate is
        creator-or-admin, layered on the membership boundary."""
        org = self._organization(org_id)
        self._require_org_access(org, actor)
        if not (self._is_admin(actor) or org["created_by"] == self._name(actor)):
            raise PermissionDenied(
                "only the organization creator or a platform admin may add members"
            )
        _text(username, "username")
        with self._lock:
            if username in org["members"]:
                raise ValidationError(
                    "%r is already a member of organization %s" % (username, org_id)
                )
            org["members"].append(username)
        self._record(actor, "member_add", org_id, {"username": username})
        return self._org_view(org)

    # -- participants (platform registry) -----------------------------------

    def register_participant(self, participant_ref, label, actor):
        """Register a vendor / applicant participant. Registration
        records are not identity proofing (IA-2 stays with the
        embedding organization)."""
        self._require_role(actor, "registry_write")
        _text(participant_ref, "participant_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._participants.values():
                if existing["participant_ref"] == participant_ref:
                    raise ValidationError(
                        "participant_ref already exists: %r" % (participant_ref,)
                    )
            participant = {
                "id": self._mint("par-"),
                "participant_ref": participant_ref,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._participants[participant["id"]] = participant
        self._record(actor, "participant_register", participant["id"],
                     {"participant_ref": participant_ref})
        return dict(participant)

    def list_participants(self, actor):
        # Platform registry: reads are open to any actor.
        return [dict(p) for p in self._participants.values()]

    def get_participant(self, participant_id, actor):
        # Platform registry: reads are open to any actor.
        participant = self._participants.get(participant_id)
        if participant is None:
            raise NotFoundError("no such participant: %r" % (participant_id,))
        return dict(participant)

    # -- contracts ---------------------------------------------------------------

    def _check_modification_bounds(self, contract, existing_amounts,
                                   additional_cents):
        """Modification bounds seam: the obligated amount — the sum
        of ``existing_amounts`` (amounts already obligated, which
        for a modification include the contract's base award) plus
        ``additional_cents`` — must satisfy
        ``0 <= obligated <= contract["ceiling_cents"]``. Raises
        ValidationError on a violation. (This is the seam the
        negative control mutates.)"""
        obligated = sum(existing_amounts) + additional_cents
        if obligated < 0:
            raise ValidationError(
                "obligated amount would fall below zero: %d cents" % obligated
            )
        if obligated > contract["ceiling_cents"]:
            raise ValidationError(
                "obligated amount %d exceeds contract ceiling %d cents"
                % (obligated, contract["ceiling_cents"])
            )

    def _contract_view(self, contract, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        obligated = contract["award_cents"] + sum(
            m["amount_cents"] for m in self._modifications.values()
            if m["contract_id"] == contract["id"]
        )
        period_elapsed = False
        if contract["period_end"] is not None:
            period_elapsed = moment > _parse_moment(
                contract["period_end"], "period_end")
        view = dict(contract)
        view["obligated_cents"] = obligated
        view["period_elapsed"] = period_elapsed
        return view

    def create_contract(self, org_id, contract_ref, title, counterparty_ref,
                        ceiling_cents, award_cents, actor,
                        period_start=None, period_end=None):
        self._scoped_org(org_id, actor, "contract_write")
        _text(contract_ref, "contract_ref")
        _text(title, "title")
        _text(counterparty_ref, "counterparty_ref")
        _cents_nonneg(ceiling_cents, "ceiling_cents")
        _cents_nonneg(award_cents, "award_cents")
        start_moment = None
        end_moment = None
        if period_start is not None:
            start_moment = _parse_moment(period_start, "period_start")
        if period_end is not None:
            end_moment = _parse_moment(period_end, "period_end")
        if (start_moment is not None and end_moment is not None
                and end_moment < start_moment):
            raise ValidationError("period_end must not precede period_start")
        would_be = {"ceiling_cents": ceiling_cents}
        # The bounds seam runs before the record exists: the base
        # award is the amount under test, with nothing yet obligated.
        self._check_modification_bounds(would_be, [], award_cents)
        with self._lock:
            for existing in self._contracts.values():
                if (existing["org_id"] == org_id
                        and existing["contract_ref"] == contract_ref):
                    raise ValidationError(
                        "contract_ref %r already exists in organization %s"
                        % (contract_ref, org_id)
                    )
            contract = {
                "id": self._mint("con-"),
                "org_id": org_id,
                "contract_ref": contract_ref,
                "title": title,
                "counterparty_ref": counterparty_ref,
                "ceiling_cents": ceiling_cents,
                "award_cents": award_cents,
                "period_start": period_start,
                "period_end": period_end,
                "status": "active",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._contracts[contract["id"]] = contract
        self._record(actor, "contract_create", contract["id"], {"org_id": org_id})
        return dict(contract)

    def get_contract(self, org_id, contract_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        contract = self._contract_in(org_id, contract_id)
        return self._contract_view(contract, now=now)

    def list_contracts(self, org_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        return [
            self._contract_view(c, now=now) for c in self._contracts.values()
            if c["org_id"] == org_id
        ]

    def close_contract(self, org_id, contract_id, actor):
        self._scoped_org(org_id, actor, "contract_write")
        contract = self._contract_in(org_id, contract_id)
        with self._lock:
            if contract["status"] != "active":
                raise ValidationError(
                    "contract %s is %r; only an active contract can be closed"
                    % (contract_id, contract["status"])
                )
            contract["status"] = "closed"
        self._record(actor, "contract_close", contract_id, {"org_id": org_id})
        return dict(contract)

    # -- modifications ---------------------------------------------------------------

    def record_modification(self, org_id, contract_id, mod_ref, amount_cents,
                            actor, label=None):
        self._scoped_org(org_id, actor, "contract_write")
        contract = self._contract_in(org_id, contract_id)
        _text(mod_ref, "mod_ref")
        _cents_any(amount_cents, "amount_cents")
        _optional_text(label, "label")
        with self._lock:
            if contract["status"] != "active":
                raise ValidationError(
                    "contract %s is %r; modifications are recorded against "
                    "active contracts only" % (contract_id, contract["status"])
                )
            existing_mods = [
                m for m in self._modifications.values()
                if m["contract_id"] == contract_id
            ]
            for existing in existing_mods:
                if existing["mod_ref"] == mod_ref:
                    raise ValidationError(
                        "mod_ref %r already exists in contract %s"
                        % (mod_ref, contract_id)
                    )
            self._check_modification_bounds(
                contract,
                [contract["award_cents"]]
                + [m["amount_cents"] for m in existing_mods],
                amount_cents,
            )
            modification = {
                "id": self._mint("mod-"),
                "org_id": org_id,
                "contract_id": contract_id,
                "mod_ref": mod_ref,
                "amount_cents": amount_cents,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._modifications[modification["id"]] = modification
        self._record(actor, "modification_record", modification["id"],
                     {"org_id": org_id, "contract_id": contract_id})
        return dict(modification)

    def list_modifications(self, org_id, contract_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        self._contract_in(org_id, contract_id)
        return [
            dict(m) for m in self._modifications.values()
            if m["org_id"] == org_id and m["contract_id"] == contract_id
        ]

    # -- compliance requirements ---------------------------------------------------

    def create_requirement(self, org_id, requirement_ref, label, actor):
        self._scoped_org(org_id, actor, "compliance_write")
        _text(requirement_ref, "requirement_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._requirements.values():
                if (existing["org_id"] == org_id
                        and existing["requirement_ref"] == requirement_ref):
                    raise ValidationError(
                        "requirement_ref %r already exists in organization %s"
                        % (requirement_ref, org_id)
                    )
            requirement = {
                "id": self._mint("req-"),
                "org_id": org_id,
                "requirement_ref": requirement_ref,
                "label": label,
                "status": "open",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._requirements[requirement["id"]] = requirement
        self._record(actor, "requirement_create", requirement["id"],
                     {"org_id": org_id})
        return dict(requirement)

    def _requirement_in(self, org_id, requirement_id):
        requirement = self._requirements.get(requirement_id)
        if requirement is None or requirement["org_id"] != org_id:
            raise NotFoundError(
                "no such requirement in organization %s: %r"
                % (org_id, requirement_id)
            )
        return requirement

    def _transition_requirement(self, org_id, requirement_id, actor,
                                target_status, action):
        self._scoped_org(org_id, actor, "compliance_write")
        requirement = self._requirement_in(org_id, requirement_id)
        with self._lock:
            if requirement["status"] != "open":
                raise ValidationError(
                    "requirement %s is %r; only an open requirement can "
                    "become %s" % (requirement_id, requirement["status"],
                                   target_status)
                )
            requirement["status"] = target_status
        self._record(actor, action, requirement_id, {"org_id": org_id})
        return dict(requirement)

    def satisfy_requirement(self, org_id, requirement_id, actor):
        return self._transition_requirement(
            org_id, requirement_id, actor, "satisfied", "requirement_satisfy")

    def waive_requirement(self, org_id, requirement_id, actor):
        return self._transition_requirement(
            org_id, requirement_id, actor, "waived", "requirement_waive")

    def get_requirement(self, org_id, requirement_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._requirement_in(org_id, requirement_id))

    def list_requirements(self, org_id, actor, status=None):
        self._scoped_org(org_id, actor, "org_read")
        if status is not None and status not in REQUIREMENT_STATUSES:
            raise ValidationError(
                "status must be one of %s" % (", ".join(REQUIREMENT_STATUSES),)
            )
        return [
            dict(r) for r in self._requirements.values()
            if r["org_id"] == org_id and (status is None or r["status"] == status)
        ]

    # -- protests -----------------------------------------------------------------

    @staticmethod
    def _case_view(record, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        view = dict(record)
        view["overdue"] = bool(
            record["status"] == "open"
            and moment > _parse_moment(record["due_at"], "due_at")
        )
        return view

    def create_protest(self, org_id, protest_ref, label, due_at, actor,
                       contract_id=None, opportunity_id=None):
        self._scoped_org(org_id, actor, "case_write")
        _text(protest_ref, "protest_ref")
        _text(label, "label")
        if due_at is None:
            raise ValidationError("due_at is required")
        _parse_moment(due_at, "due_at")
        if (contract_id is None) == (opportunity_id is None):
            raise ValidationError(
                "exactly one of contract_id / opportunity_id must be given"
            )
        if contract_id is not None:
            self._contract_in(org_id, contract_id)
        if opportunity_id is not None:
            self._opportunity_in(org_id, opportunity_id)
        with self._lock:
            for existing in self._protests.values():
                if (existing["org_id"] == org_id
                        and existing["protest_ref"] == protest_ref):
                    raise ValidationError(
                        "protest_ref %r already exists in organization %s"
                        % (protest_ref, org_id)
                    )
            protest = {
                "id": self._mint("pro-"),
                "org_id": org_id,
                "protest_ref": protest_ref,
                "contract_id": contract_id,
                "opportunity_id": opportunity_id,
                "label": label,
                "due_at": due_at,
                "status": "open",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._protests[protest["id"]] = protest
        self._record(actor, "protest_create", protest["id"], {"org_id": org_id})
        return dict(protest)

    def _protest_in(self, org_id, protest_id):
        protest = self._protests.get(protest_id)
        if protest is None or protest["org_id"] != org_id:
            raise NotFoundError(
                "no such protest in organization %s: %r" % (org_id, protest_id)
            )
        return protest

    def get_protest(self, org_id, protest_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        return self._case_view(self._protest_in(org_id, protest_id), now=now)

    def list_protests(self, org_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        return [
            self._case_view(p, now=now) for p in self._protests.values()
            if p["org_id"] == org_id
        ]

    def close_protest(self, org_id, protest_id, actor):
        self._scoped_org(org_id, actor, "case_write")
        protest = self._protest_in(org_id, protest_id)
        with self._lock:
            if protest["status"] != "open":
                raise ValidationError(
                    "protest %s is %r; only an open protest can be closed"
                    % (protest_id, protest["status"])
                )
            protest["status"] = "closed"
        self._record(actor, "protest_close", protest_id, {"org_id": org_id})
        return dict(protest)

    # -- data calls -----------------------------------------------------------------

    def create_datacall(self, org_id, datacall_ref, requester_ref, label,
                        due_at, actor):
        self._scoped_org(org_id, actor, "case_write")
        _text(datacall_ref, "datacall_ref")
        _text(requester_ref, "requester_ref")
        _text(label, "label")
        if due_at is None:
            raise ValidationError("due_at is required")
        _parse_moment(due_at, "due_at")
        with self._lock:
            for existing in self._datacalls.values():
                if (existing["org_id"] == org_id
                        and existing["datacall_ref"] == datacall_ref):
                    raise ValidationError(
                        "datacall_ref %r already exists in organization %s"
                        % (datacall_ref, org_id)
                    )
            datacall = {
                "id": self._mint("dcl-"),
                "org_id": org_id,
                "datacall_ref": datacall_ref,
                "requester_ref": requester_ref,
                "label": label,
                "due_at": due_at,
                "status": "open",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._datacalls[datacall["id"]] = datacall
        self._record(actor, "datacall_create", datacall["id"], {"org_id": org_id})
        return dict(datacall)

    def _datacall_in(self, org_id, datacall_id):
        datacall = self._datacalls.get(datacall_id)
        if datacall is None or datacall["org_id"] != org_id:
            raise NotFoundError(
                "no such data call in organization %s: %r" % (org_id, datacall_id)
            )
        return datacall

    def get_datacall(self, org_id, datacall_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        return self._case_view(self._datacall_in(org_id, datacall_id), now=now)

    def list_datacalls(self, org_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        return [
            self._case_view(d, now=now) for d in self._datacalls.values()
            if d["org_id"] == org_id
        ]

    def close_datacall(self, org_id, datacall_id, actor):
        self._scoped_org(org_id, actor, "case_write")
        datacall = self._datacall_in(org_id, datacall_id)
        with self._lock:
            if datacall["status"] != "open":
                raise ValidationError(
                    "data call %s is %r; only an open data call can be closed"
                    % (datacall_id, datacall["status"])
                )
            datacall["status"] = "closed"
        self._record(actor, "datacall_close", datacall_id, {"org_id": org_id})
        return dict(datacall)

    # -- risks -----------------------------------------------------------------

    def create_risk(self, org_id, risk_ref, label, actor, contract_id=None):
        self._scoped_org(org_id, actor, "case_write")
        _text(risk_ref, "risk_ref")
        _text(label, "label")
        if contract_id is not None:
            self._contract_in(org_id, contract_id)
        with self._lock:
            for existing in self._risks.values():
                if (existing["org_id"] == org_id
                        and existing["risk_ref"] == risk_ref):
                    raise ValidationError(
                        "risk_ref %r already exists in organization %s"
                        % (risk_ref, org_id)
                    )
            risk = {
                "id": self._mint("rsk-"),
                "org_id": org_id,
                "risk_ref": risk_ref,
                "contract_id": contract_id,
                "label": label,
                "status": "open",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._risks[risk["id"]] = risk
        self._record(actor, "risk_create", risk["id"], {"org_id": org_id})
        return dict(risk)

    def _risk_in(self, org_id, risk_id):
        risk = self._risks.get(risk_id)
        if risk is None or risk["org_id"] != org_id:
            raise NotFoundError(
                "no such risk in organization %s: %r" % (org_id, risk_id)
            )
        return risk

    def get_risk(self, org_id, risk_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return dict(self._risk_in(org_id, risk_id))

    def list_risks(self, org_id, actor, contract_id=None):
        self._scoped_org(org_id, actor, "org_read")
        if contract_id is not None:
            self._contract_in(org_id, contract_id)
        return [
            dict(r) for r in self._risks.values()
            if r["org_id"] == org_id
            and (contract_id is None or r["contract_id"] == contract_id)
        ]

    def close_risk(self, org_id, risk_id, actor):
        self._scoped_org(org_id, actor, "case_write")
        risk = self._risk_in(org_id, risk_id)
        with self._lock:
            if risk["status"] != "open":
                raise ValidationError(
                    "risk %s is %r; only an open risk can be closed"
                    % (risk_id, risk["status"])
                )
            risk["status"] = "closed"
        self._record(actor, "risk_close", risk_id, {"org_id": org_id})
        return dict(risk)

    # -- communications (metadata only) -------------------------------------------

    def record_communication(self, org_id, comm_ref, counterparty_ref,
                             direction, label, actor):
        """Record a communication's metadata. There is deliberately
        no parameter for message content."""
        self._scoped_org(org_id, actor, "comm_write")
        _text(comm_ref, "comm_ref")
        _text(counterparty_ref, "counterparty_ref")
        if direction not in DIRECTIONS:
            raise ValidationError(
                "direction must be one of %s" % (", ".join(DIRECTIONS),)
            )
        _text(label, "label")
        with self._lock:
            for existing in self._communications.values():
                if (existing["org_id"] == org_id
                        and existing["comm_ref"] == comm_ref):
                    raise ValidationError(
                        "comm_ref %r already exists in organization %s"
                        % (comm_ref, org_id)
                    )
            communication = {
                "id": self._mint("com-"),
                "org_id": org_id,
                "comm_ref": comm_ref,
                "counterparty_ref": counterparty_ref,
                "direction": direction,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._communications[communication["id"]] = communication
        self._record(actor, "communication_record", communication["id"],
                     {"org_id": org_id})
        return dict(communication)

    def list_communications(self, org_id, actor, direction=None):
        self._scoped_org(org_id, actor, "org_read")
        if direction is not None and direction not in DIRECTIONS:
            raise ValidationError(
                "direction must be one of %s" % (", ".join(DIRECTIONS),)
            )
        return [
            dict(c) for c in self._communications.values()
            if c["org_id"] == org_id
            and (direction is None or c["direction"] == direction)
        ]

    # -- opportunities -----------------------------------------------------------------

    def _opportunity_view(self, opportunity, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        past_close = False
        if opportunity["closes_at"] is not None:
            past_close = moment > _parse_moment(
                opportunity["closes_at"], "closes_at")
        view = dict(opportunity)
        view["directed_to"] = list(opportunity["directed_to"])
        view["past_close"] = past_close
        return view

    def create_opportunity(self, org_id, opportunity_ref, title, kind, actor,
                           audience="public", directed_to=None,
                           closes_at=None):
        self._scoped_org(org_id, actor, "portal_write")
        _text(opportunity_ref, "opportunity_ref")
        _text(title, "title")
        if kind not in OPPORTUNITY_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(OPPORTUNITY_KINDS),)
            )
        if audience not in AUDIENCES:
            raise ValidationError(
                "audience must be one of %s" % (", ".join(AUDIENCES),)
            )
        if closes_at is not None:
            _parse_moment(closes_at, "closes_at")
        stored_directed = []
        if audience == "directed":
            if not isinstance(directed_to, list) or not directed_to:
                raise ValidationError(
                    "a directed opportunity requires a non-empty directed_to "
                    "list of participant references"
                )
            for ref in directed_to:
                _text(ref, "directed_to entry")
                if self._participant_by_ref(ref) is None:
                    raise ValidationError(
                        "directed_to participant is not registered: %r" % (ref,)
                    )
            stored_directed = list(directed_to)
        elif directed_to:
            raise ValidationError(
                "a public opportunity takes no directed_to list"
            )
        with self._lock:
            for existing in self._opportunities.values():
                if (existing["org_id"] == org_id
                        and existing["opportunity_ref"] == opportunity_ref):
                    raise ValidationError(
                        "opportunity_ref %r already exists in organization %s"
                        % (opportunity_ref, org_id)
                    )
            opportunity = {
                "id": self._mint("opp-"),
                "org_id": org_id,
                "opportunity_ref": opportunity_ref,
                "title": title,
                "kind": kind,
                "audience": audience,
                "directed_to": stored_directed,
                "closes_at": closes_at,
                "status": "open",
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._opportunities[opportunity["id"]] = opportunity
        self._record(actor, "opportunity_create", opportunity["id"],
                     {"org_id": org_id})
        return dict(opportunity)

    def get_opportunity(self, org_id, opportunity_id, actor, now=None):
        self._scoped_org(org_id, actor, "org_read")
        opportunity = self._opportunity_in(org_id, opportunity_id)
        return self._opportunity_view(opportunity, now=now)

    def list_opportunities(self, org_id, actor, kind=None, now=None):
        self._scoped_org(org_id, actor, "org_read")
        if kind is not None and kind not in OPPORTUNITY_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(OPPORTUNITY_KINDS),)
            )
        return [
            self._opportunity_view(o, now=now)
            for o in self._opportunities.values()
            if o["org_id"] == org_id and (kind is None or o["kind"] == kind)
        ]

    def close_opportunity(self, org_id, opportunity_id, actor):
        self._scoped_org(org_id, actor, "portal_write")
        opportunity = self._opportunity_in(org_id, opportunity_id)
        with self._lock:
            if opportunity["status"] != "open":
                raise ValidationError(
                    "opportunity %s is %r; only an open opportunity can be "
                    "closed" % (opportunity_id, opportunity["status"])
                )
            opportunity["status"] = "closed"
        self._record(actor, "opportunity_close", opportunity_id,
                     {"org_id": org_id})
        return dict(opportunity)

    # -- submissions -----------------------------------------------------------------

    def _submission_view(self, submission):
        view = dict(submission)
        view["awarded"] = any(
            a["submission_id"] == submission["id"] for a in self._awards.values()
        )
        return view

    def record_submission(self, org_id, opportunity_id, submission_ref,
                          participant_ref, actor):
        self._scoped_org(org_id, actor, "portal_write")
        opportunity = self._opportunity_in(org_id, opportunity_id)
        _text(submission_ref, "submission_ref")
        _text(participant_ref, "participant_ref")
        with self._lock:
            if opportunity["status"] != "open":
                raise ValidationError(
                    "opportunity %s is %r; submissions are recorded against "
                    "open opportunities only"
                    % (opportunity_id, opportunity["status"])
                )
            if opportunity["closes_at"] is not None and _utc_now() > _parse_moment(
                    opportunity["closes_at"], "closes_at"):
                raise ValidationError(
                    "opportunity %s is past its close time; submissions are "
                    "no longer accepted" % (opportunity_id,)
                )
            if self._participant_by_ref(participant_ref) is None:
                raise ValidationError(
                    "participant is not registered: %r" % (participant_ref,)
                )
            if (opportunity["audience"] == "directed"
                    and participant_ref not in opportunity["directed_to"]):
                raise PermissionDenied(
                    "participant %r is not a directed recipient of "
                    "opportunity %s" % (participant_ref, opportunity_id)
                )
            for existing in self._submissions.values():
                if (existing["opportunity_id"] == opportunity_id
                        and existing["submission_ref"] == submission_ref):
                    raise ValidationError(
                        "submission_ref %r already exists in opportunity %s"
                        % (submission_ref, opportunity_id)
                    )
            submission = {
                "id": self._mint("sub-"),
                "org_id": org_id,
                "opportunity_id": opportunity_id,
                "submission_ref": submission_ref,
                "participant_ref": participant_ref,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._submissions[submission["id"]] = submission
        self._record(actor, "submission_record", submission["id"],
                     {"org_id": org_id, "opportunity_id": opportunity_id})
        return dict(submission)

    def _submission_in(self, org_id, submission_id):
        submission = self._submissions.get(submission_id)
        if submission is None or submission["org_id"] != org_id:
            raise NotFoundError(
                "no such submission in organization %s: %r"
                % (org_id, submission_id)
            )
        return submission

    def get_submission(self, org_id, submission_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return self._submission_view(self._submission_in(org_id, submission_id))

    def list_submissions(self, org_id, opportunity_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        self._opportunity_in(org_id, opportunity_id)
        return [
            self._submission_view(s) for s in self._submissions.values()
            if s["org_id"] == org_id and s["opportunity_id"] == opportunity_id
        ]

    # -- awards -----------------------------------------------------------------

    def record_award(self, org_id, opportunity_id, submission_id, award_ref,
                     amount_cents, actor):
        self._scoped_org(org_id, actor, "portal_write")
        self._opportunity_in(org_id, opportunity_id)
        submission = self._submission_in(org_id, submission_id)
        if submission["opportunity_id"] != opportunity_id:
            raise NotFoundError(
                "no such submission in opportunity %s: %r"
                % (opportunity_id, submission_id)
            )
        _text(award_ref, "award_ref")
        _cents_nonneg(amount_cents, "amount_cents")
        with self._lock:
            for existing in self._awards.values():
                if existing["submission_id"] == submission_id:
                    raise ValidationError(
                        "submission %s is already awarded; a submission is "
                        "awarded at most once" % (submission_id,)
                    )
                if (existing["opportunity_id"] == opportunity_id
                        and existing["award_ref"] == award_ref):
                    raise ValidationError(
                        "award_ref %r already exists in opportunity %s"
                        % (award_ref, opportunity_id)
                    )
            award = {
                "id": self._mint("awd-"),
                "org_id": org_id,
                "opportunity_id": opportunity_id,
                "submission_id": submission_id,
                "award_ref": award_ref,
                "amount_cents": amount_cents,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._awards[award["id"]] = award
        self._record(actor, "award_record", award["id"],
                     {"org_id": org_id, "opportunity_id": opportunity_id})
        return dict(award)

    def list_awards(self, org_id, opportunity_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        self._opportunity_in(org_id, opportunity_id)
        return [
            dict(a) for a in self._awards.values()
            if a["org_id"] == org_id and a["opportunity_id"] == opportunity_id
        ]

    # -- fee & payment records ---------------------------------------------------

    def record_payment(self, org_id, payment_ref, kind, amount_cents, actor,
                       opportunity_id=None, award_id=None):
        self._scoped_org(org_id, actor, "payment_write")
        _text(payment_ref, "payment_ref")
        if kind not in PAYMENT_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(PAYMENT_KINDS),)
            )
        _cents_positive(amount_cents, "amount_cents")
        if opportunity_id is not None:
            self._opportunity_in(org_id, opportunity_id)
        if award_id is not None:
            award = self._awards.get(award_id)
            if award is None or award["org_id"] != org_id:
                raise NotFoundError(
                    "no such award in organization %s: %r" % (org_id, award_id)
                )
            if (opportunity_id is not None
                    and award["opportunity_id"] != opportunity_id):
                raise ValidationError(
                    "award %s does not belong to opportunity %s"
                    % (award_id, opportunity_id)
                )
        with self._lock:
            for existing in self._payments.values():
                if (existing["org_id"] == org_id
                        and existing["payment_ref"] == payment_ref):
                    raise ValidationError(
                        "payment_ref %r already exists in organization %s"
                        % (payment_ref, org_id)
                    )
            payment = {
                "id": self._mint("pay-"),
                "org_id": org_id,
                "payment_ref": payment_ref,
                "kind": kind,
                "amount_cents": amount_cents,
                "opportunity_id": opportunity_id,
                "award_id": award_id,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._payments[payment["id"]] = payment
        self._record(actor, "payment_record", payment["id"], {"org_id": org_id})
        return dict(payment)

    def list_payments(self, org_id, actor, kind=None):
        self._scoped_org(org_id, actor, "org_read")
        if kind is not None and kind not in PAYMENT_KINDS:
            raise ValidationError(
                "kind must be one of %s" % (", ".join(PAYMENT_KINDS),)
            )
        return [
            dict(p) for p in self._payments.values()
            if p["org_id"] == org_id and (kind is None or p["kind"] == kind)
        ]

    # -- workflow definitions (records only, never execute) ----------------------

    def register_workflow(self, org_id, workflow_ref, label, actor):
        self._scoped_org(org_id, actor, "registry_write")
        _text(workflow_ref, "workflow_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._workflows.values():
                if (existing["org_id"] == org_id
                        and existing["workflow_ref"] == workflow_ref):
                    raise ValidationError(
                        "workflow_ref %r already exists in organization %s"
                        % (workflow_ref, org_id)
                    )
            workflow = {
                "id": self._mint("wfl-"),
                "org_id": org_id,
                "workflow_ref": workflow_ref,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._workflows[workflow["id"]] = workflow
        self._record(actor, "workflow_register", workflow["id"],
                     {"org_id": org_id})
        return dict(workflow)

    def list_workflows(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [dict(w) for w in self._workflows.values() if w["org_id"] == org_id]

    # -- integrations (records of interfaces, never transports) ------------------

    def register_integration(self, org_id, integration_ref, system_ref, label,
                             actor):
        self._scoped_org(org_id, actor, "registry_write")
        _text(integration_ref, "integration_ref")
        _text(system_ref, "system_ref")
        _text(label, "label")
        with self._lock:
            for existing in self._integrations.values():
                if (existing["org_id"] == org_id
                        and existing["integration_ref"] == integration_ref):
                    raise ValidationError(
                        "integration_ref %r already exists in organization %s"
                        % (integration_ref, org_id)
                    )
            integration = {
                "id": self._mint("int-"),
                "org_id": org_id,
                "integration_ref": integration_ref,
                "system_ref": system_ref,
                "label": label,
                "created_by": self._name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._integrations[integration["id"]] = integration
        self._record(actor, "integration_register", integration["id"],
                     {"org_id": org_id})
        return dict(integration)

    def list_integrations(self, org_id, actor):
        self._scoped_org(org_id, actor, "org_read")
        return [
            dict(i) for i in self._integrations.values() if i["org_id"] == org_id
        ]

    # -- reporting & registry search ---------------------------------------------------

    def org_report(self, org_id, actor, now=None):
        """Counts and cent sums for one organization, computed on
        read. ``overdue_datacalls`` is the derived count (open data
        calls past their due date at the read clock); nothing is
        scored."""
        self._scoped_org(org_id, actor, "report_read")
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        contracts = [c for c in self._contracts.values() if c["org_id"] == org_id]
        contracts_by_status = {s: 0 for s in CONTRACT_STATUSES}
        for contract in contracts:
            contracts_by_status[contract["status"]] += 1
        requirements = [
            r for r in self._requirements.values() if r["org_id"] == org_id
        ]
        requirements_by_status = {s: 0 for s in REQUIREMENT_STATUSES}
        for requirement in requirements:
            requirements_by_status[requirement["status"]] += 1
        protests = [p for p in self._protests.values() if p["org_id"] == org_id]
        datacalls = [d for d in self._datacalls.values() if d["org_id"] == org_id]
        risks = [r for r in self._risks.values() if r["org_id"] == org_id]
        opportunities = [
            o for o in self._opportunities.values() if o["org_id"] == org_id
        ]
        opportunities_by_kind = {k: 0 for k in OPPORTUNITY_KINDS}
        opportunities_by_status = {s: 0 for s in OPPORTUNITY_STATUSES}
        for opportunity in opportunities:
            opportunities_by_kind[opportunity["kind"]] += 1
            opportunities_by_status[opportunity["status"]] += 1
        awards = [a for a in self._awards.values() if a["org_id"] == org_id]
        payments = [p for p in self._payments.values() if p["org_id"] == org_id]
        payments_by_kind = {k: 0 for k in PAYMENT_KINDS}
        for payment in payments:
            payments_by_kind[payment["kind"]] += payment["amount_cents"]
        return {
            "org_id": org_id,
            "contract_count": len(contracts),
            "contracts_by_status": contracts_by_status,
            "obligated_cents_total": sum(
                c["award_cents"] for c in contracts
            ) + sum(
                m["amount_cents"] for m in self._modifications.values()
                if m["org_id"] == org_id
            ),
            "ceiling_cents_total": sum(c["ceiling_cents"] for c in contracts),
            "modification_count": sum(
                1 for m in self._modifications.values() if m["org_id"] == org_id
            ),
            "requirement_count": len(requirements),
            "requirements_by_status": requirements_by_status,
            "protest_count": len(protests),
            "open_protests": sum(1 for p in protests if p["status"] == "open"),
            "datacall_count": len(datacalls),
            "open_datacalls": sum(1 for d in datacalls if d["status"] == "open"),
            "overdue_datacalls": sum(
                1 for d in datacalls
                if d["status"] == "open"
                and moment > _parse_moment(d["due_at"], "due_at")
            ),
            "risk_count": len(risks),
            "open_risks": sum(1 for r in risks if r["status"] == "open"),
            "communication_count": sum(
                1 for c in self._communications.values() if c["org_id"] == org_id
            ),
            "opportunity_count": len(opportunities),
            "opportunities_by_kind": opportunities_by_kind,
            "opportunities_by_status": opportunities_by_status,
            "submission_count": sum(
                1 for s in self._submissions.values() if s["org_id"] == org_id
            ),
            "award_count": len(awards),
            "award_cents_total": sum(a["amount_cents"] for a in awards),
            "payment_count": len(payments),
            "payment_cents_total": sum(p["amount_cents"] for p in payments),
            "payments_by_kind": payments_by_kind,
            "workflow_count": sum(
                1 for w in self._workflows.values() if w["org_id"] == org_id
            ),
            "integration_count": sum(
                1 for i in self._integrations.values() if i["org_id"] == org_id
            ),
        }

    def search_registry(self, actor, query):
        """Literal case-insensitive substring search over registry
        metadata (references, titles, labels, kinds), scoped to
        organizations the actor belongs to (or all for a platform
        admin), plus the platform participant registry."""
        self._require_role(actor, "org_read")
        if not isinstance(query, str) or not query.strip():
            raise ValidationError("query must be a non-empty string")
        needle = query.strip().lower()

        def hit(*fields):
            return any(
                f is not None and needle in str(f).lower() for f in fields
            )

        visible = {
            o["id"] for o in self._organizations.values()
            if self._is_admin(actor) or self._name(actor) in o["members"]
        }
        return {
            "organizations": [
                self._org_view(o) for o in self._organizations.values()
                if o["id"] in visible and hit(o["org_ref"], o["label"])
            ],
            "participants": [
                dict(p) for p in self._participants.values()
                if hit(p["participant_ref"], p["label"])
            ],
            "contracts": [
                self._contract_view(c) for c in self._contracts.values()
                if c["org_id"] in visible
                and hit(c["contract_ref"], c["title"], c["counterparty_ref"])
            ],
            "opportunities": [
                self._opportunity_view(o) for o in self._opportunities.values()
                if o["org_id"] in visible
                and hit(o["opportunity_ref"], o["title"], o["kind"])
            ],
            "workflows": [
                dict(w) for w in self._workflows.values()
                if w["org_id"] in visible and hit(w["workflow_ref"], w["label"])
            ],
            "integrations": [
                dict(i) for i in self._integrations.values()
                if i["org_id"] in visible
                and hit(i["integration_ref"], i["system_ref"], i["label"])
            ],
        }
