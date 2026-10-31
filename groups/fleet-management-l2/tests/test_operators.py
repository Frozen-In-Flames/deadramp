"""Operator record tests (privacy discipline).

Traces to: Core function 2 (Operator records) -- records keyed by an
OPAQUE caller-supplied reference, with NO fields that can hold a real
name, license number, or other PII (Group 18/21 style privacy
discipline). The exact key set is pinned here.
"""

import unittest

from fleet_helpers import ADMIN, VIEWER, fresh_store
from fleet.errors import NotFoundError, ValidationError

OPERATOR_KEYS = {"id", "operator_ref", "credential_kind", "credential_status",
                 "created_by", "created_utc"}


class TestOperators(unittest.TestCase):
    """Core 2: operator record shape is exactly the opaque-reference key set."""

    def test_create_shape_exact_keys(self):
        """Core 2 (privacy): an operator record's key set is EXACTLY the pinned set -- no name/license/PII fields exist."""
        store = fresh_store()
        op = store.create_operator("OP-REF-001", "license", ADMIN)
        self.assertEqual(set(op), OPERATOR_KEYS)
        self.assertEqual(op["id"], "opr-1")
        self.assertEqual(op["operator_ref"], "OP-REF-001")
        self.assertEqual(op["credential_kind"], "license")
        self.assertEqual(op["credential_status"], "active")
        for forbidden in ("name", "full_name", "license_number", "licence_number",
                          "ssn", "email", "phone", "address", "dob"):
            self.assertNotIn(forbidden, op)

    def test_credential_status_enum(self):
        """Core 2: credential_status accepts the defined set; anything else -> ValidationError, no id consumed."""
        store = fresh_store()
        for status in ("active", "suspended", "revoked", "expired"):
            op = store.create_operator("REF-%s" % status, "license", ADMIN, credential_status=status)
            self.assertEqual(op["credential_status"], status)
        with self.assertRaises(ValidationError):
            store.create_operator("REF-X", "license", ADMIN, credential_status="unknown")
        self.assertEqual(store.create_operator("REF-Y", "license", ADMIN)["id"], "opr-5")

    def test_empty_ref_rejected(self):
        """Core 2 (SI-10): empty operator_ref / credential_kind -> ValidationError."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_operator("", "license", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_operator("REF", "", ADMIN)
        self.assertEqual(store.list_operators(ADMIN), [])

    def test_get_and_list(self):
        """Core 2: get/list return operator records to a viewer (read is baseline)."""
        store = fresh_store()
        op = store.create_operator("OP-REF-9", "cdl", ADMIN)
        self.assertEqual(store.get_operator(op["id"], VIEWER)["operator_ref"], "OP-REF-9")
        self.assertEqual(len(store.list_operators(VIEWER)), 1)
        with self.assertRaises(NotFoundError):
            store.get_operator("opr-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
