"""Guidance content registry tests.

Traces to: Core 4 (Guidance content registry) -- claim basis
guidance_adoption (WalkMe) -- and control families CM-6, SA-4.
Guides are records; nothing here renders guidance into an app.
"""

import unittest

import crm_helpers as H
from crm.errors import NotFoundError, PermissionDenied, ValidationError


class TestGuides(unittest.TestCase):
    """Core 4: guides (guide-), versioned."""

    def setUp(self):
        self.store = H.fresh_store()

    def test_create_shape(self):
        """Core 4: guide shape at version 1 with versions list."""
        guide = self.store.create_guide(
            H.OPERATOR, "Onboarding tour", "walkthrough", "surface:portal",
            steps=["Open portal", "Click start"])
        self.assertEqual(guide["id"], "guide-1")
        self.assertEqual(guide["version"], 1)
        self.assertEqual(len(guide["versions"]), 1)
        self.assertEqual(guide["versions"][0]["steps"], ["Open portal", "Click start"])
        self.assertTrue(guide["enabled"])

    def test_all_kinds(self):
        """Core 4: all four guide kinds accepted; unknown kind ->
        ValidationError."""
        for kind in ("walkthrough", "tooltip", "checklist", "announcement"):
            g = self.store.create_guide(H.OPERATOR, "t", kind, "surface:x")
            self.assertEqual(g["kind"], kind)
        with self.assertRaises(ValidationError):
            self.store.create_guide(H.OPERATOR, "t", "video", "surface:x")

    def test_validation(self):
        """Core 4 (SI-10): empty title/target, bad steps, non-bool
        enabled -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.create_guide(H.OPERATOR, "", "walkthrough", "surface:x")
        with self.assertRaises(ValidationError):
            self.store.create_guide(H.OPERATOR, "t", "walkthrough", "")
        with self.assertRaises(ValidationError):
            self.store.create_guide(H.OPERATOR, "t", "walkthrough", "surface:x",
                                    steps=["ok", " "])
        with self.assertRaises(ValidationError):
            self.store.create_guide(H.OPERATOR, "t", "walkthrough", "surface:x",
                                    steps="not-a-list")
        with self.assertRaises(ValidationError):
            self.store.create_guide(H.OPERATOR, "t", "walkthrough", "surface:x",
                                    enabled="yes")

    def test_update_versions(self):
        """Core 4 (CM-6): update appends a version, carries unchanged
        fields forward, bumps the counter."""
        guide = self.store.create_guide(H.OPERATOR, "Tour", "walkthrough",
                                        "surface:a", steps=["one"])
        out = self.store.update_guide(guide["id"], H.OPERATOR, steps=["one", "two"])
        self.assertEqual(out["version"], 2)
        self.assertEqual(out["steps"], ["one", "two"])
        self.assertEqual(out["target_ref"], "surface:a")
        self.assertEqual(len(out["versions"]), 2)
        self.assertEqual(out["versions"][0]["steps"], ["one"])

    def test_update_enabled_and_target(self):
        """Core 4: enabled/target_ref updates version too."""
        guide = self.store.create_guide(H.OPERATOR, "Tour", "tooltip", "surface:a")
        out = self.store.update_guide(guide["id"], H.OPERATOR, enabled=False,
                                      target_ref="surface:b")
        self.assertFalse(out["enabled"])
        self.assertEqual(out["target_ref"], "surface:b")
        self.assertEqual(out["version"], 2)

    def test_update_unknown(self):
        """Core 4: updating an unknown guide -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.update_guide("guide-99", H.OPERATOR, steps=["x"])

    def test_viewer_write_denied(self):
        """Core 4/10 (AC-3): viewer may not write guides."""
        with self.assertRaises(PermissionDenied):
            self.store.create_guide(H.VIEWER, "t", "walkthrough", "surface:x")

    def test_copies_are_copies(self):
        """Core 4: returned guides (incl. versions) are deep copies."""
        guide = self.store.create_guide(H.OPERATOR, "Tour", "walkthrough",
                                        "surface:a", steps=["one"])
        guide["versions"][0]["steps"].append("tampered")
        fresh = self.store.get_guide(guide["id"], H.VIEWER)
        self.assertEqual(fresh["versions"][0]["steps"], ["one"])


if __name__ == "__main__":
    unittest.main()
