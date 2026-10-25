"""Participant registry tests.

Traces to: Core function 1 (Participant registry, opaque refs only;
AC-2, AU-2, SI-12) and the privacy discipline -- participants are
keyed by a caller-supplied opaque ``participant_ref`` only; no name,
contact, date-of-birth or other identifier field exists.
"""

import unittest

from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER, fresh_store, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError


class TestParticipants(unittest.TestCase):
    """Core 1: participant registry under opaque references only."""

    def test_create_shape_and_provenance(self):
        """Core 1 (SI-12): created participant carries exactly id/participant_ref/kind/created_by/created_utc with a par- id."""
        store = fresh_store()
        rec = store.create_participant("carol", ADMIN)
        self.assertEqual(rec["id"], "par-1")
        self.assertEqual(rec["participant_ref"], "carol")
        self.assertEqual(rec["kind"], "patient")
        self.assertEqual(rec["created_by"], "alice")
        self.assertEqual(set(rec), {"id", "participant_ref", "kind",
                                    "created_by", "created_utc"})

    def test_kinds_and_duplicate_ref_rejected(self):
        """Core 1: kind must be patient/caregiver/professional; a second create with the same ref raises ValidationError and consumes no id."""
        store = fresh_store()
        store.create_participant("carol", ADMIN, kind="caregiver")
        with self.assertRaises(ValidationError):
            store.create_participant("carol", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_participant("erin", ADMIN, kind="alien")
        with self.assertRaises(ValidationError):
            store.create_participant("", ADMIN)
        nxt = store.create_participant("erin", ADMIN, kind="professional")
        self.assertEqual(nxt["id"], "par-2")

    def test_get_list_sorted_and_unknown(self):
        """Core 1: get returns the record; list is sorted by numeric id; unknown id -> NotFoundError."""
        store, program, participant = make_store()
        second = store.create_participant("erin", ADMIN)
        listing = store.list_participants(ADMIN)
        self.assertEqual([r["id"] for r in listing], [participant["id"], second["id"]])
        self.assertEqual(store.get_participant(second["id"], AUDITOR)["participant_ref"], "erin")
        with self.assertRaises(NotFoundError):
            store.get_participant("par-999", ADMIN)

    def test_write_admin_only(self):
        """Core 1 / Core 9 (AC-3): participant_write is admin-only -- clinician, member and auditor are denied."""
        store = fresh_store()
        for actor in (CLINICIAN, MEMBER, AUDITOR):
            with self.assertRaises(PermissionDenied):
                store.create_participant("erin", actor)

    def test_member_scope(self):
        """Core 1 + privacy discipline (member scope): member carol reads only the participant record whose ref is 'carol'; another participant's record -> PermissionDenied; lists exclude others."""
        store, _, participant = make_store()
        other = store.create_participant("erin", ADMIN)
        self.assertEqual(store.get_participant(participant["id"], MEMBER)["participant_ref"], "carol")
        with self.assertRaises(PermissionDenied):
            store.get_participant(other["id"], MEMBER)
        listing = store.list_participants(MEMBER)
        self.assertEqual([r["participant_ref"] for r in listing], ["carol"])

    def test_no_identifier_fields_exist(self):
        """Privacy discipline: no name/dob/email/ssn field exists on a participant record."""
        store, _, participant = make_store()
        for forbidden in ("name", "dob", "date_of_birth", "email", "phone", "ssn",
                          "address", "diagnosis", "note"):
            self.assertNotIn(forbidden, participant)


if __name__ == "__main__":
    unittest.main()
