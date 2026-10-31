"""Maintenance & inspection record tests (derived due status).

Traces to: Core function 6 (Maintenance & inspection records) --
the stored record carries NO status field; due status is DERIVED at
read by ``FleetStore._derive_due_status(record, as_of_date)``:
completed if completed_date set, overdue if as_of > due_date, else
current.
"""

import unittest

from fleet_helpers import ADMIN, MANAGER, VIEWER, make_store
from fleet.errors import NotFoundError, ValidationError


class TestMaintenance(unittest.TestCase):
    """Core 6: stored record has no status; the read view derives it."""

    def test_stored_record_has_no_status_key(self):
        """Core 6, traced claim: the STORED maintenance record has no 'status' and no 'derived_status' key -- status exists only in the read view."""
        store, vehicle, operator = make_store()
        view = store.create_maintenance(vehicle["id"], "maintenance", "2026-12-01", ADMIN)
        stored = store._maintenance[view["id"]]
        self.assertNotIn("status", stored)
        self.assertNotIn("derived_status", stored)
        self.assertEqual(set(stored), {"id", "vehicle_id", "kind", "due_date",
                                       "completed_date", "created_by", "created_utc"})
        self.assertIsNone(stored["completed_date"])

    def test_derived_current(self):
        """Core 6 derivation: as_of on or before due_date -> derived_status 'current'."""
        store, vehicle, operator = make_store()
        rec = store.create_maintenance(vehicle["id"], "inspection", "2026-12-01", ADMIN)
        self.assertEqual(store.get_maintenance(rec["id"], VIEWER, as_of="2026-11-15")["derived_status"], "current")
        self.assertEqual(store.get_maintenance(rec["id"], VIEWER, as_of="2026-12-01")["derived_status"], "current")

    def test_derived_overdue(self):
        """Core 6 derivation: as_of after due_date (and not completed) -> derived_status 'overdue'."""
        store, vehicle, operator = make_store()
        rec = store.create_maintenance(vehicle["id"], "maintenance", "2026-12-01", ADMIN)
        self.assertEqual(store.get_maintenance(rec["id"], ADMIN, as_of="2026-12-02")["derived_status"], "overdue")
        listed = store.list_maintenance(vehicle_id=vehicle["id"], actor=ADMIN, as_of="2027-01-01")
        self.assertEqual(listed[0]["derived_status"], "overdue")

    def test_derived_completed(self):
        """Core 6 derivation: completed_date set -> derived_status 'completed', even when as_of is past due_date."""
        store, vehicle, operator = make_store()
        rec = store.create_maintenance(vehicle["id"], "maintenance", "2026-12-01", ADMIN)
        done = store.complete_maintenance(rec["id"], MANAGER, completed_date="2026-11-20")
        self.assertEqual(done["completed_date"], "2026-11-20")
        self.assertEqual(done["derived_status"], "completed")
        self.assertEqual(store.get_maintenance(rec["id"], ADMIN, as_of="2027-06-01")["derived_status"], "completed")

    def test_complete_twice_rejected(self):
        """Core 6: completing an already-completed record -> ValidationError."""
        store, vehicle, operator = make_store()
        rec = store.create_maintenance(vehicle["id"], "inspection", "2026-12-01", ADMIN)
        store.complete_maintenance(rec["id"], ADMIN)
        with self.assertRaises(ValidationError):
            store.complete_maintenance(rec["id"], ADMIN)

    def test_bad_kind_and_due_date_rejected(self):
        """Core 6 (SI-10): unknown kind / malformed due_date -> ValidationError, no id consumed; unknown id -> NotFoundError."""
        store, vehicle, operator = make_store()
        with self.assertRaises(ValidationError):
            store.create_maintenance(vehicle["id"], "repair", "2026-12-01", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_maintenance(vehicle["id"], "maintenance", "Dec 1 2026", ADMIN)
        self.assertEqual(store.create_maintenance(vehicle["id"], "maintenance", "2026-12-01", ADMIN)["id"], "mnt-1")
        with self.assertRaises(NotFoundError):
            store.get_maintenance("mnt-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
