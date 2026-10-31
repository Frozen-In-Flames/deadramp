"""Record families: deployment templates (never executed),
monitoring records, platform security service records, backup &
recovery records, identity configuration records
(Core functions 6, 7, 8, 9, 10)."""

import unittest

import cloudinfra_helpers as H
from cloudinfra.errors import NotFoundError, ValidationError
from cloudinfra.store import CloudInfraStore


class _OrgCase(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()
        self.org = H.make_org(self.store)
        self.oid = self.org["id"]


class TestTemplates(_OrgCase):
    def test_register_template_stores_settings_verbatim(self):
        settings = "image=base\nreplicas=2\n# a comment"
        tpl = self.store.register_template(
            self.oid, "tpl-hw", "Hot-warm", settings, H.MEMBER)
        self.assertEqual(tpl["settings_text"], settings)
        self.assertEqual(
            self.store.get_template(self.oid, tpl["id"], H.MEMBER)["settings_text"],
            settings)

    def test_template_registry_never_executes(self):
        # The registry records; it does not run. No store operation
        # may execute, apply, launch, or provision anything.
        names = [n for n in dir(CloudInfraStore) if not n.startswith("_")]
        for forbidden in ("execute", "apply", "launch", "provision",
                          "deploy_workload", "run"):
            for name in names:
                self.assertNotIn(forbidden, name)

    def test_duplicate_template_ref_rejected(self):
        self.store.register_template(self.oid, "tpl-a", "A", "x=1", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_template(self.oid, "tpl-a", "A2", "x=2", H.MEMBER)

    def test_template_settings_required(self):
        with self.assertRaises(ValidationError):
            self.store.register_template(self.oid, "tpl-a", "A", "", H.MEMBER)


class TestMonitors(_OrgCase):
    def test_register_monitor_each_kind(self):
        for kind in ("continuous", "network", "log_ingestion", "observability"):
            mon = self.store.register_monitor(
                self.oid, "mon-%s" % kind, kind, "env-1", kind, H.MEMBER)
            self.assertEqual(mon["kind"], kind)

    def test_monitor_invalid_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.register_monitor(
                self.oid, "mon-x", "tracing", "env-1", "X", H.MEMBER)

    def test_monitor_duplicate_ref_rejected(self):
        self.store.register_monitor(
            self.oid, "mon-a", "continuous", "env-1", "A", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_monitor(
                self.oid, "mon-a", "network", "env-1", "A2", H.MEMBER)


class TestSecurityServices(_OrgCase):
    def test_register_each_security_kind(self):
        kinds = ("intrusion_prevention", "intrusion_detection",
                 "web_application_firewall", "endpoint_protection",
                 "endpoint_detection_response", "antivirus",
                 "file_integrity_monitoring")
        for kind in kinds:
            svc = self.store.register_security_service(
                self.oid, "sec-%s" % kind, kind, "ten-1", kind, H.MEMBER)
            self.assertEqual(svc["kind"], kind)

    def test_security_invalid_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.register_security_service(
                self.oid, "sec-x", "dlp", "ten-1", "X", H.MEMBER)


class TestProtectionRecords(_OrgCase):
    def test_record_each_protection_kind(self):
        for kind in ("backup", "restore", "disaster_recovery"):
            rec = self.store.record_protection(
                self.oid, "pro-%s" % kind, kind, "dep-1", kind, H.MEMBER,
                occurred_at="2026-10-01")
            self.assertEqual(rec["kind"], kind)
            self.assertEqual(rec["occurred_at"], "2026-10-01")

    def test_protection_occurred_at_validated(self):
        with self.assertRaises(ValidationError):
            self.store.record_protection(
                self.oid, "pro-x", "backup", "dep-1", "X", H.MEMBER,
                occurred_at="not-a-date")

    def test_protection_invalid_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.record_protection(
                self.oid, "pro-x", "snapshot", "dep-1", "X", H.MEMBER)


class TestIdentityConfigs(_OrgCase):
    EXPECTED_KEYS = {
        "id", "org_id", "identity_ref", "kind", "label", "provider_ref",
        "created_by", "created_utc",
    }

    def test_register_each_identity_kind(self):
        for kind in ("single_sign_on", "iam_policy", "directory",
                     "authentication"):
            cfg = self.store.register_identity_config(
                self.oid, "idc-%s" % kind, kind, kind, H.MEMBER)
            self.assertEqual(cfg["kind"], kind)

    def test_identity_config_shape_has_no_credential_field(self):
        cfg = self.store.register_identity_config(
            self.oid, "idc-sso", "single_sign_on", "SSO via directory",
            H.MEMBER, provider_ref="dir-main")
        self.assertEqual(set(cfg.keys()), self.EXPECTED_KEYS)
        self.assertEqual(cfg["provider_ref"], "dir-main")

    def test_identity_invalid_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.register_identity_config(
                self.oid, "idc-x", "password_vault", "X", H.MEMBER)

    def test_cross_org_record_not_found(self):
        cfg = self.store.register_identity_config(
            self.oid, "idc-a", "directory", "A", H.MEMBER)
        other = self.store.create_organization("org-other", "Other", H.ADMIN)
        with self.assertRaises(NotFoundError):
            self.store.get_identity_config(other["id"], cfg["id"], H.ADMIN)


if __name__ == "__main__":
    unittest.main()
