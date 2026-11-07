"""Final-GAPS-batch extension surface — Group 33, GRC L2.

Pins the records built in ``src/grc/extensions.py`` for the
seven Extended functions registered under this group's GAPS.md
section (inventory idx 353–359), per ``../../gaps-batch/
DECISION.md``. Every test traces to an entry in ``../BATCH.md``.

The category doctrine binds this surface exactly as it binds
the core: posture is counts only and no key mentioning score /
rating / grade / percent exists anywhere (recursive scan
below); reported statuses, outcomes, priorities, and values
are stored verbatim, never computed; date-based figures are
derived at read, never stored.
"""

import unittest

from grc.audit import AuditLog
from grc.errors import NotFoundError, PermissionDenied, ValidationError
from grc.extensions import GrcExtensions

from grc_helpers import (
    ADMIN,
    MEMBER,
    SEED_FRAMEWORK_ID,
    VIEWER,
    fresh_store,
    make_finding,
    make_indicator,
    make_store,
    make_system,
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


def make_extensions():
    """A core store (canonical system + indicator) and its
    extension surface, sharing one audit log."""
    audit = AuditLog()
    store, _system, _indicator = make_store(audit=audit)
    return GrcExtensions(store), store, audit


def make_evidence(store, actor=MEMBER, name="config export"):
    return store.create_evidence(
        name, "artifact-content", ["IA-2"], ["SYS-001"], actor=actor)


class TestCollectionSourcesAndValidation(unittest.TestCase):
    """Entry idx 353 — automated evidence-validation engine,
    incl. API / telemetry evidence collection: source and job
    definitions as data; outcomes as verbatim report records;
    nothing collected, nothing validated here."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_collection_source_record_shape_and_labels(self):
        source = self.ext.register_collection_source(
            "api", "SYS-001", "config API collector", actor=MEMBER)
        self.assertEqual(source["id"], "col-1")
        self.assertEqual(source["kind"], "api")
        self.assertEqual(source["system_ref"], "SYS-001")
        self.assertIs(source["reference_transport"], True)
        self.assertIs(source["collected_here"], False)
        self.assertEqual(source["recorded_by"], "bob")
        telemetry = self.ext.register_collection_source(
            "telemetry", "SYS-001", "host telemetry tap", actor=ADMIN)
        self.assertEqual(telemetry["id"], "col-2")
        self.assertEqual(
            self.ext.list_collection_sources(VIEWER)[1]["kind"], "telemetry")
        self.assertEqual(
            self.ext.list_collection_sources(VIEWER, system_ref="SYS-001"),
            self.ext.list_collection_sources(VIEWER))
        self.assertEqual(self.ext.list_collection_sources(
            VIEWER, system_ref="SYS-404"), [])

    def test_collection_source_rejects_bad_kind_and_unknown_system(self):
        with self.assertRaises(ValidationError):
            self.ext.register_collection_source(
                "carrier-pigeon", "SYS-001", "x", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.register_collection_source(
                "api", "SYS-404", "x", actor=MEMBER)
        # Failed operations consume no id.
        source = self.ext.register_collection_source(
            "api", "SYS-001", "ok", actor=MEMBER)
        self.assertEqual(source["id"], "col-1")

    def test_validation_job_labels_and_evidence_link(self):
        evidence = make_evidence(self.store)
        job = self.ext.create_validation_job(evidence["id"], "AuditShield",
                                             actor=MEMBER)
        self.assertEqual(job["id"], "vjob-1")
        self.assertEqual(job["evidence_id"], evidence["id"])
        self.assertIs(job["reference_stub"], True)
        self.assertIs(job["validated_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.create_validation_job("ev-404", "engine", actor=MEMBER)
        job2 = self.ext.create_validation_job(evidence["id"], "engine",
                                              actor=MEMBER)
        self.assertEqual(job2["id"], "vjob-2")

    def test_validation_report_verbatim_and_core_evidence_untouched(self):
        evidence = make_evidence(self.store)
        before = self.store.get_evidence(evidence["id"], ADMIN)
        job = self.ext.create_validation_job(evidence["id"], "AuditShield",
                                             actor=MEMBER)
        report = self.ext.record_validation_report(
            job["id"], "Passed w/ Observations", actor=MEMBER,
            reported_utc="2026-07-01T09:30:00+00:00")
        self.assertEqual(report["id"], "vrep-1")
        self.assertEqual(report["reported_status"], "Passed w/ Observations")
        self.assertEqual(report["evidence_id"], evidence["id"])
        self.assertEqual(report["reported_utc"], "2026-07-01T09:30:00+00:00")
        # The report does NOT set the core record's validation
        # status: only a reviewer's core review does that.
        after = self.store.get_evidence(evidence["id"], ADMIN)
        self.assertEqual(after, before)
        self.assertEqual(after["validation_status"], "unvalidated")
        self.assertEqual(
            len(self.ext.list_validation_reports(VIEWER, job_id=job["id"])), 1)

    def test_validation_report_rejects_bad_timestamp_and_unknown_job(self):
        evidence = make_evidence(self.store)
        job = self.ext.create_validation_job(evidence["id"], "e", actor=MEMBER)
        with self.assertRaises(ValidationError):
            self.ext.record_validation_report(job["id"], "ok", actor=MEMBER,
                                              reported_utc="not-a-time")
        with self.assertRaises(NotFoundError):
            self.ext.record_validation_report("vjob-404", "ok", actor=MEMBER)
        report = self.ext.record_validation_report(job["id"], "ok",
                                                   actor=MEMBER)
        self.assertEqual(report["id"], "vrep-1")


class TestFeeds(unittest.TestCase):
    """Entry idx 354 — continuous-monitoring feeds & scanner
    integrations: definitions as data; receipts as records about
    the feed; nothing connected, nothing ingested, and a receipt
    creates no core record."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_feed_record_shape_and_labels(self):
        feed = self.ext.register_feed("monitoring_feed", "SYS-001",
                                      "conmon feed", actor=MEMBER)
        self.assertEqual(feed["id"], "feed-1")
        self.assertIs(feed["reference_stub"], True)
        self.assertIs(feed["reference_transport"], True)
        self.assertIs(feed["connected_here"], False)
        self.assertIs(feed["ingested_here"], False)
        with self.assertRaises(ValidationError):
            self.ext.register_feed("smoke-signal", "SYS-001", "x",
                                   actor=MEMBER)

    def test_feed_receipt_creates_no_core_result_or_finding(self):
        feed = self.ext.register_feed("scanner_integration", "SYS-001",
                                      "scanner link", actor=MEMBER)
        results_before = len(self.store.list_indicator_results(ADMIN))
        findings_before = len(self.store.list_findings(ADMIN))
        receipt = self.ext.record_feed_receipt(
            feed["id"], "Feed Reported OK", 7, actor=MEMBER)
        self.assertEqual(receipt["id"], "rcpt-1")
        self.assertEqual(receipt["reported_status"], "Feed Reported OK")
        self.assertEqual(receipt["reported_count"], 7)
        self.assertEqual(len(self.store.list_indicator_results(ADMIN)),
                         results_before)
        self.assertEqual(len(self.store.list_findings(ADMIN)),
                         findings_before)

    def test_feed_receipt_rejects_non_integer_counts(self):
        feed = self.ext.register_feed("monitoring_feed", "SYS-001", "f",
                                      actor=MEMBER)
        for bad in (True, 1.5, -1, "7"):
            with self.assertRaises(ValidationError):
                self.ext.record_feed_receipt(feed["id"], "ok", bad,
                                             actor=MEMBER)
        receipt = self.ext.record_feed_receipt(feed["id"], "ok", 0,
                                               actor=MEMBER)
        self.assertEqual(receipt["id"], "rcpt-1")


class TestScanRecords(unittest.TestCase):
    """Entry idx 355 — vulnerability scanning engine
    (prioritization / scoring of findings): scan jobs and reports
    as records; priority labels recorded verbatim against core
    findings; nothing scanned, nothing prioritized or computed
    here, and a scan report creates no core finding."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_scan_job_labels(self):
        job = self.ext.create_scan_job("SYS-001", "scanner-x", actor=MEMBER,
                                       scope_label="weekly sweep")
        self.assertEqual(job["id"], "scan-1")
        self.assertIs(job["scanned_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.create_scan_job("SYS-404", "scanner-x", actor=MEMBER)

    def test_scan_report_verbatim_and_creates_no_core_finding(self):
        job = self.ext.create_scan_job("SYS-001", "scanner-x", actor=MEMBER)
        before = len(self.store.list_findings(ADMIN))
        report = self.ext.record_scan_report(job["id"], "Completed (Partial)",
                                             3, actor=MEMBER)
        self.assertEqual(report["id"], "srep-1")
        self.assertEqual(report["reported_outcome"], "Completed (Partial)")
        self.assertEqual(report["findings_reported"], 3)
        self.assertEqual(report["system_ref"], "SYS-001")
        self.assertEqual(len(self.store.list_findings(ADMIN)), before)
        with self.assertRaises(ValidationError):
            self.ext.record_scan_report(job["id"], "ok", 2.5, actor=MEMBER)

    def test_finding_priority_verbatim_and_core_finding_untouched(self):
        finding = make_finding(self.store)
        before = self.store.get_finding(finding["id"], ADMIN)
        priority = self.ext.record_finding_priority(
            finding["id"], "P1 - Fix First", actor=MEMBER,
            reporter="scanner-x")
        self.assertEqual(priority["id"], "prio-1")
        self.assertEqual(priority["reported_priority"], "P1 - Fix First")
        self.assertIs(priority["prioritized_here"], False)
        self.assertIs(priority["computed_here"], False)
        self.assertEqual(self.store.get_finding(finding["id"], ADMIN), before)
        with self.assertRaises(NotFoundError):
            self.ext.record_finding_priority("find-404", "P9", actor=MEMBER)


class TestKsiRuns(unittest.TestCase):
    """Entry idx 356 — automated KSI validation: run definitions
    and verbatim run reports; nothing evaluated here, and a run
    report creates NO core indicator result."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_ksi_run_labels_and_links(self):
        run = self.ext.create_ksi_run("KSI-1", "SYS-001", "AuditShield",
                                      actor=MEMBER)
        self.assertEqual(run["id"], "krun-1")
        self.assertIs(run["reference_stub"], True)
        self.assertIs(run["validated_here"], False)
        self.assertIs(run["evaluated_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.create_ksi_run("KSI-404", "SYS-001", "e", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_ksi_run("KSI-1", "SYS-404", "e", actor=MEMBER)

    def test_ksi_report_verbatim_and_creates_no_core_result(self):
        run = self.ext.create_ksi_run("KSI-1", "SYS-001", "AuditShield",
                                      actor=MEMBER)
        before = len(self.store.list_indicator_results(ADMIN))
        report = self.ext.record_ksi_report(run["id"], "Meets Threshold",
                                            actor=MEMBER)
        self.assertEqual(report["id"], "krep-1")
        self.assertEqual(report["reported_status"], "Meets Threshold")
        self.assertEqual(report["indicator_id"], "KSI-1")
        self.assertEqual(len(self.store.list_indicator_results(ADMIN)),
                         before)
        # The core's own recording path still works independently.
        self.store.record_indicator_result("KSI-1", "SYS-001", "recorded",
                                           actor=MEMBER)
        self.assertEqual(len(self.store.list_indicator_results(ADMIN)),
                         before + 1)


class TestReportedValues(unittest.TestCase):
    """Entry idx 357 — posture / risk scoring engines: the
    engine's reported values recorded verbatim as labels with
    their reported scale; nothing computed here, and the core
    posture summary neither reads nor reflects these records."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_reported_value_record_shape(self):
        value = self.ext.record_reported_value(
            "SYS-001", "vendor-engine", "87", actor=MEMBER,
            scale_label="0-100 vendor scale",
            reported_utc="2026-07-02T00:00:00Z")
        self.assertEqual(value["id"], "rval-1")
        self.assertEqual(value["value_label"], "87")
        self.assertEqual(value["scale_label"], "0-100 vendor scale")
        self.assertEqual(value["reported_utc"], "2026-07-02T00:00:00Z")
        self.assertIs(value["computed_here"], False)
        self.assertIsNone(value["framework_id"])
        with_framework = self.ext.record_reported_value(
            "SYS-001", "assessor", "B+", actor=ADMIN,
            framework_id=SEED_FRAMEWORK_ID)
        self.assertEqual(with_framework["framework_id"], SEED_FRAMEWORK_ID)

    def test_reported_value_validates_references(self):
        with self.assertRaises(NotFoundError):
            self.ext.record_reported_value("SYS-404", "e", "1", actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.record_reported_value(
                "SYS-001", "e", "1", actor=MEMBER, framework_id="NOPE")
        with self.assertRaises(ValidationError):
            self.ext.record_reported_value("SYS-001", "e", "  ", actor=MEMBER)
        value = self.ext.record_reported_value("SYS-001", "e", "1",
                                               actor=MEMBER)
        self.assertEqual(value["id"], "rval-1")

    def test_core_posture_ignores_reported_values(self):
        before = self.store.posture_summary(ADMIN, as_of="2026-07-01")
        self.ext.record_reported_value("SYS-001", "vendor-engine", "87",
                                       actor=MEMBER)
        self.ext.record_reported_value("SYS-001", "assessor", "B+",
                                       actor=ADMIN)
        after = self.store.posture_summary(ADMIN, as_of="2026-07-01")
        self.assertEqual(before, after)
        summary = self.ext.extension_summary(VIEWER)
        self.assertEqual(summary["reported_values"]["total"], 2)
        self.assertEqual(summary["reported_values"]["by_value_label"],
                         {"87": 1, "B+": 1})
        self.assertEqual(summary["reported_values"]["by_reporter"],
                         {"vendor-engine": 1, "assessor": 1})


class TestEnclaveOperations(unittest.TestCase):
    """Entry idx 358 — hosted enclave & PaaS operations
    themselves: environment and operation records over core
    governed systems; nothing hosted or operated here."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_environment_record_labels(self):
        env = self.ext.register_environment("SYS-001", "govcloud enclave",
                                            actor=MEMBER)
        self.assertEqual(env["id"], "env-1")
        self.assertIs(env["reference_stub"], True)
        self.assertIs(env["hosted_here"], False)
        self.assertIs(env["operated_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.register_environment("SYS-404", "x", actor=MEMBER)

    def test_operation_record_verbatim(self):
        env = self.ext.register_environment("SYS-001", "govcloud enclave",
                                            actor=MEMBER)
        operation = self.ext.record_operation(
            env["id"], "patch window", "Completed by platform team",
            actor=MEMBER)
        self.assertEqual(operation["id"], "op-1")
        self.assertEqual(operation["operation_kind"], "patch window")
        self.assertEqual(operation["reported_outcome"],
                         "Completed by platform team")
        self.assertEqual(operation["system_ref"], "SYS-001")
        with self.assertRaises(NotFoundError):
            self.ext.record_operation("env-404", "x", "y", actor=MEMBER)
        summary = self.ext.extension_summary(VIEWER)
        self.assertEqual(summary["operations"]["by_kind"],
                         {"patch window": 1})


class TestPackages(unittest.TestCase):
    """Entry idx 359 — FedRAMP authorization package generation:
    the package record stores no figures; the manifest view is
    derived at read from core records (references and counts
    only) and tracks registry state; nothing is generated as a
    document, exported, or submitted."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()

    def test_package_record_stores_no_figures(self):
        package = self.ext.create_package("SYS-001", SEED_FRAMEWORK_ID,
                                          actor=MEMBER)
        self.assertEqual(package["id"], "pkg-1")
        self.assertEqual(
            set(package),
            {"id", "system_ref", "framework_id", "note", "submitted_here",
             "exported_here", "recorded_by", "recorded_utc"})
        self.assertIs(package["submitted_here"], False)
        self.assertIs(package["exported_here"], False)
        with self.assertRaises(NotFoundError):
            self.ext.create_package("SYS-404", SEED_FRAMEWORK_ID,
                                    actor=MEMBER)
        with self.assertRaises(NotFoundError):
            self.ext.create_package("SYS-001", "NOPE", actor=MEMBER)

    def test_package_view_derives_from_core_records(self):
        finding = make_finding(self.store)  # due 2026-06-30, open
        evidence = make_evidence(self.store)
        self.store.create_assessment("SYS-001", SEED_FRAMEWORK_ID, "full",
                                     "assessor-1", "2026-06-01", "satisfied",
                                     actor=MEMBER)
        auth = self.store.create_authorization("SYS-001", SEED_FRAMEWORK_ID,
                                               actor=ADMIN)
        self.store.record_indicator_result("KSI-1", "SYS-001", "passing",
                                           actor=MEMBER)
        package = self.ext.create_package("SYS-001", SEED_FRAMEWORK_ID,
                                          actor=MEMBER)
        view = self.ext.package_view(package["id"], VIEWER,
                                     as_of="2026-07-01")
        self.assertEqual(view["controls_total"], 21)
        self.assertEqual(view["authorizations"],
                         [{"id": auth["id"], "status": "not_started"}])
        self.assertEqual(len(view["assessments"]), 1)
        self.assertEqual(view["evidence"]["total"], 1)
        self.assertEqual(view["evidence"]["by_validation_status"],
                         {"unvalidated": 1})
        self.assertEqual(view["findings"]["total"], 1)
        self.assertEqual(view["findings"]["by_status"], {"open": 1})
        self.assertEqual(view["findings"]["overdue"], 1)
        self.assertEqual(view["indicator_results"]["total"], 1)
        self.assertEqual(view["indicator_results"]["by_status"],
                         {"passing": 1})
        self.assertIs(view["submitted_here"], False)
        self.assertIs(view["exported_here"], False)
        # Same record, earlier as-of: the finding is not yet overdue.
        earlier = self.ext.package_view(package["id"], VIEWER,
                                        as_of="2026-06-30")
        self.assertEqual(earlier["findings"]["overdue"], 0)

    def test_package_view_tracks_registry_state(self):
        package = self.ext.create_package("SYS-001", SEED_FRAMEWORK_ID,
                                          actor=MEMBER)
        first = self.ext.package_view(package["id"], VIEWER,
                                      as_of="2026-07-01")
        self.assertEqual(first["evidence"]["total"], 0)
        self.assertEqual(first["findings"]["total"], 0)
        make_evidence(self.store)
        make_finding(self.store)
        second = self.ext.package_view(package["id"], VIEWER,
                                       as_of="2026-07-01")
        self.assertEqual(second["evidence"]["total"], 1)
        self.assertEqual(second["findings"]["total"], 1)
        self.assertEqual(second["findings"]["overdue"], 1)
        # The stored package record itself never gained a figure.
        stored = self.ext.get_package(package["id"], VIEWER)
        self.assertNotIn("evidence", stored)
        self.assertNotIn("findings", stored)

    def test_package_view_excludes_other_systems(self):
        make_system(self.store, ref="SYS-002", name="other system")
        make_finding(self.store, system_ref="SYS-002")
        package = self.ext.create_package("SYS-001", SEED_FRAMEWORK_ID,
                                          actor=MEMBER)
        view = self.ext.package_view(package["id"], VIEWER,
                                     as_of="2026-07-01")
        self.assertEqual(view["findings"]["total"], 0)
        self.assertEqual(view["findings"]["overdue"], 0)


class TestExtensionInvariants(unittest.TestCase):
    """Cross-surface doctrine pins: the no-score recursive scan
    over every extension record kind and both derived views,
    exact record shapes, RBAC riding the core matrix, audit
    landing under ext_ actions, and failed operations consuming
    no ids anywhere."""

    def setUp(self):
        self.ext, self.store, self.audit = make_extensions()
        evidence = make_evidence(self.store)
        self.evidence = evidence
        self.ext.register_collection_source("api", "SYS-001", "collector",
                                            actor=MEMBER)
        job = self.ext.create_validation_job(evidence["id"], "engine",
                                             actor=MEMBER)
        self.ext.record_validation_report(job["id"], "pass", actor=MEMBER)
        feed = self.ext.register_feed("monitoring_feed", "SYS-001", "feed",
                                      actor=MEMBER)
        self.ext.record_feed_receipt(feed["id"], "ok", 2, actor=MEMBER)
        scan = self.ext.create_scan_job("SYS-001", "scanner", actor=MEMBER)
        self.ext.record_scan_report(scan["id"], "done", 1, actor=MEMBER)
        finding = make_finding(self.store)
        self.ext.record_finding_priority(finding["id"], "P2", actor=MEMBER)
        run = self.ext.create_ksi_run("KSI-1", "SYS-001", "engine",
                                      actor=MEMBER)
        self.ext.record_ksi_report(run["id"], "pass", actor=MEMBER)
        self.ext.record_reported_value("SYS-001", "engine", "87",
                                       actor=MEMBER)
        env = self.ext.register_environment("SYS-001", "enclave",
                                            actor=MEMBER)
        self.ext.record_operation(env["id"], "patch", "done", actor=MEMBER)
        self.package = self.ext.create_package("SYS-001", SEED_FRAMEWORK_ID,
                                               actor=MEMBER)

    def _whole_surface(self):
        ext, store = self.ext, self.store
        return [
            ext.list_collection_sources(ADMIN),
            ext.list_validation_jobs(ADMIN),
            ext.list_validation_reports(ADMIN),
            ext.list_feeds(ADMIN),
            ext.list_feed_receipts(ADMIN),
            ext.list_scan_jobs(ADMIN),
            ext.list_scan_reports(ADMIN),
            ext.list_finding_priorities(ADMIN),
            ext.list_ksi_runs(ADMIN),
            ext.list_ksi_reports(ADMIN),
            ext.list_reported_values(ADMIN),
            ext.list_environments(ADMIN),
            ext.list_operations(ADMIN),
            ext.list_packages(ADMIN),
            ext.package_view(self.package["id"], ADMIN, as_of="2026-07-01"),
            ext.extension_summary(ADMIN),
            store.posture_summary(ADMIN, as_of="2026-07-01"),
        ]

    def test_no_score_keys_anywhere_on_the_surface(self):
        for surface in self._whole_surface():
            assert_no_score_keys(self, surface)

    def test_extension_writes_are_audited_with_ext_actions(self):
        actions = [entry["action"] for entry in self.audit.entries()]
        for expected in (
            "ext_collection_source_create", "ext_validation_job_create",
            "ext_validation_report_record", "ext_feed_create",
            "ext_feed_receipt_record", "ext_scan_job_create",
            "ext_scan_report_record", "ext_finding_priority_record",
            "ext_ksi_run_create", "ext_ksi_report_record",
            "ext_reported_value_record", "ext_environment_create",
            "ext_operation_record", "ext_package_create",
        ):
            self.assertIn(expected, actions)

    def test_viewer_is_read_only_across_the_surface(self):
        attempts = [
            lambda: self.ext.register_collection_source(
                "api", "SYS-001", "x", actor=VIEWER),
            lambda: self.ext.create_validation_job(
                self.evidence["id"], "e", actor=VIEWER),
            lambda: self.ext.register_feed(
                "monitoring_feed", "SYS-001", "x", actor=VIEWER),
            lambda: self.ext.create_scan_job("SYS-001", "s", actor=VIEWER),
            lambda: self.ext.create_ksi_run("KSI-1", "SYS-001", "e",
                                            actor=VIEWER),
            lambda: self.ext.record_reported_value(
                "SYS-001", "e", "1", actor=VIEWER),
            lambda: self.ext.register_environment("SYS-001", "x",
                                                  actor=VIEWER),
            lambda: self.ext.create_package("SYS-001", SEED_FRAMEWORK_ID,
                                            actor=VIEWER),
        ]
        for attempt in attempts:
            with self.assertRaises(PermissionDenied):
                attempt()
        # Every read remains open to the viewer.
        self.assertEqual(len(self.ext.list_packages(VIEWER)), 1)
        self.assertEqual(self.ext.extension_summary(VIEWER)["packages"]
                         ["total"], 1)

    def test_summary_counts(self):
        summary = self.ext.extension_summary(ADMIN)
        self.assertEqual(summary["collection_sources"]["total"], 1)
        self.assertEqual(summary["collection_sources"]["by_kind"],
                         {"api": 1})
        self.assertEqual(summary["validation_jobs"]["total"], 1)
        self.assertEqual(summary["validation_reports"]["by_reported_status"],
                         {"pass": 1})
        self.assertEqual(summary["feeds"]["by_kind"], {"monitoring_feed": 1})
        self.assertEqual(summary["feed_receipts"]["total"], 1)
        self.assertEqual(summary["scan_jobs"]["total"], 1)
        self.assertEqual(summary["scan_reports"]["findings_reported_total"], 1)
        self.assertEqual(summary["finding_priorities"]["by_reported_priority"],
                         {"P2": 1})
        self.assertEqual(summary["ksi_runs"]["total"], 1)
        self.assertEqual(summary["ksi_reports"]["by_reported_status"],
                         {"pass": 1})
        self.assertEqual(summary["reported_values"]["total"], 1)
        self.assertEqual(summary["environments"]["total"], 1)
        self.assertEqual(summary["operations"]["total"], 1)
        self.assertEqual(summary["packages"]["total"], 1)


class NeverOverdueExtensions(GrcExtensions):
    """Mutant: the package overdue seam never counts anything —
    the live counterpart of the drill patched into the real
    module (see tests/README.md)."""

    def _package_overdue_count(self, findings, as_of_date):
        return 0


class TestPackageDerivationNegativeControl(unittest.TestCase):
    """Fresh negative control for the batch's new code.

    Traced claim: the package manifest's overdue figure is
    *derived at read* from the core findings' due dates,
    lifecycle states, and the as-of date, through the single
    seam ``_package_overdue_count``. An open finding due
    2026-06-30 derives overdue 1 at as_of 2026-07-01 and
    overdue 0 on the due date itself. The mutant collapses
    both to 0, so treating the mutant's output as the expected
    output fails — asserted literally with
    ``assertRaises(AssertionError)``.
    """

    def setUp(self):
        self.audit = AuditLog()
        self.store, _system, _indicator = make_store(audit=self.audit)
        make_finding(self.store)  # open, due 2026-06-30
        self.ext = GrcExtensions(self.store)
        self.mutant = NeverOverdueExtensions(self.store)
        self.package = self.ext.create_package("SYS-001", SEED_FRAMEWORK_ID,
                                               actor=MEMBER)
        self.mutant_package = self.mutant.create_package(
            "SYS-001", SEED_FRAMEWORK_ID, actor=MEMBER)

    def test_real_derivation_separates_the_canonical_pair(self):
        overdue = self.ext.package_view(self.package["id"], VIEWER,
                                        as_of="2026-07-01")
        current = self.ext.package_view(self.package["id"], VIEWER,
                                        as_of="2026-06-30")
        self.assertEqual(overdue["findings"]["overdue"], 1)
        self.assertEqual(current["findings"]["overdue"], 0)

    def test_mutant_collapses_both_to_zero(self):
        for as_of in ("2026-07-01", "2026-06-30"):
            view = self.mutant.package_view(self.mutant_package["id"],
                                            VIEWER, as_of=as_of)
            self.assertEqual(view["findings"]["overdue"], 0)

    def test_mutant_output_as_expectation_fails(self):
        view = self.ext.package_view(self.package["id"], VIEWER,
                                     as_of="2026-07-01")
        mutant_view = self.mutant.package_view(self.mutant_package["id"],
                                               VIEWER, as_of="2026-07-01")
        with self.assertRaises(AssertionError):
            self.assertEqual(view["findings"]["overdue"],
                             mutant_view["findings"]["overdue"])


if __name__ == "__main__":
    unittest.main()
