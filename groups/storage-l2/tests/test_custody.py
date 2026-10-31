"""Core function 10: key custody records. The record names a
custodian by opaque reference and a key by opaque label -- no
field could hold key material. At most one active custody record
per collection: the fork's own statement is that a single holder
holds the keys, kept here as a record invariant.
"""

import unittest

from storage.errors import NotFoundError, ValidationError

from storage_helpers import (ADMIN, OPERATOR, make_archive, make_custody,
                             make_store)

CUSTODY_KEYS = {"id", "org_id", "collection_id", "custodian_ref",
                "key_label", "status", "created_by", "created_utc",
                "retired_by", "retired_utc"}
FORBIDDEN_KEYS = {"key", "key_material", "private_key", "secret",
                  "passphrase", "seed", "bytes"}


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.org, self.policy, self.collection = make_archive(self.store)

    def test_shape_holds_no_key_material(self):
        custody = make_custody(self.store, self.org, self.collection)
        self.assertEqual(set(custody), CUSTODY_KEYS)
        for key in custody:
            self.assertNotIn(key, FORBIDDEN_KEYS)
        self.assertEqual(custody["status"], "active")

    def test_one_active_custody_per_collection(self):
        make_custody(self.store, self.org, self.collection)
        with self.assertRaises(ValidationError):
            self.store.create_custody(OPERATOR, self.org["id"],
                                      self.collection["id"],
                                      "CUSTODIAN-REF-2", "KEY-LABEL-2")
        other = self.store.create_collection(
            ADMIN, self.org["id"], "Second archive", self.policy["id"],
            "native")
        second = self.store.create_custody(OPERATOR, self.org["id"],
                                           other["id"], "CUSTODIAN-REF-2",
                                           "KEY-LABEL-2")
        self.assertEqual(second["status"], "active")

    def test_retire_and_replace(self):
        custody = make_custody(self.store, self.org, self.collection)
        retired = self.store.retire_custody(OPERATOR, custody["id"])
        self.assertEqual(retired["status"], "retired")
        self.assertEqual(retired["retired_by"], "bob")
        with self.assertRaises(ValidationError):
            self.store.retire_custody(OPERATOR, custody["id"])
        replacement = self.store.create_custody(
            OPERATOR, self.org["id"], self.collection["id"],
            "CUSTODIAN-REF-2", "KEY-LABEL-2")
        self.assertEqual(replacement["status"], "active")
        active = self.store.list_custodies(ADMIN, status="active")
        self.assertEqual([c["id"] for c in active], [replacement["id"]])

    def test_org_collection_mismatch(self):
        other_org = self.store.create_organization(ADMIN, "ORG-0002",
                                                   "Other org")
        with self.assertRaises(ValidationError):
            self.store.create_custody(OPERATOR, other_org["id"],
                                      self.collection["id"], "C", "K")
        with self.assertRaises(NotFoundError):
            self.store.retire_custody(OPERATOR, "key-99")


if __name__ == "__main__":
    unittest.main()
