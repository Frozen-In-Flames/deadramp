"""Vehicle & asset registry tests.

Traces to: Core function 1 (Vehicle & asset registry) -- vehicle
records {id, label, vehicle_type, status(active/retired), created_by,
created_utc} with sequential ``veh-`` ids.
"""

import unittest

from fleet_helpers import ADMIN, MANAGER, VIEWER, fresh_store
from fleet.errors import NotFoundError, PermissionDenied, ValidationError


class TestVehicles(unittest.TestCase):
    """Core 1: vehicle creation shape/provenance, ids, validation, RBAC."""

    def test_create_shape_and_ids(self):
        """Core 1: a vehicle record carries the contract fields and veh- ids are sequential."""
        store = fresh_store()
        v1 = store.create_vehicle("Pool Sedan 1", "sedan", MANAGER)
        v2 = store.create_vehicle("Cargo Van 2", "van", ADMIN, status="retired")
        self.assertEqual(v1["id"], "veh-1")
        self.assertEqual(v2["id"], "veh-2")
        self.assertEqual(set(v1), {"id", "label", "vehicle_type", "status", "created_by", "created_utc"})
        self.assertEqual(v1["status"], "active")
        self.assertEqual(v2["status"], "retired")
        self.assertEqual(v1["created_by"], "bob")

    def test_get_and_list(self):
        """Core 1: get returns one vehicle; list returns all sorted by id; unknown id -> NotFoundError."""
        store = fresh_store()
        vehicle = store.create_vehicle("Truck", "truck", ADMIN)
        self.assertEqual(store.get_vehicle(vehicle["id"], VIEWER)["label"], "Truck")
        self.assertEqual(len(store.list_vehicles(VIEWER)), 1)
        with self.assertRaises(NotFoundError):
            store.get_vehicle("veh-999", ADMIN)

    def test_empty_label_rejected_no_id_consumed(self):
        """Core 1 (SI-10): empty label / bad status -> ValidationError, no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_vehicle("", "sedan", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_vehicle("X", "sedan", ADMIN, status="flying")
        self.assertEqual(store.create_vehicle("First", "sedan", ADMIN)["id"], "veh-1")

    def test_viewer_write_denied(self):
        """Core 1 / Core 10 (AC-3): viewer cannot create a vehicle."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_vehicle("Nope", "sedan", VIEWER)
        self.assertEqual(store.list_vehicles(ADMIN), [])

    def test_plain_string_actor_convention(self):
        """Core 1: a plain-string actor carries identity for provenance but no role to enforce."""
        store = fresh_store()
        vehicle = store.create_vehicle("Legacy", "sedan", "alice")
        self.assertEqual(vehicle["created_by"], "alice")


if __name__ == "__main__":
    unittest.main()
