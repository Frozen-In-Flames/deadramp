"""Final GAPS batch tests, second unit — Travel Management L2
(remainder addition section).

Pins the extension surface in ``travel.extensions_addition``
for the 2 open entries of the "Remainder Addition — Travel
Management L2 (+1 fork)" section: relocation case records with
an event-driven lifecycle under separation of duties and
verbatim processing-event records (idx 681), and relocation
policy rule definitions as data with entitlement claims stored
verbatim and determinations derived at read against the
recorded caps (idx 682) — plus the cross-cutting disciplines
(exact record shapes, honesty labels, TypeError signature pins,
no score key anywhere, no per-diem shape anywhere, denied
attempts audited with a ``:denied`` suffix, failed operations
consuming no ids, the core traveler record byte-identical
across the addition flow) and the fresh mutation-verified
negative control for the entitlement derivation seam.
"""

import unittest

from travel.errors import NotFoundError, PermissionDenied, ValidationError
from travel.extensions_addition import TravelExtensionsAddition

from travel_helpers import (
    ADMIN,
    DECIDER,
    MEMBER,
    OUTSIDER,
    VIEWER,
    make_store,
    make_traveler,
)

MOVE_DATE = "2026-09-01"
ESTIMATED_CENTS = 900_000
CAP_CENTS = 400_000


def _all_keys(value):
    """Every dict key in a nested structure, recursively."""
    keys = set()
    if isinstance(value, dict):
        for key, sub in value.items():
            keys.add(key)
            keys |= _all_keys(sub)
    elif isinstance(value, (list, tuple)):
        for sub in value:
            keys |= _all_keys(sub)
    return keys


class AdditionTestCase(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()
        self.ext = TravelExtensionsAddition(self.store)
        self.traveler = make_traveler(self.store, self.org)

    def make_case(self, actor=MEMBER, **overrides):
        kwargs = {
            "origin_label": "Denver, CO",
            "destination_label": "Arlington, VA",
            "move_date": MOVE_DATE,
            "estimated_cost_cents": ESTIMATED_CENTS,
        }
        kwargs.update(overrides)
        return self.ext.create_relocation_case(
            actor, self.org["id"], self.traveler["id"], **kwargs)

    def make_approved_case(self, **overrides):
        case = self.make_case(**overrides)
        self.ext.submit_relocation_case(MEMBER, case["id"])
        self.ext.decide_relocation_case(DECIDER, case["id"], True,
                                        note="Approved")
        return self.ext.get_relocation_case(MEMBER, case["id"])

    def make_rule(self, actor=MEMBER, **overrides):
        kwargs = {
            "corpus_label": "ftr",
            "rule_ref": "FTR-HHG-1",
            "entitlement_kind": "household_goods",
            "cap_cents": CAP_CENTS,
            "rule_label": "Household goods weight allowance cap",
        }
        kwargs.update(overrides)
        return self.ext.register_policy_rule(
            actor, self.org["id"], **kwargs)


class TestRelocationCases(AdditionTestCase):
    def test_case_record_shape_and_labels(self):
        case = self.make_case()
        self.assertEqual(
            set(case),
            {"id", "org_id", "traveler_id", "origin_label",
             "destination_label", "move_date", "estimated_cost_cents",
             "status", "moved_here", "relocated_here", "processed_here",
             "state", "created_by", "created_utc"})
        self.assertEqual(case["status"], "draft")
        self.assertEqual(case["state"], "recorded_case_only")
        self.assertFalse(case["moved_here"])
        self.assertFalse(case["relocated_here"])
        self.assertFalse(case["processed_here"])
        self.assertEqual(case["traveler_id"], self.traveler["id"])

    def test_case_is_not_bound_to_any_trip_authorization(self):
        case = self.make_case()
        self.assertNotIn("authorization_id", case)
        self.assertEqual(self.store.list_authorizations(
            MEMBER, self.org["id"]), [])

    def test_core_traveler_byte_identical_across_flow(self):
        before = self.store.get_traveler(MEMBER, self.traveler["id"])
        case = self.make_approved_case()
        self.ext.record_relocation_event(
            MEMBER, case["id"], "household_goods", "reported_completed",
            reported_amount_cents=350_000)
        after = self.store.get_traveler(MEMBER, self.traveler["id"])
        self.assertEqual(before, after)

    def test_lifecycle_and_separation_of_duties(self):
        case = self.make_case()
        with self.assertRaises(ValidationError):
            self.ext.decide_relocation_case(DECIDER, case["id"], True)
        self.ext.submit_relocation_case(MEMBER, case["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.decide_relocation_case(MEMBER, case["id"], True)
        decision = self.ext.decide_relocation_case(
            DECIDER, case["id"], True, note="Approved")
        self.assertTrue(decision["approve"])
        decided = self.ext.get_relocation_case(MEMBER, case["id"])
        self.assertEqual(decided["status"], "approved")
        with self.assertRaises(ValidationError):
            self.ext.submit_relocation_case(MEMBER, case["id"])

    def test_declined_case_takes_no_events(self):
        case = self.make_case()
        self.ext.submit_relocation_case(MEMBER, case["id"])
        self.ext.decide_relocation_case(DECIDER, case["id"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_relocation_event(
                MEMBER, case["id"], "travel", "reported_completed")

    def test_money_and_date_boundaries(self):
        for bad in (True, 1.5, "9000", -1, 0):
            with self.assertRaises(ValidationError):
                self.make_case(estimated_cost_cents=bad)
        with self.assertRaises(ValidationError):
            self.make_case(move_date="September 1, 2026")
        # No id was consumed by any failure above.
        self.assertEqual(self.make_case()["id"], "rlc-1")

    def test_traveler_from_another_org_rejected(self):
        org2 = self.store.create_organization(ADMIN, "ORG-200",
                                              "Agency Two")
        self.store.add_member(ADMIN, org2["id"], MEMBER.name)
        with self.assertRaises(ValidationError):
            self.ext.create_relocation_case(
                MEMBER, org2["id"], self.traveler["id"], "A", "B",
                MOVE_DATE, ESTIMATED_CENTS)

    def test_unknown_traveler_and_case(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_relocation_case(
                MEMBER, self.org["id"], "trv-999", "A", "B",
                MOVE_DATE, ESTIMATED_CENTS)
        with self.assertRaises(NotFoundError):
            self.ext.get_relocation_case(MEMBER, "rlc-999")


class TestRelocationEvents(AdditionTestCase):
    def test_event_shape_and_view_derivations(self):
        case = self.make_approved_case()
        first = self.ext.record_relocation_event(
            MEMBER, case["id"], "household_goods", "reported_in_progress",
            reported_amount_cents=100_000)
        self.assertEqual(
            set(first),
            {"id", "case_id", "org_id", "event_kind", "outcome_label",
             "reported_amount_cents", "processed_here", "created_by",
             "created_utc"})
        self.assertFalse(first["processed_here"])
        self.ext.record_relocation_event(
            MEMBER, case["id"], "household_goods", "reported_completed",
            reported_amount_cents=250_000)
        self.ext.record_relocation_event(
            MEMBER, case["id"], "closeout", "reported_completed")
        view = self.ext.relocation_case_view(MEMBER, case["id"])
        self.assertEqual(view["event_count"], 3)
        self.assertEqual(view["current_outcome"], "reported_completed")
        # A sum of amounts reported by others, stated as such.
        self.assertEqual(view["reported_event_total_cents"], 350_000)
        stored = self.ext.get_relocation_case(MEMBER, case["id"])
        self.assertNotIn("event_count", stored)
        self.assertNotIn("current_outcome", stored)
        self.assertNotIn("reported_event_total_cents", stored)

    def test_events_require_approved_case(self):
        case = self.make_case()
        with self.assertRaises(ValidationError):
            self.ext.record_relocation_event(
                MEMBER, case["id"], "travel", "reported_completed")

    def test_event_vocabulary_and_money(self):
        case = self.make_approved_case()
        with self.assertRaises(ValidationError):
            self.ext.record_relocation_event(
                MEMBER, case["id"], "teleportation", "reported_completed")
        with self.assertRaises(ValidationError):
            self.ext.record_relocation_event(
                MEMBER, case["id"], "travel", "done")
        with self.assertRaises(ValidationError):
            self.ext.record_relocation_event(
                MEMBER, case["id"], "travel", "reported_completed",
                reported_amount_cents=2.5)


class TestPolicyRules(AdditionTestCase):
    def test_rule_record_shape_and_labels(self):
        rule = self.make_rule()
        self.assertEqual(
            set(rule),
            {"id", "org_id", "corpus_label", "rule_ref",
             "entitlement_kind", "cap_cents", "rule_label",
             "definition_only", "executed_here", "corpus_text_held",
             "per_diem_computed_here", "state", "created_by",
             "created_utc"})
        self.assertTrue(rule["definition_only"])
        self.assertFalse(rule["executed_here"])
        self.assertFalse(rule["corpus_text_held"])
        self.assertFalse(rule["per_diem_computed_here"])
        self.assertEqual(rule["state"], "recorded_definition_only")

    def test_corpus_vocabulary_is_the_forks_own(self):
        for corpus in ("ftr", "jtr", "dssr", "6fam"):
            rule = self.make_rule(corpus_label=corpus,
                                  rule_ref="RULE-%s" % corpus)
            self.assertEqual(rule["corpus_label"], corpus)
        with self.assertRaises(ValidationError):
            self.make_rule(corpus_label="internal_memo",
                           rule_ref="RULE-X")

    def test_duplicate_rule_ref_refused_without_id(self):
        self.make_rule()
        with self.assertRaises(ValidationError):
            self.make_rule()
        rule = self.make_rule(rule_ref="FTR-TQ-1",
                              entitlement_kind="temporary_quarters")
        self.assertEqual(rule["id"], "rlr-2")

    def test_rule_cap_money_boundary(self):
        for bad in (True, 1.5, "4000", -1):
            with self.assertRaises(ValidationError):
                self.make_rule(cap_cents=bad)


class TestEntitlementClaims(AdditionTestCase):
    def test_claim_record_carries_no_determination(self):
        case = self.make_approved_case()
        rule = self.make_rule()
        claim = self.ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 450_000, "HHG shipment")
        self.assertEqual(
            set(claim),
            {"id", "case_id", "rule_id", "org_id", "claimed_cents",
             "claim_label", "computed_here", "created_by", "created_utc"})
        self.assertFalse(claim["computed_here"])
        self.assertNotIn("allowed_cents", claim)
        self.assertNotIn("excess_cents", claim)

    def test_evaluation_derives_against_recorded_cap(self):
        case = self.make_approved_case()
        rule = self.make_rule()
        self.ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 300_000, "HHG estimate")
        self.ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 150_000, "HHG final")
        evaluation = self.ext.entitlement_evaluation(MEMBER, case["id"])
        self.assertEqual(evaluation["evaluation_basis"],
                         "recorded_claims_against_recorded_rule_caps")
        self.assertEqual(evaluation["claimed_cents"], 450_000)
        self.assertEqual(evaluation["allowed_cents"], CAP_CENTS)
        self.assertEqual(evaluation["excess_cents"], 50_000)
        self.assertFalse(evaluation["per_diem_computed_here"])
        row = evaluation["rows"][0]
        self.assertEqual(row["cap_cents"], CAP_CENTS)
        self.assertFalse(row["within_cap"])
        # The determination is derived, never stored on any claim.
        for claim in self.ext.list_entitlement_claims(MEMBER, case["id"]):
            self.assertNotIn("allowed_cents", claim)

    def test_evaluation_within_cap(self):
        case = self.make_approved_case()
        rule = self.make_rule()
        self.ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 200_000, "HHG")
        evaluation = self.ext.entitlement_evaluation(MEMBER, case["id"])
        self.assertEqual(evaluation["allowed_cents"], 200_000)
        self.assertEqual(evaluation["excess_cents"], 0)
        self.assertTrue(evaluation["rows"][0]["within_cap"])

    def test_claims_require_approved_case_and_own_org_rule(self):
        case = self.make_case()
        rule = self.make_rule()
        with self.assertRaises(ValidationError):
            self.ext.record_entitlement_claim(
                MEMBER, case["id"], rule["id"], 100_000, "early")
        approved = self.make_approved_case()
        org2 = self.store.create_organization(ADMIN, "ORG-200",
                                              "Agency Two")
        self.store.add_member(ADMIN, org2["id"], MEMBER.name)
        foreign_rule = self.ext.register_policy_rule(
            MEMBER, org2["id"], "jtr", "JTR-1", "other", 100_000, "x")
        with self.assertRaises(ValidationError):
            self.ext.record_entitlement_claim(
                MEMBER, approved["id"], foreign_rule["id"], 100_000, "x")

    def test_case_view_entitlement_totals_track_claims(self):
        case = self.make_approved_case()
        rule = self.make_rule()
        before = self.ext.relocation_case_view(MEMBER, case["id"])
        self.assertEqual(before["entitlement_claimed_cents"], 0)
        self.ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 450_000, "HHG")
        after = self.ext.relocation_case_view(MEMBER, case["id"])
        self.assertEqual(after["entitlement_claimed_cents"], 450_000)
        self.assertEqual(after["entitlement_allowed_cents"], CAP_CENTS)
        self.assertEqual(after["entitlement_excess_cents"], 50_000)

    def test_rule_view_derives_claim_totals(self):
        case = self.make_approved_case()
        rule = self.make_rule()
        view = self.ext.policy_rule_view(MEMBER, rule["id"])
        self.assertEqual(view["claim_count"], 0)
        self.ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 125_000, "HHG")
        view = self.ext.policy_rule_view(MEMBER, rule["id"])
        self.assertEqual(view["claim_count"], 1)
        self.assertEqual(view["claimed_total_cents"], 125_000)
        stored = self.ext.get_policy_rule(MEMBER, rule["id"])
        self.assertNotIn("claim_count", stored)
        self.assertNotIn("claimed_total_cents", stored)


class TestAdditionDiscipline(AdditionTestCase):
    def test_no_score_or_per_diem_shape_anywhere(self):
        case = self.make_approved_case()
        rule = self.make_rule()
        self.ext.record_relocation_event(
            MEMBER, case["id"], "travel", "reported_completed",
            reported_amount_cents=10_000)
        self.ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 450_000, "HHG")
        views = [
            self.ext.relocation_case_view(MEMBER, case["id"]),
            self.ext.entitlement_evaluation(MEMBER, case["id"]),
            self.ext.policy_rule_view(MEMBER, rule["id"]),
        ]
        for view in views:
            keys = _all_keys(view)
            for banned in ("score", "rating", "risk", "per_diem_cents",
                           "daily_rate", "rate_cents"):
                self.assertNotIn(banned, keys)

    def test_signature_pins_no_smuggled_fields(self):
        case = self.make_approved_case()
        rule = self.make_rule()
        with self.assertRaises(TypeError):
            self.ext.create_relocation_case(
                MEMBER, self.org["id"], self.traveler["id"], "A", "B",
                MOVE_DATE, ESTIMATED_CENTS, employee_name="Someone")
        with self.assertRaises(TypeError):
            self.ext.record_entitlement_claim(
                MEMBER, case["id"], rule["id"], 100_000, "x",
                daily_rate=15_000)
        with self.assertRaises(TypeError):
            self.ext.register_policy_rule(
                MEMBER, self.org["id"], "ftr", "FTR-Z", "other", 1, "x",
                regulation_text="the corpus itself")
        with self.assertRaises(TypeError):
            self.ext.record_relocation_event(
                MEMBER, case["id"], "travel", "reported_completed",
                document_number="P123")

    def test_viewer_denied_writes_and_denial_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_relocation_case(
                VIEWER, self.org["id"], self.traveler["id"], "A", "B",
                MOVE_DATE, ESTIMATED_CENTS)
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("exta_relocation_case_create:denied", actions)
        # The denied attempt consumed no id.
        self.assertEqual(self.make_case()["id"], "rlc-1")

    def test_outsider_denied_by_membership(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_relocation_case(
                OUTSIDER, self.org["id"], self.traveler["id"], "A", "B",
                MOVE_DATE, ESTIMATED_CENTS)

    def test_addition_audits_use_exta_prefix(self):
        case = self.make_approved_case()
        rule = self.make_rule()
        self.ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 100_000, "HHG")
        actions = [e["action"] for e in self.store.audit.entries()]
        for expected in ("exta_relocation_case_create",
                         "exta_relocation_case_submit",
                         "exta_relocation_case_decide",
                         "exta_policy_rule_create",
                         "exta_entitlement_claim_create"):
            self.assertIn(expected, actions)


class CapBlindAddition(TravelExtensionsAddition):
    """Mutant: the entitlement derivation ignores the recorded
    rule cap entirely — every claim is allowed in full."""

    @staticmethod
    def _derive_entitlement(claimed_cents, cap_cents):
        return claimed_cents, 0


class TestEntitlementCapNegativeControl(AdditionTestCase):
    """Fresh mutation-verified negative control: the claim under
    test is that a case's allowed entitlement never exceeds the
    recorded rule cap — the seam
    ``TravelExtensionsAddition._derive_entitlement`` is what
    enforces it."""

    def _evaluation_for(self, ext):
        store, org = make_store()
        ext.store = store
        traveler = make_traveler(store, org)
        case = ext.create_relocation_case(
            MEMBER, org["id"], traveler["id"], "A", "B",
            MOVE_DATE, ESTIMATED_CENTS)
        ext.submit_relocation_case(MEMBER, case["id"])
        ext.decide_relocation_case(DECIDER, case["id"], True)
        rule = ext.register_policy_rule(
            MEMBER, org["id"], "ftr", "FTR-HHG-1", "household_goods",
            CAP_CENTS, "cap")
        ext.record_entitlement_claim(
            MEMBER, case["id"], rule["id"], 450_000, "HHG")
        return ext.entitlement_evaluation(MEMBER, case["id"])

    def test_canonical_derivation_caps_at_recorded_cap(self):
        evaluation = self._evaluation_for(self.ext)
        self.assertEqual(evaluation["allowed_cents"], CAP_CENTS)
        self.assertEqual(evaluation["excess_cents"], 50_000)

    def test_mutant_ignores_cap_and_differs(self):
        mutant = CapBlindAddition(self.store)
        evaluation = self._evaluation_for(mutant)
        self.assertEqual(evaluation["allowed_cents"], 450_000)
        self.assertEqual(evaluation["excess_cents"], 0)

    def test_mutant_outcome_as_expectation_fails(self):
        mutant = CapBlindAddition(self.store)
        evaluation = self._evaluation_for(mutant)
        with self.assertRaises(AssertionError):
            self.assertEqual(evaluation["allowed_cents"], CAP_CENTS)


if __name__ == "__main__":
    unittest.main()
