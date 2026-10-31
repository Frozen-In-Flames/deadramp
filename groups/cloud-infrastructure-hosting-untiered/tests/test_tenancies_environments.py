"""Tenancies and environments: hosting models, provider links,
derived deployment counts, guarded environment lifecycle
(Core functions 2, 3, 4)."""

import unittest

import cloudinfra_helpers as H
from cloudinfra.errors import NotFoundError, PermissionDenied, ValidationError


class TestTenancies(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()
        self.org = H.make_org(self.store)
        self.oid = self.org["id"]

    def test_create_tenancy_shape_and_derived_counts(self):
        tenancy = self.store.create_tenancy(
            self.oid, "ten-main", "Main tenancy", "managed", H.MEMBER)
        self.assertEqual(tenancy["id"], "ten-1")
        self.assertEqual(tenancy["hosting_model"], "managed")
        self.assertIsNone(tenancy["provider_id"])
        self.assertEqual(tenancy["deployment_count"], 0)
        self.assertEqual(tenancy["active_deployment_count"], 0)
        # Derived keys are not stored.
        self.assertNotIn("deployment_count", self.store._tenancies["ten-1"])
        self.assertNotIn("active_deployment_count", self.store._tenancies["ten-1"])

    def test_all_hosting_models_accepted(self):
        for i, model in enumerate(
                ("boundary_protected", "managed", "enclave", "shared")):
            tenancy = self.store.create_tenancy(
                self.oid, "ten-%s" % model, model, model, H.MEMBER)
            self.assertEqual(tenancy["hosting_model"], model)

    def test_invalid_hosting_model_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_tenancy(
                self.oid, "ten-x", "X", "kubernetes", H.MEMBER)

    def test_duplicate_tenancy_ref_rejected(self):
        self.store.create_tenancy(self.oid, "ten-a", "A", "shared", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.create_tenancy(self.oid, "ten-a", "A2", "shared", H.MEMBER)

    def test_provider_link_must_exist_in_org(self):
        with self.assertRaises(NotFoundError):
            self.store.create_tenancy(
                self.oid, "ten-a", "A", "shared", H.MEMBER,
                provider_id="prv-99")
        provider = self.store.register_provider(
            self.oid, "prv-aws", "AWS US East/West", H.MEMBER)
        tenancy = self.store.create_tenancy(
            self.oid, "ten-a", "A", "shared", H.MEMBER,
            provider_id=provider["id"])
        self.assertEqual(tenancy["provider_id"], provider["id"])

    def test_provider_link_from_other_org_rejected(self):
        other = self.store.create_organization("org-other", "Other", H.ADMIN)
        foreign = self.store.register_provider(
            other["id"], "prv-x", "X", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.create_tenancy(
                self.oid, "ten-a", "A", "shared", H.MEMBER,
                provider_id=foreign["id"])

    def test_derived_counts_track_deployments(self):
        tenancy = self.store.create_tenancy(
            self.oid, "ten-a", "A", "shared", H.MEMBER)
        d1 = self.store.create_deployment(
            self.oid, tenancy["id"], "dep-1", "wl-1", H.MEMBER)
        self.store.create_deployment(
            self.oid, tenancy["id"], "dep-2", "wl-2", H.MEMBER)
        view = self.store.get_tenancy(self.oid, tenancy["id"], H.MEMBER)
        self.assertEqual(view["deployment_count"], 2)
        self.assertEqual(view["active_deployment_count"], 0)
        self.store.activate_deployment(self.oid, d1["id"], H.MEMBER)
        view = self.store.get_tenancy(self.oid, tenancy["id"], H.MEMBER)
        self.assertEqual(view["active_deployment_count"], 1)

    def test_viewer_cannot_create_tenancy(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_tenancy(
                self.oid, "ten-a", "A", "shared", H.VIEWER)

    def test_outsider_cannot_create_tenancy(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_tenancy(
                self.oid, "ten-a", "A", "shared", H.OUTSIDER)


class TestEnvironments(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()
        self.org = H.make_org(self.store)
        self.oid = self.org["id"]
        self.tenancy = self.store.create_tenancy(
            self.oid, "ten-a", "A", "enclave", H.MEMBER)

    def test_create_environment_defaults(self):
        env = self.store.create_environment(
            self.oid, "env-prod", "Production", H.MEMBER,
            tenancy_id=self.tenancy["id"], residency_label="U.S. soil")
        self.assertEqual(env["status"], "provisioned")
        self.assertEqual(env["residency_label"], "U.S. soil")
        self.assertEqual(env["tenancy_id"], self.tenancy["id"])

    def test_environment_tenancy_link_validated(self):
        with self.assertRaises(NotFoundError):
            self.store.create_environment(
                self.oid, "env-x", "X", H.MEMBER, tenancy_id="ten-99")

    def test_environment_lifecycle_happy_path(self):
        env = self.store.create_environment(
            self.oid, "env-prod", "Production", H.MEMBER)
        env = self.store.set_environment_status(
            self.oid, env["id"], "active", H.MEMBER)
        self.assertEqual(env["status"], "active")
        env = self.store.set_environment_status(
            self.oid, env["id"], "retired", H.MEMBER)
        self.assertEqual(env["status"], "retired")

    def test_environment_provisioned_may_retire_directly(self):
        env = self.store.create_environment(
            self.oid, "env-x", "X", H.MEMBER)
        env = self.store.set_environment_status(
            self.oid, env["id"], "retired", H.MEMBER)
        self.assertEqual(env["status"], "retired")

    def test_environment_invalid_transitions_rejected(self):
        env = self.store.create_environment(
            self.oid, "env-x", "X", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.set_environment_status(
                self.oid, env["id"], "provisioned", H.MEMBER)
        self.store.set_environment_status(self.oid, env["id"], "retired", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.set_environment_status(
                self.oid, env["id"], "active", H.MEMBER)

    def test_duplicate_environment_ref_rejected(self):
        self.store.create_environment(self.oid, "env-x", "X", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.create_environment(self.oid, "env-x", "X2", H.MEMBER)


if __name__ == "__main__":
    unittest.main()
