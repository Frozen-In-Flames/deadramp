"""Final GAPS batch, Untiered Set 10 (idx 839-845): the
extension surface in ``sysadmin.extensions``.

Traces to: ``../BATCH.md`` for the per-entry disposition and
``../UNION-SPEC.md`` for the substrate these records extend.
Pins, per entry: the exact record shapes, the honesty labels
(reference stubs carry ``reference_stub: True`` and state
``recorded_reference_only``; built families carry their
``*_here: False`` labels and no stub label), derived-never-
stored derivations (case current state, a capacity pool's
latest observation), validation before mutation (failed
operations consume no id), the membership boundary and the
``:denied`` audit record, and -- recursively over every
extension record, view, and summary -- the tier-null scan (no
tier / CMMC / baseline key can exist on this surface) and the
core no-score scan.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import NotFoundError, PermissionDenied, ValidationError
from sysadmin.extensions import SysadminExtensions

# The core suite's forbidden set (test_store_validation.py),
# plus the tier-null additions: at tier null no key naming a
# tier, an equivalence, or a baseline may exist anywhere.
FORBIDDEN_KEYS = {"score", "rating", "health", "health_score", "posture",
                  "compliance", "compliance_score", "risk", "risk_score",
                  "grade", "severity_score", "sla_met",
                  "tier", "cmmc_tier", "cmmc", "baseline",
                  "fedramp_impact_level", "impact_level", "equivalence"}


def _scan(obj, path="$"):
    hits = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS or "tier" in key or "cmmc" in key \
                    or "baseline" in key:
                hits.append("%s.%s" % (path, key))
            hits.extend(_scan(value, "%s.%s" % (path, key)))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            hits.extend(_scan(value, "%s[%d]" % (path, i)))
    return hits


def make_ext():
    store, org = H.make_store()
    system = H.make_system(store, org)
    return store, org, SysadminExtensions(store), system


class TestObservabilityReference(unittest.TestCase):
    """idx 839 -- stub-engine, labeled reference implementation."""

    def setUp(self):
        self.store, self.org, self.ext, self.system = make_ext()

    def test_source_shape_and_stub_labels_pinned(self):
        source = self.ext.create_telemetry_source(
            H.MEMBER, self.org["id"], "TEL-1", "Metrics feed", "metrics")
        self.assertEqual(set(source), {
            "id", "org_id", "ref", "label", "source_kind",
            "reference_stub", "state", "observed_here", "sensed_here",
            "created_by", "created_utc"})
        self.assertEqual(source["id"], "obs-1")
        self.assertIs(source["reference_stub"], True)
        self.assertEqual(source["state"], "recorded_reference_only")
        self.assertIs(source["observed_here"], False)
        self.assertIs(source["sensed_here"], False)

    def test_report_shape_pinned_and_holds_no_payload(self):
        source = self.ext.create_telemetry_source(
            H.MEMBER, self.org["id"], "TEL-1", "Metrics feed", "metrics")
        report = self.ext.record_observation_report(
            H.MEMBER, self.org["id"], source["id"], "OBS-REF-1",
            "reported_nominal")
        self.assertEqual(set(report), {
            "id", "org_id", "source_id", "report_ref", "outcome_label",
            "reference_stub", "state", "observed_here", "sensed_here",
            "created_by", "created_utc"})
        self.assertIs(report["reference_stub"], True)
        with self.assertRaises(TypeError):
            self.ext.record_observation_report(
                H.MEMBER, self.org["id"], source["id"], "OBS-REF-2",
                "reported_nominal", payload="raw telemetry")

    def test_invalid_kind_rejected_and_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.create_telemetry_source(
                H.MEMBER, self.org["id"], "TEL-1", "Feed", "smoke_signals")
        source = self.ext.create_telemetry_source(
            H.MEMBER, self.org["id"], "TEL-1", "Feed", "logs")
        self.assertEqual(source["id"], "obs-1")

    def test_duplicate_ref_rejected(self):
        self.ext.create_telemetry_source(
            H.MEMBER, self.org["id"], "TEL-1", "Feed", "logs")
        with self.assertRaises(ValidationError):
            self.ext.create_telemetry_source(
                H.MEMBER, self.org["id"], "TEL-1", "Again", "traces")

    def test_cross_org_source_binding_rejected(self):
        other = H.make_org(self.store, ref="AGENCY-2", label="Agency Two")
        source = self.ext.create_telemetry_source(
            H.MEMBER, self.org["id"], "TEL-1", "Feed", "logs")
        with self.assertRaises(ValidationError):
            self.ext.record_observation_report(
                H.ADMIN, other["id"], source["id"], "OBS-1", "reported_x")

    def test_summary_counts(self):
        source = self.ext.create_telemetry_source(
            H.MEMBER, self.org["id"], "TEL-1", "Feed", "metrics")
        self.ext.record_observation_report(
            H.MEMBER, self.org["id"], source["id"], "O-1", "reported_nominal")
        self.ext.record_observation_report(
            H.MEMBER, self.org["id"], source["id"], "O-2", "reported_nominal")
        summary = self.ext.observability_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary["telemetry_sources"], 1)
        self.assertEqual(summary["telemetry_sources_by_kind"]["metrics"], 1)
        self.assertEqual(summary["observation_reports"], 2)
        self.assertEqual(
            summary["observation_reports_by_outcome"], {"reported_nominal": 2})


class TestAnalysisReports(unittest.TestCase):
    """idx 840 -- build-extension, prediction-records form."""

    def setUp(self):
        self.store, self.org, self.ext, self.system = make_ext()
        self.source = self.ext.create_telemetry_source(
            H.MEMBER, self.org["id"], "TEL-1", "Metrics feed", "metrics")

    def test_definition_shape_no_stub_label(self):
        definition = self.ext.create_analysis_definition(
            H.MEMBER, self.org["id"], "AN-1", "Causal analysis", "root_cause")
        self.assertEqual(set(definition), {
            "id", "org_id", "ref", "label", "analysis_kind",
            "inferred_here", "computed_here", "created_by", "created_utc"})
        self.assertNotIn("reference_stub", definition)
        self.assertIs(definition["inferred_here"], False)
        self.assertIs(definition["computed_here"], False)

    def test_report_binds_definition_and_source(self):
        definition = self.ext.create_analysis_definition(
            H.MEMBER, self.org["id"], "AN-1", "Causal analysis", "root_cause")
        report = self.ext.record_analysis_report(
            H.MEMBER, self.org["id"], definition["id"], self.source["id"],
            "RCA-REF-1", "cause_reported")
        self.assertEqual(set(report), {
            "id", "org_id", "definition_id", "source_id", "report_ref",
            "outcome_label", "inferred_here", "computed_here",
            "created_by", "created_utc"})
        self.assertIs(report["inferred_here"], False)
        self.assertIs(report["computed_here"], False)

    def test_no_confidence_or_content_can_be_supplied(self):
        definition = self.ext.create_analysis_definition(
            H.MEMBER, self.org["id"], "AN-1", "Forecast", "prediction")
        with self.assertRaises(TypeError):
            self.ext.record_analysis_report(
                H.MEMBER, self.org["id"], definition["id"],
                self.source["id"], "P-1", "spike_predicted", confidence=0.9)
        with self.assertRaises(TypeError):
            self.ext.record_analysis_report(
                H.MEMBER, self.org["id"], definition["id"],
                self.source["id"], "P-1", "spike_predicted",
                content="the cause was ...")

    def test_cross_org_definition_rejected(self):
        other = H.make_org(self.store, ref="AGENCY-2", label="Agency Two")
        definition = self.ext.create_analysis_definition(
            H.MEMBER, self.org["id"], "AN-1", "Causal", "root_cause")
        with self.assertRaises(ValidationError):
            self.ext.record_analysis_report(
                H.ADMIN, other["id"], definition["id"], self.source["id"],
                "R-1", "cause_reported")

    def test_summary_counts(self):
        definition = self.ext.create_analysis_definition(
            H.MEMBER, self.org["id"], "AN-1", "Causal", "root_cause")
        self.ext.record_analysis_report(
            H.MEMBER, self.org["id"], definition["id"], self.source["id"],
            "R-1", "cause_reported")
        summary = self.ext.analytics_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary["analysis_definitions"], 1)
        self.assertEqual(
            summary["analysis_definitions_by_kind"]["root_cause"], 1)
        self.assertEqual(summary["analysis_reports_by_outcome"],
                         {"cause_reported": 1})


class TestServiceCases(unittest.TestCase):
    """idx 841 -- build-extension: cases, links, alerting, rotations."""

    def setUp(self):
        self.store, self.org, self.ext, self.system = make_ext()

    def test_stored_case_shape_has_no_state_key(self):
        case = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "INC-1", "Mail relay down", "incident",
            system_id=self.system["id"])
        stored = self.ext._service_cases[case["id"]]
        self.assertEqual(set(stored), {
            "id", "org_id", "ref", "summary", "case_kind", "system_id",
            "created_by", "created_utc"})
        self.assertNotIn("state", stored)
        self.assertNotIn("current_state", stored)

    def test_current_state_derived_from_latest_label(self):
        case = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "INC-1", "Mail relay down", "incident")
        view = self.ext.get_service_case(H.MEMBER, case["id"])
        self.assertEqual(view["current_state"], "recorded")
        self.ext.record_case_state(
            H.MEMBER, self.org["id"], case["id"], "reported_open")
        self.ext.record_case_state(
            H.MEMBER, self.org["id"], case["id"], "reported_resolved")
        view = self.ext.get_service_case(H.MEMBER, case["id"])
        self.assertEqual(view["current_state"], "reported_resolved")
        stored = self.ext._service_cases[case["id"]]
        self.assertNotIn("current_state", stored)

    def test_invalid_state_label_rejected(self):
        case = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "INC-1", "Mail relay down", "incident")
        with self.assertRaises(ValidationError):
            self.ext.record_case_state(
                H.MEMBER, self.org["id"], case["id"], "closed_by_engine")

    def test_major_incident_coordination_link(self):
        major = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "MI-1", "Datacenter outage",
            "major_incident")
        case = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "INC-1", "Mail relay down", "incident")
        link = self.ext.link_service_case(
            H.MEMBER, self.org["id"], major["id"], case["id"])
        self.assertIs(link["coordinated_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.link_service_case(
                H.MEMBER, self.org["id"], major["id"], case["id"])
        with self.assertRaises(ValidationError):
            self.ext.link_service_case(
                H.MEMBER, self.org["id"], case["id"], major["id"])
        with self.assertRaises(ValidationError):
            self.ext.link_service_case(
                H.MEMBER, self.org["id"], major["id"], major["id"])

    def test_alert_policy_and_dispatch_forms(self):
        policy = self.ext.create_alert_policy(
            H.MEMBER, self.org["id"], "ALP-1", "Major incident alert",
            "major_incident_declared")
        self.assertIs(policy["executed_here"], False)
        self.assertIs(policy["dispatched_here"], False)
        case = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "MI-1", "Outage", "major_incident")
        dispatch = self.ext.record_alert_dispatch(
            H.MEMBER, self.org["id"], policy["id"], case["id"],
            "reported_paged")
        self.assertEqual(set(dispatch), {
            "id", "org_id", "policy_id", "case_id", "outcome_label",
            "reference_transport", "dispatched_here", "delivered_here",
            "created_by", "created_utc"})
        self.assertIs(dispatch["reference_transport"], True)
        self.assertIs(dispatch["dispatched_here"], False)
        self.assertIs(dispatch["delivered_here"], False)

    def test_oncall_rotation_is_a_definition(self):
        rotation = self.ext.create_oncall_rotation(
            H.MEMBER, self.org["id"], "OCR-1", "Primary rotation", "SCHED-9")
        self.assertIs(rotation["executed_here"], False)
        self.assertEqual(rotation["schedule_ref"], "SCHED-9")

    def test_itsm_summary_counts(self):
        major = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "MI-1", "Outage", "major_incident")
        case = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "INC-1", "Mail relay down", "incident")
        self.ext.record_case_state(
            H.MEMBER, self.org["id"], case["id"], "reported_open")
        self.ext.record_case_state(
            H.MEMBER, self.org["id"], case["id"], "reported_resolved")
        self.ext.link_service_case(
            H.MEMBER, self.org["id"], major["id"], case["id"])
        summary = self.ext.itsm_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary["service_cases"], 2)
        self.assertEqual(
            summary["service_cases_by_current_state"],
            {"recorded": 1, "reported_resolved": 1})
        self.assertEqual(summary["case_links"], 1)


class TestDiscovery(unittest.TestCase):
    """idx 842 -- build-extension: jobs, reported items, mapping, signals."""

    def setUp(self):
        self.store, self.org, self.ext, self.system = make_ext()
        self.job = self.ext.create_discovery_job(
            H.MEMBER, self.org["id"], "DCJ-1", "Nightly discovery", "SCOPE-A")

    def test_job_shape_and_flags(self):
        self.assertIs(self.job["discovered_here"], False)
        self.assertIs(self.job["scanned_here"], False)

    def test_item_is_reported_data(self):
        item = self.ext.record_inventory_item(
            H.MEMBER, self.org["id"], self.job["id"], "ITEM-1",
            "Directory service", "service")
        self.assertEqual(set(item), {
            "id", "org_id", "job_id", "item_ref", "label", "item_kind",
            "discovered_here", "created_by", "created_utc"})
        self.assertIs(item["discovered_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_inventory_item(
                H.MEMBER, self.org["id"], self.job["id"], "ITEM-1",
                "Duplicate", "device")
        with self.assertRaises(TypeError):
            self.ext.record_inventory_item(
                H.MEMBER, self.org["id"], self.job["id"], "ITEM-2",
                "Host", "device", ip_address="10.0.0.1")

    def test_relationship_mapping_and_self_rejection(self):
        a = self.ext.record_inventory_item(
            H.MEMBER, self.org["id"], self.job["id"], "ITEM-1", "App",
            "application")
        b = self.ext.record_inventory_item(
            H.MEMBER, self.org["id"], self.job["id"], "ITEM-2", "DB",
            "service")
        rel = self.ext.record_item_relationship(
            H.MEMBER, self.org["id"], a["id"], b["id"], "depends_on")
        self.assertEqual(rel["relationship_label"], "depends_on")
        with self.assertRaises(ValidationError):
            self.ext.record_item_relationship(
                H.MEMBER, self.org["id"], a["id"], a["id"], "depends_on")

    def test_signal_correlation_is_reported(self):
        s1 = self.ext.record_signal_report(
            H.MEMBER, self.org["id"], self.job["id"], "SIG-1",
            "reported_firing")
        s2 = self.ext.record_signal_report(
            H.MEMBER, self.org["id"], self.job["id"], "SIG-2",
            "reported_firing")
        self.assertIs(s1["correlated_here"], False)
        link = self.ext.record_signal_correlation(
            H.MEMBER, self.org["id"], s1["id"], s2["id"], "same_root_event")
        self.assertIs(link["correlated_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_signal_correlation(
                H.MEMBER, self.org["id"], s1["id"], s1["id"], "self")

    def test_discovery_summary_counts(self):
        item = self.ext.record_inventory_item(
            H.MEMBER, self.org["id"], self.job["id"], "ITEM-1", "App",
            "application")
        self.ext.record_signal_report(
            H.MEMBER, self.org["id"], self.job["id"], "SIG-1",
            "reported_firing")
        summary = self.ext.discovery_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary["discovery_jobs"], 1)
        self.assertEqual(summary["inventory_items"], 1)
        self.assertEqual(summary["inventory_items_by_kind"]["application"], 1)
        self.assertEqual(summary["signal_reports"], 1)


class TestEndpointOperations(unittest.TestCase):
    """idx 843 -- build-extension: endpoints, definitions, reported runs."""

    def setUp(self):
        self.store, self.org, self.ext, self.system = make_ext()
        self.endpoint = self.ext.create_endpoint_record(
            H.MEMBER, self.org["id"], "END-1", "Front-desk workstation")
        self.definition = self.ext.create_operation_definition(
            H.MEMBER, self.org["id"], "OP-1", "Monthly patch ring", "patch")

    def test_endpoint_shape_has_no_live_identifier_field(self):
        self.assertEqual(set(self.endpoint), {
            "id", "org_id", "endpoint_ref", "label", "created_by",
            "created_utc"})
        with self.assertRaises(TypeError):
            self.ext.create_endpoint_record(
                H.MEMBER, self.org["id"], "END-2", "Host",
                hostname="ws-01.example")

    def test_duplicate_endpoint_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.create_endpoint_record(
                H.MEMBER, self.org["id"], "END-1", "Again")

    def test_definition_is_data_never_executed(self):
        self.assertIs(self.definition["executed_here"], False)

    def test_run_records_reported_outcome_and_binds_core_change(self):
        change = H.make_change(self.store, self.org, self.system)
        before = self.store.get_change(H.MEMBER, change["id"])
        run = self.ext.record_operation_run(
            H.MEMBER, self.org["id"], self.definition["id"],
            self.endpoint["id"], "reported_applied", change_id=change["id"])
        self.assertEqual(set(run), {
            "id", "org_id", "definition_id", "endpoint_id", "change_id",
            "outcome_label", "executed_here", "created_by", "created_utc"})
        self.assertIs(run["executed_here"], False)
        # Patching rides Core's change records as records only:
        # recording the run modified no core record.
        after = self.store.get_change(H.MEMBER, change["id"])
        self.assertEqual(before, after)

    def test_run_with_unknown_change_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_operation_run(
                H.MEMBER, self.org["id"], self.definition["id"],
                self.endpoint["id"], "reported_applied",
                change_id="chg-999")

    def test_endpoint_summary_counts(self):
        self.ext.record_operation_run(
            H.MEMBER, self.org["id"], self.definition["id"],
            self.endpoint["id"], "reported_applied")
        summary = self.ext.endpoint_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary["endpoints"], 1)
        self.assertEqual(
            summary["operation_definitions_by_kind"]["patch"], 1)
        self.assertEqual(summary["operation_runs_by_outcome"],
                         {"reported_applied": 1})


class TestVulnerabilityReference(unittest.TestCase):
    """idx 844 -- stub-engine, labeled reference implementation."""

    def setUp(self):
        self.store, self.org, self.ext, self.system = make_ext()
        self.job = self.ext.create_scan_job(
            H.MEMBER, self.org["id"], "SCJ-1", "Weekly scan",
            self.system["id"])

    def test_scan_job_stub_labels_pinned(self):
        self.assertEqual(set(self.job), {
            "id", "org_id", "ref", "label", "system_id", "reference_stub",
            "state", "scanned_here", "detected_here", "created_by",
            "created_utc"})
        self.assertIs(self.job["reference_stub"], True)
        self.assertEqual(self.job["state"], "recorded_reference_only")
        self.assertIs(self.job["scanned_here"], False)
        self.assertIs(self.job["detected_here"], False)

    def test_finding_severity_is_a_verbatim_label(self):
        finding = self.ext.record_vulnerability_finding(
            H.MEMBER, self.org["id"], self.job["id"], "CVE-REF-1",
            "reported_critical")
        self.assertEqual(finding["severity_label"], "reported_critical")
        self.assertIs(finding["reference_stub"], True)
        self.assertIs(finding["detected_here"], False)

    def test_priority_is_the_engines_reported_label(self):
        finding = self.ext.record_vulnerability_finding(
            H.MEMBER, self.org["id"], self.job["id"], "CVE-REF-1",
            "reported_critical")
        priority = self.ext.record_remediation_priority(
            H.MEMBER, self.org["id"], finding["id"], "remediate_first")
        self.assertEqual(priority["priority_label"], "remediate_first")
        self.assertIs(priority["prioritized_here"], False)
        self.assertIs(priority["reference_stub"], True)
        with self.assertRaises(ValidationError):
            self.ext.record_remediation_priority(
                H.MEMBER, self.org["id"], finding["id"], "remediate_later")

    def test_vulnerability_summary_counts(self):
        finding = self.ext.record_vulnerability_finding(
            H.MEMBER, self.org["id"], self.job["id"], "CVE-REF-1",
            "reported_critical")
        self.ext.record_remediation_priority(
            H.MEMBER, self.org["id"], finding["id"], "remediate_first")
        summary = self.ext.vulnerability_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary["scan_jobs"], 1)
        self.assertEqual(summary["findings_by_severity_label"],
                         {"reported_critical": 1})
        self.assertEqual(summary["priorities_by_label"],
                         {"remediate_first": 1})


class TestCapacity(unittest.TestCase):
    """idx 845 -- build-extension: pools, observations, chargeback."""

    def setUp(self):
        self.store, self.org, self.ext, self.system = make_ext()
        self.pool = self.ext.create_capacity_pool(
            H.MEMBER, self.org["id"], "CAP-1", "Primary storage pool",
            system_id=self.system["id"])

    def test_observation_quantities_are_reported_data(self):
        obs = self.ext.record_capacity_observation(
            H.MEMBER, self.org["id"], self.pool["id"], 40, 100,
            "reported_within_capacity")
        self.assertEqual(obs["used_units"], 40)
        self.assertEqual(obs["total_units"], 100)
        self.assertIs(obs["measured_here"], False)

    def test_observation_rejects_floats_bools_and_overrun(self):
        with self.assertRaises(ValidationError):
            self.ext.record_capacity_observation(
                H.MEMBER, self.org["id"], self.pool["id"], 40.5, 100,
                "reported_x")
        with self.assertRaises(ValidationError):
            self.ext.record_capacity_observation(
                H.MEMBER, self.org["id"], self.pool["id"], True, 100,
                "reported_x")
        with self.assertRaises(ValidationError):
            self.ext.record_capacity_observation(
                H.MEMBER, self.org["id"], self.pool["id"], 101, 100,
                "reported_x")
        self.assertEqual(
            self.ext.list_capacity_observations(H.MEMBER, self.org["id"]),
            [])
        obs = self.ext.record_capacity_observation(
            H.MEMBER, self.org["id"], self.pool["id"], 40, 100,
            "reported_within_capacity")
        self.assertEqual(obs["id"], "cpo-1")

    def test_latest_observation_derived_at_read_never_stored(self):
        stored = self.ext._capacity_pools[self.pool["id"]]
        self.assertNotIn("latest_observation", stored)
        view = self.ext.get_capacity_pool(H.MEMBER, self.pool["id"])
        self.assertIsNone(view["latest_observation"])
        self.ext.record_capacity_observation(
            H.MEMBER, self.org["id"], self.pool["id"], 40, 100,
            "reported_within_capacity")
        self.ext.record_capacity_observation(
            H.MEMBER, self.org["id"], self.pool["id"], 85, 100,
            "reported_near_capacity")
        view = self.ext.get_capacity_pool(H.MEMBER, self.pool["id"])
        self.assertEqual(view["latest_observation"]["used_units"], 85)
        self.assertEqual(view["latest_observation"]["outcome_label"],
                         "reported_near_capacity")
        stored = self.ext._capacity_pools[self.pool["id"]]
        self.assertNotIn("latest_observation", stored)

    def test_recommendation_is_an_opaque_reference(self):
        rec = self.ext.record_optimization_recommendation(
            H.MEMBER, self.org["id"], self.pool["id"], "REC-REF-1",
            "rightsizing_reported")
        self.assertIs(rec["optimized_here"], False)
        with self.assertRaises(TypeError):
            self.ext.record_optimization_recommendation(
                H.MEMBER, self.org["id"], self.pool["id"], "REC-REF-2",
                "rightsizing_reported", new_size_units=50)

    def test_chargeback_amount_is_integer_cents_held_verbatim(self):
        report = self.ext.record_chargeback_report(
            H.MEMBER, self.org["id"], self.pool["id"], "2026-Q3", 125000,
            "CB-REF-1")
        self.assertEqual(report["amount_cents"], 125000)
        self.assertIs(report["computed_here"], False)
        self.assertIs(report["charged_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_chargeback_report(
                H.MEMBER, self.org["id"], self.pool["id"], "2026-Q4",
                1250.50, "CB-REF-2")
        with self.assertRaises(ValidationError):
            self.ext.record_chargeback_report(
                H.MEMBER, self.org["id"], self.pool["id"], "2026-Q4",
                -100, "CB-REF-2")

    def test_capacity_summary_is_counts_only(self):
        self.ext.record_capacity_observation(
            H.MEMBER, self.org["id"], self.pool["id"], 40, 100,
            "reported_within_capacity")
        self.ext.record_chargeback_report(
            H.MEMBER, self.org["id"], self.pool["id"], "2026-Q3", 125000,
            "CB-REF-1")
        summary = self.ext.capacity_summary(H.MEMBER, self.org["id"])
        self.assertEqual(summary, {
            "org_id": self.org["id"],
            "capacity_pools": 1,
            "capacity_observations": 1,
            "optimization_recommendations": 0,
            "chargeback_reports": 1})


class MutantExtensions(SysadminExtensions):
    """An extension whose current-state derivation reads the
    EARLIEST recorded label instead of the latest."""

    @staticmethod
    def _latest_state_label(state_records):
        if not state_records:
            return "recorded"
        return state_records[0]["state_label"]


def _case_fixture(ext, org):
    case = ext.create_service_case(
        H.MEMBER, org["id"], "INC-1", "Mail relay down", "incident")
    ext.record_case_state(H.MEMBER, org["id"], case["id"], "reported_open")
    ext.record_case_state(H.MEMBER, org["id"], case["id"],
                          "reported_resolved")
    return case


class TestLatestStateNegativeControl(unittest.TestCase):
    """Fresh negative control: latest-label derivation must be
    load-bearing. A case recorded open then resolved reads
    ``reported_resolved`` -- if the derivation read the earliest
    label, the superseded ``reported_open`` would resurrect."""

    def test_canonical_expectation(self):
        store, org, ext, system = make_ext()
        case = _case_fixture(ext, org)
        view = ext.get_service_case(H.MEMBER, case["id"])
        self.assertEqual(view["current_state"], "reported_resolved")

    def test_implementation_matches_canonical_in_summary(self):
        store, org, ext, system = make_ext()
        case = _case_fixture(ext, org)
        summary = ext.itsm_summary(H.MEMBER, org["id"])
        self.assertEqual(summary["service_cases_by_current_state"],
                         {"reported_resolved": 1})

    def test_mutant_would_resurrect_the_superseded_state(self):
        store, org = H.make_store()
        ext = MutantExtensions(store)
        case = _case_fixture(ext, org)
        view = ext.get_service_case(H.MEMBER, case["id"])
        self.assertEqual(view["current_state"], "reported_open")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["current_state"], "reported_resolved")


class TestCrossCutting(unittest.TestCase):
    """Tier-null scan, no-score scan, RBAC/audit discipline."""

    def setUp(self):
        self.store, self.org, self.ext, self.system = make_ext()

    def _one_of_everything(self):
        ext, org = self.ext, self.org
        source = ext.create_telemetry_source(
            H.MEMBER, org["id"], "TEL-1", "Feed", "metrics")
        records = [source]
        records.append(ext.record_observation_report(
            H.MEMBER, org["id"], source["id"], "O-1", "reported_nominal"))
        definition = ext.create_analysis_definition(
            H.MEMBER, org["id"], "AN-1", "Causal", "root_cause")
        records.append(definition)
        records.append(ext.record_analysis_report(
            H.MEMBER, org["id"], definition["id"], source["id"], "R-1",
            "cause_reported"))
        major = ext.create_service_case(
            H.MEMBER, org["id"], "MI-1", "Outage", "major_incident")
        case = ext.create_service_case(
            H.MEMBER, org["id"], "INC-1", "Mail relay down", "incident",
            system_id=self.system["id"])
        ext.record_case_state(H.MEMBER, org["id"], case["id"],
                              "reported_open")
        records.append(ext.get_service_case(H.MEMBER, case["id"]))
        records.append(ext.link_service_case(
            H.MEMBER, org["id"], major["id"], case["id"]))
        policy = ext.create_alert_policy(
            H.MEMBER, org["id"], "ALP-1", "Alert", "major_declared")
        records.append(policy)
        records.append(ext.record_alert_dispatch(
            H.MEMBER, org["id"], policy["id"], case["id"], "reported_paged"))
        records.append(ext.create_oncall_rotation(
            H.MEMBER, org["id"], "OCR-1", "Primary", "SCHED-9"))
        job = ext.create_discovery_job(
            H.MEMBER, org["id"], "DCJ-1", "Discovery", "SCOPE-A")
        records.append(job)
        item = ext.record_inventory_item(
            H.MEMBER, org["id"], job["id"], "ITEM-1", "App", "application")
        item2 = ext.record_inventory_item(
            H.MEMBER, org["id"], job["id"], "ITEM-2", "DB", "service")
        records.append(item)
        records.append(ext.record_item_relationship(
            H.MEMBER, org["id"], item["id"], item2["id"], "depends_on"))
        sig = ext.record_signal_report(
            H.MEMBER, org["id"], job["id"], "SIG-1", "reported_firing")
        sig2 = ext.record_signal_report(
            H.MEMBER, org["id"], job["id"], "SIG-2", "reported_firing")
        records.append(ext.record_signal_correlation(
            H.MEMBER, org["id"], sig["id"], sig2["id"], "same_root_event"))
        endpoint = ext.create_endpoint_record(
            H.MEMBER, org["id"], "END-1", "Workstation")
        records.append(endpoint)
        opdef = ext.create_operation_definition(
            H.MEMBER, org["id"], "OP-1", "Patch ring", "patch")
        records.append(opdef)
        records.append(ext.record_operation_run(
            H.MEMBER, org["id"], opdef["id"], endpoint["id"],
            "reported_applied"))
        scan = ext.create_scan_job(
            H.MEMBER, org["id"], "SCJ-1", "Weekly scan", self.system["id"])
        records.append(scan)
        finding = ext.record_vulnerability_finding(
            H.MEMBER, org["id"], scan["id"], "CVE-REF-1",
            "reported_critical")
        records.append(finding)
        records.append(ext.record_remediation_priority(
            H.MEMBER, org["id"], finding["id"], "remediate_first"))
        pool = ext.create_capacity_pool(
            H.MEMBER, org["id"], "CAP-1", "Pool", system_id=self.system["id"])
        ext.record_capacity_observation(
            H.MEMBER, org["id"], pool["id"], 40, 100,
            "reported_within_capacity")
        records.append(ext.get_capacity_pool(H.MEMBER, pool["id"]))
        records.append(ext.record_optimization_recommendation(
            H.MEMBER, org["id"], pool["id"], "REC-1", "rightsizing_reported"))
        records.append(ext.record_chargeback_report(
            H.MEMBER, org["id"], pool["id"], "2026-Q3", 125000, "CB-1"))
        records.extend([
            ext.observability_summary(H.MEMBER, org["id"]),
            ext.analytics_summary(H.MEMBER, org["id"]),
            ext.itsm_summary(H.MEMBER, org["id"]),
            ext.discovery_summary(H.MEMBER, org["id"]),
            ext.endpoint_summary(H.MEMBER, org["id"]),
            ext.vulnerability_summary(H.MEMBER, org["id"]),
            ext.capacity_summary(H.MEMBER, org["id"]),
        ])
        return records

    def test_tier_null_and_no_score_scan_over_whole_surface(self):
        for record in self._one_of_everything():
            self.assertEqual(_scan(record), [], record)

    def test_viewer_write_denied_and_audited_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_telemetry_source(
                H.VIEWER, self.org["id"], "TEL-1", "Feed", "metrics")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_telemetry_source_create:denied", actions)

    def test_outsider_denied_by_membership_boundary(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_service_case(
                H.OUTSIDER, self.org["id"], "INC-9", "Nope", "incident")
        with self.assertRaises(PermissionDenied):
            self.ext.itsm_summary(H.OUTSIDER, self.org["id"])

    def test_successful_mutations_audited_with_ext_prefix(self):
        self.ext.create_telemetry_source(
            H.MEMBER, self.org["id"], "TEL-1", "Feed", "metrics")
        actions = [e["action"] for e in self.store.audit.entries()
                   if e["action"].startswith("ext_")]
        self.assertEqual(actions, ["ext_telemetry_source_create"])

    def test_failed_create_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.create_service_case(
                H.MEMBER, self.org["id"], "INC-1", "Bad kind", "ticket")
        case = self.ext.create_service_case(
            H.MEMBER, self.org["id"], "INC-1", "Mail relay down", "incident")
        self.assertEqual(case["id"], "svc-1")


if __name__ == "__main__":
    unittest.main()
