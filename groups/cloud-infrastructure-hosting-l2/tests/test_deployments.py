"""Deployments: link validation, guarded lifecycle, and the
functional side of the deployment slot rule (Core function 5).
The load-bearing proof for the slot rule lives in
test_negative_control.py."""

import unittest

import cloudinfra_helpers as H
from cloudinfra.errors import NotFoundError, ValidationError


class TestDeployments(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()
        self.org = H.make_org(self.store)
        self.oid = self.org["id"]
        self.tenancy = self.store.create_tenancy(
            self.oid, "ten-a", "A", "shared", H.MEMBER)
        self.tenancy2 = self.store.create_tenancy(
            self.oid, "ten-b", "B", "managed", H.MEMBER)

    def _deployment(self, ref, workload, tenancy=None, **kw):
        return self.store.create_deployment(
            self.oid, (tenancy or self.tenancy)["id"], ref, workload,
            H.MEMBER, **kw)

    def test_create_deployment_defaults_recorded(self):
        dep = self._deployment("dep-1", "wl-1")
        self.assertEqual(dep["status"], "recorded")
        self.assertIsNone(dep["environment_id"])
        self.assertIsNone(dep["template_id"])
        self.assertIsNone(dep["encryption_label"])

    def test_deployment_links_validated(self):
        env = self.store.create_environment(
            self.oid, "env-1", "Env", H.MEMBER,
            tenancy_id=self.tenancy["id"])
        tpl = self.store.register_template(
            self.oid, "tpl-1", "Template", "size=large", H.MEMBER)
        dep = self._deployment(
            "dep-1", "wl-1", environment_id=env["id"],
            template_id=tpl["id"], encryption_label="encryption at rest")
        self.assertEqual(dep["environment_id"], env["id"])
        self.assertEqual(dep["template_id"], tpl["id"])
        self.assertEqual(dep["encryption_label"], "encryption at rest")
        with self.assertRaises(NotFoundError):
            self._deployment("dep-2", "wl-2", environment_id="env-99")
        with self.assertRaises(NotFoundError):
            self._deployment("dep-2", "wl-2", template_id="tpl-99")
        with self.assertRaises(NotFoundError):
            self.store.create_deployment(
                self.oid, "ten-99", "dep-2", "wl-2", H.MEMBER)

    def test_duplicate_deployment_ref_rejected(self):
        self._deployment("dep-1", "wl-1")
        with self.assertRaises(ValidationError):
            self._deployment("dep-1", "wl-2")

    def test_activate_and_stop_happy_path(self):
        dep = self._deployment("dep-1", "wl-1")
        dep = self.store.activate_deployment(self.oid, dep["id"], H.MEMBER)
        self.assertEqual(dep["status"], "active")
        dep = self.store.stop_deployment(self.oid, dep["id"], H.MEMBER)
        self.assertEqual(dep["status"], "stopped")

    def test_stop_from_recorded_rejected(self):
        dep = self._deployment("dep-1", "wl-1")
        with self.assertRaises(ValidationError):
            self.store.stop_deployment(self.oid, dep["id"], H.MEMBER)

    def test_activate_from_stopped_rejected(self):
        dep = self._deployment("dep-1", "wl-1")
        self.store.activate_deployment(self.oid, dep["id"], H.MEMBER)
        self.store.stop_deployment(self.oid, dep["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.activate_deployment(self.oid, dep["id"], H.MEMBER)

    def test_slot_rule_blocks_second_active_same_workload(self):
        first = self._deployment("dep-1", "wl-1")
        second = self._deployment("dep-2", "wl-1")
        self.store.activate_deployment(self.oid, first["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.activate_deployment(self.oid, second["id"], H.MEMBER)
        # The refused activation changed nothing.
        self.assertEqual(
            self.store.get_deployment(self.oid, second["id"], H.MEMBER)["status"],
            "recorded")

    def test_slot_rule_is_per_tenancy(self):
        first = self._deployment("dep-1", "wl-1")
        second = self._deployment("dep-2", "wl-1", tenancy=self.tenancy2)
        self.store.activate_deployment(self.oid, first["id"], H.MEMBER)
        activated = self.store.activate_deployment(
            self.oid, second["id"], H.MEMBER)
        self.assertEqual(activated["status"], "active")

    def test_slot_rule_is_per_workload(self):
        first = self._deployment("dep-1", "wl-1")
        second = self._deployment("dep-2", "wl-2")
        self.store.activate_deployment(self.oid, first["id"], H.MEMBER)
        activated = self.store.activate_deployment(
            self.oid, second["id"], H.MEMBER)
        self.assertEqual(activated["status"], "active")

    def test_slot_frees_after_stop(self):
        first = self._deployment("dep-1", "wl-1")
        second = self._deployment("dep-2", "wl-1")
        self.store.activate_deployment(self.oid, first["id"], H.MEMBER)
        self.store.stop_deployment(self.oid, first["id"], H.MEMBER)
        activated = self.store.activate_deployment(
            self.oid, second["id"], H.MEMBER)
        self.assertEqual(activated["status"], "active")

    def test_list_deployments_filter_by_tenancy(self):
        self._deployment("dep-1", "wl-1")
        self._deployment("dep-2", "wl-2", tenancy=self.tenancy2)
        self.assertEqual(len(self.store.list_deployments(self.oid, H.MEMBER)), 2)
        only = self.store.list_deployments(
            self.oid, H.MEMBER, tenancy_id=self.tenancy2["id"])
        self.assertEqual([d["deployment_ref"] for d in only], ["dep-2"])


if __name__ == "__main__":
    unittest.main()
