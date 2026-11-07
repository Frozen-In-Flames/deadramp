"""Final GAPS batch tests — Untiered Set 16 extension surface.

Pins the seven batch entries of this set (inventory idx 905–911)
in their in-substrate forms, the stub labels on the two reference
entries, the tier-null scan over every extension record and
derived view, the no-PII invariant (forbidden keys, forbidden
signature parameters, TypeError on smuggled PII/content keyword
arguments), derived-never-stored for every computed figure, RBAC
and employee scope, failed operations consuming no id, and the
fresh mutation-verified negative control on the payroll net seam
(``hr.extensions._derive_net_cents``).
"""

import inspect
import unittest

from hr.access import User
from hr.errors import NotFoundError, PermissionDenied, ValidationError
from hr.extensions import (
    FORBIDDEN_KEYS,
    FORBIDDEN_PARAMS,
    TIER_KEYS,
    HrExtensions,
    _derive_net_cents,
)
from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST, make_store

DIGEST_A = "a" * 64
DIGEST_B = "0123456789abcdef" * 4
OTHER_EMPLOYEE = User("erin", "employee")


def _walk_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _walk_keys(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            keys |= _walk_keys(item)
    return keys


def _tier_shaped(keys):
    return {k for k in keys
            if k in TIER_KEYS or "tier" in k or "cmmc" in k
            or "baseline" in k or "fedramp" in k or "impact" in k}


def make_extensions():
    """Canonical fixture: core store (position + carol) + extensions.

    A second person (erin) is registered for scope tests. Returns
    (store, extensions).
    """
    store, _, _ = make_store()
    store.create_person("erin", ADMIN, kind="employee")
    return store, HrExtensions(store)


def stocked_extensions():
    """Fixture with one record of every extension kind. Returns
    (store, extensions, ids) where ids maps a short label to the
    created record's id."""
    store, ext = make_extensions()
    run = ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST,
                                 label="October first half")
    ext.add_pay_statement(run["id"], "carol", 500000, SPECIALIST,
                          deductions=[{"label": "tax withholding",
                                       "amount_cents": 75000},
                                      {"label": "benefit election",
                                       "amount_cents": 25000}])
    report = ext.create_expense_report("carol", "Site visit", SPECIALIST)
    ext.add_expense_line(report["id"], "travel", 12345, SPECIALIST,
                         incurred_on="2026-10-03", note_ref="receipt-1")
    entry = ext.record_time_entry("carol", "proj-alpha", "2026-10-06", 480,
                                  SPECIALIST, activity_label="intake")
    assignment = ext.create_schedule_assignment(
        "carol", "proj-alpha", "2026-10-05", "2026-10-09", 2400, SPECIALIST)
    comm = ext.create_communication("announcement", "all-staff", "msg-1",
                                    SPECIALIST, subject_label="Open enrollment")
    ext.record_delivery_receipt(comm["id"], "delivered", SPECIALIST,
                                reported_count=42)
    doc = ext.register_document("doc-handbook", "policy", SPECIALIST,
                                digest=DIGEST_A, retention_label="retain-7y")
    fed = ext.create_federation_record("agency-idp", SPECIALIST,
                                       protocol_label="saml")
    review = ext.record_access_review("carol", "approved", SPECIALIST)
    mon = ext.record_monitoring_report("soc-feed", "no anomalies", SPECIALIST,
                                       reported_count=0)
    vul = ext.record_vulnerability_report("scanner-a", "high", SPECIALIST,
                                          reported_count=3)
    inc = ext.record_security_incident("Reported phishing wave", SPECIALIST)
    ids = {
        "run": run["id"], "report": report["id"], "entry": entry["id"],
        "assignment": assignment["id"], "comm": comm["id"],
        "doc": doc["id"], "fed": fed["id"], "review": review["id"],
        "mon": mon["id"], "vul": vul["id"], "inc": inc["id"],
    }
    return store, ext, ids


class TestPayroll(unittest.TestCase):
    """idx 905 — Payroll processing engine (built, records form)."""

    def test_run_and_statement_net_derived_never_stored(self):
        """Payroll: the statement's net (500000 - 75000 - 25000 = 400000) and the run totals appear only on the derived view; the stored statement carries no net or total key."""
        store, ext = make_extensions()
        run = ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST)
        view = ext.add_pay_statement(
            run["id"], "carol", 500000, SPECIALIST,
            deductions=[{"label": "tax withholding", "amount_cents": 75000},
                        {"label": "benefit election", "amount_cents": 25000}])
        statement = view["statements"][0]
        self.assertEqual(statement["net_amount_cents"], 400000)
        self.assertEqual(view["total_gross_cents"], 500000)
        self.assertEqual(view["total_deduction_cents"], 100000)
        self.assertEqual(view["total_net_cents"], 400000)
        self.assertEqual(view["statement_count"], 1)
        self.assertTrue(view["derived"])
        stored = ext._payroll_runs[run["id"]]["statements"][0]
        self.assertEqual(
            set(stored),
            {"statement_id", "person_ref", "gross_amount_cents", "deductions"})
        self.assertNotIn("net_amount_cents", _walk_keys(ext._payroll_runs))

    def test_run_record_labels_and_state(self):
        """Payroll: the run record states paid_here / executed_here False; closing the run blocks further statements."""
        store, ext = make_extensions()
        run = ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST)
        self.assertEqual(run["id"], "prn-1")
        self.assertFalse(run["paid_here"])
        self.assertFalse(run["executed_here"])
        ext.set_payroll_run_state(run["id"], "closed", SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.add_pay_statement(run["id"], "carol", 100, SPECIALIST)

    def test_amounts_are_integer_cents_only(self):
        """Payroll: float and bool gross amounts and float deduction amounts are rejected; a rejected statement consumes no slot."""
        store, ext = make_extensions()
        run = ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST)
        for bad in (100.5, True, "100"):
            with self.assertRaises(ValidationError):
                ext.add_pay_statement(run["id"], "carol", bad, SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.add_pay_statement(
                run["id"], "carol", 1000, SPECIALIST,
                deductions=[{"label": "x", "amount_cents": 1.5}])
        view = ext.add_pay_statement(run["id"], "carol", 1000, SPECIALIST)
        self.assertEqual(view["statements"][0]["statement_id"], "s-1")

    def test_statement_requires_core_person_and_no_duplicates(self):
        """Payroll: an unknown person_ref is NotFound; a second statement for the same person on one run is rejected."""
        store, ext = make_extensions()
        run = ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST)
        with self.assertRaises(NotFoundError):
            ext.add_pay_statement(run["id"], "ghost", 100, SPECIALIST)
        ext.add_pay_statement(run["id"], "carol", 100, SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.add_pay_statement(run["id"], "carol", 200, SPECIALIST)

    def test_employee_view_scoped_to_own_statements(self):
        """Payroll: an employee-role reader sees only their own statements and totals over them alone."""
        store, ext = make_extensions()
        run = ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST)
        ext.add_pay_statement(run["id"], "carol", 1000, SPECIALIST)
        ext.add_pay_statement(run["id"], "erin", 2000, SPECIALIST)
        view = ext.get_payroll_run(run["id"], EMPLOYEE)
        self.assertEqual([s["person_ref"] for s in view["statements"]],
                         ["carol"])
        self.assertEqual(view["total_gross_cents"], 1000)
        full = ext.get_payroll_run(run["id"], SPECIALIST)
        self.assertEqual(full["statement_count"], 2)


class TestExpenses(unittest.TestCase):
    """idx 906 — Expense tracking & management (built)."""

    def test_total_derived_never_stored(self):
        """Expenses: the report total (12345 + 755 = 13100) is derived at read; the stored record carries no total key."""
        store, ext = make_extensions()
        report = ext.create_expense_report("carol", "Site visit", SPECIALIST)
        ext.add_expense_line(report["id"], "travel", 12345, SPECIALIST)
        view = ext.add_expense_line(report["id"], "meals", 755, SPECIALIST)
        self.assertEqual(view["total_cents"], 13100)
        self.assertEqual(view["line_count"], 2)
        self.assertFalse(view["reimbursed_here"])
        stored = ext._expense_reports[report["id"]]
        self.assertNotIn("total_cents", _walk_keys(stored))

    def test_line_validation(self):
        """Expenses: unknown category, zero / negative / float amounts, and lines on a closed report are rejected whole."""
        store, ext = make_extensions()
        report = ext.create_expense_report("carol", "Trip", SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.add_expense_line(report["id"], "airfare", 100, SPECIALIST)
        for bad in (0, -5, 9.99, False):
            with self.assertRaises(ValidationError):
                ext.add_expense_line(report["id"], "travel", bad, SPECIALIST)
        ext.set_expense_report_state(report["id"], "closed", SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.add_expense_line(report["id"], "travel", 100, SPECIALIST)

    def test_state_is_a_recorded_label(self):
        """Expenses: approval is a recorded state label; the record still states reimbursed_here False after approval."""
        store, ext = make_extensions()
        report = ext.create_expense_report("carol", "Trip", SPECIALIST)
        ext.set_expense_report_state(report["id"], "submitted", SPECIALIST)
        view = ext.set_expense_report_state(report["id"], "approved", SPECIALIST)
        self.assertEqual(view["state"], "approved")
        self.assertFalse(view["reimbursed_here"])
        with self.assertRaises(ValidationError):
            ext.set_expense_report_state(report["id"], "paid", SPECIALIST)

    def test_employee_scope(self):
        """Expenses: an employee reads only their own reports; reading another person's report is PermissionDenied."""
        store, ext = make_extensions()
        mine = ext.create_expense_report("carol", "Mine", SPECIALIST)
        theirs = ext.create_expense_report("erin", "Theirs", SPECIALIST)
        self.assertEqual(
            [r["id"] for r in ext.list_expense_reports(EMPLOYEE)],
            [mine["id"]])
        with self.assertRaises(PermissionDenied):
            ext.get_expense_report(theirs["id"], EMPLOYEE)


class TestTimeAndScheduling(unittest.TestCase):
    """idx 907 — Project time tracking & resource scheduling (built)."""

    def test_time_entry_recorded_in_integer_minutes(self):
        """Time: entries hold integer minutes with source 'recorded'; float / bool / zero minutes are rejected."""
        store, ext = make_extensions()
        entry = ext.record_time_entry("carol", "proj-alpha", "2026-10-06",
                                      480, SPECIALIST)
        self.assertEqual(entry["id"], "tme-1")
        self.assertEqual(entry["minutes"], 480)
        self.assertEqual(entry["source"], "recorded")
        for bad in (7.5, True, 0, -30):
            with self.assertRaises(ValidationError):
                ext.record_time_entry("carol", "proj-alpha", "2026-10-06",
                                      bad, SPECIALIST)

    def test_assignment_is_data_not_computation(self):
        """Scheduling: an assignment is a recorded plan carrying assigned_automatically False; end before start is rejected."""
        store, ext = make_extensions()
        assignment = ext.create_schedule_assignment(
            "carol", "proj-alpha", "2026-10-05", "2026-10-09", 2400,
            SPECIALIST)
        self.assertFalse(assignment["assigned_automatically"])
        self.assertEqual(assignment["planned_minutes"], 2400)
        with self.assertRaises(ValidationError):
            ext.create_schedule_assignment(
                "carol", "proj-alpha", "2026-10-09", "2026-10-05", 60,
                SPECIALIST)

    def test_project_summary_derived_counts_and_sums(self):
        """Time: the project summary derives entry/assignment counts, recorded and scheduled minutes, and distinct persons at read; it is stored nowhere."""
        store, ext = make_extensions()
        ext.record_time_entry("carol", "proj-alpha", "2026-10-06", 480,
                              SPECIALIST)
        ext.record_time_entry("erin", "proj-alpha", "2026-10-06", 240,
                              SPECIALIST)
        ext.record_time_entry("carol", "proj-beta", "2026-10-06", 60,
                              SPECIALIST)
        ext.create_schedule_assignment("carol", "proj-alpha", "2026-10-05",
                                       "2026-10-09", 2400, SPECIALIST)
        summary = ext.project_time_summary("proj-alpha", ADMIN)
        self.assertEqual(summary["entry_count"], 2)
        self.assertEqual(summary["recorded_minutes"], 720)
        self.assertEqual(summary["scheduled_minutes"], 2400)
        self.assertEqual(summary["person_count"], 2)
        self.assertTrue(summary["derived"])
        self.assertFalse(summary["stored"])
        with self.assertRaises(PermissionDenied):
            ext.project_time_summary("proj-alpha", EMPLOYEE)

    def test_person_summary_and_scope(self):
        """Time: the per-person summary sums only that person's records; an employee cannot read another person's summary."""
        store, ext = make_extensions()
        ext.record_time_entry("carol", "proj-alpha", "2026-10-06", 480,
                              SPECIALIST)
        ext.record_time_entry("carol", "proj-beta", "2026-10-07", 120,
                              SPECIALIST)
        summary = ext.person_time_summary("carol", EMPLOYEE)
        self.assertEqual(summary["recorded_minutes"], 600)
        with self.assertRaises(PermissionDenied):
            ext.person_time_summary("erin", EMPLOYEE)


class TestCommunications(unittest.TestCase):
    """idx 908 — Employee communications & messaging platform (built,
    transport half labeled)."""

    def test_communication_record_is_metadata_only(self):
        """Communications: the record holds channel / audience / message references and states reference_transport True, delivered_here False, messages_held_here False."""
        store, ext = make_extensions()
        comm = ext.create_communication("announcement", "all-staff", "msg-1",
                                        SPECIALIST)
        self.assertEqual(comm["id"], "com-1")
        self.assertTrue(comm["reference_transport"])
        self.assertFalse(comm["delivered_here"])
        self.assertFalse(comm["messages_held_here"])
        self.assertEqual(comm["receipt_count"], 0)
        self.assertIsNone(comm["latest_outcome_label"])

    def test_delivery_receipt_is_a_reported_outcome(self):
        """Communications: a receipt records the transport's reported outcome verbatim; the view derives the receipt count and latest outcome at read."""
        store, ext = make_extensions()
        comm = ext.create_communication("email_notice", "new-hires", "msg-2",
                                        SPECIALIST)
        receipt = ext.record_delivery_receipt(comm["id"], "delivered",
                                              SPECIALIST, reported_count=17)
        self.assertTrue(receipt["reference_transport"])
        self.assertFalse(receipt["delivered_here"])
        view = ext.get_communication(comm["id"], SPECIALIST)
        self.assertEqual(view["receipt_count"], 1)
        self.assertEqual(view["latest_outcome_label"], "delivered")

    def test_no_content_parameter_exists(self):
        """Communications: passing message content as a keyword argument raises TypeError — no parameter can accept it."""
        store, ext = make_extensions()
        with self.assertRaises(TypeError):
            ext.create_communication("announcement", "all-staff", "msg-1",
                                     SPECIALIST, content="hello")
        with self.assertRaises(TypeError):
            ext.create_communication("announcement", "all-staff", "msg-1",
                                     SPECIALIST, message_text="hello")


class TestDocuments(unittest.TestCase):
    """idx 909 — Document management services (built, registry form)."""

    def test_document_registry_and_derived_current_version(self):
        """Documents: the record holds an opaque reference plus digests and states content_held_here / stored_here False; current version and digest derive at read from the chain."""
        store, ext = make_extensions()
        doc = ext.register_document("doc-handbook", "policy", SPECIALIST,
                                    digest=DIGEST_A)
        self.assertFalse(doc["content_held_here"])
        self.assertFalse(doc["stored_here"])
        self.assertEqual(doc["current_version"], 1)
        self.assertEqual(doc["current_digest"], DIGEST_A)
        view = ext.add_document_version(doc["id"], SPECIALIST,
                                        digest=DIGEST_B)
        self.assertEqual(view["current_version"], 2)
        self.assertEqual(view["current_digest"], DIGEST_B)
        self.assertEqual(view["version_count"], 2)
        stored = ext._documents[doc["id"]]
        self.assertNotIn("current_version", _walk_keys(stored))
        self.assertNotIn("current_digest", _walk_keys(stored))

    def test_digest_validation(self):
        """Documents: a malformed digest (short, non-hex, non-string) is rejected; an uppercase digest is normalized to lowercase."""
        store, ext = make_extensions()
        for bad in ("abc", "g" * 64, 12345):
            with self.assertRaises(ValidationError):
                ext.register_document("doc-x", "form", SPECIALIST, digest=bad)
        doc = ext.register_document("doc-y", "form", SPECIALIST,
                                    digest="A" * 64)
        self.assertEqual(doc["current_digest"], "a" * 64)

    def test_duplicate_document_ref_rejected(self):
        """Documents: registering the same opaque document_ref twice is a validation error."""
        store, ext = make_extensions()
        ext.register_document("doc-handbook", "policy", SPECIALIST)
        with self.assertRaises(ValidationError):
            ext.register_document("doc-handbook", "notice", SPECIALIST)

    def test_no_content_parameter_exists(self):
        """Documents: passing document content as a keyword argument raises TypeError."""
        store, ext = make_extensions()
        with self.assertRaises(TypeError):
            ext.register_document("doc-z", "form", SPECIALIST,
                                  content="full text")
        with self.assertRaises(TypeError):
            ext.register_document("doc-z", "form", SPECIALIST,
                                  document_text="full text")


class TestIdentityFederationReference(unittest.TestCase):
    """idx 910 — Identity federation / PAM services (reference)."""

    def test_federation_record_is_a_labeled_stub(self):
        """Federation: the record carries reference_stub True, state recorded_reference_only, identity_provider False, federated_here False."""
        store, ext = make_extensions()
        record = ext.create_federation_record("agency-idp", SPECIALIST,
                                              protocol_label="saml")
        self.assertEqual(record["id"], "fed-1")
        self.assertTrue(record["reference_stub"])
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertFalse(record["identity_provider"])
        self.assertFalse(record["federated_here"])

    def test_access_review_outcome_is_reported_not_determined(self):
        """PAM: a review records the reported outcome label verbatim and states determined_here / managed_here False; unknown persons are NotFound."""
        store, ext = make_extensions()
        record = ext.record_access_review("carol", "approved", SPECIALIST)
        self.assertTrue(record["reference_stub"])
        self.assertEqual(record["outcome_label"], "approved")
        self.assertFalse(record["determined_here"])
        self.assertFalse(record["managed_here"])
        with self.assertRaises(NotFoundError):
            ext.record_access_review("ghost", "approved", SPECIALIST)

    def test_reference_records_change_no_core_record(self):
        """Federation/PAM: creating reference records leaves the core report byte-identical — nothing federates, nothing is provisioned."""
        store, ext = make_extensions()
        before = store.report(ADMIN)
        ext.create_federation_record("agency-idp", SPECIALIST)
        ext.record_access_review("carol", "approved", SPECIALIST)
        self.assertEqual(store.report(ADMIN), before)


class TestSecurityOperationsReference(unittest.TestCase):
    """idx 911 — Security operations engines (reference)."""

    def test_monitoring_and_vulnerability_records_are_stubs(self):
        """SecOps: monitoring and vulnerability records carry reference_stub True and state monitored_here / scanned_here False; the severity label is held verbatim."""
        store, ext = make_extensions()
        mon = ext.record_monitoring_report("soc-feed", "no anomalies",
                                           SPECIALIST, reported_count=0)
        self.assertTrue(mon["reference_stub"])
        self.assertFalse(mon["monitored_here"])
        self.assertFalse(mon["detected_here"])
        vul = ext.record_vulnerability_report("scanner-a", "high",
                                              SPECIALIST, reported_count=3)
        self.assertTrue(vul["reference_stub"])
        self.assertFalse(vul["scanned_here"])
        self.assertEqual(vul["severity_label"], "high")
        self.assertEqual(vul["reported_count"], 3)

    def test_incident_record_and_core_case_binding(self):
        """SecOps: an incident may bind to an existing core case (left byte-identical) and states responded_here False; a missing case is NotFound."""
        store, ext = make_extensions()
        case = store.create_case("carol", "general", "Inquiry", SPECIALIST)
        before = store.get_case(case["id"], SPECIALIST)
        incident = ext.record_security_incident("Reported phishing wave",
                                                SPECIALIST,
                                                case_id=case["id"])
        self.assertTrue(incident["reference_stub"])
        self.assertFalse(incident["responded_here"])
        self.assertEqual(store.get_case(case["id"], SPECIALIST), before)
        with self.assertRaises(NotFoundError):
            ext.record_security_incident("x", SPECIALIST, case_id="cas-99")

    def test_summary_counts_derived(self):
        """SecOps: the summary counts the three reference families at read and is stored nowhere."""
        store, ext, _ = stocked_extensions()
        summary = ext.security_operations_summary(ADMIN)
        self.assertEqual(summary["monitoring_reports"], 1)
        self.assertEqual(summary["vulnerability_reports"], 1)
        self.assertEqual(summary["security_incidents"], 1)
        self.assertTrue(summary["reference_stub"])
        self.assertFalse(summary["stored"])


class TestCrossCutting(unittest.TestCase):
    """Tier-null scan, no-PII invariant, RBAC, audit, id discipline."""

    def _all_records_and_views(self, ext, ids):
        records = []
        for container in (ext._payroll_runs, ext._expense_reports,
                          ext._time_entries, ext._schedule_assignments,
                          ext._communications, ext._delivery_receipts,
                          ext._documents, ext._federation_records,
                          ext._access_reviews, ext._monitoring_reports,
                          ext._vulnerability_reports,
                          ext._security_incidents):
            records.extend(container.values())
        views = [
            ext.get_payroll_run(ids["run"], ADMIN),
            ext.get_expense_report(ids["report"], ADMIN),
            ext.get_communication(ids["comm"], ADMIN),
            ext.get_document(ids["doc"], ADMIN),
            ext.project_time_summary("proj-alpha", ADMIN),
            ext.person_time_summary("carol", ADMIN),
            ext.security_operations_summary(ADMIN),
            ext.extension_summary(ADMIN),
        ]
        return records + views

    def test_tier_null_scan_over_every_record_and_view(self):
        """Tier-null: walking every stored extension record and every derived view finds no tier / cmmc / baseline / fedramp / impact key anywhere."""
        store, ext, ids = stocked_extensions()
        for obj in self._all_records_and_views(ext, ids):
            self.assertEqual(_tier_shaped(_walk_keys(obj)), set())

    def test_no_forbidden_keys_over_every_record_and_view(self):
        """Privacy: walking every stored extension record and every derived view finds no key in the core forbidden set {name, ssn, social_security_number, salary, compensation, pay, dob, date_of_birth, address, phone, email}."""
        store, ext, ids = stocked_extensions()
        for obj in self._all_records_and_views(ext, ids):
            self.assertEqual(_walk_keys(obj) & FORBIDDEN_KEYS, set())

    def test_no_pii_shaped_signature_parameters(self):
        """Privacy: no public HrExtensions method accepts a name-, identifier-, or content-shaped parameter (signature scan over the whole surface)."""
        for attr_name in dir(HrExtensions):
            if attr_name.startswith("_"):
                continue
            member = getattr(HrExtensions, attr_name)
            if not callable(member):
                continue
            params = set(inspect.signature(member).parameters)
            self.assertEqual(params & FORBIDDEN_PARAMS, set(),
                             "%s accepts %s" % (attr_name,
                                                params & FORBIDDEN_PARAMS))
            for param in inspect.signature(member).parameters.values():
                self.assertNotEqual(param.kind,
                                    inspect.Parameter.VAR_KEYWORD,
                                    "%s swallows **kwargs" % attr_name)

    def test_smuggled_pii_kwargs_raise_type_error(self):
        """Privacy: passing email= / phone= / ssn= keyword arguments to extension creates raises TypeError."""
        store, ext = make_extensions()
        with self.assertRaises(TypeError):
            ext.create_expense_report("carol", "Trip", SPECIALIST,
                                      email="carol@example.com")
        with self.assertRaises(TypeError):
            ext.record_time_entry("carol", "proj", "2026-10-06", 60,
                                  SPECIALIST, phone="555-0100")
        with self.assertRaises(TypeError):
            ext.record_access_review("carol", "approved", SPECIALIST,
                                     ssn="000-00-0000")

    def test_rbac_denials(self):
        """RBAC: employees hold no write action on any extension family; the auditor holds no writes either; denials raise PermissionDenied."""
        store, ext = make_extensions()
        with self.assertRaises(PermissionDenied):
            ext.create_payroll_run("2026-10-01", "2026-10-15", EMPLOYEE)
        with self.assertRaises(PermissionDenied):
            ext.create_expense_report("carol", "Trip", EMPLOYEE)
        with self.assertRaises(PermissionDenied):
            ext.record_time_entry("carol", "proj", "2026-10-06", 60, EMPLOYEE)
        with self.assertRaises(PermissionDenied):
            ext.create_communication("announcement", "all", "m-1", AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.register_document("doc-1", "form", AUDITOR)
        with self.assertRaises(PermissionDenied):
            ext.create_federation_record("idp", EMPLOYEE)

    def test_failed_operations_consume_no_id(self):
        """Id discipline: a validation failure and a permission denial allocate nothing — the next successful create takes the first id of its kind."""
        store, ext = make_extensions()
        with self.assertRaises(ValidationError):
            ext.create_payroll_run("2026-10-15", "2026-10-01", SPECIALIST)
        with self.assertRaises(PermissionDenied):
            ext.create_payroll_run("2026-10-01", "2026-10-15", EMPLOYEE)
        run = ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST)
        self.assertEqual(run["id"], "prn-1")
        with self.assertRaises(ValidationError):
            ext.create_expense_report("carol", "", SPECIALIST)
        report = ext.create_expense_report("carol", "Trip", SPECIALIST)
        self.assertEqual(report["id"], "exp-1")

    def test_extension_mutations_audit_on_core_log(self):
        """Audit: successful extension mutations append ext_-prefixed entries to the core store's append-only audit log."""
        store, ext = make_extensions()
        ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST)
        ext.create_communication("announcement", "all-staff", "msg-1",
                                 SPECIALIST)
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("ext_payroll_run_create", actions)
        self.assertIn("ext_communication_create", actions)

    def test_extension_summary_counts(self):
        """Summary: extension_summary counts every family at read over the stocked fixture."""
        store, ext, _ = stocked_extensions()
        summary = ext.extension_summary(ADMIN)
        self.assertEqual(summary["payroll_runs"], 1)
        self.assertEqual(summary["expense_reports"], 1)
        self.assertEqual(summary["time_entries"], 1)
        self.assertEqual(summary["schedule_assignments"], 1)
        self.assertEqual(summary["communications"], 1)
        self.assertEqual(summary["delivery_receipts"], 1)
        self.assertEqual(summary["documents"], 1)
        self.assertEqual(summary["federation_records"], 1)
        self.assertEqual(summary["access_reviews"], 1)
        self.assertEqual(summary["monitoring_reports"], 1)
        self.assertEqual(summary["vulnerability_reports"], 1)
        self.assertEqual(summary["security_incidents"], 1)
        self.assertFalse(summary["stored"])


class TestNegativeControlPayrollNet(unittest.TestCase):
    """Fresh negative control: the payroll net derivation seam."""

    def test_canonical_net_subtracts_deductions(self):
        """Control (canonical): _derive_net_cents(500000, [75000, 25000]) is exactly 400000, deterministically."""
        self.assertEqual(_derive_net_cents(500000, [75000, 25000]), 400000)
        self.assertEqual(_derive_net_cents(500000, [75000, 25000]),
                         _derive_net_cents(500000, [75000, 25000]))
        self.assertEqual(_derive_net_cents(1000, []), 1000)

    def test_mutant_net_is_rejected_by_the_canonical_expectation(self):
        """Control (mutant): with the module seam rebound to ADD deductions, the payroll view reports 600000 — and the canonical expectation (400000) fails against it, proving the suite's net assertions load on the seam."""
        import hr.extensions as extensions_module

        store, ext = make_extensions()
        run = ext.create_payroll_run("2026-10-01", "2026-10-15", SPECIALIST)
        ext.add_pay_statement(
            run["id"], "carol", 500000, SPECIALIST,
            deductions=[{"label": "tax withholding", "amount_cents": 75000},
                        {"label": "benefit election",
                         "amount_cents": 25000}])
        canonical = ext.get_payroll_run(run["id"], SPECIALIST)
        self.assertEqual(canonical["total_net_cents"], 400000)

        original = extensions_module._derive_net_cents
        extensions_module._derive_net_cents = (
            lambda gross, amounts: gross + sum(amounts))
        try:
            mutant = ext.get_payroll_run(run["id"], SPECIALIST)
        finally:
            extensions_module._derive_net_cents = original
        self.assertEqual(mutant["total_net_cents"], 600000)
        self.assertNotEqual(mutant["total_net_cents"],
                            canonical["total_net_cents"])
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant["total_net_cents"], 400000)
        restored = ext.get_payroll_run(run["id"], SPECIALIST)
        self.assertEqual(restored["total_net_cents"], 400000)


if __name__ == "__main__":
    unittest.main()
