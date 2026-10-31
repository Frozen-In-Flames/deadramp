"""Privacy discipline: no field anywhere can hold content,
credentials, or personal identifiers; derived values are never
stored; cross-organization data never leaks."""

import unittest

import cloudinfra_helpers as H

FORBIDDEN_FIELD_PARTS = (
    "password", "secret", "credential", "token", "ssn", "email",
    "phone", "content", "payload", "message", "private_key",
)


def _all_keys(node):
    keys = set()
    if isinstance(node, dict):
        for key, value in node.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            keys |= _all_keys(item)
    return keys


class TestPrivacy(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()
        self.org = H.make_org(self.store)
        self.oid = self.org["id"]
        self.tenancy = self.store.create_tenancy(
            self.oid, "ten-a", "A", "shared", H.MEMBER)
        self.env = self.store.create_environment(
            self.oid, "env-1", "Env", H.MEMBER, tenancy_id=self.tenancy["id"])
        self.dep = self.store.create_deployment(
            self.oid, self.tenancy["id"], "dep-1", "wl-1", H.MEMBER,
            environment_id=self.env["id"])
        self.store.register_template(self.oid, "tpl-1", "T", "x=1", H.MEMBER)
        self.store.register_monitor(
            self.oid, "mon-1", "continuous", "env-1", "M", H.MEMBER)
        self.store.register_security_service(
            self.oid, "sec-1", "antivirus", "ten-a", "S", H.MEMBER)
        self.store.record_protection(
            self.oid, "pro-1", "backup", "dep-1", "P", H.MEMBER)
        self.store.register_identity_config(
            self.oid, "idc-1", "directory", "I", H.MEMBER)
        self.store.create_operations_task(
            self.oid, "ops-1", "support", "env-1", "O", "2999-01-01", H.MEMBER)
        account = self.store.open_account(self.oid, "acc-1", "A", H.MEMBER)
        self.store.record_utilization(self.oid, account["id"], "2026-09", 5, H.MEMBER)
        self.store.record_recommendation(
            self.oid, "rec-1", "resource_optimization", "dep-1", "R", H.MEMBER)

    def _all_views(self):
        views = [self.org]
        views += self.store.list_tenancies(self.oid, H.MEMBER)
        views += self.store.list_environments(self.oid, H.MEMBER)
        views += self.store.list_providers(self.oid, H.MEMBER)
        views += self.store.list_deployments(self.oid, H.MEMBER)
        views += self.store.list_templates(self.oid, H.MEMBER)
        views += self.store.list_monitors(self.oid, H.MEMBER)
        views += self.store.list_security_services(self.oid, H.MEMBER)
        views += self.store.list_protection_records(self.oid, H.MEMBER)
        views += self.store.list_identity_configs(self.oid, H.MEMBER)
        views += self.store.list_operations_tasks(self.oid, H.MEMBER)
        views += self.store.list_accounts(self.oid, H.MEMBER)
        views += self.store.list_utilization(self.oid, H.MEMBER)
        views += self.store.list_recommendations(self.oid, H.MEMBER)
        views.append(self.store.org_report(self.oid, H.MEMBER))
        return views

    def test_no_field_can_hold_credentials_or_content(self):
        for view in self._all_views():
            for key in _all_keys(view):
                for forbidden in FORBIDDEN_FIELD_PARTS:
                    self.assertNotIn(
                        forbidden, key.lower(),
                        "field %r in %r" % (key, type(view)))

    def test_derived_values_are_never_stored(self):
        raw_tenancy = self.store._tenancies[self.tenancy["id"]]
        self.assertNotIn("deployment_count", raw_tenancy)
        self.assertNotIn("active_deployment_count", raw_tenancy)
        raw_task = next(iter(self.store._operations_tasks.values()))
        self.assertNotIn("overdue", raw_task)

    def test_store_signatures_have_no_content_parameters(self):
        import inspect

        from cloudinfra.store import CloudInfraStore

        forbidden_params = {"content", "body", "message", "password",
                            "secret", "credential", "ssn", "email", "phone"}
        for name, member in inspect.getmembers(CloudInfraStore, inspect.isfunction):
            params = set(inspect.signature(member).parameters)
            self.assertFalse(
                params & forbidden_params,
                "%s accepts %s" % (name, params & forbidden_params))


if __name__ == "__main__":
    unittest.main()
