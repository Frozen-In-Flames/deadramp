"""Usage & odometer record tests.

Traces to: Core function 5 (Usage & odometer records) -- the stated
monotonic sanity rule: a reading lower than the vehicle's latest
recorded usage reading is rejected; equal or higher is accepted.
"""

import unittest

from fleet_helpers import ADMIN, MANAGER, make_store
from fleet.errors import NotFoundError, ValidationError


class TestUsage(unittest.TestCase):
    """Core 5: usage records and the monotonic odometer rule."""

    def test_record_shape_and_ids(self):
        """Core 5: a usage record carries the contract fields and use- ids are sequential."""
        store, vehicle, operator = make_store()
        rec = store.record_usage(vehicle["id"], 10000, MANAGER)
        self.assertEqual(rec["id"], "use-1")
        self.assertEqual(set(rec), {"id", "vehicle_id", "odometer_reading",
                                    "recorded_utc", "created_by"})
        self.assertEqual(rec["odometer_reading"], 10000)
        self.assertEqual(store.record_usage(vehicle["id"], 10050, ADMIN)["id"], "use-2")

    def test_monotonic_rule(self):
        """Core 5 monotonic rule: lower than latest -> ValidationError (nothing recorded, no id consumed); equal and higher accepted."""
        store, vehicle, operator = make_store()
        store.record_usage(vehicle["id"], 10000, ADMIN)
        with self.assertRaises(ValidationError):
            store.record_usage(vehicle["id"], 9999, ADMIN)
        self.assertEqual(len(store.list_usage(vehicle_id=vehicle["id"], actor=ADMIN)), 1)
        equal = store.record_usage(vehicle["id"], 10000, ADMIN)
        self.assertEqual(equal["id"], "use-2")
        self.assertEqual(store.record_usage(vehicle["id"], 10001, ADMIN)["id"], "use-3")

    def test_monotonic_is_per_vehicle(self):
        """Core 5: the monotonic rule compares against the SAME vehicle's latest reading only."""
        store, vehicle, operator = make_store()
        other = store.create_vehicle("Other", "van", ADMIN)
        store.record_usage(vehicle["id"], 50000, ADMIN)
        rec = store.record_usage(other["id"], 10, ADMIN)
        self.assertEqual(rec["odometer_reading"], 10)

    def test_unknown_vehicle_and_bad_reading(self):
        """Core 5 (SI-10): unknown vehicle -> NotFoundError; negative / float / string reading -> ValidationError."""
        store, vehicle, operator = make_store()
        with self.assertRaises(NotFoundError):
            store.record_usage("veh-999", 100, ADMIN)
        for bad in (-5, 1.5, "100", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    store.record_usage(vehicle["id"], bad, ADMIN)
        self.assertEqual(store.list_usage(actor=ADMIN), [])


if __name__ == "__main__":
    unittest.main()
