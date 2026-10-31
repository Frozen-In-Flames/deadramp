"""Earned-wage accrual, access-request, and disbursement tests.

Traces to: UNION-SPEC Core function 3 (Earned-wage accrual & access
records — the earned-cap invariant) and Core function 8 (Workflow &
approvals — requested -> approved/denied, approved -> disbursed via a
disbursement record, requested/denied -> void, separation of duties);
Implementation contract for ``finance/store.py`` accrual / access /
disbursement methods; control families SI-10 (integer cents, validation
before mutation) and AC-5 (the decider is never the creator).
"""

import unittest

from finance_helpers import (
    ADMIN,
    DATE_JAN,
    MEMBER,
    OUTSIDER,
    PERIOD,
    PERIOD_OTHER,
    VIEWER,
    approved_request,
    make_accrual,
    make_employee,
    make_request,
    make_store,
    make_traveler,
)
from finance.errors import NotFoundError, PermissionDenied, ValidationError

ACCRUAL_KEYS = {
    "id", "program_id", "participant_id", "period", "earned_cents",
    "created_by", "created_utc",
}
REQUEST_KEYS = {
    "id", "program_id", "participant_id", "period", "amount_cents",
    "date", "status", "created_by", "created_utc", "decided_by",
    "decided_utc", "disbursement_id",
}
DISBURSEMENT_KEYS = {
    "id", "program_id", "request_id", "participant_id", "period",
    "amount_cents", "date", "method", "recorded_by", "recorded_utc",
}


class EarnedWageBase(unittest.TestCase):
    """A canonical program with one employee and one traveler."""

    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.employee = make_employee(self.store, self.program_id)
        self.traveler = make_traveler(self.store, self.program_id)
        self.emp_id = self.employee["id"]
        self.trav_id = self.traveler["id"]


class TestAccruals(EarnedWageBase):
    """Core 3: Earned-wage accrual — shape and validation."""

    def test_record_accrual_returns_the_contract_dict(self):
        """Core 3: Earned-wage accrual. Contract: record_accrual
        returns {id, program_id, participant_id, period,
        earned_cents, created_by, created_utc} with the acc- prefix."""
        accrual = make_accrual(self.store, self.program_id, self.emp_id)
        self.assertEqual(set(accrual.keys()), ACCRUAL_KEYS)
        self.assertEqual(accrual["id"], "acc-1")
        self.assertEqual(accrual["program_id"], self.program_id)
        self.assertEqual(accrual["participant_id"], self.emp_id)
        self.assertEqual(accrual["period"], PERIOD)
        self.assertEqual(accrual["earned_cents"], 100000)
        self.assertEqual(accrual["created_by"], "bob")

    def test_accrual_ids_are_sequential(self):
        """Core 3: Earned-wage accrual. Contract: ids are sequential
        per object type with the acc- prefix."""
        other = make_employee(self.store, self.program_id, ref="emp-2")
        first = make_accrual(self.store, self.program_id, self.emp_id)
        second = make_accrual(self.store, self.program_id, other["id"])
        self.assertEqual([first["id"], second["id"]], ["acc-1", "acc-2"])

    def test_zero_earned_is_accepted(self):
        """Core 3: Earned-wage accrual. earned_cents is an int >= 0,
        so zero is valid."""
        accrual = make_accrual(
            self.store, self.program_id, self.emp_id, earned_cents=0
        )
        self.assertEqual(accrual["earned_cents"], 0)

    def test_float_or_bool_earned_is_a_validation_error(self):
        """Core 3: Earned-wage accrual (SI-10). Contract: any amount
        that is not an int (booleans included, floats even when
        integral) raises ValidationError."""
        for bad in (100.0, 100.5, True, False, "10000"):
            with self.subTest(earned=bad):
                with self.assertRaises(ValidationError):
                    make_accrual(
                        self.store, self.program_id, self.emp_id,
                        earned_cents=bad,
                    )
        self.assertEqual(self.store.list_accruals(self.program_id, MEMBER), [])

    def test_negative_earned_is_a_validation_error(self):
        """Core 3: Earned-wage accrual (SI-10). earned_cents must be
        >= 0."""
        with self.assertRaises(ValidationError):
            make_accrual(
                self.store, self.program_id, self.emp_id, earned_cents=-1
            )

    def test_duplicate_participant_period_accrual_is_a_validation_error(self):
        """Core 3: Earned-wage accrual. Contract: 'a second accrual
        for the same (participant, period) -> ValidationError'."""
        make_accrual(self.store, self.program_id, self.emp_id, PERIOD, 100000)
        with self.assertRaises(ValidationError):
            make_accrual(self.store, self.program_id, self.emp_id, PERIOD, 5000)
        accruals = self.store.list_accruals(self.program_id, MEMBER)
        self.assertEqual(len(accruals), 1)
        self.assertEqual(accruals[0]["earned_cents"], 100000)

    def test_same_period_for_another_participant_and_other_period_ok(self):
        """Core 3: Earned-wage accrual. Uniqueness is per (participant,
        period): another participant in the same period, and the same
        participant in another period, are both accepted."""
        other = make_employee(self.store, self.program_id, ref="emp-2")
        make_accrual(self.store, self.program_id, self.emp_id, PERIOD, 100000)
        make_accrual(self.store, self.program_id, other["id"], PERIOD, 50000)
        feb = make_accrual(
            self.store, self.program_id, self.emp_id, PERIOD_OTHER, 70000
        )
        self.assertEqual(feb["period"], PERIOD_OTHER)

    def test_accrual_for_traveler_is_a_validation_error(self):
        """Core 3: Earned-wage accrual. Contract: the participant must
        be of kind employee (a traveler accrual -> ValidationError)."""
        with self.assertRaises(ValidationError):
            make_accrual(self.store, self.program_id, self.trav_id)

    def test_accrual_for_unknown_participant_is_not_found(self):
        """Core 3: Earned-wage accrual. Contract: the participant must
        exist in this program (NotFoundError)."""
        with self.assertRaises(NotFoundError):
            make_accrual(self.store, self.program_id, "part-999999")

    def test_bad_period_is_a_validation_error(self):
        """Core 3: Earned-wage accrual. Contract: period must be a
        valid YYYY-MM (month 01-12)."""
        for bad in ("2026-13", "2026-00", "2026-1", "Jan 2026", "2026-01-05", ""):
            with self.subTest(period=bad):
                with self.assertRaises(ValidationError):
                    make_accrual(
                        self.store, self.program_id, self.emp_id, period=bad
                    )

    def test_failed_accrual_consumes_no_id(self):
        """Core 3: Earned-wage accrual (SI-10). A failed accrual
        changes nothing: the next successful accrual is acc-1."""
        with self.assertRaises(ValidationError):
            make_accrual(
                self.store, self.program_id, self.emp_id, earned_cents=-5
            )
        accrual = make_accrual(self.store, self.program_id, self.emp_id)
        self.assertEqual(accrual["id"], "acc-1")

    def test_list_accruals_in_creation_order_and_participant_filter(self):
        """Core 3: Earned-wage accrual. Contract: list_accruals
        returns accrual views in creation order, honouring
        participant_id=."""
        other = make_employee(self.store, self.program_id, ref="emp-2")
        first = make_accrual(self.store, self.program_id, self.emp_id)
        second = make_accrual(self.store, self.program_id, other["id"])
        all_accruals = self.store.list_accruals(self.program_id, MEMBER)
        self.assertEqual(
            [a["id"] for a in all_accruals], [first["id"], second["id"]]
        )
        mine = self.store.list_accruals(
            self.program_id, MEMBER, participant_id=self.emp_id
        )
        self.assertEqual([a["id"] for a in mine], [first["id"]])


class TestRequestFlow(EarnedWageBase):
    """Core 3+8: Access requests — creation, validation, the cap."""

    def setUp(self):
        super().setUp()
        self.accrual = make_accrual(
            self.store, self.program_id, self.emp_id, PERIOD, 100000
        )

    def test_request_returns_the_contract_dict(self):
        """Core 3: Earned-wage access. Contract: request_access
        returns {id, program_id, participant_id, period,
        amount_cents, date, status, created_by, created_utc,
        decided_by, decided_utc, disbursement_id}, status requested,
        decided_by/decided_utc/disbursement_id starting as None."""
        request = make_request(self.store, self.program_id, self.emp_id)
        self.assertEqual(set(request.keys()), REQUEST_KEYS)
        self.assertEqual(request["id"], "req-1")
        self.assertEqual(request["status"], "requested")
        self.assertEqual(request["amount_cents"], 10000)
        self.assertEqual(request["date"], DATE_JAN)
        self.assertIsNone(request["decided_by"])
        self.assertIsNone(request["decided_utc"])
        self.assertIsNone(request["disbursement_id"])

    def test_request_without_accrual_is_a_validation_error(self):
        """Core 3: Earned-wage access. Contract: 'an accrual must
        exist for (participant, period) (else ValidationError)' — no
        accrual at all, and an accrual only in another period, both
        fail."""
        other = make_employee(self.store, self.program_id, ref="emp-2")
        with self.assertRaises(ValidationError):
            make_request(self.store, self.program_id, other["id"])
        with self.assertRaises(ValidationError):
            make_request(
                self.store, self.program_id, self.emp_id,
                period=PERIOD_OTHER,
            )
        self.assertEqual(
            self.store.list_access_requests(self.program_id, MEMBER), []
        )

    def test_request_for_traveler_is_a_validation_error(self):
        """Core 3: Earned-wage access. Contract: the participant must
        be an employee."""
        with self.assertRaises(ValidationError):
            make_request(self.store, self.program_id, self.trav_id)

    def test_request_for_unknown_participant_is_not_found(self):
        """Core 3: Earned-wage access. Contract: the participant must
        exist (NotFoundError)."""
        with self.assertRaises(NotFoundError):
            make_request(self.store, self.program_id, "part-999999")

    def test_float_or_bool_amount_is_a_validation_error(self):
        """Core 3: Earned-wage access (SI-10). amount_cents must be an
        int: floats (even integral) and bools are rejected."""
        for bad in (100.0, 99.9, True):
            with self.subTest(amount=bad):
                with self.assertRaises(ValidationError):
                    make_request(
                        self.store, self.program_id, self.emp_id,
                        amount_cents=bad,
                    )

    def test_zero_or_negative_amount_is_a_validation_error(self):
        """Core 3: Earned-wage access. Contract: amount_cents is a
        *positive* int — zero and negatives are rejected."""
        for bad in (0, -1, -10000):
            with self.subTest(amount=bad):
                with self.assertRaises(ValidationError):
                    make_request(
                        self.store, self.program_id, self.emp_id,
                        amount_cents=bad,
                    )

    def test_bad_request_date_is_a_validation_error(self):
        """Core 3: Earned-wage access. Contract: date must be a valid
        ISO date."""
        for bad in ("2026-13-01", "2026-02-30", "Jan 10 2026", "", None):
            with self.subTest(date=bad):
                with self.assertRaises(ValidationError):
                    make_request(
                        self.store, self.program_id, self.emp_id, date=bad
                    )

    def test_request_exactly_at_cap_is_ok(self):
        """Core 3: Earned-wage access — the earned-cap invariant.
        amount == earned (100000) does not exceed the cap."""
        request = make_request(
            self.store, self.program_id, self.emp_id, amount_cents=100000
        )
        self.assertEqual(request["status"], "requested")

    def test_request_one_cent_over_cap_is_rejected_whole(self):
        """Core 3: Earned-wage access — the earned-cap invariant
        (SI-10). amount == earned + 1 raises ValidationError, nothing
        is stored, and no request id is consumed."""
        with self.assertRaises(ValidationError):
            make_request(
                self.store, self.program_id, self.emp_id,
                amount_cents=100001,
            )
        self.assertEqual(
            self.store.list_access_requests(self.program_id, MEMBER), []
        )
        good = make_request(
            self.store, self.program_id, self.emp_id, amount_cents=1000
        )
        self.assertEqual(good["id"], "req-1")

    def test_two_requests_summing_over_cap_second_is_rejected(self):
        """Core 3: Earned-wage access — the earned-cap invariant is
        over the committed total (pending + accessed), not per
        request: 60000 + 40000 reaches the cap exactly, and one more
        cent is rejected and consumes no id."""
        make_request(self.store, self.program_id, self.emp_id,
                     amount_cents=60000)
        make_request(self.store, self.program_id, self.emp_id,
                     amount_cents=40000)
        with self.assertRaises(ValidationError):
            make_request(self.store, self.program_id, self.emp_id,
                         amount_cents=1)
        requests = self.store.list_access_requests(self.program_id, MEMBER)
        self.assertEqual([r["id"] for r in requests], ["req-1", "req-2"])

    def test_list_access_requests_status_filter(self):
        """Core 8: Workflow & approvals. Contract: list_access_requests
        honours status= over the valid statuses (requested, approved,
        denied, disbursed, void)."""
        pending = make_request(self.store, self.program_id, self.emp_id,
                               amount_cents=1000)
        approved = approved_request(self.store, self.program_id, self.emp_id,
                                    amount_cents=2000)
        requested = self.store.list_access_requests(
            self.program_id, MEMBER, status="requested"
        )
        self.assertEqual([r["id"] for r in requested], [pending["id"]])
        approved_list = self.store.list_access_requests(
            self.program_id, MEMBER, status="approved"
        )
        self.assertEqual([r["id"] for r in approved_list], [approved["id"]])

    def test_list_access_requests_unknown_status_is_validation_error(self):
        """Core 8: Workflow & approvals. Contract: 'an unknown status
        filter -> ValidationError'."""
        with self.assertRaises(ValidationError):
            self.store.list_access_requests(
                self.program_id, MEMBER, status="pending"
            )


class TestDerivedAccrualView(EarnedWageBase):
    """Core 3: Earned-wage access — derived accessed/pending/available."""

    def test_derived_view_math_with_every_status(self):
        """Core 3: Earned-wage access. Contract: get_accrual returns
        the record plus derived {accessed_cents, pending_cents,
        available_cents}: accessed = approved + disbursed only,
        pending = requested only, denied/void count toward neither,
        available = earned - accessed - pending. Scenario (earned
        100000): approved 10000, disbursed 20000, pending 5000,
        denied 7000, void 3000 — so accessed 30000, pending 5000,
        available 65000."""
        accrual = make_accrual(
            self.store, self.program_id, self.emp_id, PERIOD, 100000
        )
        approved_request(self.store, self.program_id, self.emp_id,
                         amount_cents=10000)
        to_disburse = approved_request(
            self.store, self.program_id, self.emp_id, amount_cents=20000
        )
        self.store.record_disbursement(
            self.program_id, to_disburse["id"], "2026-01-20", MEMBER
        )
        make_request(self.store, self.program_id, self.emp_id,
                     amount_cents=5000)
        denied = make_request(self.store, self.program_id, self.emp_id,
                              amount_cents=7000)
        self.store.decide_access(self.program_id, denied["id"], False, ADMIN)
        voided = make_request(self.store, self.program_id, self.emp_id,
                              amount_cents=3000)
        self.store.void_access(self.program_id, voided["id"], MEMBER)

        view = self.store.get_accrual(self.program_id, accrual["id"], MEMBER)
        for key in ACCRUAL_KEYS:
            self.assertIn(key, view)
        self.assertEqual(view["earned_cents"], 100000)
        self.assertEqual(view["accessed_cents"], 30000)
        self.assertEqual(view["pending_cents"], 5000)
        self.assertEqual(view["available_cents"], 100000 - 30000 - 5000)

    def test_derived_view_with_no_requests_is_full_available(self):
        """Core 3: Earned-wage access. With no requests, accessed and
        pending are 0 and the whole earned amount is available."""
        accrual = make_accrual(
            self.store, self.program_id, self.emp_id, PERIOD, 42000
        )
        view = self.store.get_accrual(self.program_id, accrual["id"], MEMBER)
        self.assertEqual(view["accessed_cents"], 0)
        self.assertEqual(view["pending_cents"], 0)
        self.assertEqual(view["available_cents"], 42000)

    def test_get_unknown_accrual_is_not_found(self):
        """Core 3: Earned-wage access. Unknown accrual id ->
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_accrual(self.program_id, "acc-999999", MEMBER)


class TestDecideAccess(EarnedWageBase):
    """Core 8: Workflow & approvals — decide and separation of duties."""

    def setUp(self):
        super().setUp()
        make_accrual(self.store, self.program_id, self.emp_id, PERIOD, 100000)

    def test_approve_by_other_member_sets_decision_fields(self):
        """Core 8: Workflow & approvals (AC-5). A decider other than
        the creator approves: status approved, decided_by/decided_utc
        set. ADMIN decides here; she is not the creator."""
        request = make_request(self.store, self.program_id, self.emp_id)
        decided = self.store.decide_access(
            self.program_id, request["id"], True, ADMIN
        )
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(decided["decided_by"], "alice")
        self.assertIsNotNone(decided["decided_utc"])
        self.assertEqual(set(decided.keys()), REQUEST_KEYS)

    def test_deny_by_other_sets_status_denied(self):
        """Core 8: Workflow & approvals. approve=False -> status
        denied with decision provenance."""
        request = make_request(self.store, self.program_id, self.emp_id)
        decided = self.store.decide_access(
            self.program_id, request["id"], False, ADMIN
        )
        self.assertEqual(decided["status"], "denied")
        self.assertEqual(decided["decided_by"], "alice")

    def test_creator_deciding_own_request_is_permission_denied(self):
        """Core 8: Workflow & approvals (AC-5 separation of duties).
        Contract: 'the actor's name must differ from created_by (else
        PermissionDenied)' — for both approve and deny, and the
        request stays requested."""
        request = make_request(self.store, self.program_id, self.emp_id)
        for approve in (True, False):
            with self.subTest(approve=approve):
                with self.assertRaises(PermissionDenied):
                    self.store.decide_access(
                        self.program_id, request["id"], approve, MEMBER
                    )
        got = self.store.get_access_request(self.program_id, request["id"],
                                            MEMBER)
        self.assertEqual(got["status"], "requested")

    def test_decide_non_requested_is_a_validation_error(self):
        """Core 8: Workflow & approvals. Contract: decide requires
        status requested — deciding an approved or a denied request
        raises ValidationError."""
        approved = approved_request(self.store, self.program_id, self.emp_id,
                                    amount_cents=1000)
        with self.assertRaises(ValidationError):
            self.store.decide_access(self.program_id, approved["id"], True,
                                     ADMIN)
        denied_req = make_request(self.store, self.program_id, self.emp_id,
                                  amount_cents=1000)
        self.store.decide_access(self.program_id, denied_req["id"], False,
                                 ADMIN)
        with self.assertRaises(ValidationError):
            self.store.decide_access(self.program_id, denied_req["id"], True,
                                     ADMIN)

    def test_decide_with_non_bool_approve_is_a_validation_error(self):
        """Core 8: Workflow & approvals (SI-10). Contract: 'approve
        must be a bool (else ValidationError)' — strings, ints and
        None are rejected and the request stays requested."""
        request = make_request(self.store, self.program_id, self.emp_id)
        for bad in ("yes", 1, 0, None):
            with self.subTest(approve=bad):
                with self.assertRaises(ValidationError):
                    self.store.decide_access(
                        self.program_id, request["id"], bad, ADMIN
                    )
        got = self.store.get_access_request(self.program_id, request["id"],
                                            MEMBER)
        self.assertEqual(got["status"], "requested")

    def test_decide_unknown_request_is_not_found(self):
        """Core 8: Workflow & approvals. Unknown request id ->
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.decide_access(self.program_id, "req-999999", True,
                                     ADMIN)

    def test_viewer_cannot_decide_by_role(self):
        """Core 8 + Core 10: Workflow / access control. decide is not
        in the viewer permission set."""
        request = make_request(self.store, self.program_id, self.emp_id)
        with self.assertRaises(PermissionDenied):
            self.store.decide_access(self.program_id, request["id"], True,
                                     VIEWER)


class TestDisbursement(EarnedWageBase):
    """Core 3+8: Disbursement records — approved -> disbursed."""

    def setUp(self):
        super().setUp()
        make_accrual(self.store, self.program_id, self.emp_id, PERIOD, 100000)

    def test_disbursement_on_approved_request(self):
        """Core 3: Earned-wage access. Contract: record_disbursement
        on an approved request returns {id, program_id, request_id,
        participant_id, period, amount_cents, date, method,
        recorded_by, recorded_utc} with amount/participant/period
        copied from the request; the request becomes disbursed with
        disbursement_id set."""
        approved = approved_request(self.store, self.program_id, self.emp_id,
                                    amount_cents=12345)
        disbursement = self.store.record_disbursement(
            self.program_id, approved["id"], "2026-01-20", MEMBER,
            method="payroll",
        )
        self.assertEqual(set(disbursement.keys()), DISBURSEMENT_KEYS)
        self.assertEqual(disbursement["id"], "dis-1")
        self.assertEqual(disbursement["request_id"], approved["id"])
        self.assertEqual(disbursement["participant_id"], self.emp_id)
        self.assertEqual(disbursement["period"], PERIOD)
        self.assertEqual(disbursement["amount_cents"], 12345)
        self.assertEqual(disbursement["date"], "2026-01-20")
        self.assertEqual(disbursement["method"], "payroll")
        self.assertEqual(disbursement["recorded_by"], "bob")
        got = self.store.get_access_request(self.program_id, approved["id"],
                                            MEMBER)
        self.assertEqual(got["status"], "disbursed")
        self.assertEqual(got["disbursement_id"], disbursement["id"])

    def test_disbursement_method_defaults_to_empty_string(self):
        """Core 3: Earned-wage access. Contract:
        record_disbursement(..., method="") — the method is an opaque
        label and defaults to empty."""
        approved = approved_request(self.store, self.program_id, self.emp_id,
                                    amount_cents=1000)
        disbursement = self.store.record_disbursement(
            self.program_id, approved["id"], "2026-01-20", MEMBER
        )
        self.assertEqual(disbursement["method"], "")

    def test_disbursement_on_requested_is_a_validation_error(self):
        """Core 8: Workflow & approvals. Contract: the request must be
        in status approved — disbursing a still-requested request
        raises ValidationError and stores nothing."""
        request = make_request(self.store, self.program_id, self.emp_id)
        with self.assertRaises(ValidationError):
            self.store.record_disbursement(
                self.program_id, request["id"], "2026-01-20", MEMBER
            )
        self.assertEqual(self.store.list_disbursements(self.program_id,
                                                       MEMBER), [])
        got = self.store.get_access_request(self.program_id, request["id"],
                                            MEMBER)
        self.assertEqual(got["status"], "requested")

    def test_disbursement_on_denied_is_a_validation_error(self):
        """Core 8: Workflow & approvals. A denied request can never be
        disbursed (ValidationError)."""
        request = make_request(self.store, self.program_id, self.emp_id)
        self.store.decide_access(self.program_id, request["id"], False, ADMIN)
        with self.assertRaises(ValidationError):
            self.store.record_disbursement(
                self.program_id, request["id"], "2026-01-20", MEMBER
            )

    def test_disbursement_twice_is_a_validation_error(self):
        """Core 8: Workflow & approvals. After disbursement the
        request is disbursed, not approved, so a second disbursement
        raises ValidationError."""
        approved = approved_request(self.store, self.program_id, self.emp_id,
                                    amount_cents=1000)
        self.store.record_disbursement(
            self.program_id, approved["id"], "2026-01-20", MEMBER
        )
        with self.assertRaises(ValidationError):
            self.store.record_disbursement(
                self.program_id, approved["id"], "2026-01-21", MEMBER
            )
        self.assertEqual(
            len(self.store.list_disbursements(self.program_id, MEMBER)), 1
        )

    def test_disbursement_with_float_or_bad_date_is_validation_error(self):
        """Core 3: Earned-wage access (SI-10). Contract: the
        disbursement date must be a valid ISO date — a float, an int,
        and malformed strings are all ValidationError."""
        approved = approved_request(self.store, self.program_id, self.emp_id,
                                    amount_cents=1000)
        for bad in (20260120.0, 20260120, "2026-13-20", "Jan 20 2026", ""):
            with self.subTest(date=bad):
                with self.assertRaises(ValidationError):
                    self.store.record_disbursement(
                        self.program_id, approved["id"], bad, MEMBER
                    )
        got = self.store.get_access_request(self.program_id, approved["id"],
                                            MEMBER)
        self.assertEqual(got["status"], "approved")

    def test_disbursement_unknown_request_is_not_found(self):
        """Core 3: Earned-wage access. Contract: the request must
        exist (NotFoundError)."""
        with self.assertRaises(NotFoundError):
            self.store.record_disbursement(
                self.program_id, "req-999999", "2026-01-20", MEMBER
            )

    def test_list_disbursements_and_request_filter(self):
        """Core 3: Earned-wage access. Contract: list_disbursements
        returns disbursements in creation order, honouring
        request_id=."""
        first = approved_request(self.store, self.program_id, self.emp_id,
                                 amount_cents=1000)
        second = approved_request(self.store, self.program_id, self.emp_id,
                                  amount_cents=2000)
        dis1 = self.store.record_disbursement(
            self.program_id, first["id"], "2026-01-20", MEMBER
        )
        dis2 = self.store.record_disbursement(
            self.program_id, second["id"], "2026-01-21", MEMBER
        )
        all_dis = self.store.list_disbursements(self.program_id, MEMBER)
        self.assertEqual([d["id"] for d in all_dis], [dis1["id"], dis2["id"]])
        filtered = self.store.list_disbursements(
            self.program_id, MEMBER, request_id=second["id"]
        )
        self.assertEqual([d["id"] for d in filtered], [dis2["id"]])


class TestVoidAccess(EarnedWageBase):
    """Core 8: Workflow & approvals — void and who may void."""

    def setUp(self):
        super().setUp()
        make_accrual(self.store, self.program_id, self.emp_id, PERIOD, 100000)

    def test_void_from_requested_by_creator(self):
        """Core 8: Workflow & approvals. Contract: status requested ->
        void, by the creator."""
        request = make_request(self.store, self.program_id, self.emp_id)
        voided = self.store.void_access(self.program_id, request["id"],
                                        MEMBER)
        self.assertEqual(voided["status"], "void")
        self.assertEqual(set(voided.keys()), REQUEST_KEYS)

    def test_void_from_denied_by_creator(self):
        """Core 8: Workflow & approvals. Contract: status denied ->
        void is also allowed."""
        request = make_request(self.store, self.program_id, self.emp_id)
        self.store.decide_access(self.program_id, request["id"], False, ADMIN)
        voided = self.store.void_access(self.program_id, request["id"],
                                        MEMBER)
        self.assertEqual(voided["status"], "void")

    def test_void_from_approved_is_a_validation_error(self):
        """Core 8: Workflow & approvals. Contract: void is only from
        requested or denied — an approved request raises
        ValidationError and stays approved."""
        approved = approved_request(self.store, self.program_id, self.emp_id,
                                    amount_cents=1000)
        with self.assertRaises(ValidationError):
            self.store.void_access(self.program_id, approved["id"], MEMBER)
        got = self.store.get_access_request(self.program_id, approved["id"],
                                            MEMBER)
        self.assertEqual(got["status"], "approved")

    def test_void_from_disbursed_is_a_validation_error(self):
        """Core 8: Workflow & approvals. A disbursed request cannot be
        voided (ValidationError)."""
        approved = approved_request(self.store, self.program_id, self.emp_id,
                                    amount_cents=1000)
        self.store.record_disbursement(
            self.program_id, approved["id"], "2026-01-20", MEMBER
        )
        with self.assertRaises(ValidationError):
            self.store.void_access(self.program_id, approved["id"], MEMBER)

    def test_void_by_program_owner_and_by_platform_admin(self):
        """Core 8: Workflow & approvals. Contract: void is limited to
        'the creator, the program owner, or a platform admin' — the
        owner voids a request created by another member, and the
        platform admin voids one too."""
        self.store.add_member(self.program_id, OUTSIDER.name, MEMBER)
        by_outsider = make_request(
            self.store, self.program_id, self.emp_id, amount_cents=1000,
            actor=OUTSIDER,
        )
        voided = self.store.void_access(self.program_id, by_outsider["id"],
                                        MEMBER)  # bob is the owner
        self.assertEqual(voided["status"], "void")
        mine = make_request(self.store, self.program_id, self.emp_id,
                            amount_cents=1000)
        voided = self.store.void_access(self.program_id, mine["id"], ADMIN)
        self.assertEqual(voided["status"], "void")

    def test_void_by_unrelated_member_is_permission_denied(self):
        """Core 8: Workflow & approvals (AC-5/AC-3). Contract: an
        actor who is neither creator, owner, nor platform admin may
        not void — an unrelated program member gets PermissionDenied
        and the request stays requested."""
        self.store.add_member(self.program_id, OUTSIDER.name, MEMBER)
        request = make_request(self.store, self.program_id, self.emp_id)
        with self.assertRaises(PermissionDenied):
            self.store.void_access(self.program_id, request["id"], OUTSIDER)
        got = self.store.get_access_request(self.program_id, request["id"],
                                            MEMBER)
        self.assertEqual(got["status"], "requested")

    def test_void_by_non_member_is_permission_denied(self):
        """Core 8: Workflow & approvals (AC-3). A non-member cannot
        void (membership boundary)."""
        request = make_request(self.store, self.program_id, self.emp_id)
        with self.assertRaises(PermissionDenied):
            self.store.void_access(self.program_id, request["id"], OUTSIDER)


if __name__ == "__main__":
    unittest.main()
