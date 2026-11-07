"""Final GAPS batch, second unit: Remainder Addition — Finance L2.

Pins the ``finance.extensions_addition`` surface that closes the
6 open entries of the GAPS.md section "Remainder Addition —
Finance L2 (+4 forks)" (idx 589–594 in ``gaps-batch/inventory.json``):
the federal financial management system of record (Momentum,
registry + journal records with balances derived at read), the
procurement lifecycle engine (Coupa, stage records with the
contract ceiling as a bound), the spend analytics engine (Coupa,
a derived view capped at counts and recorded-cent sums), the
technology business management & FinOps engine (Apptio,
allocation/tagging records + reported outcomes), the trust
accounting & wealth management platform (Innovest, account and
transaction records with values as reported — and NO order or
execution surface, the "trading & investment execution" named
absence standing), and the AI/ML document processing engine
(Coupa — a labeled reference implementation).

Honesty pins mirror the group's suites: exact record key sets
(no field can hold a real account identifier or a computed
score), honesty labels False on the face of every record,
derived values never stored, money validated as integer cents
with a rejected operation consuming no id, access rules enforced
before state change with denied attempts audited under the
``exta_`` prefix, and a fresh mutation-verified negative control
on the ledger derivation seam (in
:meth:`AccountTotalsNegativeControl` at the bottom).
"""

import unittest

from finance import extensions_addition as exta
from finance.errors import NotFoundError, PermissionDenied, ValidationError
from finance.extensions_addition import FinanceExtensionsAddition

from finance_helpers import (
    ADMIN,
    MEMBER,
    VIEWER,
    OUTSIDER,
    PERIOD,
    PERIOD_OTHER,
    make_store,
)


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.ext = FinanceExtensionsAddition(self.store)
        self.pid = self.program_id

    # -- shared builders -----------------------------------------------

    def make_accounts(self, actor=MEMBER):
        alpha = self.ext.register_ledger_account(
            self.pid, "1000", "Operating funds", actor)
        beta = self.ext.register_ledger_account(
            self.pid, "2000", "Program revenue", actor)
        gamma = self.ext.register_ledger_account(
            self.pid, "3000", "Equipment", actor)
        return alpha, beta, gamma

    def make_entries(self, actor=MEMBER):
        alpha, beta, gamma = self.make_accounts(actor)
        self.ext.record_journal_entry(
            self.pid, PERIOD, alpha["id"], beta["id"], 10000,
            "initial funding", actor)
        self.ext.record_journal_entry(
            self.pid, PERIOD, alpha["id"], gamma["id"], 5000,
            "equipment reserve", actor)
        self.ext.record_journal_entry(
            self.pid, PERIOD, beta["id"], alpha["id"], 2000,
            "revenue share", actor)
        return alpha, beta, gamma

    def make_supplier(self, actor=MEMBER):
        return self.ext.register_supplier(
            self.pid, "sup-1", "Acme Cloud Services", actor)

    def make_contract(self, ceiling=100000, actor=MEMBER):
        supplier = self.make_supplier(actor)
        return self.ext.create_contract_record(
            self.pid, supplier["id"], "ctr-2026-001", ceiling, actor)

    def make_order(self, amount=40000, actor=MEMBER):
        contract = self.make_contract(actor=actor)
        return self.ext.create_purchase_order(
            self.pid, contract["id"], PERIOD, amount, actor)

    def make_trust_account(self, currency="USD", actor=MEMBER):
        from finance_helpers import make_employee
        participant = make_employee(self.store, self.pid)
        return self.ext.open_trust_account(
            self.pid, participant["id"], "trust-main", currency, actor)


class MomentumSystemOfRecord(AdditionFixture):
    """595-shaped surface for idx 589 (Momentum)."""

    def test_ledger_account_shape_has_no_identifier_field(self):
        account = self.ext.register_ledger_account(
            self.pid, "1000", "Operating funds", MEMBER)
        self.assertEqual(account["id"], "glac-1")
        self.assertIs(account["authoritative_here"], False)
        self.assertEqual(account["state"], "registered_record_only")
        self.assertEqual(
            set(account),
            {"id", "program_id", "account_ref", "title",
             "authoritative_here", "state", "created_by", "created_utc"},
        )

    def test_account_ref_must_be_unique_within_program(self):
        self.ext.register_ledger_account(
            self.pid, "1000", "Operating funds", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_ledger_account(
                self.pid, "1000", "Duplicate ref", MEMBER)

    def test_journal_entry_shape_and_binding(self):
        alpha, beta, _ = self.make_accounts()
        entry = self.ext.record_journal_entry(
            self.pid, PERIOD, alpha["id"], beta["id"], 10000,
            "initial funding", MEMBER)
        self.assertEqual(entry["id"], "jrnl-1")
        self.assertIs(entry["authoritative_here"], False)
        self.assertEqual(
            set(entry),
            {"id", "program_id", "period", "debit_account_id",
             "credit_account_id", "amount_cents", "memo_label",
             "authoritative_here", "created_by", "created_utc"},
        )

    def test_entry_rejects_same_account_on_both_sides(self):
        alpha, _, _ = self.make_accounts()
        with self.assertRaises(ValidationError):
            self.ext.record_journal_entry(
                self.pid, PERIOD, alpha["id"], alpha["id"], 100,
                "self posting", MEMBER)

    def test_entry_rejects_unknown_account_and_bad_period(self):
        alpha, _, _ = self.make_accounts()
        with self.assertRaises(NotFoundError):
            self.ext.record_journal_entry(
                self.pid, PERIOD, alpha["id"], "glac-99", 100,
                "ghost credit", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_journal_entry(
                self.pid, "2026/01", alpha["id"], "glac-2", 100,
                "bad period", MEMBER)

    def test_entry_money_boundary_consumes_no_id(self):
        alpha, beta, _ = self.make_accounts()
        for bad in (100.0, True, "100"):
            with self.assertRaises(ValidationError):
                self.ext.record_journal_entry(
                    self.pid, PERIOD, alpha["id"], beta["id"], bad,
                    "bad money", MEMBER)
        good = self.ext.record_journal_entry(
            self.pid, PERIOD, alpha["id"], beta["id"], 100, "ok", MEMBER)
        self.assertEqual(good["id"], "jrnl-1")

    def test_account_balances_derived_at_read_never_stored(self):
        alpha, beta, gamma = self.make_entries()
        view_a = self.ext.ledger_account_view(self.pid, alpha["id"], MEMBER)
        self.assertEqual(view_a["debit_total_cents"], 15000)
        self.assertEqual(view_a["credit_total_cents"], 2000)
        self.assertEqual(view_a["balance_cents"], 13000)
        self.assertEqual(view_a["journal_entries"], 3)
        view_b = self.ext.ledger_account_view(self.pid, beta["id"], MEMBER)
        self.assertEqual(view_b["balance_cents"], -8000)
        view_g = self.ext.ledger_account_view(self.pid, gamma["id"], MEMBER)
        self.assertEqual(view_g["balance_cents"], -5000)
        stored = self.ext.get_ledger_account(self.pid, alpha["id"], MEMBER)
        self.assertNotIn("balance_cents", stored)
        self.assertNotIn("debit_total_cents", stored)

    def test_trial_balance_derives_balanced_totals(self):
        self.make_entries()
        trial = self.ext.trial_balance(self.pid, MEMBER)
        self.assertEqual(trial["total_debits_cents"], 17000)
        self.assertEqual(trial["total_credits_cents"], 17000)
        self.assertIs(trial["balanced"], True)
        self.assertIs(trial["authoritative_here"], False)
        self.assertIs(trial["derived"], True)
        by_ref = {a["account_ref"]: a for a in trial["accounts"]}
        self.assertEqual(by_ref["1000"]["balance_cents"], 13000)
        empty = self.ext.trial_balance(self.pid, MEMBER, PERIOD_OTHER)
        self.assertEqual(empty["total_debits_cents"], 0)
        self.assertIs(empty["balanced"], True)


class ProcurementLifecycle(AdditionFixture):
    """idx 590 (Coupa): stage records, ceiling bound, payment reports."""

    def test_supplier_shape_and_unique_ref(self):
        supplier = self.make_supplier()
        self.assertEqual(supplier["id"], "supp-1")
        self.assertIs(supplier["vetted_here"], False)
        self.assertEqual(
            set(supplier),
            {"id", "program_id", "supplier_ref", "name_label",
             "vetted_here", "state", "created_by", "created_utc"},
        )
        with self.assertRaises(ValidationError):
            self.ext.register_supplier(
                self.pid, "sup-1", "Duplicate", MEMBER)

    def test_requisition_and_decision_are_separate_records(self):
        supplier = self.make_supplier()
        req = self.ext.create_requisition(
            self.pid, supplier["id"], "cloud hosting renewal", 25000,
            MEMBER)
        self.assertIs(req["approved_here"], False)
        decision = self.ext.record_requisition_decision(
            self.pid, req["id"], "approved by contracting officer",
            MEMBER, detail="FY26 renewal")
        self.assertEqual(decision["decision_label"],
                         "approved by contracting officer")
        self.assertIs(decision["decided_here"], False)
        stored = self.ext.list_requisitions(self.pid, MEMBER)[0]
        self.assertEqual(stored, req)  # decision left it byte-identical

    def test_purchase_order_bounded_by_recorded_ceiling(self):
        contract = self.make_contract(ceiling=100000)
        first = self.ext.create_purchase_order(
            self.pid, contract["id"], PERIOD, 60000, MEMBER)
        self.assertIs(first["placed_here"], False)
        self.assertEqual(first["supplier_id"], contract["supplier_id"])
        with self.assertRaises(ValidationError):
            self.ext.create_purchase_order(
                self.pid, contract["id"], PERIOD, 40001, MEMBER)
        second = self.ext.create_purchase_order(
            self.pid, contract["id"], PERIOD, 40000, MEMBER)
        self.assertEqual(second["id"], "pord-2")

    def test_invoice_inherits_order_fields(self):
        order = self.make_order()
        invoice = self.ext.record_invoice(
            self.pid, order["id"], 40000, MEMBER)
        self.assertEqual(invoice["contract_id"], order["contract_id"])
        self.assertEqual(invoice["supplier_id"], order["supplier_id"])
        self.assertEqual(invoice["period"], PERIOD)
        self.assertIs(invoice["issued_here"], False)
        self.assertIs(invoice["paid_here"], False)

    def test_payment_report_records_outcome_verbatim(self):
        order = self.make_order()
        invoice = self.ext.record_invoice(self.pid, order["id"], 40000,
                                          MEMBER)
        report = self.ext.record_supplier_payment_report(
            self.pid, invoice["id"], "paid in full by agency finance",
            MEMBER)
        self.assertEqual(report["outcome_label"],
                         "paid in full by agency finance")
        self.assertIs(report["paid_here"], False)
        stored = self.ext.list_invoices(self.pid, MEMBER)[0]
        self.assertEqual(stored, invoice)  # report left it byte-identical

    def test_summary_counts_and_sums_by_stage(self):
        order = self.make_order()
        invoice = self.ext.record_invoice(self.pid, order["id"], 40000,
                                          MEMBER)
        self.ext.record_supplier_payment_report(
            self.pid, invoice["id"], "paid", MEMBER)
        summary = self.ext.procurement_summary(self.pid, MEMBER)
        self.assertEqual(summary["suppliers"], 1)
        self.assertEqual(summary["contracts"], 1)
        self.assertEqual(summary["contract_ceiling_total_cents"], 100000)
        self.assertEqual(summary["orders"], 1)
        self.assertEqual(summary["order_total_cents"], 40000)
        self.assertEqual(summary["invoices"], 1)
        self.assertEqual(summary["invoice_total_cents"], 40000)
        self.assertEqual(summary["payment_reports"], 1)
        self.assertIs(summary["paid_here"], False)


class SpendAnalytics(AdditionFixture):
    """idx 591 (Coupa): derived view, counts and sums, no forecast."""

    def test_view_combines_core_and_procurement_records(self):
        from finance_helpers import (
            disbursed_request, make_accrual, make_booking,
            make_employee, make_traveler,
        )
        employee = make_employee(self.store, self.pid)
        make_accrual(self.store, self.pid, employee["id"])
        disbursed_request(self.store, self.pid, employee["id"])
        traveler = make_traveler(self.store, self.pid)
        make_booking(self.store, self.pid, traveler["id"])  # air, 30000
        order = self.make_order()
        self.ext.record_invoice(self.pid, order["id"], 40000, MEMBER)
        view = self.ext.spend_analytics(self.pid, PERIOD, MEMBER)
        self.assertEqual(view["bookings"]["air"],
                         {"count": 1, "total_cents": 30000})
        self.assertEqual(view["bookings"]["hotel"],
                         {"count": 0, "total_cents": 0})
        self.assertEqual(view["earned_wage_disbursements"], 1)
        self.assertEqual(view["earned_wage_disbursed_cents"], 10000)
        self.assertEqual(view["procurement_orders"], 1)
        self.assertEqual(view["procurement_order_total_cents"], 40000)
        self.assertEqual(view["procurement_invoice_total_cents"], 40000)
        self.assertIs(view["derived"], True)

    def test_view_shape_carries_no_rate_trend_or_total(self):
        view = self.ext.spend_analytics(self.pid, PERIOD, MEMBER)
        self.assertEqual(
            set(view),
            {"program_id", "period", "bookings",
             "earned_wage_disbursements", "earned_wage_disbursed_cents",
             "procurement_orders", "procurement_order_total_cents",
             "procurement_invoices", "procurement_invoice_total_cents",
             "derived", "method"},
        )
        keys = set()

        def collect(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    keys.add(key)
                    collect(item)
            elif isinstance(value, list):
                for item in value:
                    collect(item)

        collect(view)
        for banned in ("rate", "trend", "forecast", "average",
                       "grand_total", "grand_total_cents"):
            self.assertNotIn(banned, keys)

    def test_other_period_is_empty(self):
        self.make_order()
        view = self.ext.spend_analytics(self.pid, PERIOD_OTHER, MEMBER)
        self.assertEqual(view["procurement_orders"], 0)
        self.assertEqual(view["procurement_order_total_cents"], 0)


class FinOps(AdditionFixture):
    """idx 592 (Apptio): allocation/tagging records + reported figures."""

    def test_allocation_shape(self):
        alloc = self.ext.record_cost_allocation(
            self.pid, PERIOD, "public cloud provider", "agency platform",
            75000, MEMBER)
        self.assertEqual(alloc["id"], "allo-1")
        self.assertIs(alloc["optimized_here"], False)
        self.assertEqual(
            set(alloc),
            {"id", "program_id", "period", "source_label", "target_label",
             "amount_cents", "optimized_here", "state", "created_by",
             "created_utc"},
        )

    def test_tag_binds_to_existing_allocation(self):
        alloc = self.ext.record_cost_allocation(
            self.pid, PERIOD, "saas subscriptions", "agency platform",
            1000, MEMBER)
        tag = self.ext.tag_cost_allocation(
            self.pid, alloc["id"], "cost-center: 4410", MEMBER)
        self.assertEqual(tag["allocation_id"], alloc["id"])
        with self.assertRaises(NotFoundError):
            self.ext.tag_cost_allocation(self.pid, "allo-99", "x", MEMBER)

    def test_optimization_report_stores_figure_as_reported(self):
        report = self.ext.record_optimization_report(
            self.pid, PERIOD, "rightsizing recommended by engine",
            MEMBER, reported_savings_cents=12345)
        self.assertEqual(report["reported_savings_cents"], 12345)
        self.assertIs(report["optimized_here"], False)
        self.assertIs(report["savings_computed_here"], False)

    def test_summary_derives_totals_by_target(self):
        self.ext.record_cost_allocation(
            self.pid, PERIOD, "cloud", "agency platform", 75000, MEMBER)
        self.ext.record_cost_allocation(
            self.pid, PERIOD, "saas", "agency platform", 25000, MEMBER)
        self.ext.record_cost_allocation(
            self.pid, PERIOD, "cloud", "field office", 5000, MEMBER)
        self.ext.record_optimization_report(
            self.pid, PERIOD, "idle resources flagged", MEMBER,
            reported_savings_cents=2000)
        summary = self.ext.finops_summary(self.pid, MEMBER)
        self.assertEqual(summary["allocations"], 3)
        self.assertEqual(summary["allocated_total_cents"], 105000)
        self.assertEqual(
            summary["allocations_by_target"]["agency platform"],
            {"count": 2, "total_cents": 100000})
        self.assertEqual(summary["reported_savings_total_cents"], 2000)
        self.assertIs(summary["optimized_here"], False)
        self.assertIs(summary["derived"], True)


class TrustAccounting(AdditionFixture):
    """idx 593 (Innovest): records with values as reported."""

    def test_account_shape_and_labels(self):
        account = self.make_trust_account()
        self.assertEqual(account["id"], "tacc-1")
        self.assertIs(account["valued_here"], False)
        self.assertIs(account["managed_here"], False)
        self.assertIs(account["converted_here"], False)
        self.assertEqual(
            set(account),
            {"id", "program_id", "participant_id", "account_ref",
             "currency_label", "valued_here", "managed_here",
             "converted_here", "state", "created_by", "created_utc"},
        )

    def test_no_execution_surface_exists(self):
        for name in ("create_trade_order", "execute_trade",
                     "place_trade", "buy", "sell"):
            self.assertFalse(hasattr(self.ext, name), name)

    def test_balance_derives_by_recorded_arithmetic(self):
        account = self.make_trust_account()
        self.ext.record_trust_transaction(
            self.pid, account["id"], PERIOD, "contribution", 100000,
            MEMBER)
        self.ext.record_trust_transaction(
            self.pid, account["id"], PERIOD, "income", 2500, MEMBER)
        self.ext.record_trust_transaction(
            self.pid, account["id"], PERIOD, "distribution", 30000,
            MEMBER)
        self.ext.record_trust_transaction(
            self.pid, account["id"], PERIOD, "fee", 500, MEMBER)
        view = self.ext.trust_account_view(self.pid, account["id"], MEMBER)
        self.assertEqual(view["balance_cents"], 72000)
        self.assertEqual(
            view["transactions_by_kind"]["contribution"],
            {"count": 1, "total_cents": 100000})
        self.assertEqual(
            view["transactions_by_kind"]["fee"],
            {"count": 1, "total_cents": 500})
        stored = self.ext.get_trust_account(self.pid, account["id"], MEMBER)
        self.assertNotIn("balance_cents", stored)

    def test_bad_kind_rejected(self):
        account = self.make_trust_account()
        with self.assertRaises(ValidationError):
            self.ext.record_trust_transaction(
                self.pid, account["id"], PERIOD, "trade", 100, MEMBER)

    def test_position_value_stored_as_reported(self):
        account = self.make_trust_account()
        report = self.ext.record_position_report(
            self.pid, account["id"], "fund-ref-7", 987654, MEMBER)
        self.assertEqual(report["reported_value_cents"], 987654)
        self.assertIs(report["valued_here"], False)
        view = self.ext.trust_account_view(self.pid, account["id"], MEMBER)
        self.assertEqual(view["reported_position_total_cents"], 987654)

    def test_summary_counts_without_cross_currency_sums(self):
        from finance_helpers import make_employee
        self.make_trust_account(currency="USD")
        participant = make_employee(self.store, self.pid, ref="emp-2")
        self.ext.open_trust_account(
            self.pid, participant["id"], "trust-eu", "EUR", MEMBER)
        summary = self.ext.trust_summary(self.pid, MEMBER)
        self.assertEqual(summary["accounts"], 2)
        self.assertEqual(summary["accounts_by_currency"],
                         {"USD": 1, "EUR": 1})
        self.assertIs(summary["converted_here"], False)
        self.assertNotIn("total_cents", summary)
        self.assertNotIn("balance_cents", summary)


class DocumentProcessingStub(AdditionFixture):
    """idx 594 (Coupa): labeled reference implementation."""

    def test_job_record_carries_stub_labels(self):
        job = self.ext.record_document_processing_job(
            self.pid, "doc-ref-1", "document_processing", MEMBER)
        self.assertEqual(job["id"], "djob-1")
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["processed_here"], False)
        self.assertIs(job["recognized_here"], False)
        self.assertIs(job["content_held"], False)
        self.assertEqual(
            set(job),
            {"id", "program_id", "document_ref", "job_kind",
             "reference_stub", "processed_here", "recognized_here",
             "content_held", "state", "created_by", "created_utc"},
        )

    def test_image_recognition_kind_and_report(self):
        job = self.ext.record_document_processing_job(
            self.pid, "img-ref-9", "image_recognition", MEMBER)
        report = self.ext.record_document_processing_report(
            self.pid, job["id"], "fields extracted by vendor engine",
            MEMBER)
        self.assertIs(report["reference_stub"], True)
        self.assertEqual(report["outcome_label"],
                         "fields extracted by vendor engine")
        summary = self.ext.document_processing_summary(self.pid, MEMBER)
        self.assertIs(summary["reference_stub"], True)
        self.assertEqual(summary["jobs_by_kind"],
                         {"document_processing": 0, "image_recognition": 1})

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.record_document_processing_job(
                self.pid, "doc-ref-2", "translation", MEMBER)


BANNED_EXACT_KEYS = {
    "account_number", "routing_number", "iban", "sort_code",
    "card_number", "bank_account", "credit_score", "score",
}


def all_keys(value):
    keys = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            keys |= all_keys(item)
    elif isinstance(value, list):
        for item in value:
            keys |= all_keys(item)
    return keys


class CrossCutting(AdditionFixture):
    def _one_record_of_each_kind(self):
        order = self.make_order()
        invoice = self.ext.record_invoice(self.pid, order["id"], 40000,
                                          MEMBER)
        trust = self.make_trust_account()
        account, _, _ = self.make_accounts()
        alloc = self.ext.record_cost_allocation(
            self.pid, PERIOD, "cloud", "agency", 1000, MEMBER)
        job = self.ext.record_document_processing_job(
            self.pid, "doc-ref-1", "document_processing", MEMBER)
        return [
            account,
            self.ext.record_journal_entry(
                self.pid, PERIOD, "glac-1", "glac-2", 100, "m", MEMBER),
            self.ext.get_supplier(self.pid, order["supplier_id"], MEMBER),
            self.ext.record_requisition_decision(
                self.pid,
                self.ext.create_requisition(
                    self.pid, order["supplier_id"], "x", 100, MEMBER)["id"],
                "approved", MEMBER),
            self.ext.list_contracts(self.pid, MEMBER)[0],
            order, invoice,
            self.ext.record_supplier_payment_report(
                self.pid, invoice["id"], "paid", MEMBER),
            alloc,
            self.ext.tag_cost_allocation(
                self.pid, alloc["id"], "tag", MEMBER),
            self.ext.record_optimization_report(
                self.pid, PERIOD, "reported", MEMBER),
            trust,
            self.ext.record_trust_transaction(
                self.pid, trust["id"], PERIOD, "income", 100, MEMBER),
            self.ext.record_position_report(
                self.pid, trust["id"], "fund-ref", 100, MEMBER),
            job,
            self.ext.record_document_processing_report(
                self.pid, job["id"], "done", MEMBER),
        ]

    def test_no_record_shape_can_hold_an_identifier_or_score(self):
        for record in self._one_record_of_each_kind():
            self.assertTrue(
                BANNED_EXACT_KEYS.isdisjoint(all_keys(record)), record)

    def test_viewer_writes_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_ledger_account(
                self.pid, "1000", "Operating funds", VIEWER)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "exta_ledger_account_register:denied"]
        self.assertEqual(len(denied), 1)

    def test_outsider_denied_everywhere(self):
        with self.assertRaises(PermissionDenied):
            self.ext.list_suppliers(self.pid, OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.register_supplier(
                self.pid, "sup-9", "Ghost", OUTSIDER)

    def test_platform_admin_reaches_without_membership(self):
        supplier = self.ext.register_supplier(
            self.pid, "sup-admin", "Admin-entered", ADMIN)
        self.assertEqual(supplier["created_by"], "alice")
        self.assertEqual(
            self.ext.list_suppliers(self.pid, ADMIN)[0]["id"],
            supplier["id"])

    def test_records_invisible_across_programs(self):
        other = self.store.create_program("other-program", MEMBER)
        supplier = self.make_supplier()
        self.assertEqual(self.ext.list_suppliers(other["id"], MEMBER), [])
        with self.assertRaises(NotFoundError):
            self.ext.get_supplier(other["id"], supplier["id"], MEMBER)

    def test_audit_failure_rolls_back_record_and_id(self):
        class Boom:
            def record(self, *args, **kwargs):
                raise RuntimeError("audit unavailable")

        real_audit = self.store.audit
        self.store.audit = Boom()
        try:
            with self.assertRaises(RuntimeError):
                self.ext.register_supplier(
                    self.pid, "sup-x", "Doomed", MEMBER)
        finally:
            self.store.audit = real_audit
        self.assertEqual(self.ext.list_suppliers(self.pid, MEMBER), [])
        supplier = self.ext.register_supplier(
            self.pid, "sup-x", "Doomed", MEMBER)
        self.assertEqual(supplier["id"], "supp-1")

    def test_successes_audited_under_exta_prefix(self):
        self.make_supplier()
        actions = {e["action"] for e in self.audit.entries()}
        self.assertIn("exta_supplier_register", actions)


def mutant_account_totals(journal_entries, account_id):
    """The defect under control: the credit side is added to the
    debit total instead of being netted against it, silently
    corrupting every derived balance while leaving every stored
    record's shape intact."""
    debit_total = 0
    credit_total = 0
    for entry in journal_entries:
        if entry["debit_account_id"] == account_id:
            debit_total += entry["amount_cents"]
        if entry["credit_account_id"] == account_id:
            debit_total += entry["amount_cents"]
    return debit_total, credit_total


class AccountTotalsNegativeControl(unittest.TestCase):
    """Mutation-verified negative control for this unit's ledger
    derivation: balances derive at read via ``_account_totals``,
    so a derivation that nets credits the wrong way must be
    caught. The canonical scenario is synthetic journal entries
    run through the real derivation; the live drill (patching the
    real seam to the mutant body and re-running this suite) is
    recorded in tests/README.md.
    """

    ENTRIES = [
        {"debit_account_id": "glac-1", "credit_account_id": "glac-2",
         "amount_cents": 10000},
        {"debit_account_id": "glac-1", "credit_account_id": "glac-3",
         "amount_cents": 5000},
        {"debit_account_id": "glac-2", "credit_account_id": "glac-1",
         "amount_cents": 2000},
    ]

    def test_canonical_expectation_holds(self):
        debits, credits = exta._account_totals(self.ENTRIES, "glac-1")
        self.assertEqual((debits, credits), (15000, 2000))
        self.assertEqual(debits - credits, 13000)

    def test_mutant_totals_differ_from_canonical(self):
        m_debits, m_credits = mutant_account_totals(self.ENTRIES, "glac-1")
        self.assertEqual((m_debits, m_credits), (17000, 0))
        self.assertNotEqual(
            (m_debits, m_credits),
            exta._account_totals(self.ENTRIES, "glac-1"))

    def test_mutant_balance_fails_the_canonical_check(self):
        m_debits, m_credits = mutant_account_totals(self.ENTRIES, "glac-1")
        with self.assertRaises(AssertionError):
            self.assertEqual(m_debits - m_credits, 13000)

    def test_only_debits_case_both_agree(self):
        entries = [{"debit_account_id": "glac-9",
                    "credit_account_id": "glac-2", "amount_cents": 700}]
        self.assertEqual(exta._account_totals(entries, "glac-9"), (700, 0))
        self.assertEqual(mutant_account_totals(entries, "glac-9"), (700, 0))


if __name__ == "__main__":
    unittest.main()
