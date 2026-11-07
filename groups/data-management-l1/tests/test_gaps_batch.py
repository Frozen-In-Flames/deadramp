"""Final GAPS batch tests — Data Management L1 singleton.

Traces to: the five Extended functions new with this group's fork
in GAPS.md under "Singleton 38 — Data Management L1 (1 fork)",
disposed in ../BATCH.md — web crawling & snapshot capture (built,
records form), web page rendering for capture (reference,
re-judged), change detection & dynamic monitoring engine
(reference), archive storage, integrity sealing & replay / playback
(records form), full-content search & indexing over the archive
(reference) — plus the batch's fresh negative control: the
sealer/recorder separation-of-duties seam in
``datamgmt.extensions`` (test_gaps_batch.TestSealingNegativeControl).

Every test pins the honesty bound on its face: nothing in the
extension surface captures, renders, detects, seals content,
replays, indexes, or searches content, and every record says so.
"""

import unittest

from datamgmt.audit import AuditLog
from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError
from datamgmt.extensions import DataMgmtExtensions
from datamgmt.store import DataMgmtStore

from datamgmt_helpers import ADMIN, STEWARD, VIEWER


def archive_store():
    """Fresh store + an archive dataset + a crawl source."""
    audit = AuditLog()
    store = DataMgmtStore(audit=audit)
    dataset = store.create_dataset(
        "Website Archive",
        "Registry for captured website snapshots",
        STEWARD,
        classification="internal",
        tags=["archive", "web"],
        schema=[],
    )
    source = store.register_source(
        "site-crawl", "api", STEWARD, location="crawler.internal"
    )
    return store, audit, dataset, source


def make_capture(ext, store, dataset, source, recorder=STEWARD,
                 checksum="abc123", record_count=42):
    """Target + completed core ingestion + capture over it."""
    target = ext.define_crawl_target(
        dataset["id"], "Main site watch", "site-main", recorder,
        source_id=source["id"], schedule_label="nightly",
    )
    ingestion = store.record_ingestion(
        dataset["id"], source["id"], recorder, mode="full",
        record_count=record_count, checksum=checksum, status="completed",
    )
    capture = ext.record_capture(
        target["id"], ingestion["id"], recorder, pages_reported=10
    )
    return target, ingestion, capture


class TestCrawlTargets(unittest.TestCase):
    """GAPS idx 389 — crawl targets are definitions, never crawls."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = archive_store()
        self.ext = DataMgmtExtensions(self.store)

    def test_define_crawl_target_shape_and_labels(self):
        target = self.ext.define_crawl_target(
            self.dataset["id"], "Main site watch", "site-main", STEWARD,
            source_id=self.source["id"], schedule_label="nightly",
        )
        self.assertEqual(target["id"], "cwt-1")
        self.assertEqual(target["dataset_id"], self.dataset["id"])
        self.assertEqual(target["site_ref"], "site-main")
        self.assertEqual(target["source_id"], self.source["id"])
        self.assertEqual(target["schedule_label"], "nightly")
        self.assertIs(target["captured_here"], False)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_crawl_target_define", actions)

    def test_define_crawl_target_unknown_dataset_consumes_no_id(self):
        with self.assertRaises(NotFoundError):
            self.ext.define_crawl_target("ds-99", "X", "site-x", STEWARD)
        target = self.ext.define_crawl_target(
            self.dataset["id"], "Main site watch", "site-main", STEWARD
        )
        self.assertEqual(target["id"], "cwt-1")

    def test_define_crawl_target_unknown_source(self):
        with self.assertRaises(NotFoundError):
            self.ext.define_crawl_target(
                self.dataset["id"], "X", "site-x", STEWARD, source_id="src-99"
            )

    def test_define_crawl_target_viewer_denied_and_audited(self):
        with self.assertRaises(PermissionDenied):
            self.ext.define_crawl_target(
                self.dataset["id"], "Main site watch", "site-main", VIEWER
            )
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("ext_crawl_target_define:denied", actions)
        target = self.ext.define_crawl_target(
            self.dataset["id"], "Main site watch", "site-main", STEWARD
        )
        self.assertEqual(target["id"], "cwt-1")

    def test_get_and_list_crawl_targets(self):
        self.ext.define_crawl_target(
            self.dataset["id"], "Main site watch", "site-main", STEWARD
        )
        self.ext.define_crawl_target(
            self.dataset["id"], "Docs watch", "site-docs", STEWARD
        )
        self.assertEqual(
            len(self.ext.list_crawl_targets(self.dataset["id"], STEWARD)), 2
        )
        self.assertEqual(
            self.ext.get_crawl_target("cwt-2", STEWARD)["site_ref"],
            "site-docs",
        )
        with self.assertRaises(NotFoundError):
            self.ext.list_crawl_targets("ds-99", STEWARD)


class TestCaptures(unittest.TestCase):
    """GAPS idx 389 — a capture is a record over a core ingestion."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = archive_store()
        self.ext = DataMgmtExtensions(self.store)

    def test_record_capture_shape(self):
        _, _, capture = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        self.assertEqual(capture["id"], "cap-1")
        self.assertEqual(capture["target_id"], "cwt-1")
        self.assertEqual(capture["dataset_id"], self.dataset["id"])
        self.assertEqual(capture["ingestion_id"], "ing-1")
        self.assertEqual(capture["pages_reported"], 10)
        self.assertIs(capture["captured_here"], False)

    def test_capture_record_shape_holds_no_content(self):
        _, _, capture = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        self.assertEqual(
            set(capture),
            {"id", "target_id", "dataset_id", "ingestion_id",
             "pages_reported", "captured_here", "created_by",
             "created_utc"},
        )

    def test_record_capture_cross_dataset_ingestion_rejected(self):
        target = self.ext.define_crawl_target(
            self.dataset["id"], "Main site watch", "site-main", STEWARD
        )
        other = self.store.create_dataset(
            "Other Collection", "Another archive", STEWARD, schema=[]
        )
        foreign = self.store.record_ingestion(
            other["id"], self.source["id"], STEWARD, record_count=1,
            status="completed",
        )
        with self.assertRaises(ValidationError):
            self.ext.record_capture(target["id"], foreign["id"], STEWARD)
        _, _, capture = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        self.assertEqual(capture["id"], "cap-1")

    def test_record_capture_duplicate_ingestion_rejected(self):
        target, ingestion, _ = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        with self.assertRaises(ValidationError):
            self.ext.record_capture(target["id"], ingestion["id"], STEWARD)

    def test_record_capture_unknown_ingestion(self):
        target = self.ext.define_crawl_target(
            self.dataset["id"], "Main site watch", "site-main", STEWARD
        )
        with self.assertRaises(NotFoundError):
            self.ext.record_capture(target["id"], "ing-99", STEWARD)

    def test_list_captures_by_target(self):
        target, _, _ = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        self.assertEqual(len(self.ext.list_captures(target["id"], STEWARD)), 1)
        with self.assertRaises(NotFoundError):
            self.ext.list_captures("cwt-99", STEWARD)
        with self.assertRaises(NotFoundError):
            self.ext.get_capture("cap-99", STEWARD)


class TestArchiveSummary(unittest.TestCase):
    """GAPS idx 389/392 — the archive view is derived, never stored."""

    def test_archive_summary_derived_counts(self):
        store, audit, dataset, source = archive_store()
        ext = DataMgmtExtensions(store)
        _, _, capture = make_capture(ext, store, dataset, source)
        store.record_ingestion(
            dataset["id"], source["id"], STEWARD, mode="incremental",
            record_count=7, status="failed",
        )
        ext.seal_capture(capture["id"], ADMIN)
        summary = ext.archive_summary(dataset["id"], STEWARD)
        self.assertEqual(summary["crawl_targets"], 1)
        self.assertEqual(summary["captures"], 1)
        self.assertEqual(summary["archive_seals"], 1)
        # Core provenance totals count completed ingestions only:
        # the failed 7-record run is not part of the archive total.
        self.assertEqual(summary["total_records"], 42)
        self.assertIs(summary["captured_here"], False)
        self.assertIs(summary["sealed_here"], False)
        self.assertIs(summary["content_held"], False)


class TestRenderReference(unittest.TestCase):
    """GAPS idx 390 — rendering ships as a labeled reference."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = archive_store()
        self.ext = DataMgmtExtensions(self.store)

    def test_render_profile_shape_and_stub_labels(self):
        profile = self.ext.define_render_profile(
            "Settled JS", "dynamic_javascript_settled", STEWARD,
            wait_label="network idle",
        )
        self.assertEqual(profile["id"], "rpf-1")
        self.assertEqual(profile["mode"], "dynamic_javascript_settled")
        self.assertIs(profile["reference_stub"], True)
        self.assertIs(profile["rendered_here"], False)

    def test_render_profile_bad_mode_rejected_no_id(self):
        with self.assertRaises(ValidationError):
            self.ext.define_render_profile("X", "teleport", STEWARD)
        profile = self.ext.define_render_profile("Static", "static", STEWARD)
        self.assertEqual(profile["id"], "rpf-1")

    def test_render_report_verbatim_and_labels(self):
        _, _, capture = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        profile = self.ext.define_render_profile(
            "Settled JS", "dynamic_javascript", STEWARD
        )
        report = self.ext.record_render_report(
            capture["id"], profile["id"], "reported_partial", STEWARD,
            pages_rendered=9,
        )
        self.assertEqual(report["id"], "rrp-1")
        self.assertEqual(report["outcome"], "reported_partial")
        self.assertEqual(report["pages_rendered"], 9)
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["rendered_here"], False)

    def test_render_report_unknown_capture(self):
        profile = self.ext.define_render_profile("Static", "static", STEWARD)
        with self.assertRaises(NotFoundError):
            self.ext.record_render_report(
                "cap-99", profile["id"], "reported_rendered", STEWARD
            )


class TestChangeDetectionReference(unittest.TestCase):
    """GAPS idx 391 — change detection ships as a labeled reference."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = archive_store()
        self.ext = DataMgmtExtensions(self.store)
        self.target = self.ext.define_crawl_target(
            self.dataset["id"], "Main site watch", "site-main", STEWARD
        )

    def test_monitor_shape_and_stub_labels(self):
        monitor = self.ext.define_monitor(
            self.target["id"], STEWARD, cadence_label="hourly"
        )
        self.assertEqual(monitor["id"], "mon-1")
        self.assertIs(monitor["reference_stub"], True)
        self.assertIs(monitor["monitored_here"], False)
        self.assertIs(monitor["detected_here"], False)

    def test_change_report_verbatim_and_labels(self):
        monitor = self.ext.define_monitor(self.target["id"], STEWARD)
        report = self.ext.record_change_report(
            monitor["id"], "reported_changed_pages", STEWARD,
            pages_changed=3, note="as reported by the monitor",
        )
        self.assertEqual(report["id"], "chg-1")
        self.assertEqual(report["outcome"], "reported_changed_pages")
        self.assertEqual(report["pages_changed"], 3)
        self.assertIs(report["reference_stub"], True)
        self.assertIs(report["detected_here"], False)

    def test_change_report_bad_outcome_rejected(self):
        monitor = self.ext.define_monitor(self.target["id"], STEWARD)
        with self.assertRaises(ValidationError):
            self.ext.record_change_report(
                monitor["id"], "definitely_changed", STEWARD
            )


class TestArchiveSealing(unittest.TestCase):
    """GAPS idx 392 — seals state the core record's checksum."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = archive_store()
        self.ext = DataMgmtExtensions(self.store)

    def test_seal_carries_core_ingestion_checksum(self):
        _, ingestion, capture = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        seal = self.ext.seal_capture(capture["id"], ADMIN)
        self.assertEqual(seal["id"], "asl-1")
        self.assertEqual(seal["ingestion_id"], ingestion["id"])
        self.assertEqual(seal["checksum"], "abc123")
        self.assertIs(seal["sealed_here"], False)
        self.assertIs(seal["content_held"], False)
        self.assertEqual(
            set(seal),
            {"id", "capture_id", "ingestion_id", "checksum",
             "sealed_here", "content_held", "created_by", "created_utc"},
        )

    def test_seal_without_core_checksum_states_none(self):
        _, _, capture = make_capture(
            self.ext, self.store, self.dataset, self.source, checksum=None
        )
        seal = self.ext.seal_capture(capture["id"], ADMIN)
        self.assertIsNone(seal["checksum"])

    def test_recorder_cannot_seal_own_capture(self):
        _, _, capture = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        with self.assertRaises(PermissionDenied):
            self.ext.seal_capture(capture["id"], STEWARD)
        self.assertEqual(self.ext.list_archive_seals(capture["id"], ADMIN), [])

    def test_duplicate_seal_rejected(self):
        _, _, capture = make_capture(
            self.ext, self.store, self.dataset, self.source
        )
        self.ext.seal_capture(capture["id"], ADMIN)
        with self.assertRaises(ValidationError):
            self.ext.seal_capture(capture["id"], ADMIN)

    def test_seal_unknown_capture(self):
        with self.assertRaises(NotFoundError):
            self.ext.seal_capture("cap-99", ADMIN)


class TestReplayRequests(unittest.TestCase):
    """GAPS idx 392 — replay is a labeled transport request record."""

    def test_replay_request_shape_and_transport_label(self):
        store, audit, dataset, source = archive_store()
        ext = DataMgmtExtensions(store)
        _, _, capture = make_capture(ext, store, dataset, source)
        seal = ext.seal_capture(capture["id"], ADMIN)
        request = ext.record_replay_request(
            seal["id"], "reviewer-7", VIEWER, purpose="legal review"
        )
        self.assertEqual(request["id"], "rpl-1")
        self.assertEqual(request["requester_ref"], "reviewer-7")
        self.assertIs(request["reference_transport"], True)
        self.assertIs(request["replayed_here"], False)
        self.assertIs(request["content_held"], False)

    def test_replay_request_unknown_seal(self):
        store, audit, dataset, source = archive_store()
        ext = DataMgmtExtensions(store)
        with self.assertRaises(NotFoundError):
            ext.record_replay_request("asl-99", "reviewer-7", VIEWER)


class TestContentIndexReference(unittest.TestCase):
    """GAPS idx 393 — full-content indexing ships as a reference."""

    def setUp(self):
        self.store, self.audit, self.dataset, self.source = archive_store()
        self.ext = DataMgmtExtensions(self.store)

    def test_content_index_shape_and_stub_labels(self):
        index = self.ext.define_content_index(
            "Archive full text", STEWARD, scope_label="all captures"
        )
        self.assertEqual(index["id"], "cix-1")
        self.assertIs(index["reference_stub"], True)
        self.assertIs(index["indexed_here"], False)
        self.assertIs(index["content_held"], False)

    def test_index_snapshots_and_summary_latest_derived(self):
        index = self.ext.define_content_index("Archive full text", STEWARD)
        self.ext.record_index_snapshot(index["id"], 100, STEWARD)
        self.ext.record_index_snapshot(
            index["id"], 250, STEWARD, checksum="feed42"
        )
        summary = self.ext.content_index_summary(index["id"], STEWARD)
        self.assertEqual(summary["snapshots"], 2)
        self.assertEqual(summary["latest_documents_reported"], 250)
        self.assertIs(summary["indexed_here"], False)
        self.assertIs(summary["searched_here"], False)
        self.assertIs(summary["content_held"], False)

    def test_index_summary_no_snapshots(self):
        index = self.ext.define_content_index("Archive full text", STEWARD)
        summary = self.ext.content_index_summary(index["id"], STEWARD)
        self.assertEqual(summary["snapshots"], 0)
        self.assertIsNone(summary["latest_documents_reported"])

    def test_core_metadata_search_remains_the_only_search(self):
        # The core's registry-metadata search still runs and finds
        # the archive dataset by name; the extension surface offers
        # no full-content search over captured pages at all.
        result = self.store.search("website archive", STEWARD)
        self.assertEqual(
            [d["id"] for d in result["datasets"]], [self.dataset["id"]]
        )
        self.assertFalse(hasattr(self.ext, "search_archive_content"))
        self.assertFalse(hasattr(self.ext, "search_content"))


class MutantExtensions(DataMgmtExtensions):
    """The drill's mutant: the sealer/recorder seam is a no-op."""

    def _check_sealer_not_recorder(self, capture, actor):
        return None


class TestSealingNegativeControl(unittest.TestCase):
    """Fresh negative control: a capture's recorder never seals it.

    The traced claim is this unit's separation-of-duties rule in its
    new surface (AC-3 access enforcement at this tier; AC-5 named as
    the separation-of-duties family home, as design lineage only --
    AC-5 is not a Low-baseline selection), mirroring the core's
    signature ``_check_decider_not_requester`` guard. Each canonical
    case asserts the real implementation denies the recorder's seal
    and creates nothing, that the mutant (seam no-op) would NOT
    produce that expectation, and -- via a literal
    ``assertRaises(AssertionError)`` -- that treating the mutant's
    outcome as the expected outcome fails.
    """

    def _attempt_seal(self, ext, store, dataset, source):
        _, _, capture = make_capture(ext, store, dataset, source)
        try:
            ext.seal_capture(capture["id"], STEWARD)
        except PermissionDenied:
            return "denied", capture
        return "sealed", capture

    def test_canonical_recorder_denied_other_seals(self):
        store, audit, dataset, source = archive_store()
        ext = DataMgmtExtensions(store)
        outcome, capture = self._attempt_seal(ext, store, dataset, source)
        self.assertEqual(outcome, "denied")
        self.assertEqual(ext.list_archive_seals(capture["id"], ADMIN), [])
        seal = ext.seal_capture(capture["id"], ADMIN)
        self.assertEqual(seal["checksum"], "abc123")

    def test_mutant_would_seal_and_expectation_fails(self):
        store, audit, dataset, source = archive_store()
        mutant = MutantExtensions(store)
        outcome, capture = self._attempt_seal(mutant, store, dataset, source)
        self.assertEqual(outcome, "sealed")
        seals = mutant.list_archive_seals(capture["id"], ADMIN)
        self.assertEqual(len(seals), 1)
        self.assertEqual(seals[0]["created_by"], "bob")
        with self.assertRaises(AssertionError):
            self.assertEqual(outcome, "denied")


if __name__ == "__main__":
    unittest.main()
