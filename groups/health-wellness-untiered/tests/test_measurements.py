"""Measurement / outcome record tests.

Traces to: Core function 4 (Measurement / outcome records;
AU-2, AU-3, SI-10; claim family measurement_data 3/5) -- numeric
value + unit + metric name + date per participant, optionally per
program. No diagnosis fields, no free-text clinical notes; unknown
or extra fields are refused at the boundary.
"""

import unittest

from health_helpers import ADMIN, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError


class TestMeasurements(unittest.TestCase):
    """Core 4: measurement records with exact field discipline."""

    def test_record_shape(self):
        """Core 4: recorded measurement carries exactly the contract fields with an msr- id; program_id defaults to None."""
        store, program, participant = make_store()
        rec = store.record_measurement(participant["id"], "glucose", 120, "mg/dL",
                                       "2026-06-10", CLINICIAN)
        self.assertEqual(rec["id"], "msr-1")
        self.assertIsNone(rec["program_id"])
        self.assertEqual(set(rec), {"id", "participant_id", "program_id", "metric_name",
                                    "value", "unit", "recorded_on",
                                    "created_by", "created_utc"})
        scoped = store.record_measurement(participant["id"], "glucose", 130, "mg/dL",
                                          "2026-06-11", CLINICIAN, program_id=program["id"])
        self.assertEqual(scoped["program_id"], program["id"])

    def test_value_validation(self):
        """Core 4 (SI-10): bool, string, NaN and infinite values -> ValidationError; int/float/zero/negative accepted."""
        store, program, participant = make_store()
        for bad in (True, "120", float("nan"), float("inf"), float("-inf"), None):
            with self.assertRaises(ValidationError):
                store.record_measurement(participant["id"], "glucose", bad, "mg/dL",
                                         "2026-06-10", CLINICIAN)
        for good in (0, -5, 98.6):
            rec = store.record_measurement(participant["id"], "glucose", good, "mg/dL",
                                           "2026-06-10", CLINICIAN)
            self.assertEqual(rec["value"], good)

    def test_field_validation_and_refs(self):
        """Core 4 (SI-10): empty metric/unit, bad date, unknown participant/program -> ValidationError/NotFoundError."""
        store, program, participant = make_store()
        with self.assertRaises(ValidationError):
            store.record_measurement(participant["id"], "", 1, "mg/dL", "2026-06-10", CLINICIAN)
        with self.assertRaises(ValidationError):
            store.record_measurement(participant["id"], "glucose", 1, "", "2026-06-10", CLINICIAN)
        with self.assertRaises(ValidationError):
            store.record_measurement(participant["id"], "glucose", 1, "mg/dL", "June 10", CLINICIAN)
        with self.assertRaises(NotFoundError):
            store.record_measurement("par-999", "glucose", 1, "mg/dL", "2026-06-10", CLINICIAN)
        with self.assertRaises(NotFoundError):
            store.record_measurement(participant["id"], "glucose", 1, "mg/dL", "2026-06-10",
                                     CLINICIAN, program_id="prg-999")

    def test_no_clinical_fields_exist(self):
        """Privacy discipline: no diagnosis/note field exists on a measurement record."""
        store, _, participant = make_store()
        rec = store.record_measurement(participant["id"], "glucose", 120, "mg/dL",
                                       "2026-06-10", CLINICIAN)
        for forbidden in ("diagnosis", "note", "notes", "comment"):
            self.assertNotIn(forbidden, rec)

    def test_filters_and_member_scope(self):
        """Core 4 + member scope: filters by participant/program/metric work; member lists only own, get on another's -> PermissionDenied; member write denied."""
        store, program, participant = make_store()
        other = store.create_participant("erin", ADMIN)
        store.record_measurement(participant["id"], "glucose", 120, "mg/dL",
                                 "2026-06-10", CLINICIAN, program_id=program["id"])
        store.record_measurement(participant["id"], "weight", 70, "kg",
                                 "2026-06-10", CLINICIAN)
        foreign = store.record_measurement(other["id"], "glucose", 140, "mg/dL",
                                           "2026-06-10", CLINICIAN)
        self.assertEqual(len(store.list_measurements(ADMIN, metric_name="glucose")), 2)
        self.assertEqual(len(store.list_measurements(ADMIN, program_id=program["id"])), 1)
        own = store.list_measurements(MEMBER)
        self.assertEqual(len(own), 2)
        self.assertTrue(all(r["participant_id"] == participant["id"] for r in own))
        with self.assertRaises(PermissionDenied):
            store.get_measurement(foreign["id"], MEMBER)
        with self.assertRaises(PermissionDenied):
            store.list_measurements(MEMBER, participant_id=other["id"])
        with self.assertRaises(PermissionDenied):
            store.record_measurement(participant["id"], "glucose", 1, "mg/dL",
                                     "2026-06-10", MEMBER)


if __name__ == "__main__":
    unittest.main()
