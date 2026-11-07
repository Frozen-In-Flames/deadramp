"""Final GAPS batch addition tests -- Remainder Addition entries.

Traces to: GAPS.md section "Remainder Addition -- System
Administration L2 (+8 forks)" (inventory idx 552-560) and
``../ADDENDUM.md`` section 5, which names the nine engines this
module closes in records form over the group's own substrate.
Every test pins the extension surface of
``sysadmin.addition.SysadminAddition``: per-entry record shapes
and honesty labels, derived-never-stored current states, the
no-score discipline (recursive key scan), the stub labels on the
two reference implementations, access discipline (denied writes
audited with ``:denied``; non-members reach nothing), and the
unit's fresh negative control on the latest-state derivation
seam.
"""

import sysadmin_helpers as H
from sysadmin.addition import SysadminAddition
from sysadmin.errors import NotFoundError, PermissionDenied, ValidationError

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


class AdditionFixture:
    """Canonical fixture: core store + org + estate + addition."""

    def make(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        return store, org, system, application, SysadminAddition(store)


import unittest  # noqa: E402


class TestDeliveryPlatform(AdditionFixture, unittest.TestCase):
    """idx 552 -- virtual workspace & desktop delivery records."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_definition_shape_and_labels(self):
        record = self.ext.create_workspace_definition(
            MEMBER, self.org["id"], "WS-STD", "Standard desktop", "desktop")
        self.assertEqual(record["id"], "wsd-1")
        self.assertEqual(set(record.keys()), {
            "id", "org_id", "ref", "label", "delivery_kind",
            "delivered_here", "created_by", "created_utc",
        })
        self.assertIs(record["delivered_here"], False)

    def test_session_records_outcome_verbatim(self):
        definition = self.ext.create_workspace_definition(
            MEMBER, self.org["id"], "WS-STD", "Standard desktop", "desktop")
        session = self.ext.record_delivery_session(
            MEMBER, self.org["id"], definition["id"], "SES-1", "USER-9",
            "reported_connected")
        self.assertEqual(session["id"], "dss-1")
        self.assertEqual(session["outcome_label"], "reported_connected")
        self.assertIs(session["delivered_here"], False)

    def test_delivery_summary_counts(self):
        definition = self.ext.create_workspace_definition(
            MEMBER, self.org["id"], "WS-STD", "Standard desktop", "desktop")
        self.ext.create_workspace_definition(
            MEMBER, self.org["id"], "APP-ERP", "ERP app", "application")
        self.ext.record_delivery_session(
            MEMBER, self.org["id"], definition["id"], "SES-1", "USER-9",
            "reported_connected")
        self.ext.record_delivery_session(
            MEMBER, self.org["id"], definition["id"], "SES-2", "USER-9",
            "reported_failed")
        summary = self.ext.delivery_summary(MEMBER, self.org["id"])
        self.assertEqual(summary["workspace_definitions"], 2)
        self.assertEqual(summary["definitions_by_kind"]["desktop"], 1)
        self.assertEqual(summary["delivery_sessions"], 2)
        self.assertEqual(summary["sessions_by_outcome"],
                         {"reported_connected": 1, "reported_failed": 1})
        scan_forbidden(summary)

    def test_duplicate_ref_and_bad_kind_rejected(self):
        self.ext.create_workspace_definition(
            MEMBER, self.org["id"], "WS-STD", "Standard desktop", "desktop")
        with self.assertRaises(ValidationError):
            self.ext.create_workspace_definition(
                MEMBER, self.org["id"], "WS-STD", "Again", "desktop")
        with self.assertRaises(ValidationError):
            self.ext.create_workspace_definition(
                MEMBER, self.org["id"], "WS-X", "X", "hypervisor")


class TestObservabilityStub(AdditionFixture, unittest.TestCase):
    """idx 553 -- observability & AIOps reference implementation."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_source_carries_stub_labels(self):
        source = self.ext.create_telemetry_source(
            MEMBER, self.org["id"], "TS-MET", "Metrics feed", "metrics")
        self.assertEqual(source["id"], "obs-1")
        self.assertIs(source["reference_stub"], True)
        self.assertEqual(source["state"], "recorded_reference_only")
        self.assertIs(source["observed_here"], False)

    def test_insight_report_is_opaque_reference(self):
        source = self.ext.create_telemetry_source(
            MEMBER, self.org["id"], "TS-MET", "Metrics feed", "metrics")
        report = self.ext.record_insight_report(
            MEMBER, self.org["id"], source["id"], "INS-42",
            "reported_anomaly_flagged")
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["inferred_here"], False)
        self.assertEqual(report["report_ref"], "INS-42")
        # No field can hold the insight itself.
        self.assertEqual(set(report.keys()), {
            "id", "org_id", "source_id", "report_ref", "outcome_label",
            "reference_stub", "state", "inferred_here", "created_by",
            "created_utc",
        })


class TestItsmItam(AdditionFixture, unittest.TestCase):
    """idx 554 -- ITSM / ITAM ticket and asset records."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def _ticket_with_states(self):
        ticket = self.ext.create_service_ticket(
            MEMBER, self.org["id"], "TCK-1", "VPN drops hourly", "incident",
            system_id=self.system["id"])
        self.ext.record_ticket_state(
            MEMBER, self.org["id"], ticket["id"], "reported_open")
        self.ext.record_ticket_state(
            MEMBER, self.org["id"], ticket["id"], "reported_in_progress")
        return ticket

    def test_ticket_shape_has_no_stored_state(self):
        ticket = self.ext.create_service_ticket(
            MEMBER, self.org["id"], "TCK-1", "VPN drops hourly", "incident")
        self.assertEqual(set(ticket.keys()), {
            "id", "org_id", "ref", "summary", "ticket_kind", "system_id",
            "created_by", "created_utc",
        })

    def test_current_state_derives_latest_label(self):
        ticket = self._ticket_with_states()
        view = self.ext.get_service_ticket(MEMBER, ticket["id"])
        self.assertEqual(view["current_state"], "reported_in_progress")
        self.ext.record_ticket_state(
            MEMBER, self.org["id"], ticket["id"], "reported_resolved")
        view = self.ext.get_service_ticket(MEMBER, ticket["id"])
        self.assertEqual(view["current_state"], "reported_resolved")

    def test_state_label_vocabulary_enforced(self):
        ticket = self.ext.create_service_ticket(
            MEMBER, self.org["id"], "TCK-1", "VPN drops hourly", "incident")
        with self.assertRaises(ValidationError):
            self.ext.record_ticket_state(
                MEMBER, self.org["id"], ticket["id"], "closed")

    def test_asset_state_derives_and_summary_counts(self):
        asset = self.ext.create_asset_record(
            MEMBER, self.org["id"], "AST-1", "Field laptop", "hardware",
            system_id=self.system["id"])
        self.ext.record_asset_state(
            MEMBER, self.org["id"], asset["id"], "reported_in_service")
        self._ticket_with_states()
        summary = self.ext.itsm_summary(MEMBER, self.org["id"])
        self.assertEqual(summary["tickets_by_kind"]["incident"], 1)
        self.assertEqual(summary["tickets_by_current_state"],
                         {"reported_in_progress": 1})
        self.assertEqual(summary["assets_by_current_state"],
                         {"reported_in_service": 1})
        scan_forbidden(summary)


class TestDiscoveryCmdb(AdditionFixture, unittest.TestCase):
    """idx 555 -- discovery jobs and reported CMDB records."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_job_and_ci_labels(self):
        job = self.ext.create_discovery_job(
            MEMBER, self.org["id"], "DSC-1", "Nightly discovery", "NET-A")
        self.assertIs(job["discovered_here"], False)
        ci = self.ext.record_configuration_item(
            MEMBER, self.org["id"], job["id"], "CI-SRV-1", "App server",
            "server", "reported_active")
        self.assertIs(ci["discovered_here"], False)
        self.assertEqual(ci["reported_state"], "reported_active")

    def test_relationship_and_summary(self):
        job = self.ext.create_discovery_job(
            MEMBER, self.org["id"], "DSC-1", "Nightly discovery", "NET-A")
        one = self.ext.record_configuration_item(
            MEMBER, self.org["id"], job["id"], "CI-SRV-1", "App server",
            "server", "reported_active")
        two = self.ext.record_configuration_item(
            MEMBER, self.org["id"], job["id"], "CI-DB-1", "Database",
            "database", "reported_active")
        self.ext.record_ci_relationship(
            MEMBER, self.org["id"], one["id"], two["id"], "depends_on")
        summary = self.ext.cmdb_summary(MEMBER, self.org["id"])
        self.assertEqual(summary["configuration_items"], 2)
        self.assertEqual(summary["items_by_kind"],
                         {"server": 1, "database": 1})
        self.assertEqual(summary["ci_relationships"], 1)
        scan_forbidden(summary)

    def test_self_relationship_rejected(self):
        job = self.ext.create_discovery_job(
            MEMBER, self.org["id"], "DSC-1", "Nightly discovery", "NET-A")
        ci = self.ext.record_configuration_item(
            MEMBER, self.org["id"], job["id"], "CI-SRV-1", "App server",
            "server", "reported_active")
        with self.assertRaises(ValidationError):
            self.ext.record_ci_relationship(
                MEMBER, self.org["id"], ci["id"], ci["id"], "depends_on")


class TestPortfolioManagement(AdditionFixture, unittest.TestCase):
    """idx 556 -- portfolio and project records, counts only."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_portfolio_view_counts_by_derived_state(self):
        portfolio = self.ext.create_portfolio(
            MEMBER, self.org["id"], "PF-1", "Modernization portfolio")
        project = self.ext.create_project_record(
            MEMBER, self.org["id"], portfolio["id"], "PRJ-1",
            "Portal rebuild", system_id=self.system["id"])
        self.ext.record_project_state(
            MEMBER, self.org["id"], project["id"], "reported_proposed")
        self.ext.record_project_state(
            MEMBER, self.org["id"], project["id"], "reported_active")
        other = self.ext.create_project_record(
            MEMBER, self.org["id"], portfolio["id"], "PRJ-2", "Data cleanup")
        view = self.ext.portfolio_view(MEMBER, self.org["id"],
                                       portfolio["id"])
        self.assertEqual(view["project_count"], 2)
        self.assertEqual(view["projects_by_current_state"],
                         {"reported_active": 1, "recorded": 1})
        self.assertEqual(view["projects"][0]["current_state"],
                         "reported_active")
        self.assertEqual(other["ref"], "PRJ-2")
        scan_forbidden(view)


class TestDex(AdditionFixture, unittest.TestCase):
    """idx 557 -- DEX reports verbatim; automation never executes."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_experience_report_verbatim_not_computed(self):
        report = self.ext.record_experience_report(
            MEMBER, self.org["id"], "EP-100", "DXR-7",
            "vendor_score_82_reported_good")
        self.assertEqual(report["experience_label"],
                         "vendor_score_82_reported_good")
        self.assertIs(report["computed_here"], False)
        # The label is text; a numeric score cannot be filed as one.
        with self.assertRaises(ValidationError):
            self.ext.record_experience_report(
                MEMBER, self.org["id"], "EP-100", "DXR-8", 82)

    def test_automation_definition_and_request_never_execute(self):
        definition = self.ext.create_automation_definition(
            MEMBER, self.org["id"], "DA-1", "Disk cleanup",
            "clear_temp_files")
        self.assertIs(definition["executed_here"], False)
        request = self.ext.record_automation_request(
            MEMBER, self.org["id"], definition["id"], "EP-100",
            "reported_completed")
        self.assertIs(request["executed_here"], False)
        summary = self.ext.dex_summary(MEMBER, self.org["id"])
        self.assertEqual(summary["automation_definitions"], 1)
        self.assertEqual(summary["requests_by_outcome"],
                         {"reported_completed": 1})
        scan_forbidden(summary)


class TestGisPlatform(AdditionFixture, unittest.TestCase):
    """idx 558 -- GIS datasets and layers as metadata + opaque refs."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_dataset_and_layer_shapes_hold_no_geometry(self):
        dataset = self.ext.create_gis_dataset(
            MEMBER, self.org["id"], "DS-PARCELS", "County parcels", "vector")
        self.assertEqual(set(dataset.keys()), {
            "id", "org_id", "ref", "label", "dataset_kind",
            "rendered_here", "created_by", "created_utc",
        })
        layer = self.ext.create_gis_layer(
            MEMBER, self.org["id"], dataset["id"], "LYR-1", "Parcel layer",
            "GEO-REF-991")
        self.assertEqual(layer["geometry_ref"], "GEO-REF-991")
        self.assertIs(layer["rendered_here"], False)
        scan_forbidden(layer)
        # The store signatures reject smuggled geometry content.
        with self.assertRaises(TypeError):
            self.ext.create_gis_layer(
                MEMBER, self.org["id"], dataset["id"], "LYR-2", "Bad",
                "GEO-REF-992", geometry=[[0, 0]])

    def test_service_record_and_summary(self):
        dataset = self.ext.create_gis_dataset(
            MEMBER, self.org["id"], "DS-PARCELS", "County parcels", "vector")
        layer = self.ext.create_gis_layer(
            MEMBER, self.org["id"], dataset["id"], "LYR-1", "Parcel layer",
            "GEO-REF-991")
        service = self.ext.record_gis_service(
            MEMBER, self.org["id"], layer["id"], "SVC-1",
            "reported_published")
        self.assertIs(service["hosted_here"], False)
        summary = self.ext.gis_summary(MEMBER, self.org["id"])
        self.assertEqual(summary["datasets_by_kind"]["vector"], 1)
        self.assertEqual(summary["layers"], 1)
        self.assertEqual(summary["services"], 1)


class TestBackupDrStub(AdditionFixture, unittest.TestCase):
    """idx 559 -- managed backup & DR reference implementation."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_job_outcome_restore_carry_stub_labels(self):
        job = self.ext.create_backup_job(
            MEMBER, self.org["id"], "BK-1", "Nightly OS backup",
            self.system["id"])
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["backed_up_here"], False)
        outcome = self.ext.record_backup_outcome(
            MEMBER, self.org["id"], job["id"], "reported_succeeded",
            reported_bytes=1048576)
        self.assertIs(outcome["reference_stub"], True)
        self.assertEqual(outcome["reported_bytes"], 1048576)
        restore = self.ext.create_restore_request(
            MEMBER, self.org["id"], job["id"], "RST-1",
            "reported_completed")
        self.assertIs(restore["reference_stub"], True)
        self.assertIs(restore["restored_here"], False)
        summary = self.ext.backup_summary(MEMBER, self.org["id"])
        self.assertEqual(summary["backup_jobs"], 1)
        self.assertEqual(summary["outcomes_by_label"],
                         {"reported_succeeded": 1})
        self.assertEqual(summary["restore_requests"], 1)

    def test_reported_bytes_must_be_a_count(self):
        job = self.ext.create_backup_job(
            MEMBER, self.org["id"], "BK-1", "Nightly OS backup",
            self.system["id"])
        with self.assertRaises(ValidationError):
            self.ext.record_backup_outcome(
                MEMBER, self.org["id"], job["id"], "reported_succeeded",
                reported_bytes=1.5)


class TestSecurityOperations(AdditionFixture, unittest.TestCase):
    """idx 560 -- SOC / SIEM case and finding records, verbatim."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_case_state_derives_and_finding_is_verbatim(self):
        case = self.ext.create_security_case(
            MEMBER, self.org["id"], "SEC-1", "Unusual egress reported",
            "incident", system_id=self.system["id"])
        self.assertIs(case["detected_here"], False)
        self.ext.record_case_state(
            MEMBER, self.org["id"], case["id"], "reported_open")
        self.ext.record_case_state(
            MEMBER, self.org["id"], case["id"], "reported_triaged")
        view = self.ext.get_security_case(MEMBER, case["id"])
        self.assertEqual(view["current_state"], "reported_triaged")
        finding = self.ext.record_security_finding(
            MEMBER, self.org["id"], case["id"], "FND-1", "high",
            "reported_confirmed")
        self.assertEqual(finding["severity_label"], "high")
        self.assertIs(finding["scanning_here"], False)
        self.assertIs(finding["detected_here"], False)
        summary = self.ext.security_summary(MEMBER, self.org["id"])
        self.assertEqual(summary["cases_by_current_state"],
                         {"reported_triaged": 1})
        self.assertEqual(summary["findings_by_severity_label"],
                         {"high": 1})
        scan_forbidden(summary)


class TestAccessDiscipline(AdditionFixture, unittest.TestCase):
    """Cross-cutting: membership boundary, RBAC, audit labels."""

    def setUp(self):
        self.store, self.org, self.system, self.app, self.ext = self.make()

    def test_outsider_reaches_nothing(self):
        with self.assertRaises(PermissionDenied):
            self.ext.list_workspace_definitions(OUTSIDER, self.org["id"])
        with self.assertRaises(PermissionDenied):
            self.ext.create_workspace_definition(
                OUTSIDER, self.org["id"], "WS-X", "X", "desktop")

    def test_viewer_write_denied_and_audited(self):
        self.store.add_member(ADMIN, self.org["id"], VIEWER.name)
        with self.assertRaises(PermissionDenied):
            self.ext.create_service_ticket(
                VIEWER, self.org["id"], "TCK-V", "Viewer attempt", "other")
        denied = [e for e in self.store.audit.entries()
                  if e["action"] == "ext_service_ticket_create:denied"]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")

    def test_extension_mutations_audited_with_ext_prefix(self):
        self.ext.create_workspace_definition(
            MEMBER, self.org["id"], "WS-STD", "Standard desktop", "desktop")
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertIn("ext_workspace_definition_create", actions)

    def test_unknown_org_and_record_raise_not_found(self):
        with self.assertRaises(NotFoundError):
            self.ext.list_workspace_definitions(MEMBER, "org-999")
        with self.assertRaises(NotFoundError):
            self.ext.get_service_ticket(MEMBER, "tkt-999")

    def test_failed_write_consumes_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.create_workspace_definition(
                MEMBER, self.org["id"], "WS-BAD", "Bad", "hypervisor")
        record = self.ext.create_workspace_definition(
            MEMBER, self.org["id"], "WS-STD", "Standard desktop", "desktop")
        self.assertEqual(record["id"], "wsd-1")


class EarliestStateMutant(SysadminAddition):
    """Mutant: the current-state derivation reads the EARLIEST
    recorded label instead of the latest."""

    @staticmethod
    def _latest_state_label(state_records):
        if not state_records:
            return "recorded"
        return state_records[0]["state_label"]


class TestLatestStateNegativeControl(AdditionFixture, unittest.TestCase):
    """Fresh negative control: latest recorded state label wins.

    Canonical expectation: after ``reported_open`` then
    ``reported_resolved`` are recorded on a ticket, its derived
    current state is ``reported_resolved``. The mutant (earliest
    label) reports ``reported_open`` and is shown to violate the
    canonical expectation.
    """

    def _fixture(self, ext_class):
        store, org = H.make_store()
        return store, org, ext_class(store)

    def _canonical_current_state(self, ext, org):
        ticket = ext.create_service_ticket(
            MEMBER, org["id"], "TCK-1", "VPN drops hourly", "incident")
        ext.record_ticket_state(
            MEMBER, org["id"], ticket["id"], "reported_open")
        ext.record_ticket_state(
            MEMBER, org["id"], ticket["id"], "reported_resolved")
        return ext.get_service_ticket(MEMBER, ticket["id"])["current_state"]

    def test_canonical_expectation(self):
        store, org, ext = self._fixture(SysadminAddition)
        self.assertEqual(self._canonical_current_state(ext, org),
                         "reported_resolved")

    def test_implementation_matches_canonical(self):
        store, org, ext = self._fixture(SysadminAddition)
        ticket = ext.create_service_ticket(
            MEMBER, org["id"], "TCK-1", "VPN drops hourly", "incident")
        ext.record_ticket_state(
            MEMBER, org["id"], ticket["id"], "reported_open")
        ext.record_ticket_state(
            MEMBER, org["id"], ticket["id"], "reported_in_progress")
        ext.record_ticket_state(
            MEMBER, org["id"], ticket["id"], "reported_closed")
        view = ext.get_service_ticket(MEMBER, ticket["id"])
        self.assertEqual(view["current_state"], "reported_closed")
        summary = ext.itsm_summary(MEMBER, org["id"])
        self.assertEqual(summary["tickets_by_current_state"],
                         {"reported_closed": 1})

    def test_mutant_violates_canonical_expectation(self):
        store, org, ext = self._fixture(EarliestStateMutant)
        mutant_state = self._canonical_current_state(ext, org)
        self.assertEqual(mutant_state, "reported_open")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_state, "reported_resolved")


if __name__ == "__main__":
    unittest.main()
