"""Accounting store: books, chart of accounts, double-entry journal,
invoices, payments, expenses, budgets, reconciliation, period close,
and financial reporting.

Clean-room implementation of the union spec's implementation contract.

Two boundaries are enforced on every book-scoped operation:

1. Membership -- the actor must be a member of the book, or hold the
   platform ``admin`` role, else :class:`PermissionDenied`.
2. Role permission -- the action named for the operation must be in
   the actor's role permission set (see :mod:`accounting.access`).

Every operation validates fully before it mutates anything: a failed
operation consumes no id and changes nothing. Ids are sequential per
object type with fixed prefixes (``book-``, ``acct-``, ``je-``,
``inv-``, ``pay-``, ``exp-``, ``bud-``, ``rec-``).

The store records every successful mutation to its audit log (when
one is attached). Reads are not audited here; denied attempts and
audit reads are the HTTP layer's responsibility, so nothing is
recorded twice.

Choices where the spec is silent (documented here):

- A missing object (including an id that belongs to another book)
  raises :class:`NotFoundError`; a malformed reference inside a
  payload (for example an ``account_id`` in entry lines that does
  not name an account in the book) raises :class:`ValidationError`,
  exactly as the spec states for lines, budget lines and similar.
- ``record_payment`` follows the same rule: a missing / cross-book
  invoice raises :class:`NotFoundError`, while an invoice in the
  wrong status raises :class:`ValidationError`.
- Rejecting an object leaves ``approved_by`` unchanged (it records
  approval only); submitting (re-)sets ``submitted_by``.
- Report rows follow account creation order.
- All money is integer cents: any amount that is not a Python
  ``int`` (booleans and floats included, even integral floats) raises
  :class:`ValidationError`.
"""

import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

ACCOUNT_TYPES = ("asset", "liability", "equity", "revenue", "expense")
DEBIT_NORMAL_TYPES = frozenset(("asset", "expense"))

ENTRY_STATUSES = ("draft", "pending", "posted", "rejected", "void")
INVOICE_STATUSES = ("draft", "pending", "issued", "rejected", "void", "paid")
EXPENSE_STATUSES = ("draft", "pending", "approved", "rejected", "void", "reimbursed")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _is_admin(actor):
    return getattr(actor, "role", None) == "admin"


def _maybe_require(actor, action):
    """Enforce permissions when ``actor`` is a User-like object.

    Plain string actors carry identity (for provenance) but no role, so
    there is nothing to enforce against; enforcement for those happens
    in the service layer, which knows the role registry.
    """
    if actor is not None and hasattr(actor, "role"):
        require(actor, action)


def _validate_non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _validate_string(value, what):
    if not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _require_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer (cents)" % (what,))
    return value


def _validate_cents_nonnegative(value, what):
    _require_int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _validate_cents_positive(value, what):
    _require_int(value, what)
    if value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _validate_cents_any(value, what):
    _require_int(value, what)
    return value


def _validate_date(value, what="date"):
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ValidationError("%s must be an ISO date (YYYY-MM-DD): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("%s is not a valid calendar date: %r" % (what, value)) from exc
    return value


def _validate_period(value, what="period"):
    if not isinstance(value, str) or not _PERIOD_RE.match(value):
        raise ValidationError("%s must be a fiscal period (YYYY-MM): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValidationError("%s is not a valid fiscal period: %r" % (what, value)) from exc
    return value


def _normal_balance(account_type, debit_cents, credit_cents):
    if account_type in DEBIT_NORMAL_TYPES:
        return debit_cents - credit_cents
    return credit_cents - debit_cents


class AccountingStore:
    """In-memory store for the accounting service."""

    def __init__(self, audit=None):
        self.audit = audit
        self._books = {}
        self._book_order = []
        self._accounts = {}
        self._entries = {}
        self._invoices = {}
        self._payments = {}
        self._expenses = {}
        self._budgets = {}  # (book_id, period) -> budget dict
        self._reconciliations = {}
        self._counters = {
            "book": 0,
            "acct": 0,
            "je": 0,
            "inv": 0,
            "pay": 0,
            "exp": 0,
            "bud": 0,
            "rec": 0,
        }
        self._lock = threading.RLock()

    # -- internal helpers --------------------------------------------

    def _next_id(self, prefix):
        self._counters[prefix] += 1
        return "%s-%d" % (prefix, self._counters[prefix])

    def _audit(self, actor, action, target, details=None):
        if self.audit is not None:
            self.audit.record(actor_name(actor), action, target, details=details)

    def _get_book_record(self, book_id):
        book = self._books.get(book_id)
        if book is None:
            raise NotFoundError("book not found: %r" % (book_id,))
        return book

    def _require_book_access(self, book_id, actor, action):
        """Return the book, enforcing membership then role permission."""
        book = self._get_book_record(book_id)
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        if actor_name(actor) not in book["members"] and not _is_admin(actor):
            raise PermissionDenied(
                "permission denied: user %r is not a member of book %r"
                % (actor_name(actor), book_id)
            )
        _maybe_require(actor, action)
        return book

    @staticmethod
    def _copy_book(book):
        copied = dict(book)
        copied["members"] = list(book["members"])
        copied["closed_periods"] = list(book["closed_periods"])
        return copied

    @staticmethod
    def _copy_lines(record):
        copied = dict(record)
        copied["lines"] = [dict(line) for line in record["lines"]]
        return copied

    def _get_account_record(self, book_id, account_id):
        account = self._accounts.get(account_id)
        if account is None or account["book_id"] != book_id:
            raise NotFoundError("account not found: %r" % (account_id,))
        return account

    def _get_entry_record(self, book_id, entry_id):
        entry = self._entries.get(entry_id)
        if entry is None or entry["book_id"] != book_id:
            raise NotFoundError("entry not found: %r" % (entry_id,))
        return entry

    def _get_invoice_record(self, book_id, invoice_id):
        invoice = self._invoices.get(invoice_id)
        if invoice is None or invoice["book_id"] != book_id:
            raise NotFoundError("invoice not found: %r" % (invoice_id,))
        return invoice

    def _get_expense_record(self, book_id, expense_id):
        expense = self._expenses.get(expense_id)
        if expense is None or expense["book_id"] != book_id:
            raise NotFoundError("expense not found: %r" % (expense_id,))
        return expense

    def _book_accounts(self, book_id):
        return [a for a in self._accounts.values() if a["book_id"] == book_id]

    def _posted_entries(self, book_id):
        return [
            e
            for e in self._entries.values()
            if e["book_id"] == book_id and e["status"] == "posted"
        ]

    def _totals_by_account(self, book_id, period_eq=None, period_le=None):
        """Return {account_id: [debit_cents, credit_cents]} for posted entries."""
        totals = {}
        for entry in self._posted_entries(book_id):
            if period_eq is not None and entry["period"] != period_eq:
                continue
            if period_le is not None and entry["period"] > period_le:
                continue
            for line in entry["lines"]:
                pair = totals.setdefault(line["account_id"], [0, 0])
                pair[0] += line["debit_cents"]
                pair[1] += line["credit_cents"]
        return totals

    # -- books and members --------------------------------------------

    def create_book(self, name, actor):
        """Create a book; the creator is owner and first member."""
        _validate_non_empty(name, "book name")
        if actor is None or not actor_name(actor):
            raise PermissionDenied("permission denied: no user supplied")
        _maybe_require(actor, "create_book")
        owner = actor_name(actor)
        with self._lock:
            book_id = self._next_id("book")
            book = {
                "id": book_id,
                "name": name,
                "owner": owner,
                "members": [owner],
                "closed_periods": [],
                "created_by": owner,
                "created_utc": _utc_now(),
            }
            self._books[book_id] = book
            self._book_order.append(book_id)
            self._audit(actor, "book_create", book_id, details={"name": name})
            return self._copy_book(book)

    def list_books(self, actor):
        """Return the book dicts ``actor`` may see."""
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        _maybe_require(actor, "read")
        name = actor_name(actor)
        admin = _is_admin(actor)
        with self._lock:
            return [
                self._copy_book(self._books[bid])
                for bid in self._book_order
                if admin or name in self._books[bid]["members"]
            ]

    def get_book(self, book_id, actor):
        """Return one book dict visible to ``actor``."""
        with self._lock:
            book = self._require_book_access(book_id, actor, "read")
            return self._copy_book(book)

    def add_member(self, book_id, username, actor):
        """Add ``username`` to a book. Owner or platform admin only."""
        _validate_non_empty(username, "username")
        if actor is None:
            raise PermissionDenied("permission denied: no user supplied")
        with self._lock:
            book = self._get_book_record(book_id)
            if book["owner"] != actor_name(actor) and not _is_admin(actor):
                raise PermissionDenied(
                    "permission denied: only the book owner or a platform "
                    "admin may add members to book %r" % (book_id,)
                )
            if username in book["members"]:
                raise ValidationError(
                    "user %r is already a member of book %r" % (username, book_id)
                )
            book["members"].append(username)
            self._audit(actor, "member_add", book_id, details={"username": username})
            return self._copy_book(book)

    # -- chart of accounts --------------------------------------------

    def create_account(self, book_id, code, name, account_type, actor):
        """Create an account inside a book."""
        _validate_non_empty(code, "account code")
        _validate_non_empty(name, "account name")
        if account_type not in ACCOUNT_TYPES:
            raise ValidationError(
                "account_type must be one of %s" % (", ".join(ACCOUNT_TYPES),)
            )
        with self._lock:
            self._require_book_access(book_id, actor, "enter")
            for existing in self._accounts.values():
                if existing["book_id"] == book_id and existing["code"] == code:
                    raise ValidationError(
                        "account code %r already exists in book %r" % (code, book_id)
                    )
            account_id = self._next_id("acct")
            account = {
                "id": account_id,
                "book_id": book_id,
                "code": code,
                "name": name,
                "type": account_type,
                "active": True,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._accounts[account_id] = account
            self._audit(actor, "account_create", account_id, details={"code": code})
            return dict(account)

    def list_accounts(self, book_id, actor):
        """Return a book's accounts, in creation order."""
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return [dict(a) for a in self._book_accounts(book_id)]

    def get_account(self, book_id, account_id, actor):
        """Return one account dict from a book."""
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return dict(self._get_account_record(book_id, account_id))

    # -- journal entries ----------------------------------------------

    def create_entry(self, book_id, date, memo="", lines=None, actor=None):
        """Create a balanced double-entry journal entry in ``draft``.

        The entry must balance whole-or-nothing: total debits must
        equal total credits and be positive, or nothing is stored.
        """
        _validate_date(date, "date")
        if memo is None:
            memo = ""
        _validate_string(memo, "memo")
        if not isinstance(lines, (list, tuple)) or len(lines) < 2:
            raise ValidationError("entry lines must be a list of at least two lines")
        period = date[:7]
        with self._lock:
            book = self._require_book_access(book_id, actor, "enter")
            if period in book["closed_periods"]:
                raise ValidationError("period %r is closed" % (period,))
            normalized = []
            total_debits = 0
            total_credits = 0
            for line in lines:
                if not isinstance(line, dict):
                    raise ValidationError("entry line must be an object")
                account_id = line.get("account_id")
                if not isinstance(account_id, str) or not account_id:
                    raise ValidationError("entry line account_id must be a string")
                account = self._accounts.get(account_id)
                if account is None or account["book_id"] != book_id:
                    raise ValidationError(
                        "entry line account_id does not name an account in this book: %r"
                        % (account_id,)
                    )
                debit = line.get("debit_cents", 0)
                credit = line.get("credit_cents", 0)
                _validate_cents_nonnegative(debit, "debit_cents")
                _validate_cents_nonnegative(credit, "credit_cents")
                if not ((debit > 0 and credit == 0) or (debit == 0 and credit > 0)):
                    raise ValidationError(
                        "each entry line must have exactly one side positive and the other zero"
                    )
                total_debits += debit
                total_credits += credit
                normalized.append(
                    {"account_id": account_id, "debit_cents": debit, "credit_cents": credit}
                )
            # The balance check: an unbalanced entry is rejected whole.
            if total_debits != total_credits or total_debits <= 0:
                raise ValidationError(
                    "entry must balance: total debits must equal total credits and be positive"
                )
            entry_id = self._next_id("je")
            entry = {
                "id": entry_id,
                "book_id": book_id,
                "date": date,
                "period": period,
                "memo": memo,
                "lines": normalized,
                "total_cents": total_debits,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "submitted_by": None,
                "approved_by": None,
                "posted_utc": None,
            }
            self._entries[entry_id] = entry
            self._audit(actor, "entry_create", entry_id, details={"period": period})
            return self._copy_lines(entry)

    def get_entry(self, book_id, entry_id, actor):
        """Return one entry dict from a book."""
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return self._copy_lines(self._get_entry_record(book_id, entry_id))

    def list_entries(self, book_id, actor, status=None):
        """Return a book's entries, in creation order, optionally filtered."""
        if status is not None and status not in ENTRY_STATUSES:
            raise ValidationError("unknown entry status: %r" % (status,))
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return [
                self._copy_lines(e)
                for e in self._entries.values()
                if e["book_id"] == book_id and (status is None or e["status"] == status)
            ]

    def submit_entry(self, book_id, entry_id, actor):
        """Move an entry ``draft``/``rejected`` -> ``pending``."""
        with self._lock:
            self._require_book_access(book_id, actor, "submit")
            entry = self._get_entry_record(book_id, entry_id)
            if entry["status"] not in ("draft", "rejected"):
                raise ValidationError(
                    "entry in status %r cannot be submitted" % (entry["status"],)
                )
            entry["status"] = "pending"
            entry["submitted_by"] = actor_name(actor)
            self._audit(actor, "entry_submit", entry_id)
            return self._copy_lines(entry)

    def approve_entry(self, book_id, entry_id, actor):
        """Move an entry ``pending`` -> ``posted`` (separation of duties)."""
        with self._lock:
            book = self._require_book_access(book_id, actor, "approve")
            entry = self._get_entry_record(book_id, entry_id)
            if entry["status"] != "pending":
                raise ValidationError(
                    "entry in status %r cannot be approved" % (entry["status"],)
                )
            if actor_name(actor) == entry["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not approve their own entry"
                )
            if entry["period"] in book["closed_periods"]:
                raise ValidationError("period %r is closed" % (entry["period"],))
            entry["status"] = "posted"
            entry["approved_by"] = actor_name(actor)
            entry["posted_utc"] = _utc_now()
            self._audit(actor, "entry_post", entry_id)
            return self._copy_lines(entry)

    def reject_entry(self, book_id, entry_id, actor):
        """Move an entry ``pending`` -> ``rejected`` (separation of duties)."""
        with self._lock:
            self._require_book_access(book_id, actor, "approve")
            entry = self._get_entry_record(book_id, entry_id)
            if entry["status"] != "pending":
                raise ValidationError(
                    "entry in status %r cannot be rejected" % (entry["status"],)
                )
            if actor_name(actor) == entry["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not reject their own entry"
                )
            entry["status"] = "rejected"
            self._audit(actor, "entry_reject", entry_id)
            return self._copy_lines(entry)

    def void_entry(self, book_id, entry_id, actor):
        """Move an entry ``draft``/``rejected`` -> ``void``."""
        with self._lock:
            book = self._require_book_access(book_id, actor, "enter")
            entry = self._get_entry_record(book_id, entry_id)
            if entry["status"] not in ("draft", "rejected"):
                raise ValidationError(
                    "entry in status %r cannot be voided" % (entry["status"],)
                )
            if (
                actor_name(actor) != entry["created_by"]
                and actor_name(actor) != book["owner"]
                and not _is_admin(actor)
            ):
                raise PermissionDenied(
                    "permission denied: only the creator, the book owner, or a "
                    "platform admin may void this entry"
                )
            entry["status"] = "void"
            self._audit(actor, "entry_void", entry_id)
            return self._copy_lines(entry)

    # -- invoices -------------------------------------------------------

    def create_invoice(self, book_id, customer, date, due_date, lines, actor):
        """Create an invoice in ``draft``; amounts are computed here."""
        _validate_non_empty(customer, "customer")
        _validate_date(date, "date")
        _validate_date(due_date, "due_date")
        if due_date < date:
            raise ValidationError("due_date must not be before date")
        if not isinstance(lines, (list, tuple)) or len(lines) < 1:
            raise ValidationError("invoice lines must be a list of at least one line")
        with self._lock:
            self._require_book_access(book_id, actor, "enter")
            normalized = []
            total = 0
            for line in lines:
                if not isinstance(line, dict):
                    raise ValidationError("invoice line must be an object")
                description = line.get("description")
                _validate_non_empty(description, "invoice line description")
                quantity = line.get("quantity")
                _require_int(quantity, "quantity")
                if quantity < 1:
                    raise ValidationError("quantity must be at least 1")
                unit_price = line.get("unit_price_cents")
                _validate_cents_nonnegative(unit_price, "unit_price_cents")
                amount = quantity * unit_price
                total += amount
                normalized.append(
                    {
                        "description": description,
                        "quantity": quantity,
                        "unit_price_cents": unit_price,
                        "amount_cents": amount,
                    }
                )
            if total <= 0:
                raise ValidationError("invoice total must be positive")
            invoice_id = self._next_id("inv")
            invoice = {
                "id": invoice_id,
                "book_id": book_id,
                "customer": customer,
                "date": date,
                "due_date": due_date,
                "lines": normalized,
                "total_cents": total,
                "paid_cents": 0,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "submitted_by": None,
                "approved_by": None,
                "issued_utc": None,
            }
            self._invoices[invoice_id] = invoice
            self._audit(actor, "invoice_create", invoice_id)
            return self._copy_lines(invoice)

    def get_invoice(self, book_id, invoice_id, actor):
        """Return one invoice dict from a book."""
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return self._copy_lines(self._get_invoice_record(book_id, invoice_id))

    def list_invoices(self, book_id, actor, status=None):
        """Return a book's invoices, in creation order, optionally filtered."""
        if status is not None and status not in INVOICE_STATUSES:
            raise ValidationError("unknown invoice status: %r" % (status,))
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return [
                self._copy_lines(inv)
                for inv in self._invoices.values()
                if inv["book_id"] == book_id and (status is None or inv["status"] == status)
            ]

    def submit_invoice(self, book_id, invoice_id, actor):
        """Move an invoice ``draft``/``rejected`` -> ``pending``."""
        with self._lock:
            self._require_book_access(book_id, actor, "submit")
            invoice = self._get_invoice_record(book_id, invoice_id)
            if invoice["status"] not in ("draft", "rejected"):
                raise ValidationError(
                    "invoice in status %r cannot be submitted" % (invoice["status"],)
                )
            invoice["status"] = "pending"
            invoice["submitted_by"] = actor_name(actor)
            self._audit(actor, "invoice_submit", invoice_id)
            return self._copy_lines(invoice)

    def approve_invoice(self, book_id, invoice_id, actor):
        """Move an invoice ``pending`` -> ``issued`` (separation of duties)."""
        with self._lock:
            self._require_book_access(book_id, actor, "approve")
            invoice = self._get_invoice_record(book_id, invoice_id)
            if invoice["status"] != "pending":
                raise ValidationError(
                    "invoice in status %r cannot be approved" % (invoice["status"],)
                )
            if actor_name(actor) == invoice["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not approve their own invoice"
                )
            invoice["status"] = "issued"
            invoice["approved_by"] = actor_name(actor)
            invoice["issued_utc"] = _utc_now()
            self._audit(actor, "invoice_issue", invoice_id)
            return self._copy_lines(invoice)

    def reject_invoice(self, book_id, invoice_id, actor):
        """Move an invoice ``pending`` -> ``rejected`` (separation of duties)."""
        with self._lock:
            self._require_book_access(book_id, actor, "approve")
            invoice = self._get_invoice_record(book_id, invoice_id)
            if invoice["status"] != "pending":
                raise ValidationError(
                    "invoice in status %r cannot be rejected" % (invoice["status"],)
                )
            if actor_name(actor) == invoice["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not reject their own invoice"
                )
            invoice["status"] = "rejected"
            self._audit(actor, "invoice_reject", invoice_id)
            return self._copy_lines(invoice)

    def void_invoice(self, book_id, invoice_id, actor):
        """Move an invoice ``draft``/``rejected`` (or unpaid ``issued``) -> ``void``."""
        with self._lock:
            book = self._require_book_access(book_id, actor, "enter")
            invoice = self._get_invoice_record(book_id, invoice_id)
            allowed = invoice["status"] in ("draft", "rejected") or (
                invoice["status"] == "issued" and invoice["paid_cents"] == 0
            )
            if not allowed:
                raise ValidationError(
                    "invoice in status %r cannot be voided" % (invoice["status"],)
                )
            if (
                actor_name(actor) != invoice["created_by"]
                and actor_name(actor) != book["owner"]
                and not _is_admin(actor)
            ):
                raise PermissionDenied(
                    "permission denied: only the creator, the book owner, or a "
                    "platform admin may void this invoice"
                )
            invoice["status"] = "void"
            self._audit(actor, "invoice_void", invoice_id)
            return self._copy_lines(invoice)

    # -- payments -------------------------------------------------------

    def record_payment(self, book_id, invoice_id, amount_cents, date, actor, method=""):
        """Record a payment against an ``issued`` invoice.

        Everything is validated before anything is applied: a failed
        payment changes neither the invoice nor the id sequence.
        """
        _validate_cents_positive(amount_cents, "amount_cents")
        _validate_date(date, "date")
        if method is None:
            method = ""
        _validate_string(method, "method")
        with self._lock:
            self._require_book_access(book_id, actor, "pay")
            invoice = self._get_invoice_record(book_id, invoice_id)
            if invoice["status"] != "issued":
                raise ValidationError(
                    "payments may only be recorded against an issued invoice"
                )
            remaining = invoice["total_cents"] - invoice["paid_cents"]
            if amount_cents > remaining:
                raise ValidationError("payment exceeds the invoice balance due")
            payment_id = self._next_id("pay")
            payment = {
                "id": payment_id,
                "book_id": book_id,
                "invoice_id": invoice_id,
                "amount_cents": amount_cents,
                "date": date,
                "method": method,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._payments[payment_id] = payment
            invoice["paid_cents"] += amount_cents
            if invoice["paid_cents"] == invoice["total_cents"]:
                invoice["status"] = "paid"
            self._audit(actor, "payment_record", payment_id, details={"invoice_id": invoice_id})
            return dict(payment)

    def list_payments(self, book_id, actor, invoice_id=None):
        """Return a book's payments, in creation order, optionally filtered."""
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return [
                dict(p)
                for p in self._payments.values()
                if p["book_id"] == book_id
                and (invoice_id is None or p["invoice_id"] == invoice_id)
            ]

    # -- expenses -------------------------------------------------------

    def create_expense(self, book_id, date, category, description, amount_cents, actor):
        """Create an expense record in ``draft``."""
        _validate_date(date, "date")
        _validate_non_empty(category, "category")
        _validate_non_empty(description, "description")
        _validate_cents_positive(amount_cents, "amount_cents")
        with self._lock:
            self._require_book_access(book_id, actor, "enter")
            expense_id = self._next_id("exp")
            expense = {
                "id": expense_id,
                "book_id": book_id,
                "date": date,
                "category": category,
                "description": description,
                "amount_cents": amount_cents,
                "status": "draft",
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
                "submitted_by": None,
                "approved_by": None,
            }
            self._expenses[expense_id] = expense
            self._audit(actor, "expense_create", expense_id)
            return dict(expense)

    def get_expense(self, book_id, expense_id, actor):
        """Return one expense dict from a book."""
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return dict(self._get_expense_record(book_id, expense_id))

    def list_expenses(self, book_id, actor, status=None):
        """Return a book's expenses, in creation order, optionally filtered."""
        if status is not None and status not in EXPENSE_STATUSES:
            raise ValidationError("unknown expense status: %r" % (status,))
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            return [
                dict(e)
                for e in self._expenses.values()
                if e["book_id"] == book_id and (status is None or e["status"] == status)
            ]

    def submit_expense(self, book_id, expense_id, actor):
        """Move an expense ``draft``/``rejected`` -> ``pending``."""
        with self._lock:
            self._require_book_access(book_id, actor, "submit")
            expense = self._get_expense_record(book_id, expense_id)
            if expense["status"] not in ("draft", "rejected"):
                raise ValidationError(
                    "expense in status %r cannot be submitted" % (expense["status"],)
                )
            expense["status"] = "pending"
            expense["submitted_by"] = actor_name(actor)
            self._audit(actor, "expense_submit", expense_id)
            return dict(expense)

    def approve_expense(self, book_id, expense_id, actor):
        """Move an expense ``pending`` -> ``approved`` (separation of duties)."""
        with self._lock:
            self._require_book_access(book_id, actor, "approve")
            expense = self._get_expense_record(book_id, expense_id)
            if expense["status"] != "pending":
                raise ValidationError(
                    "expense in status %r cannot be approved" % (expense["status"],)
                )
            if actor_name(actor) == expense["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not approve their own expense"
                )
            expense["status"] = "approved"
            expense["approved_by"] = actor_name(actor)
            self._audit(actor, "expense_approve", expense_id)
            return dict(expense)

    def reject_expense(self, book_id, expense_id, actor):
        """Move an expense ``pending`` -> ``rejected`` (separation of duties)."""
        with self._lock:
            self._require_book_access(book_id, actor, "approve")
            expense = self._get_expense_record(book_id, expense_id)
            if expense["status"] != "pending":
                raise ValidationError(
                    "expense in status %r cannot be rejected" % (expense["status"],)
                )
            if actor_name(actor) == expense["created_by"]:
                raise PermissionDenied(
                    "permission denied: the creator may not reject their own expense"
                )
            expense["status"] = "rejected"
            self._audit(actor, "expense_reject", expense_id)
            return dict(expense)

    def void_expense(self, book_id, expense_id, actor):
        """Move an expense ``draft``/``rejected`` -> ``void``."""
        with self._lock:
            book = self._require_book_access(book_id, actor, "enter")
            expense = self._get_expense_record(book_id, expense_id)
            if expense["status"] not in ("draft", "rejected"):
                raise ValidationError(
                    "expense in status %r cannot be voided" % (expense["status"],)
                )
            if (
                actor_name(actor) != expense["created_by"]
                and actor_name(actor) != book["owner"]
                and not _is_admin(actor)
            ):
                raise PermissionDenied(
                    "permission denied: only the creator, the book owner, or a "
                    "platform admin may void this expense"
                )
            expense["status"] = "void"
            self._audit(actor, "expense_void", expense_id)
            return dict(expense)

    def reimburse_expense(self, book_id, expense_id, actor):
        """Move an expense ``approved`` -> ``reimbursed``."""
        with self._lock:
            self._require_book_access(book_id, actor, "pay")
            expense = self._get_expense_record(book_id, expense_id)
            if expense["status"] != "approved":
                raise ValidationError(
                    "expense in status %r cannot be reimbursed" % (expense["status"],)
                )
            expense["status"] = "reimbursed"
            self._audit(actor, "expense_reimburse", expense_id)
            return dict(expense)

    # -- budgets --------------------------------------------------------

    def set_budget(self, book_id, period, lines, actor):
        """Set (or replace the lines of) the budget for a period."""
        _validate_period(period, "period")
        if not isinstance(lines, (list, tuple)) or len(lines) < 1:
            raise ValidationError("budget lines must be a list of at least one line")
        with self._lock:
            self._require_book_access(book_id, actor, "enter")
            normalized = []
            seen = set()
            total = 0
            for line in lines:
                if not isinstance(line, dict):
                    raise ValidationError("budget line must be an object")
                account_id = line.get("account_id")
                if not isinstance(account_id, str) or not account_id:
                    raise ValidationError("budget line account_id must be a string")
                account = self._accounts.get(account_id)
                if account is None or account["book_id"] != book_id:
                    raise ValidationError(
                        "budget line account_id does not name an account in this book: %r"
                        % (account_id,)
                    )
                if account_id in seen:
                    raise ValidationError(
                        "budget line repeats account %r" % (account_id,)
                    )
                seen.add(account_id)
                amount = line.get("amount_cents")
                _validate_cents_nonnegative(amount, "amount_cents")
                total += amount
                normalized.append({"account_id": account_id, "amount_cents": amount})
            key = (book_id, period)
            existing = self._budgets.get(key)
            now = _utc_now()
            if existing is not None:
                existing["lines"] = normalized
                existing["total_cents"] = total
                existing["updated_utc"] = now
                budget = existing
            else:
                budget_id = self._next_id("bud")
                budget = {
                    "id": budget_id,
                    "book_id": book_id,
                    "period": period,
                    "lines": normalized,
                    "total_cents": total,
                    "created_by": actor_name(actor),
                    "created_utc": now,
                    "updated_utc": now,
                }
                self._budgets[key] = budget
            self._audit(actor, "budget_set", budget["id"], details={"period": period})
            return self._copy_lines(budget)

    def get_budget(self, book_id, period, actor):
        """Return the budget for a period, or raise NotFoundError."""
        _validate_period(period, "period")
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            budget = self._budgets.get((book_id, period))
            if budget is None:
                raise NotFoundError(
                    "no budget set for period %r in book %r" % (period, book_id)
                )
            return self._copy_lines(budget)

    def budget_vs_actual(self, book_id, period, actor):
        """Compare budgeted amounts against posted movement for a period."""
        _validate_period(period, "period")
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            budget = self._budgets.get((book_id, period))
            if budget is None:
                raise NotFoundError(
                    "no budget set for period %r in book %r" % (period, book_id)
                )
            totals = self._totals_by_account(book_id, period_eq=period)
            lines = []
            total_budgeted = 0
            total_actual = 0
            total_variance = 0
            for line in budget["lines"]:
                account = self._get_account_record(book_id, line["account_id"])
                debits, credits = totals.get(line["account_id"], [0, 0])
                actual = _normal_balance(account["type"], debits, credits)
                variance = line["amount_cents"] - actual
                lines.append(
                    {
                        "account_id": account["id"],
                        "code": account["code"],
                        "name": account["name"],
                        "type": account["type"],
                        "budgeted_cents": line["amount_cents"],
                        "actual_cents": actual,
                        "variance_cents": variance,
                    }
                )
                total_budgeted += line["amount_cents"]
                total_actual += actual
                total_variance += variance
            return {
                "book_id": book_id,
                "period": period,
                "lines": lines,
                "total_budgeted_cents": total_budgeted,
                "total_actual_cents": total_actual,
                "total_variance_cents": total_variance,
            }

    # -- balances, activity and reports (posted entries only) -----------

    def trial_balance(self, book_id, actor, period=None):
        """Per-account debit/credit columns; the totals must be equal."""
        if period is not None:
            _validate_period(period, "period")
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            totals = self._totals_by_account(book_id, period_eq=period)
            accounts = []
            total_debits = 0
            total_credits = 0
            for account in self._book_accounts(book_id):
                debits, credits = totals.get(account["id"], [0, 0])
                net = debits - credits
                if net == 0:
                    continue
                debit_cents = net if net > 0 else 0
                credit_cents = -net if net < 0 else 0
                accounts.append(
                    {
                        "account_id": account["id"],
                        "code": account["code"],
                        "name": account["name"],
                        "type": account["type"],
                        "debit_cents": debit_cents,
                        "credit_cents": credit_cents,
                    }
                )
                total_debits += debit_cents
                total_credits += credit_cents
            return {
                "book_id": book_id,
                "period": period,
                "accounts": accounts,
                "total_debits_cents": total_debits,
                "total_credits_cents": total_credits,
                "balanced": total_debits == total_credits,
            }

    def account_balance(self, book_id, account_id, actor, period=None):
        """Raw posted totals and the normal-direction balance for an account."""
        if period is not None:
            _validate_period(period, "period")
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            account = self._get_account_record(book_id, account_id)
            totals = self._totals_by_account(book_id, period_eq=period)
            debits, credits = totals.get(account_id, [0, 0])
            return {
                "account_id": account_id,
                "book_id": book_id,
                "period": period,
                "debit_cents": debits,
                "credit_cents": credits,
                "balance_cents": _normal_balance(account["type"], debits, credits),
            }

    def account_activity(self, book_id, account_id, actor, period=None):
        """The account's posted lines, in entry creation order."""
        if period is not None:
            _validate_period(period, "period")
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            self._get_account_record(book_id, account_id)
            lines = []
            for entry in self._posted_entries(book_id):
                if period is not None and entry["period"] != period:
                    continue
                for line in entry["lines"]:
                    if line["account_id"] != account_id:
                        continue
                    lines.append(
                        {
                            "entry_id": entry["id"],
                            "date": entry["date"],
                            "period": entry["period"],
                            "memo": entry["memo"],
                            "debit_cents": line["debit_cents"],
                            "credit_cents": line["credit_cents"],
                        }
                    )
            return {
                "account_id": account_id,
                "book_id": book_id,
                "period": period,
                "lines": lines,
            }

    def income_statement(self, book_id, period, actor):
        """Revenue, expenses and net income for one period."""
        if period is None:
            raise ValidationError("period is required")
        _validate_period(period, "period")
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            totals = self._totals_by_account(book_id, period_eq=period)
            revenue = []
            expenses = []
            total_revenue = 0
            total_expense = 0
            for account in self._book_accounts(book_id):
                debits, credits = totals.get(account["id"], [0, 0])
                if account["type"] == "revenue":
                    amount = credits - debits
                    if amount == 0:
                        continue
                    revenue.append(
                        {
                            "account_id": account["id"],
                            "code": account["code"],
                            "name": account["name"],
                            "amount_cents": amount,
                        }
                    )
                    total_revenue += amount
                elif account["type"] == "expense":
                    amount = debits - credits
                    if amount == 0:
                        continue
                    expenses.append(
                        {
                            "account_id": account["id"],
                            "code": account["code"],
                            "name": account["name"],
                            "amount_cents": amount,
                        }
                    )
                    total_expense += amount
            return {
                "book_id": book_id,
                "period": period,
                "revenue": revenue,
                "total_revenue_cents": total_revenue,
                "expenses": expenses,
                "total_expense_cents": total_expense,
                "net_income_cents": total_revenue - total_expense,
            }

    def balance_sheet(self, book_id, actor, through_period=None):
        """Cumulative balance sheet through a period (or all periods)."""
        if through_period is not None:
            _validate_period(through_period, "through_period")
        with self._lock:
            self._require_book_access(book_id, actor, "read")
            totals = self._totals_by_account(book_id, period_le=through_period)
            sections = {"asset": [], "liability": [], "equity": []}
            section_totals = {"asset": 0, "liability": 0, "equity": 0}
            total_revenue = 0
            total_expense = 0
            for account in self._book_accounts(book_id):
                debits, credits = totals.get(account["id"], [0, 0])
                if account["type"] in sections:
                    amount = _normal_balance(account["type"], debits, credits)
                    if amount == 0:
                        continue
                    sections[account["type"]].append(
                        {
                            "account_id": account["id"],
                            "code": account["code"],
                            "name": account["name"],
                            "amount_cents": amount,
                        }
                    )
                    section_totals[account["type"]] += amount
                elif account["type"] == "revenue":
                    total_revenue += credits - debits
                elif account["type"] == "expense":
                    total_expense += debits - credits
            net_income = total_revenue - total_expense
            total_assets = section_totals["asset"]
            total_liabilities_equity = (
                section_totals["liability"] + section_totals["equity"] + net_income
            )
            return {
                "book_id": book_id,
                "through_period": through_period,
                "assets": sections["asset"],
                "total_assets_cents": total_assets,
                "liabilities": sections["liability"],
                "total_liabilities_cents": section_totals["liability"],
                "equity": sections["equity"],
                "total_equity_cents": section_totals["equity"],
                "net_income_cents": net_income,
                "total_liabilities_equity_cents": total_liabilities_equity,
                "balanced": total_assets == total_liabilities_equity,
            }

    # -- reconciliation and period close --------------------------------

    def reconcile_account(self, book_id, account_id, period, expected_balance_cents, actor):
        """Reconcile an account for a period against an expected balance."""
        _validate_period(period, "period")
        _validate_cents_any(expected_balance_cents, "expected_balance_cents")
        with self._lock:
            self._require_book_access(book_id, actor, "close")
            account = self._get_account_record(book_id, account_id)
            totals = self._totals_by_account(book_id, period_le=period)
            debits, credits = totals.get(account_id, [0, 0])
            book_balance = _normal_balance(account["type"], debits, credits)
            difference = book_balance - expected_balance_cents
            rec_id = self._next_id("rec")
            record = {
                "id": rec_id,
                "book_id": book_id,
                "account_id": account_id,
                "period": period,
                "book_balance_cents": book_balance,
                "expected_cents": expected_balance_cents,
                "difference_cents": difference,
                "matched": difference == 0,
                "created_by": actor_name(actor),
                "created_utc": _utc_now(),
            }
            self._reconciliations[rec_id] = record
            self._audit(
                actor, "reconciliation_create", rec_id, details={"account_id": account_id}
            )
            return dict(record)

    def close_period(self, book_id, period, actor):
        """Close a fiscal period, locking its ledger."""
        _validate_period(period, "period")
        with self._lock:
            book = self._require_book_access(book_id, actor, "close")
            if period in book["closed_periods"]:
                raise ValidationError("period %r is already closed" % (period,))
            book["closed_periods"].append(period)
            book["closed_periods"].sort()
            result = {
                "book_id": book_id,
                "period": period,
                "closed_by": actor_name(actor),
                "closed_utc": _utc_now(),
            }
            self._audit(actor, "period_close", book_id, details={"period": period})
            return dict(result)
