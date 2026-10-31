"""Core: Review records and decision & award records. Traces to
UNION-SPEC core functions 4 and 5, the separation-of-duties seam
(AC-5), the award-cap invariant (SI-10), and the no-computed-scores
discipline: reviews and decisions are recorded verbatim, and no
record anywhere carries a score field."""

import unittest

import grants_helpers as H
from grants.errors import PermissionDenied, ValidationError


def _keys_recursive(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _keys_recursive(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _keys_recursive(value)
    return keys


class TestReviews(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_review_recorded_verbatim(self):
        app = H.make_under_review(self.store, self.program, self.org)
        review = self.store.add_review(H.STAFF, app["id"], "award",
                                       "Strong reach; budget is lean but real.")
        self.assertEqual(review["note"], "Strong reach; budget is lean but real.")
        self.assertEqual(review["recommendation"], "award")
        self.assertEqual(review["reviewer"], "erin")

    def test_review_requires_under_review(self):
        app = H.make_application(self.store, self.program, self.org)
        with self.assertRaises(ValidationError):
            self.store.add_review(H.STAFF, app["id"], "award", "too soon")

    def test_bad_recommendation_and_empty_note(self):
        app = H.make_under_review(self.store, self.program, self.org)
        with self.assertRaises(ValidationError):
            self.store.add_review(H.STAFF, app["id"], "maybe", "note")
        with self.assertRaises(ValidationError):
            self.store.add_review(H.STAFF, app["id"], "award", "  ")

    def test_no_score_field_anywhere(self):
        app, result = H.make_award(self.store, self.program, self.org)
        views = [
            self.store.get_program(H.MEMBER, self.program["id"]),
            self.store.get_application(H.MEMBER, app["id"]),
            result["decision"], result["award"],
            self.store.program_summary(H.MEMBER, self.program["id"]),
        ]
        for view in views:
            self.assertNotIn("score", _keys_recursive(view))
            self.assertNotIn("rating", _keys_recursive(view))
            self.assertNotIn("grade", _keys_recursive(view))


class TestDecisions(unittest.TestCase):
    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_approval_records_decision_and_award(self):
        app = H.make_under_review(self.store, self.program, self.org)
        result = self.store.decide_application(H.STAFF, app["id"], True,
                                               amount_cents=250_000,
                                               note="Fund it")
        self.assertEqual(result["decision"]["decider"], "erin")
        self.assertEqual(result["decision"]["amount_cents"], 250_000)
        self.assertEqual(result["award"]["amount_cents"], 250_000)
        self.assertEqual(result["award"]["org_id"], self.org["id"])
        self.assertEqual(result["application"]["status"], "awarded")
        view = self.store.get_program(H.MEMBER, self.program["id"])
        self.assertEqual(view["awarded_cents"], 250_000)
        self.assertEqual(view["remaining_cents"], H.BUDGET_CENTS - 250_000)

    def test_decline_records_decision_only(self):
        app = H.make_under_review(self.store, self.program, self.org)
        result = self.store.decide_application(H.STAFF, app["id"], False,
                                               note="Out of scope")
        self.assertNotIn("award", result)
        self.assertIsNone(result["decision"]["amount_cents"])
        self.assertEqual(result["application"]["status"], "declined")
        self.assertEqual(self.store.list_awards(H.MEMBER, self.program["id"]), [])

    def test_decider_is_never_the_submitter(self):
        app = H.make_under_review(self.store, self.program, self.org)
        with self.assertRaises(PermissionDenied):
            self.store.decide_application(H.MEMBER, app["id"], True,
                                          amount_cents=100)
        # The failed attempt changed nothing.
        self.assertEqual(
            self.store.get_application(H.STAFF, app["id"])["status"],
            "under_review")

    def test_decide_requires_under_review(self):
        app = H.make_application(self.store, self.program, self.org)
        with self.assertRaises(ValidationError):
            self.store.decide_application(H.STAFF, app["id"], True,
                                          amount_cents=100)

    def test_approve_flag_must_be_bool(self):
        app = H.make_under_review(self.store, self.program, self.org)
        with self.assertRaises(ValidationError):
            self.store.decide_application(H.STAFF, app["id"], "yes",
                                          amount_cents=100)

    def test_approval_requires_amount_and_decline_forbids_it(self):
        app = H.make_under_review(self.store, self.program, self.org)
        with self.assertRaises(ValidationError):
            self.store.decide_application(H.STAFF, app["id"], True)
        with self.assertRaises(ValidationError):
            self.store.decide_application(H.STAFF, app["id"], False,
                                          amount_cents=100)

    def test_amount_must_be_positive_integer_cents(self):
        app = H.make_under_review(self.store, self.program, self.org)
        for bad in (100.0, True, 0, -1):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.store.decide_application(H.STAFF, app["id"], True,
                                              amount_cents=bad)


class TestAwardCap(unittest.TestCase):
    """The award-cap invariant: awards against a program never
    exceed its budget. Rejection is whole — no decision, no award,
    no status change, no id consumed."""

    def setUp(self):
        self.store, self.program, self.org = H.make_store()

    def test_exactly_at_budget_is_allowed(self):
        app = H.make_under_review(self.store, self.program, self.org)
        result = self.store.decide_application(H.STAFF, app["id"], True,
                                               amount_cents=H.BUDGET_CENTS)
        self.assertEqual(result["award"]["amount_cents"], H.BUDGET_CENTS)
        view = self.store.get_program(H.MEMBER, self.program["id"])
        self.assertEqual(view["remaining_cents"], 0)

    def test_one_cent_over_is_rejected_whole(self):
        app = H.make_under_review(self.store, self.program, self.org)
        with self.assertRaises(ValidationError):
            self.store.decide_application(H.STAFF, app["id"], True,
                                          amount_cents=H.BUDGET_CENTS + 1)
        self.assertEqual(
            self.store.get_application(H.STAFF, app["id"])["status"],
            "under_review")
        self.assertEqual(self.store.list_awards(H.MEMBER, self.program["id"]), [])
        self.assertEqual(len(self.store._decisions), 0)

    def test_two_awards_summing_over_budget_second_rejected(self):
        H.make_award(self.store, self.program, self.org, amount_cents=700_000)
        app = H.make_under_review(self.store, self.program, self.org,
                                  summary="Second applicant project")
        with self.assertRaises(ValidationError):
            self.store.decide_application(H.STAFF, app["id"], True,
                                          amount_cents=300_001)
        result = self.store.decide_application(H.STAFF, app["id"], True,
                                               amount_cents=300_000)
        self.assertTrue(result["award"]["id"].startswith("awd-"))
        view = self.store.get_program(H.MEMBER, self.program["id"])
        self.assertEqual(view["remaining_cents"], 0)


if __name__ == "__main__":
    unittest.main()
