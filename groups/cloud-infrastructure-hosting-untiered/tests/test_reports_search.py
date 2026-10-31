"""Reporting and search: counts and unit sums computed on read,
no scores and no money anywhere, membership-scoped search
(Core functions 14, 15)."""

import unittest

import cloudinfra_helpers as H

FORBIDDEN_KEYS = ("score", "cents", "amount", "price", "fee", "rating")


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


class TestReportAndSearch(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()
        self.org = H.make_org(self.store)
        self.oid = self.org["id"]
        provider = self.store.register_provider(
            self.oid, "prv-aws", "AWS US East/West", H.MEMBER)
        tenancy = self.store.create_tenancy(
            self.oid, "ten-a", "Boundary tenancy", "boundary_protected",
            H.MEMBER, provider_id=provider["id"])
        self.store.create_tenancy(self.oid, "ten-b", "Managed", "managed", H.MEMBER)
        env = self.store.create_environment(
            self.oid, "env-1", "Prod", H.MEMBER, tenancy_id=tenancy["id"])
        self.store.set_environment_status(self.oid, env["id"], "active", H.MEMBER)
        dep = self.store.create_deployment(
            self.oid, tenancy["id"], "dep-1", "wl-1", H.MEMBER)
        self.store.activate_deployment(self.oid, dep["id"], H.MEMBER)
        self.store.register_template(self.oid, "tpl-1", "Tpl", "x=1", H.MEMBER)
        self.store.register_monitor(
            self.oid, "mon-1", "continuous", "env-1", "CM", H.MEMBER)
        self.store.register_security_service(
            self.oid, "sec-1", "intrusion_prevention", "ten-a", "IPS", H.MEMBER)
        self.store.record_protection(
            self.oid, "pro-1", "backup", "dep-1", "Nightly", H.MEMBER)
        self.store.register_identity_config(
            self.oid, "idc-1", "single_sign_on", "SSO", H.MEMBER)
        self.store.create_operations_task(
            self.oid, "ops-1", "patching", "env-1", "Patch", "2026-01-15",
            H.MEMBER)
        account = self.store.open_account(self.oid, "acc-1", "Acct", H.MEMBER)
        self.store.record_utilization(self.oid, account["id"], "2026-09", 100, H.MEMBER)
        self.store.record_utilization(self.oid, account["id"], "2026-10", 250, H.MEMBER)
        self.store.record_recommendation(
            self.oid, "rec-1", "ai_recommendation", "dep-1", "Rec", H.MEMBER)

    def test_report_counts(self):
        report = self.store.org_report(self.oid, H.MEMBER, at="2026-01-10")
        self.assertEqual(report["tenancies"]["total"], 2)
        self.assertEqual(
            report["tenancies"]["by_hosting_model"],
            {"boundary_protected": 1, "managed": 1})
        self.assertEqual(report["environments"]["by_status"], {"active": 1})
        self.assertEqual(report["providers"]["total"], 1)
        self.assertEqual(report["deployments"]["by_status"], {"active": 1})
        self.assertEqual(report["templates"]["total"], 1)
        self.assertEqual(report["monitors"]["by_kind"], {"continuous": 1})
        self.assertEqual(
            report["security_services"]["by_kind"], {"intrusion_prevention": 1})
        self.assertEqual(report["protection_records"]["by_kind"], {"backup": 1})
        self.assertEqual(
            report["identity_configs"]["by_kind"], {"single_sign_on": 1})
        self.assertEqual(report["operations_tasks"]["total"], 1)
        self.assertEqual(report["operations_tasks"]["overdue"], 0)
        self.assertEqual(report["accounts"]["by_status"], {"open": 1})
        self.assertEqual(report["recommendations"]["by_kind"],
                         {"ai_recommendation": 1})

    def test_report_units_by_period(self):
        report = self.store.org_report(self.oid, H.MEMBER)
        self.assertEqual(report["utilization"]["records"], 2)
        self.assertEqual(
            report["utilization"]["units_by_period"],
            {"2026-09": 100, "2026-10": 250})

    def test_report_overdue_derived_with_at(self):
        report = self.store.org_report(self.oid, H.MEMBER, at="2026-02-01")
        self.assertEqual(report["operations_tasks"]["overdue"], 1)

    def test_report_has_no_score_or_money_keys(self):
        report = self.store.org_report(self.oid, H.MEMBER)
        for key in _all_keys(report):
            for forbidden in FORBIDDEN_KEYS:
                self.assertNotIn(forbidden, key.lower())

    def test_viewer_may_read_report(self):
        report = self.store.org_report(self.oid, H.VIEWER)
        self.assertEqual(report["org_ref"], H.ORG_REF)

    def test_search_finds_across_families(self):
        results = self.store.search(self.oid, "ten-a", H.MEMBER)
        self.assertEqual(len(results["tenancies"]), 1)
        self.assertEqual(len(results["security_services"]), 1)
        results = self.store.search(self.oid, "sso", H.MEMBER)
        self.assertEqual(len(results["identity_configs"]), 1)
        results = self.store.search(self.oid, "wl-1", H.MEMBER)
        self.assertEqual(len(results["deployments"]), 1)

    def test_search_is_membership_scoped(self):
        other = self.store.create_organization("org-other", "Other", H.ADMIN)
        self.store.create_tenancy(other["id"], "ten-secret", "Secret",
                                  "shared", H.ADMIN)
        results = self.store.search(self.oid, "secret", H.MEMBER)
        self.assertEqual(results["tenancies"], [])

    def test_search_no_match(self):
        results = self.store.search(self.oid, "zzz-nothing", H.MEMBER)
        self.assertTrue(all(not v for v in results.values()))


if __name__ == "__main__":
    unittest.main()
