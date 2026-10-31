"""Core function 9: advisory engagement records.

Engagements record the three claimed consulting kinds (budgeting,
market_intelligence, risk_management). The note is stored verbatim.
The advice itself is Extended -- what is Core is the record.
"""

import unittest

from energy.errors import NotFoundError, PermissionDenied, ValidationError

from energy_helpers import VIEWER, make_customer, make_store, ADMIN

NOTE = "Budget review for FY25 supply; ceiling noted at 410 c/kWh."


class EngagementTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.customer = make_customer(self.store)

    def engage(self, kind="budgeting", note=NOTE):
        return self.store.create_engagement(ADMIN, self.customer["id"],
                                            kind, note)

    def test_created_open_with_verbatim_note(self):
        eng = self.engage()
        self.assertEqual(eng["id"], "eng-1")
        self.assertEqual(eng["status"], "open")
        self.assertEqual(eng["note"], NOTE)
        self.assertEqual(eng["kind"], "budgeting")

    def test_all_three_kinds(self):
        for kind in ("budgeting", "market_intelligence", "risk_management"):
            eng = self.engage(kind=kind)
            self.assertEqual(eng["kind"], kind)

    def test_close_lifecycle(self):
        eng = self.engage()
        closed = self.store.close_engagement(ADMIN, eng["id"])
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_engagement(ADMIN, eng["id"])
        with self.assertRaises(NotFoundError):
            self.store.close_engagement(ADMIN, "eng-99")

    def test_validation_and_filters(self):
        with self.assertRaises(ValidationError):
            self.engage(kind="legal_advice")
        with self.assertRaises(ValidationError):
            self.engage(note="   ")
        with self.assertRaises(NotFoundError):
            self.store.create_engagement(ADMIN, "cust-99", "budgeting", NOTE)
        self.engage()
        self.engage(kind="risk_management")
        self.assertEqual(
            len(self.store.list_engagements(ADMIN, kind="budgeting")), 1)
        self.assertEqual(
            len(self.store.list_engagements(ADMIN, status="open")), 2)
        with self.assertRaises(ValidationError):
            self.store.list_engagements(ADMIN, status="pending")
        got = self.store.get_engagement(VIEWER, "eng-1")
        self.assertEqual(got["note"], NOTE)

    def test_roles(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_engagement(VIEWER, self.customer["id"],
                                         "budgeting", NOTE)


if __name__ == "__main__":
    unittest.main()
