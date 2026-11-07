"""Final GAPS batch extensions, second unit — Finance L2
remainder additions (the 4 forks of build unit
``addition:finance-l2``: Apptio TBM, CGI Momentum, Coupa Spend
Management for Federal, Innovest Trust & Wealth Management).

This module closes the 6 open entries of the GAPS.md section
"Remainder Addition — Finance L2 (+4 forks)" (idx 589–594 in
``../../gaps-batch/inventory.json``): 5 built as in-substrate
records extensions over the core's own entities, 1 shipped as a
labeled reference implementation (the drafted stub-engine entry,
AI/ML document processing). See ``BATCH-ADDITION.md`` in the group
directory for the per-entry disposition. The first batch unit's
surface lives in :mod:`finance.extensions` and is untouched by
this module, as is every core module (byte-identical).

Design, following the group's doctrines (see ``UNION-SPEC.md``,
``ADDENDUM.md``, and the first unit's ``BATCH.md``):

- This module is a second wrapper around :class:`FinanceStore`.
  Core state is always read through the core store's public API,
  never re-implemented, and no operation here writes core state.
- **Records, not execution** is not repealed: nothing here runs
  an agency's financial system, sources or pays a supplier,
  optimizes cloud spend, values a holding, manages wealth, or
  processes a document. Each entry lands as the records surface
  its name reduces to — a ledger of recorded postings with
  balances derived at read, a procurement lifecycle held as
  stage records, analytics computed on read from recorded spend,
  allocation/tagging records with optimization outcomes stored
  as reported, trust account/transaction records with position
  values stored as reported — with the honesty label on the face
  of every record (``authoritative_here`` / ``vetted_here`` /
  ``approved_here`` / ``decided_here`` / ``performed_here`` /
  ``placed_here`` / ``issued_here`` / ``paid_here`` /
  ``optimized_here`` / ``savings_computed_here`` /
  ``valued_here`` / ``managed_here`` / ``converted_here`` /
  ``processed_here`` / ``recognized_here`` — all ``False``).
- **The "trading & investment execution" named absence still
  stands.** Innovest asserts wealth management, not trading
  (``ADDENDUM.md`` §5), and this module builds no order or
  execution surface for the trust entry: trust accounts hold
  transaction *records* and custodian-reported position values,
  nothing is bought, sold, priced, or settled here.
- **Money is integer cents, everywhere.** Every ``*_cents``
  field is validated exactly as the core validates: a Python
  ``int``, booleans and floats rejected at the boundary, and a
  rejected operation consumes no id and stores nothing.
- **Derived values are derived at read and never stored**:
  ledger balances and the trial balance, procurement rollups,
  the spend-analytics view, FinOps totals, trust balances. The
  ledger balance derivation lives in the module-level seam
  :func:`_account_totals` — this unit's fresh negative-control
  target.
- RBAC goes through :mod:`finance.access` exactly as the core
  and the first unit enforce it (creates onto ``enter``, outcome
  reports onto ``record``, reads onto ``read``), checked before
  any state change or id allocation, with denied attempts
  recorded on the core audit log as ``exta_<action>:denied`` and
  successes as ``exta_<action>`` (the ``exta_`` prefix keeps this
  unit's actions distinct from the first unit's ``ext_`` actions
  on the shared log). Program membership is enforced through the
  core store's own access-checked program read. If an audit
  write fails, the record insertion and its id roll back before
  the error propagates.
- People are known only by the core's opaque-reference
  participants, and suppliers only by caller-supplied opaque
  references. **No record shape in this module has a field that
  could hold a real account identifier** (no account-number,
  routing, IBAN, sort-code, or card-number field) and none
  carries a credit score field; both absences are pinned by
  exact key-set tests and recursive key scans in
  ``tests/test_gaps_batch_addition.py``.
- The stub-engine family ships as a labeled reference
  implementation: every record it creates carries
  ``reference_stub: True`` and ``content_held: False`` — a
  document is named by an opaque reference only, and no
  document content ever enters a record.
"""

import copy
import re
import threading
from datetime import datetime, timezone

from .access import require
from .audit import actor_name
from .errors import NotFoundError, PermissionDenied, ValidationError

PROCUREMENT_STAGES = (
    "supplier_identification",
    "sourcing",
    "contracting",
    "ordering",
    "invoicing",
    "supplier_payment",
)
TRUST_TRANSACTION_KINDS = (
    "contribution",
    "distribution",
    "fee",
    "income",
    "adjustment",
)
KNOWN_TRUST_TRANSACTION_KINDS = frozenset(TRUST_TRANSACTION_KINDS)
# Recorded-arithmetic sign convention for trust transactions:
# contributions, income, and adjustments add to the recorded
# balance; distributions and fees subtract. Amounts themselves
# are always positive integer cents.
TRUST_CREDIT_KINDS = frozenset(("distribution", "fee"))
DOCUMENT_JOB_KINDS = (
    "document_processing",
    "image_recognition",
)
KNOWN_DOCUMENT_JOB_KINDS = frozenset(DOCUMENT_JOB_KINDS)

_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _non_empty(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % (what,))
    return value


def _string_or_none(value, what):
    if value is not None and not isinstance(value, str):
        raise ValidationError("%s must be a string" % (what,))
    return value


def _require_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("%s must be an integer (cents)" % (what,))
    return value


def _cents_positive(value, what):
    _require_int(value, what)
    if value <= 0:
        raise ValidationError("%s must be positive" % (what,))
    return value


def _cents_nonnegative(value, what):
    _require_int(value, what)
    if value < 0:
        raise ValidationError("%s must not be negative" % (what,))
    return value


def _validate_period(value, what="period"):
    if not isinstance(value, str) or not _PERIOD_RE.match(value):
        raise ValidationError(
            "%s must be a period (YYYY-MM): %r" % (what, value))
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValidationError(
            "%s is not a valid period: %r" % (what, value)) from exc
    return value


def _one_of(value, known, names, what):
    if value not in known:
        raise ValidationError(
            "%s must be one of %s" % (what, ", ".join(names)))
    return value


def _account_totals(journal_entries, account_id):
    """Ledger totals for one account over recorded journal entries.

    Returns ``(debit_total_cents, credit_total_cents)``: the sum
    of amounts of entries where the account is the debit side,
    and the sum where it is the credit side. An account's recorded
    balance, derived at read, is debits minus credits. This is
    the negative control's target: a derivation that nets the
    credit side the wrong way silently corrupts every balance
    while leaving every stored record's shape intact.
    """
    debit_total = 0
    credit_total = 0
    for entry in journal_entries:
        if entry["debit_account_id"] == account_id:
            debit_total += entry["amount_cents"]
        if entry["credit_account_id"] == account_id:
            credit_total += entry["amount_cents"]
    return debit_total, credit_total


class FinanceExtensionsAddition:
    """Second GAPS-batch extension surface over a core FinanceStore."""

    def __init__(self, store):
        self.store = store
        self._records = {}  # (kind, id) -> dict
        self._order = []  # (kind, id) in creation order
        self._counters = {}
        self._lock = threading.RLock()

    # -- internal helpers ---------------------------------------------

    def _audit(self, actor, action, target, details=None):
        audit = getattr(self.store, "audit", None)
        if audit is not None:
            audit.record(actor_name(actor), action, target, details=details)

    def _guard(self, actor, core_action, audit_action, target=None):
        """Enforce a permission, auditing a denial (core convention)."""
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

    def _program(self, program_id, actor):
        """Core access-checked program read (membership + read role)."""
        return self.store.get_program(program_id, actor)

    def _create(self, kind, prefix, fields, actor, audit_action):
        with self._lock:
            self._counters[prefix] = self._counters.get(prefix, 0) + 1
            record_id = "%s-%d" % (prefix, self._counters[prefix])
            record = {"id": record_id}
            record.update(fields)
            record["created_by"] = actor_name(actor)
            record["created_utc"] = _utc_now()
            self._records[(kind, record_id)] = record
            self._order.append((kind, record_id))
            try:
                self._audit(actor, audit_action, record_id,
                            details={"kind": kind})
            except Exception:
                # Fail closed: an operation whose audit write fails
                # does not proceed -- the insertion and the id roll
                # back before the error propagates.
                del self._records[(kind, record_id)]
                self._order.pop()
                self._counters[prefix] -= 1
                raise
            return copy.deepcopy(record)

    def _get(self, kind, record_id, program_id):
        record = self._records.get((kind, record_id))
        if record is None or record["program_id"] != program_id:
            raise NotFoundError("%s not found: %r" % (kind, record_id))
        return record

    def _fetch(self, kind, record_id, program_id):
        return copy.deepcopy(self._get(kind, record_id, program_id))

    def _list(self, kind, program_id, **filters):
        result = []
        for key in self._order:
            if key[0] != kind:
                continue
            record = self._records[key]
            if record["program_id"] != program_id:
                continue
            if all(record.get(f) == v for f, v in filters.items()):
                result.append(copy.deepcopy(record))
        return result

    def _participant(self, program_id, participant_id, actor):
        """Return the core participant (NotFoundError if absent)."""
        return self.store.get_participant(program_id, participant_id, actor)

    def _ref_taken(self, kind, program_id, field, value):
        for record in self._list(kind, program_id):
            if record[field] == value:
                return True
        return False

    # -- Federal financial management system of record (Momentum) ------
    #
    # The general-ledger system carrying the financial, budget,
    # asset, and procurement lifecycles end to end. What lands
    # here is the records surface that name reduces to: a chart of
    # ledger accounts (opaque references plus titles, held as
    # data) and journal entry records (a debit side, a credit
    # side, an integer-cent amount, a period, a memo label), with
    # account balances and the trial balance derived at read by
    # recorded arithmetic over those entries. The agency's
    # authoritative system of record is the external ERP;
    # ``authoritative_here`` is False on every record, no
    # lifecycle is executed, and no entry moves money — a journal
    # record states that a posting was recorded, on the books
    # kept elsewhere.

    def register_ledger_account(self, program_id, account_ref, title, actor):
        """Register a ledger account record in a program.

        ``account_ref`` is the caller's own opaque chart-of-
        accounts label, held as data; it must be unique within
        the program, because the ref is the ledger's own key.
        """
        self._guard(actor, "enter", "exta_ledger_account_register")
        self._program(program_id, actor)
        _non_empty(account_ref, "account_ref")
        _non_empty(title, "title")
        if self._ref_taken(
                "ledger_account", program_id, "account_ref", account_ref):
            raise ValidationError(
                "ledger account_ref %r is already registered in "
                "program %r" % (account_ref, program_id))
        return self._create(
            "ledger_account", "glac",
            {"program_id": program_id, "account_ref": account_ref,
             "title": title, "authoritative_here": False,
             "state": "registered_record_only"},
            actor, "exta_ledger_account_register")

    def record_journal_entry(
        self, program_id, period, debit_account_id, credit_account_id,
        amount_cents, memo_label, actor
    ):
        """Record a journal entry against two ledger accounts.

        Both accounts must be registered ledger accounts of this
        program and must differ (a posting from an account to
        itself records nothing). The amount is positive integer
        cents. The entry is a record of a posting; balances are
        derived from entries at read, never stored.
        """
        self._guard(actor, "enter", "exta_journal_entry_record",
                    target=debit_account_id)
        self._program(program_id, actor)
        _validate_period(period, "period")
        _cents_positive(amount_cents, "amount_cents")
        _non_empty(memo_label, "memo_label")
        if debit_account_id == credit_account_id:
            raise ValidationError(
                "a journal entry's debit and credit accounts must differ")
        self._get("ledger_account", debit_account_id, program_id)
        self._get("ledger_account", credit_account_id, program_id)
        return self._create(
            "journal_entry", "jrnl",
            {"program_id": program_id, "period": period,
             "debit_account_id": debit_account_id,
             "credit_account_id": credit_account_id,
             "amount_cents": amount_cents, "memo_label": memo_label,
             "authoritative_here": False},
            actor, "exta_journal_entry_record")

    def get_ledger_account(self, program_id, account_id, actor):
        self._guard(actor, "read", "exta_ledger_account_get",
                    target=account_id)
        self._program(program_id, actor)
        return self._fetch("ledger_account", account_id, program_id)

    def list_ledger_accounts(self, program_id, actor):
        self._guard(actor, "read", "exta_ledger_account_list")
        self._program(program_id, actor)
        return self._list("ledger_account", program_id)

    def list_journal_entries(self, program_id, actor, account_id=None):
        self._guard(actor, "read", "exta_journal_entry_list")
        self._program(program_id, actor)
        entries = self._list("journal_entry", program_id)
        if account_id is not None:
            entries = [
                e for e in entries
                if e["debit_account_id"] == account_id
                or e["credit_account_id"] == account_id
            ]
        return entries

    def ledger_account_view(self, program_id, account_id, actor):
        """One ledger account plus its derived totals.

        Debit/credit totals and the balance (debits minus
        credits) are derived at read from the program's journal
        entries via :func:`_account_totals`; the stored account
        record carries none of them.
        """
        self._guard(actor, "read", "exta_ledger_account_view",
                    target=account_id)
        self._program(program_id, actor)
        account = self._fetch("ledger_account", account_id, program_id)
        entries = self._list("journal_entry", program_id)
        debits, credits = _account_totals(entries, account_id)
        view = dict(account)
        view.update({
            "debit_total_cents": debits,
            "credit_total_cents": credits,
            "balance_cents": debits - credits,
            "journal_entries": sum(
                1 for e in entries
                if e["debit_account_id"] == account_id
                or e["credit_account_id"] == account_id),
            "derived": True,
            "method": "sums_over_journal_entry_records",
        })
        return view

    def trial_balance(self, program_id, actor, period=None):
        """Derived at read: per-account totals over journal entries.

        Every recorded entry contributes its amount once as a
        debit and once as a credit, so the totals agree and
        ``balanced`` is True by construction — the view states
        the recorded arithmetic, it does not assert the books
        are right. With ``period``, only that period's entries
        count.
        """
        self._guard(actor, "read", "exta_trial_balance")
        self._program(program_id, actor)
        if period is not None:
            _validate_period(period, "period")
        entries = self._list("journal_entry", program_id)
        if period is not None:
            entries = [e for e in entries if e["period"] == period]
        accounts = []
        total_debits = 0
        total_credits = 0
        for account in self._list("ledger_account", program_id):
            debits, credits = _account_totals(entries, account["id"])
            total_debits += debits
            total_credits += credits
            accounts.append({
                "account_id": account["id"],
                "account_ref": account["account_ref"],
                "debit_total_cents": debits,
                "credit_total_cents": credits,
                "balance_cents": debits - credits,
            })
        return {
            "program_id": program_id,
            "period": period,
            "accounts": accounts,
            "total_debits_cents": total_debits,
            "total_credits_cents": total_credits,
            "balanced": total_debits == total_credits,
            "authoritative_here": False,
            "derived": True,
            "method": "sums_over_journal_entry_records",
        }

    # -- Procurement lifecycle engine (Coupa) ---------------------------
    #
    # Supplier identification, sourcing, contracting, procurement
    # against contracts, invoicing, and supplier payment
    # execution. The lifecycle lands as one record kind per stage
    # over this substrate: supplier registrations (opaque refs;
    # identification and vetting happen elsewhere), requisition
    # records with the decider's label stored verbatim as
    # reported, contract records with a recorded ceiling that
    # bounds the orders recorded against them, purchase order
    # records, invoice records, and supplier payment reports.
    # Supplier payments are recorded in THIS family, deliberately
    # not in the earned-wage disbursement family (a different
    # flow: supplier disbursement against invoices, not access
    # to earned wages — ADDENDUM.md §5). Nothing is sourced,
    # awarded, ordered, issued, or paid here; every stage carries
    # its ``*_here: False`` label.

    def register_supplier(self, program_id, supplier_ref, name_label, actor):
        """Register a supplier record (identification stage).

        ``supplier_ref`` is an opaque caller reference, unique
        within the program; ``name_label`` is the caller's own
        label for the supplier, held as data. No field can hold
        a bank account identifier, so a supplier's payment
        details cannot enter this substrate.
        """
        self._guard(actor, "enter", "exta_supplier_register")
        self._program(program_id, actor)
        _non_empty(supplier_ref, "supplier_ref")
        _non_empty(name_label, "name_label")
        if self._ref_taken("supplier", program_id, "supplier_ref",
                           supplier_ref):
            raise ValidationError(
                "supplier_ref %r is already registered in program %r"
                % (supplier_ref, program_id))
        return self._create(
            "supplier", "supp",
            {"program_id": program_id, "supplier_ref": supplier_ref,
             "name_label": name_label, "vetted_here": False,
             "state": "registered_record_only"},
            actor, "exta_supplier_register")

    def create_requisition(
        self, program_id, supplier_id, description_label, amount_cents,
        actor
    ):
        """Record a sourcing requisition against a supplier.

        The amount is integer-cents data about the requisition;
        nothing is approved or sourced here.
        """
        self._guard(actor, "enter", "exta_requisition_create",
                    target=supplier_id)
        self._program(program_id, actor)
        _non_empty(description_label, "description_label")
        _cents_positive(amount_cents, "amount_cents")
        self._get("supplier", supplier_id, program_id)
        return self._create(
            "requisition", "reqn",
            {"program_id": program_id, "supplier_id": supplier_id,
             "description_label": description_label,
             "amount_cents": amount_cents, "approved_here": False,
             "state": "recorded_requisition_only"},
            actor, "exta_requisition_create")

    def record_requisition_decision(
        self, program_id, requisition_id, decision_label, actor, detail=None
    ):
        """Record a requisition decision, verbatim.

        ``decision_label`` is the deciding party's own label,
        stored as reported; this build decided nothing
        (``decided_here: False``) and the requisition record is
        left byte-identical.
        """
        self._guard(actor, "record", "exta_requisition_decision",
                    target=requisition_id)
        self._program(program_id, actor)
        _non_empty(decision_label, "decision_label")
        _string_or_none(detail, "detail")
        requisition = self._get("requisition", requisition_id, program_id)
        return self._create(
            "requisition_decision", "rdec",
            {"program_id": program_id, "requisition_id": requisition_id,
             "supplier_id": requisition["supplier_id"],
             "decision_label": decision_label, "detail": detail,
             "decided_here": False},
            actor, "exta_requisition_decision")

    def create_contract_record(
        self, program_id, supplier_id, contract_ref, ceiling_cents, actor
    ):
        """Record a contract with a supplier (contracting stage).

        ``contract_ref`` is the caller's opaque label for the
        contract, held as data; ``ceiling_cents`` is the recorded
        ceiling that bounds the purchase orders recorded against
        this contract. The contract itself was awarded and
        executed by the parties elsewhere (``performed_here:
        False``).
        """
        self._guard(actor, "enter", "exta_contract_create",
                    target=supplier_id)
        self._program(program_id, actor)
        _non_empty(contract_ref, "contract_ref")
        _cents_nonnegative(ceiling_cents, "ceiling_cents")
        self._get("supplier", supplier_id, program_id)
        return self._create(
            "contract", "cntr",
            {"program_id": program_id, "supplier_id": supplier_id,
             "contract_ref": contract_ref, "ceiling_cents": ceiling_cents,
             "performed_here": False, "state": "recorded_contract_only"},
            actor, "exta_contract_create")

    def _contract_committed_cents(self, contract_id):
        """Total of purchase-order amounts recorded against a contract."""
        return sum(
            o["amount_cents"]
            for o in self._records.values()
            if o.get("contract_id") == contract_id
            and o["id"].startswith("pord-"))

    def create_purchase_order(
        self, program_id, contract_id, period, amount_cents, actor
    ):
        """Record a purchase order against a contract.

        Procurement against contracts is bounded by the
        contract's recorded ceiling: the order's amount plus the
        amounts of orders already recorded against the contract
        may not exceed ``ceiling_cents`` — else the order is
        rejected whole and nothing is stored. The order itself
        was placed on the supplier's systems elsewhere
        (``placed_here: False``).
        """
        self._guard(actor, "enter", "exta_purchase_order_create",
                    target=contract_id)
        self._program(program_id, actor)
        _validate_period(period, "period")
        _cents_positive(amount_cents, "amount_cents")
        contract = self._get("contract", contract_id, program_id)
        committed = self._contract_committed_cents(contract_id)
        if committed + amount_cents > contract["ceiling_cents"]:
            raise ValidationError(
                "purchase order exceeds the contract's recorded "
                "ceiling: ceiling %d, committed %d, ordered %d"
                % (contract["ceiling_cents"], committed, amount_cents))
        return self._create(
            "purchase_order", "pord",
            {"program_id": program_id, "contract_id": contract_id,
             "supplier_id": contract["supplier_id"], "period": period,
             "amount_cents": amount_cents, "placed_here": False,
             "state": "recorded_order_only"},
            actor, "exta_purchase_order_create")

    def record_invoice(self, program_id, order_id, amount_cents, actor):
        """Record a supplier invoice against a purchase order.

        The invoice record copies the order's contract, supplier,
        and period. The invoice was issued by the supplier
        elsewhere (``issued_here: False``); recording it pays
        nothing.
        """
        self._guard(actor, "enter", "exta_invoice_record", target=order_id)
        self._program(program_id, actor)
        _cents_nonnegative(amount_cents, "amount_cents")
        order = self._get("purchase_order", order_id, program_id)
        return self._create(
            "invoice", "invc",
            {"program_id": program_id, "order_id": order_id,
             "contract_id": order["contract_id"],
             "supplier_id": order["supplier_id"],
             "period": order["period"], "amount_cents": amount_cents,
             "issued_here": False, "paid_here": False,
             "state": "recorded_invoice_only"},
            actor, "exta_invoice_record")

    def record_supplier_payment_report(
        self, program_id, invoice_id, outcome_label, actor, detail=None
    ):
        """Record a supplier payment outcome, verbatim.

        Supplier payment execution is recorded in this family —
        deliberately NOT in the earned-wage disbursement family
        (ADDENDUM.md §5). ``outcome_label`` is the paying
        system's own label, stored as reported; this build paid
        nothing (``paid_here: False``) and the invoice record is
        left byte-identical.
        """
        self._guard(actor, "record", "exta_supplier_payment_report",
                    target=invoice_id)
        self._program(program_id, actor)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(detail, "detail")
        invoice = self._get("invoice", invoice_id, program_id)
        return self._create(
            "supplier_payment_report", "spay",
            {"program_id": program_id, "invoice_id": invoice_id,
             "order_id": invoice["order_id"],
             "supplier_id": invoice["supplier_id"],
             "outcome_label": outcome_label, "detail": detail,
             "paid_here": False},
            actor, "exta_supplier_payment_report")

    def get_supplier(self, program_id, supplier_id, actor):
        self._guard(actor, "read", "exta_supplier_get", target=supplier_id)
        self._program(program_id, actor)
        return self._fetch("supplier", supplier_id, program_id)

    def list_suppliers(self, program_id, actor):
        self._guard(actor, "read", "exta_supplier_list")
        self._program(program_id, actor)
        return self._list("supplier", program_id)

    def list_requisitions(self, program_id, actor, supplier_id=None):
        self._guard(actor, "read", "exta_requisition_list")
        self._program(program_id, actor)
        filters = {}
        if supplier_id is not None:
            filters["supplier_id"] = supplier_id
        return self._list("requisition", program_id, **filters)

    def list_requisition_decisions(
        self, program_id, actor, requisition_id=None
    ):
        self._guard(actor, "read", "exta_requisition_decision_list")
        self._program(program_id, actor)
        filters = {}
        if requisition_id is not None:
            filters["requisition_id"] = requisition_id
        return self._list("requisition_decision", program_id, **filters)

    def list_contracts(self, program_id, actor, supplier_id=None):
        self._guard(actor, "read", "exta_contract_list")
        self._program(program_id, actor)
        filters = {}
        if supplier_id is not None:
            filters["supplier_id"] = supplier_id
        return self._list("contract", program_id, **filters)

    def list_purchase_orders(self, program_id, actor, contract_id=None):
        self._guard(actor, "read", "exta_purchase_order_list")
        self._program(program_id, actor)
        filters = {}
        if contract_id is not None:
            filters["contract_id"] = contract_id
        return self._list("purchase_order", program_id, **filters)

    def list_invoices(self, program_id, actor, order_id=None):
        self._guard(actor, "read", "exta_invoice_list")
        self._program(program_id, actor)
        filters = {}
        if order_id is not None:
            filters["order_id"] = order_id
        return self._list("invoice", program_id, **filters)

    def list_supplier_payment_reports(
        self, program_id, actor, invoice_id=None
    ):
        self._guard(actor, "read", "exta_supplier_payment_report_list")
        self._program(program_id, actor)
        filters = {}
        if invoice_id is not None:
            filters["invoice_id"] = invoice_id
        return self._list("supplier_payment_report", program_id, **filters)

    def procurement_summary(self, program_id, actor):
        """Derived at read: counts and recorded-cent totals over
        this surface's procurement records, by lifecycle stage.
        Nothing is stored."""
        self._guard(actor, "read", "exta_procurement_summary")
        self._program(program_id, actor)
        suppliers = self._list("supplier", program_id)
        requisitions = self._list("requisition", program_id)
        contracts = self._list("contract", program_id)
        orders = self._list("purchase_order", program_id)
        invoices = self._list("invoice", program_id)
        payments = self._list("supplier_payment_report", program_id)
        return {
            "program_id": program_id,
            "suppliers": len(suppliers),
            "requisitions": len(requisitions),
            "requisition_total_cents": sum(
                r["amount_cents"] for r in requisitions),
            "contracts": len(contracts),
            "contract_ceiling_total_cents": sum(
                c["ceiling_cents"] for c in contracts),
            "orders": len(orders),
            "order_total_cents": sum(
                o["amount_cents"] for o in orders),
            "invoices": len(invoices),
            "invoice_total_cents": sum(
                i["amount_cents"] for i in invoices),
            "payment_reports": len(payments),
            "paid_here": False,
            "derived": True,
            "method": "counts_and_sums_over_procurement_records",
        }

    # -- Spend analytics engine (Coupa) ---------------------------------
    #
    # Analytics over spend data. The honest records form of an
    # analytics engine in this substrate is a view computed on
    # read from recorded spend — the same posture as Core 7
    # reporting and Core 5 spend-vs-budget: counts and
    # integer-cent sums over the substrate's own spend records
    # (core bookings and disbursements, plus this unit's purchase
    # orders and invoices), attributed to a period exactly as the
    # core attributes them (bookings by start month, disbursements
    # by disbursement month, orders and invoices by their recorded
    # period). No rate, trend, forecast, or average is computed:
    # the view's shape is pinned to counts and cent totals, and
    # the categories are distinct record families — invoice
    # amounts restate order amounts at a later lifecycle stage,
    # so the view deliberately carries no grand total that would
    # double-count them.

    def spend_analytics(self, program_id, period, actor):
        """Derived at read: recorded spend for one period, by family."""
        self._guard(actor, "read", "exta_spend_analytics")
        self._program(program_id, actor)
        _validate_period(period, "period")
        bookings = {"air": {"count": 0, "total_cents": 0},
                    "hotel": {"count": 0, "total_cents": 0}}
        for booking in self.store.list_bookings(program_id, actor):
            if booking["status"] == "cancelled":
                continue
            if not booking["start_date"].startswith(period):
                continue
            cell = bookings[booking["kind"]]
            cell["count"] += 1
            cell["total_cents"] += booking["amount_cents"]
        disbursed_cents = 0
        disbursement_count = 0
        for disbursement in self.store.list_disbursements(program_id, actor):
            if disbursement["date"].startswith(period):
                disbursement_count += 1
                disbursed_cents += disbursement["amount_cents"]
        orders = [o for o in self._list("purchase_order", program_id)
                  if o["period"] == period]
        invoices = [i for i in self._list("invoice", program_id)
                    if i["period"] == period]
        return {
            "program_id": program_id,
            "period": period,
            "bookings": bookings,
            "earned_wage_disbursements": disbursement_count,
            "earned_wage_disbursed_cents": disbursed_cents,
            "procurement_orders": len(orders),
            "procurement_order_total_cents": sum(
                o["amount_cents"] for o in orders),
            "procurement_invoices": len(invoices),
            "procurement_invoice_total_cents": sum(
                i["amount_cents"] for i in invoices),
            "derived": True,
            "method": "counts_and_sums_over_recorded_spend_records",
        }

    # -- Technology business management & FinOps engine (Apptio) --------
    #
    # Cost allocation and chargeback ("allocate cloud costs back
    # to the agency", "price and recover shared services"), cloud
    # cost optimization across providers, FinOps enablement. What
    # lands is allocation records (a source label, a target label,
    # a period, an integer-cent amount as recorded), tag records
    # bound to allocations, and optimization reports whose
    # outcomes — including any savings figure — are stored
    # verbatim as reported by the FinOps engine that actually
    # ran. Totals in the summary are sums of recorded amounts,
    # stated as such; no cost is optimized here and no savings
    # figure is computed here (``optimized_here`` /
    # ``savings_computed_here`` False throughout).

    def record_cost_allocation(
        self, program_id, period, source_label, target_label,
        amount_cents, actor
    ):
        """Record a cost allocation from a source to a target.

        ``source_label`` names the cost source (a provider or
        shared service) and ``target_label`` the agency or unit
        the cost is allocated back to — both caller labels held
        as data. The amount is the recorded allocation in
        integer cents.
        """
        self._guard(actor, "enter", "exta_cost_allocation_record")
        self._program(program_id, actor)
        _validate_period(period, "period")
        _non_empty(source_label, "source_label")
        _non_empty(target_label, "target_label")
        _cents_nonnegative(amount_cents, "amount_cents")
        return self._create(
            "cost_allocation", "allo",
            {"program_id": program_id, "period": period,
             "source_label": source_label, "target_label": target_label,
             "amount_cents": amount_cents, "optimized_here": False,
             "state": "recorded_allocation_only"},
            actor, "exta_cost_allocation_record")

    def tag_cost_allocation(self, program_id, allocation_id, tag_label, actor):
        """Record a tag on a cost allocation (tagging records)."""
        self._guard(actor, "enter", "exta_cost_tag_record",
                    target=allocation_id)
        self._program(program_id, actor)
        _non_empty(tag_label, "tag_label")
        self._get("cost_allocation", allocation_id, program_id)
        return self._create(
            "cost_tag", "ctag",
            {"program_id": program_id, "allocation_id": allocation_id,
             "tag_label": tag_label, "optimized_here": False},
            actor, "exta_cost_tag_record")

    def record_optimization_report(
        self, program_id, period, outcome_label, actor,
        reported_savings_cents=None, detail=None
    ):
        """Record a FinOps engine's reported optimization outcome.

        The outcome label — and any savings figure — is stored
        verbatim as reported by the external engine; nothing was
        optimized here and no savings were computed here.
        """
        self._guard(actor, "record", "exta_optimization_report",
                    target=period)
        self._program(program_id, actor)
        _validate_period(period, "period")
        _non_empty(outcome_label, "outcome_label")
        if reported_savings_cents is not None:
            _cents_nonnegative(
                reported_savings_cents, "reported_savings_cents")
        _string_or_none(detail, "detail")
        return self._create(
            "optimization_report", "fopt",
            {"program_id": program_id, "period": period,
             "outcome_label": outcome_label,
             "reported_savings_cents": reported_savings_cents,
             "detail": detail, "optimized_here": False,
             "savings_computed_here": False},
            actor, "exta_optimization_report")

    def list_cost_allocations(
        self, program_id, actor, period=None, target_label=None
    ):
        self._guard(actor, "read", "exta_cost_allocation_list")
        self._program(program_id, actor)
        filters = {}
        if period is not None:
            filters["period"] = period
        if target_label is not None:
            filters["target_label"] = target_label
        return self._list("cost_allocation", program_id, **filters)

    def list_cost_tags(self, program_id, actor, allocation_id=None):
        self._guard(actor, "read", "exta_cost_tag_list")
        self._program(program_id, actor)
        filters = {}
        if allocation_id is not None:
            filters["allocation_id"] = allocation_id
        return self._list("cost_tag", program_id, **filters)

    def list_optimization_reports(self, program_id, actor, period=None):
        self._guard(actor, "read", "exta_optimization_report_list")
        self._program(program_id, actor)
        filters = {}
        if period is not None:
            filters["period"] = period
        return self._list("optimization_report", program_id, **filters)

    def finops_summary(self, program_id, actor, period=None):
        """Derived at read: allocation counts and recorded-cent
        totals (overall and by target label), tag counts, and
        optimization report counts with savings totals *as
        reported*. Nothing is stored and nothing is optimized."""
        self._guard(actor, "read", "exta_finops_summary")
        self._program(program_id, actor)
        if period is not None:
            _validate_period(period, "period")
        allocations = self._list("cost_allocation", program_id)
        reports = self._list("optimization_report", program_id)
        if period is not None:
            allocations = [a for a in allocations if a["period"] == period]
            reports = [r for r in reports if r["period"] == period]
        by_target = {}
        for allocation in allocations:
            cell = by_target.setdefault(
                allocation["target_label"], {"count": 0, "total_cents": 0})
            cell["count"] += 1
            cell["total_cents"] += allocation["amount_cents"]
        return {
            "program_id": program_id,
            "period": period,
            "allocations": len(allocations),
            "allocated_total_cents": sum(
                a["amount_cents"] for a in allocations),
            "allocations_by_target": by_target,
            "tags": len(self._list("cost_tag", program_id)),
            "optimization_reports": len(reports),
            "reported_savings_total_cents": sum(
                r["reported_savings_cents"] or 0 for r in reports),
            "optimized_here": False,
            "savings_computed_here": False,
            "derived": True,
            "method": "counts_and_sums_over_finops_records",
        }

    # -- Trust accounting & wealth management platform (Innovest) -------
    #
    # A multi-currency trust accounting system of record and
    # wealth management tooling. What lands is trust account
    # records bound to core participants (known only by their
    # opaque references), transaction records whose amounts are
    # integer cents in the account's own currency, and position
    # reports whose values are stored verbatim as reported by the
    # custodian. Balances derive at read by the recorded
    # arithmetic stated on the transaction kinds; holdings are
    # never valued here (``valued_here: False``), currencies are
    # labels held as data and never converted
    # (``converted_here: False`` — and the summary sums nothing
    # across currencies), and no wealth is managed here
    # (``managed_here: False``). The union's "trading &
    # investment execution" named absence still stands: this
    # surface has no order or execution operation at all.

    def open_trust_account(
        self, program_id, participant_id, account_ref, currency_label, actor
    ):
        """Record a trust account for a core participant.

        ``account_ref`` is the caller's opaque label for the
        account, unique within the program — no field can hold
        an account number. ``currency_label`` names the
        account's currency as data (multi-currency platform);
        no conversion is ever computed.
        """
        self._guard(actor, "enter", "exta_trust_account_open",
                    target=participant_id)
        self._program(program_id, actor)
        _non_empty(account_ref, "account_ref")
        _non_empty(currency_label, "currency_label")
        self._participant(program_id, participant_id, actor)
        if self._ref_taken(
                "trust_account", program_id, "account_ref", account_ref):
            raise ValidationError(
                "trust account_ref %r is already registered in "
                "program %r" % (account_ref, program_id))
        return self._create(
            "trust_account", "tacc",
            {"program_id": program_id, "participant_id": participant_id,
             "account_ref": account_ref, "currency_label": currency_label,
             "valued_here": False, "managed_here": False,
             "converted_here": False, "state": "recorded_account_only"},
            actor, "exta_trust_account_open")

    def record_trust_transaction(
        self, program_id, account_id, period, kind, amount_cents, actor
    ):
        """Record a trust transaction against an account.

        ``kind`` is one of contribution / distribution / fee /
        income / adjustment; the amount is positive integer
        cents in the account's currency. The transaction is a
        record — contributions, distributions, and fees are
        executed by the custodian elsewhere.
        """
        self._guard(actor, "enter", "exta_trust_transaction_record",
                    target=account_id)
        self._program(program_id, actor)
        _validate_period(period, "period")
        _one_of(kind, KNOWN_TRUST_TRANSACTION_KINDS,
                TRUST_TRANSACTION_KINDS, "kind")
        _cents_positive(amount_cents, "amount_cents")
        account = self._get("trust_account", account_id, program_id)
        return self._create(
            "trust_transaction", "ttxn",
            {"program_id": program_id, "account_id": account_id,
             "participant_id": account["participant_id"],
             "period": period, "kind": kind,
             "amount_cents": amount_cents, "valued_here": False},
            actor, "exta_trust_transaction_record")

    def record_position_report(
        self, program_id, account_id, instrument_ref, reported_value_cents,
        actor, detail=None
    ):
        """Record a custodian's reported position value, verbatim.

        ``instrument_ref`` is an opaque caller label for the
        holding; ``reported_value_cents`` is the value the
        custodian reported, stored as reported — this build
        values nothing (``valued_here: False``).
        """
        self._guard(actor, "record", "exta_position_report",
                    target=account_id)
        self._program(program_id, actor)
        _non_empty(instrument_ref, "instrument_ref")
        _cents_nonnegative(reported_value_cents, "reported_value_cents")
        _string_or_none(detail, "detail")
        self._get("trust_account", account_id, program_id)
        return self._create(
            "position_report", "tpos",
            {"program_id": program_id, "account_id": account_id,
             "instrument_ref": instrument_ref,
             "reported_value_cents": reported_value_cents,
             "detail": detail, "valued_here": False},
            actor, "exta_position_report")

    def get_trust_account(self, program_id, account_id, actor):
        self._guard(actor, "read", "exta_trust_account_get",
                    target=account_id)
        self._program(program_id, actor)
        return self._fetch("trust_account", account_id, program_id)

    def list_trust_accounts(self, program_id, actor, participant_id=None):
        self._guard(actor, "read", "exta_trust_account_list")
        self._program(program_id, actor)
        filters = {}
        if participant_id is not None:
            filters["participant_id"] = participant_id
        return self._list("trust_account", program_id, **filters)

    def list_trust_transactions(self, program_id, actor, account_id=None):
        self._guard(actor, "read", "exta_trust_transaction_list")
        self._program(program_id, actor)
        filters = {}
        if account_id is not None:
            filters["account_id"] = account_id
        return self._list("trust_transaction", program_id, **filters)

    def list_position_reports(self, program_id, actor, account_id=None):
        self._guard(actor, "read", "exta_position_report_list")
        self._program(program_id, actor)
        filters = {}
        if account_id is not None:
            filters["account_id"] = account_id
        return self._list("position_report", program_id, **filters)

    def trust_account_view(self, program_id, account_id, actor):
        """One trust account plus derived totals, in its currency.

        Transaction totals by kind and the recorded balance
        (contributions + income + adjustments − distributions −
        fees) are derived at read from the account's transaction
        records; position values are summed *as reported*.
        The stored account record carries no balance.
        """
        self._guard(actor, "read", "exta_trust_account_view",
                    target=account_id)
        self._program(program_id, actor)
        account = self._fetch("trust_account", account_id, program_id)
        transactions = self._list(
            "trust_transaction", program_id, account_id=account_id)
        positions = self._list(
            "position_report", program_id, account_id=account_id)
        by_kind = {k: {"count": 0, "total_cents": 0}
                   for k in TRUST_TRANSACTION_KINDS}
        balance = 0
        for txn in transactions:
            cell = by_kind[txn["kind"]]
            cell["count"] += 1
            cell["total_cents"] += txn["amount_cents"]
            if txn["kind"] in TRUST_CREDIT_KINDS:
                balance -= txn["amount_cents"]
            else:
                balance += txn["amount_cents"]
        view = dict(account)
        view.update({
            "transactions_by_kind": by_kind,
            "balance_cents": balance,
            "position_reports": len(positions),
            "reported_position_total_cents": sum(
                p["reported_value_cents"] for p in positions),
            "derived": True,
            "method": "sums_over_trust_transaction_records",
        })
        return view

    def trust_summary(self, program_id, actor):
        """Derived at read: trust counts. Balances are per-account
        in their own currencies, so this summary sums no money
        across accounts — counts only, plus the currency census."""
        self._guard(actor, "read", "exta_trust_summary")
        self._program(program_id, actor)
        accounts = self._list("trust_account", program_id)
        by_currency = {}
        for account in accounts:
            by_currency[account["currency_label"]] = (
                by_currency.get(account["currency_label"], 0) + 1)
        return {
            "program_id": program_id,
            "accounts": len(accounts),
            "accounts_by_currency": by_currency,
            "transactions": len(self._list("trust_transaction", program_id)),
            "position_reports": len(
                self._list("position_report", program_id)),
            "valued_here": False,
            "converted_here": False,
            "derived": True,
            "method": "counts_over_trust_records",
        }

    # -- AI / ML document processing & image recognition (Coupa; stub) --
    #
    # Labeled reference implementation. Document processing and
    # image recognition are engines over document content, and
    # this substrate holds no document content: a job record
    # names a document by an opaque caller reference and a kind,
    # and a report record stores the processing system's outcome
    # label verbatim. Every record carries ``reference_stub:
    # True``, ``processed_here: False``, ``recognized_here:
    # False``, and ``content_held: False``; no record shape has
    # a field that could hold document content or an image.

    def record_document_processing_job(
        self, program_id, document_ref, job_kind, actor
    ):
        """Record a document-processing job reference (stub).

        ``document_ref`` is an opaque caller reference to a
        document held elsewhere; the document itself never
        enters this substrate.
        """
        self._guard(actor, "enter", "exta_document_job_record")
        self._program(program_id, actor)
        _non_empty(document_ref, "document_ref")
        _one_of(job_kind, KNOWN_DOCUMENT_JOB_KINDS,
                DOCUMENT_JOB_KINDS, "job_kind")
        return self._create(
            "document_processing_job", "djob",
            {"program_id": program_id, "document_ref": document_ref,
             "job_kind": job_kind, "reference_stub": True,
             "processed_here": False, "recognized_here": False,
             "content_held": False, "state": "recorded_reference_only"},
            actor, "exta_document_job_record")

    def record_document_processing_report(
        self, program_id, job_id, outcome_label, actor, detail=None
    ):
        """Record a processing system's reported outcome (stub),
        stored verbatim as a label."""
        self._guard(actor, "record", "exta_document_report",
                    target=job_id)
        self._program(program_id, actor)
        _non_empty(outcome_label, "outcome_label")
        _string_or_none(detail, "detail")
        self._get("document_processing_job", job_id, program_id)
        return self._create(
            "document_processing_report", "dprt",
            {"program_id": program_id, "job_id": job_id,
             "outcome_label": outcome_label, "detail": detail,
             "reference_stub": True, "processed_here": False,
             "recognized_here": False, "content_held": False},
            actor, "exta_document_report")

    def get_document_processing_job(self, program_id, job_id, actor):
        self._guard(actor, "read", "exta_document_job_get", target=job_id)
        self._program(program_id, actor)
        return self._fetch("document_processing_job", job_id, program_id)

    def list_document_processing_jobs(
        self, program_id, actor, job_kind=None
    ):
        self._guard(actor, "read", "exta_document_job_list")
        self._program(program_id, actor)
        filters = {}
        if job_kind is not None:
            filters["job_kind"] = job_kind
        return self._list("document_processing_job", program_id, **filters)

    def list_document_processing_reports(
        self, program_id, actor, job_id=None
    ):
        self._guard(actor, "read", "exta_document_report_list")
        self._program(program_id, actor)
        filters = {}
        if job_id is not None:
            filters["job_id"] = job_id
        return self._list(
            "document_processing_report", program_id, **filters)

    def document_processing_summary(self, program_id, actor):
        """Derived at read: job/report counts over this stub's
        records. Nothing was processed here."""
        self._guard(actor, "read", "exta_document_summary")
        self._program(program_id, actor)
        jobs = self._list("document_processing_job", program_id)
        reports = self._list("document_processing_report", program_id)
        by_kind = {k: 0 for k in DOCUMENT_JOB_KINDS}
        for job in jobs:
            by_kind[job["job_kind"]] += 1
        return {
            "program_id": program_id,
            "jobs": len(jobs),
            "reports": len(reports),
            "jobs_by_kind": by_kind,
            "reference_stub": True,
            "processed_here": False,
            "recognized_here": False,
            "content_held": False,
            "derived": True,
            "method": "counts_over_document_processing_records",
        }
