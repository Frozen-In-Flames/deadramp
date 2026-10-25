"""Activity / appointment record tests.

Traces to: Core function 6 (Activity / appointment records;
AU-2, CM-6) -- scheduled activities and appointments bound to a
participant and optionally a program, with a lifecycle state.
"""

import unittest

from health_helpers import ADMIN, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError


class TestActivities(unittest.TestCase):
    """Core 6: activity/appointment records and lifecycle states."""

    def test_create_shape_and_state_transition(self):
        """Core 6: created activity carries an act- id with state 'scheduled'; set_activity_state moves it to completed/cancelled."""
        store, program, participant = make_store()
        rec = store.create_activity(participant["id"], "Clinic visit",
                                    "2026-07-01T09:00:00Z", CLINICIAN,
                                    program_id=program["id"])
        self.assertEqual(rec["id"], "act-1")
        self.assertEqual(rec["state"], "scheduled")
        self.assertEqual(rec["kind"], "appointment")
        done = store.set_activity_state(rec["id"], "completed", CLINICIAN)
        self.assertEqual(done["state"], "completed")
        cancelled = store.set_activity_state(rec["id"], "cancelled", CLINICIAN)
        self.assertEqual(cancelled["state"], "cancelled")

    def test_kinds(self):
        """Core 6: kinds appointment/activity/session accepted."""
        store, _, participant = make_store()
        for kind in ("appointment", "activity", "session"):
            rec = store.create_activity(participant["id"], "T",
                                        "2026-07-01T09:00:00Z", CLINICIAN, kind=kind)
            self.assertEqual(rec["kind"], kind)

    def test_validation(self):
        """Core 6 (SI-10): ends before starts, bad kind, malformed datetimes, bad state, unknown refs -> ValidationError/NotFoundError."""
        store, program, participant = make_store()
        with self.assertRaises(ValidationError):
            store.create_activity(participant["id"], "T", "2026-07-01T09:00:00Z",
                                  CLINICIAN, ends_at="2026-07-01T08:00:00Z")
        with self.assertRaises(ValidationError):
            store.create_activity(participant["id"], "T", "soon", CLINICIAN)
        with self.assertRaises(ValidationError):
            store.create_activity(participant["id"], "T", "2026-07-01T09:00:00Z",
                                  CLINICIAN, kind="alien")
        with self.assertRaises(NotFoundError):
            store.create_activity("par-999", "T", "2026-07-01T09:00:00Z", CLINICIAN)
        rec = store.create_activity(participant["id"], "T", "2026-07-01T09:00:00Z",
                                    CLINICIAN, ends_at="2026-07-01T10:00:00Z")
        self.assertEqual(rec["ends_at"], "2026-07-01T10:00:00Z")
        with self.assertRaises(ValidationError):
            store.set_activity_state(rec["id"], "alien", CLINICIAN)
        with self.assertRaises(NotFoundError):
            store.set_activity_state("act-999", "completed", CLINICIAN)

    def test_filters_and_member_scope(self):
        """Core 6 + member scope: filters work; member lists only own, get on another's -> PermissionDenied; member write denied."""
        store, program, participant = make_store()
        other = store.create_participant("erin", ADMIN)
        own = store.create_activity(participant["id"], "Mine", "2026-07-01T09:00:00Z",
                                    CLINICIAN, program_id=program["id"])
        foreign = store.create_activity(other["id"], "Theirs", "2026-07-01T09:00:00Z",
                                        CLINICIAN)
        self.assertEqual(len(store.list_activities(ADMIN, program_id=program["id"])), 1)
        listing = store.list_activities(MEMBER)
        self.assertEqual([r["id"] for r in listing], [own["id"]])
        with self.assertRaises(PermissionDenied):
            store.get_activity(foreign["id"], MEMBER)
        with self.assertRaises(PermissionDenied):
            store.create_activity(participant["id"], "X", "2026-07-01T09:00:00Z", MEMBER)


if __name__ == "__main__":
    unittest.main()
