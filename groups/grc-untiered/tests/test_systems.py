"""Governed-system registry tests.

Traces to: Core function 2 (governed-system registry — systems under
governance keyed by opaque caller-supplied references; free-text names
are labels only); control family CM-8.
"""

import unittest

from grc_helpers import ADMIN, MEMBER, VIEWER, SYSTEM_REF, fresh_store, make_store
from grc.errors import NotFoundError, PermissionDenied, ValidationError


class TestSystemRegistry(unittest.TestCase):
    """Core 2: governed systems keyed by caller-supplied references."""

    def setUp(self):
        self.store = fresh_store()

    def test_create_system_shape_and_provenance(self):
        """Core 2. A system record is keyed by its opaque ref and
        carries the free-text label, description, and provenance."""
        system = self.store.create_system(
            SYSTEM_REF, "example portal", actor=MEMBER, description="first system"
        )
        self.assertEqual(system["ref"], SYSTEM_REF)
        self.assertEqual(system["name"], "example portal")
        self.assertEqual(system["description"], "first system")
        self.assertEqual(system["created_by"], "bob")
        self.assertIn("created_utc", system)
        self.assertIn("updated_utc", system)
        self.assertEqual(self.store.get_system(SYSTEM_REF, actor=VIEWER), system)

    def test_ref_is_opaque_and_caller_supplied(self):
        """Core 2. Any non-empty string works as a reference; no
        agency or product naming is required or imposed."""
        for ref in ["SYS-001", "a1b2c3", "opaque/ref-42", "x"]:
            system = self.store.create_system(ref, "label", actor=MEMBER)
            self.assertEqual(system["ref"], ref)
        self.assertEqual(len(self.store.list_systems(actor=ADMIN)), 4)

    def test_duplicate_ref_rejected(self):
        """Core 2. A duplicate reference is a ValidationError and the
        registry is unchanged."""
        self.store.create_system(SYSTEM_REF, "one", actor=MEMBER)
        with self.assertRaises(ValidationError):
            self.store.create_system(SYSTEM_REF, "two", actor=MEMBER)
        self.assertEqual(len(self.store.list_systems(actor=ADMIN)), 1)

    def test_empty_ref_or_name_rejected(self):
        """Core 2. Empty / non-string ref or name is a ValidationError."""
        for ref, name in [("", "x"), (None, "x"), ("R", ""), ("R", None)]:
            with self.assertRaises(ValidationError):
                self.store.create_system(ref, name, actor=MEMBER)

    def test_get_missing_system_404(self):
        """Core 2. An unknown reference is a NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_system("NOPE", actor=ADMIN)

    def test_viewer_may_read_but_not_create(self):
        """Core 2 + Core 9 RBAC. Viewer reads systems; creating one
        as viewer is PermissionDenied."""
        store, system, _ = make_store()
        self.assertEqual(store.get_system(SYSTEM_REF, actor=VIEWER)["ref"], SYSTEM_REF)
        with self.assertRaises(PermissionDenied):
            store.create_system("SYS-002", "second", actor=VIEWER)


if __name__ == "__main__":
    unittest.main()
