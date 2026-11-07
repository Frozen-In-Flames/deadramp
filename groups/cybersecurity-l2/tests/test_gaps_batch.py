"""Final GAPS batch — Cybersecurity & Risk Management L2 extension surface.

Traces to: the 17 open entries of this group's section in the
repo-root GAPS.md (the 18th entry, detection engines and staffed SOC
services, was closed as re-scoped before this unit and is not touched
here) and to gaps-batch/DECISION.md. Every test names its entry.

Category discipline pinned throughout: this module builds records
forms only — no engine scans, detects, enforces, executes, or scores.
Stub-engine families carry ``reference_stub: true`` on every record
(pipeline receipts also ``reference_transport: true``), posture views
are counts only, and identity surfaces are hooks / reported outcomes,
never an IdP or a decision.
"""

import unittest

from cyber_helpers import ADMIN, ANALYST, VIEWER  # noqa: F401  (path setup)

from cyber.audit import AuditLog
from cyber.errors import NotFoundError, PermissionDenied, ValidationError
from cyber.extensions import ExtensionStore


def fresh_ext(audit=None):
    if audit is None:
        audit = AuditLog()
    return ExtensionStore(audit=audit), audit


def _all_keys(obj):
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class TestEnforcementPlanes(unittest.TestCase):
    """Entry: Network enforcement planes (11) — records form."""

    def test_register_and_coverage_counts(self):
        ext, _ = fresh_ext()
        point = ext.register_enforcement_point(
            "plane-alpha", "firewall", "scope-north", "policy-base",
            actor=ANALYST,
        )
        self.assertEqual(point["id"], "plane-1")
        self.assertEqual(point["status"], "registered")
        ext.register_enforcement_point(
            "plane-beta", "segmentation", "scope-north", "policy-base",
            actor=ANALYST,
        )
        coverage = ext.enforcement_coverage(actor=VIEWER)
        self.assertEqual(coverage["total_registered"], 2)
        self.assertEqual(coverage["by_kind"]["firewall"], 1)
        self.assertEqual(coverage["by_kind"]["waf"], 0)

    def test_retire_removes_from_derived_coverage(self):
        ext, _ = fresh_ext()
        point = ext.register_enforcement_point(
            "plane-alpha", "ztna", "scope-a", "policy-a", actor=ANALYST
        )
        ext.retire_enforcement_point(point["id"], actor=ANALYST)
        coverage = ext.enforcement_coverage(actor=ANALYST)
        self.assertEqual(coverage["total_registered"], 0)
        with self.assertRaises(ValidationError):
            ext.retire_enforcement_point(point["id"], actor=ANALYST)

    def test_address_shaped_refs_rejected_and_no_id_consumed(self):
        ext, _ = fresh_ext()
        for bad in ("10.0.0.1", "https://example", "host.example", "has space"):
            with self.assertRaises(ValidationError):
                ext.register_enforcement_point(
                    "plane-x", "firewall", bad, "policy-a", actor=ANALYST
                )
        point = ext.register_enforcement_point(
            "plane-x", "firewall", "scope-a", "policy-a", actor=ANALYST
        )
        self.assertEqual(point["id"], "plane-1")

    def test_bad_kind_rejected(self):
        ext, _ = fresh_ext()
        with self.assertRaises(ValidationError):
            ext.register_enforcement_point(
                "plane-x", "antivirus", "scope-a", "policy-a", actor=ANALYST
            )


class TestThreatIntel(unittest.TestCase):
    """Entry: Threat-intelligence feeds (9) — records form."""

    def test_feed_item_lifecycle(self):
        ext, _ = fresh_ext()
        feed = ext.register_intel_feed(
            "feed-alpha", "provider-a", "ioc", actor=ANALYST
        )
        item = ext.ingest_intel_item(
            feed["id"], "indicator-1", "hash", "high", actor=ANALYST,
            summary="reported by feed",
        )
        self.assertEqual(item["status"], "new")
        self.assertEqual(item["reported_level"], "high")
        moved = ext.transition_intel_item(item["id"], "reviewed", actor=ANALYST)
        self.assertEqual(moved["status"], "reviewed")
        with self.assertRaises(ValidationError):
            ext.transition_intel_item(item["id"], "new", actor=ANALYST)

    def test_item_requires_registered_feed(self):
        ext, _ = fresh_ext()
        with self.assertRaises(NotFoundError):
            ext.ingest_intel_item(
                "feed-99", "indicator-1", "hash", "low", actor=ANALYST
            )


class TestGrcAutomation(unittest.TestCase):
    """Entry: Full GRC automation suites (8) — records form beyond
    the core control mapping: frameworks + evidence workflow."""

    def test_evidence_task_full_lifecycle_two_actors(self):
        ext, _ = fresh_ext()
        framework = ext.register_framework(
            "fw-800-53", "NIST SP 800-53 Rev. 5", actor=ADMIN
        )
        task = ext.create_evidence_task(
            framework["id"], "AC-2", "owner-team-a", actor=ADMIN
        )
        self.assertEqual(task["status"], "open")
        collected = ext.transition_evidence_task(
            task["id"], "collected", actor=ANALYST
        )
        self.assertEqual(collected["collected_by"], "bob")
        verified = ext.transition_evidence_task(
            task["id"], "verified", actor=ADMIN
        )
        self.assertEqual(verified["verified_by"], "alice")
        self.assertEqual(verified["status"], "verified")

    def test_evidence_task_unknown_control_rejected(self):
        ext, _ = fresh_ext()
        framework = ext.register_framework("fw-x", "Framework X", actor=ADMIN)
        with self.assertRaises(ValidationError):
            ext.create_evidence_task(
                framework["id"], "ZZ-9", "owner-a", actor=ADMIN
            )

    def test_separation_of_duties_guard(self):
        """The fresh negative control's canonical expectation: the
        collector of evidence may not verify it. Mutating the guard
        seam in src/cyber/extensions.py must fail this test (drill
        recorded in tests/README.md)."""
        ext, _ = fresh_ext()
        framework = ext.register_framework("fw-x", "Framework X", actor=ADMIN)
        task = ext.create_evidence_task(
            framework["id"], "AU-2", "owner-a", actor=ADMIN
        )
        ext.transition_evidence_task(task["id"], "collected", actor=ANALYST)
        with self.assertRaises(ValidationError):
            ext.transition_evidence_task(task["id"], "verified", actor=ANALYST)
        still = ext.list_evidence_tasks(actor=ADMIN, status="collected")
        self.assertEqual(len(still), 1)


class TestIdentityHooks(unittest.TestCase):
    """Entry: Identity products (8) — hooks only, no IdP."""

    def test_hook_record_states_hook_only(self):
        ext, _ = fresh_ext()
        hook = ext.register_identity_hook(
            "idp-product-a", "sso", "service login flow", actor=ANALYST
        )
        self.assertTrue(hook["hook_only"])
        self.assertFalse(hook["identity_provider"])

    def test_bad_hook_kind_rejected(self):
        ext, _ = fresh_ext()
        with self.assertRaises(ValidationError):
            ext.register_identity_hook(
                "prod-a", "password_vault", "login", actor=ANALYST
            )


class TestEdrAgents(unittest.TestCase):
    """Entry: EDR/XDR agents (7) — enrollment + reported health."""

    def test_enroll_and_report(self):
        ext, _ = fresh_ext()
        agent = ext.register_edr_agent("agent-1", "asset-ref-1", actor=ANALYST)
        self.assertEqual(agent["last_reported_status"], "unknown")
        updated = ext.record_agent_report(agent["id"], "degraded", actor=ANALYST)
        self.assertEqual(updated["last_reported_status"], "degraded")
        with self.assertRaises(ValidationError):
            ext.record_agent_report(agent["id"], "on_fire", actor=ANALYST)


class TestPhishingTraining(unittest.TestCase):
    """Entry: Phishing simulation / training (7) — program records;
    nothing is sent or simulated."""

    def test_campaign_and_training_counts(self):
        ext, _ = fresh_ext()
        campaign = ext.create_campaign(
            "camp-q1", "Q1 awareness", "audience-staff", actor=ANALYST
        )
        self.assertFalse(campaign["messages_sent"])
        first = ext.assign_training(campaign["id"], "learner-1", actor=ANALYST)
        ext.assign_training(campaign["id"], "learner-2", actor=ANALYST)
        ext.complete_training(first["id"], actor=ANALYST)
        counts = ext.campaign_counts(actor=VIEWER, campaign_id=campaign["id"])
        self.assertEqual(counts["total"], 2)
        self.assertEqual(counts["by_status"]["completed"], 1)
        self.assertEqual(counts["by_status"]["assigned"], 1)

    def test_campaign_lifecycle_rejects_skip(self):
        ext, _ = fresh_ext()
        campaign = ext.create_campaign(
            "camp-q1", "Q1 awareness", "audience-staff", actor=ANALYST
        )
        with self.assertRaises(ValidationError):
            ext.transition_campaign(campaign["id"], "completed", actor=ANALYST)


class TestAppSecEngines(unittest.TestCase):
    """Entry: AppSec testing engines (6) — registry + run records."""

    def test_run_record(self):
        ext, _ = fresh_ext()
        engine = ext.register_appsec_engine("engine-a", "sast", actor=ANALYST)
        run = ext.record_appsec_run(engine["id"], "asset-ref-1", 12,
                                    actor=ANALYST)
        self.assertEqual(run["reported_finding_count"], 12)
        self.assertFalse(run["executed_here"])
        with self.assertRaises(ValidationError):
            ext.record_appsec_run(engine["id"], "asset-ref-1", True,
                                  actor=ANALYST)


class TestPostureEngines(unittest.TestCase):
    """Entry: CSPM/CNAPP/SSPM posture engines (5) — snapshots are
    counts only; the derived aggregate carries no score."""

    def test_snapshot_aggregate_is_counts_only(self):
        ext, _ = fresh_ext()
        engine = ext.register_posture_engine(
            "posture-a", "cspm", "scope-cloud-a", actor=ANALYST
        )
        ext.record_posture_snapshot(
            engine["id"], {"misconfigured": 3, "compliant": 10}, actor=ANALYST
        )
        ext.record_posture_snapshot(
            engine["id"], {"misconfigured": 1}, actor=ANALYST
        )
        totals = ext.posture_counts(actor=VIEWER, engine_id=engine["id"])
        self.assertEqual(totals["snapshots"], 2)
        self.assertEqual(totals["counts"]["misconfigured"], 4)
        self.assertEqual(totals["counts"]["compliant"], 10)
        for key in _all_keys(totals):
            self.assertNotIn("score", key)
            self.assertNotIn("grade", key)
            self.assertNotIn("rate", key)

    def test_snapshot_rejects_non_counts(self):
        ext, _ = fresh_ext()
        engine = ext.register_posture_engine(
            "posture-a", "cnapp", "scope-a", actor=ANALYST
        )
        for bad in ({"a": -1}, {"a": 1.5}, {"a": True}, {"a": "3"}, {}):
            with self.assertRaises(ValidationError):
                ext.record_posture_snapshot(engine["id"], bad, actor=ANALYST)


class TestScanners(unittest.TestCase):
    """Entry: Vulnerability scanners (4) — registry + scan records;
    scanning itself stays Extended, output stays in core findings."""

    def test_scanner_and_scan_record(self):
        ext, _ = fresh_ext()
        scanner = ext.register_scanner("scanner-a", actor=ANALYST)
        scan = ext.record_scan(scanner["id"], "asset-ref-9", actor=ANALYST)
        self.assertFalse(scan["executed_here"])
        self.assertEqual(
            len(ext.list_scan_records(actor=VIEWER, asset_ref="asset-ref-9")), 1
        )


class TestEnclaves(unittest.TestCase):
    """Entry: CUI enclaves / VDI (3) — environment + session records;
    nothing is hosted."""

    def test_session_active_count_is_derived(self):
        ext, _ = fresh_ext()
        enclave = ext.register_enclave("enclave-a", "CUI", actor=ANALYST)
        self.assertFalse(enclave["hosted_here"])
        one = ext.start_enclave_session(enclave["id"], "user-1", actor=ANALYST)
        ext.start_enclave_session(enclave["id"], "user-2", actor=ANALYST)
        self.assertEqual(
            ext.active_session_count(actor=VIEWER, enclave_id=enclave["id"]),
            {"enclave_id": enclave["id"], "active_sessions": 2},
        )
        ext.end_enclave_session(one["id"], actor=ANALYST)
        self.assertEqual(
            ext.active_session_count(actor=ANALYST, enclave_id=enclave["id"])
            ["active_sessions"],
            1,
        )


class TestProofing(unittest.TestCase):
    """Entry: Identity proofing / fraud (2) — reported outcomes only;
    no decision, no score."""

    def test_proofing_record_shape(self):
        ext, _ = fresh_ext()
        record = ext.record_proofing_check(
            "subject-1", "document", "passed", actor=ANALYST
        )
        self.assertFalse(record["decision_made"])
        self.assertNotIn("score", _all_keys(record))


class TestMgmtAgents(unittest.TestCase):
    """Entry: Endpoint management agents (2) — registry + reported
    patch status records."""

    def test_patch_status_record(self):
        ext, _ = fresh_ext()
        agent = ext.register_mgmt_agent(
            "mgmt-1", "asset-ref-1", ["patching", "configuration"],
            actor=ANALYST,
        )
        patch = ext.record_patch_status(
            agent["id"], "patch-2026-01", "applied", actor=ANALYST
        )
        self.assertFalse(patch["applied_here"])
        with self.assertRaises(ValidationError):
            ext.register_mgmt_agent(
                "mgmt-2", "asset-ref-1", ["remote_shell"], actor=ANALYST
            )


class TestModelReferences(unittest.TestCase):
    """Entry (stub-engine): AI/ML detection models (17 siblings) —
    labeled reference records; no inference, no score."""

    def test_model_records_are_labeled_stubs(self):
        ext, _ = fresh_ext()
        model = ext.register_model_reference(
            "model-a", "anomaly_detection", actor=ANALYST
        )
        self.assertTrue(model["reference_stub"])
        output = ext.record_model_output_reference(
            model["id"], "find-1", "anomalous", actor=ANALYST
        )
        self.assertTrue(output["reference_stub"])
        self.assertNotIn("score", _all_keys(output))


class TestSoarReferences(unittest.TestCase):
    """Entry (stub-engine): SOAR / orchestration engines (14) —
    labeled reference records; runs state executed: false."""

    def test_playbook_run_is_reference_only(self):
        ext, _ = fresh_ext()
        playbook = ext.register_playbook_reference(
            "pb-triage", "Triage playbook", actor=ANALYST
        )
        self.assertTrue(playbook["reference_stub"])
        run = ext.record_playbook_run_reference(
            playbook["id"], "find-1", actor=ANALYST
        )
        self.assertTrue(run["reference_stub"])
        self.assertFalse(run["executed"])


class TestBackupReferences(unittest.TestCase):
    """Entry (stub-engine): Backup / recovery products (9) —
    labeled reference records; no backup runs here."""

    def test_backup_job_reference(self):
        ext, _ = fresh_ext()
        product = ext.register_backup_product_reference(
            "backup-a", actor=ANALYST
        )
        self.assertTrue(product["reference_stub"])
        job = ext.record_backup_job_reference(
            product["id"], "asset-ref-1", "completed", actor=ANALYST
        )
        self.assertTrue(job["reference_stub"])
        self.assertFalse(job["executed_here"])


class TestDlpReferences(unittest.TestCase):
    """Entry (stub-engine): DLP / insider monitoring engines (7) —
    labeled reference records; alerts arrive as records, no content
    is inspected here."""

    def test_dlp_alert_reference(self):
        ext, _ = fresh_ext()
        engine = ext.register_dlp_engine_reference(
            "dlp-a", "endpoint", actor=ANALYST
        )
        self.assertTrue(engine["reference_stub"])
        alert = ext.record_dlp_alert_reference(
            engine["id"], "asset-ref-1", "high", actor=ANALYST
        )
        self.assertTrue(alert["reference_stub"])
        self.assertEqual(alert["reported_level"], "high")


class TestPipelineReferences(unittest.TestCase):
    """Entry (stub-engine): Log / telemetry pipelines (5) — labeled
    reference records; receipts carry reference_transport."""

    def test_pipeline_receipt_labels(self):
        ext, _ = fresh_ext()
        pipeline = ext.register_pipeline_reference("pipe-a", actor=ANALYST)
        self.assertTrue(pipeline["reference_stub"])
        receipt = ext.record_pipeline_receipt(
            pipeline["id"], "batch-1", 500, actor=ANALYST
        )
        self.assertTrue(receipt["reference_stub"])
        self.assertTrue(receipt["reference_transport"])
        self.assertEqual(receipt["event_count"], 500)
        with self.assertRaises(ValidationError):
            ext.record_pipeline_receipt(
                pipeline["id"], "batch-2", -1, actor=ANALYST
            )


class TestAccessAndAudit(unittest.TestCase):
    """Cross-cutting founding doctrines: RBAC via the existing
    access module, denied attempts audited, summary counts only."""

    def test_viewer_cannot_register_and_denial_is_audited(self):
        ext, audit = fresh_ext()
        with self.assertRaises(PermissionDenied):
            ext.register_enforcement_point(
                "plane-a", "firewall", "scope-a", "policy-a", actor=VIEWER
            )
        actions = [entry["action"] for entry in audit.entries()]
        self.assertIn("plane_register:denied", actions)
        self.assertEqual(ext.list_enforcement_points(actor=ADMIN), [])

    def test_viewer_can_read(self):
        ext, _ = fresh_ext()
        ext.register_scanner("scanner-a", actor=ANALYST)
        self.assertEqual(len(ext.list_scanners(actor=VIEWER)), 1)

    def test_extension_summary_counts_only(self):
        ext, _ = fresh_ext()
        ext.register_scanner("scanner-a", actor=ANALYST)
        ext.register_pipeline_reference("pipe-a", actor=ANALYST)
        summary = ext.extension_summary(actor=VIEWER)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["records"]["scanners"], 1)
        for key in _all_keys(summary):
            self.assertNotIn("score", key)


if __name__ == "__main__":
    unittest.main()
