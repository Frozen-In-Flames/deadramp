"""Tests for the final GAPS batch extension (cyber.extensions).

Traces to: UNION-SPEC.md "Implementation contract" (extension
surface) and the repo-root GAPS.md section "Untiered Set 1 —
Cybersecurity & Risk Management" (the thirteen open entries this
batch closes). The founding discipline binds throughout: the
extension is records form only — registries, ingestion records of
engine-reported output, tracking workflows, derived counts — with
labeled reference implementations where the triage says
stub-engine. Nothing in the extension scans, detects, enforces,
blocks, trains, monitors, hosts, or executes, and no extension view
carries a score, a rate, or a grade.
"""

import unittest

from cyber_helpers import ADMIN, ANALYST, VIEWER

from cyber.audit import AuditLog
from cyber.errors import PermissionDenied, ValidationError
from cyber.extensions import ExtensionStore

FORBIDDEN_KEYS = ("score", "rate", "grade", "percent")


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


def assert_counts_only(test_case, view):
    for key in _all_keys(view):
        for forbidden in FORBIDDEN_KEYS:
            test_case.assertNotIn(
                forbidden, key,
                "counts-only view leaked key %r" % (key,),
            )


def fresh(audit=None):
    return ExtensionStore(audit=audit if audit is not None else AuditLog())


class TestEnforcementPlanes(unittest.TestCase):
    def test_register_and_coverage_counts(self):
        store = fresh()
        store.register_enforcement_point(
            "plane-alpha", "firewall", "scope-east", "policy-main",
            actor=ANALYST,
        )
        store.register_enforcement_point(
            "plane-beta", "ztna", "scope-west", "policy-main",
            actor=ANALYST,
        )
        coverage = store.enforcement_coverage(actor=VIEWER)
        self.assertEqual(coverage["total_registered"], 2)
        self.assertEqual(coverage["by_kind"]["firewall"], 1)
        self.assertEqual(coverage["by_kind"]["ztna"], 1)
        assert_counts_only(self, coverage)

    def test_retire_removes_from_coverage(self):
        store = fresh()
        plane = store.register_enforcement_point(
            "plane-alpha", "waf", "scope-edge", "policy-main",
            actor=ANALYST,
        )
        retired = store.retire_enforcement_point(plane["id"], actor=ANALYST)
        self.assertEqual(retired["status"], "retired")
        self.assertEqual(
            store.enforcement_coverage(actor=VIEWER)["total_registered"], 0
        )
        with self.assertRaises(ValidationError):
            store.retire_enforcement_point(plane["id"], actor=ANALYST)


class TestThreatIntelligence(unittest.TestCase):
    def test_feed_item_lifecycle_and_summary(self):
        store = fresh()
        feed = store.register_intel_feed(
            "feed-alpha", "provider-one", "ioc", actor=ANALYST
        )
        item = store.ingest_intel_item(
            feed["id"], "indicator-1", "hash", "high", actor=ANALYST,
            summary="reported by feed",
        )
        self.assertEqual(item["status"], "new")
        self.assertEqual(item["reported_level"], "high")
        moved = store.transition_intel_item(item["id"], "reviewed",
                                            actor=ANALYST)
        self.assertEqual(moved["status"], "reviewed")
        with self.assertRaises(ValidationError):
            store.transition_intel_item(item["id"], "new", actor=ANALYST)
        summary = store.intel_summary(actor=VIEWER)
        self.assertEqual(summary["feeds"], 1)
        self.assertEqual(summary["items"], 1)
        self.assertEqual(summary["items_by_kind"]["hash"], 1)
        assert_counts_only(self, summary)


class TestEdrAgents(unittest.TestCase):
    def test_register_and_report(self):
        store = fresh()
        agent = store.register_edr_agent("agent-1", "asset-1", actor=ANALYST)
        self.assertEqual(agent["last_reported_status"], "unknown")
        updated = store.record_agent_report(agent["id"], "degraded",
                                            actor=ANALYST)
        self.assertEqual(updated["last_reported_status"], "degraded")
        agents = store.list_edr_agents(actor=VIEWER, asset_ref="asset-1")
        self.assertEqual(len(agents), 1)


class TestPhishingCampaigns(unittest.TestCase):
    def test_campaign_lifecycle_and_training_counts(self):
        store = fresh()
        campaign = store.create_campaign(
            "camp-1", "Q4 awareness", "audience-all", actor=ANALYST
        )
        self.assertEqual(campaign["status"], "planned")
        self.assertFalse(campaign["messages_sent"])
        store.transition_campaign(campaign["id"], "approved", actor=ANALYST)
        assignment = store.assign_training(campaign["id"], "learner-7",
                                           actor=ANALYST)
        store.complete_training(assignment["id"], actor=ANALYST)
        counts = store.campaign_counts(actor=VIEWER,
                                       campaign_id=campaign["id"])
        self.assertEqual(counts["total"], 1)
        self.assertEqual(counts["by_status"]["completed"], 1)
        self.assertEqual(counts["by_status"]["assigned"], 0)
        assert_counts_only(self, counts)

    def test_campaign_transition_guard(self):
        store = fresh()
        campaign = store.create_campaign(
            "camp-1", "Q4 awareness", "audience-all", actor=ANALYST
        )
        with self.assertRaises(ValidationError):
            store.transition_campaign(campaign["id"], "completed",
                                      actor=ANALYST)


class TestAppSecEngines(unittest.TestCase):
    def test_engine_and_run_record(self):
        store = fresh()
        engine = store.register_appsec_engine("engine-sast", "sast",
                                              actor=ANALYST)
        run = store.record_appsec_run(engine["id"], "asset-repo-1", 3,
                                      actor=ANALYST)
        self.assertFalse(run["executed_here"])
        self.assertEqual(run["reported_finding_count"], 3)
        runs = store.list_appsec_runs(actor=VIEWER, engine_id=engine["id"])
        self.assertEqual(len(runs), 1)


class TestPostureEngines(unittest.TestCase):
    def test_snapshot_aggregation_counts_only(self):
        store = fresh()
        engine = store.register_posture_engine(
            "engine-cspm", "cspm", "scope-cloud", actor=ANALYST
        )
        store.record_posture_snapshot(
            engine["id"], {"misconfigurations": 4, "open_alerts": 2},
            actor=ANALYST,
        )
        store.record_posture_snapshot(
            engine["id"], {"misconfigurations": 1}, actor=ANALYST
        )
        counts = store.posture_counts(actor=VIEWER, engine_id=engine["id"])
        self.assertEqual(counts["snapshots"], 2)
        self.assertEqual(counts["counts"]["misconfigurations"], 5)
        self.assertEqual(counts["counts"]["open_alerts"], 2)
        assert_counts_only(self, counts)

    def test_snapshot_rejects_non_counts(self):
        store = fresh()
        engine = store.register_posture_engine(
            "engine-cspm", "cspm", "scope-cloud", actor=ANALYST
        )
        with self.assertRaises(ValidationError):
            store.record_posture_snapshot(
                engine["id"], {"posture": "good"}, actor=ANALYST
            )
        with self.assertRaises(ValidationError):
            store.record_posture_snapshot(
                engine["id"], {"misconfigurations": 1.5}, actor=ANALYST
            )
        with self.assertRaises(ValidationError):
            store.record_posture_snapshot(engine["id"], {}, actor=ANALYST)


class TestMgmtAgents(unittest.TestCase):
    def test_agent_and_patch_record(self):
        store = fresh()
        agent = store.register_mgmt_agent(
            "mgmt-1", "asset-1", ["patching", "configuration"],
            actor=ANALYST,
        )
        record = store.record_patch_status(agent["id"], "patch-2026-11",
                                           "applied", actor=ANALYST)
        self.assertFalse(record["applied_here"])
        self.assertEqual(record["reported_status"], "applied")
        with self.assertRaises(ValidationError):
            store.register_mgmt_agent(
                "mgmt-2", "asset-1", ["teleportation"], actor=ANALYST
            )


class TestDlpEngines(unittest.TestCase):
    def test_policy_vocabulary_is_monitor_alert_only(self):
        store = fresh()
        policy = store.create_dlp_policy(
            "egress-watch", "email", "alert", actor=ANALYST
        )
        self.assertEqual(policy["declared_action"], "alert")
        with self.assertRaises(ValidationError):
            store.create_dlp_policy("egress-block", "email", "block",
                                    actor=ANALYST)

    def test_events_and_summary_by_classification(self):
        store = fresh()
        policy = store.create_dlp_policy(
            "egress-watch", "web", "monitor", actor=ANALYST
        )
        store.record_dlp_event(policy["id"], "asset-1", "confidential",
                               actor=ANALYST)
        store.record_dlp_event(policy["id"], "asset-1", "internal",
                               actor=ANALYST)
        store.record_dlp_event(policy["id"], "asset-2", "confidential",
                               actor=ANALYST)
        summary = store.dlp_summary(actor=VIEWER)
        self.assertEqual(summary["policies"], 1)
        self.assertEqual(summary["events"], 3)
        self.assertEqual(
            summary["events_by_classification"]["confidential"], 2
        )
        self.assertEqual(summary["events_by_classification"]["internal"], 1)
        assert_counts_only(self, summary)


class TestProofing(unittest.TestCase):
    def test_case_outcome_and_derived_view(self):
        store = fresh()
        case = store.create_proofing_case("subject-9", "document_check",
                                          actor=ANALYST)
        self.assertIsNone(
            store.proofing_case_view(case["id"], actor=VIEWER)
            ["current_outcome"]
        )
        store.record_proofing_outcome(case["id"], "verified_declared",
                                      actor=ADMIN)
        view = store.proofing_case_view(case["id"], actor=VIEWER)
        self.assertEqual(view["current_outcome"], "verified_declared")
        self.assertEqual(view["outcome_count"], 1)
        self.assertNotIn("current_outcome", case)

    def test_outcome_recorder_must_differ_from_opener(self):
        # The canonical separation-of-duties pin: this is the test
        # the gaps-batch negative control mutates against (see
        # tests/README.md). The opener may not record the outcome.
        store = fresh()
        case = store.create_proofing_case("subject-9", "manual_review",
                                          actor=ANALYST)
        with self.assertRaises(ValidationError):
            store.record_proofing_outcome(case["id"], "verified_declared",
                                          actor=ANALYST)
        outcome = store.record_proofing_outcome(
            case["id"], "verified_declared", actor=ADMIN
        )
        self.assertEqual(outcome["outcome"], "verified_declared")


class TestModelReferences(unittest.TestCase):
    def test_model_and_output_carry_reference_labels(self):
        store = fresh()
        model = store.register_model_reference(
            "model-1", "anomaly_detection", actor=ANALYST
        )
        self.assertTrue(model["reference_stub"])
        output = store.record_model_output_reference(
            model["id"], "finding-42", "suspicious", actor=ANALYST
        )
        self.assertTrue(output["reference_stub"])
        self.assertEqual(output["reported_label"], "suspicious")


class TestPlaybookReferences(unittest.TestCase):
    def test_playbook_and_run_carry_reference_labels(self):
        store = fresh()
        playbook = store.register_playbook_reference(
            "pb-isolate", "Isolate host workflow", actor=ANALYST
        )
        self.assertTrue(playbook["reference_stub"])
        run = store.record_playbook_run_reference(
            playbook["id"], "trigger-7", actor=ANALYST
        )
        self.assertTrue(run["reference_stub"])
        self.assertFalse(run["executed"])


class TestIdentityProductReferences(unittest.TestCase):
    def test_identity_record_is_hook_only_reference(self):
        store = fresh()
        record = store.register_identity_product_reference(
            "idp-ext", "sso", "service login hook", actor=ANALYST
        )
        self.assertTrue(record["reference_stub"])
        self.assertTrue(record["hook_only"])
        self.assertFalse(record["identity_provider"])
        listed = store.list_identity_product_references(
            actor=VIEWER, hook_kind="sso"
        )
        self.assertEqual(len(listed), 1)


class TestPipelineReferences(unittest.TestCase):
    def test_receipt_carries_transport_label(self):
        store = fresh()
        pipeline = store.register_pipeline_reference("pipe-main",
                                                     actor=ANALYST)
        self.assertTrue(pipeline["reference_stub"])
        receipt = store.record_pipeline_receipt(
            pipeline["id"], "batch-2026-11-07", 500, actor=ANALYST
        )
        self.assertTrue(receipt["reference_stub"])
        self.assertTrue(receipt["reference_transport"])
        self.assertEqual(receipt["event_count"], 500)


class TestCrossCutting(unittest.TestCase):
    def test_address_shaped_refs_rejected(self):
        store = fresh()
        with self.assertRaises(ValidationError):
            store.register_enforcement_point(
                "10.0.0.1", "firewall", "scope-east", "policy-main",
                actor=ANALYST,
            )
        with self.assertRaises(ValidationError):
            store.register_enforcement_point(
                "plane-alpha", "firewall", "https://example.com/x",
                "policy-main", actor=ANALYST,
            )
        with self.assertRaises(ValidationError):
            store.register_enforcement_point(
                "plane-alpha", "firewall", "host.internal", "policy-main",
                actor=ANALYST,
            )

    def test_learner_ref_rejects_pii_shaped_values(self):
        store = fresh()
        campaign = store.create_campaign(
            "camp-1", "Q4 awareness", "audience-all", actor=ANALYST
        )
        with self.assertRaises(ValidationError):
            store.assign_training(campaign["id"], "jane.doe", actor=ANALYST)

    def test_denied_attempt_is_audited(self):
        audit = AuditLog()
        store = fresh(audit=audit)
        with self.assertRaises(PermissionDenied):
            store.register_enforcement_point(
                "plane-alpha", "firewall", "scope-east", "policy-main",
                actor=VIEWER,
            )
        actions = [entry["action"] for entry in audit.entries()]
        self.assertIn("plane_register:denied", actions)

    def test_extension_summary_counts_only(self):
        store = fresh()
        store.register_enforcement_point(
            "plane-alpha", "firewall", "scope-east", "policy-main",
            actor=ANALYST,
        )
        store.register_pipeline_reference("pipe-main", actor=ANALYST)
        summary = store.extension_summary(actor=VIEWER)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["records"]["planes"], 1)
        self.assertEqual(summary["records"]["pipelines"], 1)
        assert_counts_only(self, summary)


if __name__ == "__main__":
    unittest.main()
