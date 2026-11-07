"""Final GAPS batch: the extension surface for Remainder Group 4's
14 open gap entries (6 built, 8 labeled reference implementations).

Traces to: gaps-batch/DECISION.md (build pattern) and the group's
BATCH.md (per-entry dispositions). Pins, per entry, the records
form and its honesty labels; cross-cutting, the batch disciplines:
no money shape anywhere (recursive key scan), derived values never
stored, RBAC through the core action set with denied attempts
audited, and the fresh mutation-verified negative control — the
verification separation-of-duties seam
``_check_verification_decider_not_opener``.
"""

import inspect
import unittest

import cloudinfra_helpers as H
from cloudinfra.errors import NotFoundError, PermissionDenied, ValidationError
from cloudinfra.extensions import (
    REFERENCE_KINDS,
    CloudInfraExtensions,
)

MONEY_FIELD_PARTS = (
    "amount", "price", "fee", "cents", "cost", "currency", "money",
    "rate", "charge",
)
FORBIDDEN_PARAM_PARTS = (
    "password", "secret", "credential", "token", "content", "payload",
    "material",
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


class _ExtCase(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()
        self.org = H.make_org(self.store)
        self.oid = self.org["id"]
        self.ext = CloudInfraExtensions(self.store)
        self.tenancy = self.store.create_tenancy(
            self.oid, "ten-a", "A", "shared", H.MEMBER)
        self.env = self.store.create_environment(
            self.oid, "env-1", "Env", H.MEMBER, tenancy_id=self.tenancy["id"])
        self.template = self.store.register_template(
            self.oid, "tpl-1", "T", "x=1\ny=2", H.MEMBER)
        self.dep = self.store.create_deployment(
            self.oid, self.tenancy["id"], "dep-1", "wl-1", H.MEMBER,
            environment_id=self.env["id"], template_id=self.template["id"])
        self.sec = self.store.register_security_service(
            self.oid, "sec-1", "antivirus", "ten-a", "S", H.MEMBER)
        self.monitor = self.store.register_monitor(
            self.oid, "mon-1", "continuous", "env-1", "M", H.MEMBER)
        self.protection = self.store.record_protection(
            self.oid, "pro-1", "backup", "dep-1", "P", H.MEMBER)
        self.task = self.store.create_operations_task(
            self.oid, "ops-1", "patching", "env-1", "O", "2999-01-01",
            H.MEMBER)
        self.account = self.store.open_account(
            self.oid, "acc-1", "A", H.MEMBER)


class TestDeploymentIntents(_ExtCase):
    """Entry: template execution engine — intents referencing the
    verbatim-settings registry; nothing executes."""

    def test_intent_references_template_and_derives_settings(self):
        intent = self.ext.record_deployment_intent(
            self.oid, "int-1", self.template["id"], self.tenancy["id"],
            "wl-1", H.MEMBER, environment_id=self.env["id"],
            deployment_id=self.dep["id"])
        self.assertEqual(intent["status"], "recorded")
        self.assertIs(intent["executed"], False)
        # Derived at read, never stored on the intent record.
        self.assertNotIn("settings_text", intent)
        self.assertNotIn("template_ref", intent)
        view = self.ext.get_deployment_intent(self.oid, intent["id"], H.MEMBER)
        self.assertEqual(view["settings_text"], "x=1\ny=2")
        self.assertEqual(view["template_ref"], "tpl-1")

    def test_intent_links_validated_and_ref_unique(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_deployment_intent(
                self.oid, "int-x", "tpl-999", self.tenancy["id"], "wl-1",
                H.MEMBER)
        self.ext.record_deployment_intent(
            self.oid, "int-1", self.template["id"], self.tenancy["id"],
            "wl-1", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_deployment_intent(
                self.oid, "int-1", self.template["id"], self.tenancy["id"],
                "wl-2", H.MEMBER)

    def test_intent_cancel_lifecycle(self):
        intent = self.ext.record_deployment_intent(
            self.oid, "int-1", self.template["id"], self.tenancy["id"],
            "wl-1", H.MEMBER)
        cancelled = self.ext.cancel_deployment_intent(
            self.oid, intent["id"], H.MEMBER)
        self.assertEqual(cancelled["status"], "cancelled")
        with self.assertRaises(ValidationError):
            self.ext.cancel_deployment_intent(self.oid, intent["id"], H.MEMBER)

    def test_no_execution_surface(self):
        # The registry records; it does not run. Mirrors the core's
        # template pin, applied to the extension class.
        names = [n for n in dir(CloudInfraExtensions)
                 if not n.startswith("_")]
        for forbidden in ("execute", "apply", "launch", "run"):
            for name in names:
                self.assertNotIn(forbidden, name)


class TestSecurityServiceEngines(_ExtCase):
    """Entry: platform security service engines — configuration
    records plus reported check results."""

    def test_config_settings_verbatim(self):
        config = self.ext.record_security_service_config(
            self.oid, "scc-1", self.sec["id"], "mode=strict\nlevel=3",
            H.MEMBER, label="AV config")
        self.assertEqual(config["settings_text"], "mode=strict\nlevel=3")
        self.assertEqual(config["state"], "recorded")
        with self.assertRaises(ValidationError):
            self.ext.record_security_service_config(
                self.oid, "scc-1", self.sec["id"], "mode=loose", H.MEMBER)

    def test_check_results_are_reported_outcomes(self):
        self.ext.record_security_check_result(
            self.oid, "scr-1", self.sec["id"], "reported_pass", H.MEMBER,
            checked_at="2026-09-01")
        with self.assertRaises(ValidationError):
            self.ext.record_security_check_result(
                self.oid, "scr-2", self.sec["id"], "passed", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_security_check_result(
                self.oid, "scr-3", self.sec["id"], "reported_pass",
                H.MEMBER, checked_at="not-a-date")

    def test_summary_derives_latest_and_counts(self):
        self.ext.record_security_service_config(
            self.oid, "scc-1", self.sec["id"], "a=1", H.MEMBER)
        self.ext.record_security_check_result(
            self.oid, "scr-1", self.sec["id"], "reported_fail", H.MEMBER)
        self.ext.record_security_check_result(
            self.oid, "scr-2", self.sec["id"], "reported_pass", H.MEMBER)
        summary = self.ext.security_service_summary(
            self.oid, self.sec["id"], H.MEMBER)
        self.assertEqual(summary["config_count"], 1)
        self.assertEqual(summary["result_count"], 2)
        self.assertEqual(
            summary["results_by_outcome"],
            {"reported_fail": 1, "reported_pass": 1})
        self.assertEqual(summary["latest_outcome"], "reported_pass")


class TestOperationRequests(_ExtCase):
    """Entry: operations execution engines — request records with
    recorded states; nothing executes."""

    def test_request_outcome_lifecycle(self):
        request = self.ext.request_operation(
            self.oid, "opr-1", "patching", "env-1", "Patch cycle",
            H.MEMBER, task_id=self.task["id"])
        self.assertEqual(request["status"], "requested")
        self.assertIs(request["executed"], False)
        done = self.ext.record_operation_outcome(
            self.oid, request["id"], "reported_completed", H.MEMBER,
            detail="runner report 42")
        self.assertEqual(done["status"], "reported_completed")
        with self.assertRaises(ValidationError):
            self.ext.record_operation_outcome(
                self.oid, request["id"], "reported_failed", H.MEMBER)

    def test_request_validation_and_cancel(self):
        with self.assertRaises(ValidationError):
            self.ext.request_operation(
                self.oid, "opr-x", "rebooting", "env-1", "X", H.MEMBER)
        request = self.ext.request_operation(
            self.oid, "opr-1", "support", "env-1", "Help", H.MEMBER)
        cancelled = self.ext.cancel_operation_request(
            self.oid, request["id"], H.MEMBER)
        self.assertEqual(cancelled["status"], "cancelled")

    def test_operations_summary_counts(self):
        self.ext.request_operation(
            self.oid, "opr-1", "patching", "env-1", "P", H.MEMBER)
        self.ext.request_operation(
            self.oid, "opr-2", "support", "env-1", "S", H.MEMBER)
        summary = self.ext.operations_summary(self.oid, H.MEMBER)
        self.assertEqual(summary["operation_requests"]["total"], 2)
        self.assertEqual(
            summary["operation_requests"]["by_status"], {"requested": 2})


class TestInvoicesFinOps(_ExtCase):
    """Entry: invoicing / billing & FinOps engine — invoice records
    with no money shape; FinOps derivations over core utilization."""

    def test_invoice_record_shape_and_uniqueness(self):
        invoice = self.ext.record_invoice(
            self.oid, "inv-1", self.account["id"], "2026-09", H.MEMBER,
            label="September")
        self.assertEqual(invoice["status"], "issued")
        self.assertEqual(
            set(invoice),
            {"id", "org_id", "invoice_ref", "account_id", "period",
             "label", "status", "created_by", "created_utc"})
        with self.assertRaises(ValidationError):
            self.ext.record_invoice(
                self.oid, "inv-2", self.account["id"], "2026-09", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_invoice(
                self.oid, "inv-3", self.account["id"], "2026-13", H.MEMBER)

    def test_invoice_status_lifecycle(self):
        invoice = self.ext.record_invoice(
            self.oid, "inv-1", self.account["id"], "2026-09", H.MEMBER)
        settled = self.ext.set_invoice_status(
            self.oid, invoice["id"], "settled", H.MEMBER)
        self.assertEqual(settled["status"], "settled")
        with self.assertRaises(ValidationError):
            self.ext.set_invoice_status(
                self.oid, invoice["id"], "void", H.MEMBER)
        other = self.ext.record_invoice(
            self.oid, "inv-2", self.account["id"], "2026-10", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.set_invoice_status(
                self.oid, other["id"], "issued", H.MEMBER)

    def test_finops_summary_derives_units_and_counts(self):
        self.store.record_utilization(
            self.oid, self.account["id"], "2026-09", 5, H.MEMBER)
        self.ext.record_invoice(
            self.oid, "inv-1", self.account["id"], "2026-09", H.MEMBER)
        summary = self.ext.finops_summary(self.oid, H.MEMBER)
        self.assertEqual(summary["utilization"]["units_total"], 5)
        self.assertEqual(
            summary["utilization"]["units_by_period"], {"2026-09": 5})
        self.assertEqual(summary["invoices"]["total"], 1)
        self.assertEqual(
            summary["invoices"]["by_status"], {"issued": 1})
        filtered = self.ext.finops_summary(self.oid, H.MEMBER,
                                           period="2026-10")
        self.assertEqual(filtered["utilization"]["units_total"], 0)
        self.assertEqual(filtered["invoices"]["total"], 0)


class TestResourceAllocations(_ExtCase):
    """Entry: application resource management engine — allocation
    records with derived utilization counts; no scheduler."""

    def test_allocation_lifecycle_and_units_discipline(self):
        allocation = self.ext.record_resource_allocation(
            self.oid, "ral-1", "wl-1", "compute", 40, H.MEMBER,
            deployment_id=self.dep["id"])
        self.assertEqual(allocation["status"], "active")
        for bad in (True, 1.5, "40", -1):
            with self.assertRaises(ValidationError):
                self.ext.record_resource_allocation(
                    self.oid, "ral-x", "wl-1", "compute", bad, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_resource_allocation(
                self.oid, "ral-y", "wl-1", "gpu", 1, H.MEMBER)
        released = self.ext.release_resource_allocation(
            self.oid, allocation["id"], H.MEMBER)
        self.assertEqual(released["status"], "released")
        with self.assertRaises(ValidationError):
            self.ext.release_resource_allocation(
                self.oid, allocation["id"], H.MEMBER)

    def test_resource_summary_derives_active_units(self):
        self.ext.record_resource_allocation(
            self.oid, "ral-1", "wl-1", "compute", 40, H.MEMBER)
        second = self.ext.record_resource_allocation(
            self.oid, "ral-2", "wl-1", "compute", 10, H.MEMBER)
        self.ext.record_resource_allocation(
            self.oid, "ral-3", "wl-2", "storage", 7, H.MEMBER)
        self.ext.release_resource_allocation(self.oid, second["id"], H.MEMBER)
        summary = self.ext.resource_summary(self.oid, H.MEMBER)
        self.assertEqual(summary["allocations"]["total"], 3)
        self.assertEqual(
            summary["active_units_by_kind"], {"compute": 40, "storage": 7})
        self.assertEqual(summary["active_units_total"], 47)


class TestVerificationCases(_ExtCase):
    """Entry: residency & personnel verification — case records
    with reported outcomes; the build verifies nothing itself."""

    def test_case_status_derived_never_stored(self):
        case = self.ext.open_verification_case(
            self.oid, "vfc-1", "env-1", "data_residency", H.MEMBER,
            environment_id=self.env["id"])
        for derived in ("status", "current_outcome", "outcome_count"):
            self.assertNotIn(derived, case)
        view = self.ext.get_verification_case(self.oid, case["id"], H.MEMBER)
        self.assertEqual(view["status"], "open")
        self.assertIsNone(view["current_outcome"])
        self.assertEqual(view["outcome_count"], 0)

    def test_outcome_recording_and_derived_view(self):
        case = self.ext.open_verification_case(
            self.oid, "vfc-1", "roster-ref-7", "personnel_us_citizenship",
            H.MEMBER)
        self.ext.record_verification_outcome(
            self.oid, case["id"], "reported_verified", H.ADMIN,
            detail="organizational attestation on file")
        view = self.ext.get_verification_case(self.oid, case["id"], H.MEMBER)
        self.assertEqual(view["status"], "decided")
        self.assertEqual(view["current_outcome"], "reported_verified")
        outcomes = self.ext.list_verification_outcomes(
            self.oid, case["id"], H.MEMBER)
        self.assertEqual(len(outcomes), 1)
        with self.assertRaises(ValidationError):
            self.ext.record_verification_outcome(
                self.oid, case["id"], "verified", H.ADMIN)

    def test_opener_may_not_record_outcome(self):
        case = self.ext.open_verification_case(
            self.oid, "vfc-1", "env-1", "operations_residency", H.MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.record_verification_outcome(
                self.oid, case["id"], "reported_verified", H.MEMBER)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "ext_verification_outcome:denied"]
        self.assertEqual(len(denied), 1)


class MutantDeciderBlindExtensions(CloudInfraExtensions):
    """The mutant: the verification separation-of-duties seam
    removed."""

    def _check_verification_decider_not_opener(self, case, actor):
        return None


class TestVerificationNegativeControl(_ExtCase):
    """Fresh negative control: the decider-not-opener seam must be
    load-bearing. (1) canonical expectation from the real
    implementation, (2) the mutant would NOT produce it, (3)
    treating the mutant's outcome as the expectation fails."""

    def test_canonical_expectation_refuses_opener(self):
        case = self.ext.open_verification_case(
            self.oid, "vfc-1", "env-1", "data_residency", H.MEMBER)
        with self.assertRaises(PermissionDenied):
            self.ext.record_verification_outcome(
                self.oid, case["id"], "reported_verified", H.MEMBER)
        view = self.ext.get_verification_case(self.oid, case["id"], H.MEMBER)
        self.assertEqual(view["status"], "open")
        self.assertIsNone(view["current_outcome"])

    def test_mutant_would_not_produce_that_expectation(self):
        mutant = MutantDeciderBlindExtensions(self.store)
        case = mutant.open_verification_case(
            self.oid, "vfc-1", "env-1", "data_residency", H.MEMBER)
        outcome = mutant.record_verification_outcome(
            self.oid, case["id"], "reported_verified", H.MEMBER)
        self.assertEqual(outcome["outcome"], "reported_verified")
        view = mutant.get_verification_case(self.oid, case["id"], H.MEMBER)
        self.assertEqual(view["status"], "decided")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["status"], "open")


class TestReferenceImplementations(_ExtCase):
    """The 8 stub-engine entries: labeled reference records that
    change no core record and execute nothing."""

    def _create_all_references(self):
        return [
            self.ext.record_provisioning_reference(
                self.oid, "pvr-1", "ten-a", "Provisioning plan", H.MEMBER),
            self.ext.record_elastic_hosting_reference(
                self.oid, "elr-1", "dep-1", "Elastic hosting", H.MEMBER,
                delivery_form="serverless"),
            self.ext.record_telemetry_reference(
                self.oid, "tlr-1", "observability", "env-1", "Pipeline",
                H.MEMBER, monitor_id=self.monitor["id"]),
            self.ext.record_backup_execution_reference(
                self.oid, "bkr-1", "backup", "dep-1", "Nightly", H.MEMBER,
                protection_id=self.protection["id"]),
            self.ext.record_key_metadata(
                self.oid, "kym-1", "symmetric_key", "At-rest key", H.MEMBER,
                algorithm_label="caller-stated label"),
            self.ext.record_ai_engine_reference(
                self.oid, "air-1", "Recommendation engine", H.MEMBER,
                target_ref="dep-1"),
            self.ext.record_cdn_reference(
                self.oid, "cdr-1", "dep-1", "Delivery", H.MEMBER,
                provider_label="network named by the fork"),
            self.ext.record_authorization_support_reference(
                self.oid, "aar-1", "A&A support", H.MEMBER, target_ref="ten-a"),
        ]

    def test_reference_labels(self):
        for record in self._create_all_references():
            self.assertIs(record["reference_stub"], True)
            self.assertEqual(record["status"], "recorded_reference_only")

    def test_reference_listing_and_get(self):
        created = self._create_all_references()
        listed = self.ext.list_reference_records(self.oid, H.MEMBER)
        self.assertEqual(len(listed), 8)
        kinds = {r["id"]: r for r in listed}
        for record in created:
            self.assertIn(record["id"], kinds)
        only_keys = self.ext.list_reference_records(
            self.oid, H.MEMBER, kind="key_metadata")
        self.assertEqual(len(only_keys), 1)
        fetched = self.ext.get_reference_record(
            self.oid, created[0]["id"], H.MEMBER)
        self.assertEqual(fetched["id"], created[0]["id"])
        with self.assertRaises(NotFoundError):
            self.ext.get_reference_record(self.oid, "pvr-999", H.MEMBER)

    def test_reference_flags_per_entry(self):
        provisioning, elastic, telemetry, backup, _key, ai, cdn, aa = (
            self._create_all_references())
        self.assertIs(provisioning["provisioned"], False)
        self.assertIs(elastic["hosted_here"], False)
        self.assertEqual(elastic["delivery_form"], "serverless")
        self.assertIs(telemetry["reference_transport"], True)
        self.assertIs(telemetry["telemetry_collected"], False)
        self.assertIs(backup["executed"], False)
        self.assertIs(ai["issues_recommendations"], False)
        self.assertIs(cdn["reference_transport"], True)
        self.assertIs(cdn["traffic_carried"], False)
        self.assertIs(aa["package_prepared"], False)

    def test_references_change_no_core_records(self):
        before = self.store.org_report(self.oid, H.ADMIN)
        self._create_all_references()
        after = self.store.org_report(self.oid, H.ADMIN)
        self.assertEqual(before, after)

    def test_key_metadata_exact_shape_no_material(self):
        record = self.ext.record_key_metadata(
            self.oid, "kym-1", "certificate", "TLS cert", H.MEMBER,
            algorithm_label="caller-stated label", note="metadata only")
        self.assertEqual(
            set(record),
            {"id", "org_id", "reference_ref", "key_ref", "key_kind",
             "label", "algorithm_label", "note", "reference_stub",
             "status", "created_by", "created_utc"})
        params = set(inspect.signature(
            CloudInfraExtensions.record_key_metadata).parameters)
        for part in FORBIDDEN_PARAM_PARTS:
            for param in params:
                self.assertNotIn(part, param)

    def test_reference_refs_unique_per_kind(self):
        self.ext.record_cdn_reference(
            self.oid, "cdr-1", "dep-1", "Delivery", H.MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_cdn_reference(
                self.oid, "cdr-1", "dep-2", "Again", H.MEMBER)
        # The same ref under a different kind is a different record.
        self.ext.record_provisioning_reference(
            self.oid, "cdr-1", "ten-a", "Plan", H.MEMBER)


class TestBatchDiscipline(_ExtCase):
    """Cross-cutting pins: no money shape anywhere, signatures
    carry no forbidden parameter, RBAC and membership are enforced
    with denials audited, and mutations reach the audit log."""

    def _populate(self):
        intent = self.ext.record_deployment_intent(
            self.oid, "int-1", self.template["id"], self.tenancy["id"],
            "wl-1", H.MEMBER)
        self.ext.record_security_service_config(
            self.oid, "scc-1", self.sec["id"], "a=1", H.MEMBER)
        self.ext.record_security_check_result(
            self.oid, "scr-1", self.sec["id"], "reported_pass", H.MEMBER)
        self.ext.request_operation(
            self.oid, "opr-1", "patching", "env-1", "P", H.MEMBER)
        self.ext.record_invoice(
            self.oid, "inv-1", self.account["id"], "2026-09", H.MEMBER)
        self.store.record_utilization(
            self.oid, self.account["id"], "2026-09", 5, H.MEMBER)
        self.ext.record_resource_allocation(
            self.oid, "ral-1", "wl-1", "compute", 40, H.MEMBER)
        case = self.ext.open_verification_case(
            self.oid, "vfc-1", "env-1", "data_residency", H.MEMBER)
        self.ext.record_verification_outcome(
            self.oid, case["id"], "reported_verified", H.ADMIN)
        TestReferenceImplementations._create_all_references(self)
        return intent

    def test_no_money_shape_anywhere(self):
        intent = self._populate()
        surfaces = [
            self.ext.get_deployment_intent(self.oid, intent["id"], H.MEMBER),
            self.ext.list_security_service_configs(self.oid, H.MEMBER),
            self.ext.list_security_check_results(self.oid, H.MEMBER),
            self.ext.security_service_summary(self.oid, self.sec["id"],
                                              H.MEMBER),
            self.ext.list_operation_requests(self.oid, H.MEMBER),
            self.ext.operations_summary(self.oid, H.MEMBER),
            self.ext.list_invoices(self.oid, H.MEMBER),
            self.ext.finops_summary(self.oid, H.MEMBER),
            self.ext.list_resource_allocations(self.oid, H.MEMBER),
            self.ext.resource_summary(self.oid, H.MEMBER),
            self.ext.list_verification_cases(self.oid, H.MEMBER),
            self.ext.list_reference_records(self.oid, H.MEMBER),
        ]
        keys = set()
        for surface in surfaces:
            keys |= _all_keys(surface)
        for part in MONEY_FIELD_PARTS:
            for key in keys:
                self.assertNotIn(
                    part, key,
                    "money-shaped key %r (part %r) in extension surface"
                    % (key, part))

    def test_no_forbidden_parameters(self):
        for name in dir(CloudInfraExtensions):
            if name.startswith("_"):
                continue
            member = getattr(CloudInfraExtensions, name)
            if not callable(member):
                continue
            for param in inspect.signature(member).parameters.values():
                for part in FORBIDDEN_PARAM_PARTS:
                    self.assertNotIn(part, param.name)

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_invoice(
                self.oid, "inv-1", self.account["id"], "2026-09", H.VIEWER)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "ext_invoice_record:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(self.ext.list_invoices(self.oid, H.MEMBER), [])

    def test_outsider_denied_by_membership(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_deployment_intent(
                self.oid, "int-1", self.template["id"], self.tenancy["id"],
                "wl-1", H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.ext.list_invoices(self.oid, H.OUTSIDER)

    def test_mutations_reach_audit_with_ext_prefix(self):
        self._populate()
        actions = {e["action"] for e in self.audit.entries()}
        ext_actions = {a for a in actions if a.startswith("ext_")}
        self.assertIn("ext_deployment_intent_record", ext_actions)
        self.assertIn("ext_invoice_record", ext_actions)
        self.assertIn("ext_verification_outcome", ext_actions)
        self.assertIn("ext_key_metadata_record", ext_actions)
        self.assertGreaterEqual(len(ext_actions), 10)

    def test_cross_org_records_invisible(self):
        other = self.store.create_organization("org-other", "Other", H.ADMIN)
        invoice = self.ext.record_invoice(
            self.oid, "inv-1", self.account["id"], "2026-09", H.MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.get_invoice(other["id"], invoice["id"], H.ADMIN)
        self.assertEqual(
            self.ext.list_invoices(other["id"], H.ADMIN), [])


if __name__ == "__main__":
    unittest.main()
