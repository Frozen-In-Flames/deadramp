"""Final GAPS batch tests — Group 42, Finance L3-adjacent.

Pins the extension surface in ``src/finance/extensions.py``
(``FinanceExtensions``, wrapping the core ``FinanceStore``): one
test class per open GAPS.md entry for this group (see ``../BATCH.md``
for the per-entry disposition), plus cross-cutting pins —
``ext_``-prefixed actions and ``:denied`` denials on the core
hash-chained audit log, the separated ``auditor`` role denied every
extension operation while its core audit duty works, stub labels on
every reference record (and their absence on built records),
derived-never-stored values (platform posture, screening summary,
monitoring summary), the no-money / no-bank-detail / no-identifier
shape pins, the standing trading & investment execution absence pin,
and the batch's fresh negative control: the by-label count seam
``_count_by_label``.

Fixtures: ``make_store()`` (a program owned by MEMBER=bob with
VIEWER=carol added as a member) from ``finance_helpers``;
ADMIN=alice/admin (platform admin, not a program member),
AUDITOR=dana/auditor (audit_read only), OUTSIDER=dave/member
(no fixture program).
"""

import unittest

from finance_helpers import (
    ADMIN,
    AUDITOR,
    MEMBER,
    OUTSIDER,
    PERIOD,
    VIEWER,
    make_accrual,
    make_employee,
    make_store,
)

from finance.errors import NotFoundError, PermissionDenied, ValidationError
from finance.extensions import FinanceExtensions, _count_by_label

SERVICE_LABELS = ("compute", "storage", "networking", "database", "other")
ATTESTATION_LABELS = (
    "personnel_eligibility",
    "physical_operation",
    "handling_environment",
    "authorization_boundary",
)
SCREENING_LABELS = (
    "reported_eligible",
    "reported_ineligible",
    "reported_pending",
)
MONITORING_LABELS = (
    "reported_healthy",
    "reported_degraded",
    "reported_incident",
    "reported_outage",
)


def mutant_count_by_label(records, key, labels):
    """The defect under control: the result dict is built with
    every label at zero and the records are never counted."""
    counts = {label: 0 for label in labels}
    _ = (records, key)
    return counts


def all_keys(obj):
    """Every dict key in a record, recursively."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            keys.add(key)
            keys |= all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            keys |= all_keys(item)
    return keys


class BatchFixture(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.program_id = make_store()
        self.ext = FinanceExtensions(self.store)

    def audit_actions(self):
        return [e["action"] for e in self.audit.entries()]

    def make_region(self, ref="region-east", name="GovCloud (US-East)"):
        return self.ext.register_region(self.program_id, ref, name, MEMBER)


class TestCloudPlatformBuilt(BatchFixture):
    """Entry (idx 404): The cloud infrastructure platform itself —
    built as region and service-catalog records. The platform is
    operated elsewhere; this surface records its catalog and
    provisions nothing."""

    def test_region_record_shape_and_labels(self):
        region = self.make_region()
        self.assertEqual(region["id"], "regn-1")
        self.assertEqual(
            set(region),
            {
                "id", "program_id", "region_ref", "name_label",
                "operated_here", "state", "created_by", "created_utc",
            },
        )
        self.assertIs(region["operated_here"], False)
        self.assertEqual(region["state"], "recorded_reference_only")
        self.assertNotIn("reference_stub", region)

    def test_duplicate_region_ref_rejected_and_no_id_consumed(self):
        self.make_region()
        with self.assertRaises(ValidationError):
            self.ext.register_region(
                self.program_id, "region-east", "Duplicate", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_region(self.program_id, "  ", "Blank", MEMBER)
        second = self.ext.register_region(
            self.program_id, "region-west", "GovCloud (US-West)", MEMBER)
        self.assertEqual(second["id"], "regn-2")

    def test_service_record_shape_and_category_validation(self):
        region = self.make_region()
        service = self.ext.record_region_service(
            self.program_id, region["id"], "svc-compute-1", "compute",
            MEMBER, label="Compute service")
        self.assertEqual(service["id"], "rsvc-1")
        self.assertEqual(
            set(service),
            {
                "id", "program_id", "region_id", "service_ref",
                "category", "label", "operated_here", "created_by",
                "created_utc",
            },
        )
        self.assertIs(service["operated_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.record_region_service(
                self.program_id, region["id"], "svc-x", "quantum", MEMBER)
        good = self.ext.record_region_service(
            self.program_id, region["id"], "svc-store-1", "storage", MEMBER)
        self.assertEqual(good["id"], "rsvc-2")

    def test_service_unknown_region_rejected(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_region_service(
                self.program_id, "regn-99", "svc-1", "compute", MEMBER)

    def test_posture_derived_counts(self):
        east = self.make_region()
        west = self.ext.register_region(
            self.program_id, "region-west", "GovCloud (US-West)", MEMBER)
        self.ext.record_region_service(
            self.program_id, east["id"], "svc-c1", "compute", MEMBER)
        self.ext.record_region_service(
            self.program_id, west["id"], "svc-c2", "compute", MEMBER)
        self.ext.record_region_service(
            self.program_id, east["id"], "svc-s1", "storage", MEMBER)
        posture = self.ext.platform_posture(self.program_id, MEMBER)
        self.assertEqual(posture["regions"], 2)
        self.assertEqual(posture["services"], 3)
        self.assertEqual(
            posture["services_by_category"],
            {"compute": 2, "storage": 1, "networking": 0,
             "database": 0, "other": 0},
        )
        self.assertEqual(posture["attestations"], 0)
        self.assertIs(posture["operated_here"], False)
        self.assertIs(posture["verified_here"], False)
        self.assertIs(posture["derived"], True)

    def test_stored_region_carries_no_derived_key(self):
        region = self.make_region()
        self.ext.record_region_service(
            self.program_id, region["id"], "svc-c1", "compute", MEMBER)
        stored = self.ext.get_region(self.program_id, region["id"], MEMBER)
        for derived_key in ("services", "services_by_category",
                            "attestations", "attestations_by_kind"):
            self.assertNotIn(derived_key, stored)


class TestRegionAttestationsBuilt(BatchFixture):
    """Entry (idx 405): Region operations & sovereignty properties —
    built as provider attestation records stored verbatim. The
    properties are the provider's; nothing here verifies or
    enforces one."""

    def setUp(self):
        super().setUp()
        self.region = self.make_region()

    def test_attestation_shape_and_labels_verbatim(self):
        attestation = self.ext.record_region_attestation(
            self.program_id, self.region["id"], "physical_operation",
            "Operated on US soil by US citizens", MEMBER)
        self.assertEqual(attestation["id"], "ratt-1")
        self.assertEqual(
            set(attestation),
            {
                "id", "program_id", "region_id", "attestation_kind",
                "statement_label", "attested_by_provider",
                "verified_here", "enforced_here", "created_by",
                "created_utc",
            },
        )
        self.assertEqual(
            attestation["statement_label"],
            "Operated on US soil by US citizens")
        self.assertIs(attestation["attested_by_provider"], True)
        self.assertIs(attestation["verified_here"], False)
        self.assertIs(attestation["enforced_here"], False)
        self.assertNotIn("reference_stub", attestation)

    def test_bad_kind_rejected_and_no_id_consumed(self):
        with self.assertRaises(ValidationError):
            self.ext.record_region_attestation(
                self.program_id, self.region["id"], "marketing",
                "A statement", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_region_attestation(
                self.program_id, self.region["id"],
                "physical_operation", "  ", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_region_attestation(
                self.program_id, "regn-99", "physical_operation",
                "A statement", MEMBER)
        good = self.ext.record_region_attestation(
            self.program_id, self.region["id"], "handling_environment",
            "ITAR-regulated environment", MEMBER)
        self.assertEqual(good["id"], "ratt-1")

    def test_attestation_leaves_region_record_identical(self):
        before = self.ext.get_region(
            self.program_id, self.region["id"], MEMBER)
        self.ext.record_region_attestation(
            self.program_id, self.region["id"],
            "authorization_boundary", "FedRAMP High boundary", MEMBER)
        after = self.ext.get_region(
            self.program_id, self.region["id"], MEMBER)
        self.assertEqual(before, after)

    def test_posture_counts_by_kind(self):
        self.ext.record_region_attestation(
            self.program_id, self.region["id"], "personnel_eligibility",
            "Root account holders screened", MEMBER)
        self.ext.record_region_attestation(
            self.program_id, self.region["id"],
            "authorization_boundary", "FedRAMP High boundary", MEMBER)
        self.ext.record_region_attestation(
            self.program_id, self.region["id"],
            "authorization_boundary", "Boundary statement two", MEMBER)
        posture = self.ext.platform_posture(self.program_id, MEMBER)
        self.assertEqual(posture["attestations"], 3)
        self.assertEqual(
            posture["attestations_by_kind"],
            {"personnel_eligibility": 1, "physical_operation": 0,
             "handling_environment": 0, "authorization_boundary": 2},
        )


class TestScreeningBuilt(BatchFixture):
    """Entry (idx 406): Eligibility screening of root account
    holders — built as screening case records (opaque refs only)
    plus outcome reports stored verbatim. No check is run and no
    determination is computed here."""

    def test_case_shape_and_labels(self):
        case = self.ext.record_screening_case(
            self.program_id, "root-acct-001", MEMBER,
            basis_label="new root account")
        self.assertEqual(case["id"], "scrn-1")
        self.assertEqual(
            set(case),
            {
                "id", "program_id", "account_ref", "basis_label",
                "screened_here", "determined_here", "state",
                "created_by", "created_utc",
            },
        )
        self.assertIs(case["screened_here"], False)
        self.assertIs(case["determined_here"], False)
        self.assertEqual(case["state"], "recorded_case_only")
        self.assertNotIn("reference_stub", case)

    def test_duplicate_account_ref_rejected(self):
        self.ext.record_screening_case(
            self.program_id, "root-acct-001", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_screening_case(
                self.program_id, "root-acct-001", MEMBER)
        second = self.ext.record_screening_case(
            self.program_id, "root-acct-002", MEMBER)
        self.assertEqual(second["id"], "scrn-2")

    def test_report_verbatim_and_case_byte_identical(self):
        case = self.ext.record_screening_case(
            self.program_id, "root-acct-001", MEMBER)
        before = self.ext.get_screening_case(
            self.program_id, case["id"], MEMBER)
        report = self.ext.record_screening_report(
            self.program_id, case["id"], "reported_eligible", MEMBER,
            detail="operator ref SCR-9")
        self.assertEqual(report["id"], "srpt-1")
        self.assertEqual(
            set(report),
            {
                "id", "program_id", "case_id", "outcome", "detail",
                "screened_here", "determined_here", "created_by",
                "created_utc",
            },
        )
        self.assertEqual(report["outcome"], "reported_eligible")
        self.assertEqual(report["detail"], "operator ref SCR-9")
        after = self.ext.get_screening_case(
            self.program_id, case["id"], MEMBER)
        self.assertEqual(before, after)

    def test_bad_outcome_rejected_and_no_id_consumed(self):
        case = self.ext.record_screening_case(
            self.program_id, "root-acct-001", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_screening_report(
                self.program_id, case["id"], "eligible_for_sure", MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_screening_report(
                self.program_id, "scrn-99", "reported_eligible", MEMBER)
        good = self.ext.record_screening_report(
            self.program_id, case["id"], "reported_pending", MEMBER)
        self.assertEqual(good["id"], "srpt-1")

    def test_summary_derived(self):
        first = self.ext.record_screening_case(
            self.program_id, "root-acct-001", MEMBER)
        second = self.ext.record_screening_case(
            self.program_id, "root-acct-002", MEMBER)
        self.ext.record_screening_report(
            self.program_id, first["id"], "reported_eligible", MEMBER)
        self.ext.record_screening_report(
            self.program_id, second["id"], "reported_pending", MEMBER)
        summary = self.ext.screening_summary(self.program_id, MEMBER)
        self.assertEqual(summary["cases"], 2)
        self.assertEqual(summary["reports"], 2)
        self.assertEqual(
            summary["reports_by_outcome"],
            {"reported_eligible": 1, "reported_ineligible": 0,
             "reported_pending": 1},
        )
        self.assertIs(summary["screened_here"], False)
        self.assertIs(summary["determined_here"], False)
        self.assertIs(summary["derived"], True)

    def test_no_execution_surface_exists(self):
        """The category's standing named absence — trading &
        investment execution — stands: this class has no order,
        execution, or payment operation of any kind."""
        for name in ("create_trade_order", "execute_trade",
                     "place_trade", "buy", "sell", "execute_payment",
                     "make_payment", "transfer_funds",
                     "provision_region", "start_region"):
            self.assertFalse(
                hasattr(FinanceExtensions, name),
                "unexpected execution surface: %s" % name)


class TestMonitoringReference(BatchFixture):
    """Entry (idx 407): Collaborative continuous monitoring with
    the provider — reference (stub-engine, as drafted): arrangement
    records plus status report records, every record labeled
    ``reference_stub`` / ``reference_transport``; nothing is
    monitored here."""

    def test_arrangement_shape_and_stub_labels(self):
        arrangement = self.ext.register_monitoring_arrangement(
            self.program_id, "mon-arr-1", MEMBER,
            scope_label="region status")
        self.assertEqual(arrangement["id"], "marr-1")
        self.assertEqual(
            set(arrangement),
            {
                "id", "program_id", "arrangement_ref", "scope_label",
                "reference_stub", "reference_transport",
                "monitored_here", "state", "created_by", "created_utc",
            },
        )
        self.assertIs(arrangement["reference_stub"], True)
        self.assertIs(arrangement["reference_transport"], True)
        self.assertIs(arrangement["monitored_here"], False)
        self.assertEqual(arrangement["state"], "recorded_arrangement_only")

    def test_duplicate_arrangement_ref_rejected(self):
        self.ext.register_monitoring_arrangement(
            self.program_id, "mon-arr-1", MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.register_monitoring_arrangement(
                self.program_id, "mon-arr-1", MEMBER)
        second = self.ext.register_monitoring_arrangement(
            self.program_id, "mon-arr-2", MEMBER)
        self.assertEqual(second["id"], "marr-2")

    def test_report_labels_and_event_count_validation(self):
        arrangement = self.ext.register_monitoring_arrangement(
            self.program_id, "mon-arr-1", MEMBER)
        report = self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_healthy",
            MEMBER, events_reported=12, detail="weekly status")
        self.assertEqual(report["id"], "mrpt-1")
        self.assertEqual(
            set(report),
            {
                "id", "program_id", "arrangement_id", "outcome",
                "events_reported", "detail", "reference_stub",
                "reference_transport", "monitored_here", "created_by",
                "created_utc",
            },
        )
        self.assertIs(report["reference_stub"], True)
        self.assertEqual(report["events_reported"], 12)
        for bad_count in (1.5, True, -1, "12"):
            with self.assertRaises(ValidationError):
                self.ext.record_monitoring_report(
                    self.program_id, arrangement["id"],
                    "reported_healthy", MEMBER, events_reported=bad_count)
        with self.assertRaises(ValidationError):
            self.ext.record_monitoring_report(
                self.program_id, arrangement["id"], "all_good", MEMBER)
        good = self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_degraded",
            MEMBER)
        self.assertEqual(good["id"], "mrpt-2")

    def test_summary_derived(self):
        arrangement = self.ext.register_monitoring_arrangement(
            self.program_id, "mon-arr-1", MEMBER)
        self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_healthy",
            MEMBER, events_reported=3)
        self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_healthy",
            MEMBER, events_reported=4)
        self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_incident",
            MEMBER)
        summary = self.ext.monitoring_summary(self.program_id, MEMBER)
        self.assertEqual(summary["arrangements"], 1)
        self.assertEqual(summary["reports"], 3)
        self.assertEqual(
            summary["reports_by_outcome"],
            {"reported_healthy": 2, "reported_degraded": 0,
             "reported_incident": 1, "reported_outage": 0},
        )
        self.assertEqual(summary["total_events_reported"], 7)
        self.assertIs(summary["reference_stub"], True)
        self.assertIs(summary["monitored_here"], False)
        self.assertIs(summary["derived"], True)


class TestCountByLabelNegativeControl(BatchFixture):
    """Fresh negative control for the batch: the by-label count
    seam ``_count_by_label`` in ``finance/extensions.py``.

    Traced claim: **the derived views of this surface (platform
    posture, screening summary, monitoring summary) report the
    counts of the records actually recorded** — every figure in
    them is a count of recorded labels, derived at read. The
    mutant builds the result dict with every label at zero and
    never counts the records, so every view it fed would report
    an empty platform, no screening outcomes, and no monitoring
    outcomes while the records exist. Each canonical case asserts
    (1) the real seam and the real views return the recorded
    counts, (2) the mutant returns all-zero counts for the same
    records, and (3) treating the mutant's outcome as the
    canonical expectation fails. The sanity case pins that the
    mutant is weakened, not broken: over zero records both agree.
    """

    def build_scenario(self):
        east = self.make_region()
        west = self.ext.register_region(
            self.program_id, "region-west", "GovCloud (US-West)", MEMBER)
        self.ext.record_region_service(
            self.program_id, east["id"], "svc-c1", "compute", MEMBER)
        self.ext.record_region_service(
            self.program_id, west["id"], "svc-c2", "compute", MEMBER)
        self.ext.record_region_service(
            self.program_id, east["id"], "svc-s1", "storage", MEMBER)
        self.ext.record_region_attestation(
            self.program_id, east["id"], "personnel_eligibility",
            "Root account holders screened", MEMBER)
        self.ext.record_region_attestation(
            self.program_id, east["id"], "authorization_boundary",
            "FedRAMP High boundary", MEMBER)
        self.ext.record_region_attestation(
            self.program_id, west["id"], "authorization_boundary",
            "Boundary statement two", MEMBER)
        first = self.ext.record_screening_case(
            self.program_id, "root-acct-001", MEMBER)
        second = self.ext.record_screening_case(
            self.program_id, "root-acct-002", MEMBER)
        self.ext.record_screening_report(
            self.program_id, first["id"], "reported_eligible", MEMBER)
        self.ext.record_screening_report(
            self.program_id, second["id"], "reported_pending", MEMBER)
        arrangement = self.ext.register_monitoring_arrangement(
            self.program_id, "mon-arr-1", MEMBER)
        self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_healthy",
            MEMBER, events_reported=3)
        self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_healthy",
            MEMBER, events_reported=4)
        self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_incident",
            MEMBER)

    def test_canonical_counts_from_seam(self):
        records = [{"category": "compute"}, {"category": "compute"},
                   {"category": "storage"}]
        self.assertEqual(
            _count_by_label(records, "category", SERVICE_LABELS),
            {"compute": 2, "storage": 1, "networking": 0,
             "database": 0, "other": 0},
        )

    def test_canonical_counts_match_views(self):
        self.build_scenario()
        posture = self.ext.platform_posture(self.program_id, MEMBER)
        self.assertEqual(posture["services_by_category"]["compute"], 2)
        self.assertEqual(posture["services_by_category"]["storage"], 1)
        self.assertEqual(
            posture["attestations_by_kind"]["personnel_eligibility"], 1)
        self.assertEqual(
            posture["attestations_by_kind"]["authorization_boundary"], 2)
        screening = self.ext.screening_summary(self.program_id, MEMBER)
        self.assertEqual(
            screening["reports_by_outcome"]["reported_eligible"], 1)
        self.assertEqual(
            screening["reports_by_outcome"]["reported_pending"], 1)
        monitoring = self.ext.monitoring_summary(self.program_id, MEMBER)
        self.assertEqual(
            monitoring["reports_by_outcome"]["reported_healthy"], 2)
        self.assertEqual(
            monitoring["reports_by_outcome"]["reported_incident"], 1)

    def test_mutant_returns_all_zeroes(self):
        records = [{"category": "compute"}, {"category": "compute"},
                   {"category": "storage"}]
        self.assertEqual(
            mutant_count_by_label(records, "category", SERVICE_LABELS),
            {"compute": 0, "storage": 0, "networking": 0,
             "database": 0, "other": 0},
        )

    def test_mutant_outcome_is_not_the_canonical_expectation(self):
        self.build_scenario()
        services = self.ext.list_region_services(self.program_id, MEMBER)
        canonical = _count_by_label(services, "category", SERVICE_LABELS)
        mutant = mutant_count_by_label(
            services, "category", SERVICE_LABELS)
        self.assertNotEqual(mutant, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, canonical)
        posture = self.ext.platform_posture(self.program_id, MEMBER)
        self.assertEqual(posture["services_by_category"], canonical)

    def test_mutant_agrees_on_empty_input(self):
        """Sanity: over zero records the weakened seam and the real
        seam agree (all zeroes) — the mutant is a gate that never
        counts, not a broken function."""
        empty = _count_by_label([], "category", SERVICE_LABELS)
        self.assertEqual(
            empty, mutant_count_by_label([], "category", SERVICE_LABELS))
        self.assertTrue(all(v == 0 for v in empty.values()))


class TestCrossCutting(BatchFixture):
    """Cross-cutting batch pins: RBAC + membership on the extension
    surface, the separated auditor role at High, ext_ audit actions
    with :denied denials, platform-admin reach, audit-failure
    rollback, program scoping, core state untouched, and the
    recursive forbidden-key scan across one record of every kind."""

    def test_viewer_write_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.register_region(
                self.program_id, "region-east", "GovCloud (US-East)",
                VIEWER)
        self.assertIn("ext_region_register:denied", self.audit_actions())
        self.assertEqual(self.ext.list_regions(self.program_id, MEMBER), [])

    def test_auditor_denied_extension_but_audit_duty_works(self):
        """High apparatus (AC-5): the auditor role holds audit_read
        only — every extension write AND read is denied — while its
        core audit duty (reading and verifying the hash-chained
        trail, AU-7 query) works unchanged."""
        with self.assertRaises(PermissionDenied):
            self.ext.register_region(
                self.program_id, "region-east", "GovCloud (US-East)",
                AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.list_regions(self.program_id, AUDITOR)
        with self.assertRaises(PermissionDenied):
            self.ext.platform_posture(self.program_id, AUDITOR)
        self.assertIn("ext_region_register:denied", self.audit_actions())
        denied = self.audit.query(action="ext_region_register:denied")
        self.assertGreaterEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "dana")
        ok, first_bad = self.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)

    def test_outsider_denied_by_membership(self):
        with self.assertRaises(PermissionDenied):
            self.ext.record_screening_case(
                self.program_id, "root-acct-001", OUTSIDER)
        self.assertEqual(
            self.ext.list_screening_cases(self.program_id, MEMBER), [])

    def test_admin_reaches_program_and_audit_records_ext_actions(self):
        region = self.ext.register_region(
            self.program_id, "region-east", "GovCloud (US-East)", ADMIN)
        self.assertEqual(region["id"], "regn-1")
        self.assertIn("ext_region_register", self.audit_actions())
        ok, first_bad = self.audit.verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)

    def test_cross_program_records_not_visible(self):
        other = self.store.create_program("other-program", MEMBER)
        region = self.make_region()
        with self.assertRaises(NotFoundError):
            self.ext.get_region(other["id"], region["id"], MEMBER)
        self.assertEqual(self.ext.list_regions(other["id"], MEMBER), [])

    def test_audit_failure_rolls_back_record_and_id(self):
        class Boom:
            def record(self, *args, **kwargs):
                raise RuntimeError("audit unavailable")

        real_audit = self.store.audit
        self.store.audit = Boom()
        try:
            with self.assertRaises(RuntimeError):
                self.ext.register_region(
                    self.program_id, "region-east",
                    "GovCloud (US-East)", MEMBER)
        finally:
            self.store.audit = real_audit
        self.assertEqual(self.ext.list_regions(self.program_id, MEMBER), [])
        region = self.make_region()
        self.assertEqual(region["id"], "regn-1")

    def test_extension_flow_changes_no_core_state(self):
        employee = make_employee(self.store, self.program_id)
        accrual = make_accrual(
            self.store, self.program_id, employee["id"], PERIOD, 100000)
        program_before = self.store.get_program(self.program_id, MEMBER)
        accrual_before = self.store.get_accrual(
            self.program_id, accrual["id"], MEMBER)
        summary_before = self.store.program_summary(
            self.program_id, PERIOD, MEMBER)
        region = self.make_region()
        self.ext.record_region_service(
            self.program_id, region["id"], "svc-c1", "compute", MEMBER)
        self.ext.record_region_attestation(
            self.program_id, region["id"], "physical_operation",
            "Operated on US soil by US citizens", MEMBER)
        case = self.ext.record_screening_case(
            self.program_id, "root-acct-001", MEMBER)
        self.ext.record_screening_report(
            self.program_id, case["id"], "reported_eligible", MEMBER)
        arrangement = self.ext.register_monitoring_arrangement(
            self.program_id, "mon-arr-1", MEMBER)
        self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_healthy",
            MEMBER, events_reported=1)
        self.assertEqual(
            self.store.get_program(self.program_id, MEMBER), program_before)
        self.assertEqual(
            self.store.get_accrual(self.program_id, accrual["id"], MEMBER),
            accrual_before)
        self.assertEqual(
            self.store.program_summary(self.program_id, PERIOD, MEMBER),
            summary_before)

    def _one_of_every_kind(self):
        region = self.make_region()
        service = self.ext.record_region_service(
            self.program_id, region["id"], "svc-c1", "compute", MEMBER)
        attestation = self.ext.record_region_attestation(
            self.program_id, region["id"], "physical_operation",
            "Operated on US soil by US citizens", MEMBER)
        case = self.ext.record_screening_case(
            self.program_id, "root-acct-001", MEMBER)
        report = self.ext.record_screening_report(
            self.program_id, case["id"], "reported_eligible", MEMBER)
        arrangement = self.ext.register_monitoring_arrangement(
            self.program_id, "mon-arr-1", MEMBER)
        monitoring_report = self.ext.record_monitoring_report(
            self.program_id, arrangement["id"], "reported_healthy",
            MEMBER, events_reported=1)
        return (region, service, attestation, case, report, arrangement,
                monitoring_report)

    def test_forbidden_keys_absent_across_all_kinds(self):
        """Money discipline and identity discipline, by scan: no
        record on this surface carries a money field (no ``*_cents``
        key at all — none of the four entries is a money function),
        a bank-detail key, a score key, or a computed-figure key."""
        records = self._one_of_every_kind()
        self.assertEqual(len(records), 7)
        fragments = ("score", "account_number", "routing", "iban",
                     "sort_code", "card_number", "bank", "credit",
                     "ssn", "passport", "license_number")
        exact_banned = {"rate", "trend", "forecast", "average",
                        "grand_total", "total"}
        for record in records:
            keys = all_keys(record)
            for key in keys:
                self.assertFalse(
                    key.endswith("_cents"),
                    "money field %r on %s" % (key, record["id"]))
                self.assertNotIn(key, exact_banned)
                for fragment in fragments:
                    self.assertNotIn(fragment, key.lower())

    def test_built_records_carry_no_reference_stub(self):
        records = self._one_of_every_kind()
        built = records[:5]
        reference = records[5:]
        for record in built:
            self.assertNotIn("reference_stub", record)
        for record in reference:
            self.assertIs(record["reference_stub"], True)
            self.assertIs(record["reference_transport"], True)


if __name__ == "__main__":
    unittest.main()
