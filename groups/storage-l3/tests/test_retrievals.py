"""Core function 9: retrieval & export records -- realtime or
batch, to an inbox, a data file, or the interface; completion is a
recorded action. Delivery itself is Extended transport.
"""

import unittest

from storage.errors import NotFoundError, ValidationError

from storage_helpers import (ADMIN, OPERATOR, make_archive, make_message,
                             make_store)


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)
        self.message = make_message(self.store, self.collection)

    def test_create_and_complete(self):
        retrieval = self.store.create_retrieval(
            OPERATOR, self.message["id"], "batch", "data_file",
            "REQUESTER-REF-1")
        self.assertEqual(retrieval["status"], "requested")
        self.assertEqual(retrieval["mode"], "batch")
        done = self.store.complete_retrieval(OPERATOR, retrieval["id"])
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["completed_by"], "bob")
        with self.assertRaises(ValidationError):
            self.store.complete_retrieval(OPERATOR, retrieval["id"])

    def test_all_modes_and_destinations(self):
        for mode in ("realtime", "batch"):
            for destination in ("inbox", "data_file", "interface"):
                record = self.store.create_retrieval(
                    OPERATOR, self.message["id"], mode, destination, "R")
                self.assertEqual(record["mode"], mode)
                self.assertEqual(record["destination"], destination)
        self.assertEqual(len(self.store.list_retrievals(ADMIN)), 6)
        requested = self.store.list_retrievals(ADMIN, status="requested")
        self.assertEqual(len(requested), 6)

    def test_validation(self):
        with self.assertRaises(ValidationError):
            self.store.create_retrieval(OPERATOR, self.message["id"],
                                        "instant", "inbox", "R")
        with self.assertRaises(ValidationError):
            self.store.create_retrieval(OPERATOR, self.message["id"],
                                        "batch", "usb_drive", "R")
        with self.assertRaises(ValidationError):
            self.store.create_retrieval(OPERATOR, self.message["id"],
                                        "batch", "inbox", "")
        with self.assertRaises(NotFoundError):
            self.store.create_retrieval(OPERATOR, "msg-99", "batch",
                                        "inbox", "R")
        with self.assertRaises(NotFoundError):
            self.store.complete_retrieval(OPERATOR, "ret-99")
        self.assertEqual(self.store.list_retrievals(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
