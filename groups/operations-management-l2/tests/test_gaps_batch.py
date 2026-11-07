"""Final GAPS batch tests — Group 36, Operations Management L2.

Pins the extension surface in ``src/opsmgmt/extensions.py``
(``OpsExtensions``, wrapping the core ``OpsStore``): one test class
per open GAPS.md entry for this group (see ``../BATCH.md`` for the
per-entry disposition), plus cross-cutting pins -- ``ext_``-prefixed
actions and ``:denied`` denials on the core audit log,
stub/transport labels on every reference record,
derived-never-stored values (coverage views, summaries,
application views), opaque-reference-only record shapes, and the
batch's fresh negative control: the shift-overlap guard
``_check_shift_overlap``.

Fixtures: ``make_store()`` (a person, an organization, and a
project with the person as member) from ``opsmgmt_helpers``;
ADMIN=alice/admin, OPERATOR=bob/operator, VIEWER=carol/viewer.
"""

import unittest

import opsmgmt.extensions as extensions_module
from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER, make_store

from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError
from opsmgmt.extensions import OpsExtensions


class ExtFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.person, self.org, self.project = make_store()
        self.ext = OpsExtensions(self.store)
        self.pid = self.person["id"]
        self.proj = self.project["id"]

    def audit_actions(self):
        return [e["action"] for e in self.store.audit.entries()]

    def make_second_person(self):
        return self.store.create_person(
            "Second Person", ADMIN, reference="EXT-1002")


class TestLowCodeApps(ExtFixture):
    """Entry: Low-code application builder & deployment engine --
    built as application definition records (components as data)
    plus deployment-intent records; nothing is built or deployed."""

    def test_definition_shape_and_labels(self):
        app = self.ext.create_application(
            "Intake App", ADMIN, project_id=self.proj,
            components=[{"kind": "form", "fields": ["a"]},
                        {"kind": "table"}],
            description="field intake")
        self.assertEqual(app["id"], "app-1")
        self.assertEqual(app["version"], 1)
        self.assertIs(app["built_here"], False)
        self.assertIs(app["deployed_here"], False)
        self.assertEqual(app["components"][0]["kind"], "form")
        # Returned records are copies; mutating one changes nothing.
        app["components"].append({"kind": "bogus"})
        stored = self.ext.get_application(app["id"], ADMIN)
        self.assertEqual(len(stored["components"]), 2)

    def test_update_bumps_version(self):
        app = self.ext.create_application("Intake App", ADMIN)
        updated = self.ext.update_application(
            app["id"], ADMIN, components=[{"kind": "chart"}])
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["components"], [{"kind": "chart"}])

    def test_deployment_intent_recorded_not_executed(self):
        app = self.ext.create_application("Intake App", ADMIN)
        intent = self.ext.record_deployment_intent(
            app["id"], "env-prod-1", ADMIN)
        self.assertEqual(intent["id"], "dep-1")
        self.assertEqual(intent["status"], "recorded")
        self.assertIs(intent["executed"], False)
        self.assertIs(intent["deployed_here"], False)
        view = self.ext.application_view(app["id"], ADMIN)
        self.assertEqual(view["deployment_intent_count"], 1)
        # The count is derived: the stored definition carries none.
        self.assertNotIn("deployment_intent_count",
                         self.ext.get_application(app["id"], ADMIN))

    def test_unknown_project_and_app_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.create_application("X", ADMIN, project_id="proj-99")
        with self.assertRaises(NotFoundError):
            self.ext.record_deployment_intent("app-99", "env-1", ADMIN)

    def test_component_without_kind_rejected_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.create_application(
                "Bad", ADMIN, components=[{"fields": []}])
        app = self.ext.create_application("Good", ADMIN)
        self.assertEqual(app["id"], "app-1")

    def test_operator_denied_and_audited(self):
        # Application definitions are configuration: workflow_write
        # is admin-only, exactly as the core workflow registry.
        with self.assertRaises(PermissionDenied):
            self.ext.create_application("Nope", OPERATOR)
        self.assertIn("ext_app_create:denied", self.audit_actions())
        self.assertEqual(self.ext.list_applications(ADMIN), [])


class TestMobileSync(ExtFixture):
    """Entry: Mobile applications & offline sync -- built as
    sync-session and conflict records with recorded states; no
    device syncs, and a recorded resolution is applied nowhere."""

    def test_session_conflict_resolution_lifecycle(self):
        session = self.ext.start_sync_session("device-ref-1", OPERATOR,
                                              client_ref="client-ref-1")
        self.assertEqual(session["id"], "syn-1")
        self.assertEqual(session["status"], "open")
        self.assertIs(session["synced_here"], False)
        conflict = self.ext.record_sync_conflict(
            session["id"], OPERATOR, "record-ref-9", "status-field",
            "open", "closed")
        self.assertEqual(conflict["local_value"], "open")
        self.assertEqual(conflict["remote_value"], "closed")
        self.assertIsNone(conflict["resolution"])
        self.assertIs(conflict["applied_here"], False)
        resolved = self.ext.resolve_sync_conflict(
            conflict["id"], "remote_wins", OPERATOR)
        self.assertEqual(resolved["resolution"], "remote_wins")
        self.assertIs(resolved["applied_here"], False)
        closed = self.ext.close_sync_session(session["id"], OPERATOR)
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["outcome"], "completed")

    def test_conflict_on_closed_session_rejected(self):
        session = self.ext.start_sync_session("device-ref-1", OPERATOR)
        self.ext.close_sync_session(session["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_sync_conflict(
                session["id"], OPERATOR, "rec-1", "fld-1", "a", "b")

    def test_double_resolution_rejected(self):
        session = self.ext.start_sync_session("device-ref-1", OPERATOR)
        conflict = self.ext.record_sync_conflict(
            session["id"], OPERATOR, "rec-1", "fld-1", 1, 2)
        self.ext.resolve_sync_conflict(conflict["id"], "merged", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.resolve_sync_conflict(
                conflict["id"], "local_wins", OPERATOR)

    def test_summary_counts_derived(self):
        s1 = self.ext.start_sync_session("device-ref-1", OPERATOR)
        self.ext.start_sync_session("device-ref-2", OPERATOR)
        self.ext.record_sync_conflict(
            s1["id"], OPERATOR, "rec-1", "fld-1", "a", "b")
        summary = self.ext.sync_summary(ADMIN)
        self.assertEqual(summary["sessions"], 2)
        self.assertEqual(summary["sessions_by_status"], {"open": 2})
        self.assertEqual(summary["conflicts"], 1)
        self.assertEqual(summary["conflicts_unresolved"], 1)
        self.assertIs(summary["synced_here"], False)

    def test_address_shaped_refs_rejected(self):
        for bad in ("10.0.0.1", "https://device.example", "device host"):
            with self.assertRaises(ValidationError):
                self.ext.start_sync_session(bad, OPERATOR)


class TestSecurityServices(ExtFixture):
    """Entry: Common security services enforcement plane -- built
    as an enforcement-point registry plus state records as
    reported by the external services; nothing is enforced."""

    def test_point_shape_and_labels(self):
        point = self.ext.register_security_service_point(
            "gw-east", "access_gateway", "scope-proj-alpha", OPERATOR,
            policy_ref="policy-main")
        self.assertEqual(point["id"], "enf-1")
        self.assertEqual(point["status"], "registered")
        self.assertIs(point["enforced_here"], False)

    def test_states_reported_and_coverage_derived(self):
        p1 = self.ext.register_security_service_point(
            "gw-east", "access_gateway", "scope-a", OPERATOR)
        p2 = self.ext.register_security_service_point(
            "scan-1", "vulnerability_scanning", "scope-a", OPERATOR)
        self.ext.record_security_service_state(
            p1["id"], "enforcing_reported", OPERATOR)
        self.ext.record_security_service_state(
            p1["id"], "degraded_reported", OPERATOR)
        coverage = self.ext.security_service_coverage(ADMIN)
        self.assertEqual(coverage["points"], 2)
        self.assertEqual(
            coverage["points_by_kind"],
            {"access_gateway": 1, "vulnerability_scanning": 1})
        self.assertEqual(coverage["state_records"], 2)
        self.assertEqual(
            coverage["state_records_by_reported_state"],
            {"enforcing_reported": 1, "degraded_reported": 1})
        self.assertEqual(coverage["points_with_state_records"], 1)
        self.assertIs(coverage["enforced_here"], False)
        # Coverage is derived: the stored point record carries none.
        self.assertEqual(
            set(self.ext.get_security_service_point(p2["id"], ADMIN)),
            {"id", "point_ref", "kind", "scope_ref", "policy_ref",
             "status", "enforced_here", "created_by", "created_utc",
             "updated_utc"})

    def test_retire_and_double_retire_rejected(self):
        point = self.ext.register_security_service_point(
            "gw-east", "access_gateway", "scope-a", OPERATOR)
        retired = self.ext.retire_security_service_point(point["id"],
                                                         OPERATOR)
        self.assertEqual(retired["status"], "retired")
        with self.assertRaises(ValidationError):
            self.ext.retire_security_service_point(point["id"], OPERATOR)

    def test_bad_kind_rejected_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.register_security_service_point(
                "x-1", "mind_control", "scope-a", OPERATOR)
        point = self.ext.register_security_service_point(
            "gw-east", "access_gateway", "scope-a", OPERATOR)
        self.assertEqual(point["id"], "enf-1")


class TestPolicyPlane(ExtFixture):
    """Entry: Policy enforcement plane (runtime enforcement
    across projects) -- built as policy definition and assignment
    records plus evaluation records stored as reported; the build
    evaluates no policy and enforces nothing."""

    def test_definition_assignment_and_duplicate(self):
        policy = self.ext.create_policy(
            "Require MFA", "all projects require mfa", ADMIN)
        self.assertIs(policy["enforced_here"], False)
        assignment = self.ext.assign_policy(policy["id"], self.proj, ADMIN)
        self.assertEqual(assignment["status"], "active")
        with self.assertRaises(ValidationError):
            self.ext.assign_policy(policy["id"], self.proj, ADMIN)

    def test_evaluation_reported_and_summary(self):
        policy = self.ext.create_policy("P", "rule text", ADMIN)
        evaluation = self.ext.record_policy_evaluation(
            policy["id"], OPERATOR, "compliant_reported",
            project_id=self.proj)
        self.assertEqual(evaluation["outcome"], "compliant_reported")
        self.assertIs(evaluation["enforced_here"], False)
        summary = self.ext.policy_summary(ADMIN)
        self.assertEqual(summary["policies"], 1)
        self.assertEqual(summary["evaluations"], 1)
        self.assertEqual(summary["evaluations_by_outcome"],
                         {"compliant_reported": 1})

    def test_evaluator_may_not_be_creator(self):
        policy = self.ext.create_policy("P", "rule text", ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.record_policy_evaluation(
                policy["id"], ADMIN, "compliant_reported")
        evaluation = self.ext.record_policy_evaluation(
            policy["id"], OPERATOR, "inconclusive")
        self.assertEqual(evaluation["outcome"], "inconclusive")

    def test_operator_denied_policy_create_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_policy("Nope", "rule", OPERATOR)
        self.assertIn("ext_policy_create:denied", self.audit_actions())


class TestScheduling(ExtFixture):
    """Entry: Scheduling & rostering (0 of 2; named absence) --
    built as roster/shift/assignment records over the core
    directory, with coverage derived at read."""

    def _roster_with_shift(self, starts="2026-06-01T09:00:00Z",
                           ends="2026-06-01T11:00:00Z", required=1):
        roster = self.ext.create_roster("Field Roster", OPERATOR,
                                        project_id=self.proj)
        shift = self.ext.create_shift(roster["id"], OPERATOR, starts,
                                      ends, required_count=required)
        return roster, shift

    def test_coverage_derived_at_read(self):
        roster, shift = self._roster_with_shift(required=2)
        self.ext.assign_shift(shift["id"], self.pid, OPERATOR)
        coverage = self.ext.roster_coverage(roster["id"], ADMIN)
        entry = coverage["shifts"][0]
        self.assertEqual(entry["assigned_count"], 1)
        self.assertIs(entry["covered"], False)
        self.assertEqual(entry["shortfall"], 1)
        second = self.make_second_person()
        self.ext.assign_shift(shift["id"], second["id"], OPERATOR)
        coverage = self.ext.roster_coverage(roster["id"], ADMIN)
        self.assertIs(coverage["shifts"][0]["covered"], True)
        self.assertEqual(coverage["covered_shift_count"], 1)
        # Coverage is derived: the stored shift carries no count.
        stored = self.ext.list_shifts(ADMIN, roster_id=roster["id"])[0]
        self.assertNotIn("assigned_count", stored)

    def test_overlap_rejected_canonical(self):
        _, shift = self._roster_with_shift()
        self.ext.assign_shift(shift["id"], self.pid, OPERATOR)
        other_roster = self.ext.create_roster("Other Roster", OPERATOR)
        overlapping = self.ext.create_shift(
            other_roster["id"], OPERATOR, "2026-06-01T10:00:00Z",
            "2026-06-01T12:00:00Z")
        with self.assertRaises(ValidationError):
            self.ext.assign_shift(overlapping["id"], self.pid, OPERATOR)
        active = self.ext.list_shift_assignments(
            ADMIN, person_id=self.pid, status="active")
        self.assertEqual(len(active), 1)

    def test_adjacent_shifts_do_not_overlap(self):
        _, shift = self._roster_with_shift()
        self.ext.assign_shift(shift["id"], self.pid, OPERATOR)
        roster2 = self.ext.create_roster("R2", OPERATOR)
        adjacent = self.ext.create_shift(
            roster2["id"], OPERATOR, "2026-06-01T11:00:00Z",
            "2026-06-01T13:00:00Z")
        assignment = self.ext.assign_shift(adjacent["id"], self.pid,
                                           OPERATOR)
        self.assertEqual(assignment["status"], "active")

    def test_withdrawn_assignment_frees_window(self):
        _, shift = self._roster_with_shift()
        assignment = self.ext.assign_shift(shift["id"], self.pid, OPERATOR)
        self.ext.withdraw_shift_assignment(assignment["id"], OPERATOR)
        roster2 = self.ext.create_roster("R2", OPERATOR)
        overlapping = self.ext.create_shift(
            roster2["id"], OPERATOR, "2026-06-01T10:00:00Z",
            "2026-06-01T12:00:00Z")
        new = self.ext.assign_shift(overlapping["id"], self.pid, OPERATOR)
        self.assertEqual(new["status"], "active")

    def test_duplicate_assignment_rejected(self):
        _, shift = self._roster_with_shift()
        self.ext.assign_shift(shift["id"], self.pid, OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.assign_shift(shift["id"], self.pid, OPERATOR)

    def test_shift_validation(self):
        roster = self.ext.create_roster("R", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.create_shift(roster["id"], OPERATOR,
                                  "2026-06-01T11:00:00Z",
                                  "2026-06-01T09:00:00Z")
        with self.assertRaises(ValidationError):
            self.ext.create_shift(roster["id"], OPERATOR,
                                  "2026-06-01T09:00:00Z",
                                  "2026-06-01T11:00:00Z",
                                  required_count=0)
        with self.assertRaises(ValidationError):
            self.ext.create_shift(roster["id"], OPERATOR,
                                  "2026-06-01T09:00:00Z",
                                  "2026-06-01T11:00:00Z",
                                  required_count=True)

    def test_unknown_person_rejected(self):
        _, shift = self._roster_with_shift()
        with self.assertRaises(NotFoundError):
            self.ext.assign_shift(shift["id"], "per-99", OPERATOR)


class TestShiftOverlapNegativeControl(ExtFixture):
    """Fresh negative control for the batch: a person may not
    hold two active shift assignments whose windows overlap (the
    ``_check_shift_overlap`` seam in ``opsmgmt/extensions.py``).

    Three legs, the house form: (1) the canonical expectation
    from the real implementation, (2) the mutant (the seam
    patched to a no-op in-process) would NOT produce it -- the
    overlapping assignment succeeds, and (3) treating the
    mutant's outcome as the expected outcome fails.
    """

    def test_overlap_guard_canonical_but_mutant_not(self):
        roster = self.ext.create_roster("R", OPERATOR)
        first = self.ext.create_shift(
            roster["id"], OPERATOR, "2026-06-01T09:00:00Z",
            "2026-06-01T11:00:00Z")
        second = self.ext.create_shift(
            roster["id"], OPERATOR, "2026-06-01T10:00:00Z",
            "2026-06-01T12:00:00Z")
        self.ext.assign_shift(first["id"], self.pid, OPERATOR)

        # (1) Canonical: the overlapping assignment is refused and
        # the person still holds exactly one active assignment.
        with self.assertRaises(ValidationError):
            self.ext.assign_shift(second["id"], self.pid, OPERATOR)
        canonical_active = self.ext.list_shift_assignments(
            ADMIN, person_id=self.pid, status="active")
        self.assertEqual(len(canonical_active), 1)

        # (2) Mutant: with the guard seam disabled, the same
        # assignment succeeds -- the mutant would NOT produce the
        # canonical outcome.
        original = extensions_module._check_shift_overlap
        extensions_module._check_shift_overlap = (
            lambda existing_windows, new_window: None)
        try:
            mutant_assignment = self.ext.assign_shift(
                second["id"], self.pid, OPERATOR)
        finally:
            extensions_module._check_shift_overlap = original
        self.assertEqual(mutant_assignment["status"], "active")
        mutant_active = self.ext.list_shift_assignments(
            ADMIN, person_id=self.pid, status="active")
        self.assertEqual(len(mutant_active), 2)

        # (3) Treating the mutant's outcome as the expectation
        # fails.
        with self.assertRaises(AssertionError):
            self.assertEqual(len(mutant_active), len(canonical_active))


class TestIoT(ExtFixture):
    """Entry: IoT / telematics data collection (0 of 2; named
    absence) -- built as device-registration records keyed by
    opaque references (no identifier fields) plus reported
    reading records stored verbatim; nothing is collected."""

    def test_device_shape_has_no_identifier_fields(self):
        device = self.ext.register_device("device-ref-7", "sensor",
                                          OPERATOR)
        self.assertEqual(
            set(device.keys()),
            {"id", "device_ref", "kind", "asset_id", "collected_here",
             "created_by", "created_utc", "updated_utc"})
        self.assertIs(device["collected_here"], False)
        for key in device:
            for token in ("imei", "serial", "vin", "mac", "phone"):
                self.assertNotIn(token, key.lower())

    def test_readings_verbatim_and_summary(self):
        device = self.ext.register_device("device-ref-7", "tracker",
                                          OPERATOR)
        r1 = self.ext.record_telemetry_reading(
            device["id"], "temperature", 21.5, OPERATOR,
            reported_at="2026-06-01T10:00:00Z")
        self.assertEqual(r1["value"], 21.5)
        self.assertIs(r1["collected_here"], False)
        self.ext.record_telemetry_reading(device["id"], "temperature",
                                          22, OPERATOR)
        self.ext.record_telemetry_reading(device["id"], "status",
                                          "ok", OPERATOR)
        summary = self.ext.telemetry_summary(ADMIN)
        self.assertEqual(summary["devices"], 1)
        self.assertEqual(summary["devices_by_kind"], {"tracker": 1})
        self.assertEqual(summary["readings"], 3)
        self.assertEqual(summary["readings_by_metric"],
                         {"temperature": 2, "status": 1})

    def test_non_scalar_values_rejected(self):
        device = self.ext.register_device("device-ref-7", "sensor",
                                          OPERATOR)
        for bad in (True, None, {"x": 1}, [1, 2]):
            with self.assertRaises(ValidationError):
                self.ext.record_telemetry_reading(
                    device["id"], "m", bad, OPERATOR)

    def test_address_shaped_device_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.ext.register_device("192.168.0.1", "sensor", OPERATOR)


class TestWorkflowRunReferences(ExtFixture):
    """Entry: Workflow automation execution engine -- shipped as
    a labeled reference implementation: run references copy the
    core workflow definition as data and are marked not
    executed; the registry never executes."""

    def _workflow(self):
        return self.store.create_workflow(
            ADMIN, "Due inspection", "inspection",
            "when a work order is due", "notify the assignee")

    def test_run_reference_copies_current_definition(self):
        workflow = self._workflow()
        self.store.update_workflow(
            workflow["id"], ADMIN, action_text="escalate to the lead")
        ref = self.ext.register_workflow_run_reference(
            workflow["id"], ADMIN, reported_status="reported_failed")
        self.assertIs(ref["reference_stub"], True)
        self.assertIs(ref["executed"], False)
        self.assertEqual(ref["definition_version"], 2)
        self.assertEqual(ref["definition_snapshot"]["action_text"],
                         "escalate to the lead")
        self.assertEqual(ref["definition_snapshot"]["trigger_text"],
                         "when a work order is due")

    def test_run_reference_changes_no_core_record(self):
        workflow = self._workflow()
        wo = self.store.create_work_order(
            OPERATOR, "inspection", "Inspect pump station",
            project_id=self.proj)
        before = self.store.list_work_orders(OPERATOR)
        self.ext.register_workflow_run_reference(workflow["id"], ADMIN)
        after = self.store.list_work_orders(OPERATOR)
        self.assertEqual(before, after)
        self.assertEqual(
            self.store.get_work_order(wo["id"], OPERATOR)["status"],
            "open")

    def test_operator_denied_run_reference(self):
        workflow = self._workflow()
        with self.assertRaises(PermissionDenied):
            self.ext.register_workflow_run_reference(workflow["id"],
                                                     OPERATOR)

    def test_unknown_workflow_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.register_workflow_run_reference("wf-99", ADMIN)


class TestStreamReferences(ExtFixture):
    """Entry: Real-time intelligence & analytics engine --
    shipped as a labeled reference implementation: stream
    references plus snapshot references carrying counts as
    reported; nothing streams and no analytics is computed."""

    def test_stream_and_snapshot_labels(self):
        stream = self.ext.register_stream_reference(
            "ops-events", "event_stream", OPERATOR, scope_ref="scope-a")
        self.assertIs(stream["reference_stub"], True)
        self.assertIs(stream["streamed_here"], False)
        snapshot = self.ext.record_stream_snapshot_reference(
            stream["id"], {"events": 120, "alerts": 3}, OPERATOR)
        self.assertIs(snapshot["reference_stub"], True)
        self.assertIs(snapshot["reference_transport"], True)
        self.assertIs(snapshot["computed_here"], False)
        self.assertEqual(snapshot["counts"], {"events": 120, "alerts": 3})

    def test_counts_validation(self):
        stream = self.ext.register_stream_reference(
            "ops-events", "metric_stream", OPERATOR)
        for bad in ({"events": -1}, {"events": True}, {"events": 1.5}, {}):
            with self.assertRaises(ValidationError):
                self.ext.record_stream_snapshot_reference(
                    stream["id"], bad, OPERATOR)


class TestModelReferences(ExtFixture):
    """Entry: AI models (1 claim) -- shipped as a labeled
    reference implementation: model references plus output
    references with labels stored as reported; no model is
    trained or run, and no output record carries a score."""

    def test_model_and_output_labels(self):
        model = self.ext.register_model_reference(
            "readiness-forecast", "prediction", OPERATOR,
            project_id=self.proj)
        self.assertIs(model["reference_stub"], True)
        self.assertIs(model["trained_here"], False)
        self.assertIs(model["inference_here"], False)
        output = self.ext.record_model_output_reference(
            model["id"], "at_risk", OPERATOR, subject_ref="proj-alpha")
        self.assertEqual(output["label"], "at_risk")
        self.assertIs(output["reference_stub"], True)
        self.assertNotIn("score", output)
        self.assertNotIn("confidence", output)


class TestConnectorReferences(ExtFixture):
    """Entry: Integration connector engines & catalog -- shipped
    as a labeled reference implementation: catalog references
    plus run references; nothing connects or moves."""

    def test_connector_and_run_labels(self):
        connector = self.ext.register_connector_reference(
            "erp-sync", "api", OPERATOR, target_ref="erp-ref-1")
        self.assertIs(connector["reference_stub"], True)
        self.assertIs(connector["connected_here"], False)
        run = self.ext.record_connector_run_reference(
            connector["id"], "reported_partial", OPERATOR,
            records_reported=42)
        self.assertIs(run["reference_stub"], True)
        self.assertIs(run["reference_transport"], True)
        self.assertIs(run["executed_here"], False)
        self.assertEqual(run["records_reported"], 42)


class TestPlatformReferences(ExtFixture):
    """Entry: Network connectivity services & cloud platform
    operations (platform-layer; one sibling's own service) --
    shipped as a labeled reference implementation: service and
    operation references; nothing is hosted or operated."""

    def test_service_and_operation_labels(self):
        service = self.ext.register_platform_service_reference(
            "agency-net", "network_connectivity", OPERATOR,
            scope_ref="scope-a")
        self.assertIs(service["reference_stub"], True)
        self.assertIs(service["hosted_here"], False)
        self.assertIs(service["operated_here"], False)
        operation = self.ext.record_platform_operation_reference(
            service["id"], "failover drill", "reported_completed",
            OPERATOR)
        self.assertIs(operation["reference_stub"], True)
        self.assertIs(operation["performed_here"], False)


class TestIdentityHooks(ExtFixture):
    """Entry: Authorization service / identity provider (the
    build ships RBAC hooks, not an IdP) -- shipped as hook
    records only, per PLATFORM-LAYER.md decision 1."""

    def test_hook_shape_is_hook_only(self):
        hook = self.ext.register_identity_hook(
            "agency-sso", "sso", ADMIN, scope_ref="scope-a")
        self.assertIs(hook["hook_only"], True)
        self.assertIs(hook["identity_provider"], False)
        self.assertIs(hook["reference_stub"], True)
        hooks = self.ext.list_identity_hooks(ADMIN, kind="sso")
        self.assertEqual(len(hooks), 1)

    def test_operator_denied_hook_register_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_identity_hook("agency-sso", "sso", OPERATOR)
        self.assertIn("ext_identity_hook_register:denied",
                      self.audit_actions())


class TestGovernanceReferences(ExtFixture):
    """Entry: Governance / compliance console engine (continuous
    compliance monitoring depth) -- shipped as a labeled
    reference implementation: framework references plus snapshot
    references with counts as reported; no monitoring happens
    and no posture score is computed."""

    def test_framework_snapshot_and_summary(self):
        framework = self.ext.register_governance_framework_reference(
            "nist-800-171", "NIST SP 800-171", OPERATOR,
            control_refs=["3-1-1", "3-3-1"])
        self.assertIs(framework["reference_stub"], True)
        self.assertIs(framework["monitored_here"], False)
        snapshot = self.ext.record_compliance_snapshot_reference(
            framework["id"], {"controls_reported": 110,
                              "findings_reported": 4}, OPERATOR)
        self.assertIs(snapshot["reference_stub"], True)
        self.assertIs(snapshot["computed_here"], False)
        summary = self.ext.governance_summary(ADMIN)
        self.assertEqual(summary["frameworks"], 1)
        self.assertEqual(summary["snapshots"], 1)
        self.assertEqual(summary["snapshots_by_framework"],
                         {framework["id"]: 1})
        # Counts only: no score/rate/grade key anywhere in the view.
        for key in summary:
            for token in ("score", "rate", "grade", "percent"):
                self.assertNotIn(token, key.lower())

    def test_snapshot_counts_validation(self):
        framework = self.ext.register_governance_framework_reference(
            "fw-1", "Framework", OPERATOR)
        with self.assertRaises(ValidationError):
            self.ext.record_compliance_snapshot_reference(
                framework["id"], {"controls": -2}, OPERATOR)


class TestCrossCutting(ExtFixture):
    """Cross-cutting pins for the whole extension surface."""

    def test_ext_actions_recorded_on_core_audit(self):
        self.ext.create_application("App", ADMIN)
        self.ext.register_device("device-ref-1", "sensor", OPERATOR)
        actions = self.audit_actions()
        self.assertIn("ext_app_create", actions)
        self.assertIn("ext_device_register", actions)

    def test_denied_attempt_audited_and_no_state_change(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_device("device-ref-1", "sensor", VIEWER)
        self.assertIn("ext_device_register:denied", self.audit_actions())
        self.assertEqual(self.ext.list_devices(ADMIN), [])

    def test_no_actor_write_denied(self):
        with self.assertRaises(PermissionDenied):
            self.ext.create_application("App", None)

    def test_failed_create_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.register_device("device-ref-1", "holodeck", OPERATOR)
        device = self.ext.register_device("device-ref-1", "sensor",
                                          OPERATOR)
        self.assertEqual(device["id"], "dev-1")

    def test_unknown_extension_record(self):
        with self.assertRaises(NotFoundError):
            self.ext.get_application("app-99", ADMIN)
        with self.assertRaises(NotFoundError):
            self.ext.get_device("dev-99", ADMIN)

    def test_extension_records_are_copies(self):
        device = self.ext.register_device("device-ref-1", "sensor",
                                          OPERATOR)
        device["kind"] = "tampered"
        stored = self.ext.get_device(device["id"], ADMIN)
        self.assertEqual(stored["kind"], "sensor")


if __name__ == "__main__":
    unittest.main()
