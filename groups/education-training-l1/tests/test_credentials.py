"""Certificate/credential record tests.

Traces to: Core function 5 (Certificate/credential RECORDS; claim
family certificates_credentials 0/2 in this group, carried under the
core-boundary decision (3/8 at L2); AU-2). Records only -- credential
issuance is claimed by 0 siblings in either tier and is NOT implemented;
these tests assert the record form only.
"""

import unittest

from learn_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from learn.errors import NotFoundError, PermissionDenied, ValidationError


class TestCredentials(unittest.TestCase):
    """Core 5: credential records and their tracked status (no issuance)."""

    def test_create_credential_record(self):
        """Core 5: a credential record carries cred- id, learner, kind, status and ISO dates."""
        store, _ = make_store()
        rec = store.create_credential(
            "carol", "Safety Certification", ADMIN,
            kind="certification", issued_date="2026-01-15", expiry_date="2027-01-15",
        )
        self.assertEqual(rec["id"], "cred-1")
        self.assertEqual(rec["status"], "active")
        self.assertEqual(rec["issued_date"], "2026-01-15")
        self.assertEqual(rec["expiry_date"], "2027-01-15")

    def test_status_update_is_a_record_change(self):
        """Core 5 (AU-2): set_credential_status updates the tracked status on the record; bad status -> ValidationError."""
        store, _ = make_store()
        rec = store.create_credential("carol", "License", ADMIN, kind="licensure")
        updated = store.set_credential_status(rec["id"], "expired", ADMIN)
        self.assertEqual(updated["status"], "expired")
        with self.assertRaises(ValidationError):
            store.set_credential_status(rec["id"], "issued-by-engine", ADMIN)
        with self.assertRaises(NotFoundError):
            store.set_credential_status("cred-999", "active", ADMIN)

    def test_date_validation(self):
        """Core 5 (SI-10): non-ISO dates and expiry before issued are validation errors."""
        store, _ = make_store()
        with self.assertRaises(ValidationError):
            store.create_credential("carol", "X", ADMIN, issued_date="Jan 2026")
        with self.assertRaises(ValidationError):
            store.create_credential(
                "carol", "X", ADMIN, issued_date="2026-06-01", expiry_date="2026-01-01"
            )

    def test_credential_write_admin_only_and_scope(self):
        """Core 5 / Core 9: credential_write is admin-only in this build; learner reads own records only."""
        store, _ = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_credential("carol", "X", INSTRUCTOR)
        own = store.create_credential("carol", "Cert", ADMIN)
        other = store.create_credential("erin", "Cert", ADMIN)
        self.assertEqual(store.get_credential(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_credential(other["id"], LEARNER)
        self.assertEqual([c["id"] for c in store.list_credentials(LEARNER)], [own["id"]])


if __name__ == "__main__":
    unittest.main()
