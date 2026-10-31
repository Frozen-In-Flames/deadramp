"""Module configuration registry tests.

Traces to: Core 6 (Configuration / module registry) -- claim basis
configuration_extensibility (both siblings) -- and control families
CM-6, SA-4. Writes are admin-only; settings are stored verbatim and
never executed.
"""

import unittest

import crm_helpers as H
from crm.errors import NotFoundError, PermissionDenied, ValidationError


class TestModules(unittest.TestCase):
    """Core 6: modules (mod-), versioned, admin-write."""

    def setUp(self):
        self.store = H.fresh_store()

    def test_create_shape(self):
        """Core 6: module shape at version 1 with versions list."""
        mod = self.store.create_module(H.ADMIN, "case-routing", "service",
                                       "route=inquiry->tier1")
        self.assertEqual(mod["id"], "mod-1")
        self.assertEqual(mod["version"], 1)
        self.assertEqual(mod["versions"][0]["settings_text"], "route=inquiry->tier1")
        self.assertTrue(mod["enabled"])

    def test_validation(self):
        """Core 6 (SI-10): empty name/scope/settings, non-bool
        enabled -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_module(H.ADMIN, "", "service", "x=1")
        with self.assertRaises(ValidationError):
            self.store.create_module(H.ADMIN, "m", "", "x=1")
        with self.assertRaises(ValidationError):
            self.store.create_module(H.ADMIN, "m", "service", "")
        with self.assertRaises(ValidationError):
            self.store.create_module(H.ADMIN, "m", "service", "x=1", enabled=1)

    def test_admin_only_write(self):
        """Core 6/10 (AC-6): config_write is admin-only -- operator
        and viewer are denied create and update."""
        with self.assertRaises(PermissionDenied):
            self.store.create_module(H.OPERATOR, "m", "service", "x=1")
        with self.assertRaises(PermissionDenied):
            self.store.create_module(H.VIEWER, "m", "service", "x=1")
        mod = self.store.create_module(H.ADMIN, "m", "service", "x=1")
        with self.assertRaises(PermissionDenied):
            self.store.update_module(mod["id"], H.OPERATOR, settings_text="x=2")

    def test_update_versions(self):
        """Core 6 (CM-6): update appends a version carrying unchanged
        fields forward."""
        mod = self.store.create_module(H.ADMIN, "m", "service", "x=1")
        out = self.store.update_module(mod["id"], H.ADMIN, enabled=False)
        self.assertEqual(out["version"], 2)
        self.assertEqual(out["settings_text"], "x=1")
        self.assertFalse(out["enabled"])
        out = self.store.update_module(mod["id"], H.ADMIN, settings_text="x=2")
        self.assertEqual(out["version"], 3)
        self.assertEqual(out["settings_text"], "x=2")
        self.assertEqual(len(out["versions"]), 3)

    def test_update_unknown(self):
        """Core 6: unknown module -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.update_module("mod-99", H.ADMIN, settings_text="x=2")

    def test_reads_open_to_viewer(self):
        """Core 6: config_read is a normal read -- viewer may read."""
        mod = self.store.create_module(H.ADMIN, "m", "service", "x=1")
        self.assertEqual(self.store.get_module(mod["id"], H.VIEWER)["label"], "m")
        self.assertEqual(len(self.store.list_modules(H.VIEWER)), 1)


if __name__ == "__main__":
    unittest.main()
