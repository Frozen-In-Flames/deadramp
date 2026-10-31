"""Travel store: organizations, travelers, trip authorizations,
decisions, expense reports and line items, vouchers, notification
records, and an integration definition registry.

Clean-room implementation of the union spec's implementation
contract.

Two boundaries are enforced on every organization-scoped operation:

1. Membership -- the actor must be a member of the organization, or
   hold the platform ``admin`` role, else :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be in
   the actor's role permission set (see :mod:`travel.access`) when
   the actor is a User-like object. A plain string actor carries
   identity (for provenance) but no role, so role enforcement for
   those happens in the service layer.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``org-``, ``trv-``, ``auth-``,
``dec-``, ``exp-``, ``itm-``, ``vou-``, ``ntf-``, ``int-``).

Derivation discipline: any status that depends on a date or on other
records is derived at read time and never stored. A trip's phase
(``upcoming`` / ``in_progress`` / ``completed``) is computed from its
depart and return dates against the read clock, and an expense
report's total, reimbursed sum, and remaining balance are computed
from its line items and vouchers. The stored records carry no such
keys. A record's lifecycle status (``draft`` / ``submitted`` /
``approved`` / ``declined``), by contrast, is event-driven (it
changes only through recorded lifecycle actions), so it is stored.

Money discipline: amounts are integer cents. Any amount that is not
a Python ``int`` (booleans and floats included, even integral
floats) raises :class:`ValidationError`.

Caps: two caps stand. The signature invariant is the voucher cap --
the cumulative vouchers recorded against an expense report never
exceed its total -- enforced at :meth:`_check_voucher_cap` before
anything is stored. At expense-report submission, the cumulative
totals of submitted and approved reports against an authorization
never exceed its authorized amount (:meth:`_check_authorization_cap`).

Separation of duties: the decider of an authorization or an expense
report is never its creator (the requester of record). Enforced on
every decision.

Privacy discipline: traveler records carry an opaque caller-supplied
reference and a label only; the record shape is pinned, so no field
can hold a document number or other real personal data. Trips carry
a destination label and dates, never a personal itinerary.

Scoring discipline: summaries are counts and money sums. Nothing in
this store computes a score, a rating, or a risk value, and no
record shape carries a field for one.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.
"""

import re
import threading
from datetime import date, datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

LIFECYCLE_STATUSES = ("draft", "submitted", "approved", "declined")
EXPENSE_CATEGORIES = ("lodging", "meals", "transport", "incidentals", "other")
NOTIFICATION_KINDS = ("decision", "reminder", "general")
INTEGRATION_KINDS = ("api", "file", "service", "other")


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_date(value, field):
    """Parse an ISO date (or datetime) into a :class:`datetime.date`."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                return datetime.strptime(text, "%Y-%m-%d").date()
            moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return moment.date()
        except ValueError:
            raise ValidationError("%s is not an ISO date: %r" % (field, value))
    raise ValidationError("%s must be an ISO date string" % field)


def _money(value, field, allow_zero=True):
    """Validate an integer-cents amount; floats and bools are rejected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer number of cents" % field)
    if allow_zero and value < 0:
        raise ValidationError("%s must not be negative" % field)
    if not allow_zero and value <= 0:
        raise ValidationError("%s must be positive" % field)
    return value


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % field)
    return value


class TravelStore:
    """In-memory travel records store with an optional audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._organizations = {}
        self._org_members = {}
        self._travelers = {}
        self._authorizations = {}
        self._decisions = {}
        self._expense_reports = {}
        self._expense_items = {}
        self._vouchers = {}
        self._notifications = {}
        self._integrations = {}
        self._counters = {}

    # -- internals ------------------------------------------------------

    def _mint(self, prefix):
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return "%s%d" % (prefix, self._counters[prefix])

    def _record(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor, action, target, details)

    def _check_role(self, actor, action):
        if hasattr(actor, "role"):
            require(actor, action)

    def _organization(self, org_id):
        org = self._organizations.get(org_id)
        if org is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return org

    def _check_org_access(self, actor, org_id):
        org = self._organization(org_id)
        if getattr(actor, "role", None) == "admin":
            return org
        name = actor_name(actor)
        if name not in self._org_members.get(org_id, set()):
            raise PermissionDenied(
                "permission denied: %r is not a member of organization %s"
                % (name, org_id)
            )
        return org

    def _traveler(self, traveler_id):
        traveler = self._travelers.get(traveler_id)
        if traveler is None:
            raise NotFoundError("no such traveler: %r" % (traveler_id,))
        return traveler

    def _authorization(self, authorization_id):
        auth = self._authorizations.get(authorization_id)
        if auth is None:
            raise NotFoundError("no such authorization: %r" % (authorization_id,))
        return auth

    def _expense_report(self, report_id):
        report = self._expense_reports.get(report_id)
        if report is None:
            raise NotFoundError("no such expense report: %r" % (report_id,))
        return report

    def _check_decider_not_requester(self, actor, record, what):
        if actor_name(actor) == record["created_by"]:
            raise PermissionDenied(
                "permission denied: the decider of %s may not be its requester"
                % what
            )

    # -- organizations ----------------------------------------------------

    def create_organization(self, actor, ref, label):
        """Create an organization (agency) record; creator is a member."""
        self._check_role(actor, "enter")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            org = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[org["id"]] = org
            self._org_members[org["id"]] = {actor_name(actor)}
        self._record(actor, "organization_create", org["id"], {"ref": ref})
        return dict(org)

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        org = self._check_org_access(actor, org_id)
        return dict(org)

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        name = actor_name(actor)
        result = []
        for org in self._organizations.values():
            if getattr(actor, "role", None) == "admin" or \
                    name in self._org_members.get(org["id"], set()):
                result.append(dict(org))
        return result

    def add_member(self, actor, org_id, username):
        """Add ``username`` to an organization's membership."""
        self._check_role(actor, "manage_members")
        org = self._organization(org_id)
        if getattr(actor, "role", None) != "admin":
            self._check_org_access(actor, org_id)
        _text(username, "username")
        with self._lock:
            self._org_members.setdefault(org_id, set()).add(username)
        self._record(actor, "member_add", org_id, {"username": username})
        return dict(org)

    def list_members(self, actor, org_id):
        self._check_role(actor, "read")
        self._check_org_access(actor, org_id)
        return sorted(self._org_members.get(org_id, set()))

    # -- travelers --------------------------------------------------------

    def create_traveler(self, actor, org_id, traveler_ref, label):
        """Register a traveler by opaque reference only."""
        self._check_role(actor, "enter")
        self._check_org_access(actor, org_id)
        _text(traveler_ref, "traveler_ref")
        _text(label, "label")
        with self._lock:
            traveler = {
                "id": self._mint("trv-"),
                "org_id": org_id,
                "traveler_ref": traveler_ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._travelers[traveler["id"]] = traveler
        self._record(actor, "traveler_create", traveler["id"],
                     {"org_id": org_id, "traveler_ref": traveler_ref})
        return dict(traveler)

    def get_traveler(self, actor, traveler_id):
        self._check_role(actor, "read")
        traveler = self._traveler(traveler_id)
        self._check_org_access(actor, traveler["org_id"])
        return dict(traveler)

    def list_travelers(self, actor, org_id):
        self._check_role(actor, "read")
        self._check_org_access(actor, org_id)
        return [dict(t) for t in self._travelers.values()
                if t["org_id"] == org_id]

    # -- authorizations ---------------------------------------------------

    def create_authorization(self, actor, org_id, traveler_id,
                             destination_label, purpose,
                             depart_date, return_date, authorized_cents):
        """Create a trip authorization in ``draft``.

        ``authorized_cents`` is the cap that later expense reports
        are checked against at submission.
        """
        self._check_role(actor, "enter")
        self._check_org_access(actor, org_id)
        traveler = self._traveler(traveler_id)
        if traveler["org_id"] != org_id:
            raise ValidationError("traveler %s is not in organization %s"
                                  % (traveler_id, org_id))
        _text(destination_label, "destination_label")
        _text(purpose, "purpose")
        depart = _parse_date(depart_date, "depart_date")
        back = _parse_date(return_date, "return_date")
        if back < depart:
            raise ValidationError("return_date must not precede depart_date")
        _money(authorized_cents, "authorized_cents", allow_zero=False)
        with self._lock:
            auth = {
                "id": self._mint("auth-"),
                "org_id": org_id,
                "traveler_id": traveler_id,
                "destination_label": destination_label,
                "purpose": purpose,
                "depart_date": depart.isoformat(),
                "return_date": back.isoformat(),
                "authorized_cents": authorized_cents,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._authorizations[auth["id"]] = auth
        self._record(actor, "authorization_create", auth["id"],
                     {"org_id": org_id, "traveler_id": traveler_id})
        return dict(auth)

    def _derive_phase(self, auth, as_of):
        moment = _parse_date(as_of, "as_of") if as_of is not None \
            else _utc_now().date()
        depart = _parse_date(auth["depart_date"], "depart_date")
        back = _parse_date(auth["return_date"], "return_date")
        if moment < depart:
            return "upcoming"
        if moment <= back:
            return "in_progress"
        return "completed"

    def _authorization_view(self, auth, as_of=None):
        view = dict(auth)
        view["phase"] = self._derive_phase(auth, as_of)
        claimed = 0
        reimbursed = 0
        for report in self._expense_reports.values():
            if report["authorization_id"] == auth["id"] \
                    and report["status"] == "approved":
                claimed += self._report_total(report["id"])
                reimbursed += self._report_reimbursed(report["id"])
        view["claimed_cents"] = claimed
        view["reimbursed_cents"] = reimbursed
        return view

    def get_authorization(self, actor, authorization_id, as_of=None):
        self._check_role(actor, "read")
        auth = self._authorization(authorization_id)
        self._check_org_access(actor, auth["org_id"])
        return self._authorization_view(auth, as_of=as_of)

    def list_authorizations(self, actor, org_id, as_of=None):
        self._check_role(actor, "read")
        self._check_org_access(actor, org_id)
        return [self._authorization_view(a, as_of=as_of)
                for a in self._authorizations.values()
                if a["org_id"] == org_id]

    def submit_authorization(self, actor, authorization_id):
        """Move a draft authorization to ``submitted``."""
        self._check_role(actor, "enter")
        auth = self._authorization(authorization_id)
        self._check_org_access(actor, auth["org_id"])
        with self._lock:
            if auth["status"] != "draft":
                raise ValidationError(
                    "only a draft authorization can be submitted; "
                    "status is %r" % auth["status"])
            auth["status"] = "submitted"
        self._record(actor, "authorization_submit", auth["id"], {})
        return self._authorization_view(auth)

    def decide_authorization(self, actor, authorization_id, approve, note=""):
        """Record a decision on a submitted authorization.

        The decider is never the authorization's creator. On success
        a decision record is stored and the lifecycle status moves.
        The whole operation validates before anything is stored.
        """
        self._check_role(actor, "decide")
        auth = self._authorization(authorization_id)
        self._check_org_access(actor, auth["org_id"])
        self._check_decider_not_requester(actor, auth, "an authorization")
        if not isinstance(approve, bool):
            raise ValidationError("approve must be a boolean")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            if auth["status"] != "submitted":
                raise ValidationError(
                    "only a submitted authorization can be decided; "
                    "status is %r" % auth["status"])
            decision = {
                "id": self._mint("dec-"),
                "org_id": auth["org_id"],
                "target_kind": "authorization",
                "target_id": auth["id"],
                "decider": actor_name(actor),
                "approve": approve,
                "note": note,
                "created_utc": _utc_now().isoformat(),
            }
            self._decisions[decision["id"]] = decision
            auth["status"] = "approved" if approve else "declined"
        self._record(actor, "authorization_decide", auth["id"],
                     {"decision_id": decision["id"], "approve": approve})
        return {"decision": dict(decision),
                "authorization": self._authorization_view(auth)}

    def list_decisions(self, actor, org_id, target_id=None):
        self._check_role(actor, "read")
        self._check_org_access(actor, org_id)
        return [dict(d) for d in self._decisions.values()
                if d["org_id"] == org_id
                and (target_id is None or d["target_id"] == target_id)]

    # -- expense reports ----------------------------------------------------

    def _report_total(self, report_id):
        return sum(item["amount_cents"]
                   for item in self._expense_items.values()
                   if item["report_id"] == report_id)

    def _report_reimbursed(self, report_id):
        return sum(v["amount_cents"]
                   for v in self._vouchers.values()
                   if v["report_id"] == report_id)

    def _report_view(self, report):
        view = dict(report)
        total = self._report_total(report["id"])
        reimbursed = self._report_reimbursed(report["id"])
        view["total_cents"] = total
        view["reimbursed_cents"] = reimbursed
        view["remaining_cents"] = total - reimbursed
        return view

    def create_expense_report(self, actor, authorization_id, title):
        """Create an expense report in ``draft`` against an approved
        authorization."""
        self._check_role(actor, "enter")
        auth = self._authorization(authorization_id)
        self._check_org_access(actor, auth["org_id"])
        _text(title, "title")
        if auth["status"] != "approved":
            raise ValidationError(
                "expense reports require an approved authorization; "
                "status is %r" % auth["status"])
        with self._lock:
            report = {
                "id": self._mint("exp-"),
                "org_id": auth["org_id"],
                "authorization_id": authorization_id,
                "traveler_id": auth["traveler_id"],
                "title": title,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._expense_reports[report["id"]] = report
        self._record(actor, "expense_report_create", report["id"],
                     {"authorization_id": authorization_id})
        return self._report_view(report)

    def add_expense_item(self, actor, report_id, category, amount_cents,
                         item_date, note=""):
        """Add a line item to a draft expense report."""
        self._check_role(actor, "enter")
        report = self._expense_report(report_id)
        self._check_org_access(actor, report["org_id"])
        if category not in EXPENSE_CATEGORIES:
            raise ValidationError("category must be one of %r"
                                  % (EXPENSE_CATEGORIES,))
        _money(amount_cents, "amount_cents", allow_zero=False)
        day = _parse_date(item_date, "item_date")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            if report["status"] != "draft":
                raise ValidationError(
                    "line items can be added only to a draft report; "
                    "status is %r" % report["status"])
            item = {
                "id": self._mint("itm-"),
                "report_id": report_id,
                "category": category,
                "amount_cents": amount_cents,
                "item_date": day.isoformat(),
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._expense_items[item["id"]] = item
        self._record(actor, "expense_item_add", item["id"],
                     {"report_id": report_id})
        return dict(item)

    def list_expense_items(self, actor, report_id):
        self._check_role(actor, "read")
        report = self._expense_report(report_id)
        self._check_org_access(actor, report["org_id"])
        return [dict(i) for i in self._expense_items.values()
                if i["report_id"] == report_id]

    def get_expense_report(self, actor, report_id):
        self._check_role(actor, "read")
        report = self._expense_report(report_id)
        self._check_org_access(actor, report["org_id"])
        return self._report_view(report)

    def list_expense_reports(self, actor, authorization_id):
        self._check_role(actor, "read")
        auth = self._authorization(authorization_id)
        self._check_org_access(actor, auth["org_id"])
        return [self._report_view(r)
                for r in self._expense_reports.values()
                if r["authorization_id"] == authorization_id]

    def _check_authorization_cap(self, auth, report):
        """Cumulative submitted+approved report totals against an
        authorization never exceed its authorized amount."""
        committed = 0
        for other in self._expense_reports.values():
            if other["authorization_id"] == auth["id"] \
                    and other["id"] != report["id"] \
                    and other["status"] in ("submitted", "approved"):
                committed += self._report_total(other["id"])
        if committed + self._report_total(report["id"]) \
                > auth["authorized_cents"]:
            raise ValidationError(
                "expense reports totalling %d cents would exceed the "
                "authorization's authorized amount: %d already committed "
                "of %d" % (self._report_total(report["id"]), committed,
                           auth["authorized_cents"]))

    def submit_expense_report(self, actor, report_id):
        """Move a draft expense report to ``submitted``, checking the
        authorization cap."""
        self._check_role(actor, "enter")
        report = self._expense_report(report_id)
        self._check_org_access(actor, report["org_id"])
        auth = self._authorization(report["authorization_id"])
        with self._lock:
            if report["status"] != "draft":
                raise ValidationError(
                    "only a draft expense report can be submitted; "
                    "status is %r" % report["status"])
            if not any(i["report_id"] == report_id
                       for i in self._expense_items.values()):
                raise ValidationError(
                    "an expense report with no line items cannot be "
                    "submitted")
            self._check_authorization_cap(auth, report)
            report["status"] = "submitted"
        self._record(actor, "expense_report_submit", report["id"], {})
        return self._report_view(report)

    def decide_expense_report(self, actor, report_id, approve, note=""):
        """Record a decision on a submitted expense report.

        The decider is never the report's creator.
        """
        self._check_role(actor, "decide")
        report = self._expense_report(report_id)
        self._check_org_access(actor, report["org_id"])
        self._check_decider_not_requester(actor, report, "an expense report")
        if not isinstance(approve, bool):
            raise ValidationError("approve must be a boolean")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            if report["status"] != "submitted":
                raise ValidationError(
                    "only a submitted expense report can be decided; "
                    "status is %r" % report["status"])
            decision = {
                "id": self._mint("dec-"),
                "org_id": report["org_id"],
                "target_kind": "expense_report",
                "target_id": report["id"],
                "decider": actor_name(actor),
                "approve": approve,
                "note": note,
                "created_utc": _utc_now().isoformat(),
            }
            self._decisions[decision["id"]] = decision
            report["status"] = "approved" if approve else "declined"
        self._record(actor, "expense_report_decide", report["id"],
                     {"decision_id": decision["id"], "approve": approve})
        return {"decision": dict(decision),
                "expense_report": self._report_view(report)}

    # -- vouchers -----------------------------------------------------------

    def _check_voucher_cap(self, report, amount_cents):
        """Signature invariant: cumulative vouchers against an expense
        report never exceed the report's total."""
        total = self._report_total(report["id"])
        already = self._report_reimbursed(report["id"])
        if already + amount_cents > total:
            raise ValidationError(
                "voucher of %d cents would exceed the expense report "
                "total: %d already recorded of %d"
                % (amount_cents, already, total))

    def record_voucher(self, actor, report_id, amount_cents, note=""):
        """Record a voucher (reimbursement record) against an approved
        expense report. A record only: no money moves."""
        self._check_role(actor, "record")
        report = self._expense_report(report_id)
        self._check_org_access(actor, report["org_id"])
        _money(amount_cents, "amount_cents", allow_zero=False)
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            if report["status"] != "approved":
                raise ValidationError(
                    "vouchers require an approved expense report; "
                    "status is %r" % report["status"])
            self._check_voucher_cap(report, amount_cents)
            voucher = {
                "id": self._mint("vou-"),
                "org_id": report["org_id"],
                "report_id": report_id,
                "amount_cents": amount_cents,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._vouchers[voucher["id"]] = voucher
        self._record(actor, "voucher_create", voucher["id"],
                     {"report_id": report_id, "amount_cents": amount_cents})
        return dict(voucher)

    def list_vouchers(self, actor, report_id):
        self._check_role(actor, "read")
        report = self._expense_report(report_id)
        self._check_org_access(actor, report["org_id"])
        return [dict(v) for v in self._vouchers.values()
                if v["report_id"] == report_id]

    # -- notifications --------------------------------------------------------

    def create_notification(self, actor, org_id, kind, recipient_ref,
                            target_kind="", target_id="", note=""):
        """Record a notification. Records only: nothing is delivered."""
        self._check_role(actor, "record")
        self._check_org_access(actor, org_id)
        if kind not in NOTIFICATION_KINDS:
            raise ValidationError("kind must be one of %r"
                                  % (NOTIFICATION_KINDS,))
        _text(recipient_ref, "recipient_ref")
        if not isinstance(target_kind, str) or not isinstance(target_id, str):
            raise ValidationError("target_kind and target_id must be strings")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            notification = {
                "id": self._mint("ntf-"),
                "org_id": org_id,
                "kind": kind,
                "recipient_ref": recipient_ref,
                "target_kind": target_kind,
                "target_id": target_id,
                "note": note,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._notifications[notification["id"]] = notification
        self._record(actor, "notification_create", notification["id"],
                     {"org_id": org_id, "kind": kind})
        return dict(notification)

    def list_notifications(self, actor, org_id):
        self._check_role(actor, "read")
        self._check_org_access(actor, org_id)
        return [dict(n) for n in self._notifications.values()
                if n["org_id"] == org_id]

    # -- integration registry -------------------------------------------------

    def register_integration(self, actor, org_id, name, kind, target_label):
        """Register an integration definition as data.

        The registry never executes a definition; there is no execute
        path in this build.
        """
        self._check_role(actor, "record")
        self._check_org_access(actor, org_id)
        _text(name, "name")
        if kind not in INTEGRATION_KINDS:
            raise ValidationError("kind must be one of %r"
                                  % (INTEGRATION_KINDS,))
        _text(target_label, "target_label")
        with self._lock:
            integration = {
                "id": self._mint("int-"),
                "org_id": org_id,
                "name": name,
                "kind": kind,
                "target_label": target_label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._integrations[integration["id"]] = integration
        self._record(actor, "integration_register", integration["id"],
                     {"org_id": org_id, "name": name})
        return dict(integration)

    def list_integrations(self, actor, org_id):
        self._check_role(actor, "read")
        self._check_org_access(actor, org_id)
        return [dict(i) for i in self._integrations.values()
                if i["org_id"] == org_id]

    # -- search & summary -------------------------------------------------------

    def search(self, actor, org_id, query):
        """Substring search over travelers, authorizations, reports."""
        self._check_role(actor, "read")
        self._check_org_access(actor, org_id)
        _text(query, "query")
        needle = query.lower()
        travelers = [dict(t) for t in self._travelers.values()
                     if t["org_id"] == org_id
                     and (needle in t["traveler_ref"].lower()
                          or needle in t["label"].lower())]
        authorizations = [self._authorization_view(a)
                          for a in self._authorizations.values()
                          if a["org_id"] == org_id
                          and (needle in a["destination_label"].lower()
                               or needle in a["purpose"].lower())]
        reports = [self._report_view(r)
                   for r in self._expense_reports.values()
                   if r["org_id"] == org_id
                   and needle in r["title"].lower()]
        return {"travelers": travelers,
                "authorizations": authorizations,
                "expense_reports": reports}

    def summary(self, actor, org_id):
        """Per-organization counts and money sums, computed on read.

        Counts and sums only: no score, rating, or risk value is
        computed anywhere in this build.
        """
        self._check_role(actor, "read")
        self._check_org_access(actor, org_id)
        auths = [a for a in self._authorizations.values()
                 if a["org_id"] == org_id]
        reports = [r for r in self._expense_reports.values()
                   if r["org_id"] == org_id]
        by_status = {status: 0 for status in LIFECYCLE_STATUSES}
        for auth in auths:
            by_status[auth["status"]] += 1
        report_by_status = {status: 0 for status in LIFECYCLE_STATUSES}
        for report in reports:
            report_by_status[report["status"]] += 1
        claimed = sum(self._report_total(r["id"]) for r in reports
                      if r["status"] == "approved")
        reimbursed = sum(v["amount_cents"]
                         for v in self._vouchers.values()
                         if v["org_id"] == org_id)
        return {
            "org_id": org_id,
            "travelers": sum(1 for t in self._travelers.values()
                             if t["org_id"] == org_id),
            "authorizations": by_status,
            "expense_reports": report_by_status,
            "authorized_cents": sum(a["authorized_cents"] for a in auths),
            "claimed_cents": claimed,
            "reimbursed_cents": reimbursed,
            "notifications": sum(1 for n in self._notifications.values()
                                 if n["org_id"] == org_id),
            "integrations": sum(1 for i in self._integrations.values()
                                if i["org_id"] == org_id),
        }
