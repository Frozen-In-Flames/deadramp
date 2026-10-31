"""Core function 6: price-observation records.

The records price charts are drawn from; the latest observation
per series is derived at read by the summary. Prices are integer
cents; zero is a legitimate observed price, negatives are not.
"""

import unittest

from energy.errors import PermissionDenied, ValidationError

from energy_helpers import MEMBER, VIEWER, make_store, ADMIN


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()

    def observe(self, price=350, at="2024-06-02T00:00:00+00:00", actor=ADMIN):
        return self.store.record_observation(actor, "ERCOT-North",
                                             "electricity", price,
                                             observed_at=at)

    def test_record_shape(self):
        obs = self.observe()
        self.assertEqual(obs["id"], "obs-1")
        self.assertEqual(obs["region"], "ERCOT-North")
        self.assertEqual(obs["price_cents_per_unit"], 350)
        self.assertEqual(obs["observed_at"], "2024-06-02T00:00:00+00:00")

    def test_zero_price_allowed_negative_and_floats_rejected(self):
        self.assertEqual(self.observe(price=0)["price_cents_per_unit"], 0)
        for bad in (-1, 3.5, 350.0, True, "350"):
            with self.assertRaises(ValidationError):
                self.observe(price=bad)

    def test_filters(self):
        self.observe()
        self.store.record_observation(ADMIN, "ERCOT-South", "natural gas",
                                      210,
                                      observed_at="2024-06-02T00:00:00+00:00")
        self.assertEqual(len(self.store.list_observations(ADMIN)), 2)
        self.assertEqual(
            len(self.store.list_observations(ADMIN, region="ERCOT-North")), 1)
        self.assertEqual(
            len(self.store.list_observations(ADMIN, commodity="natural gas")),
            1)

    def test_roles(self):
        with self.assertRaises(PermissionDenied):
            self.observe(actor=VIEWER)
        self.observe(actor=MEMBER)


if __name__ == "__main__":
    unittest.main()
