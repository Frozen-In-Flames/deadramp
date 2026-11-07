"""Final GAPS batch, second unit -- remainder-addition tests for
Group 21, Human Resources L2.

Pins the second extension surface in
``src/hr/extensions_addition.py`` (``HrExtensionsAddition``,
wrapping the core ``HrStore``): one test class per open entry of
the GAPS.md section "Remainder Addition -- Human Resources L2
(+3 forks)" (see ``../BATCH-ADDITION.md``), plus cross-cutting
pins -- the founding privacy discipline over the new shapes
(forbidden keys, and a signature scan proving no method can accept
a real name, identifier, pay figure, or free-text response
content), no aggregate key on any stored addition record,
derived-never-stored, RBAC denials consuming no id, employee
scope, ``ext2_``-prefixed audit actions, and the unit's fresh
mutation-verified negative control (the leave-balance mutant,
``TestLeaveBalanceMutant``).

Fixtures: ``make_store()`` (position "Program Analyst" series 0343
grade 13, person_ref "carol") plus a second person ("erin").
"""

import inspect
import unittest

from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST, make_store
from hr.access import User

ERIN_EMPLOYEE = User("erin", "employee")
from hr.errors import NotFoundError, PermissionDenied, ValidationError
from hr.extensions_addition import (
    AGGREGATE_KEYS,
    FORBIDDEN_KEYS,
    HrExtensionsAddition,
)

FORBIDDEN_PARAMS = {
    "name", "ssn", "social_security_number", "salary", "compensation",
    "pay", "dob", "date_of_birth", "address", "phone", "email",
    "content", "comment", "text", "response_text", "narrative",
}


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class AdditionFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.position, self.person = make_store()
        self.store.create_person("erin", ADMIN, kind="employee")
        self.ext = HrExtensionsAddition(self.store)

    def make_benefits(self, person_ref="carol", kind="retirement_case"):
        return self.store.create_benefits_record(
            person_ref, kind, "plan-a", SPECIALIST
        )

    def make_leave_setup(self):
        account = self.ext.create_leave_account("carol", "annual", 480, SPECIALIST)
        self.ext.record_leave_accrual(account["id"], 10, SPECIALIST)
        approved = self.ext.create_leave_request(
            "carol", "annual", 600, "2026-12-01", SPECIALIST
        )
        self.ext.set_leave_request_state(approved["id"], "approved", SPECIALIST)
        self.ext.create_leave_request("carol", "annual", 300, "2026-12-15", SPECIALIST)
        return account


class TestTimeAttendanceLeave(AdditionFixture):
    """Entry idx 607: Time, attendance & leave tracking engine --
    built as time-entry/correction records, leave-account records
    with the accrual rate as data, and a balance derived at read."""

    def test_time_entry_record_shape_and_ids(self):
        entry = self.ext.record_time_entry(
            "carol", "2026-11-02", 480, "regular", SPECIALIST
        )
        self.assertEqual(entry["id"], "tim-1")
        self.assertEqual(entry["person_ref"], "carol")
        self.assertEqual(entry["minutes"], 480)
        self.assertNotIn("effective_minutes", entry)

    def test_correction_derives_effective_minutes_original_unchanged(self):
        entry = self.ext.record_time_entry(
            "carol", "2026-11-02", 480, "regular", SPECIALIST
        )
        self.ext.record_time_correction(entry["id"], 450, "review", SPECIALIST)
        self.ext.record_time_correction(entry["id"], 445, "second review", SPECIALIST)
        views = self.ext.list_time_entries(SPECIALIST)
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0]["minutes"], 480)
        self.assertEqual(views[0]["effective_minutes"], 445)

    def test_time_summary_counts_and_totals(self):
        self.ext.record_time_entry("carol", "2026-11-02", 480, "regular", SPECIALIST)
        overtime = self.ext.record_time_entry(
            "carol", "2026-11-03", 120, "overtime", SPECIALIST
        )
        self.ext.record_time_correction(overtime["id"], 90, "review", SPECIALIST)
        summary = self.ext.time_summary("carol", SPECIALIST)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertTrue(summary["derived"])
        self.assertFalse(summary["stored"])
        self.assertEqual(summary["entry_count"], 2)
        self.assertEqual(summary["effective_minutes_total"], 570)
        self.assertEqual(summary["entries_by_kind"], {"regular": 1, "overtime": 1})

    def test_leave_balance_derived_from_records(self):
        self.make_leave_setup()
        view = self.ext.leave_balance_view("carol", "annual", SPECIALIST)
        self.assertEqual(view["method"], "integer_leave_accounting")
        self.assertTrue(view["derived"])
        self.assertFalse(view["stored"])
        self.assertEqual(view["accrued_minutes"], 4800)
        self.assertEqual(view["used_minutes"], 600)
        self.assertEqual(view["pending_minutes"], 300)
        self.assertEqual(view["balance_minutes"], 4200)

    def test_leave_balance_freshness(self):
        account = self.make_leave_setup()
        before = self.ext.leave_balance_view("carol", "annual", SPECIALIST)
        self.ext.record_leave_accrual(account["id"], 1, SPECIALIST)
        after = self.ext.leave_balance_view("carol", "annual", SPECIALIST)
        self.assertEqual(after["balance_minutes"], before["balance_minutes"] + 480)

    def test_denied_and_taken_states_count_used(self):
        account = self.ext.create_leave_account("carol", "sick", 240, SPECIALIST)
        self.ext.record_leave_accrual(account["id"], 4, SPECIALIST)
        denied = self.ext.create_leave_request(
            "carol", "sick", 100, "2026-11-10", SPECIALIST
        )
        self.ext.set_leave_request_state(denied["id"], "denied", SPECIALIST)
        taken = self.ext.create_leave_request(
            "carol", "sick", 200, "2026-11-11", SPECIALIST
        )
        self.ext.set_leave_request_state(taken["id"], "taken", SPECIALIST)
        view = self.ext.leave_balance_view("carol", "sick", SPECIALIST)
        self.assertEqual(view["used_minutes"], 200)
        self.assertEqual(view["balance_minutes"], 760)

    def test_validation_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.record_time_entry("carol", "2026-13-01", 10, "regular", SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.record_time_entry("carol", "2026-11-02", -1, "regular", SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.record_time_entry("carol", "2026-11-02", 10, "bogus", SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.record_time_entry("carol", "2026-11-02", True, "regular", SPECIALIST)
        with self.assertRaises(NotFoundError):
            self.ext.record_time_entry("ghost", "2026-11-02", 10, "regular", SPECIALIST)
        entry = self.ext.record_time_entry(
            "carol", "2026-11-02", 10, "regular", SPECIALIST
        )
        self.assertEqual(entry["id"], "tim-1")
        with self.assertRaises(ValidationError):
            self.ext.create_leave_account("carol", "bogus", 10, SPECIALIST)
        account = self.ext.create_leave_account("carol", "annual", 480, SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.create_leave_account("carol", "annual", 480, SPECIALIST)
        self.assertEqual(account["id"], "lva-1")

    def test_employee_scope_on_leave_views(self):
        self.make_leave_setup()
        view = self.ext.leave_balance_view("carol", "annual", EMPLOYEE)
        self.assertEqual(view["balance_minutes"], 4200)
        with self.assertRaises(PermissionDenied):
            self.ext.leave_balance_view("erin", "annual", EMPLOYEE)
        self.assertEqual(
            self.ext.list_leave_requests(EMPLOYEE)[0]["person_ref"], "carol"
        )
        self.assertEqual(len(self.ext.list_leave_requests(EMPLOYEE)), 2)


class TestLeaveBalanceMutant(AdditionFixture):
    """Fresh negative control: the leave balance's used-minutes seam
    is load-bearing. The mutant counts merely-requested minutes as
    used; the canonical case (600 approved, 300 still requested,
    4800 accrued) must read balance 4200 in the real implementation
    and 3900 in the mutant, and treating the mutant's figure as the
    expectation must fail."""

    def test_used_minutes_seam_is_load_bearing(self):
        self.make_leave_setup()
        view = self.ext.leave_balance_view("carol", "annual", SPECIALIST)
        self.assertEqual(view["balance_minutes"], 4200)

        class MutantAddition(HrExtensionsAddition):
            def _leave_used_minutes(self, requests):
                return sum(
                    r["minutes_requested"] for r in requests
                    if r["state"] in ("approved", "taken", "requested")
                )

        # The mutant has its own containers, so the identical setup
        # is recorded through it (for erin): 4800 accrued, 600
        # approved, 300 still requested.
        mutant = MutantAddition(self.store)
        account = mutant.create_leave_account("erin", "annual", 480, SPECIALIST)
        mutant.record_leave_accrual(account["id"], 10, SPECIALIST)
        approved = mutant.create_leave_request(
            "erin", "annual", 600, "2026-12-01", SPECIALIST
        )
        mutant.set_leave_request_state(approved["id"], "approved", SPECIALIST)
        mutant.create_leave_request("erin", "annual", 300, "2026-12-15", SPECIALIST)
        mutant_view = mutant.leave_balance_view("erin", "annual", SPECIALIST)
        self.assertEqual(mutant_view["balance_minutes"], 3900)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_view["balance_minutes"], 4200)


class TestOrgChart(AdditionFixture):
    """Entry idx 608: Organizational chart generation & maintenance
    automation -- built as org-unit and assignment records with the
    chart derived at read from the current records."""

    def test_unit_and_assignment_records(self):
        unit = self.ext.create_org_unit("hq", "Headquarters", ADMIN)
        self.assertEqual(unit["id"], "ogu-1")
        child = self.ext.create_org_unit("ops", "Operations", ADMIN, parent_unit_ref="hq")
        self.assertEqual(child["parent_unit_ref"], "hq")
        assignment = self.ext.assign_position_to_unit(self.position["id"], "ops", ADMIN)
        self.assertEqual(assignment["id"], "oga-1")
        self.assertEqual(assignment["unit_ref"], "ops")

    def test_chart_view_derived_and_fresh(self):
        self.ext.create_org_unit("hq", "Headquarters", ADMIN)
        before = self.ext.org_chart_view(ADMIN)
        self.assertEqual(before["method"], "deterministic_org_chart_derivation")
        self.assertTrue(before["derived"])
        self.assertEqual(before["units"][0]["position_count"], 0)
        self.assertEqual(before["unassigned_position_ids"], [self.position["id"]])
        self.ext.assign_position_to_unit(self.position["id"], "hq", ADMIN)
        after = self.ext.org_chart_view(ADMIN)
        self.assertEqual(after["units"][0]["position_ids"], [self.position["id"]])
        self.assertEqual(after["units"][0]["position_count"], 1)
        self.assertEqual(after["unassigned_position_ids"], [])

    def test_assignment_never_modifies_position(self):
        self.ext.create_org_unit("hq", "Headquarters", ADMIN)
        before = self.store.get_position(self.position["id"], ADMIN)
        self.ext.assign_position_to_unit(self.position["id"], "hq", ADMIN)
        self.assertEqual(self.store.get_position(self.position["id"], ADMIN), before)

    def test_change_record_is_reported_only(self):
        self.ext.create_org_unit("hq", "Headquarters", ADMIN)
        change = self.ext.record_org_change("hq", "reorganization", "reported", ADMIN)
        self.assertEqual(change["id"], "ogc-1")
        self.assertFalse(change["applied_here"])

    def test_validation(self):
        self.ext.create_org_unit("hq", "Headquarters", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_org_unit("hq", "Duplicate", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.create_org_unit("x", "X", ADMIN, parent_unit_ref="ghost")
        with self.assertRaises(NotFoundError):
            self.ext.assign_position_to_unit(self.position["id"], "ghost", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.assign_position_to_unit("pos-99", "hq", ADMIN)
        self.ext.assign_position_to_unit(self.position["id"], "hq", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.assign_position_to_unit(self.position["id"], "hq", ADMIN)


class TestSurveyListening(AdditionFixture):
    """Entry idx 609: Employee engagement survey & listening
    platform -- built as instrument definitions, verbatim rating
    responses, label-only listening signals, and verbatim multi-
    rater feedback; summaries are counts, never means or scores."""

    QUESTIONS = [
        {"question_ref": "q1", "topic_label": "belonging", "max_rating": 5},
        {"question_ref": "q2", "topic_label": "growth", "max_rating": 3},
    ]

    def make_instrument(self):
        return self.ext.create_survey_instrument(
            "pulse-2026", "Pulse survey", list(self.QUESTIONS), SPECIALIST
        )

    def test_instrument_and_response_records_verbatim(self):
        instrument = self.make_instrument()
        self.assertEqual(instrument["id"], "svi-1")
        response = self.ext.record_survey_response(
            instrument["id"], "carol",
            [{"question_ref": "q1", "rating": 4}, {"question_ref": "q2", "rating": 2}],
            SPECIALIST,
        )
        self.assertEqual(response["id"], "svr-1")
        self.assertEqual(
            response["answers"],
            [{"question_ref": "q1", "rating": 4}, {"question_ref": "q2", "rating": 2}],
        )

    def test_summary_is_counts_only(self):
        instrument = self.make_instrument()
        self.ext.record_survey_response(
            instrument["id"], "carol", [{"question_ref": "q1", "rating": 4}], SPECIALIST
        )
        self.ext.record_survey_response(
            instrument["id"], "erin", [{"question_ref": "q1", "rating": 4}], SPECIALIST
        )
        self.ext.record_survey_response(
            instrument["id"], "erin", [{"question_ref": "q1", "rating": 1}], SPECIALIST
        )
        summary = self.ext.survey_summary(instrument["id"], AUDITOR)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertEqual(summary["response_count"], 3)
        q1 = summary["questions"][0]
        self.assertEqual(
            q1["rating_counts"],
            [{"rating": 1, "count": 1}, {"rating": 4, "count": 2}],
        )
        self.assertEqual(q1["answer_count"], 3)
        self.assertEqual(_all_keys(summary) & AGGREGATE_KEYS, set())
        self.assertNotIn("mean", _all_keys(summary))

    def test_no_free_text_response_can_exist(self):
        instrument = self.make_instrument()
        with self.assertRaises(TypeError):
            self.ext.record_survey_response(
                instrument["id"], "carol",
                [{"question_ref": "q1", "rating": 4}],
                SPECIALIST, content="narrative",
            )
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                instrument["id"], "carol",
                [{"question_ref": "q1", "rating": 4, "comment": "hi"}],
                SPECIALIST,
            )
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                instrument["id"], "carol",
                [{"question_ref": "q1", "rating": 5, "extra": 1}],
                SPECIALIST,
            )

    def test_rating_bounds_come_from_the_instrument(self):
        instrument = self.make_instrument()
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                instrument["id"], "carol",
                [{"question_ref": "q2", "rating": 4}], SPECIALIST,
            )
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                instrument["id"], "carol",
                [{"question_ref": "qx", "rating": 1}], SPECIALIST,
            )
        with self.assertRaises(ValidationError):
            self.ext.record_survey_response(
                instrument["id"], "carol",
                [{"question_ref": "q1", "rating": True}], SPECIALIST,
            )
        response = self.ext.record_survey_response(
            instrument["id"], "carol", [{"question_ref": "q1", "rating": 3}], SPECIALIST
        )
        self.assertEqual(response["id"], "svr-1")

    def test_listening_signals_are_labels_only(self):
        signal = self.ext.record_listening_signal(
            "carol", "always_on", "schedule_concern", SPECIALIST
        )
        self.assertEqual(signal["id"], "lis-1")
        self.assertEqual(signal["signal_label"], "schedule_concern")
        with self.assertRaises(ValidationError):
            self.ext.record_listening_signal("carol", "bogus", "x", SPECIALIST)
        with self.assertRaises(TypeError):
            self.ext.record_listening_signal(
                "carol", "pulse", "x", SPECIALIST, text="narrative"
            )
        self.assertEqual(len(self.ext.list_listening_signals(EMPLOYEE)), 1)
        self.assertEqual(
            self.ext.list_listening_signals(EMPLOYEE)[0]["person_ref"], "carol"
        )

    def test_feedback_verbatim_no_aggregate(self):
        first = self.ext.record_feedback("carol", "rater-1", "teamwork", 5, SPECIALIST)
        self.ext.record_feedback("carol", "rater-2", "teamwork", 3, SPECIALIST)
        self.assertEqual(first["rating"], 5)
        records = self.ext.list_feedback(SPECIALIST, person_ref="carol")
        self.assertEqual([r["rating"] for r in records], [5, 3])
        for record in records:
            self.assertEqual(_all_keys(record) & AGGREGATE_KEYS, set())
        with self.assertRaises(ValidationError):
            self.ext.record_feedback("carol", "rater-3", "teamwork", 6, SPECIALIST)


class TestBenefitsAdministration(AdditionFixture):
    """Entry idx 610: Federal retirement & benefits administration
    platform depth -- built as administration cases over the core
    benefits records with derived status, plus reported action and
    counseling-session records."""

    def test_case_status_derived_never_stored(self):
        benefits = self.make_benefits()
        case = self.ext.create_admin_case(
            benefits["id"], "retirement_counseling", SPECIALIST,
            task_titles=["Review record", "Confirm election"],
        )
        self.assertEqual(case["id"], "adc-1")
        self.assertEqual(case["status"], "not_started")
        stored = self.ext._admin_cases[case["id"]]
        self.assertNotIn("status", stored)
        case = self.ext.set_admin_task_state(case["id"], "t-1", "done", SPECIALIST)
        self.assertEqual(case["status"], "in_progress")
        case = self.ext.set_admin_task_state(case["id"], "t-2", "waived", SPECIALIST)
        self.assertEqual(case["status"], "complete")
        case = self.ext.add_admin_task(case["id"], "File copies", SPECIALIST)
        self.assertEqual(case["status"], "in_progress")

    def test_cancel_is_a_recorded_event(self):
        benefits = self.make_benefits()
        case = self.ext.create_admin_case(
            benefits["id"], "general_administration", SPECIALIST
        )
        self.assertEqual(case["status"], "not_started")
        case = self.ext.cancel_admin_case(case["id"], SPECIALIST)
        self.assertEqual(case["status"], "cancelled")
        self.assertTrue(self.ext._admin_cases[case["id"]]["cancelled"])

    def test_case_binds_core_record_without_modifying_it(self):
        benefits = self.make_benefits()
        before = self.store.get_benefits_record(benefits["id"], ADMIN)
        self.ext.create_admin_case(
            benefits["id"], "enrollment_review", SPECIALIST, task_titles=["Check"]
        )
        self.assertEqual(self.store.get_benefits_record(benefits["id"], ADMIN), before)
        with self.assertRaises(NotFoundError):
            self.ext.create_admin_case("ben-99", "enrollment_review", SPECIALIST)

    def test_employee_scope_through_benefits_record(self):
        benefits = self.make_benefits()
        case = self.ext.create_admin_case(
            benefits["id"], "eligibility_review", SPECIALIST
        )
        self.assertEqual(self.ext.get_admin_case(case["id"], EMPLOYEE)["id"], "adc-1")
        erin_benefits = self.make_benefits(person_ref="erin")
        erin_case = self.ext.create_admin_case(
            erin_benefits["id"], "eligibility_review", SPECIALIST
        )
        with self.assertRaises(PermissionDenied):
            self.ext.get_admin_case(erin_case["id"], EMPLOYEE)
        self.assertEqual(
            [c["id"] for c in self.ext.list_admin_cases(EMPLOYEE)], ["adc-1"]
        )

    def test_actions_and_sessions_are_reported_records(self):
        benefits = self.make_benefits()
        case = self.ext.create_admin_case(
            benefits["id"], "provider_coordination", SPECIALIST
        )
        action = self.ext.record_admin_action(
            case["id"], "provider call", "confirmed", SPECIALIST
        )
        self.assertEqual(action["id"], "ada-1")
        self.assertFalse(action["administered_here"])
        session = self.ext.record_counseling_session(
            "carol", "retirement", "plan reviewed", SPECIALIST
        )
        self.assertEqual(session["id"], "cns-1")
        self.assertFalse(session["conducted_here"])
        self.assertEqual(len(self.ext.list_counseling_sessions(EMPLOYEE)), 1)


class TestPortalDashboard(AdditionFixture):
    """Entry idx 611: Employee self-service portal & HR dashboard --
    built as portal-profile configuration records (identity and
    serving stated as not-here on the record), self-service request
    records, and dashboard definitions whose figures derive at
    read over the records visible to the actor."""

    def test_portal_profile_states_its_boundaries(self):
        profile = self.ext.create_portal_profile(
            "carol", ["benefits", "leave"], SPECIALIST
        )
        self.assertEqual(profile["id"], "prt-1")
        self.assertFalse(profile["identity_provider"])
        self.assertFalse(profile["served_here"])
        self.assertEqual(profile["section_labels"], ["benefits", "leave"])
        with self.assertRaises(ValidationError):
            self.ext.create_portal_profile("carol", ["cases"], SPECIALIST)
        with self.assertRaises(PermissionDenied):
            self.ext.get_portal_profile(profile["id"], ERIN_EMPLOYEE)

    def test_service_request_lifecycle(self):
        request = self.ext.create_service_request("carol", "general", SPECIALIST)
        self.assertEqual(request["id"], "ssr-1")
        self.assertEqual(request["state"], "opened")
        request = self.ext.set_service_request_state(request["id"], "closed", SPECIALIST)
        self.assertEqual(request["state"], "closed")
        with self.assertRaises(ValidationError):
            self.ext.create_service_request("carol", "bogus", SPECIALIST)
        self.assertEqual(len(self.ext.list_service_requests(EMPLOYEE)), 1)

    def test_dashboard_definition_key_set_exact(self):
        dashboard = self.ext.create_dashboard(
            "Overview", ["persons", "positions"], SPECIALIST
        )
        self.assertEqual(
            set(dashboard), {"id", "title", "panels", "created_by", "created_utc"}
        )
        self.assertEqual(dashboard["id"], "dsh-1")

    def test_dashboard_view_derives_fresh_scoped_figures(self):
        dashboard = self.ext.create_dashboard(
            "Overview", ["persons", "applications"], SPECIALIST
        )
        view = self.ext.dashboard_view(dashboard["id"], AUDITOR)
        self.assertEqual(view["method"], "deterministic_counts")
        figures = {f["panel"]: f["count"] for f in view["figures"]}
        self.assertEqual(figures["persons"], 2)
        self.assertEqual(figures["applications"], 0)
        vacancy = self.store.create_vacancy(self.position["id"], "Opening", ADMIN)
        self.store.create_application("erin", vacancy["id"], SPECIALIST)
        view = self.ext.dashboard_view(dashboard["id"], AUDITOR)
        figures = {f["panel"]: f["count"] for f in view["figures"]}
        self.assertEqual(figures["applications"], 1)
        with self.assertRaises(PermissionDenied):
            self.ext.dashboard_view(dashboard["id"], EMPLOYEE)


class TestUniformAllowance(AdditionFixture):
    """Entry idx 612: Uniform allowance request processing -- built
    as integer-cents request records with recorded states,
    processing-step records, and a derived summary."""

    def test_request_record_and_states(self):
        request = self.ext.create_allowance_request(
            "carol", "jacket", 12500, SPECIALIST
        )
        self.assertEqual(request["id"], "uar-1")
        self.assertEqual(request["amount_cents"], 12500)
        self.assertEqual(request["state"], "requested")
        request = self.ext.set_allowance_request_state(
            request["id"], "approved", SPECIALIST
        )
        self.assertEqual(request["state"], "approved")
        with self.assertRaises(ValidationError):
            self.ext.create_allowance_request("carol", "boots", 12.5, SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.create_allowance_request("carol", "boots", True, SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.set_allowance_request_state(request["id"], "bogus", SPECIALIST)

    def test_steps_are_records_and_change_no_state(self):
        request = self.ext.create_allowance_request(
            "carol", "jacket", 12500, SPECIALIST
        )
        step = self.ext.record_allowance_step(
            request["id"], "verify eligibility", "verified", SPECIALIST
        )
        self.assertEqual(step["id"], "uas-1")
        self.assertFalse(step["processed_here"])
        current = self.ext.list_allowance_requests(SPECIALIST)[0]
        self.assertEqual(current["state"], "requested")
        self.assertEqual(len(self.ext.list_allowance_steps(EMPLOYEE)), 1)

    def test_summary_derived_counts_and_cents(self):
        first = self.ext.create_allowance_request("carol", "jacket", 12500, SPECIALIST)
        self.ext.set_allowance_request_state(first["id"], "fulfilled", SPECIALIST)
        self.ext.create_allowance_request("erin", "boots", 8000, SPECIALIST)
        summary = self.ext.allowance_summary(AUDITOR)
        self.assertEqual(summary["method"], "deterministic_counts")
        self.assertTrue(summary["derived"])
        self.assertEqual(summary["request_count"], 2)
        self.assertEqual(
            summary["requests_by_state"], {"fulfilled": 1, "requested": 1}
        )
        self.assertEqual(
            summary["amount_cents_by_state"], {"fulfilled": 12500, "requested": 8000}
        )
        with self.assertRaises(PermissionDenied):
            self.ext.allowance_summary(EMPLOYEE)


class TestCrossCuttingAddition(AdditionFixture):
    """Cross-cutting pins for the addition surface: privacy (keys
    and signatures), no aggregate key on any stored record, RBAC
    denials consuming no id, employee write denial, and ext2_
    audit actions."""

    def _exercise_everything(self):
        ext = self.ext
        entry = ext.record_time_entry("carol", "2026-11-02", 480, "regular", SPECIALIST)
        correction = ext.record_time_correction(entry["id"], 450, "review", SPECIALIST)
        account = ext.create_leave_account("carol", "annual", 480, SPECIALIST)
        accrual = ext.record_leave_accrual(account["id"], 2, SPECIALIST)
        request = ext.create_leave_request("carol", "annual", 60, "2026-12-01", SPECIALIST)
        unit = ext.create_org_unit("hq", "Headquarters", ADMIN)
        assignment = ext.assign_position_to_unit(self.position["id"], "hq", ADMIN)
        change = ext.record_org_change("hq", "reorg", "reported", ADMIN)
        instrument = ext.create_survey_instrument(
            "pulse", "Pulse",
            [{"question_ref": "q1", "topic_label": "belonging", "max_rating": 5}],
            SPECIALIST,
        )
        response = ext.record_survey_response(
            instrument["id"], "carol", [{"question_ref": "q1", "rating": 4}], SPECIALIST
        )
        signal = ext.record_listening_signal("carol", "pulse", "ok", SPECIALIST)
        feedback = ext.record_feedback("carol", "rater-1", "teamwork", 5, SPECIALIST)
        benefits = self.make_benefits()
        case = ext.create_admin_case(
            benefits["id"], "general_administration", SPECIALIST, task_titles=["Check"]
        )
        action = ext.record_admin_action(case["id"], "call", "done", SPECIALIST)
        session = ext.record_counseling_session("carol", "retirement", "done", SPECIALIST)
        profile = ext.create_portal_profile("carol", ["benefits"], SPECIALIST)
        service = ext.create_service_request("carol", "general", SPECIALIST)
        dashboard = ext.create_dashboard("Overview", ["persons"], SPECIALIST)
        allowance = ext.create_allowance_request("carol", "jacket", 100, SPECIALIST)
        step = ext.record_allowance_step(allowance["id"], "verify", "ok", SPECIALIST)
        return [
            entry, correction, account, accrual, request, unit, assignment,
            change, instrument, response, signal, feedback, case, action,
            session, profile, service, dashboard, allowance, step,
        ]

    def test_no_forbidden_or_aggregate_keys_on_any_stored_record(self):
        for record in self._exercise_everything():
            keys = _all_keys(record)
            self.assertEqual(keys & FORBIDDEN_KEYS, set(), record)
            self.assertEqual(keys & AGGREGATE_KEYS, set(), record)

    def test_signature_scan_no_forbidden_params_no_kwargs(self):
        for attr_name in dir(HrExtensionsAddition):
            if attr_name.startswith("_"):
                continue
            member = getattr(HrExtensionsAddition, attr_name)
            if not callable(member):
                continue
            params = inspect.signature(member).parameters
            for param_name, param in params.items():
                self.assertNotIn(param_name, FORBIDDEN_PARAMS, attr_name)
                self.assertNotEqual(
                    param.kind, inspect.Parameter.VAR_KEYWORD, attr_name
                )

    def test_rbac_denials_consume_no_id(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_time_entry("carol", "2026-11-02", 10, "regular", EMPLOYEE)
        with self.assertRaises(PermissionDenied):
            self.ext.record_time_entry("carol", "2026-11-02", 10, "regular", AUDITOR)
        entry = self.ext.record_time_entry(
            "carol", "2026-11-02", 10, "regular", SPECIALIST
        )
        self.assertEqual(entry["id"], "tim-1")
        with self.assertRaises(PermissionDenied):
            self.ext.create_org_unit("hq", "HQ", EMPLOYEE)
        unit = self.ext.create_org_unit("hq", "HQ", ADMIN)
        self.assertEqual(unit["id"], "ogu-1")

    def test_audit_actions_carry_ext2_prefix(self):
        self._exercise_everything()
        actions = {e["action"] for e in self.store.audit.entries()}
        ext_actions = {a for a in actions if a.startswith("ext2_")}
        self.assertIn("ext2_time_entry_create", ext_actions)
        self.assertIn("ext2_leave_account_create", ext_actions)
        self.assertIn("ext2_survey_response_create", ext_actions)
        self.assertIn("ext2_dashboard_create", ext_actions)
        self.assertIn("ext2_allowance_request_create", ext_actions)
        self.assertTrue(all(a.startswith("ext2_") for a in ext_actions))


if __name__ == "__main__":
    unittest.main()
