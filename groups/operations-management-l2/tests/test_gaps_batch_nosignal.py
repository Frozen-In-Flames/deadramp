"""Final GAPS batch tests — No-Signal Addition, Operations Mgmt L2.

Pins the extension surface in ``src/opsmgmt/extensions_nosignal.py``
(``OpsNoSignal``, wrapping the core ``OpsStore``): one test class
per open GAPS.md entry for the "No-Signal Addition — Operations
Management L2 (SMX Elevate IAP, F1603077867)" section (see
``../BATCH-NOSIGNAL.md`` for the per-entry disposition), plus
cross-cutting pins -- ``extn_``-prefixed actions and ``:denied``
denials on the core audit log, stub labels on every reference
record, derived-never-stored values (guardrail view, summaries),
opaque-reference-only record shapes, and the unit's fresh
negative control: the checker-not-definer guard
``_check_checker_not_definer``.

Fixtures: ``make_store()`` (a person, an organization, and a
project with the person as member) from ``opsmgmt_helpers``;
ADMIN=alice/admin, OPERATOR=bob/operator, VIEWER=carol/viewer.
"""

import unittest

import opsmgmt.extensions_nosignal as nosignal_module
from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER, make_store

from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from opsmgmt.extensions_nosignal import OpsNoSignal


class NsFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.person, self.org, self.project = make_store()
        self.ns = OpsNoSignal(self.store)
        self.pid = self.person["id"]
        self.proj = self.project["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]

    def make_platform(self):
        return self.ns.register_cloud_platform_reference(
            "platform-ref-1", OPERATOR,
            cloud_labels=["cloud-a", "cloud-b"],
            automation_modes=["infrastructure_as_code",
                              "operations_as_code",
                              "infrastructure_as_code"])

    def make_guardrail(self):
        pack = self.ns.register_baseline_pack(
            "fedramp", ADMIN, name="FedRAMP pack",
            control_refs=["AC-2", "AU-2"])
        return pack, self.ns.create_guardrail(
            "Tenant Isolation", "tenants stay isolated", ADMIN,
            baseline_pack_id=pack["id"], scope_kind="multi_tenant",
            project_id=self.proj)


class TestCloudPlatformReferences(NsFixture):
    """Entry (idx 969): Cloud platform operations & lifecycle
    management engine -- stub-engine, shipped as a labeled
    reference implementation: platform references plus lifecycle
    operation references; automation modes are data and nothing
    is provisioned, operated, monitored, secured, or
    lifecycle-managed here."""

    def test_platform_shape_and_labels(self):
        platform = self.make_platform()
        self.assertEqual(platform["id"], "cpr-1")
        self.assertIs(platform["reference_stub"], True)
        self.assertIs(platform["provisioned_here"], False)
        self.assertIs(platform["operated_here"], False)
        self.assertIs(platform["monitored_here"], False)
        self.assertIs(platform["secured_here"], False)
        self.assertIs(platform["lifecycle_managed_here"], False)
        self.assertEqual(platform["cloud_labels"], ["cloud-a", "cloud-b"])
        # Automation modes are held as data, de-duplicated; no
        # mode is executed by registering the reference.
        self.assertEqual(platform["automation_modes"],
                         ["infrastructure_as_code", "operations_as_code"])
        # Returned records are copies; mutating one changes nothing.
        platform["cloud_labels"].append("bogus")
        stored = self.ns.list_cloud_platform_references(ADMIN)
        self.assertEqual(stored[0]["cloud_labels"], ["cloud-a", "cloud-b"])

    def test_operation_reference_recorded_not_performed(self):
        platform = self.make_platform()
        operation = self.ns.record_lifecycle_operation_reference(
            platform["id"], "provisioning", "reported_completed",
            OPERATOR, counts={"platforms": 3})
        self.assertEqual(operation["id"], "clo-1")
        self.assertIs(operation["reference_stub"], True)
        self.assertIs(operation["performed_here"], False)
        self.assertIs(operation["executed_here"], False)
        # Counts are stored exactly as reported, never recomputed.
        self.assertEqual(operation["counts"], {"platforms": 3})

    def test_summary_derives_counts_only(self):
        platform = self.make_platform()
        self.ns.record_lifecycle_operation_reference(
            platform["id"], "provisioning", "reported_completed", OPERATOR)
        self.ns.record_lifecycle_operation_reference(
            platform["id"], "monitoring", "reported_in_progress", OPERATOR)
        self.ns.record_lifecycle_operation_reference(
            platform["id"], "monitoring", "reported_failed", OPERATOR)
        summary = self.ns.cloud_platform_summary(ADMIN)
        self.assertEqual(summary["platforms"], 1)
        self.assertEqual(summary["operations"], 3)
        self.assertEqual(summary["operations_by_kind"],
                         {"provisioning": 1, "monitoring": 2})
        self.assertEqual(summary["operations_by_status"],
                         {"reported_completed": 1,
                          "reported_in_progress": 1,
                          "reported_failed": 1})
        self.assertIs(summary["reference_stub"], True)
        self.assertIs(summary["operated_here"], False)

    def test_unknown_platform_rejected_no_id_consumed(self):
        with self.assertRaises(NotFoundError):
            self.ns.record_lifecycle_operation_reference(
                "cpr-99", "lifecycle", "reported_completed", OPERATOR)
        platform = self.make_platform()
        operation = self.ns.record_lifecycle_operation_reference(
            platform["id"], "lifecycle", "reported_completed", OPERATOR)
        self.assertEqual(operation["id"], "clo-1")

    def test_address_shaped_ref_rejected(self):
        for bad in ("https://platform.example", "10.0.0.9",
                    "platform.example.internal", "has space"):
            with self.assertRaises(ValidationError):
                self.ns.register_cloud_platform_reference(bad, OPERATOR)
        self.assertEqual(self.ns.list_cloud_platform_references(ADMIN), [])

    def test_bad_automation_mode_rejected(self):
        with self.assertRaises(ValidationError):
            self.ns.register_cloud_platform_reference(
                "platform-ref-1", OPERATOR,
                automation_modes=["terraform_magic"])

    def test_viewer_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ns.register_cloud_platform_reference(
                "platform-ref-1", VIEWER)
        self.assertIn("extn_cloud_platform_register:denied",
                      self.audit_actions())
        self.assertEqual(self.ns.list_cloud_platform_references(ADMIN), [])

    def test_successful_actions_audited_with_extn_prefix(self):
        platform = self.make_platform()
        self.ns.record_lifecycle_operation_reference(
            platform["id"], "security", "reported_completed", OPERATOR)
        actions = self.audit_actions()
        self.assertIn("extn_cloud_platform_register", actions)
        self.assertIn("extn_lifecycle_operation", actions)


class TestBaselinePacks(NsFixture):
    """Entry (idx 970), pack surface: baseline packs naming the
    baselines the fork names in its own words, control references
    held as data; nothing is automated or enforced here."""

    def test_pack_shape_and_labels(self):
        pack = self.ns.register_baseline_pack(
            "cmmc", ADMIN, name="CMMC pack", control_refs=["3.1.1"])
        self.assertEqual(pack["id"], "bpk-1")
        self.assertEqual(pack["baseline_label"], "cmmc")
        self.assertEqual(pack["control_refs"], ["3.1.1"])
        self.assertIs(pack["automated_here"], False)
        self.assertIs(pack["enforced_here"], False)

    def test_all_named_baselines_accepted(self):
        for label in ("cmmc", "hipaa", "hitech", "cjis", "pci",
                      "soc_1", "soc_2", "fedramp", "dod_il"):
            pack = self.ns.register_baseline_pack(label, ADMIN)
            self.assertEqual(pack["baseline_label"], label)
        self.assertEqual(len(self.ns.list_baseline_packs(ADMIN)), 9)

    def test_unnamed_baseline_rejected_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ns.register_baseline_pack("iso_27001", ADMIN)
        pack = self.ns.register_baseline_pack("pci", ADMIN)
        self.assertEqual(pack["id"], "bpk-1")

    def test_operator_denied_and_audited(self):
        # Baseline packs are configuration: workflow_write is
        # admin-only, exactly as the core workflow registry.
        with self.assertRaises(PermissionDenied):
            self.ns.register_baseline_pack("hipaa", OPERATOR)
        self.assertIn("extn_baseline_pack_register:denied",
                      self.audit_actions())


class TestGuardrails(NsFixture):
    """Entry (idx 970): Built-in compliance automation & policy
    guardrails engine -- built as baseline packs, guardrail
    definitions (rule text verbatim, never evaluated), and
    guardrail check records (outcomes exactly as reported by an
    external automation); nothing automates or enforces here."""

    def test_definition_shape_and_labels(self):
        pack, guardrail = self.make_guardrail()
        self.assertEqual(guardrail["id"], "grl-1")
        self.assertEqual(guardrail["rule_text"], "tenants stay isolated")
        self.assertEqual(guardrail["baseline_pack_id"], pack["id"])
        self.assertEqual(guardrail["scope_kind"], "multi_tenant")
        self.assertIs(guardrail["automated_here"], False)
        self.assertIs(guardrail["enforced_here"], False)
        # The stored definition carries no derived state.
        self.assertNotIn("check_count", guardrail)
        self.assertNotIn("latest_outcome", guardrail)

    def test_unknown_pack_and_project_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ns.create_guardrail("G", "rule", ADMIN,
                                     baseline_pack_id="bpk-99")
        with self.assertRaises(NotFoundError):
            self.ns.create_guardrail("G", "rule", ADMIN,
                                     project_id="proj-99")

    def test_check_recorded_verbatim_and_labeled(self):
        pack, guardrail = self.make_guardrail()
        check = self.ns.record_guardrail_check(
            guardrail["id"], OPERATOR, "noncompliant_reported",
            note="reported by external automation")
        self.assertEqual(check["id"], "gck-1")
        self.assertEqual(check["outcome"], "noncompliant_reported")
        self.assertIs(check["automated_here"], False)
        self.assertIs(check["evaluated_here"], False)
        self.assertIs(check["enforced_here"], False)

    def test_view_derives_check_state_at_read(self):
        pack, guardrail = self.make_guardrail()
        self.ns.record_guardrail_check(
            guardrail["id"], OPERATOR, "compliant_reported")
        self.ns.record_guardrail_check(
            guardrail["id"], OPERATOR, "noncompliant_reported")
        view = self.ns.guardrail_view(guardrail["id"], ADMIN)
        self.assertEqual(view["check_count"], 2)
        self.assertEqual(view["checks_by_outcome"],
                         {"compliant_reported": 1,
                          "noncompliant_reported": 1})
        # The latest outcome is the LAST reported check's, derived.
        self.assertEqual(view["latest_outcome"], "noncompliant_reported")
        # ... and still never stored on the definition.
        stored = self.ns.get_guardrail(guardrail["id"], ADMIN)
        self.assertNotIn("check_count", stored)
        self.assertNotIn("latest_outcome", stored)

    def test_summary_counts_only_no_score_keys(self):
        pack, guardrail = self.make_guardrail()
        self.ns.create_guardrail(
            "Domain Boundary", "domains stay separate", ADMIN,
            scope_kind="cross_domain")
        self.ns.record_guardrail_check(
            guardrail["id"], OPERATOR, "compliant_reported")
        summary = self.ns.compliance_summary(ADMIN)
        self.assertEqual(summary["baseline_packs"], 1)
        self.assertEqual(summary["baseline_packs_by_label"],
                         {"fedramp": 1})
        self.assertEqual(summary["guardrails"], 2)
        self.assertEqual(summary["guardrails_by_scope"],
                         {"multi_tenant": 1, "cross_domain": 1})
        self.assertEqual(summary["checks"], 1)
        self.assertEqual(summary["checks_by_outcome"],
                         {"compliant_reported": 1})
        for forbidden in ("score", "rate", "grade", "percent"):
            self.assertNotIn(forbidden, summary)

    def test_invalid_outcome_rejected_no_id_consumed(self):
        pack, guardrail = self.make_guardrail()
        with self.assertRaises(ValidationError):
            self.ns.record_guardrail_check(
                guardrail["id"], OPERATOR, "mostly_fine")
        check = self.ns.record_guardrail_check(
            guardrail["id"], OPERATOR, "inconclusive")
        self.assertEqual(check["id"], "gck-1")

    def test_definer_may_not_check_canonical(self):
        pack, guardrail = self.make_guardrail()
        with self.assertRaises(ValidationError):
            self.ns.record_guardrail_check(
                guardrail["id"], ADMIN, "compliant_reported")
        self.assertEqual(
            self.ns.list_guardrail_checks(ADMIN,
                                          guardrail_id=guardrail["id"]),
            [])

    def test_operator_denied_definition_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ns.create_guardrail("Nope", "rule", OPERATOR)
        self.assertIn("extn_guardrail_create:denied", self.audit_actions())


class TestCheckerNotDefinerNegativeControl(NsFixture):
    """Fresh negative control for this unit: the actor who
    records a guardrail check may never be the guardrail's
    definer (the ``_check_checker_not_definer`` seam in
    ``opsmgmt/extensions_nosignal.py``).

    Three legs, the house form: (1) the canonical expectation
    from the real implementation, (2) the mutant (the seam
    patched to a no-op in-process) would NOT produce it -- the
    definer's own check succeeds, and (3) treating the mutant's
    outcome as the expected outcome fails.
    """

    def test_checker_guard_canonical_but_mutant_not(self):
        pack, guardrail = self.make_guardrail()

        # (1) Canonical: the definer's check is refused and no
        # check is recorded.
        with self.assertRaises(ValidationError):
            self.ns.record_guardrail_check(
                guardrail["id"], ADMIN, "compliant_reported")
        canonical = self.ns.list_guardrail_checks(
            ADMIN, guardrail_id=guardrail["id"])
        self.assertEqual(len(canonical), 0)

        # (2) Mutant: with the guard seam disabled, the same
        # check succeeds -- the mutant would NOT produce the
        # canonical outcome.
        original = nosignal_module._check_checker_not_definer
        nosignal_module._check_checker_not_definer = (
            lambda defined_by, checker: None)
        try:
            mutant_check = self.ns.record_guardrail_check(
                guardrail["id"], ADMIN, "compliant_reported")
        finally:
            nosignal_module._check_checker_not_definer = original
        self.assertEqual(mutant_check["outcome"], "compliant_reported")
        mutant = self.ns.list_guardrail_checks(
            ADMIN, guardrail_id=guardrail["id"])
        self.assertEqual(len(mutant), 1)

        # (3) Treating the mutant's outcome as the expectation
        # fails.
        with self.assertRaises(AssertionError):
            self.assertEqual(len(mutant), len(canonical))


if __name__ == "__main__":
    unittest.main()
