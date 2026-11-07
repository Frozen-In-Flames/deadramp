"""Final GAPS batch singleton tests -- Singleton 54 entries.

Traces to: GAPS.md section "Singleton 54 -- System Administration
L2 (1 fork, new category)" (inventory idx 515-520) and
``../UNION-SPEC.md``'s gap list, which names the six operations
this module closes in records form over the group's own substrate:
managed administration operations, provisioning & deployment,
application delivery & hosting runtime, the virtualization
engine, high-availability network operation, and third-party CSP
hosting platforms. Every test pins the extension surface of
``sysadmin.singleton_extensions.SysadminSingletonExtensions``:
per-entry record shapes and honesty labels, the stub labels on the
three reference implementations, derived-never-stored current
states, the no-score discipline (recursive key scan), access
discipline (denied writes audited with ``:denied``; non-members
reach nothing; failed writes consume no id), and the unit's fresh
negative control on the latest-state derivation seam.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import NotFoundError, PermissionDenied, ValidationError
from sysadmin.singleton_extensions import SysadminSingletonExtensions

ADMIN = H.ADMIN
MEMBER = H.MEMBER
STAFF = H.STAFF
VIEWER = H.VIEWER
OUTSIDER = H.OUTSIDER

FORBIDDEN_KEYS = {
    "score", "rating", "health", "posture", "rank", "grade",
    "geometry", "coordinates", "hostname", "ip_address", "password",
    "credential", "status",
}


def scan_forbidden(node, path="$"):
    """Recursively assert no forbidden key appears in a view."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in FORBIDDEN_KEYS, "forbidden key %r at %s" % (
                key, path)
            scan_forbidden(value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            scan_forbidden(value, "%s[%d]" % (path, index))


class SingletonFixture:
    """Canonical fixture: core store + org + estate + extensions."""

    def make(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        return store, org, system, application, SysadminSingletonExtensions(
            store)


class TestAdminOperations(SingletonFixture, unittest.TestCase):
    """idx 515 -- managed administration operations as records."""

    def test_definition_shape_and_labels(self):
        store, org, system, app, ext = self.make()
        record = ext.create_operation_definition(
            MEMBER, org["id"], "OPS-PATCH", "Monthly patching", "patch")
        self.assertEqual(record["id"], "aod-1")
        self.assertEqual(record["operation_kind"], "patch")
        self.assertFalse(record["executed_here"])
        self.assertEqual(
            set(record),
            {"id", "org_id", "ref", "label", "operation_kind",
             "executed_here", "created_by", "created_utc"})

    def test_definition_kind_validated_and_ref_unique(self):
        store, org, system, app, ext = self.make()
        with self.assertRaises(ValidationError):
            ext.create_operation_definition(
                MEMBER, org["id"], "OPS-X", "Bad kind", "teleport")
        ext.create_operation_definition(
            MEMBER, org["id"], "OPS-PATCH", "Monthly patching", "patch")
        with self.assertRaises(ValidationError):
            ext.create_operation_definition(
                MEMBER, org["id"], "OPS-PATCH", "Duplicate", "harden")

    def test_operation_record_verbatim_and_alters_no_system(self):
        store, org, system, app, ext = self.make()
        definition = ext.create_operation_definition(
            MEMBER, org["id"], "OPS-PATCH", "Monthly patching", "patch")
        before = store.get_system(ADMIN, system["id"])
        record = ext.record_admin_operation(
            MEMBER, org["id"], definition["id"], system["id"],
            "reported_completed")
        self.assertFalse(record["operated_here"])
        self.assertFalse(record["executed_here"])
        self.assertEqual(record["outcome_label"], "reported_completed")
        self.assertEqual(store.get_system(ADMIN, system["id"]), before)

    def test_operation_requires_system_in_org(self):
        store, org, system, app, ext = self.make()
        definition = ext.create_operation_definition(
            MEMBER, org["id"], "OPS-PATCH", "Monthly patching", "patch")
        with self.assertRaises(NotFoundError):
            ext.record_admin_operation(
                MEMBER, org["id"], definition["id"], "sys-999",
                "reported_completed")

    def test_summary_counts_only(self):
        store, org, system, app, ext = self.make()
        definition = ext.create_operation_definition(
            MEMBER, org["id"], "OPS-PATCH", "Monthly patching", "patch")
        ext.record_admin_operation(
            MEMBER, org["id"], definition["id"], system["id"],
            "reported_completed")
        ext.record_admin_operation(
            MEMBER, org["id"], definition["id"], system["id"],
            "reported_completed")
        summary = ext.admin_operations_summary(MEMBER, org["id"])
        self.assertEqual(summary["operation_definitions"], 1)
        self.assertEqual(summary["definitions_by_kind"]["patch"], 1)
        self.assertEqual(summary["admin_operations"], 2)
        self.assertEqual(
            summary["operations_by_outcome"], {"reported_completed": 2})
        scan_forbidden(summary)


class TestProvisioningReference(SingletonFixture, unittest.TestCase):
    """idx 516 -- provisioning & deployment, labeled reference."""

    def test_job_shape_and_stub_labels(self):
        store, org, system, app, ext = self.make()
        job = ext.create_provisioning_job(
            MEMBER, org["id"], "PRV-1", "Stand up app tier", "TARGET-APP-1")
        self.assertEqual(job["id"], "pvj-1")
        self.assertTrue(job["reference_stub"])
        self.assertEqual(job["state"], "recorded_reference_only")
        self.assertFalse(job["provisioned_here"])
        self.assertFalse(job["deployed_here"])
        # The target names no core system: it does not exist yet.
        self.assertNotIn("system_id", job)

    def test_outcome_verbatim_with_reported_count(self):
        store, org, system, app, ext = self.make()
        job = ext.create_provisioning_job(
            MEMBER, org["id"], "PRV-1", "Stand up app tier", "TARGET-APP-1")
        outcome = ext.record_provisioning_outcome(
            MEMBER, org["id"], job["id"], "reported_provisioned",
            reported_count=3)
        self.assertTrue(outcome["reference_stub"])
        self.assertFalse(outcome["provisioned_here"])
        self.assertEqual(outcome["reported_count"], 3)

    def test_reported_count_rejects_floats_and_bools(self):
        store, org, system, app, ext = self.make()
        job = ext.create_provisioning_job(
            MEMBER, org["id"], "PRV-1", "Stand up app tier", "TARGET-APP-1")
        for bad in (1.5, True, -1):
            with self.assertRaises(ValidationError):
                ext.record_provisioning_outcome(
                    MEMBER, org["id"], job["id"], "reported_provisioned",
                    reported_count=bad)


class TestHostingReference(SingletonFixture, unittest.TestCase):
    """idx 517 -- delivery & hosting runtime, labeled reference."""

    def test_profile_shape_and_stub_labels(self):
        store, org, system, app, ext = self.make()
        profile = ext.create_hosting_profile(
            MEMBER, org["id"], "HST-1", "Portal hosting", app["id"])
        self.assertEqual(profile["id"], "dlp-1")
        self.assertTrue(profile["reference_stub"])
        self.assertFalse(profile["hosted_here"])
        self.assertFalse(profile["delivered_here"])
        self.assertEqual(profile["application_id"], app["id"])

    def test_profile_requires_application_in_org(self):
        store, org, system, app, ext = self.make()
        with self.assertRaises(NotFoundError):
            ext.create_hosting_profile(
                MEMBER, org["id"], "HST-1", "Portal hosting", "app-999")

    def test_report_verbatim(self):
        store, org, system, app, ext = self.make()
        profile = ext.create_hosting_profile(
            MEMBER, org["id"], "HST-1", "Portal hosting", app["id"])
        report = ext.record_hosting_report(
            MEMBER, org["id"], profile["id"], "reported_serving")
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["hosted_here"])
        self.assertEqual(
            len(ext.list_hosting_reports(MEMBER, org["id"])), 1)


class TestVirtualization(SingletonFixture, unittest.TestCase):
    """idx 518 -- virtual instances as reported data."""

    def test_instance_shape_and_labels(self):
        store, org, system, app, ext = self.make()
        instance = ext.create_virtual_instance(
            MEMBER, org["id"], "VM-1", "App server", "PLAT-A",
            system_id=system["id"])
        self.assertEqual(instance["id"], "vin-1")
        self.assertFalse(instance["virtualized_here"])
        self.assertEqual(instance["platform_ref"], "PLAT-A")
        # No current state is stored on the record itself.
        self.assertNotIn("current_state", instance)
        self.assertNotIn(
            "current_state", ext._virtual_instances[instance["id"]])

    def test_current_state_derives_latest_label(self):
        store, org, system, app, ext = self.make()
        instance = ext.create_virtual_instance(
            MEMBER, org["id"], "VM-1", "App server", "PLAT-A")
        ext.record_instance_state(
            MEMBER, org["id"], instance["id"], "reported_provisioning")
        ext.record_instance_state(
            MEMBER, org["id"], instance["id"], "reported_running")
        view = ext.get_virtual_instance(MEMBER, instance["id"])
        self.assertEqual(view["current_state"], "reported_running")

    def test_no_state_labels_reads_recorded(self):
        store, org, system, app, ext = self.make()
        instance = ext.create_virtual_instance(
            MEMBER, org["id"], "VM-1", "App server", "PLAT-A")
        view = ext.get_virtual_instance(MEMBER, instance["id"])
        self.assertEqual(view["current_state"], "recorded")

    def test_state_label_validated(self):
        store, org, system, app, ext = self.make()
        instance = ext.create_virtual_instance(
            MEMBER, org["id"], "VM-1", "App server", "PLAT-A")
        with self.assertRaises(ValidationError):
            ext.record_instance_state(
                MEMBER, org["id"], instance["id"], "reported_flying")

    def test_summary_counts_by_derived_state(self):
        store, org, system, app, ext = self.make()
        one = ext.create_virtual_instance(
            MEMBER, org["id"], "VM-1", "App server", "PLAT-A")
        ext.create_virtual_instance(
            MEMBER, org["id"], "VM-2", "Db server", "PLAT-A")
        ext.record_instance_state(
            MEMBER, org["id"], one["id"], "reported_running")
        summary = ext.virtualization_summary(MEMBER, org["id"])
        self.assertEqual(summary["virtual_instances"], 2)
        self.assertEqual(
            summary["instances_by_current_state"],
            {"reported_running": 1, "recorded": 1})
        scan_forbidden(summary)


class TestHighAvailability(SingletonFixture, unittest.TestCase):
    """idx 519 -- HA configurations and reported events."""

    def test_configuration_shape_and_labels(self):
        store, org, system, app, ext = self.make()
        config = ext.create_ha_configuration(
            MEMBER, org["id"], "HA-1", "Portal HA pair", "active-passive",
            system_id=system["id"])
        self.assertEqual(config["id"], "hac-1")
        self.assertFalse(config["operated_here"])
        self.assertFalse(config["failover_performed_here"])
        self.assertNotIn("current_state", config)

    def test_current_state_derives_latest_event(self):
        store, org, system, app, ext = self.make()
        config = ext.create_ha_configuration(
            MEMBER, org["id"], "HA-1", "Portal HA pair", "active-passive")
        ext.record_ha_event(MEMBER, org["id"], config["id"],
                            "reported_healthy")
        ext.record_ha_event(MEMBER, org["id"], config["id"],
                            "reported_failover")
        view = ext.get_ha_configuration(MEMBER, config["id"])
        self.assertEqual(view["current_state"], "reported_failover")

    def test_event_label_validated(self):
        store, org, system, app, ext = self.make()
        config = ext.create_ha_configuration(
            MEMBER, org["id"], "HA-1", "Portal HA pair", "active-passive")
        with self.assertRaises(ValidationError):
            ext.record_ha_event(MEMBER, org["id"], config["id"],
                                "reported_exploded")

    def test_summary_counts(self):
        store, org, system, app, ext = self.make()
        config = ext.create_ha_configuration(
            MEMBER, org["id"], "HA-1", "Portal HA pair", "active-passive")
        ext.record_ha_event(MEMBER, org["id"], config["id"],
                            "reported_healthy")
        ext.record_ha_event(MEMBER, org["id"], config["id"],
                            "reported_degraded")
        summary = ext.ha_summary(MEMBER, org["id"])
        self.assertEqual(summary["ha_configurations"], 1)
        self.assertEqual(
            summary["configurations_by_current_state"],
            {"reported_degraded": 1})
        self.assertEqual(summary["ha_events"], 2)
        scan_forbidden(summary)


class TestPlatformDeclarations(SingletonFixture, unittest.TestCase):
    """idx 520 -- CSP hosting platforms, labeled reference."""

    def test_declaration_shape_and_stub_labels(self):
        store, org, system, app, ext = self.make()
        declaration = ext.create_platform_declaration(
            MEMBER, org["id"], "PLAT-A", "Agency cloud platform")
        self.assertEqual(declaration["id"], "pld-1")
        self.assertTrue(declaration["reference_stub"])
        self.assertEqual(declaration["state"], "recorded_reference_only")
        self.assertFalse(declaration["hosted_here"])
        self.assertFalse(declaration["operated_here"])

    def test_platform_ref_unique_per_org(self):
        store, org, system, app, ext = self.make()
        ext.create_platform_declaration(
            MEMBER, org["id"], "PLAT-A", "Agency cloud platform")
        with self.assertRaises(ValidationError):
            ext.create_platform_declaration(
                MEMBER, org["id"], "PLAT-A", "Duplicate platform")

    def test_report_verbatim(self):
        store, org, system, app, ext = self.make()
        declaration = ext.create_platform_declaration(
            MEMBER, org["id"], "PLAT-A", "Agency cloud platform")
        report = ext.record_platform_report(
            MEMBER, org["id"], declaration["id"], "reported_available")
        self.assertTrue(report["reference_stub"])
        self.assertFalse(report["hosted_here"])
        self.assertEqual(
            len(ext.list_platform_reports(MEMBER, org["id"])), 1)


class TestAccessDiscipline(SingletonFixture, unittest.TestCase):
    """Cross-cutting: RBAC, membership, audit, id discipline."""

    def test_viewer_write_denied_and_audited(self):
        store, org, system, app, ext = self.make()
        with self.assertRaises(PermissionDenied):
            ext.create_operation_definition(
                VIEWER, org["id"], "OPS-PATCH", "Monthly patching", "patch")
        denied = [e for e in store.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertTrue(any(
            e["action"] == "exts_operation_definition_create:denied"
            for e in denied))

    def test_outsider_reaches_nothing(self):
        store, org, system, app, ext = self.make()
        with self.assertRaises(PermissionDenied):
            ext.create_virtual_instance(
                OUTSIDER, org["id"], "VM-1", "App server", "PLAT-A")
        with self.assertRaises(PermissionDenied):
            ext.list_virtual_instances(OUTSIDER, org["id"])

    def test_failed_write_consumes_no_id(self):
        store, org, system, app, ext = self.make()
        with self.assertRaises(ValidationError):
            ext.create_operation_definition(
                MEMBER, org["id"], "OPS-X", "Bad kind", "teleport")
        record = ext.create_operation_definition(
            MEMBER, org["id"], "OPS-PATCH", "Monthly patching", "patch")
        self.assertEqual(record["id"], "aod-1")

    def test_mutations_audited_with_exts_prefix(self):
        store, org, system, app, ext = self.make()
        ext.create_platform_declaration(
            MEMBER, org["id"], "PLAT-A", "Agency cloud platform")
        actions = [e["action"] for e in store.audit.entries()]
        self.assertIn("exts_platform_declaration_create", actions)

    def test_no_score_keys_anywhere(self):
        store, org, system, app, ext = self.make()
        definition = ext.create_operation_definition(
            MEMBER, org["id"], "OPS-PATCH", "Monthly patching", "patch")
        ext.record_admin_operation(
            MEMBER, org["id"], definition["id"], system["id"],
            "reported_completed")
        job = ext.create_provisioning_job(
            MEMBER, org["id"], "PRV-1", "Stand up app tier", "TARGET-APP-1")
        ext.record_provisioning_outcome(
            MEMBER, org["id"], job["id"], "reported_provisioned",
            reported_count=2)
        profile = ext.create_hosting_profile(
            MEMBER, org["id"], "HST-1", "Portal hosting", app["id"])
        instance = ext.create_virtual_instance(
            MEMBER, org["id"], "VM-1", "App server", "PLAT-A")
        ext.record_instance_state(
            MEMBER, org["id"], instance["id"], "reported_running")
        config = ext.create_ha_configuration(
            MEMBER, org["id"], "HA-1", "Portal HA pair", "active-passive")
        ext.record_ha_event(MEMBER, org["id"], config["id"],
                            "reported_healthy")
        declaration = ext.create_platform_declaration(
            MEMBER, org["id"], "PLAT-A", "Agency cloud platform")
        views = [
            ext.list_operation_definitions(MEMBER, org["id"]),
            ext.list_admin_operations(MEMBER, org["id"]),
            ext.admin_operations_summary(MEMBER, org["id"]),
            ext.list_provisioning_jobs(MEMBER, org["id"]),
            ext.list_provisioning_outcomes(MEMBER, org["id"]),
            ext.list_hosting_profiles(MEMBER, org["id"]),
            ext.get_virtual_instance(MEMBER, instance["id"]),
            ext.virtualization_summary(MEMBER, org["id"]),
            ext.get_ha_configuration(MEMBER, config["id"]),
            ext.ha_summary(MEMBER, org["id"]),
            ext.list_platform_declarations(MEMBER, org["id"]),
        ]
        for view in views:
            scan_forbidden(view)


class _EarliestLabelExtensions(SysadminSingletonExtensions):
    """Mutant: current state reads the EARLIEST recorded label."""

    @staticmethod
    def _latest_state_label(state_records):
        if not state_records:
            return "recorded"
        return state_records[0]["state_label"]


class TestSingletonLatestStateNegativeControl(
        SingletonFixture, unittest.TestCase):
    """Fresh negative control: latest recorded label wins.

    The canonical expectation is that a record's current state is
    its LATEST recorded label. The mutant subclass reads the
    earliest label instead and must violate the canonical
    expectation on both derivation surfaces (HA configurations and
    virtual instances).
    """

    def test_canonical_expectation(self):
        store, org, system, app, ext = self.make()
        config = ext.create_ha_configuration(
            MEMBER, org["id"], "HA-1", "Portal HA pair", "active-passive")
        ext.record_ha_event(MEMBER, org["id"], config["id"],
                            "reported_healthy")
        ext.record_ha_event(MEMBER, org["id"], config["id"],
                            "reported_failover")
        self.assertEqual(
            ext.get_ha_configuration(MEMBER, config["id"])["current_state"],
            "reported_failover")

    def test_implementation_matches_canonical_in_summary(self):
        store, org, system, app, ext = self.make()
        instance = ext.create_virtual_instance(
            MEMBER, org["id"], "VM-1", "App server", "PLAT-A")
        ext.record_instance_state(
            MEMBER, org["id"], instance["id"], "reported_provisioning")
        ext.record_instance_state(
            MEMBER, org["id"], instance["id"], "reported_running")
        summary = ext.virtualization_summary(MEMBER, org["id"])
        self.assertEqual(
            summary["instances_by_current_state"], {"reported_running": 1})

    def test_mutant_violates_canonical_expectation(self):
        store, org, system, app, ext = self.make()
        mutant = _EarliestLabelExtensions(store)
        config = mutant.create_ha_configuration(
            MEMBER, org["id"], "HA-1", "Portal HA pair", "active-passive")
        mutant.record_ha_event(MEMBER, org["id"], config["id"],
                               "reported_healthy")
        mutant.record_ha_event(MEMBER, org["id"], config["id"],
                               "reported_failover")
        self.assertEqual(
            mutant.get_ha_configuration(MEMBER, config["id"])[
                "current_state"],
            "reported_healthy")
        with self.assertRaises(AssertionError):
            self.assertEqual(
                mutant.get_ha_configuration(MEMBER, config["id"])[
                    "current_state"],
                "reported_failover")


if __name__ == "__main__":
    unittest.main()
