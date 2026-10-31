"""Core: Access request records. Traces to UNION-SPEC core
functions 6 (data sharing, transacted as records) and 7 (open
access & controlled access data): requests exist only for
controlled datasets — a request against an open dataset is a
false gate and is rejected (SI-10). The lifecycle is
event-driven: pending -> approved / denied, plus withdrawn
while pending."""

import unittest

import research_helpers as H
from research.errors import PermissionDenied, ValidationError

EXPECTED_KEYS = {"id", "dataset_id", "commons_id", "requester", "purpose",
                 "duration_days", "status", "created_by", "created_utc"}


class TestAccessRequests(unittest.TestCase):
    def setUp(self):
        self.store, self.commons, self.org = H.make_store()
        self.dataset = H.make_dataset(self.store, self.commons)
        self.open_dataset = H.make_dataset(
            self.store, self.commons, name="open-registry",
            access_tier="open", sha256=H.SHA256_B)

    def test_request_on_controlled_dataset_shape(self):
        request = H.make_access_request(self.store, self.dataset)
        self.assertEqual(set(request.keys()), EXPECTED_KEYS)
        self.assertTrue(request["id"].startswith("ar-"))
        self.assertEqual(request["dataset_id"], self.dataset["id"])
        self.assertEqual(request["commons_id"], self.commons["id"])
        self.assertEqual(request["requester"], "bob")
        self.assertEqual(request["created_by"], "bob")
        self.assertEqual(request["duration_days"], 30)
        self.assertEqual(request["status"], "pending")

    def test_request_on_open_dataset_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_access_request(self.store, self.open_dataset)
        self.assertEqual(
            self.store.list_access_requests(H.MEMBER,
                                            self.open_dataset["id"]), [])

    def test_duration_days_validation(self):
        for bad in (0, -1, 1.5, True, "30"):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                H.make_access_request(self.store, self.dataset,
                                      duration_days=bad)
        # Rejection is whole: no request record was created.
        self.assertEqual(
            self.store.list_access_requests(H.MEMBER, self.dataset["id"]),
            [])

    def test_empty_purpose_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_access_request(self.store, self.dataset, purpose="  ")

    def test_withdraw_from_pending(self):
        request = H.make_access_request(self.store, self.dataset)
        withdrawn = self.store.withdraw_access_request(H.MEMBER,
                                                       request["id"])
        self.assertEqual(withdrawn["status"], "withdrawn")
        self.assertEqual(
            self.store.get_access_request(H.MEMBER,
                                          request["id"])["status"],
            "withdrawn")

    def test_withdraw_after_decision_rejected(self):
        request = H.make_access_request(self.store, self.dataset)
        self.store.decide_access_request(H.STAFF, request["id"], True,
                                         starts_at=H.T0)
        with self.assertRaises(ValidationError):
            self.store.withdraw_access_request(H.MEMBER, request["id"])

    def test_withdraw_twice_rejected(self):
        request = H.make_access_request(self.store, self.dataset)
        self.store.withdraw_access_request(H.MEMBER, request["id"])
        with self.assertRaises(ValidationError):
            self.store.withdraw_access_request(H.MEMBER, request["id"])

    def test_get_and_list(self):
        first = H.make_access_request(self.store, self.dataset)
        H.make_access_request(self.store, self.dataset,
                              purpose="Second planned analysis")
        fetched = self.store.get_access_request(H.STAFF, first["id"])
        self.assertEqual(fetched["requester"], "bob")
        requests = self.store.list_access_requests(H.MEMBER,
                                                   self.dataset["id"])
        self.assertEqual(len(requests), 2)
        self.assertEqual(
            self.store.list_access_requests(H.MEMBER,
                                            self.open_dataset["id"]), [])

    def test_outsider_denied(self):
        request = H.make_access_request(self.store, self.dataset)
        with self.assertRaises(PermissionDenied):
            H.make_access_request(self.store, self.dataset,
                                  actor=H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.get_access_request(H.OUTSIDER, request["id"])
        with self.assertRaises(PermissionDenied):
            self.store.list_access_requests(H.OUTSIDER,
                                            self.dataset["id"])


if __name__ == "__main__":
    unittest.main()
