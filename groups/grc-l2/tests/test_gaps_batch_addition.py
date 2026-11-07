"""Final-GAPS-batch extension surface, second unit — the
Remainder Addition section of the GRC L2 group.

Pins the records built in ``src/grc/extensions_addition.py``
for the seven Extended functions registered under the
**Remainder Addition — GRC L2 (+5 forks)** GAPS.md section
(inventory idx 571–577), per ``../../gaps-batch/DECISION.md``.
Every test traces to an entry in ``../BATCH-ADDITION.md``.

The category doctrine binds this surface exactly as it binds
the core and the first batch unit: posture is counts only and
no key mentioning score / rating / grade / percent exists
anywhere (recursive scan below); reported statuses, outcomes,
severities, priorities, and values are stored verbatim, never
computed; state and date-based figures are derived at read,
never stored.
"""

import unittest

from grc.audit import AuditLog
from grc.errors import NotFoundError, PermissionDenied, ValidationError
from grc.extensions_addition import GrcExtensionsAddition

from grc_helpers import (
    ADMIN,
    MEMBER,
    SEED_FRAMEWORK_ID,
    VIEWER,
    make_store,
)

FORBIDDEN_KEY_PARTS = ("score", "rating", "grade", "percent")


def assert_no_score_keys(case, node, path="$"):
    """Recursively assert no dict key anywhere in ``node``
    mentions score / rating / grade / percent (the category
    doctrine, as pinned by the founding posture suite)."""
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            for part in FORBIDDEN_KEY_PARTS:
                case.assertNotIn(part, lowered,
                                 "forbidden key part %r at %s" % (part, path))
            assert_no_score_keys(case, value, "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            assert_no_score_keys(case, value, "%s[%d]" % (path, index))


def make_addition():
    """A core store (canonical system + indicator) and its
    addition extension surface, sharing one audit log."""
    audit = AuditLog()
    store, _system, _indicator = make_store(audit=audit)
    return GrcExtensionsAddition(store), store, audit


def make_evidence(store, actor=MEMBER, name="policy document"):
    return store.create_evidence(
        name, "artifact-content", ["IA-2"], ["SYS-001"], actor=actor)


def make_assessment(store, actor=MEMBER):
    return store.create_assessment(
        "SYS-001", SEED_FRAMEWORK_ID, "full control baseline",
        "assessor-7", "2026-05-01", "satisfied, per assessor",
        actor=actor)


def drive_policy_to_approved(ext, lifecycle_id):
    """Record drafted -> in_review -> approved on a lifecycle
    registered by MEMBER (approval recorded by ADMIN, per the
    separation-of-duties rule)."""
    ext.record_policy_stage_event(lifecycle_id, "drafted", actor=MEMBER)
    ext.record_policy_stage_event(lifecycle_id, "in_review", actor=MEMBER)
    ext.record_policy_stage_event(lifecycle_id, "approved", actor=ADMIN)


class TestPolicyLifecycle(unittest.TestCase):
    """Entry idx 571 — policy lifecycle management engine:
    lifecycle records over the policy's Core records form, an
    append-only stage-event stream, the stage derived at read,
    and the filer-may-not-approve separation."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()

    def test_lifecycle_record_shape_and_labels(self):
        evidence = make_evidence(self.store)
        lifecycle = self.ext.create_policy_lifecycle(
            "evidence", evidence["id"], "Acceptable Use Policy",
            actor=MEMBER)
        self.assertEqual(lifecycle["id"], "plc-1")
        self.assertEqual(lifecycle["subject_kind"], "evidence")
        self.assertEqual(lifecycle["subject_ref"], evidence["id"])
        self.assertIs(lifecycle["authored_here"], False)
        self.assertIs(lifecycle["enforced_here"], False)
        self.assertEqual(lifecycle["recorded_by"], "bob")
        # No stage is stored on the record.
        self.assertNotIn("stage", lifecycle)
        self.assertNotIn("current_stage", lifecycle)
        framework_lifecycle = self.ext.create_policy_lifecycle(
            "framework", SEED_FRAMEWORK_ID, "Custom policy set",
            actor=ADMIN)
        self.assertEqual(framework_lifecycle["id"], "plc-2")
        self.assertEqual(framework_lifecycle["subject_kind"], "framework")

    def test_lifecycle_rejects_bad_subject_and_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.create_policy_lifecycle(
                "scroll", "x", "t", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_policy_lifecycle(
                "evidence", "ev-404", "t", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_policy_lifecycle(
                "framework", "NOPE", "t", actor=MEMBER)
        evidence = make_evidence(self.store)
        lifecycle = self.ext.create_policy_lifecycle(
            "evidence", evidence["id"], "ok", actor=MEMBER)
        self.assertEqual(lifecycle["id"], "plc-1")

    def test_stage_flow_derives_current_stage_at_read(self):
        evidence = make_evidence(self.store)
        lifecycle = self.ext.create_policy_lifecycle(
            "evidence", evidence["id"], "Access Control Policy",
            actor=MEMBER)
        view = self.ext.policy_lifecycle_view(lifecycle["id"], VIEWER)
        self.assertEqual(view["current_stage"], "registered")
        self.assertEqual(view["event_count"], 0)
        drive_policy_to_approved(self.ext, lifecycle["id"])
        view = self.ext.policy_lifecycle_view(lifecycle["id"], VIEWER)
        self.assertEqual(view["current_stage"], "approved")
        self.assertEqual(view["event_count"], 3)
        # The stored record still carries no stage.
        stored = self.ext.get_policy_lifecycle(lifecycle["id"], VIEWER)
        self.assertNotIn("current_stage", stored)
        self.assertNotIn("stage", stored)
        enforced = self.ext.record_policy_stage_event(
            lifecycle["id"], "enforcement_reported", actor=ADMIN,
            reported_outcome="Enforced by IdP policy push, per report")
        self.assertEqual(enforced["reported_outcome"],
                         "Enforced by IdP policy push, per report")
        self.assertIs(self.ext.get_policy_lifecycle(
            lifecycle["id"], VIEWER)["enforced_here"], False)
        view = self.ext.policy_lifecycle_view(lifecycle["id"], VIEWER)
        self.assertEqual(view["current_stage"], "enforcement_reported")

    def test_illegal_transition_rejected_and_consumes_no_id(self):
        evidence = make_evidence(self.store)
        lifecycle = self.ext.create_policy_lifecycle(
            "evidence", evidence["id"], "Incident Response Policy",
            actor=MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_policy_stage_event(
                lifecycle["id"], "approved", actor=ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_policy_stage_event(
                lifecycle["id"], "bogus", actor=MEMBER)
        event = self.ext.record_policy_stage_event(
            lifecycle["id"], "drafted", actor=MEMBER)
        self.assertEqual(event["id"], "pev-1")
        self.ext.record_policy_stage_event(
            lifecycle["id"], "in_review", actor=MEMBER)
        self.ext.record_policy_stage_event(
            lifecycle["id"], "rejected", actor=ADMIN)
        # A rejected policy may be redrafted, then retired; retired
        # is terminal.
        self.ext.record_policy_stage_event(
            lifecycle["id"], "drafted", actor=MEMBER)
        self.ext.record_policy_stage_event(
            lifecycle["id"], "retired", actor=MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_policy_stage_event(
                lifecycle["id"], "drafted", actor=MEMBER)
        view = self.ext.policy_lifecycle_view(lifecycle["id"], VIEWER)
        self.assertEqual(view["current_stage"], "retired")
        self.assertEqual(view["event_count"], 5)

    def test_approval_separation_of_duties(self):
        evidence = make_evidence(self.store)
        lifecycle = self.ext.create_policy_lifecycle(
            "evidence", evidence["id"], "Data Handling Policy",
            actor=MEMBER)
        self.ext.record_policy_stage_event(
            lifecycle["id"], "drafted", actor=MEMBER)
        self.ext.record_policy_stage_event(
            lifecycle["id"], "in_review", actor=MEMBER)
        # The actor who registered the lifecycle may not approve it.
        with self.assertRaises(PermissionDenied):
            self.ext.record_policy_stage_event(
                lifecycle["id"], "approved", actor=MEMBER)
        approved = self.ext.record_policy_stage_event(
            lifecycle["id"], "approved", actor=ADMIN)
        # The denied approval consumed no event id.
        self.assertEqual(approved["id"], "pev-3")


class TestPolicyStageDerivationNegativeControl(unittest.TestCase):
    """Fresh negative control for the new code: the policy
    stage derivation. The traced claim is that a lifecycle's
    current stage is the stage of its MOST RECENT stage event,
    derived at read — the mutant below reads the FIRST event
    instead, so a lifecycle that moved drafted -> in_review ->
    approved reads ``"drafted"`` under the mutant and
    ``"approved"`` under the real derivation."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()
        evidence = make_evidence(self.store)
        self.lifecycle = self.ext.create_policy_lifecycle(
            "evidence", evidence["id"], "Audit Policy", actor=MEMBER)
        drive_policy_to_approved(self.ext, self.lifecycle["id"])

    @staticmethod
    def _first_event_mutant(events):
        """Never-derive mutant: the stage of the FIRST event."""
        if not events:
            return "registered"
        return events[0]["stage"]

    def _events(self):
        return self.ext.list_policy_stage_events(
            VIEWER, lifecycle_id=self.lifecycle["id"])

    def test_real_derivation_separates_the_canonical_pair(self):
        events = self._events()
        self.assertEqual(
            GrcExtensionsAddition._derive_policy_stage(events), "approved")
        self.assertEqual(
            self.ext.policy_lifecycle_view(
                self.lifecycle["id"], VIEWER)["current_stage"],
            "approved")
        self.assertEqual(
            GrcExtensionsAddition._derive_policy_stage([]), "registered")

    def test_mutant_collapses_to_the_first_event(self):
        self.assertEqual(self._first_event_mutant(self._events()), "drafted")
        self.assertEqual(self._first_event_mutant([]), "registered")

    def test_mutant_output_as_expectation_fails(self):
        mutant_stage = self._first_event_mutant(self._events())
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_stage, "approved")


class TestAgentDefinitionsRunsReports(unittest.TestCase):
    """Entry idx 572 — agentic workflow execution engine:
    definitions as data and run/report records; nothing
    executes."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()

    def test_definition_run_and_report_flow(self):
        definition = self.ext.register_agent_definition(
            "evidence-chaser", "SYS-001", "evidence collection workflow",
            actor=MEMBER)
        self.assertEqual(definition["id"], "agt-1")
        self.assertIs(definition["reference_stub"], True)
        self.assertIs(definition["executed_here"], False)
        run = self.ext.create_agent_run(definition["id"], actor=MEMBER)
        self.assertEqual(run["id"], "arun-1")
        self.assertEqual(run["system_ref"], "SYS-001")
        self.assertIs(run["executed_here"], False)
        report = self.ext.record_agent_run_report(
            run["id"], "Completed with 2 exceptions, per agent log",
            actor=MEMBER)
        self.assertEqual(report["id"], "arep-1")
        self.assertEqual(report["reported_status"],
                         "Completed with 2 exceptions, per agent log")
        self.assertEqual(
            self.ext.list_agent_run_reports(VIEWER, run_id=run["id"]),
            [report])

    def test_run_and_report_change_no_core_record(self):
        posture_before = self.store.posture_summary(ADMIN)
        definition = self.ext.register_agent_definition(
            "control-mapper", "SYS-001", "control mapping", actor=MEMBER)
        run = self.ext.create_agent_run(definition["id"], actor=MEMBER)
        self.ext.record_agent_run_report(
            run["id"], "mapped 21 controls, per agent", actor=MEMBER)
        self.assertEqual(self.store.posture_summary(ADMIN), posture_before)
        self.assertEqual(self.store.list_findings(VIEWER), [])
        self.assertEqual(self.store.list_assessments(VIEWER), [])
        self.assertEqual(self.store.list_indicator_results(VIEWER), [])

    def test_agent_rejects_unknown_system_and_run(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_agent_definition(
                "x", "SYS-404", "w", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_agent_run("agt-404", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_agent_run_report(
                "arun-404", "done", actor=MEMBER)
        definition = self.ext.register_agent_definition(
            "ok", "SYS-001", "w", actor=MEMBER)
        self.assertEqual(definition["id"], "agt-1")


class TestGenerationRequestsReports(unittest.TestCase):
    """Entry idx 573 — AI control-narrative & assessment-response
    generation / secure AI enclave: request and report records;
    no text is generated or held here, and a report never
    changes the core assessment."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()
        self.assessment = make_assessment(self.store)

    def test_request_shape_labels_and_assessment_link(self):
        request = self.ext.create_generation_request(
            self.assessment["id"], "control_narrative", "Kovr enclave",
            actor=MEMBER)
        self.assertEqual(request["id"], "gen-1")
        self.assertEqual(request["assessment_id"], self.assessment["id"])
        self.assertEqual(request["system_ref"], "SYS-001")
        self.assertEqual(request["enclave_label"], "Kovr enclave")
        self.assertIs(request["reference_stub"], True)
        self.assertIs(request["generated_here"], False)

    def test_request_rejects_bad_kind_and_unknown_assessment(self):
        with self.assertRaises(ValidationError):
            self.ext.create_generation_request(
                self.assessment["id"], "poem", "enclave", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_generation_request(
                "asmt-404", "control_narrative", "enclave", actor=MEMBER)
        request = self.ext.create_generation_request(
            self.assessment["id"], "assessment_response", "enclave",
            actor=MEMBER)
        self.assertEqual(request["id"], "gen-1")

    def test_report_records_filing_reference_and_changes_no_core(self):
        assessment_before = self.store.get_assessment(
            self.assessment["id"], ADMIN)
        evidence = make_evidence(self.store, name="filed narrative")
        request = self.ext.create_generation_request(
            self.assessment["id"], "control_narrative", "Kovr enclave",
            actor=MEMBER)
        report = self.ext.record_generation_report(
            request["id"], "Generated and filed, per engine",
            filed_evidence_id=evidence["id"], actor=MEMBER)
        self.assertEqual(report["id"], "gnr-1")
        self.assertEqual(report["filed_evidence_id"], evidence["id"])
        self.assertEqual(report["reported_status"],
                         "Generated and filed, per engine")
        # The core assessment is byte-identical and no new core
        # evidence was created by the report.
        self.assertEqual(
            self.store.get_assessment(self.assessment["id"], ADMIN),
            assessment_before)
        self.assertEqual(len(self.store.list_evidence(VIEWER)), 1)

    def test_report_rejects_unknown_filed_evidence(self):
        request = self.ext.create_generation_request(
            self.assessment["id"], "control_narrative", "enclave",
            actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_generation_report(
                request["id"], "filed", filed_evidence_id="ev-404",
                actor=MEMBER)
        report = self.ext.record_generation_report(
            request["id"], "filed elsewhere, per engine", actor=MEMBER)
        self.assertEqual(report["id"], "gnr-1")
        self.assertIsNone(report["filed_evidence_id"])


class TestConnectorsAndReceipts(unittest.TestCase):
    """Entry idx 574 — data-integration connector engine:
    connector definitions and sync receipts; a receipt imports
    nothing."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()

    def test_connector_shape_and_labels(self):
        connector = self.ext.register_connector(
            "system_sync", "SYS-001", "agency IS sync", actor=MEMBER)
        self.assertEqual(connector["id"], "con-1")
        self.assertIs(connector["reference_stub"], True)
        self.assertIs(connector["reference_transport"], True)
        self.assertIs(connector["connected_here"], False)
        self.assertIs(connector["synced_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_connector(
                "carrier-pigeon", "SYS-001", "x", actor=MEMBER)

    def test_receipt_records_reported_count_verbatim(self):
        connector = self.ext.register_connector(
            "data_import", "SYS-001", "GRC data import", actor=MEMBER)
        receipt = self.ext.record_sync_receipt(
            connector["id"], "Sync OK, per connector",
            records_reported=42, actor=MEMBER)
        self.assertEqual(receipt["id"], "syn-1")
        self.assertEqual(receipt["reported_status"], "Sync OK, per connector")
        self.assertEqual(receipt["records_reported"], 42)
        self.assertEqual(receipt["system_ref"], "SYS-001")

    def test_receipt_rejects_non_integer_counts(self):
        connector = self.ext.register_connector(
            "system_sync", "SYS-001", "sync", actor=MEMBER)
        for bad in (True, 1.5, -1, "42"):
            with self.assertRaises(ValidationError):
                self.ext.record_sync_receipt(
                    connector["id"], "ok", records_reported=bad,
                    actor=MEMBER)
        receipt = self.ext.record_sync_receipt(
            connector["id"], "ok", records_reported=0, actor=MEMBER)
        self.assertEqual(receipt["id"], "syn-1")

    def test_receipt_imports_no_core_records(self):
        before = {
            "systems": len(self.store.list_systems(VIEWER)),
            "evidence": len(self.store.list_evidence(VIEWER)),
            "findings": len(self.store.list_findings(VIEWER)),
            "results": len(self.store.list_indicator_results(VIEWER)),
        }
        connector = self.ext.register_connector(
            "data_export", "SYS-001", "export", actor=MEMBER)
        self.ext.record_sync_receipt(
            connector["id"], "exported 500 records, per connector",
            records_reported=500, actor=MEMBER)
        after = {
            "systems": len(self.store.list_systems(VIEWER)),
            "evidence": len(self.store.list_evidence(VIEWER)),
            "findings": len(self.store.list_findings(VIEWER)),
            "results": len(self.store.list_indicator_results(VIEWER)),
        }
        self.assertEqual(before, after)


class TestConfigItemsTicketsSla(unittest.TestCase):
    """Entry idx 575 — ITSM / ESM suite incl. CMDB / SLA:
    configuration-item records, ticket records whose status is
    derived at read, and SLA policies held as data."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()

    def test_config_item_shape_duplicate_and_labels(self):
        item = self.ext.register_config_item(
            "CI-DB-01", "primary database", "database",
            system_ref="SYS-001", actor=MEMBER)
        self.assertEqual(item["id"], "ci-1")
        self.assertEqual(item["ref"], "CI-DB-01")
        self.assertIs(item["discovered_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_config_item(
                "CI-DB-01", "dupe", "database", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.register_config_item(
                "CI-X", "x", "server", system_ref="SYS-404", actor=MEMBER)
        second = self.ext.register_config_item(
            "CI-WEB-01", "web tier", "server", actor=MEMBER)
        self.assertEqual(second["id"], "ci-2")
        self.assertIsNone(second["system_ref"])

    def test_ticket_status_derived_at_read_never_stored(self):
        ticket = self.ext.create_ticket(
            "incident", "portal outage", reported_priority="P1, per desk",
            actor=MEMBER)
        self.assertEqual(ticket["id"], "tkt-1")
        self.assertNotIn("status", ticket)
        self.assertNotIn("current_status", ticket)
        view = self.ext.ticket_view(ticket["id"], VIEWER)
        self.assertEqual(view["current_status"], "recorded")
        self.assertEqual(view["event_count"], 0)
        self.ext.record_ticket_event(
            ticket["id"], "In Progress", actor=MEMBER)
        self.ext.record_ticket_event(
            ticket["id"], "Resolved, per desk", actor=MEMBER)
        view = self.ext.ticket_view(ticket["id"], VIEWER)
        self.assertEqual(view["current_status"], "Resolved, per desk")
        self.assertEqual(view["event_count"], 2)
        stored = self.ext.get_ticket(ticket["id"], VIEWER)
        self.assertNotIn("current_status", stored)
        self.assertEqual(stored["reported_priority"], "P1, per desk")

    def test_ticket_rejects_bad_kind_and_unknown_links(self):
        with self.assertRaises(ValidationError):
            self.ext.create_ticket("chore", "x", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_ticket(
                "change", "x", ci_id="ci-404", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_ticket_event("tkt-404", "Open", actor=MEMBER)

    def test_sla_policy_held_as_data(self):
        policy = self.ext.register_sla_policy(
            "gold response", "Respond within 4 business hours, as reported",
            ticket_kind="incident", actor=MEMBER)
        self.assertEqual(policy["id"], "sla-1")
        self.assertEqual(policy["terms_label"],
                         "Respond within 4 business hours, as reported")
        self.assertIs(policy["evaluated_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_sla_policy(
                "bad", "terms", ticket_kind="chore", actor=MEMBER)


class TestHealthcareQuality(unittest.TestCase):
    """Entry idx 576 — healthcare quality management suite:
    personnel records by opaque reference, certification
    records with currency derived at read, and verbatim
    training / quality-event / maintenance records."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()
        self.personnel = self.ext.register_personnel(
            "EMP-0042", "lab technician", actor=MEMBER)

    def test_personnel_shape_and_duplicate(self):
        self.assertEqual(self.personnel["id"], "per-1")
        self.assertEqual(self.personnel["person_ref"], "EMP-0042")
        self.assertEqual(
            set(self.personnel),
            {"id", "person_ref", "role_label", "note", "recorded_by",
             "recorded_utc"})
        with self.assertRaises(ValidationError):
            self.ext.register_personnel("EMP-0042", "dupe", actor=MEMBER)

    def test_certification_currency_derived_at_read(self):
        cert = self.ext.record_certification(
            self.personnel["id"], "Certified Lab Technician",
            "State Board", "2027-06-30", actor=MEMBER)
        self.assertEqual(cert["id"], "crt-1")
        self.assertIs(cert["assessed_here"], False)
        self.assertNotIn("currency", cert)
        self.assertEqual(
            self.ext.certification_view(
                cert["id"], VIEWER, as_of="2027-06-30")["currency"],
            "current")
        self.assertEqual(
            self.ext.certification_view(
                cert["id"], VIEWER, as_of="2027-07-01")["currency"],
            "expired")
        with self.assertRaises(ValidationError):
            self.ext.record_certification(
                self.personnel["id"], "x", "y", "June 30, 2027",
                actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_certification(
                "per-404", "x", "y", "2027-01-01", actor=MEMBER)

    def test_training_quality_and_maintenance_records(self):
        training = self.ext.record_training(
            self.personnel["id"], "HIPAA refresher 2026",
            "Completed, per LMS", actor=MEMBER)
        self.assertEqual(training["id"], "trn-1")
        self.assertEqual(training["reported_outcome"], "Completed, per LMS")
        self.assertIs(training["assessed_here"], False)
        event = self.ext.record_quality_event(
            "non-conforming event", "mislabeled sample batch",
            reported_severity="Moderate, per reporter",
            personnel_id=self.personnel["id"], actor=MEMBER)
        self.assertEqual(event["id"], "qev-1")
        self.assertEqual(event["reported_severity"], "Moderate, per reporter")
        action = self.ext.record_corrective_action(
            event["id"], "Batch re-labeled and re-verified, per owner",
            actor=MEMBER)
        self.assertEqual(action["id"], "cor-1")
        maintenance = self.ext.record_maintenance(
            "INST-7", "centrifuge calibration",
            "Calibrated, within tolerance, per technician",
            performed_on="2026-10-15", actor=MEMBER)
        self.assertEqual(maintenance["id"], "mnt-1")
        self.assertEqual(maintenance["performed_on"], "2026-10-15")
        with self.assertRaises(ValidationError):
            self.ext.record_maintenance(
                "INST-7", "x", "y", performed_on="last Tuesday",
                actor=MEMBER)


class TestConnectedReporting(unittest.TestCase):
    """Entry idx 577 — connected financial & regulatory
    reporting / publishing platform: report records, data
    points holding reported values verbatim as labels, and
    publication records; counts of records only."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()

    def _report(self):
        return self.ext.create_report(
            "SYS-001", SEED_FRAMEWORK_ID, "FY2026 Q3",
            "Quarterly regulatory filing", actor=MEMBER)

    def test_report_shape_and_labels(self):
        report = self._report()
        self.assertEqual(report["id"], "rpt-1")
        self.assertEqual(report["period_label"], "FY2026 Q3")
        self.assertIs(report["filed_here"], False)
        self.assertIs(report["published_here"], False)
        self.assertNotIn("data_point_count", report)
        with self.assertRaises(NotFoundError):
            self.ext.create_report(
                "SYS-001", "NOPE", "FY2026", "x", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_report(
                "SYS-404", SEED_FRAMEWORK_ID, "FY2026", "x", actor=MEMBER)

    def test_data_points_verbatim_and_view_counts(self):
        report = self._report()
        point = self.ext.record_data_point(
            report["id"], "general-ledger extract", "1,234,567 (as reported)",
            actor=MEMBER)
        self.assertEqual(point["id"], "dpt-1")
        self.assertEqual(point["value_label"], "1,234,567 (as reported)")
        self.assertIs(point["computed_here"], False)
        view = self.ext.report_view(report["id"], VIEWER)
        self.assertEqual(view["data_point_count"], 1)
        self.assertEqual(view["publication_count"], 0)
        self.ext.record_data_point(
            report["id"], "general-ledger extract", "88 (as reported)",
            actor=MEMBER)
        self.ext.record_data_point(
            report["id"], "tax workbook", "filed value, per preparer",
            actor=MEMBER)
        # The view tracks registry state; the stored record does not.
        view = self.ext.report_view(report["id"], VIEWER)
        self.assertEqual(view["data_point_count"], 3)
        self.assertEqual(view["data_points_by_source"],
                         {"general-ledger extract": 2, "tax workbook": 1})
        self.assertNotIn(
            "data_point_count", self.ext.get_report(report["id"], VIEWER))

    def test_publication_records_reported_outcome(self):
        report = self._report()
        publication = self.ext.record_publication(
            report["id"], "Published to regulator portal, per platform",
            channel_label="regulator portal", actor=MEMBER)
        self.assertEqual(publication["id"], "pub-1")
        self.assertEqual(publication["reported_outcome"],
                         "Published to regulator portal, per platform")
        self.assertIs(publication["published_here"], False)
        self.assertIs(
            self.ext.get_report(report["id"], VIEWER)["published_here"],
            False)
        view = self.ext.report_view(report["id"], VIEWER)
        self.assertEqual(view["publication_count"], 1)


class TestAdditionInvariants(unittest.TestCase):
    """Cross-cutting pins for the addition surface: the
    no-score recursive scan over every record kind and view,
    the core RBAC matrix (the viewer is denied every write),
    and audit entries under ``exta_`` actions."""

    def setUp(self):
        self.ext, self.store, self.audit = make_addition()

    def _exercise_everything(self):
        ext = self.ext
        evidence = make_evidence(self.store)
        assessment = make_assessment(self.store)
        lifecycle = ext.create_policy_lifecycle(
            "evidence", evidence["id"], "Access Policy", actor=MEMBER)
        drive_policy_to_approved(ext, lifecycle["id"])
        definition = ext.register_agent_definition(
            "agent", "SYS-001", "workflow", actor=MEMBER)
        run = ext.create_agent_run(definition["id"], actor=MEMBER)
        ext.record_agent_run_report(run["id"], "done, per agent",
                                    actor=MEMBER)
        request = ext.create_generation_request(
            assessment["id"], "control_narrative", "enclave", actor=MEMBER)
        ext.record_generation_report(
            request["id"], "generated, per engine",
            filed_evidence_id=evidence["id"], actor=MEMBER)
        connector = ext.register_connector(
            "system_sync", "SYS-001", "sync", actor=MEMBER)
        ext.record_sync_receipt(connector["id"], "ok, per connector",
                                records_reported=3, actor=MEMBER)
        item = ext.register_config_item(
            "CI-1", "db", "database", system_ref="SYS-001", actor=MEMBER)
        ticket = ext.create_ticket(
            "incident", "outage", ci_id=item["id"], actor=MEMBER)
        ext.record_ticket_event(ticket["id"], "Open", actor=MEMBER)
        ext.register_sla_policy("gold", "terms, as reported", actor=MEMBER)
        personnel = ext.register_personnel("EMP-1", "tech", actor=MEMBER)
        cert = ext.record_certification(
            personnel["id"], "cred", "issuer", "2027-01-01", actor=MEMBER)
        ext.record_training(personnel["id"], "course", "done, per LMS",
                            actor=MEMBER)
        event = ext.record_quality_event(
            "non-conforming", "batch", personnel_id=personnel["id"],
            actor=MEMBER)
        ext.record_corrective_action(event["id"], "fixed, per owner",
                                     actor=MEMBER)
        ext.record_maintenance("INST-1", "calibration", "ok, per tech",
                               actor=MEMBER)
        report = ext.create_report(
            "SYS-001", SEED_FRAMEWORK_ID, "FY2026 Q3", "filing",
            actor=MEMBER)
        ext.record_data_point(report["id"], "ledger", "42 (as reported)",
                              actor=MEMBER)
        ext.record_publication(report["id"], "published, per platform",
                               actor=MEMBER)
        return lifecycle, ticket, cert, report

    def test_no_score_keys_anywhere_on_the_addition_surface(self):
        lifecycle, ticket, cert, report = self._exercise_everything()
        ext = self.ext
        surfaces = [
            ext.list_policy_lifecycles(VIEWER),
            ext.list_policy_stage_events(VIEWER),
            ext.policy_lifecycle_view(lifecycle["id"], VIEWER),
            ext.list_agent_definitions(VIEWER),
            ext.list_agent_runs(VIEWER),
            ext.list_agent_run_reports(VIEWER),
            ext.list_generation_requests(VIEWER),
            ext.list_generation_reports(VIEWER),
            ext.list_connectors(VIEWER),
            ext.list_sync_receipts(VIEWER),
            ext.list_config_items(VIEWER),
            ext.list_tickets(VIEWER),
            ext.list_ticket_events(VIEWER),
            ext.ticket_view(ticket["id"], VIEWER),
            ext.list_sla_policies(VIEWER),
            ext.list_personnel(VIEWER),
            ext.list_certifications(VIEWER),
            ext.certification_view(cert["id"], VIEWER, as_of="2026-01-01"),
            ext.list_training_records(VIEWER),
            ext.list_quality_events(VIEWER),
            ext.list_corrective_actions(VIEWER),
            ext.list_maintenance_records(VIEWER),
            ext.list_reports(VIEWER),
            ext.list_data_points(VIEWER),
            ext.list_publications(VIEWER),
            ext.report_view(report["id"], VIEWER),
            ext.addition_summary(VIEWER),
        ]
        for surface in surfaces:
            assert_no_score_keys(self, surface)

    def test_viewer_denied_every_addition_write(self):
        ext = self.ext
        evidence = make_evidence(self.store)
        assessment = make_assessment(self.store)
        writes = [
            lambda: ext.create_policy_lifecycle(
                "evidence", evidence["id"], "t", actor=VIEWER),
            lambda: ext.register_agent_definition(
                "a", "SYS-001", "w", actor=VIEWER),
            lambda: ext.create_generation_request(
                assessment["id"], "control_narrative", "e", actor=VIEWER),
            lambda: ext.register_connector(
                "system_sync", "SYS-001", "c", actor=VIEWER),
            lambda: ext.register_config_item("CI-V", "x", "server",
                                             actor=VIEWER),
            lambda: ext.create_ticket("incident", "x", actor=VIEWER),
            lambda: ext.register_sla_policy("g", "t", actor=VIEWER),
            lambda: ext.register_personnel("EMP-V", "r", actor=VIEWER),
            lambda: ext.create_report(
                "SYS-001", SEED_FRAMEWORK_ID, "FY2026", "t", actor=VIEWER),
        ]
        for write in writes:
            with self.assertRaises(PermissionDenied):
                write()
        # Denied writes recorded nothing.
        self.assertEqual(ext.addition_summary(VIEWER)["tickets"]["total"], 0)
        self.assertEqual(
            ext.addition_summary(VIEWER)["policy_lifecycles"]["total"], 0)

    def test_addition_writes_audited_under_exta_actions(self):
        self._exercise_everything()
        actions = {entry["action"] for entry in self.audit.entries()}
        for expected in (
                "exta_policy_lifecycle_create",
                "exta_policy_stage_event_record",
                "exta_agent_run_report_record",
                "exta_generation_report_record",
                "exta_sync_receipt_record",
                "exta_ticket_create",
                "exta_certification_record",
                "exta_data_point_record",
                "exta_publication_record"):
            self.assertIn(expected, actions)

    def test_addition_summary_counts(self):
        self._exercise_everything()
        summary = self.ext.addition_summary(VIEWER)
        self.assertEqual(summary["policy_lifecycles"]["total"], 1)
        self.assertEqual(
            summary["policy_lifecycles"]["by_current_stage"],
            {"approved": 1})
        self.assertEqual(summary["policy_stage_events"]["total"], 3)
        self.assertEqual(summary["agent_runs"]["total"], 1)
        self.assertEqual(summary["generation_requests"]["total"], 1)
        self.assertEqual(summary["sync_receipts"]["records_reported_total"], 3)
        self.assertEqual(summary["tickets"]["by_kind"], {"incident": 1})
        self.assertEqual(summary["certifications"]["total"], 1)
        self.assertEqual(summary["data_points"]["total"], 1)
        self.assertEqual(summary["publications"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
