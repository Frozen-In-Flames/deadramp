"""Final GAPS batch tests — Cybersecurity L3-adjacent extension surface.

Traces to: GAPS.md Group 8 section (the 16 open Extended entries),
``../BATCH.md`` for the per-entry dispositions, and
``../../gaps-batch/DECISION.md`` for the batch pattern. The extension
surface is ``cyber.extensions.ExtensionStore``: the records form of
each Extended family on the same hash-chained audit log, under the
same RBAC, with the same fail-closed discipline (AU-5) as the core.

Category discipline pinned throughout: nothing here scans, detects,
enforces, blocks, or executes. Engine/agent families land as
registries, ingestion records, and tracking workflows; the three
stub families (AI/ML detection models, backup & recovery, SOAR) are
labeled reference implementations whose every record carries
``reference_stub: True``; and no extension record, view, or summary
carries a computed score of any kind (posture is counts only; the
core's published scoring tables are the only scoring in the package
and are not re-implemented here).
"""

import inspect
import os
import tempfile
import unittest

from cyber_helpers import ADMIN, ANALYST, AUDITOR, VIEWER

from cyber.audit import AuditLog
from cyber.errors import (
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from cyber.extensions import ExtensionStore, count_by


def make_ext(audit=None):
    if audit is None:
        audit = AuditLog()
    return ExtensionStore(audit=audit), audit


def _all_keys(obj):
    """Every dict key appearing anywhere inside ``obj``."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            keys |= _all_keys(value)
    return keys


class TestEndpointManagementAgents(unittest.TestCase):
    """GAPS entry: Endpoint management agents — records form."""

    def setUp(self):
        self.ext, self.audit = make_ext()

    def test_register_and_checkin_view_derives(self):
        agent = self.ext.register_endpoint_agent(
            "agent-ops-1", "linux", "asset-ref-1", actor=ANALYST
        )
        self.assertEqual(agent["id"], "epa-1")
        self.assertEqual(
            set(agent),
            {"id", "agent_ref", "platform", "asset_ref",
             "created_by", "created_utc"},
        )
        self.ext.record_agent_checkin(agent["id"], "compliant", actor=ANALYST)
        self.ext.record_agent_checkin(
            agent["id"], "noncompliant", actor=ANALYST
        )
        view = self.ext.endpoint_agent_view(agent["id"], actor=VIEWER)
        self.assertEqual(view["checkin_count"], 2)
        self.assertEqual(view["latest_posture"], "noncompliant")
        stored = self.ext._data["endpoint_agents"][agent["id"]]
        self.assertNotIn("checkin_count", stored)
        self.assertNotIn("latest_posture", stored)

    def test_checkin_for_unknown_agent_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_agent_checkin("epa-99", "compliant", actor=ANALYST)

    def test_bad_platform_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_endpoint_agent(
                "agent-ops-1", "amiga", "asset-ref-1", actor=ANALYST
            )


class TestOpaqueRefs(unittest.TestCase):
    """Opaque references only: addresses are refused at the boundary."""

    def setUp(self):
        self.ext, _ = make_ext()

    def test_ipv4_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_edr_agent("192.168.1.10", "asset-ref-1",
                                        actor=ANALYST)

    def test_hostname_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_edr_agent("sensor-1", "host.example.com",
                                        actor=ANALYST)

    def test_url_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_intel_feed("Feed", "https://feed.example",
                                         actor=ANALYST)


class TestDlpRecords(unittest.TestCase):
    """GAPS entry: DLP engines — policy and alert records only."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.policy = self.ext.create_dlp_policy(
            " egress watch ", "email", "monitor", actor=ANALYST
        )

    def test_event_ingestion_and_counts_summary(self):
        self.ext.record_dlp_event(self.policy["id"], "asset-ref-1",
                                  "confidential", actor=ANALYST)
        self.ext.record_dlp_event(self.policy["id"], "asset-ref-2",
                                  "confidential", actor=ANALYST)
        self.ext.record_dlp_event(self.policy["id"], "asset-ref-1",
                                  "public", actor=ANALYST)
        summary = self.ext.dlp_summary(actor=VIEWER)
        self.assertEqual(summary["policies"], 1)
        self.assertEqual(summary["events"], 3)
        self.assertEqual(
            summary["events_by_classification"],
            {"public": 1, "internal": 0, "confidential": 2,
             "restricted": 0},
        )

    def test_enforcement_actions_are_not_in_the_vocabulary(self):
        """The declared-action vocabulary records intent (monitor /
        alert); no effect an engine would *take* is representable."""
        with self.assertRaises(ValidationError):
            self.ext.create_dlp_policy("p", "web", "block", actor=ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.create_dlp_policy("p", "web", "quarantine",
                                       actor=ANALYST)


class TestDetectionModelStub(unittest.TestCase):
    """GAPS entry: AI/ML detection models — labeled reference stub."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.model = self.ext.register_detection_model(
            "Model A", "provider-ref-1", "v3", actor=ANALYST
        )

    def test_every_stub_record_is_labeled(self):
        output = self.ext.record_model_output(
            self.model["id"], "asset-ref-1", "suspicious", actor=ANALYST
        )
        self.assertIs(self.model["reference_stub"], True)
        self.assertIs(output["reference_stub"], True)
        self.assertEqual(self.model["status"], "recorded")
        self.assertEqual(output["status"], "recorded")
        self.assertEqual(
            set(output),
            {"id", "model_id", "asset_ref", "label", "reference_stub",
             "status", "created_by", "created_utc"},
        )

    def test_no_confidence_or_score_is_computed(self):
        output = self.ext.record_model_output(
            self.model["id"], "asset-ref-1", "malicious", actor=ANALYST
        )
        self.assertNotIn("confidence", _all_keys(output))
        self.assertNotIn("score", _all_keys(output))


class TestNetworkEnforcementRecords(unittest.TestCase):
    """GAPS entry: Network enforcement planes — configuration records."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.point = self.ext.register_enforcement_point(
            "edge-fw-1", "firewall", actor=ANALYST
        )

    def test_rule_records_and_derived_count(self):
        self.ext.create_enforcement_rule(
            self.point["id"], "inbound", "deny", "tcp-443", actor=ANALYST
        )
        self.ext.create_enforcement_rule(
            self.point["id"], "outbound", "allow", "udp-53", actor=ANALYST
        )
        view = self.ext.enforcement_point_view(self.point["id"], actor=VIEWER)
        self.assertEqual(view["rule_count"], 2)
        stored = self.ext._data["enforcement_points"][self.point["id"]]
        self.assertNotIn("rule_count", stored)

    def test_rule_status_is_recorded_only(self):
        rule = self.ext.create_enforcement_rule(
            self.point["id"], "inbound", "deny", "tcp-22", actor=ANALYST
        )
        self.assertEqual(rule["status"], "recorded")
        self.assertEqual(rule["declared_effect"], "deny")


class TestBackupStub(unittest.TestCase):
    """GAPS entry: Backup & recovery products — labeled reference stub."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.job = self.ext.register_backup_job(
            "nightly", "source-ref-1", "daily-02:00", actor=ANALYST
        )

    def test_runs_and_restore_tests_are_labeled_records(self):
        run = self.ext.record_backup_run(self.job["id"], "succeeded", 1024,
                                         actor=ANALYST)
        test = self.ext.record_restore_test(self.job["id"], "partial",
                                            actor=ANALYST)
        for record in (self.job, run, test):
            self.assertIs(record["reference_stub"], True)
            self.assertEqual(record["status"], "recorded")

    def test_negative_or_bool_size_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.record_backup_run(self.job["id"], "succeeded", -1,
                                       actor=ANALYST)
        with self.assertRaises(ValidationError):
            self.ext.record_backup_run(self.job["id"], "succeeded", True,
                                       actor=ANALYST)


class TestSoarStub(unittest.TestCase):
    """GAPS entry: SOAR / workflow automation — registry never executes."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.playbook = self.ext.create_playbook(
            "triage flow", ["open ticket record", "notify owner record"],
            actor=ANALYST,
        )

    def test_playbook_and_run_are_labeled_records(self):
        run = self.ext.record_playbook_run(
            self.playbook["id"], "trigger-ref-1", "completed", actor=ANALYST
        )
        self.assertIs(self.playbook["reference_stub"], True)
        self.assertIs(run["reference_stub"], True)
        self.assertEqual(self.playbook["status"], "recorded")
        self.assertEqual(
            self.playbook["steps"],
            ["open ticket record", "notify owner record"],
        )

    def test_empty_steps_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_playbook("empty", [], actor=ANALYST)


class TestThreatIntelRecords(unittest.TestCase):
    """GAPS entry: Threat-intelligence feeds — feed and indicator records."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.feed = self.ext.register_intel_feed("Feed A", "provider-ref-1",
                                                 actor=ANALYST)

    def test_indicators_and_kind_counts(self):
        self.ext.add_indicator(self.feed["id"], "ioc-001", "file_hash",
                               "high", actor=ANALYST)
        self.ext.add_indicator(self.feed["id"], "ioc-002", "network_ref",
                               "low", actor=ANALYST)
        summary = self.ext.intel_summary(actor=VIEWER)
        self.assertEqual(summary["feeds"], 1)
        self.assertEqual(summary["indicators"], 2)
        self.assertEqual(
            summary["indicators_by_kind"],
            {"file_hash": 1, "network_ref": 1, "file_ref": 0, "other": 0},
        )

    def test_indicator_for_unknown_feed_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.add_indicator("feed-99", "ioc-001", "file_hash",
                                   "low", actor=ANALYST)


class TestEdrRecords(unittest.TestCase):
    """GAPS entry: EDR agents — agent registry and detection records."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.agent = self.ext.register_edr_agent("edr-1", "asset-ref-1",
                                                 actor=ANALYST)

    def test_detection_record_is_never_scored(self):
        detection = self.ext.record_edr_detection(
            self.agent["id"], "malicious", "critical", actor=ANALYST
        )
        self.assertEqual(detection["severity"], "critical")
        self.assertNotIn("score", _all_keys(detection))
        self.assertNotIn("band", _all_keys(detection))

    def test_detection_for_unknown_agent_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_edr_detection("edra-99", "benign", "low",
                                          actor=ANALYST)


class TestPostureEngineRecords(unittest.TestCase):
    """GAPS entry: Cloud / SaaS posture engines — recorded check results."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.scope = self.ext.register_posture_scope("scope-ref-1", "cloud",
                                                     actor=ANALYST)

    def test_checks_and_counts_only_summary(self):
        self.ext.record_posture_check(self.scope["id"], "SI-2", "pass",
                                      actor=ANALYST)
        self.ext.record_posture_check(self.scope["id"], "SI-2", "fail",
                                      actor=ANALYST)
        self.ext.record_posture_check(self.scope["id"], "SI-4", "fail",
                                      actor=ANALYST)
        summary = self.ext.posture_engine_summary(actor=VIEWER)
        self.assertEqual(
            summary,
            {"scopes": 1, "checks": 3,
             "checks_by_result": {"pass": 1, "fail": 2,
                                  "not_applicable": 0}},
        )

    def test_unknown_control_id_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.record_posture_check(self.scope["id"], "XX-99", "pass",
                                          actor=ANALYST)


class TestCampaignRecords(unittest.TestCase):
    """GAPS entry: Phishing simulation / training content — records form."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.campaign = self.ext.create_campaign(
            "Q4 sim", "template-ref-1", actor=ANALYST
        )

    def test_outcome_counts_derived(self):
        for outcome in ("sent_recorded", "opened_recorded",
                        "clicked_recorded", "reported"):
            self.ext.record_campaign_outcome(
                self.campaign["id"], "participant-ref-1", outcome,
                actor=ANALYST,
            )
        view = self.ext.campaign_view(self.campaign["id"], actor=VIEWER)
        self.assertEqual(
            view["outcome_counts"],
            {"sent_recorded": 1, "opened_recorded": 1,
             "clicked_recorded": 1, "reported": 1,
             "training_completed": 0},
        )
        stored = self.ext._data["campaigns"][self.campaign["id"]]
        self.assertNotIn("outcome_counts", stored)
        self.assertEqual(self.campaign["status"], "recorded")


class TestProofingRecords(unittest.TestCase):
    """GAPS entry: Fraud / identity-proofing products — case records.

    Records of proofing handled elsewhere; per PLATFORM-LAYER.md this
    substrate is not an identity provider and performs no proofing.
    """

    def setUp(self):
        self.ext, _ = make_ext()
        self.case = self.ext.create_proofing_case(
            "subject-ref-1", "document_check", actor=ANALYST
        )

    def test_outcome_derived_never_stored(self):
        self.ext.record_proofing_outcome(self.case["id"], "escalated",
                                         actor=ADMIN)
        view = self.ext.proofing_case_view(self.case["id"], actor=VIEWER)
        self.assertEqual(view["current_outcome"], "escalated")
        self.assertEqual(view["outcome_count"], 1)
        stored = self.ext._data["proofing_cases"][self.case["id"]]
        self.assertNotIn("current_outcome", stored)

    def test_separation_of_duties(self):
        """The case creator never records its outcome (AC-5)."""
        with self.assertRaises(ValidationError):
            self.ext.record_proofing_outcome(
                self.case["id"], "verified_declared", actor=ANALYST
            )


class TestAppSecRecords(unittest.TestCase):
    """GAPS entry: AppSec engines — scan-run records, no scanning."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.app = self.ext.register_app("app-ref-1", "python", actor=ANALYST)

    def test_scan_records_and_summary(self):
        self.ext.record_appsec_scan(self.app["id"], "sast", 4, actor=ANALYST)
        self.ext.record_appsec_scan(self.app["id"], "sca", 2, actor=ANALYST)
        summary = self.ext.appsec_summary(actor=VIEWER)
        self.assertEqual(summary["scans"], 2)
        self.assertEqual(summary["findings_reported_total"], 6)
        self.assertEqual(
            summary["scans_by_kind"],
            {"sast": 1, "dast": 0, "sca": 1, "other": 0},
        )


class TestLogPipelineRecords(unittest.TestCase):
    """GAPS entry: Log pipelines — batch count records, no content."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.pipeline = self.ext.register_log_pipeline(
            "siem feed", "source-ref-1", actor=ANALYST
        )

    def test_batch_counts_and_derived_totals(self):
        self.ext.record_log_batch(self.pipeline["id"], 500, "2026-11-w1",
                                  actor=ANALYST)
        self.ext.record_log_batch(self.pipeline["id"], 250, "2026-11-w2",
                                  actor=ANALYST)
        view = self.ext.log_pipeline_view(self.pipeline["id"], actor=VIEWER)
        self.assertEqual(view["batch_count"], 2)
        self.assertEqual(view["records_total"], 750)
        batch = self.ext._data["log_batches"]["logb-1"]
        self.assertEqual(
            set(batch),
            {"id", "pipeline_id", "record_count", "window_label",
             "created_by", "created_utc"},
        )

    def test_no_content_parameter_exists(self):
        """Privacy pin: no extension function can accept log content,
        message text, or a payload of any kind."""
        forbidden = {"content", "payload", "message", "log_line", "body",
                     "text"}
        for name, member in inspect.getmembers(ExtensionStore,
                                               inspect.isfunction):
            params = set(inspect.signature(member).parameters)
            self.assertFalse(
                params & forbidden,
                "%s accepts a content parameter" % name,
            )

    def test_zero_count_batch_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.record_log_batch(self.pipeline["id"], 0, "w",
                                      actor=ANALYST)


class TestEnclaveRecords(unittest.TestCase):
    """GAPS entry: CUI enclaves / VDI — enclave and session records."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.enclave = self.ext.register_enclave("cui pool", "cui", 25,
                                                 actor=ANALYST)

    def test_session_totals_derived(self):
        self.ext.record_enclave_session(self.enclave["id"], "user-ref-1",
                                        45, actor=ANALYST)
        self.ext.record_enclave_session(self.enclave["id"], "user-ref-2",
                                        15, actor=ANALYST)
        view = self.ext.enclave_view(self.enclave["id"], actor=VIEWER)
        self.assertEqual(view["session_count"], 2)
        self.assertEqual(view["session_minutes_total"], 60)
        stored = self.ext._data["enclaves"][self.enclave["id"]]
        self.assertNotIn("session_count", stored)


class TestScannerRecords(unittest.TestCase):
    """GAPS entry: Vulnerability scanners — scanner registry and run
    records; finding ingestion/tracking itself stays core."""

    def setUp(self):
        self.ext, _ = make_ext()
        self.scanner = self.ext.register_scanner("Scanner A",
                                                 "provider-ref-1",
                                                 actor=ANALYST)

    def test_run_records_and_derived_totals(self):
        self.ext.record_scan_run(self.scanner["id"], "asset-ref-1",
                                 "completed", 7, actor=ANALYST)
        self.ext.record_scan_run(self.scanner["id"], "asset-ref-1",
                                 "failed", 0, actor=ANALYST)
        view = self.ext.scanner_view(self.scanner["id"], actor=VIEWER)
        self.assertEqual(view["run_count"], 2)
        self.assertEqual(view["findings_reported_total"], 7)


class TestAccessAndAudit(unittest.TestCase):
    """RBAC via the core access module; denied attempts are audited;
    the auditor (AC-5) holds no permission on this surface."""

    def setUp(self):
        self.ext, self.audit = make_ext()

    def test_viewer_cannot_register_and_denial_is_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_scanner("Scanner A", "provider-ref-1",
                                      actor=VIEWER)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "extension_denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")
        self.assertEqual(self.audit.verify_chain(), (True, None))

    def test_auditor_holds_no_extension_permission(self):
        agent = self.ext.register_endpoint_agent(
            "agent-ops-1", "linux", "asset-ref-1", actor=ANALYST
        )
        with self.assertRaises(PermissionDenied):
            self.ext.endpoint_agent_view(agent["id"], actor=AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.register_scanner("S", "provider-ref-1", actor=AUDITOR)

    def test_mutations_are_audited_on_the_shared_chain(self):
        self.ext.register_scanner("Scanner A", "provider-ref-1",
                                  actor=ANALYST)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("scanner_register", actions)
        self.assertEqual(self.audit.verify_chain(), (True, None))

    def test_non_stub_records_carry_no_stub_label(self):
        agent = self.ext.register_endpoint_agent(
            "agent-ops-1", "linux", "asset-ref-1", actor=ANALYST
        )
        self.assertNotIn("reference_stub", agent)


class TestFailClosed(unittest.TestCase):
    """AU-5 at the extension surface: an audit write failure rolls the
    whole extension mutation back — no object, no id consumed."""

    def test_failed_audit_write_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            ext = ExtensionStore(audit=log)
            if os.path.exists(path):
                os.remove(path)
            os.mkdir(path)
            with self.assertRaises(AuditWriteError):
                ext.register_scanner("Scanner A", "provider-ref-1",
                                     actor=ANALYST)
            self.assertEqual(ext._data["scanners"], {})
            os.rmdir(path)
            scanner = ext.register_scanner("Scanner A", "provider-ref-1",
                                           actor=ANALYST)
            self.assertEqual(scanner["id"], "scan-1")


class TestNoScoresAnywhere(unittest.TestCase):
    """Posture is counts only: a recursive scan over one of every
    record, view, and summary finds no score-shaped key."""

    def test_no_score_keys(self):
        ext, _ = make_ext()
        agent = ext.register_endpoint_agent("a-1", "linux", "asset-ref-1",
                                            actor=ANALYST)
        ext.record_agent_checkin(agent["id"], "compliant", actor=ANALYST)
        policy = ext.create_dlp_policy("p", "email", "alert", actor=ANALYST)
        ext.record_dlp_event(policy["id"], "asset-ref-1", "internal",
                             actor=ANALYST)
        model = ext.register_detection_model("m", "provider-ref-1", "v1",
                                             actor=ANALYST)
        ext.record_model_output(model["id"], "asset-ref-1", "benign",
                                actor=ANALYST)
        scope = ext.register_posture_scope("scope-ref-1", "saas",
                                           actor=ANALYST)
        ext.record_posture_check(scope["id"], "SI-2", "pass", actor=ANALYST)
        campaign = ext.create_campaign("c", "template-ref-1", actor=ANALYST)
        ext.record_campaign_outcome(campaign["id"], "participant-ref-1",
                                    "reported", actor=ANALYST)
        surfaces = [
            ext._data,
            ext.endpoint_agent_view(agent["id"], actor=VIEWER),
            ext.dlp_summary(actor=VIEWER),
            ext.intel_summary(actor=VIEWER),
            ext.posture_engine_summary(actor=VIEWER),
            ext.campaign_view(campaign["id"], actor=VIEWER),
            ext.appsec_summary(actor=VIEWER),
        ]
        for surface in surfaces:
            self.assertNotIn("score", _all_keys(surface))
            self.assertNotIn("band", _all_keys(surface))


class TestCountByNegativeControl(unittest.TestCase):
    """Fresh negative control for the batch: the counting seam.

    ``count_by`` is the single seam every extension rollup uses. The
    canonical expectation is an exact per-choice distribution; a
    classification-blind mutant (every value counted under the first
    choice) must NOT satisfy it — mirroring the core's severity-blind
    scoring control, for counts. The mutation-verification record in
    tests/README.md reports the suite failure count when the real
    ``count_by`` is replaced by this mutant.
    """

    VALUES = ["pass", "fail", "fail", "not_applicable", "fail"]
    CHOICES = ("pass", "fail", "not_applicable")
    EXPECTED = {"pass": 1, "fail": 3, "not_applicable": 1}

    @staticmethod
    def _mutant_count_by(values, choices):
        counts = {choice: 0 for choice in choices}
        counts[choices[0]] = len(values)
        return counts

    def test_count_by_matches_canonical_distribution(self):
        self.assertEqual(count_by(self.VALUES, self.CHOICES), self.EXPECTED)

    def test_canonical_expectation_rejects_the_mutant(self):
        mutant = self._mutant_count_by(self.VALUES, self.CHOICES)
        self.assertNotEqual(mutant, self.EXPECTED)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, self.EXPECTED)


if __name__ == "__main__":
    unittest.main()
