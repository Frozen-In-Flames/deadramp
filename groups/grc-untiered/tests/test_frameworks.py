"""Framework & control catalog registry tests.

Traces to: Core function 1 (framework & control catalog registry —
framework records with id/name/version, controls within them with a
control id like "AC-2", a family, and a title; a seeded 800-53-style
catalog kept modest and generic); control families CA-2 / CA-7.
"""

import unittest

from grc_helpers import ADMIN, MEMBER, SEED_FRAMEWORK_ID, fresh_store
from grc.catalog import CONTROL_CATALOG, CONTROL_IDS, control_by_id
from grc.errors import NotFoundError, PermissionDenied, ValidationError


class TestSeedCatalog(unittest.TestCase):
    """Core 1: the seeded catalog data itself."""

    def test_seed_catalog_is_modest_and_well_formed(self):
        """Core 1. The seed catalog holds exactly 21 controls, each
        {id, family, title} with family equal to the id's prefix."""
        self.assertEqual(len(CONTROL_CATALOG), 21)
        for entry in CONTROL_CATALOG:
            self.assertEqual(set(entry), {"id", "family", "title"})
            self.assertEqual(entry["family"], entry["id"].split("-", 1)[0])
            self.assertTrue(entry["title"])

    def test_control_ids_and_lookup(self):
        """Core 1. CONTROL_IDS matches the catalog and control_by_id
        returns a copy (or None for an unknown id)."""
        self.assertEqual(CONTROL_IDS, {e["id"] for e in CONTROL_CATALOG})
        entry = control_by_id("AC-2")
        self.assertEqual(entry["title"], "Account Management")
        entry["title"] = "mutated"
        self.assertEqual(control_by_id("AC-2")["title"], "Account Management")
        self.assertIsNone(control_by_id("ZZ-9"))


class TestSeededRegistry(unittest.TestCase):
    """Core 1: the store registry is seeded from the catalog."""

    def setUp(self):
        self.store = fresh_store()

    def test_seed_framework_present(self):
        """Core 1. A fresh store carries the seed framework record
        with id/name/version."""
        frameworks = self.store.list_frameworks(actor=ADMIN)
        self.assertEqual(len(frameworks), 1)
        framework = frameworks[0]
        self.assertEqual(framework["id"], SEED_FRAMEWORK_ID)
        self.assertEqual(framework["name"], "NIST SP 800-53")
        self.assertEqual(framework["version"], "Rev. 5")

    def test_seed_controls_present_in_framework(self):
        """Core 1. A fresh store carries all 21 seed controls inside
        the seed framework, each with framework_id/id/family/title."""
        controls = self.store.list_controls(actor=ADMIN, framework_id=SEED_FRAMEWORK_ID)
        self.assertEqual(len(controls), 21)
        ac2 = self.store.get_control(SEED_FRAMEWORK_ID, "AC-2", actor=ADMIN)
        self.assertEqual(
            ac2,
            {
                "framework_id": SEED_FRAMEWORK_ID,
                "id": "AC-2",
                "family": "AC",
                "title": "Account Management",
            },
        )

    def test_seeding_writes_no_audit_entries(self):
        """Core 1 + Core 10 Audit. Seeding is data loading, not a
        mutation: a fresh store with an audit log has no entries."""
        from grc.audit import AuditLog

        audit = AuditLog()
        store = fresh_store(audit=audit)
        self.assertEqual(store.list_frameworks(actor=ADMIN)[0]["id"], SEED_FRAMEWORK_ID)
        self.assertEqual(audit.entries(), [])


class TestFrameworkRegistration(unittest.TestCase):
    """Core 1: registering caller frameworks and controls."""

    def setUp(self):
        self.store = fresh_store()

    def test_create_framework_shape(self):
        """Core 1. create_framework stores id/name/version/description
        plus provenance."""
        framework = self.store.create_framework(
            "ORG-FW-1", "Internal Control Set", "2026.1",
            actor=ADMIN, description="house controls",
        )
        self.assertEqual(framework["id"], "ORG-FW-1")
        self.assertEqual(framework["name"], "Internal Control Set")
        self.assertEqual(framework["version"], "2026.1")
        self.assertEqual(framework["description"], "house controls")
        self.assertEqual(framework["created_by"], "alice")
        self.assertIn("created_utc", framework)

    def test_create_framework_duplicate_rejected(self):
        """Core 1. A duplicate framework id is a ValidationError and
        registers nothing new."""
        self.store.create_framework("ORG-FW-1", "One", "1", actor=ADMIN)
        with self.assertRaises(ValidationError):
            self.store.create_framework("ORG-FW-1", "Two", "2", actor=ADMIN)
        self.assertEqual(len(self.store.list_frameworks(actor=ADMIN)), 2)

    def test_create_framework_validation(self):
        """Core 1. Empty id/name/version are each a ValidationError."""
        for args in [("", "n", "v"), ("X", "", "v"), ("X", "n", ""), (None, "n", "v")]:
            with self.assertRaises(ValidationError):
                self.store.create_framework(*args, actor=ADMIN)

    def test_create_framework_requires_admin(self):
        """Core 1 + Core 9 RBAC. A member may not register a
        framework (manage_frameworks is admin-only)."""
        with self.assertRaises(PermissionDenied):
            self.store.create_framework("ORG-FW-1", "One", "1", actor=MEMBER)

    def test_create_control_and_family_default(self):
        """Core 1. create_control registers a control in a framework;
        family defaults to the control id's prefix."""
        self.store.create_framework("ORG-FW-1", "One", "1", actor=ADMIN)
        control = self.store.create_control("ORG-FW-1", "GV-1", "Governance", actor=ADMIN)
        self.assertEqual(control["family"], "GV")
        self.assertEqual(control["framework_id"], "ORG-FW-1")
        listed = self.store.list_controls(actor=ADMIN, framework_id="ORG-FW-1")
        self.assertEqual([c["id"] for c in listed], ["GV-1"])

    def test_create_control_unknown_framework_404(self):
        """Core 1. Registering a control in a missing framework is a
        NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.create_control("NOPE", "GV-1", "Governance", actor=ADMIN)

    def test_create_control_duplicate_rejected(self):
        """Core 1. The same control id twice in one framework is a
        ValidationError; the same id in a different framework is a
        different control and is allowed."""
        with self.assertRaises(ValidationError):
            self.store.create_control(
                SEED_FRAMEWORK_ID, "AC-2", "Duplicate", actor=ADMIN
            )
        self.store.create_framework("ORG-FW-1", "One", "1", actor=ADMIN)
        control = self.store.create_control("ORG-FW-1", "AC-2", "House AC-2", actor=ADMIN)
        self.assertEqual(control["title"], "House AC-2")

    def test_get_missing_framework_and_control_404(self):
        """Core 1. Unknown framework / control ids are NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_framework("NOPE", actor=ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_control(SEED_FRAMEWORK_ID, "ZZ-9", actor=ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.list_controls(actor=ADMIN, framework_id="NOPE")


if __name__ == "__main__":
    unittest.main()
