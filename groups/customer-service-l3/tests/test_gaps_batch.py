"""Final GAPS batch tests -- Customer Service L3-adjacent singleton.

Pins the extension surface in ``custsvc/extensions.py`` for the 7
open entries of this group's GAPS.md section (see ``../BATCH.md``):

- the reference families' records carry ``reference_stub: True``
  and their not-here flags, and their reports store reported
  outcomes verbatim;
- the built families' stored records carry no derived key --
  remediation state and migration phase exist only as read-time
  derivations (exact stored key sets pinned);
- the monitoring surface creates no core alert and the incident
  surface leaves its core case byte-identical: the core's ingest
  paths remain the only ways core state comes to exist;
- RBAC rides the core matrix: the auditor role (audit_read only)
  is denied every operation on this surface, denials are audited
  with the ``:denied`` suffix, and every mutation lands on the
  core's hash-chained audit log, which still verifies;
- audit-before-commit (AU-5): a mutation whose audit write fails
  commits nothing and consumes no id;
- the privacy/score discipline: content-shaped arguments raise
  ``TypeError`` (no parameter on this surface can accept message
  text, a transcript, a body or a comment), and a recursive scan
  over every record and view finds no content- or score-shaped
  key and no float;
- the fresh negative control: the vulnerability remediation-state
  derivation is load-bearing (three-leg test -- canonical, mutant,
  mutant-as-expectation). The live drill is recorded in
  tests/README.md.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from custsvc.errors import (  # noqa: E402
    AuditWriteError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from custsvc.extensions import _VULNERABILITY_STATES, CustsvcExtensions  # noqa: E402

from custsvc_helpers import ADMIN, AGENT, AUDITOR, NOW, VIEWER, make_case, make_store  # noqa: E402


def make_ext(audit=None):
    store, audit, requester, rsp1, rsp2 = make_store(audit=audit)
    return CustsvcExtensions(store), store, audit, requester


class TestHostingEnvironments(unittest.TestCase):
    """Entry: virtualization & cloud hosting platform (reference)."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()

    def test_register_shape_and_labels(self):
        env = self.ext.register_hosting_environment("env-east-1", "paas", ADMIN)
        self.assertEqual(
            set(env),
            {"id", "environment_ref", "delivery_model", "reference_stub",
             "hosted_here", "state", "created_by", "created_utc"})
        self.assertEqual(env["id"], "env-1")
        self.assertIs(env["reference_stub"], True)
        self.assertIs(env["hosted_here"], False)
        self.assertEqual(env["state"], "recorded_reference_only")
        self.assertEqual(self.ext.get_hosting_environment("env-1", VIEWER), env)
        self.assertEqual(self.ext.list_hosting_environments(VIEWER), [env])

    def test_invalid_delivery_model_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.register_hosting_environment("env-x", "bare_metal", ADMIN)
        env = self.ext.register_hosting_environment("env-x", "iaas", ADMIN)
        self.assertEqual(env["id"], "env-1")

    def test_environment_report_flow(self):
        self.ext.register_hosting_environment("env-east-1", "saas", ADMIN)
        report = self.ext.record_environment_report(
            "env-1", "reported_degraded", AGENT)
        self.assertEqual(report["id"], "envr-1")
        self.assertIs(report["reported"], True)
        self.assertIs(report["operated_here"], False)
        self.assertEqual(
            self.ext.list_environment_reports("env-1", VIEWER), [report])

    def test_report_requires_existing_environment_and_known_outcome(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_environment_report("env-9", "reported_down", ADMIN)
        self.ext.register_hosting_environment("env-east-1", "saas", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_environment_report("env-1", "down", ADMIN)

    def test_viewer_cannot_register(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_hosting_environment("env-east-1", "paas", VIEWER)
        self.assertEqual(self.ext.list_hosting_environments(ADMIN), [])


class TestControlInheritance(unittest.TestCase):
    """Entry: authorization acceleration & control inheritance (reference)."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()

    def test_inheritance_shape_and_labels(self):
        inh = self.ext.record_control_inheritance(
            "customer-001", "NIST SP 800-53", ["AC-2", "AU-2"], ADMIN)
        self.assertEqual(
            set(inh),
            {"id", "customer_ref", "framework_label", "control_labels",
             "reference_stub", "assessed_here", "authorized_here", "state",
             "created_by", "created_utc"})
        self.assertIs(inh["assessed_here"], False)
        self.assertIs(inh["authorized_here"], False)
        self.assertEqual(inh["control_labels"], ["AC-2", "AU-2"])
        self.assertEqual(
            self.ext.list_control_inheritances(ADMIN, customer_ref="customer-001"),
            [inh])
        self.assertEqual(
            self.ext.list_control_inheritances(ADMIN, customer_ref="other"), [])

    def test_inheritance_requires_at_least_one_control_label(self):
        with self.assertRaises(ValidationError):
            self.ext.record_control_inheritance("c-1", "FW", [], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_control_inheritance("c-1", "FW", None, ADMIN)

    def test_assessment_report_flow(self):
        self.ext.record_control_inheritance("c-1", "FW", ["AC-2"], ADMIN)
        report = self.ext.record_assessment_report(
            "inh-1", "reported_completed_with_findings", AGENT,
            reuse_label="full_inheritance_reported")
        self.assertEqual(report["id"], "asr-1")
        self.assertEqual(report["outcome"], "reported_completed_with_findings")
        self.assertEqual(report["reuse_label"], "full_inheritance_reported")
        self.assertIs(report["assessed_here"], False)
        self.assertEqual(self.ext.list_assessment_reports("inh-1", VIEWER),
                         [report])

    def test_assessment_report_validation(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_assessment_report("inh-9", "reported_completed",
                                              ADMIN)
        self.ext.record_control_inheritance("c-1", "FW", ["AC-2"], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_assessment_report("inh-1", "passed", ADMIN)


class TestMonitoring(unittest.TestCase):
    """Entry: continuous monitoring & SOC operations (reference)."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()

    def test_source_shape_and_labels(self):
        mon = self.ext.register_monitoring_source("soc-feed-1", ADMIN)
        self.assertEqual(
            set(mon),
            {"id", "source_ref", "reference_stub", "monitors_here", "state",
             "created_by", "created_utc"})
        self.assertIs(mon["monitors_here"], False)
        self.assertEqual(self.ext.get_monitoring_source("mon-1", VIEWER), mon)

    def test_observation_flow_and_alert_link(self):
        case = make_case(self.store, self.requester)
        alert = self.store.ingest_alert("soc-feed-1", "Boundary sensor trip",
                                        "major", AGENT, case_id=case["id"])
        self.ext.register_monitoring_source("soc-feed-1", ADMIN)
        obs = self.ext.record_monitoring_observation(
            "mon-1", "reported_anomaly", AGENT, alert_id=alert["id"])
        self.assertEqual(obs["id"], "obs-1")
        self.assertEqual(obs["alert_id"], alert["id"])
        self.assertIs(obs["detected_here"], False)
        self.assertEqual(self.ext.list_monitoring_observations("mon-1", AGENT),
                         [obs])

    def test_observation_creates_no_core_alert(self):
        case = make_case(self.store, self.requester)
        alert = self.store.ingest_alert("soc-feed-1", "Boundary sensor trip",
                                        "major", AGENT, case_id=case["id"])
        before = self.store.list_alerts(ADMIN)
        self.ext.register_monitoring_source("soc-feed-1", ADMIN)
        self.ext.record_monitoring_observation("mon-1", "reported_nominal",
                                               AGENT)
        self.ext.record_monitoring_observation(
            "mon-1", "reported_outage", AGENT, alert_id=alert["id"])
        self.assertEqual(self.store.list_alerts(ADMIN), before)

    def test_observation_requires_existing_alert(self):
        self.ext.register_monitoring_source("soc-feed-1", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_monitoring_observation(
                "mon-1", "reported_anomaly", ADMIN, alert_id="alert-9")

    def test_observation_outcome_validated(self):
        self.ext.register_monitoring_source("soc-feed-1", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_monitoring_observation("mon-1", "anomaly", ADMIN)


class TestVulnerabilities(unittest.TestCase):
    """Entry: vulnerability management & patching operations (built)."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()

    def _register(self):
        return self.ext.register_vulnerability(
            "asset-7", "high", "scanner-1", ADMIN, cve_ref="CVE-2026-0001")

    def test_register_stored_shape_has_no_state(self):
        vuln = self._register()
        self.assertEqual(
            set(vuln),
            {"id", "asset_ref", "severity", "source_ref", "cve_ref",
             "scanned_here", "created_by", "created_utc"})
        self.assertIs(vuln["scanned_here"], False)
        stored = self.ext.get_vulnerability("vuln-1", ADMIN)
        self.assertNotIn("state", stored)
        self.assertEqual(stored, vuln)

    def test_register_validation(self):
        with self.assertRaises(ValidationError):
            self.ext.register_vulnerability("a", "severe", "s", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.register_vulnerability("a", 9.5, "s", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.register_vulnerability("", "high", "s", ADMIN)
        self.assertEqual(self.ext.list_vulnerabilities(ADMIN), [])

    def test_event_validation(self):
        self._register()
        with self.assertRaises(ValidationError):
            self.ext.record_vulnerability_event("vuln-1", "scan", "done",
                                                ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_vulnerability_event("vuln-1", "triage", "applied",
                                                ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_vulnerability_event("vuln-9", "triage",
                                                "confirmed", ADMIN)
        self.assertEqual(self.ext.list_vulnerability_events("vuln-1", ADMIN),
                         [])

    def test_state_derivation_walks_the_event_stream(self):
        vuln = self._register()
        view = self.ext.vulnerability_view("vuln-1", ADMIN)
        self.assertEqual(view["state"], "reported")
        self.assertEqual(view["event_count"], 0)
        self.ext.record_vulnerability_event("vuln-1", "triage", "confirmed",
                                            AGENT)
        self.assertEqual(
            self.ext.vulnerability_view("vuln-1", ADMIN)["state"], "triaged")
        self.ext.record_vulnerability_event("vuln-1", "patch_report",
                                            "applied", AGENT)
        self.assertEqual(
            self.ext.vulnerability_view("vuln-1", ADMIN)["state"],
            "remediation_reported")
        self.ext.record_vulnerability_event("vuln-1", "verification",
                                            "verified", AGENT)
        view = self.ext.vulnerability_view("vuln-1", ADMIN)
        self.assertEqual(view["state"], "verified_closed")
        self.assertEqual(view["event_count"], 3)
        self.assertIs(view["derived"], True)
        # The stored record still carries no state key.
        self.assertNotIn("state", self.ext.get_vulnerability("vuln-1", ADMIN))

    def test_reopen_and_risk_acceptance_paths(self):
        self._register()
        self.ext.record_vulnerability_event("vuln-1", "triage", "confirmed",
                                            ADMIN)
        self.ext.record_vulnerability_event("vuln-1", "verification",
                                            "still_present", ADMIN)
        self.assertEqual(
            self.ext.vulnerability_view("vuln-1", ADMIN)["state"], "reopened")
        other = self.ext.register_vulnerability("asset-8", "low", "scanner-1",
                                                ADMIN)
        self.ext.record_vulnerability_event(other["id"], "risk_acceptance",
                                            "accepted", ADMIN)
        self.assertEqual(
            self.ext.vulnerability_view(other["id"], ADMIN)["state"],
            "risk_accepted")

    def test_patch_campaign_flow(self):
        vuln = self._register()
        campaign = self.ext.create_patch_campaign(
            "October boundary patching", ADMIN, vulnerability_ids=["vuln-1"])
        self.assertEqual(
            set(campaign),
            {"id", "name", "vulnerability_ids", "applied_here", "created_by",
             "created_utc"})
        self.assertIs(campaign["applied_here"], False)
        report = self.ext.record_patch_report("patch-1", "reported_partial",
                                              AGENT)
        self.assertEqual(report["id"], "patchr-1")
        self.assertIs(report["applied_here"], False)
        self.assertEqual(self.ext.list_patch_reports("patch-1", VIEWER),
                         [report])
        self.assertEqual(vuln["id"], "vuln-1")

    def test_patch_campaign_validation(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_patch_campaign("X", ADMIN,
                                           vulnerability_ids=["vuln-9"])
        with self.assertRaises(ValidationError):
            self.ext.create_patch_campaign("X", ADMIN, vulnerability_ids=[])
        self._register()
        self.ext.create_patch_campaign("X", ADMIN,
                                       vulnerability_ids=["vuln-1"])
        with self.assertRaises(ValidationError):
            self.ext.record_patch_report("patch-1", "applied", ADMIN)

    def test_summary_counts_by_derived_state(self):
        self._register()
        self.ext.record_vulnerability_event("vuln-1", "triage", "confirmed",
                                            ADMIN)
        self.ext.record_vulnerability_event("vuln-1", "patch_report",
                                            "applied", ADMIN)
        self.ext.record_vulnerability_event("vuln-1", "verification",
                                            "verified", ADMIN)
        self.ext.register_vulnerability("asset-9", "critical", "scanner-2",
                                        ADMIN)
        self.ext.create_patch_campaign("C", ADMIN,
                                       vulnerability_ids=["vuln-1"])
        summary = self.ext.vulnerability_summary(ADMIN)
        self.assertEqual(summary["vulnerabilities"], 2)
        self.assertEqual(summary["by_severity"],
                         {"critical": 1, "high": 1, "medium": 0, "low": 0})
        self.assertEqual(summary["by_state"],
                         {"verified_closed": 1, "reported": 1})
        self.assertEqual(summary["events"], 3)
        self.assertEqual(summary["patch_campaigns"], 1)
        self.assertIs(summary["scanned_here"], False)
        self.assertIs(summary["applied_here"], False)


class TestIncidentResponses(unittest.TestCase):
    """Entry: incident response operations, hosting boundary (reference)."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()
        self.case = make_case(self.store, self.requester)

    def test_incident_shape_and_labels(self):
        inc = self.ext.record_incident_response(self.case["id"], AGENT)
        self.assertEqual(
            set(inc),
            {"id", "case_id", "alert_id", "reference_stub", "responded_here",
             "state", "created_by", "created_utc"})
        self.assertIs(inc["responded_here"], False)
        self.assertEqual(
            self.ext.list_incident_responses(ADMIN, case_id=self.case["id"]),
            [inc])
        self.assertEqual(
            self.ext.list_incident_responses(ADMIN, case_id="case-9"), [])

    def test_incident_requires_existing_case_and_alert(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_incident_response("case-9", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.record_incident_response(self.case["id"], ADMIN,
                                              alert_id="alert-9")
        alert = self.store.ingest_alert("soc-feed-1", "Boundary trip",
                                        "critical", AGENT,
                                        case_id=self.case["id"])
        inc = self.ext.record_incident_response(self.case["id"], ADMIN,
                                                alert_id=alert["id"])
        self.assertEqual(inc["alert_id"], alert["id"])

    def test_response_report_flow(self):
        self.ext.record_incident_response(self.case["id"], AGENT)
        report = self.ext.record_response_report("inc-1", "reported_contained",
                                                 AGENT)
        self.assertEqual(report["id"], "incr-1")
        self.assertIs(report["responded_here"], False)
        self.assertEqual(self.ext.list_response_reports("inc-1", VIEWER),
                         [report])
        with self.assertRaises(ValidationError):
            self.ext.record_response_report("inc-1", "contained", ADMIN)

    def test_incident_records_leave_core_case_untouched(self):
        before = self.store.get_case(self.case["id"], ADMIN, now=NOW)
        self.ext.record_incident_response(self.case["id"], AGENT)
        self.ext.record_response_report("inc-1", "reported_recovered", AGENT)
        after = self.store.get_case(self.case["id"], ADMIN, now=NOW)
        self.assertEqual(before, after)


class TestMigrations(unittest.TestCase):
    """Entry: migration & lift-and-shift services (built)."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()

    def test_project_stored_shape_has_no_phase(self):
        project = self.ext.create_migration_project(
            "legacy-app-1", "on_premises", "govcloud", ADMIN)
        self.assertEqual(
            set(project),
            {"id", "system_ref", "source_label", "target_label",
             "migrated_here", "created_by", "created_utc"})
        self.assertIs(project["migrated_here"], False)
        stored = self.ext.get_migration_project("mig-1", ADMIN)
        self.assertNotIn("phase", stored)
        self.assertNotIn("status", stored)

    def test_phase_derivation_walks_the_steps(self):
        self.ext.create_migration_project("legacy-app-1", "on_premises",
                                          "govcloud", ADMIN)
        view = self.ext.migration_view("mig-1", ADMIN)
        self.assertEqual(view["phase"], "registered")
        self.assertEqual(view["steps_recorded"], 0)
        self.assertIsNone(view["latest_step_outcome"])
        self.ext.record_migration_step("mig-1", "assessment",
                                       "reported_completed", AGENT)
        self.assertEqual(self.ext.migration_view("mig-1", ADMIN)["phase"],
                         "assessed")
        self.ext.record_migration_step("mig-1", "cutover", "reported_partial",
                                       AGENT)
        view = self.ext.migration_view("mig-1", ADMIN)
        self.assertEqual(view["phase"], "cutover_reported")
        self.assertEqual(view["latest_step_outcome"], "reported_partial")
        self.ext.record_migration_step("mig-1", "closure",
                                       "reported_completed", AGENT)
        self.assertEqual(self.ext.migration_view("mig-1", ADMIN)["phase"],
                         "closed")
        step = self.ext.list_migration_steps("mig-1", ADMIN)[0]
        self.assertIs(step["executed_here"], False)

    def test_step_validation(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_migration_step("mig-9", "assessment",
                                           "reported_completed", ADMIN)
        self.ext.create_migration_project("s-1", "a", "b", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_migration_step("mig-1", "lift", 
                                           "reported_completed", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_migration_step("mig-1", "assessment", "done",
                                           ADMIN)

    def test_summary_counts_by_derived_phase(self):
        self.ext.create_migration_project("s-1", "a", "b", ADMIN)
        self.ext.create_migration_project("s-2", "a", "b", ADMIN)
        self.ext.record_migration_step("mig-2", "planning",
                                       "reported_completed", ADMIN)
        summary = self.ext.migration_summary(ADMIN)
        self.assertEqual(summary["projects"], 2)
        self.assertEqual(summary["by_phase"],
                         {"registered": 1, "planned": 1})
        self.assertEqual(summary["steps"], 1)
        self.assertIs(summary["migrated_here"], False)


class TestHostedApplications(unittest.TestCase):
    """Entry: hosted third-party application ecosystem (reference,
    re-judged from build-extension -- see BATCH.md)."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()

    def test_register_shape_and_labels(self):
        app = self.ext.register_hosted_application(
            "app-forms-1", "Vendor A", "forms", ADMIN)
        self.assertEqual(
            set(app),
            {"id", "app_ref", "vendor_label", "category_label",
             "reference_stub", "hosted_here", "operated_here", "state",
             "created_by", "created_utc"})
        self.assertIs(app["reference_stub"], True)
        self.assertIs(app["hosted_here"], False)
        self.assertIs(app["operated_here"], False)
        self.assertEqual(self.ext.list_hosted_applications(VIEWER), [app])

    def test_hosting_report_flow(self):
        self.ext.register_hosted_application("app-forms-1", "Vendor A",
                                             "forms", ADMIN)
        report = self.ext.record_hosting_report("app-1", "reported_degraded",
                                                AGENT)
        self.assertEqual(report["id"], "appr-1")
        self.assertIs(report["hosted_here"], False)
        self.assertEqual(self.ext.list_hosting_reports("app-1", VIEWER),
                         [report])

    def test_hosting_report_validation(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_hosting_report("app-9", "reported_available",
                                           ADMIN)
        self.ext.register_hosted_application("app-1", "V", "forms", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_hosting_report("app-1", "up", ADMIN)


class TestAccessAndAudit(unittest.TestCase):
    """Cross-cutting: RBAC on the core matrix, the auditor role,
    denial auditing, the hash chain, and audit-before-commit."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()

    def test_auditor_denied_every_operation(self):
        self.ext.register_hosting_environment("env-1", "paas", ADMIN)
        with self.assertRaises(PermissionDenied):
            self.ext.register_hosting_environment("env-2", "paas", AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.get_hosting_environment("env-1", AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.list_hosting_environments(AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.vulnerability_summary(AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.record_monitoring_observation("mon-1",
                                                   "reported_nominal",
                                                   AUDITOR)

    def test_denied_attempt_is_audited_with_suffix(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_vulnerability("a-1", "high", "s-1", VIEWER)
        denied = [e for e in self.audit.entries()
                  if e["action"] == "ext_vulnerability_register:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")
        self.assertEqual(self.ext.list_vulnerabilities(ADMIN), [])

    def test_mutations_land_on_the_core_chain_and_it_verifies(self):
        self.ext.register_hosting_environment("env-1", "paas", ADMIN)
        self.ext.register_vulnerability("a-1", "high", "s-1", AGENT)
        self.ext.record_vulnerability_event("vuln-1", "triage", "confirmed",
                                            AGENT)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_hosting_environment_register", actions)
        self.assertIn("ext_vulnerability_register", actions)
        self.assertIn("ext_vulnerability_event", actions)
        queried = self.audit.query(action="ext_vulnerability_event")
        self.assertEqual(len(queried), 1)
        self.assertEqual(queried[0]["target"], "vulne-1")
        self.assertEqual(queried[0]["details"],
                         {"kind": "vulnerability_event"})
        self.assertEqual(self.audit.verify_chain(), (True, None))

    def test_audit_failure_rolls_back_record_and_id(self):
        original = self.audit.record

        def broken(*args, **kwargs):
            raise AuditWriteError("audit store unavailable")

        self.audit.record = broken
        try:
            with self.assertRaises(AuditWriteError):
                self.ext.register_hosting_environment("env-1", "paas", ADMIN)
            with self.assertRaises(AuditWriteError):
                self.ext.register_vulnerability("a-1", "high", "s-1", ADMIN)
        finally:
            self.audit.record = original
        self.assertEqual(self.ext.list_hosting_environments(ADMIN), [])
        self.assertEqual(self.ext.list_vulnerabilities(ADMIN), [])
        env = self.ext.register_hosting_environment("env-1", "paas", ADMIN)
        vuln = self.ext.register_vulnerability("a-1", "high", "s-1", ADMIN)
        self.assertEqual(env["id"], "env-1")
        self.assertEqual(vuln["id"], "vuln-1")
        self.assertEqual(self.audit.verify_chain(), (True, None))


_FORBIDDEN_KEY_PARTS = (
    "score", "rating", "sentiment", "intent", "csat",
    "transcript", "message", "content", "comment",
)


def _walk(value, path="root"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, key
            yield from _walk(item, path + "." + str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, "%s[%d]" % (path, index))


class TestPrivacyAndScoreScans(unittest.TestCase):
    """Cross-cutting: no content can be supplied, and no record or
    view carries a content- or score-shaped key or a float."""

    def setUp(self):
        self.ext, self.store, self.audit, self.requester = make_ext()
        self.case = make_case(self.store, self.requester)

    def test_content_shaped_arguments_raise_type_error(self):
        with self.assertRaises(TypeError):
            self.ext.register_hosting_environment(
                "env-1", "paas", ADMIN, transcript="hello")
        with self.assertRaises(TypeError):
            self.ext.record_control_inheritance(
                "c-1", "FW", ["AC-2"], ADMIN, score=5)
        with self.assertRaises(TypeError):
            self.ext.register_vulnerability(
                "a-1", "high", "s-1", ADMIN, body="text")
        with self.assertRaises(TypeError):
            self.ext.record_incident_response(
                self.case["id"], ADMIN, content="text")
        with self.assertRaises(TypeError):
            self.ext.create_migration_project(
                "s-1", "a", "b", ADMIN, comment="note")
        with self.assertRaises(TypeError):
            self.ext.record_monitoring_observation(
                "mon-1", "reported_nominal", ADMIN, message_text="hi")

    def _populated_surface(self):
        ext = self.ext
        ext.register_hosting_environment("env-1", "paas", ADMIN)
        ext.record_environment_report("env-1", "reported_operational", ADMIN)
        ext.record_control_inheritance("c-1", "FW", ["AC-2"], ADMIN)
        ext.record_assessment_report("inh-1", "reported_completed", ADMIN)
        ext.register_monitoring_source("soc-1", ADMIN)
        ext.record_monitoring_observation("mon-1", "reported_nominal", ADMIN)
        ext.register_vulnerability("a-1", "high", "s-1", ADMIN)
        ext.record_vulnerability_event("vuln-1", "triage", "confirmed",
                                       ADMIN)
        ext.create_patch_campaign("C", ADMIN, vulnerability_ids=["vuln-1"])
        ext.record_patch_report("patch-1", "reported_applied", ADMIN)
        ext.record_incident_response(self.case["id"], ADMIN)
        ext.record_response_report("inc-1", "reported_ongoing", ADMIN)
        ext.create_migration_project("s-1", "a", "b", ADMIN)
        ext.record_migration_step("mig-1", "assessment",
                                  "reported_completed", ADMIN)
        ext.register_hosted_application("app-1", "V", "forms", ADMIN)
        ext.record_hosting_report("app-1", "reported_available", ADMIN)
        surface = []
        surface += ext.list_hosting_environments(ADMIN)
        surface += ext.list_environment_reports("env-1", ADMIN)
        surface += ext.list_control_inheritances(ADMIN)
        surface += ext.list_assessment_reports("inh-1", ADMIN)
        surface += [ext.get_monitoring_source("mon-1", ADMIN)]
        surface += ext.list_monitoring_observations("mon-1", ADMIN)
        surface += ext.list_vulnerabilities(ADMIN)
        surface += ext.list_vulnerability_events("vuln-1", ADMIN)
        surface += [ext.vulnerability_view("vuln-1", ADMIN)]
        surface += ext.list_patch_campaigns(ADMIN)
        surface += ext.list_patch_reports("patch-1", ADMIN)
        surface += ext.list_incident_responses(ADMIN)
        surface += ext.list_response_reports("inc-1", ADMIN)
        surface += ext.list_migration_projects(ADMIN)
        surface += ext.list_migration_steps("mig-1", ADMIN)
        surface += [ext.migration_view("mig-1", ADMIN)]
        surface += ext.list_hosted_applications(ADMIN)
        surface += ext.list_hosting_reports("app-1", ADMIN)
        surface += [ext.vulnerability_summary(ADMIN),
                    ext.migration_summary(ADMIN)]
        return surface

    def test_no_content_or_score_key_and_no_float_anywhere(self):
        surface = self._populated_surface()
        self.assertTrue(surface)
        for record in surface:
            for path, key in _walk(record):
                for part in _FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(
                        part, str(key).lower(),
                        "%s key %r contains %r" % (path, key, part))
            self._assert_no_floats(record)

    def _assert_no_floats(self, value):
        if isinstance(value, dict):
            for item in value.values():
                self._assert_no_floats(item)
        elif isinstance(value, list):
            for item in value:
                self._assert_no_floats(item)
        else:
            self.assertNotIsInstance(value, float)


class FirstEventExtensions(CustsvcExtensions):
    """Mutant: remediation state derived from the FIRST event
    instead of the latest -- the in-suite form of the batch's
    fresh negative control."""

    def _derive_vulnerability_state(self, events):
        if not events:
            return "reported"
        first = events[0]
        return _VULNERABILITY_STATES[(first["kind"], first["outcome"])]


class TestNegativeControl(unittest.TestCase):
    """Three-leg control: the remediation-state derivation must be
    load-bearing. If the canonical walk passes under the mutant,
    the suite is testing that code ran, not that state is derived
    from the latest event."""

    def _walk(self, ext):
        vuln = ext.register_vulnerability("asset-1", "high", "scanner-1",
                                          ADMIN)
        ext.record_vulnerability_event(vuln["id"], "triage", "confirmed",
                                       ADMIN)
        ext.record_vulnerability_event(vuln["id"], "patch_report", "applied",
                                       ADMIN)
        ext.record_vulnerability_event(vuln["id"], "verification",
                                       "verified", ADMIN)
        return vuln["id"]

    def test_canonical_derives_from_latest_event(self):
        ext, store, audit, requester = make_ext()
        vuln_id = self._walk(ext)
        self.assertEqual(
            ext.vulnerability_view(vuln_id, ADMIN)["state"],
            "verified_closed")

    def test_mutant_derives_from_first_event(self):
        store, audit, requester, _, _ = make_store()
        ext = FirstEventExtensions(store)
        vuln_id = self._walk(ext)
        self.assertEqual(
            ext.vulnerability_view(vuln_id, ADMIN)["state"], "triaged")

    def test_mutant_as_expectation_fails(self):
        store, audit, requester, _, _ = make_store()
        ext = FirstEventExtensions(store)
        vuln_id = self._walk(ext)
        with self.assertRaises(AssertionError):
            self.assertEqual(
                ext.vulnerability_view(vuln_id, ADMIN)["state"],
                "verified_closed")


if __name__ == "__main__":
    unittest.main()
