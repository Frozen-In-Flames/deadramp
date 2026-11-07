"""Final GAPS batch tests — Group 31, Finance L2.

Pins the extension surface in ``src/finance/extensions.py``
(``FinanceExtensions``, wrapping the core ``FinanceStore``): one
test class per open GAPS.md entry for this group (see ``../BATCH.md``
for the per-entry disposition), plus cross-cutting pins —
``ext_``-prefixed actions and ``:denied`` denials on the core audit
log, stub labels on every reference record, derived-never-stored
values (GRC posture, streaming totals, payroll totals, rollups),
the no-account-identifier shape pins, the no-credit-score recursive
key scan, and the batch's fresh negative control: the disbursement
cap seam ``_check_disbursement_cap``.

Fixtures: ``make_store()`` (a program owned by MEMBER=bob with
VIEWER=carol added as a member) from ``finance_helpers``;
ADMIN=alice/admin (platform admin, not a program member),
OUTSIDER=dave/member (no fixture program).
"""

import unittest

from finance_helpers import (
    ADMIN,
    MEMBER,
    OUTSIDER,
    PERIOD,
    VIEWER,
    make_accrual,
    make_booking,
    make_employee,
    make_request,
    make_store,
    make_traveler,
)

from finance.errors import NotFoundError, PermissionDenied, ValidationError
from finance.extensions import FinanceExtensions, _check_disbursement_cap


def mutant_check(available_cents, committed_cents, amount_cents):
    """The defect under control: the total is summed, never compared."""
    total = committed_cents + amount_cents
    _ = (available_cents, total)
    return True


def mutant_gate(available_cents, committed_cents, amount_cents):
    """The cap gate as the mutant would run it: waves over-cap
    requests through as "within cap" instead of raising."""
    if not mutant_check(available_cents, committed_cents, amount_cents):
        raise ValidationError("disbursement request exceeds earned cap")
    return "within cap"


def all_keys(obj):
    """Every dict key in a record, recursively."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            keys |= all_keys(item)
    return keys


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.ext = FinanceExtensions(self.store)

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def make_employee_with_accrual(self, earned=100000, ref="emp-1"):
        employee = make_employee(self.store, self.program_id, ref=ref)
        accrual = make_accrual(
            self.store, self.program_id, employee["id"], PERIOD, earned
        )
        return employee, accrual

    def make_enrollment(self):
        employee = make_employee(
            self.store, self.program_id, ref="emp-well")
        offering = self.store.create_wellness_offering(
            self.program_id, "Budget Basics", "budgeting", MEMBER
        )
        enrollment = self.store.enroll_participant(
            self.program_id, offering["id"], employee["id"], MEMBER
        )
        return employee, offering, enrollment


class TestDisbursementExecution(BatchFixture):
    """Entry: Instant disbursement execution / payment rails —
    built as execution-REQUEST records capped by the earned cap,
    plus verbatim rail outcome reports. The core records
    disbursements and moves no money; this surface pays nothing."""

    def setUp(self):
        super().setUp()
        self.employee, self.accrual = self.make_employee_with_accrual()
        self.emp_id = self.employee["id"]

    def test_request_record_shape_and_labels(self):
        request = self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 25000, "ach", MEMBER
        )
        self.assertEqual(request["id"], "dexc-1")
        self.assertEqual(
            set(request),
            {
                "id", "program_id", "participant_id", "period",
                "amount_cents", "rail", "paid_here", "state",
                "created_by", "created_utc",
            },
        )
        self.assertIs(request["paid_here"], False)
        self.assertEqual(request["state"], "recorded_request_only")
        self.assertEqual(request["rail"], "ach")
        self.assertEqual(request["amount_cents"], 25000)

    def test_report_stored_verbatim(self):
        self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 25000, "wire", MEMBER
        )
        report = self.ext.record_disbursement_execution_report(
            self.program_id, "dexc-1", "reported_paid", MEMBER,
            detail="rail ref 9f2",
        )
        self.assertEqual(report["id"], "drep-1")
        self.assertEqual(report["outcome"], "reported_paid")
        self.assertEqual(report["detail"], "rail ref 9f2")
        self.assertIs(report["paid_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_disbursement_execution_report(
                self.program_id, "dexc-1", "paid_for_sure", MEMBER
            )

    def test_request_changes_no_core_state(self):
        before = self.store.get_accrual(
            self.program_id, self.accrual["id"], MEMBER)
        self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 25000, "ach", MEMBER
        )
        self.ext.record_disbursement_execution_report(
            self.program_id, "dexc-1", "reported_paid", MEMBER
        )
        self.assertEqual(
            self.store.list_disbursements(self.program_id, MEMBER), [])
        self.assertEqual(
            self.store.list_access_requests(self.program_id, MEMBER), [])
        after = self.store.get_accrual(
            self.program_id, self.accrual["id"], MEMBER)
        self.assertEqual(before, after)

    def test_validation_and_no_id_consumed(self):
        for bad_amount in (100.0, True, "100", 0, -5):
            with self.assertRaises(ValidationError):
                self.ext.request_disbursement_execution(
                    self.program_id, self.emp_id, PERIOD, bad_amount,
                    "ach", MEMBER,
                )
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement_execution(
                self.program_id, self.emp_id, PERIOD, 100, "teleport",
                MEMBER,
            )
        with self.assertRaises(NotFoundError):
            self.ext.request_disbursement_execution(
                self.program_id, "part-99", PERIOD, 100, "ach", MEMBER
            )
        good = self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 100, "ach", MEMBER
        )
        self.assertEqual(good["id"], "dexc-1")

    def test_traveler_and_missing_accrual_rejected(self):
        traveler = make_traveler(self.store, self.program_id)
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement_execution(
                self.program_id, traveler["id"], PERIOD, 100, "ach",
                MEMBER,
            )
        other = make_employee(self.store, self.program_id, ref="emp-2")
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement_execution(
                self.program_id, other["id"], PERIOD, 100, "ach", MEMBER
            )

    def test_core_pending_consumes_available(self):
        """The cap reads the core accrual view: a pending core
        access request of 4000 against 10000 earned leaves 6000
        available to this surface."""
        store2, audit2, pid2 = make_store()
        ext2 = FinanceExtensions(store2)
        employee = make_employee(store2, pid2)
        make_accrual(store2, pid2, employee["id"], PERIOD, 10000)
        make_request(store2, pid2, employee["id"], PERIOD, 4000)
        with self.assertRaises(ValidationError):
            ext2.request_disbursement_execution(
                pid2, employee["id"], PERIOD, 6001, "ach", MEMBER
            )
        good = ext2.request_disbursement_execution(
            pid2, employee["id"], PERIOD, 6000, "ach", MEMBER
        )
        self.assertEqual(good["id"], "dexc-1")

    def test_failed_report_releases_cap_paid_report_does_not(self):
        store2, audit2, pid2 = make_store()
        ext2 = FinanceExtensions(store2)
        employee = make_employee(store2, pid2)
        make_accrual(store2, pid2, employee["id"], PERIOD, 10000)
        ext2.request_disbursement_execution(
            pid2, employee["id"], PERIOD, 6000, "ach", MEMBER)
        ext2.record_disbursement_execution_report(
            pid2, "dexc-1", "reported_failed", MEMBER)
        second = ext2.request_disbursement_execution(
            pid2, employee["id"], PERIOD, 6000, "ach", MEMBER)
        self.assertEqual(second["id"], "dexc-2")
        ext2.record_disbursement_execution_report(
            pid2, "dexc-2", "reported_paid", MEMBER)
        with self.assertRaises(ValidationError):
            ext2.request_disbursement_execution(
                pid2, employee["id"], PERIOD, 5000, "ach", MEMBER)
        third = ext2.request_disbursement_execution(
            pid2, employee["id"], PERIOD, 4000, "ach", MEMBER)
        self.assertEqual(third["id"], "dexc-3")

    def test_summary_derived(self):
        self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 25000, "ach", MEMBER)
        self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 5000, "card", MEMBER)
        self.ext.record_disbursement_execution_report(
            self.program_id, "dexc-1", "reported_paid", MEMBER)
        summary = self.ext.disbursement_execution_summary(
            self.program_id, MEMBER)
        self.assertEqual(summary["requests"], 2)
        self.assertEqual(summary["reports"], 1)
        self.assertEqual(
            summary["reports_by_outcome"]["reported_paid"], 1)
        self.assertEqual(summary["total_requested_cents"], 30000)
        self.assertIs(summary["paid_here"], False)
        self.assertIs(summary["derived"], True)


class TestDisbursementCapNegativeControl(BatchFixture):
    """Fresh negative control for the batch: the disbursement cap
    seam ``_check_disbursement_cap`` in ``finance/extensions.py``.

    Traced claim: **the earned cap is the SI-10 / Core 3 integrity
    boundary of earned-wage access, and it binds this surface's
    disbursement execution requests exactly as it binds core access
    requests** — outstanding requested amounts for a (participant,
    period) never exceed the accrual's derived available amount.
    Each canonical case asserts (1) the real implementation raises
    ValidationError and stores nothing / consumes no id, (2) the
    mutant gate would NOT raise, and (3) treating the mutant's
    outcome as expected fails.
    """

    EARNED = 10000

    def setUp(self):
        super().setUp()
        self.employee, self.accrual = self.make_employee_with_accrual(
            earned=self.EARNED)
        self.emp_id = self.employee["id"]

    def _assert_mutant_rejected(self, mutant_outcome):
        self.assertNotEqual(mutant_outcome, "rejected")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, "rejected")

    def test_single_request_one_cent_over_available(self):
        with self.assertRaises(ValidationError):
            _check_disbursement_cap(self.EARNED, 0, self.EARNED + 1)
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement_execution(
                self.program_id, self.emp_id, PERIOD, self.EARNED + 1,
                "ach", MEMBER,
            )
        self.assertEqual(
            self.ext.list_disbursement_execution_requests(
                self.program_id, MEMBER),
            [],
        )
        mutant_outcome = mutant_gate(self.EARNED, 0, self.EARNED + 1)
        self.assertEqual(mutant_outcome, "within cap")
        self._assert_mutant_rejected(mutant_outcome)
        good = self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 5000, "ach", MEMBER)
        self.assertEqual(good["id"], "dexc-1")

    def test_two_requests_each_within_available_whose_sum_exceeds_it(self):
        first = self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 6000, "ach", MEMBER)
        self.assertEqual(first["id"], "dexc-1")
        with self.assertRaises(ValidationError):
            _check_disbursement_cap(self.EARNED, 6000, 6000)
        with self.assertRaises(ValidationError):
            self.ext.request_disbursement_execution(
                self.program_id, self.emp_id, PERIOD, 6000, "wire",
                MEMBER,
            )
        requests = self.ext.list_disbursement_execution_requests(
            self.program_id, MEMBER)
        self.assertEqual([r["id"] for r in requests], ["dexc-1"])
        mutant_outcome = mutant_gate(self.EARNED, 6000, 6000)
        self.assertEqual(mutant_outcome, "within cap")
        self._assert_mutant_rejected(mutant_outcome)
        good = self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, 4000, "wire", MEMBER)
        self.assertEqual(good["id"], "dexc-2")

    def test_request_exactly_at_cap_passes_both(self):
        _check_disbursement_cap(self.EARNED, 0, self.EARNED)
        request = self.ext.request_disbursement_execution(
            self.program_id, self.emp_id, PERIOD, self.EARNED, "ach",
            MEMBER,
        )
        self.assertEqual(request["id"], "dexc-1")
        self.assertTrue(mutant_check(self.EARNED, 0, self.EARNED))
        self.assertEqual(
            mutant_gate(self.EARNED, 0, self.EARNED), "within cap")

    def test_mutant_is_weakened_not_broken(self):
        """Within-cap input passes both gates — the mutant is a
        weakened gate, not a broken one."""
        _check_disbursement_cap(self.EARNED, 1000, 5000)
        self.assertTrue(mutant_check(self.EARNED, 1000, 5000))
        self.assertEqual(
            mutant_gate(self.EARNED, 1000, 5000), "within cap")


class TestBookingExecution(BatchFixture):
    """Entry: Travel booking execution engines — built as
    execution-REQUEST records against existing core bookings plus
    verbatim outcome reports. The core holds booking records only;
    this surface books nothing and issues no ticket."""

    def setUp(self):
        super().setUp()
        self.traveler = make_traveler(self.store, self.program_id)
        self.booking = make_booking(
            self.store, self.program_id, self.traveler["id"])

    def test_request_record_shape_and_labels(self):
        request = self.ext.request_booking_execution(
            self.program_id, self.booking["id"], "ticket_issue", MEMBER)
        self.assertEqual(request["id"], "bexc-1")
        self.assertEqual(
            set(request),
            {
                "id", "program_id", "booking_id", "participant_id",
                "action_label", "booked_here", "ticketed_here",
                "state", "created_by", "created_utc",
            },
        )
        self.assertEqual(request["participant_id"], self.traveler["id"])
        self.assertIs(request["booked_here"], False)
        self.assertIs(request["ticketed_here"], False)
        self.assertEqual(request["state"], "recorded_request_only")

    def test_report_verbatim_and_core_booking_untouched(self):
        before = self.store.get_booking(
            self.program_id, self.booking["id"], MEMBER)
        self.ext.request_booking_execution(
            self.program_id, self.booking["id"], "ticket_issue", MEMBER)
        report = self.ext.record_booking_execution_report(
            self.program_id, "bexc-1", "reported_ticketed", MEMBER,
            detail="pnr XYZ123",
        )
        self.assertEqual(report["outcome"], "reported_ticketed")
        self.assertEqual(report["detail"], "pnr XYZ123")
        self.assertIs(report["booked_here"], False)
        self.assertIs(report["ticketed_here"], False)
        after = self.store.get_booking(
            self.program_id, self.booking["id"], MEMBER)
        self.assertEqual(before, after)
        self.assertEqual(after["status"], "recorded")

    def test_unknown_booking_rejected_and_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.request_booking_execution(
                self.program_id, "bkg-99", "ticket_issue", MEMBER)
        request = self.ext.request_booking_execution(
            self.program_id, self.booking["id"], "ticket_issue", MEMBER)
        self.assertEqual(request["id"], "bexc-1")

    def test_bad_action_and_bad_outcome_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.request_booking_execution(
                self.program_id, self.booking["id"], "fly_it", MEMBER)
        self.ext.request_booking_execution(
            self.program_id, self.booking["id"], "inventory_hold",
            MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_booking_execution_report(
                self.program_id, "bexc-1", "all_booked", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_booking_execution_report(
                self.program_id, "bexc-99", "reported_booked", MEMBER)

    def test_list_filter_by_booking(self):
        self.ext.request_booking_execution(
            self.program_id, self.booking["id"], "inventory_hold",
            MEMBER)
        other = make_booking(
            self.store, self.program_id, self.traveler["id"],
            kind="hotel",
        )
        self.ext.request_booking_execution(
            self.program_id, other["id"], "reservation_confirm", MEMBER)
        filtered = self.ext.list_booking_execution_requests(
            self.program_id, MEMBER, booking_id=self.booking["id"])
        self.assertEqual([r["id"] for r in filtered], ["bexc-1"])
        self.assertEqual(
            len(self.ext.list_booking_execution_requests(
                self.program_id, MEMBER)),
            2,
        )


class TestWellnessDelivery(BatchFixture):
    """Entry: Financial wellness delivery tools — built as session
    records over core enrollments plus verbatim outcome reports.
    Content is delivered by others; nothing is delivered here."""

    def setUp(self):
        super().setUp()
        self.employee, self.offering, self.enrollment = (
            self.make_enrollment())

    def test_session_record_shape_and_labels(self):
        session = self.ext.schedule_wellness_session(
            self.program_id, self.enrollment["id"], "week-1-budgeting",
            MEMBER,
        )
        self.assertEqual(session["id"], "wses-1")
        self.assertEqual(session["offering_id"], self.offering["id"])
        self.assertEqual(session["participant_id"], self.employee["id"])
        self.assertIs(session["delivered_here"], False)
        self.assertEqual(session["state"], "scheduled_record_only")

    def test_unknown_enrollment_rejected_and_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ext.schedule_wellness_session(
                self.program_id, "enr-99", "week-1", MEMBER)
        session = self.ext.schedule_wellness_session(
            self.program_id, self.enrollment["id"], "week-1", MEMBER)
        self.assertEqual(session["id"], "wses-1")

    def test_report_verbatim_and_enrollment_untouched(self):
        self.ext.schedule_wellness_session(
            self.program_id, self.enrollment["id"], "week-1", MEMBER)
        report = self.ext.record_wellness_session_report(
            self.program_id, "wses-1", "reported_completed", MEMBER)
        self.assertEqual(report["outcome"], "reported_completed")
        self.assertIs(report["delivered_here"], False)
        enrollments = self.store.list_wellness_enrollments(
            self.program_id, MEMBER)
        self.assertEqual(len(enrollments), 1)
        self.assertEqual(enrollments[0]["status"], "enrolled")
        with self.assertRaises(ValidationError):
            self.ext.record_wellness_session_report(
                self.program_id, "wses-1", "delivered_great", MEMBER)

    def test_summary_derived(self):
        self.ext.schedule_wellness_session(
            self.program_id, self.enrollment["id"], "week-1", MEMBER)
        self.ext.schedule_wellness_session(
            self.program_id, self.enrollment["id"], "week-2", MEMBER)
        self.ext.record_wellness_session_report(
            self.program_id, "wses-1", "reported_attended", MEMBER)
        summary = self.ext.wellness_delivery_summary(
            self.program_id, MEMBER)
        self.assertEqual(summary["sessions"], 2)
        self.assertEqual(summary["reports"], 1)
        self.assertEqual(
            summary["reports_by_outcome"]["reported_attended"], 1)
        self.assertIs(summary["delivered_here"], False)


class TestLending(BatchFixture):
    """Entry: Lending & credit engines (0 claims) — built as
    application records plus verbatim reported decisions. No
    underwriting is computed, no decision is made here, nothing is
    disbursed, and no record carries a credit score field. The
    founding line stands: access is to already-earned wages only."""

    def setUp(self):
        super().setUp()
        self.employee = make_employee(self.store, self.program_id)

    def test_application_record_shape_and_labels(self):
        application = self.ext.create_loan_application(
            self.program_id, self.employee["id"], 50000,
            "equipment purchase", MEMBER,
        )
        self.assertEqual(application["id"], "loan-1")
        self.assertEqual(
            set(application),
            {
                "id", "program_id", "participant_id", "amount_cents",
                "purpose_label", "disbursed_here",
                "underwriting_computed_here", "state", "created_by",
                "created_utc",
            },
        )
        self.assertIs(application["disbursed_here"], False)
        self.assertIs(application["underwriting_computed_here"], False)
        self.assertEqual(application["state"], "recorded_application_only")

    def test_decision_stored_verbatim_and_application_untouched(self):
        application = self.ext.create_loan_application(
            self.program_id, self.employee["id"], 50000, "equipment",
            MEMBER,
        )
        before = self.ext.get_loan_application(
            self.program_id, "loan-1", MEMBER)
        self.assertEqual(before, application)
        report = self.ext.record_loan_decision_report(
            self.program_id, "loan-1",
            "approved by external lender, file 77", MEMBER,
        )
        self.assertEqual(
            report["decision_label"], "approved by external lender, file 77")
        self.assertIs(report["decided_here"], False)
        self.assertIs(report["disbursed_here"], False)
        after = self.ext.get_loan_application(
            self.program_id, "loan-1", MEMBER)
        self.assertEqual(before, after)

    def test_money_boundary_and_no_id_consumed(self):
        for bad_amount in (100.5, True, "100", 0, -1):
            with self.assertRaises(ValidationError):
                self.ext.create_loan_application(
                    self.program_id, self.employee["id"], bad_amount,
                    "equipment", MEMBER,
                )
        good = self.ext.create_loan_application(
            self.program_id, self.employee["id"], 100, "equipment",
            MEMBER,
        )
        self.assertEqual(good["id"], "loan-1")

    def test_unknown_participant_and_empty_decision_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_loan_application(
                self.program_id, "part-99", 100, "equipment", MEMBER)
        self.ext.create_loan_application(
            self.program_id, self.employee["id"], 100, "equipment",
            MEMBER,
        )
        with self.assertRaises(ValidationError):
            self.ext.record_loan_decision_report(
                self.program_id, "loan-1", "  ", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_loan_decision_report(
                self.program_id, "loan-99", "denied", MEMBER)

    def test_application_is_not_capped_by_earned_wages(self):
        """The registry evaluates nothing: an application larger
        than any accrual is still only a record (nothing is
        disbursed against it), while wage access itself stays
        capped by the core. This pins that the lending registry
        creates no credit against earned wages."""
        make_accrual(
            self.store, self.program_id, self.employee["id"], PERIOD,
            5000,
        )
        application = self.ext.create_loan_application(
            self.program_id, self.employee["id"], 999999, "equipment",
            MEMBER,
        )
        self.assertEqual(application["amount_cents"], 999999)
        self.assertIs(application["disbursed_here"], False)

    def test_no_credit_score_field_anywhere(self):
        self.ext.create_loan_application(
            self.program_id, self.employee["id"], 50000, "equipment",
            MEMBER,
        )
        self.ext.record_loan_decision_report(
            self.program_id, "loan-1", "denied by external lender",
            MEMBER,
        )
        records = (
            self.ext.list_loan_applications(self.program_id, MEMBER)
            + self.ext.list_loan_decision_reports(
                self.program_id, MEMBER)
        )
        for record in records:
            for key in all_keys(record):
                self.assertNotIn("score", key.lower())
                self.assertNotIn("credit_rating", key.lower())


class TestTrading(BatchFixture):
    """Entry: Trading & investment execution (0 claims) — built as
    order records plus verbatim execution reports. Nothing is
    executed, priced, or settled here."""

    def setUp(self):
        super().setUp()
        self.employee = make_employee(self.store, self.program_id)

    def test_order_record_shape_and_labels(self):
        order = self.ext.create_trade_order(
            self.program_id, self.employee["id"], "instrument-xyz",
            "buy", 12500, MEMBER,
        )
        self.assertEqual(order["id"], "tord-1")
        self.assertIs(order["executed_here"], False)
        self.assertEqual(order["state"], "recorded_order_only")
        self.assertEqual(order["instrument_ref"], "instrument-xyz")

    def test_report_verbatim_and_order_untouched(self):
        self.ext.create_trade_order(
            self.program_id, self.employee["id"], "instrument-xyz",
            "sell", 12500, MEMBER,
        )
        before = self.ext.get_trade_order(
            self.program_id, "tord-1", MEMBER)
        report = self.ext.record_trade_execution_report(
            self.program_id, "tord-1", "reported_executed", MEMBER)
        self.assertEqual(report["outcome"], "reported_executed")
        self.assertIs(report["executed_here"], False)
        after = self.ext.get_trade_order(
            self.program_id, "tord-1", MEMBER)
        self.assertEqual(before, after)

    def test_validation_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_trade_order(
                self.program_id, self.employee["id"], "instrument-xyz",
                "hold", 100, MEMBER,
            )
        with self.assertRaises(ValidationError):
            self.ext.create_trade_order(
                self.program_id, self.employee["id"], "instrument-xyz",
                "buy", 10.5, MEMBER,
            )
        with self.assertRaises(NotFoundError):
            self.ext.create_trade_order(
                self.program_id, "part-99", "instrument-xyz", "buy",
                100, MEMBER,
            )
        good = self.ext.create_trade_order(
            self.program_id, self.employee["id"], "instrument-xyz",
            "buy", 100, MEMBER,
        )
        self.assertEqual(good["id"], "tord-1")


class TestTax(BatchFixture):
    """Entry: Tax reporting & remittance (0 claims) — built as
    preparation records plus verbatim filing reports. Nothing is
    filed and nothing is remitted here."""

    def setUp(self):
        super().setUp()
        self.employee = make_employee(self.store, self.program_id)

    def test_preparation_record_shape_and_labels(self):
        preparation = self.ext.create_tax_preparation(
            self.program_id, self.employee["id"], PERIOD,
            "wage-reporting", 0, MEMBER,
        )
        self.assertEqual(preparation["id"], "tax-1")
        self.assertIs(preparation["filed_here"], False)
        self.assertIs(preparation["remitted_here"], False)
        self.assertEqual(
            preparation["state"], "recorded_preparation_only")
        self.assertEqual(preparation["amount_cents"], 0)

    def test_report_verbatim(self):
        self.ext.create_tax_preparation(
            self.program_id, self.employee["id"], PERIOD,
            "wage-reporting", 4200, MEMBER,
        )
        report = self.ext.record_tax_filing_report(
            self.program_id, "tax-1", "reported_filed", MEMBER)
        self.assertEqual(report["outcome"], "reported_filed")
        self.assertIs(report["filed_here"], False)
        self.assertIs(report["remitted_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_tax_filing_report(
                self.program_id, "tax-1", "filed_by_us", MEMBER)

    def test_validation_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_tax_preparation(
                self.program_id, self.employee["id"], "2026-13",
                "wage-reporting", 100, MEMBER,
            )
        with self.assertRaises(ValidationError):
            self.ext.create_tax_preparation(
                self.program_id, self.employee["id"], PERIOD,
                "wage-reporting", 1.5, MEMBER,
            )
        with self.assertRaises(ValidationError):
            self.ext.create_tax_preparation(
                self.program_id, self.employee["id"], PERIOD,
                "wage-reporting", -1, MEMBER,
            )
        good = self.ext.create_tax_preparation(
            self.program_id, self.employee["id"], PERIOD,
            "wage-reporting", 100, MEMBER,
        )
        self.assertEqual(good["id"], "tax-1")


class TestGrcPlatform(BatchFixture):
    """Entry: GRC platform functions (0 claims in text; source
    category label only) — built as framework/control records and
    mappings to existing core records; posture is counts derived
    at read. Registering a label asserts no compliance."""

    def test_framework_and_control_shapes(self):
        framework = self.ext.register_framework(
            self.program_id, "operator-framework", MEMBER,
            version_label="v1",
        )
        self.assertEqual(framework["id"], "gfw-1")
        self.assertIs(framework["compliance_asserted"], False)
        control = self.ext.register_control(
            self.program_id, "gfw-1", "AC-2", "Account management",
            MEMBER,
        )
        self.assertEqual(control["id"], "gctl-1")
        self.assertEqual(control["framework_id"], "gfw-1")
        self.assertIs(control["compliance_asserted"], False)
        with self.assertRaises(NotFoundError):
            self.ext.register_control(
                self.program_id, "gfw-99", "AC-3", "Access", MEMBER)

    def test_mapping_requires_existing_ends(self):
        employee = make_employee(self.store, self.program_id)
        self.ext.register_framework(self.program_id, "fw", MEMBER)
        self.ext.register_control(
            self.program_id, "gfw-1", "AC-2", "Accounts", MEMBER)
        mapping = self.ext.map_record_to_control(
            self.program_id, "gctl-1", "participant", employee["id"],
            MEMBER,
        )
        self.assertEqual(mapping["id"], "gmap-1")
        self.assertIs(mapping["compliance_asserted"], False)
        with self.assertRaises(NotFoundError):
            self.ext.map_record_to_control(
                self.program_id, "gctl-1", "participant", "part-99",
                MEMBER,
            )
        with self.assertRaises(ValidationError):
            self.ext.map_record_to_control(
                self.program_id, "gctl-1", "spaceship", employee["id"],
                MEMBER,
            )

    def test_posture_counts_derived(self):
        employee = make_employee(self.store, self.program_id)
        traveler = make_traveler(self.store, self.program_id)
        booking = make_booking(
            self.store, self.program_id, traveler["id"])
        self.ext.register_framework(self.program_id, "fw", MEMBER)
        self.ext.register_control(
            self.program_id, "gfw-1", "AC-2", "Accounts", MEMBER)
        self.ext.register_control(
            self.program_id, "gfw-1", "AU-2", "Audit events", MEMBER)
        self.ext.map_record_to_control(
            self.program_id, "gctl-1", "participant", employee["id"],
            MEMBER,
        )
        self.ext.map_record_to_control(
            self.program_id, "gctl-2", "booking", booking["id"],
            MEMBER,
        )
        posture = self.ext.framework_posture(self.program_id, MEMBER)
        self.assertEqual(posture["frameworks"], 1)
        self.assertEqual(posture["controls"], 2)
        self.assertEqual(posture["mappings"], 2)
        self.assertEqual(
            posture["mappings_by_record_kind"]["participant"], 1)
        self.assertEqual(posture["mappings_by_record_kind"]["booking"], 1)
        self.assertEqual(posture["mappings_by_record_kind"]["accrual"], 0)
        self.assertIs(posture["compliance_asserted"], False)
        self.assertIs(posture["derived"], True)
        for key in posture:
            self.assertNotIn("score", key.lower())

    def test_stored_records_carry_no_derived_key(self):
        framework = self.ext.register_framework(
            self.program_id, "fw", MEMBER)
        self.assertEqual(
            set(framework),
            {
                "id", "program_id", "name", "version_label",
                "compliance_asserted", "created_by", "created_utc",
            },
        )


class TestStreamingStub(BatchFixture):
    """Entry: Streaming / real-time reporting pipelines (stub) —
    labeled reference records: stream registrations and receipts
    with counts as reported. Core reporting is computed on read;
    nothing is streamed here."""

    def test_stream_record_shape_and_labels(self):
        stream = self.ext.register_reporting_stream(
            self.program_id, "summary-feed", MEMBER)
        self.assertEqual(stream["id"], "strm-1")
        self.assertEqual(
            set(stream),
            {
                "id", "program_id", "stream_ref", "reference_stub",
                "streamed_here", "created_by", "created_utc",
            },
        )
        self.assertIs(stream["reference_stub"], True)
        self.assertIs(stream["streamed_here"], False)

    def test_receipt_labels_and_counts(self):
        self.ext.register_reporting_stream(
            self.program_id, "summary-feed", MEMBER)
        receipt = self.ext.record_stream_receipt(
            self.program_id, "strm-1", 42, MEMBER)
        self.assertEqual(receipt["id"], "strc-1")
        self.assertIs(receipt["reference_stub"], True)
        self.assertIs(receipt["reference_transport"], True)
        self.assertIs(receipt["streamed_here"], False)
        self.assertEqual(receipt["events_reported"], 42)

    def test_receipt_validation_and_no_id_consumed(self):
        self.ext.register_reporting_stream(
            self.program_id, "summary-feed", MEMBER)
        for bad_count in (1.5, True, -1, "42"):
            with self.assertRaises(ValidationError):
                self.ext.record_stream_receipt(
                    self.program_id, "strm-1", bad_count, MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_stream_receipt(
                self.program_id, "strm-99", 1, MEMBER)
        good = self.ext.record_stream_receipt(
            self.program_id, "strm-1", 1, MEMBER)
        self.assertEqual(good["id"], "strc-1")

    def test_summary_derived_and_core_untouched(self):
        before = self.store.program_summary(
            self.program_id, PERIOD, MEMBER)
        self.ext.register_reporting_stream(
            self.program_id, "summary-feed", MEMBER)
        self.ext.record_stream_receipt(self.program_id, "strm-1", 10, MEMBER)
        self.ext.record_stream_receipt(self.program_id, "strm-1", 5, MEMBER)
        summary = self.ext.streaming_summary(self.program_id, MEMBER)
        self.assertEqual(summary["streams"], 1)
        self.assertEqual(summary["receipts"], 2)
        self.assertEqual(summary["total_events_reported"], 15)
        self.assertIs(summary["streamed_here"], False)
        after = self.store.program_summary(self.program_id, PERIOD, MEMBER)
        self.assertEqual(before, after)


class TestBankingStub(BatchFixture):
    """Entry: Banking integration & account verification (stub;
    0 claims) — labeled reference records: verification requests
    naming a core participant and a method label, plus reported
    outcome labels. Entity shapes forbid real account identifiers
    by design: the exact key sets are pinned and no field can hold
    an account identifier."""

    def setUp(self):
        super().setUp()
        self.employee = make_employee(self.store, self.program_id)

    def test_request_exact_key_set_and_labels(self):
        request = self.ext.record_verification_request(
            self.program_id, self.employee["id"], "external-bank-check",
            MEMBER,
        )
        self.assertEqual(request["id"], "bver-1")
        self.assertEqual(
            set(request),
            {
                "id", "program_id", "participant_id", "method_label",
                "reference_stub", "verified_here", "created_by",
                "created_utc",
            },
        )
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["verified_here"], False)

    def test_report_exact_key_set_and_verbatim_outcome(self):
        self.ext.record_verification_request(
            self.program_id, self.employee["id"], "external-bank-check",
            MEMBER,
        )
        report = self.ext.record_verification_report(
            self.program_id, "bver-1", "reported_verified", MEMBER)
        self.assertEqual(
            set(report),
            {
                "id", "program_id", "verification_id", "outcome",
                "detail", "reference_stub", "verified_here",
                "created_by", "created_utc",
            },
        )
        self.assertEqual(report["outcome"], "reported_verified")
        self.assertIs(report["verified_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_verification_report(
                self.program_id, "bver-1", "verified_by_us", MEMBER)

    def test_no_account_identifier_field_anywhere(self):
        self.ext.record_verification_request(
            self.program_id, self.employee["id"], "external-bank-check",
            MEMBER,
        )
        self.ext.record_verification_report(
            self.program_id, "bver-1", "reported_pending", MEMBER)
        records = (
            self.ext.list_verification_requests(self.program_id, MEMBER)
            + self.ext.list_verification_reports(
                self.program_id, MEMBER)
        )
        forbidden = ("account", "routing", "iban", "sort_code",
                     "card_number")
        for record in records:
            for key in all_keys(record):
                for fragment in forbidden:
                    self.assertNotIn(fragment, key.lower())

    def test_unknown_participant_and_core_shape_untouched(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_verification_request(
                self.program_id, "part-99", "external-bank-check",
                MEMBER,
            )
        self.ext.record_verification_request(
            self.program_id, self.employee["id"], "external-bank-check",
            MEMBER,
        )
        participant = self.store.get_participant(
            self.program_id, self.employee["id"], MEMBER)
        self.assertEqual(
            set(participant),
            {
                "id", "program_id", "ref", "kind", "status",
                "created_by", "created_utc",
            },
        )


class TestPayrollStub(BatchFixture):
    """Entry: Payroll system integration & wage calculation (stub;
    0 claims) — labeled reference records: sync receipts with
    counts as reported. Accruals record amounts computed
    elsewhere; no wage amount is computed or held here."""

    def test_sync_exact_key_set_and_labels(self):
        sync = self.ext.record_payroll_sync(
            self.program_id, "payroll-system-a", PERIOD, 12, 12, MEMBER)
        self.assertEqual(sync["id"], "psyn-1")
        self.assertEqual(
            set(sync),
            {
                "id", "program_id", "source_ref", "period",
                "participants_reported", "accruals_reported",
                "reference_stub", "computed_here", "created_by",
                "created_utc",
            },
        )
        self.assertIs(sync["reference_stub"], True)
        self.assertIs(sync["computed_here"], False)
        for key in sync:
            self.assertFalse(key.endswith("_cents"))

    def test_sync_validation_and_no_id_consumed(self):
        for bad_count in (1.5, True, -1, "12"):
            with self.assertRaises(ValidationError):
                self.ext.record_payroll_sync(
                    self.program_id, "payroll-system-a", PERIOD,
                    bad_count, 0, MEMBER,
                )
        with self.assertRaises(ValidationError):
            self.ext.record_payroll_sync(
                self.program_id, "payroll-system-a", "2026-13", 1, 1,
                MEMBER,
            )
        good = self.ext.record_payroll_sync(
            self.program_id, "payroll-system-a", PERIOD, 1, 1, MEMBER)
        self.assertEqual(good["id"], "psyn-1")

    def test_summary_derived_and_no_accrual_created(self):
        employee, accrual = self.make_employee_with_accrual()
        self.ext.record_payroll_sync(
            self.program_id, "payroll-system-a", PERIOD, 3, 2, MEMBER)
        self.ext.record_payroll_sync(
            self.program_id, "payroll-system-a", PERIOD, 4, 1, MEMBER)
        summary = self.ext.payroll_sync_summary(self.program_id, MEMBER)
        self.assertEqual(summary["syncs"], 2)
        self.assertEqual(summary["total_participants_reported"], 7)
        self.assertEqual(summary["total_accruals_reported"], 3)
        self.assertIs(summary["computed_here"], False)
        accruals = self.store.list_accruals(self.program_id, MEMBER)
        self.assertEqual(len(accruals), 1)
        self.assertEqual(accruals[0]["earned_cents"], 100000)


class TestCrossCutting(BatchFixture):
    """Cross-cutting batch pins: RBAC + membership on the extension
    surface, ext_ audit actions with :denied denials, platform-admin
    reach, audit-failure rollback, program scoping, and the
    recursive forbidden-key scan across one record of every kind."""

    def test_viewer_write_denied_and_audited(self):
        employee, accrual = self.make_employee_with_accrual()
        with self.assertRaises(PermissionDenied):
            self.ext.request_disbursement_execution(
                self.program_id, employee["id"], PERIOD, 100, "ach",
                VIEWER,
            )
        self.assertIn(
            "ext_disbursement_execution_request:denied",
            self.audit_actions(),
        )
        self.assertEqual(
            self.ext.list_disbursement_execution_requests(
                self.program_id, MEMBER),
            [],
        )

    def test_outsider_denied_by_membership(self):
        employee = make_employee(self.store, self.program_id)
        with self.assertRaises(PermissionDenied):
            self.ext.create_loan_application(
                self.program_id, employee["id"], 100, "equipment",
                OUTSIDER,
            )
        self.assertEqual(
            self.ext.list_loan_applications(self.program_id, MEMBER),
            [],
        )

    def test_admin_reaches_program_and_audit_records_ext_actions(self):
        framework = self.ext.register_framework(
            self.program_id, "fw", ADMIN)
        self.assertEqual(framework["id"], "gfw-1")
        self.assertIn("ext_framework_register", self.audit_actions())

    def test_cross_program_records_not_visible(self):
        other = self.store.create_program("other-program", MEMBER)
        framework = self.ext.register_framework(
            self.program_id, "fw", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_framework(other["id"], framework["id"], MEMBER)
        self.assertEqual(self.ext.list_frameworks(other["id"], MEMBER), [])

    def test_audit_failure_rolls_back_record_and_id(self):
        class Boom:
            def record(self, *args, **kwargs):
                raise RuntimeError("audit unavailable")

        real_audit = self.store.audit
        self.store.audit = Boom()
        try:
            with self.assertRaises(RuntimeError):
                self.ext.register_framework(self.program_id, "fw", MEMBER)
        finally:
            self.store.audit = real_audit
        self.assertEqual(self.ext.list_frameworks(self.program_id, MEMBER), [])
        framework = self.ext.register_framework(
            self.program_id, "fw", MEMBER)
        self.assertEqual(framework["id"], "gfw-1")

    def test_forbidden_keys_absent_across_all_kinds(self):
        employee, accrual = self.make_employee_with_accrual()
        traveler = make_traveler(self.store, self.program_id)
        booking = make_booking(
            self.store, self.program_id, traveler["id"])
        _, _, enrollment = self.make_enrollment()
        self.ext.request_disbursement_execution(
            self.program_id, employee["id"], PERIOD, 100, "ach", MEMBER)
        self.ext.record_disbursement_execution_report(
            self.program_id, "dexc-1", "reported_pending", MEMBER)
        self.ext.request_booking_execution(
            self.program_id, booking["id"], "inventory_hold", MEMBER)
        self.ext.schedule_wellness_session(
            self.program_id, enrollment["id"], "week-1", MEMBER)
        self.ext.create_loan_application(
            self.program_id, employee["id"], 100, "equipment", MEMBER)
        self.ext.create_trade_order(
            self.program_id, employee["id"], "instrument-xyz", "buy",
            100, MEMBER,
        )
        self.ext.create_tax_preparation(
            self.program_id, employee["id"], PERIOD, "wage-reporting",
            100, MEMBER,
        )
        self.ext.register_framework(self.program_id, "fw", MEMBER)
        self.ext.register_reporting_stream(
            self.program_id, "summary-feed", MEMBER)
        self.ext.record_verification_request(
            self.program_id, employee["id"], "external-bank-check",
            MEMBER,
        )
        self.ext.record_payroll_sync(
            self.program_id, "payroll-system-a", PERIOD, 1, 1, MEMBER)
        pid = self.program_id
        records = (
            self.ext.list_disbursement_execution_requests(pid, MEMBER)
            + self.ext.list_disbursement_execution_reports(pid, MEMBER)
            + self.ext.list_booking_execution_requests(pid, MEMBER)
            + self.ext.list_wellness_sessions(pid, MEMBER)
            + self.ext.list_loan_applications(pid, MEMBER)
            + self.ext.list_trade_orders(pid, MEMBER)
            + self.ext.list_tax_preparations(pid, MEMBER)
            + self.ext.list_frameworks(pid, MEMBER)
            + self.ext.list_reporting_streams(pid, MEMBER)
            + self.ext.list_verification_requests(pid, MEMBER)
            + self.ext.list_payroll_syncs(pid, MEMBER)
        )
        self.assertEqual(len(records), 11)
        forbidden = ("score", "account", "routing", "iban",
                     "sort_code", "card_number")
        for record in records:
            for key in all_keys(record):
                for fragment in forbidden:
                    self.assertNotIn(fragment, key.lower())
        stub_records = (
            self.ext.list_reporting_streams(pid, MEMBER)
            + self.ext.list_verification_requests(pid, MEMBER)
            + self.ext.list_payroll_syncs(pid, MEMBER)
        )
        for record in stub_records:
            self.assertIs(record["reference_stub"], True)


if __name__ == "__main__":
    unittest.main()
