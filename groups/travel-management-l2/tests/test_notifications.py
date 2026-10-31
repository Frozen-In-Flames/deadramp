import unittest

from travel.errors import PermissionDenied, ValidationError

from travel_helpers import MEMBER, OUTSIDER, VIEWER, make_store


class TestNotifications(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()

    def test_record_and_list(self):
        note_rec = self.store.create_notification(
            MEMBER, self.org["id"], "decision", "TRV-100",
            target_kind="authorization", target_id="auth-1")
        self.assertEqual(note_rec["kind"], "decision")
        listed = self.store.list_notifications(MEMBER, self.org["id"])
        self.assertEqual([n["id"] for n in listed], [note_rec["id"]])

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_notification(MEMBER, self.org["id"], "sms",
                                           "TRV-100")

    def test_viewer_cannot_record(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_notification(VIEWER, self.org["id"],
                                           "general", "TRV-100")

    def test_outsider_cannot_record(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_notification(OUTSIDER, self.org["id"],
                                           "general", "TRV-100")

    def test_records_only_no_delivery_fields(self):
        note_rec = self.store.create_notification(
            MEMBER, self.org["id"], "reminder", "TRV-100")
        for key in note_rec:
            self.assertNotIn(key, ("delivered", "delivered_utc", "sent",
                                   "channel_status", "message_id"))


if __name__ == "__main__":
    unittest.main()
