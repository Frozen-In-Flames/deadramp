"""Grants store: grant programs, applicant organizations,
applications, reviews, decisions, awards, post-award reports,
documents, form and workflow registries, and communications records.

Clean-room implementation of the union spec's implementation
contract.

Two boundaries are enforced on every program-scoped operation:

1. Membership -- the actor must be a member of the program, or hold
   the platform ``admin`` role, else :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be in
   the actor's role permission set (see :mod:`grants.access`) when
   the actor is a User-like object. A plain string actor carries
   identity (for provenance) but no role, so role enforcement for
   those happens in the service layer.

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``gp-``, ``org-``, ``app-``,
``rev-``, ``dec-``, ``awd-``, ``rep-``, ``doc-``, ``frm-``, ``wfl-``,
``msg-``, ``note-``, ``ntf-``).

Derivation discipline: any status that depends on a date is derived
at read time and never stored. A grant program's open status
(``upcoming`` / ``open`` / ``closed``) is computed from its window
against the read clock, and a post-award report's status
(``pending`` / ``overdue`` / ``submitted``) is computed from its due
date and submission timestamp. The stored records carry no status
key for either. An application's lifecycle status, by contrast, is
event-driven (it changes only through recorded lifecycle actions),
so it is stored, as in the sibling builds' record lifecycles.

Money discipline: amounts are integer cents. Any amount that is not
a Python ``int`` (booleans and floats included, even integral
floats) raises :class:`ValidationError`.

Scoring discipline: reviews and decisions record the reviewer's and
decider's own words and outcomes verbatim. Nothing in this store
computes a score, a rating, or an eligibility determination, and no
record shape carries a field for one.

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

APPLICATION_STATUSES = ("draft", "submitted", "under_review", "awarded", "declined", "withdrawn")
RECOMMENDATIONS = ("award", "decline", "abstain")
REPORT_KINDS = ("progress", "financial", "final")
DOCUMENT_KINDS = ("proposal", "budget", "report", "agreement", "other")
DOCUMENT_TARGETS = ("application", "award", "program")
FIELD_KINDS = ("text", "number", "money_cents", "date", "choice")
MESSAGE_DIRECTIONS = ("inbound", "outbound")

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


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


class GrantsStore:
    """In-memory grants records store with an optional audit log."""

    def __init__(self, audit=None):
        self.audit = audit
        self._lock = threading.Lock()
        self._programs = {}
        self._organizations = {}
        self._applications = {}
        self._reviews = {}
        self._decisions = {}
        self._awards = {}
        self._reports = {}
        self._documents = {}
        self._forms = {}
        self._workflows = {}
        self._messages = {}
        self._notes = {}
        self._notifications = {}
        self._counters = {}

    # -- internal helpers -------------------------------------------------

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

    def _program(self, program_id):
        program = self._programs.get(program_id)
        if program is None:
            raise NotFoundError("no such grant program: %r" % (program_id,))
        return program

    def _check_program_access(self, actor, program):
        name = actor_name(actor)
        role = getattr(actor, "role", None)
        if role == "admin" or name in program["members"]:
            return
        raise PermissionDenied(
            "permission denied: user %r is not a member of program %r"
            % (name, program["id"])
        )

    def _organization(self, org_id):
        org = self._organizations.get(org_id)
        if org is None:
            raise NotFoundError("no such organization: %r" % (org_id,))
        return org

    def _application(self, application_id):
        app = self._applications.get(application_id)
        if app is None:
            raise NotFoundError("no such application: %r" % (application_id,))
        return app

    def _award(self, award_id):
        award = self._awards.get(award_id)
        if award is None:
            raise NotFoundError("no such award: %r" % (award_id,))
        return award

    def _program_of_application(self, app):
        return self._programs[app["program_id"]]

    # -- grant programs ----------------------------------------------------

    def _program_view(self, program, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        opens = _parse_moment(program["opens_at"], "opens_at")
        closes = _parse_moment(program["closes_at"], "closes_at")
        if moment < opens:
            status = "upcoming"
        elif moment > closes:
            status = "closed"
        else:
            status = "open"
        awarded = sum(
            a["amount_cents"] for a in self._awards.values()
            if a["program_id"] == program["id"]
        )
        view = dict(program)
        view["members"] = list(program["members"])
        view["status"] = status
        view["awarded_cents"] = awarded
        view["remaining_cents"] = program["budget_cents"] - awarded
        return view

    def create_program(self, actor, name, title, sponsor_ref, opens_at,
                       closes_at, budget_cents):
        """Create a grant program. The creator becomes owner and member."""
        self._check_role(actor, "create_program")
        _text(name, "name")
        _text(title, "title")
        _text(sponsor_ref, "sponsor_ref")
        opens = _parse_moment(opens_at, "opens_at")
        closes = _parse_moment(closes_at, "closes_at")
        if closes < opens:
            raise ValidationError("closes_at must not precede opens_at")
        _money(budget_cents, "budget_cents")
        with self._lock:
            for existing in self._programs.values():
                if existing["name"] == name:
                    raise ValidationError("program name already exists: %r" % (name,))
            program = {
                "id": self._mint("gp-"),
                "name": name,
                "title": title,
                "sponsor_ref": sponsor_ref,
                "opens_at": opens_at,
                "closes_at": closes_at,
                "budget_cents": budget_cents,
                "owner": actor_name(actor),
                "members": [actor_name(actor)],
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._programs[program["id"]] = program
        self._record(actor, "program_create", program["id"], {"name": name})
        return self._program_view(program)

    def get_program(self, actor, program_id, now=None):
        self._check_role(actor, "read")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        return self._program_view(program, now=now)

    def list_programs(self, actor, now=None):
        self._check_role(actor, "read")
        name = actor_name(actor)
        role = getattr(actor, "role", None)
        result = []
        for program in self._programs.values():
            if role == "admin" or name in program["members"]:
                result.append(self._program_view(program, now=now))
        return result

    def add_member(self, actor, program_id, username):
        """Add a member (by username) to a grant program."""
        self._check_role(actor, "manage_members")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        _text(username, "username")
        with self._lock:
            if username not in program["members"]:
                program["members"].append(username)
        self._record(actor, "member_add", program_id, {"username": username})
        return self._program_view(program)

    def program_summary(self, actor, program_id, now=None):
        """Counts and money sums for one program, computed on read."""
        self._check_role(actor, "read")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        by_status = {status: 0 for status in APPLICATION_STATUSES}
        for app in self._applications.values():
            if app["program_id"] == program_id:
                by_status[app["status"]] += 1
        report_counts = {"pending": 0, "overdue": 0, "submitted": 0}
        for report in self._reports.values():
            if report["program_id"] == program_id:
                report_counts[self._report_status(report, moment)] += 1
        view = self._program_view(program, now=moment)
        return {
            "program_id": program_id,
            "status": view["status"],
            "budget_cents": program["budget_cents"],
            "awarded_cents": view["awarded_cents"],
            "remaining_cents": view["remaining_cents"],
            "applications_by_status": by_status,
            "awards": sum(1 for a in self._awards.values()
                          if a["program_id"] == program_id),
            "reports_by_status": report_counts,
        }

    # -- applicant organizations -------------------------------------------

    def create_organization(self, actor, ref, label):
        """Register an applicant organization by opaque reference."""
        self._check_role(actor, "enter")
        _text(ref, "ref")
        _text(label, "label")
        with self._lock:
            for existing in self._organizations.values():
                if existing["ref"] == ref:
                    raise ValidationError("organization ref already exists: %r" % (ref,))
            org = {
                "id": self._mint("org-"),
                "ref": ref,
                "label": label,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._organizations[org["id"]] = org
        self._record(actor, "organization_create", org["id"], {"ref": ref})
        return dict(org)

    def update_organization(self, actor, org_id, label):
        """Update an organization's profile label."""
        self._check_role(actor, "enter")
        org = self._organization(org_id)
        _text(label, "label")
        with self._lock:
            org["label"] = label
        self._record(actor, "organization_update", org_id, {})
        return dict(org)

    def get_organization(self, actor, org_id):
        self._check_role(actor, "read")
        return dict(self._organization(org_id))

    def list_organizations(self, actor):
        self._check_role(actor, "read")
        return [dict(o) for o in self._organizations.values()]

    # -- applications --------------------------------------------------------

    def create_application(self, actor, program_id, org_id, requested_cents,
                           summary, form_id=None, responses=None):
        """Enter an application record in ``draft`` status."""
        self._check_role(actor, "enter")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        self._organization(org_id)
        _money(requested_cents, "requested_cents", allow_zero=False)
        _text(summary, "summary")
        if form_id is not None:
            form = self._forms.get(form_id)
            if form is None or form["program_id"] != program_id:
                raise NotFoundError("no such form in this program: %r" % (form_id,))
        if responses is not None and not isinstance(responses, dict):
            raise ValidationError("responses must be an object of field values")
        with self._lock:
            app = {
                "id": self._mint("app-"),
                "program_id": program_id,
                "org_id": org_id,
                "form_id": form_id,
                "requested_cents": requested_cents,
                "summary": summary,
                "responses": dict(responses) if responses else {},
                "status": "draft",
                "submitted_by": actor_name(actor),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._applications[app["id"]] = app
        self._record(actor, "application_create", app["id"],
                     {"program_id": program_id, "org_id": org_id})
        return dict(app)

    def get_application(self, actor, application_id):
        self._check_role(actor, "read")
        app = self._application(application_id)
        self._check_program_access(actor, self._program_of_application(app))
        return dict(app)

    def list_applications(self, actor, program_id, status=None):
        self._check_role(actor, "read")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        if status is not None and status not in APPLICATION_STATUSES:
            raise ValidationError("unknown application status: %r" % (status,))
        return [
            dict(a) for a in self._applications.values()
            if a["program_id"] == program_id
            and (status is None or a["status"] == status)
        ]

    def _transition(self, actor, application_id, action, from_states, to_state,
                    audit_action):
        self._check_role(actor, action)
        app = self._application(application_id)
        self._check_program_access(actor, self._program_of_application(app))
        with self._lock:
            if app["status"] not in from_states:
                raise ValidationError(
                    "application %s is %r; cannot become %r from here"
                    % (application_id, app["status"], to_state)
                )
            app["status"] = to_state
        self._record(actor, audit_action, application_id, {"status": to_state})
        return dict(app)

    def submit_application(self, actor, application_id):
        return self._transition(actor, application_id, "enter",
                                ("draft",), "submitted", "application_submit")

    def start_review(self, actor, application_id):
        return self._transition(actor, application_id, "decide",
                                ("submitted",), "under_review", "application_review_start")

    def withdraw_application(self, actor, application_id):
        return self._transition(actor, application_id, "enter",
                                ("draft", "submitted", "under_review"),
                                "withdrawn", "application_withdraw")

    # -- reviews ---------------------------------------------------------------

    def add_review(self, actor, application_id, recommendation, note):
        """Record a reviewer's recommendation and note, verbatim.

        The recommendation is the reviewer's own recorded outcome; it
        is never aggregated and never decides anything by itself.
        """
        self._check_role(actor, "decide")
        app = self._application(application_id)
        self._check_program_access(actor, self._program_of_application(app))
        if recommendation not in RECOMMENDATIONS:
            raise ValidationError("unknown recommendation: %r" % (recommendation,))
        _text(note, "note")
        with self._lock:
            if app["status"] != "under_review":
                raise ValidationError(
                    "reviews are recorded while an application is under_review; "
                    "this one is %r" % (app["status"],)
                )
            review = {
                "id": self._mint("rev-"),
                "application_id": application_id,
                "reviewer": actor_name(actor),
                "recommendation": recommendation,
                "note": note,
                "created_utc": _utc_now().isoformat(),
            }
            self._reviews[review["id"]] = review
        self._record(actor, "review_add", application_id,
                     {"recommendation": recommendation})
        return dict(review)

    def list_reviews(self, actor, application_id):
        self._check_role(actor, "read")
        app = self._application(application_id)
        self._check_program_access(actor, self._program_of_application(app))
        return [dict(r) for r in self._reviews.values()
                if r["application_id"] == application_id]

    # -- decisions and awards ---------------------------------------------------

    def _check_decider_not_submitter(self, actor, app):
        """Separation of duties seam (AC-5): the decider of an
        application is never the person who submitted it."""
        if actor_name(actor) == app["submitted_by"]:
            raise PermissionDenied(
                "permission denied: the decider of an application may not "
                "be its submitter"
            )

    def _check_award_cap(self, program, amount_cents):
        """Award-cap invariant seam: the awards recorded against a
        program never exceed the program's budget."""
        awarded = sum(
            a["amount_cents"] for a in self._awards.values()
            if a["program_id"] == program["id"]
        )
        if awarded + amount_cents > program["budget_cents"]:
            raise ValidationError(
                "award of %d cents would exceed the program budget: "
                "%d already awarded of %d"
                % (amount_cents, awarded, program["budget_cents"])
            )

    def decide_application(self, actor, application_id, approve,
                           amount_cents=None, note=""):
        """Record a decision on an application under review.

        On approval this also records the award. The whole operation
        validates before anything is stored: a rejected decision
        consumes no id and changes nothing.
        """
        self._check_role(actor, "decide")
        app = self._application(application_id)
        program = self._program_of_application(app)
        self._check_program_access(actor, program)
        self._check_decider_not_submitter(actor, app)
        if not isinstance(approve, bool):
            raise ValidationError("approve must be a boolean")
        if not isinstance(note, str):
            raise ValidationError("note must be a string")
        with self._lock:
            if app["status"] != "under_review":
                raise ValidationError(
                    "only an application under_review can be decided; "
                    "this one is %r" % (app["status"],)
                )
            if approve:
                if amount_cents is None:
                    raise ValidationError("an approval requires amount_cents")
                _money(amount_cents, "amount_cents", allow_zero=False)
                self._check_award_cap(program, amount_cents)
            elif amount_cents is not None:
                raise ValidationError("a decline carries no amount_cents")
            decision = {
                "id": self._mint("dec-"),
                "application_id": application_id,
                "program_id": program["id"],
                "decider": actor_name(actor),
                "approve": approve,
                "amount_cents": amount_cents if approve else None,
                "note": note,
                "created_utc": _utc_now().isoformat(),
            }
            self._decisions[decision["id"]] = decision
            award = None
            if approve:
                award = {
                    "id": self._mint("awd-"),
                    "program_id": program["id"],
                    "application_id": application_id,
                    "org_id": app["org_id"],
                    "amount_cents": amount_cents,
                    "decision_id": decision["id"],
                    "created_by": actor_name(actor),
                    "created_utc": _utc_now().isoformat(),
                }
                self._awards[award["id"]] = award
            app["status"] = "awarded" if approve else "declined"
        self._record(actor, "application_decide", application_id,
                     {"approve": approve,
                      "amount_cents": amount_cents if approve else None})
        result = {"decision": dict(decision)}
        if award is not None:
            result["award"] = dict(award)
        result["application"] = dict(app)
        return result

    def get_award(self, actor, award_id):
        self._check_role(actor, "read")
        award = self._award(award_id)
        self._check_program_access(actor, self._programs[award["program_id"]])
        return dict(award)

    def list_awards(self, actor, program_id):
        self._check_role(actor, "read")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        return [dict(a) for a in self._awards.values()
                if a["program_id"] == program_id]

    # -- post-award reports ------------------------------------------------------

    @staticmethod
    def _report_status(report, moment):
        if report["submitted_at"] is not None:
            return "submitted"
        if moment > _parse_moment(report["due_at"], "due_at"):
            return "overdue"
        return "pending"

    def _report_view(self, report, now=None):
        moment = _parse_moment(now, "now") if now is not None else _utc_now()
        view = dict(report)
        view["status"] = self._report_status(report, moment)
        return view

    def create_report(self, actor, award_id, kind, due_at):
        """Register a post-award report obligation against an award."""
        self._check_role(actor, "record")
        award = self._award(award_id)
        self._check_program_access(actor, self._programs[award["program_id"]])
        if kind not in REPORT_KINDS:
            raise ValidationError("unknown report kind: %r" % (kind,))
        _parse_moment(due_at, "due_at")
        with self._lock:
            report = {
                "id": self._mint("rep-"),
                "award_id": award_id,
                "program_id": award["program_id"],
                "kind": kind,
                "due_at": due_at,
                "submitted_at": None,
                "summary": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._reports[report["id"]] = report
        self._record(actor, "report_create", report["id"], {"award_id": award_id})
        return self._report_view(report)

    def submit_report(self, actor, report_id, summary, submitted_at=None):
        """Record the submission of a post-award report."""
        self._check_role(actor, "record")
        report = self._reports.get(report_id)
        if report is None:
            raise NotFoundError("no such report: %r" % (report_id,))
        self._check_program_access(actor, self._programs[report["program_id"]])
        _text(summary, "summary")
        stamp = submitted_at if submitted_at is not None else _utc_now().isoformat()
        _parse_moment(stamp, "submitted_at")
        with self._lock:
            if report["submitted_at"] is not None:
                raise ValidationError("report %s was already submitted" % report_id)
            report["submitted_at"] = stamp
            report["summary"] = summary
        self._record(actor, "report_submit", report_id, {})
        return self._report_view(report)

    def get_report(self, actor, report_id, now=None):
        self._check_role(actor, "read")
        report = self._reports.get(report_id)
        if report is None:
            raise NotFoundError("no such report: %r" % (report_id,))
        self._check_program_access(actor, self._programs[report["program_id"]])
        return self._report_view(report, now=now)

    def list_reports(self, actor, award_id, now=None):
        self._check_role(actor, "read")
        award = self._award(award_id)
        self._check_program_access(actor, self._programs[award["program_id"]])
        return [self._report_view(r, now=now) for r in self._reports.values()
                if r["award_id"] == award_id]

    # -- documents -----------------------------------------------------------------

    def _resolve_target_program(self, target_type, target_id):
        if target_type == "program":
            return self._program(target_id)
        if target_type == "application":
            return self._program_of_application(self._application(target_id))
        award = self._award(target_id)
        return self._programs[award["program_id"]]

    def create_document(self, actor, target_type, target_id, name, kind,
                        sha256, size_bytes):
        """Record a document's metadata and checksum. Content is
        never stored here; the storage engine is Extended."""
        self._check_role(actor, "record")
        if target_type not in DOCUMENT_TARGETS:
            raise ValidationError("unknown document target type: %r" % (target_type,))
        program = self._resolve_target_program(target_type, target_id)
        self._check_program_access(actor, program)
        _text(name, "name")
        if kind not in DOCUMENT_KINDS:
            raise ValidationError("unknown document kind: %r" % (kind,))
        if not isinstance(sha256, str) or not _SHA256_RE.match(sha256):
            raise ValidationError("sha256 must be 64 hexadecimal characters")
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
            raise ValidationError("size_bytes must be a non-negative integer")
        with self._lock:
            doc = {
                "id": self._mint("doc-"),
                "program_id": program["id"],
                "target_type": target_type,
                "target_id": target_id,
                "name": name,
                "kind": kind,
                "sha256": sha256.lower(),
                "size_bytes": size_bytes,
                "signed_by": None,
                "signed_at": None,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._documents[doc["id"]] = doc
        self._record(actor, "document_create", doc["id"],
                     {"target_type": target_type, "target_id": target_id})
        return dict(doc)

    def sign_document(self, actor, document_id):
        """Record a signature event on a document record. The
        signing ceremony and its cryptographic binding are Extended;
        what is recorded here is who signed, and when."""
        self._check_role(actor, "record")
        doc = self._documents.get(document_id)
        if doc is None:
            raise NotFoundError("no such document: %r" % (document_id,))
        self._check_program_access(actor, self._programs[doc["program_id"]])
        with self._lock:
            if doc["signed_by"] is not None:
                raise ValidationError("document %s is already signed" % document_id)
            doc["signed_by"] = actor_name(actor)
            doc["signed_at"] = _utc_now().isoformat()
        self._record(actor, "document_sign", document_id, {})
        return dict(doc)

    def get_document(self, actor, document_id):
        self._check_role(actor, "read")
        doc = self._documents.get(document_id)
        if doc is None:
            raise NotFoundError("no such document: %r" % (document_id,))
        self._check_program_access(actor, self._programs[doc["program_id"]])
        return dict(doc)

    def list_documents(self, actor, target_type, target_id):
        self._check_role(actor, "read")
        if target_type not in DOCUMENT_TARGETS:
            raise ValidationError("unknown document target type: %r" % (target_type,))
        program = self._resolve_target_program(target_type, target_id)
        self._check_program_access(actor, program)
        return [dict(d) for d in self._documents.values()
                if d["target_type"] == target_type and d["target_id"] == target_id]

    # -- form and workflow registries ------------------------------------------------

    def create_form(self, actor, program_id, name, fields):
        """Register a form definition as data: field names, kinds,
        and required flags. Rendering and the designer are Extended."""
        self._check_role(actor, "record")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        _text(name, "name")
        if not isinstance(fields, list) or not fields:
            raise ValidationError("fields must be a non-empty list")
        cleaned = []
        seen = set()
        for field in fields:
            if not isinstance(field, dict):
                raise ValidationError("each form field must be an object")
            fname = field.get("name")
            _text(fname, "field name")
            if fname in seen:
                raise ValidationError("duplicate form field name: %r" % (fname,))
            seen.add(fname)
            kind = field.get("kind")
            if kind not in FIELD_KINDS:
                raise ValidationError("unknown field kind: %r" % (kind,))
            required = field.get("required", False)
            if not isinstance(required, bool):
                raise ValidationError("field required must be a boolean")
            cleaned.append({"name": fname, "kind": kind, "required": required})
        with self._lock:
            form = {
                "id": self._mint("frm-"),
                "program_id": program_id,
                "name": name,
                "fields": cleaned,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._forms[form["id"]] = form
        self._record(actor, "form_create", form["id"], {"program_id": program_id})
        return dict(form)

    def get_form(self, actor, form_id):
        self._check_role(actor, "read")
        form = self._forms.get(form_id)
        if form is None:
            raise NotFoundError("no such form: %r" % (form_id,))
        self._check_program_access(actor, self._programs[form["program_id"]])
        return dict(form)

    def list_forms(self, actor, program_id):
        self._check_role(actor, "read")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        return [dict(f) for f in self._forms.values()
                if f["program_id"] == program_id]

    def create_workflow(self, actor, program_id, name, steps):
        """Register a workflow definition as data: an ordered list of
        step names. The registry never executes a definition --
        registering one changes no application, ever. Execution is
        Extended."""
        self._check_role(actor, "record")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        _text(name, "name")
        if not isinstance(steps, list) or not steps:
            raise ValidationError("steps must be a non-empty list of step names")
        for step in steps:
            _text(step, "workflow step")
        with self._lock:
            workflow = {
                "id": self._mint("wfl-"),
                "program_id": program_id,
                "name": name,
                "steps": list(steps),
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._workflows[workflow["id"]] = workflow
        self._record(actor, "workflow_create", workflow["id"],
                     {"program_id": program_id})
        return dict(workflow)

    def get_workflow(self, actor, workflow_id):
        self._check_role(actor, "read")
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise NotFoundError("no such workflow: %r" % (workflow_id,))
        self._check_program_access(actor, self._programs[workflow["program_id"]])
        return dict(workflow)

    def list_workflows(self, actor, program_id):
        self._check_role(actor, "read")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        return [dict(w) for w in self._workflows.values()
                if w["program_id"] == program_id]

    # -- communications records ---------------------------------------------------------

    def create_message(self, actor, program_id, org_id, direction, body):
        """Record a message exchanged with an applicant organization."""
        self._check_role(actor, "record")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        self._organization(org_id)
        if direction not in MESSAGE_DIRECTIONS:
            raise ValidationError("unknown message direction: %r" % (direction,))
        _text(body, "body")
        with self._lock:
            message = {
                "id": self._mint("msg-"),
                "program_id": program_id,
                "org_id": org_id,
                "direction": direction,
                "body": body,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._messages[message["id"]] = message
        self._record(actor, "message_create", message["id"],
                     {"program_id": program_id, "org_id": org_id})
        return dict(message)

    def list_messages(self, actor, program_id, org_id=None):
        self._check_role(actor, "read")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        return [dict(m) for m in self._messages.values()
                if m["program_id"] == program_id
                and (org_id is None or m["org_id"] == org_id)]

    def create_note(self, actor, application_id, body):
        """Record an internal staff note on an application. Notes are
        internal: reading them takes the same staff permission as
        writing them, so a read-only role never sees them."""
        self._check_role(actor, "enter")
        app = self._application(application_id)
        self._check_program_access(actor, self._program_of_application(app))
        _text(body, "body")
        with self._lock:
            note = {
                "id": self._mint("note-"),
                "application_id": application_id,
                "program_id": app["program_id"],
                "body": body,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._notes[note["id"]] = note
        self._record(actor, "note_create", note["id"],
                     {"application_id": application_id})
        return dict(note)

    def list_notes(self, actor, application_id):
        self._check_role(actor, "enter")
        app = self._application(application_id)
        self._check_program_access(actor, self._program_of_application(app))
        return [dict(n) for n in self._notes.values()
                if n["application_id"] == application_id]

    def create_notification(self, actor, program_id, org_id, text):
        """Record a notification. Delivery (email, SMS, push) is
        Extended; what is recorded here is the notification itself."""
        self._check_role(actor, "record")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        if org_id is not None:
            self._organization(org_id)
        _text(text, "text")
        with self._lock:
            notification = {
                "id": self._mint("ntf-"),
                "program_id": program_id,
                "org_id": org_id,
                "text": text,
                "created_by": actor_name(actor),
                "created_utc": _utc_now().isoformat(),
            }
            self._notifications[notification["id"]] = notification
        self._record(actor, "notification_create", notification["id"],
                     {"program_id": program_id})
        return dict(notification)

    def list_notifications(self, actor, program_id):
        self._check_role(actor, "read")
        program = self._program(program_id)
        self._check_program_access(actor, program)
        return [dict(n) for n in self._notifications.values()
                if n["program_id"] == program_id]

    # -- search ---------------------------------------------------------------------------

    def search(self, actor, query):
        """Literal case-insensitive substring search over the programs
        the actor can access, all organizations, and the summaries of
        applications in accessible programs."""
        self._check_role(actor, "read")
        _text(query, "query")
        needle = query.lower()
        name = actor_name(actor)
        role = getattr(actor, "role", None)

        def accessible(program):
            return role == "admin" or name in program["members"]

        programs = [
            self._program_view(p) for p in self._programs.values()
            if accessible(p)
            and (needle in p["name"].lower() or needle in p["title"].lower())
        ]
        organizations = [
            dict(o) for o in self._organizations.values()
            if needle in o["ref"].lower() or needle in o["label"].lower()
        ]
        applications = [
            dict(a) for a in self._applications.values()
            if accessible(self._programs[a["program_id"]])
            and needle in a["summary"].lower()
        ]
        return {
            "programs": programs,
            "organizations": organizations,
            "applications": applications,
        }
