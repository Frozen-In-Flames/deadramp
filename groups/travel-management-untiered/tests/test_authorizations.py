import unittest

from travel.errors import PermissionDenied, ValidationError

from travel_helpers import (DECIDER, MEMBER, VIEWER, make_approved_authorization,
                            make_authorization, make_store, make_traveler)


class TestAuthorizations(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()
        self.traveler = make_traveler(self.store, self.org)

    def test_create_draft(self):
        auth = make_authorization(self.store, self.org, self.traveler)
        self.assertEqual(auth["status"], "draft")
        self.assertEqual(auth["authorized_cents"], 500_000)

    def test_return_before_depart_rejected(self):
        with self.assertRaises(ValidationError):
            make_authorization(self.store, self.org, self.traveler,
                               depart_date="2026-06-12",
                               return_date="2026-06-10")

    def test_float_authorized_cents_rejected(self):
        with self.assertRaises(ValidationError):
            make_authorization(self.store, self.org, self.traveler,
                               authorized_cents=5000.0)

    def test_bool_authorized_cents_rejected(self):
        with self.assertRaises(ValidationError):
            make_authorization(self.store, self.org, self.traveler,
                               authorized_cents=True)

    def test_zero_authorized_cents_rejected(self):
        with self.assertRaises(ValidationError):
            make_authorization(self.store, self.org, self.traveler,
                               authorized_cents=0)

    def test_traveler_from_other_org_rejected(self):
        other = self.store.create_organization(MEMBER, "ORG-200", "Two")
        with self.assertRaises(ValidationError):
            self.store.create_authorization(
                MEMBER, other["id"], self.traveler["id"], "X", "Y",
                "2026-06-10", "2026-06-11", 1000)

    def test_submit_moves_to_submitted(self):
        auth = make_authorization(self.store, self.org, self.traveler)
        view = self.store.submit_authorization(MEMBER, auth["id"])
        self.assertEqual(view["status"], "submitted")

    def test_double_submit_rejected(self):
        auth = make_authorization(self.store, self.org, self.traveler)
        self.store.submit_authorization(MEMBER, auth["id"])
        with self.assertRaises(ValidationError):
            self.store.submit_authorization(MEMBER, auth["id"])

    def test_decide_draft_rejected(self):
        auth = make_authorization(self.store, self.org, self.traveler)
        with self.assertRaises(ValidationError):
            self.store.decide_authorization(DECIDER, auth["id"], True)

    def test_creator_cannot_decide_own_authorization(self):
        auth = make_authorization(self.store, self.org, self.traveler)
        self.store.submit_authorization(MEMBER, auth["id"])
        with self.assertRaises(PermissionDenied):
            self.store.decide_authorization(MEMBER, auth["id"], True)

    def test_approve_flow_and_decision_record(self):
        auth = make_approved_authorization(self.store, self.org, self.traveler)
        self.assertEqual(auth["status"], "approved")
        decisions = self.store.list_decisions(MEMBER, self.org["id"],
                                              target_id=auth["id"])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["decider"], "dana")
        self.assertTrue(decisions[0]["approve"])
        self.assertEqual(decisions[0]["target_kind"], "authorization")

    def test_decline_flow(self):
        auth = make_authorization(self.store, self.org, self.traveler)
        self.store.submit_authorization(MEMBER, auth["id"])
        result = self.store.decide_authorization(DECIDER, auth["id"], False,
                                                 note="Not justified")
        self.assertEqual(result["authorization"]["status"], "declined")

    def test_non_bool_approve_rejected(self):
        auth = make_authorization(self.store, self.org, self.traveler)
        self.store.submit_authorization(MEMBER, auth["id"])
        with self.assertRaises(ValidationError):
            self.store.decide_authorization(DECIDER, auth["id"], "yes")

    def test_viewer_cannot_create(self):
        with self.assertRaises(PermissionDenied):
            make_authorization(self.store, self.org, self.traveler,
                               actor=VIEWER)


class TestPhaseDerivation(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()
        self.traveler = make_traveler(self.store, self.org)
        self.auth = make_authorization(self.store, self.org, self.traveler)

    def test_phase_upcoming(self):
        view = self.store.get_authorization(MEMBER, self.auth["id"],
                                            as_of="2026-06-01")
        self.assertEqual(view["phase"], "upcoming")

    def test_phase_in_progress(self):
        view = self.store.get_authorization(MEMBER, self.auth["id"],
                                            as_of="2026-06-11")
        self.assertEqual(view["phase"], "in_progress")

    def test_phase_completed(self):
        view = self.store.get_authorization(MEMBER, self.auth["id"],
                                            as_of="2026-06-13")
        self.assertEqual(view["phase"], "completed")

    def test_phase_never_stored(self):
        raw = self.store._authorizations[self.auth["id"]]
        self.assertNotIn("phase", raw)
        self.assertNotIn("claimed_cents", raw)
        self.assertNotIn("reimbursed_cents", raw)


if __name__ == "__main__":
    unittest.main()
