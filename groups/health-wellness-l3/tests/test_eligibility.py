"""Eligibility / coverage record tests.

Traces to: Core function 7 (Eligibility / coverage records;
AU-2, SI-12; claim family claims_processing 2/5 -- claims presuppose a
coverage record) -- per-participant coverage records holding an opaque
plan reference only, with derived current status (upcoming/current/
ended). No insurer names, member numbers or benefit details exist.
"""

import unittest

from health_helpers import ADMIN, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError

AS_OF = "2026-06-15"


class TestEligibility(unittest.TestCase):
    """Core 7: eligibility/coverage records and derived status."""

    def test_create_shape_no_insurer_fields(self):
        """Core 7 (SI-12): created record carries an elg- id and exactly the contract fields; no insurer/member-number/benefit field exists."""
        store, _, participant = make_store()
        rec = store.create_eligibility(participant["id"], "plan-alpha",
                                       "2026-01-01", ADMIN)
        self.assertEqual(rec["id"], "elg-1")
        self.assertIsNone(rec["coverage_end"])
        self.assertIn("derived_status", rec)
        for forbidden in ("insurer", "insurer_name", "member_number", "benefits",
                          "diagnosis", "note"):
            self.assertNotIn(forbidden, rec)

    def test_derived_upcoming_current_ended(self):
        """Core 7 (CA-7): before start -> upcoming; inside the window (incl. both boundary dates) -> current; strictly after coverage_end -> ended; open-ended coverage never ends."""
        store, _, participant = make_store()
        rec = store.create_eligibility(participant["id"], "plan-alpha",
                                       "2026-06-01", ADMIN, coverage_end="2026-06-30")
        self.assertEqual(store.eligibility_status(rec["id"], ADMIN, as_of="2026-05-15"),
                         {"id": rec["id"], "derived_status": "upcoming"})
        for as_of in ("2026-06-01", AS_OF, "2026-06-30"):
            self.assertEqual(
                store.eligibility_status(rec["id"], ADMIN, as_of=as_of)["derived_status"],
                "current")
        self.assertEqual(
            store.eligibility_status(rec["id"], ADMIN, as_of="2026-07-01")["derived_status"],
            "ended")
        open_ended = store.create_eligibility(participant["id"], "plan-beta",
                                              "2026-06-01", ADMIN)
        self.assertEqual(
            store.eligibility_status(open_ended["id"], ADMIN, as_of="2030-01-01")["derived_status"],
            "current")
        view = store.get_eligibility(rec["id"], ADMIN, as_of=AS_OF)
        self.assertEqual(view["derived_status"], "current")

    def test_validation(self):
        """Core 7 (SI-10): end before start, bad dates, empty plan_ref, unknown refs -> ValidationError/NotFoundError."""
        store, _, participant = make_store()
        with self.assertRaises(ValidationError):
            store.create_eligibility(participant["id"], "p", "2026-06-01", ADMIN,
                                     coverage_end="2026-05-01")
        with self.assertRaises(ValidationError):
            store.create_eligibility(participant["id"], "", "2026-06-01", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_eligibility(participant["id"], "p", "June 1", ADMIN)
        with self.assertRaises(NotFoundError):
            store.create_eligibility("par-999", "p", "2026-06-01", ADMIN)
        with self.assertRaises(NotFoundError):
            store.get_eligibility("elg-999", ADMIN, as_of=AS_OF)

    def test_write_admin_only_and_member_scope(self):
        """Core 7 / Core 9 + member scope: eligibility_write is admin-only (clinician denied); member reads own coverage only, list excludes others, status on another's -> PermissionDenied."""
        store, _, participant = make_store()
        other = store.create_participant("erin", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.create_eligibility(participant["id"], "p", "2026-01-01", CLINICIAN)
        own = store.create_eligibility(participant["id"], "plan-alpha", "2026-01-01", ADMIN)
        foreign = store.create_eligibility(other["id"], "plan-beta", "2026-01-01", ADMIN)
        listing = store.list_eligibilities(MEMBER, as_of=AS_OF)
        self.assertEqual([r["id"] for r in listing], [own["id"]])
        with self.assertRaises(PermissionDenied):
            store.get_eligibility(foreign["id"], MEMBER, as_of=AS_OF)
        with self.assertRaises(PermissionDenied):
            store.eligibility_status(foreign["id"], MEMBER, as_of=AS_OF)
        with self.assertRaises(PermissionDenied):
            store.list_eligibilities(MEMBER, participant_id=other["id"], as_of=AS_OF)


if __name__ == "__main__":
    unittest.main()
