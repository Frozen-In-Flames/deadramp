"""Core functions 1-3: organization registry, application
registry, and access configuration records (CM-6, SI-10; IA-2
hooks).

The application registry is the records form of the
integrated_application_suite claim; the access configuration
records are the records form of the federated_security_sso claim.
Both are registries of records: registering connects nothing,
installs nothing, and authenticates no one.
"""

import unittest

from erp.errors import NotFoundError, PermissionDenied, ValidationError

from erp_helpers import ADMIN, OPERATOR, VIEWER, make_org, make_store


class OrganizationTests(unittest.TestCase):
    def test_create_and_read_back(self):
        store, _ = make_store()
        org = make_org(store)
        self.assertEqual(org["id"], "org-1")
        self.assertEqual(store.get_organization(VIEWER, org["id"]), org)
        self.assertEqual(len(store.list_organizations(VIEWER)), 1)

    def test_ref_is_unique(self):
        store, _ = make_store()
        make_org(store)
        with self.assertRaises(ValidationError):
            store.create_organization(ADMIN, "ORG-0001", "Duplicate")

    def test_missing_org_raises_not_found(self):
        store, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.get_organization(ADMIN, "org-99")

    def test_viewer_cannot_register(self):
        store, _ = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_organization(VIEWER, "ORG-2", "Nope")

    def test_blank_fields_refused_and_no_id_consumed(self):
        store, _ = make_store()
        with self.assertRaises(ValidationError):
            store.create_organization(ADMIN, "", "Label")
        org = make_org(store)
        self.assertEqual(org["id"], "org-1")


class ApplicationTests(unittest.TestCase):
    def test_register_and_deactivate(self):
        store, _ = make_store()
        org = make_org(store)
        app = store.create_application(
            OPERATOR, org["id"], "APP-GL", "General Ledger",
            "Financials & Supply Management")
        self.assertEqual(app["status"], "active")
        done = store.deactivate_application(OPERATOR, app["id"])
        self.assertEqual(done["status"], "inactive")
        with self.assertRaises(ValidationError):
            store.deactivate_application(OPERATOR, app["id"])
        active = store.list_applications(VIEWER, org_id=org["id"],
                                         status="active")
        self.assertEqual(active, [])

    def test_app_ref_unique_per_org_only(self):
        store, _ = make_store()
        org = make_org(store)
        other = store.create_organization(ADMIN, "ORG-0002", "Second")
        store.create_application(ADMIN, org["id"], "APP-1", "One", "Suite")
        with self.assertRaises(ValidationError):
            store.create_application(ADMIN, org["id"], "APP-1", "Dup", "Suite")
        ok = store.create_application(ADMIN, other["id"], "APP-1", "One",
                                      "Suite")
        self.assertEqual(ok["org_id"], other["id"])

    def test_application_requires_existing_org(self):
        store, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.create_application(ADMIN, "org-99", "APP-1", "One", "Suite")


class AccessConfigTests(unittest.TestCase):
    def test_config_records_hold_labels_only(self):
        store, _ = make_store()
        org = make_org(store)
        config = store.create_access_config(
            OPERATOR, org["id"], "Customer IdP (label)",
            "Customer MFA solution (label)")
        self.assertEqual(
            set(config.keys()),
            {"id", "org_id", "provider_label", "mfa_label", "status",
             "created_by", "created_utc"})
        done = store.deactivate_access_config(OPERATOR, config["id"])
        self.assertEqual(done["status"], "inactive")

    def test_config_requires_existing_org(self):
        store, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.create_access_config(ADMIN, "org-99", "IdP", "MFA")


if __name__ == "__main__":
    unittest.main()
