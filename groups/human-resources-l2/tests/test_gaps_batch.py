"""Final GAPS batch tests -- Group 21, Human Resources L2.

Pins the extension surface in ``src/hr/extensions.py``
(``HrExtensions``, wrapping the core ``HrStore``): one test class
per open GAPS.md entry for this group (see ``../BATCH.md`` for the
per-entry disposition), plus cross-cutting pins -- the founding
privacy discipline over the extension shapes, derived-never-stored,
no aggregate key on any stored extension record, stub labels, RBAC
denials, employee scope, ``ext_``-prefixed audit actions, and the
batch's fresh mutation-verified negative control (the weighted-mean
mutant, ``TestWeightedMeanMutant``).

Fixtures: ``make_store()`` (position "Program Analyst" series 0343
grade 13, person_ref "carol") plus a second person ("erin") where
scope or multi-candidate derivations need one.
"""

import unittest
from fractions import Fraction

from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError
from hr.extensions import AGGREGATE_KEYS, FORBIDDEN_KEYS, HrExtensions


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


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.position, self.person = make_store()
        self.store.create_person("erin", ADMIN, kind="applicant")
        self.ext = HrExtensions(self.store)

    def make_vacancy_with_application(self, person_ref="carol"):
        vacancy = self.store.create_vacancy(
            self.position["id"], "Analyst opening", ADMIN
        )
        application = self.store.create_application(person_ref, vacancy["id"], SPECIALIST)
        return vacancy, application

    def make_panel(self, application_id, ratings, title="Panel"):
        evaluation = self.store.create_evaluation(
            application_id, "panel", title, SPECIALIST
        )
        for i, rating in enumerate(ratings):
            self.store.add_evaluation_entry(
                evaluation["id"], "rater-%d" % (i + 1), rating, "note", SPECIALIST
            )
        return evaluation


class TestMatchingEngines(BatchFixture):
    """Entry: AI talent intelligence & matching engines -- built as
    deterministic rule matching over the core records; the rule is a
    record and the evaluation a derived view with its evidence."""

    def test_rule_record_shape_and_ids(self):
        vacancy, _ = self.make_vacancy_with_application()
        rule = self.ext.create_match_rule(vacancy["id"], SPECIALIST, min_panel_entries=2)
        self.assertEqual(rule["id"], "mtr-1")
        self.assertEqual(rule["vacancy_id"], vacancy["id"])
        self.assertEqual(rule["min_panel_entries"], 2)
        self.assertEqual(rule["stages"], [
            "applied", "screened", "referred", "selected",
            "not_selected", "withdrawn",
        ])
        self.assertFalse(rule["require_completed_panel"])

    def test_evaluate_derives_matches_with_evidence(self):
        vacancy, application = self.make_vacancy_with_application()
        self.make_panel(application["id"], [4, 2, 5])
        rule = self.ext.create_match_rule(vacancy["id"], SPECIALIST, min_panel_entries=2)
        view = self.ext.evaluate_match_rule(rule["id"], ADMIN)
        self.assertEqual(view["method"], "deterministic_rule_match")
        self.assertTrue(view["derived"])
        self.assertFalse(view["stored"])
        self.assertEqual(view["match_count"], 1)
        row = view["matches"][0]
        self.assertEqual(row["person_ref"], "carol")
        self.assertEqual(row["panel_entry_count"], 3)
        self.assertFalse(row["panel_completed"])

    def test_threshold_and_stage_and_completion_filters(self):
        vacancy, application = self.make_vacancy_with_application()
        panel = self.make_panel(application["id"], [4, 2])
        rule = self.ext.create_match_rule(vacancy["id"], SPECIALIST, min_panel_entries=3)
        self.assertEqual(self.ext.evaluate_match_rule(rule["id"], ADMIN)["match_count"], 0)
        rule2 = self.ext.create_match_rule(
            vacancy["id"], SPECIALIST, min_panel_entries=1,
            require_completed_panel=True,
        )
        self.assertEqual(self.ext.evaluate_match_rule(rule2["id"], ADMIN)["match_count"], 0)
        self.store.set_evaluation_state(panel["id"], "completed", SPECIALIST)
        self.assertEqual(self.ext.evaluate_match_rule(rule2["id"], ADMIN)["match_count"], 1)
        rule3 = self.ext.create_match_rule(
            vacancy["id"], SPECIALIST, stages=["referred"]
        )
        self.assertEqual(self.ext.evaluate_match_rule(rule3["id"], ADMIN)["match_count"], 0)
        self.store.set_application_stage(application["id"], "referred", SPECIALIST)
        self.assertEqual(self.ext.evaluate_match_rule(rule3["id"], ADMIN)["match_count"], 1)

    def test_employee_sees_only_own_matches(self):
        vacancy, application = self.make_vacancy_with_application()
        self.make_panel(application["id"], [5])
        other = self.store.create_application("erin", vacancy["id"], SPECIALIST)
        self.make_panel(other["id"], [5])
        rule = self.ext.create_match_rule(vacancy["id"], SPECIALIST)
        view = self.ext.evaluate_match_rule(rule["id"], EMPLOYEE)
        self.assertEqual(view["match_count"], 1)
        self.assertEqual(view["matches"][0]["person_ref"], "carol")

    def test_validation_and_no_id_consumed(self):
        vacancy, _ = self.make_vacancy_with_application()
        with self.assertRaises(ValidationError):
            self.ext.create_match_rule(vacancy["id"], SPECIALIST, min_panel_entries=-1)
        with self.assertRaises(ValidationError):
            self.ext.create_match_rule(vacancy["id"], SPECIALIST, min_panel_entries=True)
        with self.assertRaises(NotFoundError):
            self.ext.create_match_rule("vac-99", SPECIALIST)
        rule = self.ext.create_match_rule(vacancy["id"], SPECIALIST)
        self.assertEqual(rule["id"], "mtr-1")


class TestClassificationIntelligence(BatchFixture):
    """Entry: Position classification intelligence -- a reference
    library (records) plus a deterministic keyword derivation."""

    def test_recommendation_matches_title_keywords(self):
        self.ext.create_classification_reference("0343", "13", ["analyst"], ADMIN)
        self.ext.create_classification_reference("2210", "12", ["technology"], ADMIN)
        view = self.ext.recommend_classification(self.position["id"], ADMIN)
        self.assertEqual(view["method"], "deterministic_keyword_match")
        self.assertEqual(len(view["matches"]), 1)
        self.assertEqual(view["recommended"]["series"], "0343")
        self.assertEqual(view["recommended"]["matched_keywords"], ["analyst"])

    def test_recommendation_orders_by_keyword_count(self):
        self.ext.create_classification_reference("9999", "9", ["analyst"], ADMIN)
        self.ext.create_classification_reference(
            "0343", "13", ["analyst", "program"], ADMIN
        )
        view = self.ext.recommend_classification(self.position["id"], ADMIN)
        self.assertEqual(view["recommended"]["reference_id"], "clr-2")
        self.assertEqual(len(view["matches"][0]["matched_keywords"]), 2)

    def test_no_match_recommends_none_and_comparison_null(self):
        view = self.ext.recommend_classification(self.position["id"], ADMIN)
        self.assertIsNone(view["recommended"])
        comparison = self.ext.classification_comparison(self.position["id"], ADMIN)
        self.assertEqual(comparison["recorded_series"], "0343")
        self.assertIsNone(comparison["recommended_series"])
        self.assertIsNone(comparison["agrees"])

    def test_comparison_agrees_and_position_unchanged(self):
        self.ext.create_classification_reference("0343", "13", ["analyst"], ADMIN)
        before = self.store.get_position(self.position["id"], ADMIN)
        comparison = self.ext.classification_comparison(self.position["id"], ADMIN)
        self.assertTrue(comparison["agrees"])
        self.assertEqual(self.store.get_position(self.position["id"], ADMIN), before)

    def test_reference_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_classification_reference("0343", "13", [], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_classification_reference("0343", "13", ["  "], ADMIN)


class TestJobAnalysisAndCreditingPlans(BatchFixture):
    """Entry: Job analysis & crediting-plan tooling -- analysis
    records bound to positions; crediting plans recording their
    weights as data (the inspectable rule for the scoring view)."""

    def test_job_analysis_record(self):
        analysis = self.ext.create_job_analysis(self.position["id"], [
            {"competency_ref": "analysis", "description": "Analyze data",
             "level_label": "advanced"},
            {"competency_ref": "writing", "description": "Write reports",
             "level_label": "intermediate"},
        ], SPECIALIST)
        self.assertEqual(analysis["id"], "jan-1")
        self.assertEqual(len(analysis["competencies"]), 2)
        self.assertEqual(
            self.ext.list_job_analyses(ADMIN, position_id=self.position["id"])[0]["id"],
            "jan-1",
        )

    def test_job_analysis_validation(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_job_analysis("pos-99", [
                {"competency_ref": "x", "description": "", "level_label": "y"},
            ], SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.create_job_analysis(self.position["id"], [
                {"competency_ref": "x", "description": "", "level_label": "y"},
                {"competency_ref": "x", "description": "", "level_label": "z"},
            ], SPECIALIST)

    def test_crediting_plan_records_weights_as_data(self):
        vacancy, application = self.make_vacancy_with_application()
        panel_a = self.make_panel(application["id"], [4], title="Panel A")
        panel_b = self.make_panel(application["id"], [2], title="Panel B")
        plan = self.ext.create_crediting_plan(vacancy["id"], [
            {"evaluation_id": panel_a["id"], "weight": 75},
            {"evaluation_id": panel_b["id"], "weight": 25},
        ], SPECIALIST)
        self.assertEqual(plan["id"], "crp-1")
        self.assertEqual(plan["criteria"][0]["weight"], 75)
        self.assertEqual(
            self.ext.list_crediting_plans(ADMIN, vacancy_id=vacancy["id"])[0]["id"],
            "crp-1",
        )

    def test_crediting_plan_validation(self):
        vacancy, application = self.make_vacancy_with_application()
        panel = self.make_panel(application["id"], [4])
        assessment = self.store.create_evaluation(
            application["id"], "assessment", "Test", SPECIALIST
        )
        with self.assertRaises(ValidationError):  # weights must sum to 100
            self.ext.create_crediting_plan(vacancy["id"], [
                {"evaluation_id": panel["id"], "weight": 60},
            ], SPECIALIST)
        with self.assertRaises(ValidationError):  # panels only
            self.ext.create_crediting_plan(vacancy["id"], [
                {"evaluation_id": assessment["id"], "weight": 100},
            ], SPECIALIST)
        with self.assertRaises(ValidationError):  # bool weight rejected
            self.ext.create_crediting_plan(vacancy["id"], [
                {"evaluation_id": panel["id"], "weight": True},
            ], SPECIALIST)
        other_vacancy, other_app = self.make_vacancy_with_application("erin")
        other_panel = self.make_panel(other_app["id"], [3])
        with self.assertRaises(ValidationError):  # panel of another vacancy
            self.ext.create_crediting_plan(vacancy["id"], [
                {"evaluation_id": other_panel["id"], "weight": 100},
            ], SPECIALIST)
        plan = self.ext.create_crediting_plan(vacancy["id"], [
            {"evaluation_id": panel["id"], "weight": 100},
        ], SPECIALIST)
        self.assertEqual(plan["id"], "crp-1")  # failures consumed no id


class TestScoringComputation(BatchFixture):
    """Entry: Weighted cumulative & consensus scoring computation --
    built as derived views over the verbatim ratings: computed at
    read, stored nowhere, the core evaluation records unchanged."""

    def _plan(self, weights_ratings):
        vacancy, application = self.make_vacancy_with_application()
        criteria = []
        panels = []
        for i, (weight, ratings) in enumerate(weights_ratings):
            panel = self.make_panel(application["id"], ratings, title="Panel %d" % i)
            panels.append(panel)
            criteria.append({"evaluation_id": panel["id"], "weight": weight})
        plan = self.ext.create_crediting_plan(vacancy["id"], criteria, SPECIALIST)
        return vacancy, application, panels, plan

    def test_weighted_cumulative_exact_fraction(self):
        _, _, _, plan = self._plan([(75, [4, 2]), (25, [5])])
        view = self.ext.panel_score_view(plan["id"], ADMIN)
        self.assertEqual(view["method"], "weighted_mean_of_verbatim_ratings")
        self.assertTrue(view["derived"])
        self.assertFalse(view["stored"])
        self.assertEqual(view["criteria"][0]["criterion_mean"], Fraction(3, 1))
        self.assertEqual(view["criteria"][1]["criterion_mean"], Fraction(5, 1))
        self.assertEqual(view["criteria"][0]["ratings"], [4, 2])
        self.assertEqual(view["weighted_cumulative"], Fraction(7, 2))
        self.assertEqual(view["pending_criteria"], [])

    def test_pending_criterion_excluded_and_named(self):
        vacancy, application = self.make_vacancy_with_application()
        rated = self.make_panel(application["id"], [4], title="Rated")
        empty = self.store.create_evaluation(
            application["id"], "panel", "Empty", SPECIALIST
        )
        plan = self.ext.create_crediting_plan(vacancy["id"], [
            {"evaluation_id": rated["id"], "weight": 50},
            {"evaluation_id": empty["id"], "weight": 50},
        ], SPECIALIST)
        view = self.ext.panel_score_view(plan["id"], ADMIN)
        self.assertEqual(view["pending_criteria"], [empty["id"]])
        self.assertIsNone(view["criteria"][1]["criterion_mean"])
        self.assertEqual(view["weighted_cumulative"], Fraction(4, 1))

    def test_score_view_stores_nothing_and_changes_nothing(self):
        _, application, panels, plan = self._plan([(60, [3, 5]), (40, [2])])
        before = self.store.get_evaluation(panels[0]["id"], ADMIN)
        counts_before = {
            name: len(getattr(self.ext, name))
            for name in vars(self.ext) if isinstance(getattr(self.ext, name), dict)
        }
        first = self.ext.panel_score_view(plan["id"], ADMIN)
        second = self.ext.panel_score_view(plan["id"], ADMIN)
        self.assertEqual(first, second)
        counts_after = {
            name: len(getattr(self.ext, name))
            for name in vars(self.ext) if isinstance(getattr(self.ext, name), dict)
        }
        self.assertEqual(counts_before, counts_after)
        self.assertEqual(self.store.get_evaluation(panels[0]["id"], ADMIN), before)
        self.assertNotIn("aggregate", _all_keys(before))
        stored_plan = self.ext.get_crediting_plan(plan["id"], ADMIN)
        self.assertFalse(_all_keys(stored_plan) & AGGREGATE_KEYS)

    def test_consensus_view_mean_and_spread(self):
        _, application = self.make_vacancy_with_application()
        panel = self.make_panel(application["id"], [2, 4, 5])
        view = self.ext.panel_consensus_view(panel["id"], ADMIN)
        self.assertEqual(view["ratings"], [2, 4, 5])
        self.assertEqual(view["mean"], Fraction(11, 3))
        self.assertEqual(view["consensus_spread"], Fraction(3, 1))
        self.assertEqual(view["rater_count"], 3)

    def test_consensus_view_rejects_assessment_kind(self):
        _, application = self.make_vacancy_with_application()
        assessment = self.store.create_evaluation(
            application["id"], "assessment", "Test", SPECIALIST
        )
        with self.assertRaises(ValidationError):
            self.ext.panel_consensus_view(assessment["id"], ADMIN)

    def test_score_view_employee_scope(self):
        _, _, _, plan = self._plan([(100, [4])])
        view = self.ext.panel_score_view(plan["id"], EMPLOYEE)
        self.assertEqual(view["weighted_cumulative"], Fraction(4, 1))
        vacancy2, application2 = self.make_vacancy_with_application("erin")
        panel2 = self.make_panel(application2["id"], [3])
        plan2 = self.ext.create_crediting_plan(vacancy2["id"], [
            {"evaluation_id": panel2["id"], "weight": 100},
        ], SPECIALIST)
        with self.assertRaises(PermissionDenied):
            self.ext.panel_score_view(plan2["id"], EMPLOYEE)


class TestWeightedMeanMutant(BatchFixture):
    """Fresh negative control for the batch: a mutant extension whose
    ``_weighted_cumulative`` ignores the recorded weights (a plain
    mean of criterion means). The canonical weighted expectation
    must hold for the real implementation and must NOT hold for the
    mutant -- the recorded weights are load-bearing."""

    def _fixture_plan(self, ext):
        vacancy = self.store.create_vacancy(self.position["id"], "Opening", ADMIN)
        application = self.store.create_application("carol", vacancy["id"], SPECIALIST)
        criteria = []
        for title, ratings, weight in (("A", [4, 2], 75), ("B", [5], 25)):
            evaluation = self.store.create_evaluation(
                application["id"], "panel", title, SPECIALIST
            )
            for i, rating in enumerate(ratings):
                self.store.add_evaluation_entry(
                    evaluation["id"], "rater-%d" % i, rating, "n", SPECIALIST
                )
            criteria.append({"evaluation_id": evaluation["id"], "weight": weight})
        return ext.create_crediting_plan(vacancy["id"], criteria, SPECIALIST)

    def test_weights_are_load_bearing_canonical(self):
        plan = self._fixture_plan(self.ext)
        view = self.ext.panel_score_view(plan["id"], ADMIN)
        # Weighted: (75*3 + 25*5) / 100 = 7/2. Unweighted mean of
        # means would be 4 -- a different, wrong answer.
        self.assertEqual(view["weighted_cumulative"], Fraction(7, 2))

        class MutantExtensions(HrExtensions):
            def _weighted_cumulative(self, weighted_means):
                means = [mean for _, mean in weighted_means]
                return sum(means, Fraction(0)) / len(means)

        mutant = MutantExtensions(self.store)
        mutant_plan = self._fixture_plan(mutant)
        mutant_view = mutant.panel_score_view(mutant_plan["id"], ADMIN)
        self.assertEqual(mutant_view["weighted_cumulative"], Fraction(4, 1))
        self.assertNotEqual(
            mutant_view["weighted_cumulative"], view["weighted_cumulative"]
        )
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant_view["weighted_cumulative"], Fraction(7, 2)
            )


class TestCertificates(BatchFixture):
    """Entry: Certificates of eligibles as standalone assembled
    documents -- the document record assembles the referred
    applications; entries and count are derived at read."""

    def test_assembly_collects_referred_only(self):
        vacancy, application = self.make_vacancy_with_application()
        other = self.store.create_application("erin", vacancy["id"], SPECIALIST)
        self.store.set_application_stage(application["id"], "referred", SPECIALIST)
        cert = self.ext.assemble_certificate(vacancy["id"], SPECIALIST)
        self.assertEqual(cert["id"], "crt-1")
        self.assertEqual(cert["application_ids"], [application["id"]])
        view = self.ext.get_certificate(cert["id"], ADMIN)
        self.assertEqual(view["entry_count"], 1)
        self.assertEqual(view["entries"][0]["person_ref"], "carol")
        self.assertEqual(view["entries"][0]["stage"], "referred")
        # The stored record holds ids only; person_refs are derived.
        self.assertNotIn("entries", cert)

    def test_annotate_appends(self):
        vacancy, _ = self.make_vacancy_with_application()
        cert = self.ext.assemble_certificate(vacancy["id"], SPECIALIST)
        updated = self.ext.annotate_certificate(cert["id"], "Reviewed by SO", SPECIALIST)
        self.assertEqual(len(updated["annotations"]), 1)
        self.assertEqual(updated["annotations"][0]["note"], "Reviewed by SO")

    def test_employee_cannot_read_multi_person_certificate(self):
        vacancy, application = self.make_vacancy_with_application()
        other = self.store.create_application("erin", vacancy["id"], SPECIALIST)
        self.store.set_application_stage(application["id"], "referred", SPECIALIST)
        self.store.set_application_stage(other["id"], "referred", SPECIALIST)
        cert = self.ext.assemble_certificate(vacancy["id"], SPECIALIST)
        with self.assertRaises(PermissionDenied):
            self.ext.get_certificate(cert["id"], EMPLOYEE)
        self.assertEqual(self.ext.list_certificates(EMPLOYEE), [])
        self.assertEqual(len(self.ext.list_certificates(ADMIN)), 1)

    def test_employee_reads_own_only_certificate(self):
        vacancy, application = self.make_vacancy_with_application()
        self.store.set_application_stage(application["id"], "referred", SPECIALIST)
        cert = self.ext.assemble_certificate(vacancy["id"], SPECIALIST)
        view = self.ext.get_certificate(cert["id"], EMPLOYEE)
        self.assertEqual(view["entry_count"], 1)


class TestOutreachPlatforms(BatchFixture):
    """Entry: Career sites, talent communities, campus recruiting &
    events platforms -- outreach records only; nothing is served,
    published, or sent."""

    def test_career_site_lifecycle(self):
        site = self.ext.create_career_site("agency-careers", "Agency Careers", SPECIALIST)
        self.assertEqual(site["id"], "cst-1")
        self.assertEqual(site["state"], "draft")
        updated = self.ext.set_career_site_state(site["id"], "published", SPECIALIST)
        self.assertEqual(updated["state"], "published")
        with self.assertRaises(ValidationError):
            self.ext.create_career_site("agency-careers", "Duplicate", SPECIALIST)

    def test_community_membership(self):
        community = self.ext.create_community("analysts", "Analyst Community", SPECIALIST)
        member = self.ext.add_community_member(community["id"], "carol", SPECIALIST)
        self.assertEqual(member["id"], "cmm-1")
        with self.assertRaises(ValidationError):
            self.ext.add_community_member(community["id"], "carol", SPECIALIST)
        with self.assertRaises(NotFoundError):
            self.ext.add_community_member(community["id"], "ghost", SPECIALIST)
        members = self.ext.list_community_members(community["id"], ADMIN)
        self.assertEqual(len(members), 1)
        own = self.ext.list_community_members(community["id"], EMPLOYEE)
        self.assertEqual(len(own), 1)

    def test_event_registration_and_derived_count(self):
        event = self.ext.create_recruiting_event("Campus Day", "2027-03-15", SPECIALIST)
        self.assertEqual(self.ext.get_recruiting_event(event["id"], ADMIN)["registration_count"], 0)
        self.ext.register_for_event(event["id"], "carol", SPECIALIST)
        self.ext.register_for_event(event["id"], "erin", SPECIALIST)
        view = self.ext.get_recruiting_event(event["id"], ADMIN)
        self.assertEqual(view["registration_count"], 2)
        self.assertNotIn("registration_count", self.ext._events[event["id"]])
        with self.assertRaises(ValidationError):
            self.ext.register_for_event(event["id"], "carol", SPECIALIST)
        regs = self.ext.list_event_registrations(event["id"], EMPLOYEE)
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0]["person_ref"], "carol")


class TestMobilityMarketplace(BatchFixture):
    """Entry: Talent mobility & workforce-exchange marketplace
    engines -- listing and interest records; matching is a
    deterministic series-overlap derivation with its evidence."""

    def test_listing_and_interest(self):
        listing = self.ext.create_mobility_listing(self.position["id"], "detail", SPECIALIST)
        self.assertEqual(listing["id"], "lst-1")
        interest = self.ext.record_mobility_interest(listing["id"], "carol", SPECIALIST)
        self.assertEqual(interest["id"], "int-1")
        with self.assertRaises(ValidationError):
            self.ext.record_mobility_interest(listing["id"], "carol", SPECIALIST)
        self.ext.set_mobility_listing_state(listing["id"], "closed", SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.record_mobility_interest(listing["id"], "erin", SPECIALIST)

    def test_matches_derive_from_application_series_evidence(self):
        self.make_vacancy_with_application()  # carol applied to a 0343 position
        other_position = self.store.create_position(
            "IT Specialist", ADMIN, series="2210", grade="12"
        )
        match_listing = self.ext.create_mobility_listing(
            self.position["id"], "rotation", SPECIALIST
        )
        self.ext.create_mobility_listing(other_position["id"], "exchange", SPECIALIST)
        view = self.ext.mobility_matches("carol", ADMIN)
        self.assertEqual(view["method"], "deterministic_series_overlap")
        self.assertEqual(view["evidence_series"], ["0343"])
        self.assertEqual(view["match_count"], 1)
        self.assertEqual(view["matches"][0]["listing_id"], match_listing["id"])
        empty = self.ext.mobility_matches("erin", ADMIN)
        self.assertEqual(empty["match_count"], 0)
        with self.assertRaises(PermissionDenied):
            self.ext.mobility_matches("erin", EMPLOYEE)


class TestTalentManagementDepth(BatchFixture):
    """Entry: Talent management suite depth beyond records --
    development-program records and enrollments with derived counts."""

    def test_program_enrollment_summary(self):
        program = self.ext.create_development_program(
            "mentor-2027", "Mentoring 2027", "mentoring", SPECIALIST
        )
        self.assertEqual(program["id"], "prg-1")
        enrollment = self.ext.enroll_in_program(program["id"], "carol", SPECIALIST)
        self.ext.enroll_in_program(program["id"], "erin", SPECIALIST)
        with self.assertRaises(ValidationError):
            self.ext.enroll_in_program(program["id"], "carol", SPECIALIST)
        self.ext.set_enrollment_state(enrollment["id"], "completed", SPECIALIST)
        summary = self.ext.program_summary(program["id"], ADMIN)
        self.assertEqual(summary["enrollments"], 2)
        self.assertEqual(summary["enrollments_by_state"]["completed"], 1)
        self.assertEqual(summary["enrollments_by_state"]["enrolled"], 1)
        own = self.ext.list_enrollments(EMPLOYEE)
        self.assertEqual(len(own), 1)
        self.assertEqual(own[0]["person_ref"], "carol")

    def test_program_summary_requires_report_read(self):
        program = self.ext.create_development_program(
            "retain", "Retention", "retention", SPECIALIST
        )
        with self.assertRaises(PermissionDenied):
            self.ext.program_summary(program["id"], EMPLOYEE)


class TestWorkforcePlanning(BatchFixture):
    """Entry: Workforce planning & resource-management analytics /
    models -- deterministic counts over the core records and
    scenario records whose projections derive at read."""

    def test_analytics_counts_and_vacancy_rate(self):
        self.make_vacancy_with_application()
        analytics = self.ext.workforce_analytics(ADMIN)
        self.assertEqual(analytics["method"], "deterministic_counts")
        self.assertEqual(analytics["persons"], 2)
        self.assertEqual(analytics["active_persons"], 1)
        self.assertEqual(analytics["positions"], 1)
        self.assertEqual(analytics["vacant_positions"], 1)
        self.assertEqual(analytics["vacancy_rate_bps"], 10000)
        self.assertEqual(analytics["applications_by_stage"], {"applied": 1})
        with self.assertRaises(PermissionDenied):
            self.ext.workforce_analytics(EMPLOYEE)

    def test_scenario_projection_integer_derivation(self):
        for i in range(9):
            self.store.create_person("person-%d" % i, ADMIN, kind="employee")
        scenario = self.ext.create_planning_scenario("10% attrition", 1000, 2, ADMIN)
        self.assertEqual(scenario["id"], "scn-1")
        projection = self.ext.scenario_projection(scenario["id"], ADMIN)
        self.assertEqual(projection["starting_active_persons"], 10)
        self.assertEqual(projection["periods"][0]["projected_separations"], 1)
        self.assertEqual(projection["periods"][0]["projected_headcount"], 9)
        self.assertEqual(projection["periods"][1]["projected_separations"], 0)
        self.assertEqual(projection["periods"][1]["projected_headcount"], 9)
        stored = self.ext.get_planning_scenario(scenario["id"], ADMIN)
        self.assertNotIn("periods", stored)
        again = self.ext.scenario_projection(scenario["id"], ADMIN)
        self.assertEqual(projection, again)

    def test_scenario_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.create_planning_scenario("bad", 10001, 2, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_planning_scenario("bad", 1000, 0, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_planning_scenario("bad", True, 2, ADMIN)


class TestRetirementCalculator(BatchFixture):
    """Entry: Retirement benefits calculator -- integer accrual
    arithmetic over recorded inputs, derived at read, paying nothing;
    no currency amount (no record may hold a pay figure)."""

    def test_estimate_derivation(self):
        self.ext.create_retirement_plan_parameters("fers-like", 100, 60, ADMIN)
        estimate = self.ext.retirement_estimate("carol", "fers-like", 120, ADMIN)
        self.assertEqual(estimate["method"], "integer_accrual_derivation")
        self.assertEqual(estimate["service_years"], 10)
        self.assertEqual(estimate["accrued_bps"], 1000)
        self.assertTrue(estimate["vested"])
        self.assertIsNone(estimate["currency_amount"])
        self.assertTrue(estimate["pays_nothing"])
        early = self.ext.retirement_estimate("carol", "fers-like", 30, ADMIN)
        self.assertEqual(early["accrued_bps"], 250)
        self.assertFalse(early["vested"])

    def test_estimate_validation_and_scope(self):
        self.ext.create_retirement_plan_parameters("fers-like", 100, 60, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.retirement_estimate("carol", "fers-like", True, ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.retirement_estimate("carol", "nope", 120, ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.retirement_estimate("ghost", "fers-like", 120, ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.retirement_estimate("erin", "fers-like", 120, EMPLOYEE)
        own = self.ext.retirement_estimate("carol", "fers-like", 120, EMPLOYEE)
        self.assertEqual(own["accrued_bps"], 1000)
        with self.assertRaises(ValidationError):  # duplicate plan_ref
            self.ext.create_retirement_plan_parameters("fers-like", 110, 60, ADMIN)


class TestLearningDelivery(BatchFixture):
    """Entry: Employee learning & upskilling delivery -- catalog and
    assignment records with a derived per-person summary; nothing is
    delivered to anyone."""

    def test_assignment_flow_and_summary(self):
        course = self.ext.create_course("SEC-101", "Security Basics", SPECIALIST)
        assignment = self.ext.assign_course("carol", course["id"], SPECIALIST)
        self.assertEqual(assignment["id"], "lrn-1")
        with self.assertRaises(ValidationError):
            self.ext.assign_course("carol", course["id"], SPECIALIST)
        self.ext.set_learning_state(assignment["id"], "in_progress", SPECIALIST)
        summary = self.ext.learning_summary("carol", ADMIN)
        self.assertEqual(summary["assignments"], 1)
        self.assertEqual(summary["assignments_by_state"]["in_progress"], 1)
        self.ext.set_learning_state(assignment["id"], "completed", SPECIALIST)
        again = self.ext.assign_course("carol", course["id"], SPECIALIST)
        self.assertEqual(again["id"], "lrn-2")
        own = self.ext.list_learning_assignments(EMPLOYEE)
        self.assertEqual(len(own), 2)
        with self.assertRaises(PermissionDenied):
            self.ext.learning_summary("erin", EMPLOYEE)


class TestDocumentAssembly(BatchFixture):
    """Entry: Document & template assembly engines -- template
    records with validated placeholders; assembly substitutes one
    core record's recorded fields into a document artifact."""

    def test_assembly_substitutes_recorded_fields(self):
        template = self.ext.create_template(
            "position-summary", "Position Summary", "position",
            "Position {title} (series {series}, grade {grade}) is {status}.",
            SPECIALIST,
        )
        self.assertEqual(template["placeholders"], ["title", "series", "grade", "status"])
        document = self.ext.assemble_document(template["id"], self.position["id"], SPECIALIST)
        self.assertEqual(document["id"], "doc-1")
        self.assertEqual(
            document["text"],
            "Position Program Analyst (series 0343, grade 13) is vacant.",
        )
        self.assertEqual(
            self.store.get_position(self.position["id"], ADMIN)["title"],
            "Program Analyst",
        )

    def test_template_placeholder_validation(self):
        with self.assertRaises(ValidationError):  # salary is not a position field
            self.ext.create_template("bad", "Bad", "position", "Pay: {salary}", SPECIALIST)
        with self.assertRaises(ValidationError):  # unclosed placeholder
            self.ext.create_template("bad2", "Bad", "position", "Title {title", SPECIALIST)
        with self.assertRaises(ValidationError):  # cross-kind field
            self.ext.create_template(
                "bad3", "Bad", "vacancy", "Series {series}", SPECIALIST
            )

    def test_assembly_unknown_source(self):
        template = self.ext.create_template(
            "vacancy-note", "Vacancy Note", "vacancy", "{title} is {status}.", SPECIALIST
        )
        with self.assertRaises(NotFoundError):
            self.ext.assemble_document(template["id"], "vac-99", SPECIALIST)


class TestStubSurfaces(BatchFixture):
    """Stub-engine entries (4): applicant-tracking workflow engines,
    assessment delivery & content, integration connector engines,
    general cloud hosting / platform services -- all labeled
    reference implementations: records only, never execution, and
    creating any of them changes no core record."""

    def _core_snapshot(self):
        report = self.store.report(ADMIN)
        return report

    def test_workflow_definition_is_reference_data_only(self):
        vacancy, application = self.make_vacancy_with_application()
        before = self._core_snapshot()
        workflow = self.ext.create_workflow_definition(
            "fedhire-flow", "FedHire-style flow", ["applied", "screened", "referred"],
            SPECIALIST,
        )
        self.assertTrue(workflow["reference_stub"])
        self.assertEqual(workflow["state"], "recorded_reference_only")
        self.assertEqual(workflow["steps"], ["applied", "screened", "referred"])
        self.assertEqual(
            self.store.get_application(application["id"], ADMIN)["stage"], "applied"
        )
        self.assertEqual(self._core_snapshot(), before)
        with self.assertRaises(ValidationError):
            self.ext.create_workflow_definition("bad", "Bad", ["teleported"], SPECIALIST)

    def test_posting_request_is_reference_transport(self):
        vacancy, _ = self.make_vacancy_with_application()
        before = self._core_snapshot()
        posting = self.ext.record_posting_request(vacancy["id"], "usajobs", SPECIALIST)
        self.assertTrue(posting["reference_stub"])
        self.assertTrue(posting["reference_transport"])
        self.assertEqual(posting["state"], "recorded_reference_only")
        self.assertEqual(self._core_snapshot(), before)
        self.assertEqual(
            self.store.get_vacancy(vacancy["id"], ADMIN)["status"], "draft"
        )

    def test_assessment_content_and_delivery_records(self):
        _, application = self.make_vacancy_with_application()
        evaluation = self.store.create_evaluation(
            application["id"], "assessment", "Written test", SPECIALIST
        )
        content = self.ext.create_assessment_content(
            "writing-101", "Writing Assessment", "provider-x", SPECIALIST
        )
        self.assertTrue(content["reference_stub"])
        self.assertEqual(
            set(content.keys()),
            {"id", "content_ref", "title", "provider_ref", "reference_stub",
             "state", "created_by", "created_utc"},
        )
        delivery = self.ext.record_assessment_delivery(
            evaluation["id"], "provider-x", SPECIALIST
        )
        self.assertTrue(delivery["reference_stub"])
        self.assertEqual(delivery["state"], "recorded_reference_only")
        self.assertEqual(
            self.store.get_evaluation(evaluation["id"], ADMIN)["state"], "scheduled"
        )
        own = self.ext.list_assessment_deliveries(EMPLOYEE)
        self.assertEqual(len(own), 1)

    def test_connector_and_sync_records(self):
        before = self._core_snapshot()
        connector = self.ext.create_connector("conn-usajobs", "usajobs", "outbound", ADMIN)
        self.assertTrue(connector["reference_stub"])
        sync = self.ext.record_sync(connector["id"], "vacancy", 12, ADMIN)
        self.assertTrue(sync["reference_stub"])
        self.assertTrue(sync["reference_transport"])
        self.assertEqual(sync["record_count"], 12)
        self.assertEqual(self._core_snapshot(), before)
        with self.assertRaises(ValidationError):
            self.ext.record_sync(connector["id"], "vacancy", -1, ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.create_connector("conn-bad", "x", "sideways", ADMIN)

    def test_hosting_record_states_platform_posture(self):
        record = self.ext.create_hosting_record("reference-deployment", ADMIN)
        self.assertTrue(record["reference_stub"])
        self.assertEqual(record["tenancy"], "single_tenant_reference")
        self.assertEqual(record["state"], "recorded_reference_only")
        self.assertIn("PLATFORM-LAYER", record["platform_layer"])
        self.assertEqual(len(self.ext.list_hosting_records(AUDITOR)), 1)


class TestCrossCutting(BatchFixture):
    """Cross-cutting pins over the whole extension surface."""

    def _exercise_everything(self):
        vacancy, application = self.make_vacancy_with_application()
        panel = self.make_panel(application["id"], [4, 2])
        records = []
        records.append(self.ext.create_match_rule(vacancy["id"], SPECIALIST))
        records.append(self.ext.create_classification_reference("0343", "13", ["analyst"], ADMIN))
        records.append(self.ext.create_job_analysis(self.position["id"], [
            {"competency_ref": "c1", "description": "d", "level_label": "l"},
        ], SPECIALIST))
        records.append(self.ext.create_crediting_plan(vacancy["id"], [
            {"evaluation_id": panel["id"], "weight": 100},
        ], SPECIALIST))
        self.store.set_application_stage(application["id"], "referred", SPECIALIST)
        records.append(self.ext.assemble_certificate(vacancy["id"], SPECIALIST))
        records.append(self.ext.create_career_site("site", "Site", SPECIALIST))
        community = self.ext.create_community("comm", "Community", SPECIALIST)
        records.append(community)
        records.append(self.ext.add_community_member(community["id"], "carol", SPECIALIST))
        event = self.ext.create_recruiting_event("Event", "2027-01-10", SPECIALIST)
        records.append(event)
        records.append(self.ext.register_for_event(event["id"], "carol", SPECIALIST))
        listing = self.ext.create_mobility_listing(self.position["id"], "detail", SPECIALIST)
        records.append(listing)
        records.append(self.ext.record_mobility_interest(listing["id"], "carol", SPECIALIST))
        program = self.ext.create_development_program("prog", "Program", "development", SPECIALIST)
        records.append(program)
        records.append(self.ext.enroll_in_program(program["id"], "carol", SPECIALIST))
        records.append(self.ext.create_planning_scenario("Scenario", 500, 3, ADMIN))
        records.append(self.ext.create_retirement_plan_parameters("plan", 100, 60, ADMIN))
        course = self.ext.create_course("CRS", "Course", SPECIALIST)
        records.append(course)
        records.append(self.ext.assign_course("carol", course["id"], SPECIALIST))
        template = self.ext.create_template("tpl", "Template", "position", "{title}", SPECIALIST)
        records.append(template)
        records.append(self.ext.assemble_document(template["id"], self.position["id"], SPECIALIST))
        records.append(self.ext.create_workflow_definition("wf", "Workflow", ["applied"], SPECIALIST))
        records.append(self.ext.record_posting_request(vacancy["id"], "board", SPECIALIST))
        records.append(self.ext.create_assessment_content("cnt", "Content", "prov", SPECIALIST))
        evaluation = self.store.create_evaluation(application["id"], "assessment", "A", SPECIALIST)
        records.append(self.ext.record_assessment_delivery(evaluation["id"], "prov", SPECIALIST))
        connector = self.ext.create_connector("con", "usajobs", "outbound", ADMIN)
        records.append(connector)
        records.append(self.ext.record_sync(connector["id"], "vacancy", 1, ADMIN))
        records.append(self.ext.create_hosting_record("host", ADMIN))
        return records

    def test_no_forbidden_or_aggregate_keys_on_stored_records(self):
        for record in self._exercise_everything():
            keys = _all_keys(record)
            self.assertFalse(keys & FORBIDDEN_KEYS, (record["id"], keys & FORBIDDEN_KEYS))
            self.assertFalse(keys & AGGREGATE_KEYS, (record["id"], keys & AGGREGATE_KEYS))

    def test_stub_labels_on_every_stub_record(self):
        self._exercise_everything()
        for record in self.ext.list_workflow_definitions(ADMIN):
            self.assertTrue(record["reference_stub"])
        for record in self.ext.list_posting_requests(ADMIN):
            self.assertTrue(record["reference_stub"])
            self.assertTrue(record["reference_transport"])
        for record in self.ext.list_assessment_deliveries(ADMIN):
            self.assertTrue(record["reference_stub"])
        for record in self.ext.list_connectors(ADMIN):
            self.assertTrue(record["reference_stub"])
        for record in self.ext.list_syncs(ADMIN):
            self.assertTrue(record["reference_stub"])
            self.assertTrue(record["reference_transport"])
        for record in self.ext.list_hosting_records(ADMIN):
            self.assertTrue(record["reference_stub"])

    def test_rbac_denials_and_no_id_consumed(self):
        vacancy, _ = self.make_vacancy_with_application()
        with self.assertRaises(PermissionDenied):  # employee may not write
            self.ext.create_match_rule(vacancy["id"], EMPLOYEE)
        with self.assertRaises(PermissionDenied):  # auditor may not write
            self.ext.create_classification_reference("0343", "13", ["x"], AUDITOR)
        with self.assertRaises(PermissionDenied):  # no actor at all
            self.ext.create_match_rule(vacancy["id"], None)
        rule = self.ext.create_match_rule(vacancy["id"], SPECIALIST)
        self.assertEqual(rule["id"], "mtr-1")

    def test_audit_records_ext_actions_and_denials_record_nothing(self):
        audit = self.store.audit
        before = len(audit.entries())
        self.ext.create_classification_reference("0343", "13", ["analyst"], ADMIN)
        entries = audit.entries()
        self.assertEqual(len(entries), before + 1)
        self.assertTrue(entries[-1]["action"].startswith("ext_"))
        with self.assertRaises(PermissionDenied):
            self.ext.create_classification_reference("2210", "12", ["x"], AUDITOR)
        self.assertEqual(len(audit.entries()), before + 1)

    def test_derivations_are_repeatable_and_store_nothing(self):
        vacancy, application = self.make_vacancy_with_application()
        panel = self.make_panel(application["id"], [3, 5])
        plan = self.ext.create_crediting_plan(vacancy["id"], [
            {"evaluation_id": panel["id"], "weight": 100},
        ], SPECIALIST)
        rule = self.ext.create_match_rule(vacancy["id"], SPECIALIST)
        counts = {
            name: len(getattr(self.ext, name))
            for name in vars(self.ext) if isinstance(getattr(self.ext, name), dict)
        }
        for _ in range(2):
            self.ext.panel_score_view(plan["id"], ADMIN)
            self.ext.panel_consensus_view(panel["id"], ADMIN)
            self.ext.evaluate_match_rule(rule["id"], ADMIN)
            self.ext.recommend_classification(self.position["id"], ADMIN)
            self.ext.workforce_analytics(ADMIN)
            self.ext.mobility_matches("carol", ADMIN)
        after = {
            name: len(getattr(self.ext, name))
            for name in vars(self.ext) if isinstance(getattr(self.ext, name), dict)
        }
        self.assertEqual(counts, after)
