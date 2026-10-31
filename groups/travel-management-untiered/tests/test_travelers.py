import unittest

from travel.errors import PermissionDenied, ValidationError

from travel_helpers import MEMBER, OUTSIDER, VIEWER, make_store, make_traveler

TRAVELER_KEYS = {"id", "org_id", "traveler_ref", "label",
                 "created_by", "created_utc"}


class TestTravelers(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()

    def test_shape_is_pinned(self):
        traveler = make_traveler(self.store, self.org)
        self.assertEqual(set(traveler.keys()), TRAVELER_KEYS)

    def test_no_field_can_hold_personal_data(self):
        traveler = make_traveler(self.store, self.org)
        for key in traveler:
            self.assertNotIn(key, ("name", "email", "phone", "ssn", "dob",
                                   "passport", "document_number", "address"))

    def test_get_and_list(self):
        traveler = make_traveler(self.store, self.org)
        got = self.store.get_traveler(VIEWER, traveler["id"])
        self.assertEqual(got["traveler_ref"], "TRV-100")
        listed = self.store.list_travelers(MEMBER, self.org["id"])
        self.assertEqual([t["id"] for t in listed], [traveler["id"]])

    def test_outsider_cannot_create(self):
        with self.assertRaises(PermissionDenied):
            make_traveler(self.store, self.org, actor=OUTSIDER)

    def test_viewer_cannot_create(self):
        with self.assertRaises(PermissionDenied):
            make_traveler(self.store, self.org, actor=VIEWER)

    def test_blank_ref_rejected(self):
        with self.assertRaises(ValidationError):
            make_traveler(self.store, self.org, traveler_ref="  ")


if __name__ == "__main__":
    unittest.main()
