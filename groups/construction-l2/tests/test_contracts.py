"""Contracts tests.

Traces to: Core -- Contracts (con-) lifecycle and expiry derivation;
contract for ``ConstructStore.create_contract`` /
``transition_contract`` / ``_contract_expiry_state``.
Expiry derivation: pre_execution / ended / open_ended / expired /
expiring (<=30 days) / active; derived values are NEVER stored.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from construct.errors import NotFoundError, PermissionDenied, ValidationError

NOW = "2025-06-01T00:00:00Z"


def _executed(store, project_id, end_at, org_id=None):
    """Contracts helper: a contract moved draft->in_review->executed."""
    con = store.create_contract(OPERATOR, "Deal", project_id, org_id=org_id, end_at=end_at)
    store.transition_contract(con["id"], OPERATOR, "in_review")
    store.transition_contract(con["id"], OPERATOR, "executed")
    return con


class TestContractCreation(unittest.TestCase):
    """Contracts: creation validation."""

    def test_create_shape(self):
        """Contracts. create_contract makes con- in draft with all fields."""
        store, project, prime, sub = make_store()
        con = store.create_contract(
            OPERATOR, "Main deal", project["id"], org_id=prime["id"], value_cents=5000,
            start_at="2025-01-01T00:00:00Z", end_at="2026-01-01T00:00:00Z",
            key_dates=[{"label": "kickoff", "at": "2025-02-01T00:00:00Z"}])
        self.assertEqual(con["id"], "con-1")
        self.assertEqual(con["status"], "draft")
        self.assertEqual(con["value_cents"], 5000)
        self.assertEqual(con["key_dates"], [{"label": "kickoff", "at": "2025-02-01T00:00:00Z"}])
        self.assertEqual(con["expiry_state"], "pre_execution")
        self.assertEqual(con["created_by"], "bob")

    def test_value_cents_money_rule(self):
        """Contracts. value_cents float/bool/negative/string -> ValidationError; 0/None ok."""
        store, project, prime, sub = make_store()
        for bad in (1.5, True, False, -1, "100"):
            with self.subTest(value=bad):
                with self.assertRaises(ValidationError):
                    store.create_contract(OPERATOR, "X", project["id"], value_cents=bad)
        self.assertEqual(store.create_contract(OPERATOR, "Zero", project["id"], value_cents=0)["value_cents"], 0)
        self.assertIsNone(store.create_contract(OPERATOR, "None", project["id"])["value_cents"])

    def test_key_dates_validation_and_deep_copy(self):
        """Contracts. key_dates label/at validated; stored list is a deep copy."""
        store, project, prime, sub = make_store()
        for bad in ("nope", [{"label": "", "at": "2025-01-01T00:00:00Z"}],
                    [{"label": "x", "at": "junk"}], [{"at": "2025-01-01T00:00:00Z"}],
                    [{"label": "x"}], ["x"]):
            with self.subTest(key_dates=bad):
                with self.assertRaises(ValidationError):
                    store.create_contract(OPERATOR, "X", project["id"], key_dates=bad)
        kd = [{"label": "kickoff", "at": "2025-02-01T00:00:00Z"}]
        con = store.create_contract(OPERATOR, "X", project["id"], key_dates=kd)
        kd[0]["label"] = "mutated"
        self.assertEqual(store.get_contract(con["id"], ADMIN)["key_dates"][0]["label"], "kickoff")
        got = store.get_contract(con["id"], ADMIN)
        got["key_dates"][0]["label"] = "hacked"
        self.assertEqual(store.get_contract(con["id"], ADMIN)["key_dates"][0]["label"], "kickoff")

    def test_unknown_project_org_and_no_id_on_failure(self):
        """Contracts. Unknown project/org -> NotFoundError; failures consume no id."""
        store, project, prime, sub = make_store()
        with self.assertRaises(NotFoundError):
            store.create_contract(OPERATOR, "X", "prj-99")
        with self.assertRaises(NotFoundError):
            store.create_contract(OPERATOR, "X", project["id"], org_id="org-99")
        with self.assertRaises(ValidationError):
            store.create_contract(OPERATOR, "X", project["id"], end_at="junk")
        con = store.create_contract(OPERATOR, "Good", project["id"])
        self.assertEqual(con["id"], "con-1")


class TestContractLifecycle(unittest.TestCase):
    """Contracts: lifecycle transitions."""

    def test_full_lifecycle(self):
        """Contracts. draft->in_review->executed->active->completed->closed succeeds."""
        store, project, prime, sub = make_store()
        con = store.create_contract(OPERATOR, "Deal", project["id"])
        for to in ("in_review", "executed", "active", "completed", "closed"):
            con = store.transition_contract(con["id"], OPERATOR, to)
            self.assertEqual(con["status"], to)

    def test_review_back_to_draft_and_terminations(self):
        """Contracts. in_review->draft succeeds; terminated reachable from draft/executed/active."""
        store, project, prime, sub = make_store()
        con = store.create_contract(OPERATOR, "Deal", project["id"])
        store.transition_contract(con["id"], OPERATOR, "in_review")
        self.assertEqual(store.transition_contract(con["id"], OPERATOR, "draft")["status"], "draft")
        self.assertEqual(store.transition_contract(con["id"], OPERATOR, "terminated")["status"], "terminated")
        con2 = _executed(store, project["id"], None)
        self.assertEqual(store.transition_contract(con2["id"], OPERATOR, "terminated")["status"], "terminated")

    def test_invalid_transitions(self):
        """Contracts. draft->executed, closed->draft, terminated->draft -> ValidationError."""
        store, project, prime, sub = make_store()
        con = store.create_contract(OPERATOR, "Deal", project["id"])
        with self.assertRaises(ValidationError):
            store.transition_contract(con["id"], OPERATOR, "executed")
        with self.assertRaises(ValidationError):
            store.transition_contract(con["id"], OPERATOR, "active")
        store.transition_contract(con["id"], OPERATOR, "terminated")
        with self.assertRaises(ValidationError):
            store.transition_contract(con["id"], OPERATOR, "draft")
        with self.assertRaises(PermissionDenied):
            store.transition_contract(con["id"], VIEWER, "draft")


class TestExpiryDerivation(unittest.TestCase):
    """Contracts: _contract_expiry_state derivation at read time."""

    def test_pre_execution(self):
        """Expiry. draft and in_review read pre_execution regardless of end_at."""
        store, project, prime, sub = make_store()
        con = store.create_contract(OPERATOR, "Deal", project["id"], end_at="2020-01-01T00:00:00Z")
        self.assertEqual(store.get_contract(con["id"], ADMIN, now=NOW)["expiry_state"], "pre_execution")
        store.transition_contract(con["id"], OPERATOR, "in_review")
        self.assertEqual(store.get_contract(con["id"], ADMIN, now=NOW)["expiry_state"], "pre_execution")

    def test_open_ended(self):
        """Expiry. Executed/active contract with no end_at reads open_ended, days None."""
        store, project, prime, sub = make_store()
        con = _executed(store, project["id"], None)
        view = store.get_contract(con["id"], ADMIN, now=NOW)
        self.assertEqual(view["expiry_state"], "open_ended")
        self.assertIsNone(view["days_to_expiry"])

    def test_active_far_future(self):
        """Expiry. Executed contract ending >30 days after now reads active."""
        store, project, prime, sub = make_store()
        con = _executed(store, project["id"], "2025-08-01T00:00:00Z")
        view = store.get_contract(con["id"], ADMIN, now=NOW)
        self.assertEqual(view["expiry_state"], "active")
        self.assertEqual(view["days_to_expiry"], 61)

    def test_expiring_within_30_days(self):
        """Expiry. Executed contract ending within 30 days reads expiring."""
        store, project, prime, sub = make_store()
        con = _executed(store, project["id"], "2025-06-20T00:00:00Z")
        view = store.get_contract(con["id"], ADMIN, now=NOW)
        self.assertEqual(view["expiry_state"], "expiring")
        self.assertEqual(view["days_to_expiry"], 19)
        edge = _executed(store, project["id"], "2025-07-01T00:00:00Z")
        self.assertEqual(store.get_contract(edge["id"], ADMIN, now=NOW)["expiry_state"], "expiring")

    def test_expired_and_days_negative(self):
        """Expiry. Executed contract past end_at reads expired; days_to_expiry is negative."""
        store, project, prime, sub = make_store()
        con = _executed(store, project["id"], "2025-05-30T00:00:00Z")
        view = store.get_contract(con["id"], ADMIN, now=NOW)
        self.assertEqual(view["expiry_state"], "expired")
        self.assertEqual(view["days_to_expiry"], -2)

    def test_ended_statuses(self):
        """Expiry. completed/closed/terminated read ended regardless of end_at."""
        store, project, prime, sub = make_store()
        con = _executed(store, project["id"], "2030-01-01T00:00:00Z")
        store.transition_contract(con["id"], OPERATOR, "active")
        store.transition_contract(con["id"], OPERATOR, "completed")
        self.assertEqual(store.get_contract(con["id"], ADMIN, now=NOW)["expiry_state"], "ended")
        con2 = store.create_contract(OPERATOR, "T", project["id"], end_at="2030-01-01T00:00:00Z")
        store.transition_contract(con2["id"], OPERATOR, "terminated")
        self.assertEqual(store.get_contract(con2["id"], ADMIN, now=NOW)["expiry_state"], "ended")

    def test_derived_not_stored(self):
        """Expiry. The stored record carries no expiry_state/days_to_expiry keys."""
        store, project, prime, sub = make_store()
        con = _executed(store, project["id"], "2020-01-01T00:00:00Z")
        stored = store._contracts[con["id"]]
        self.assertNotIn("expiry_state", stored)
        self.assertNotIn("days_to_expiry", stored)

    def test_list_filters(self):
        """Contracts. list_contracts filters by project_id and status, views carry expiry."""
        store, project, prime, sub = make_store()
        other = store.create_project("Other", ADMIN)
        c1 = _executed(store, project["id"], "2020-01-01T00:00:00Z")
        store.create_contract(OPERATOR, "Draft deal", other["id"])
        mine = store.list_contracts(VIEWER, now=NOW, project_id=project["id"])
        self.assertEqual([c["id"] for c in mine], [c1["id"]])
        self.assertEqual(mine[0]["expiry_state"], "expired")
        drafts = store.list_contracts(VIEWER, now=NOW, status="draft")
        self.assertEqual(len(drafts), 1)


if __name__ == "__main__":
    unittest.main()
