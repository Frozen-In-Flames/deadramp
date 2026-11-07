"""Final GAPS batch tests — Library Systems L1 extension surface.

Pins, per GAPS.md entry of Remainder Group 5: discovery queries
hold digests + result refs only (no query-text parameter exists);
preservation records hold metadata + validated digests and no
bytes; course lists compose core catalogue items with membership
derived at read; research activities, automation execution, and
integration transport are labeled reference records that execute,
connect, and transmit nothing; accessibility rendering is a
reference record (nothing is rendered or delivered here); no score
or money shape exists anywhere on the surface.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from librarysys_helpers import ALICE, BOB, CAROL, seeded  # noqa: E402
from librarysys.errors import NotFoundError, ValidationError  # noqa: E402
from librarysys.extensions import LibraryExtensions  # noqa: E402
from librarysys.access import PermissionDenied  # noqa: E402

DIGEST = "a" * 64
DIGEST2 = "b" * 64


def make():
    store, lib, item = seeded()
    return store, lib, item, LibraryExtensions(store)


def scan_no_score_or_money(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            low = str(k).lower()
            for bad in ("score", "rank", "rating", "amount", "cents",
                        "fee", "fine", "price", "recommend"):
                assert bad not in low, "%s: forbidden key %r" % (path, k)
            assert not isinstance(v, float), "%s: float at %r" % (path, k)
            scan_no_score_or_money(v, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_no_score_or_money(v, "%s[%d]" % (path, i))


class DiscoveryTests(unittest.TestCase):
    def test_query_record_exact_keys_and_derived_count(self):
        store, lib, item, ext = make()
        q = ext.record_discovery_query(lib["id"], DIGEST,
                                       ["res-1", "res-2"], BOB)
        self.assertEqual(q["result_count"], 2)
        self.assertFalse(q["searched_here"])
        stored = ext._queries[q["id"]]
        self.assertEqual(set(stored), {
            "id", "lib_id", "query_digest", "result_refs",
            "searched_here", "created_by", "created_utc"})
        self.assertNotIn("result_count", stored)

    def test_query_text_parameter_refused_by_signature(self):
        store, lib, item, ext = make()
        with self.assertRaises(TypeError):
            ext.record_discovery_query(lib["id"], DIGEST, [],
                                       BOB, query_text="catalogue")

    def test_bad_digest_rejected_and_no_id_consumed(self):
        store, lib, item, ext = make()
        with self.assertRaises(ValidationError):
            ext.record_discovery_query(lib["id"], "not-a-digest", [], BOB)
        q = ext.record_discovery_query(lib["id"], DIGEST, [], BOB)
        self.assertEqual(q["id"], "dsc-1")

    def test_delivery_report_bound_and_core_item_untouched(self):
        store, lib, item, ext = make()
        before = store.get_item(lib["id"], item["id"], BOB)
        q = ext.record_discovery_query(lib["id"], DIGEST, ["res-1"], BOB)
        d = ext.record_delivery_report(lib["id"], q["id"], item["id"],
                                       "delivered-to-branch", BOB)
        self.assertFalse(d["delivered_here"])
        self.assertEqual(d["reported_outcome"], "delivered-to-branch")
        self.assertEqual(store.get_item(lib["id"], item["id"], BOB), before)


class PreservationTests(unittest.TestCase):
    def test_preservation_record_holds_no_bytes(self):
        store, lib, item, ext = make()
        p = ext.register_preservation_record(lib["id"], item["id"],
                                             "prv-1", DIGEST, BOB)
        self.assertFalse(p["bytes_held"])
        self.assertEqual(set(p), {
            "id", "lib_id", "item_id", "preservation_ref",
            "content_digest", "bytes_held", "created_by", "created_utc"})

    def test_fixity_report_is_reported_not_verified(self):
        store, lib, item, ext = make()
        p = ext.register_preservation_record(lib["id"], item["id"],
                                             "prv-1", DIGEST, BOB)
        f = ext.record_fixity_report(lib["id"], p["id"], "match", BOB)
        self.assertFalse(f["verified_here"])
        self.assertEqual(f["reported_result"], "match")

    def test_duplicate_preservation_ref_rejected(self):
        store, lib, item, ext = make()
        ext.register_preservation_record(lib["id"], item["id"],
                                         "prv-1", DIGEST, BOB)
        with self.assertRaises(ValidationError):
            ext.register_preservation_record(lib["id"], item["id"],
                                             "prv-1", DIGEST2, BOB)


class CourseListTests(unittest.TestCase):
    def test_entries_compose_core_items_count_derived(self):
        store, lib, item, ext = make()
        item2 = store.create_item(lib["id"], "item-2", "Second Work", BOB)
        lst = ext.create_course_list(lib["id"], "crs-1", "Course A", BOB)
        ext.add_course_list_entry(lib["id"], lst["id"], item["id"], BOB)
        view = ext.add_course_list_entry(lib["id"], lst["id"],
                                         item2["id"], BOB)
        self.assertEqual(view["entry_count"], 2)
        self.assertEqual(view["entries"], [item["id"], item2["id"]])
        self.assertNotIn("entry_count", ext._course_lists[lst["id"]])

    def test_entry_for_unknown_item_rejected(self):
        store, lib, item, ext = make()
        lst = ext.create_course_list(lib["id"], "crs-1", "Course A", BOB)
        with self.assertRaises(NotFoundError):
            ext.add_course_list_entry(lib["id"], lst["id"], "cat-999", BOB)


class NegativeControlTests(unittest.TestCase):
    """Fresh mutation-verified control: the course-list entry guard
    ``_check_course_entry_absent``. Canonical rejects a duplicate
    entry; a mutant that performs no check accepts it; expecting
    the canonical rejection from the mutant fails."""

    def _list_with_item(self, ext, store, lib, item):
        lst = ext.create_course_list(lib["id"], "crs-1", "Course A", BOB)
        ext.add_course_list_entry(lib["id"], lst["id"], item["id"], BOB)
        return lst

    def test_canonical_rejects_duplicate_entry(self):
        store, lib, item, ext = make()
        lst = self._list_with_item(ext, store, lib, item)
        with self.assertRaises(ValidationError):
            ext.add_course_list_entry(lib["id"], lst["id"], item["id"], BOB)

    def test_mutant_accepts_duplicate_entry(self):
        class NoGuardExtensions(LibraryExtensions):
            def _check_course_entry_absent(self, entries, item_id):
                return None

        store, lib, item = seeded()
        ext = NoGuardExtensions(store)
        lst = self._list_with_item(ext, store, lib, item)
        view = ext.add_course_list_entry(lib["id"], lst["id"],
                                         item["id"], BOB)
        self.assertEqual(view["entries"], [item["id"], item["id"]])

    def test_mutant_as_expectation_fails(self):
        class NoGuardExtensions(LibraryExtensions):
            def _check_course_entry_absent(self, entries, item_id):
                return None

        store, lib, item = seeded()
        ext = NoGuardExtensions(store)
        lst = self._list_with_item(ext, store, lib, item)
        with self.assertRaises(AssertionError):
            with self.assertRaises(ValidationError):
                ext.add_course_list_entry(lib["id"], lst["id"],
                                          item["id"], BOB)


class ResearchTests(unittest.TestCase):
    def test_research_activity_is_labeled_reference(self):
        store, lib, item, ext = make()
        r = ext.register_research_activity(lib["id"], "rsa-1",
                                           "Visibility study", BOB)
        self.assertTrue(r["reference_stub"])
        self.assertFalse(r["platform_operated_here"])
        o = ext.record_research_outcome(lib["id"], r["id"],
                                        "report-filed", BOB)
        self.assertTrue(o["reference_stub"])
        self.assertEqual(o["reported_outcome"], "report-filed")


class KnowledgeTests(unittest.TestCase):
    def test_knowledge_links_derive_count(self):
        store, lib, item, ext = make()
        item2 = store.create_item(lib["id"], "item-2", "Second Work", BOB)
        k = ext.create_knowledge_record(lib["id"], "knw-1", "Topic", BOB)
        ext.link_knowledge_record(lib["id"], k["id"], item["id"], BOB)
        ext.link_knowledge_record(lib["id"], k["id"], item2["id"], BOB)
        view = ext.get_knowledge_record(lib["id"], k["id"], BOB)
        self.assertEqual(view["link_count"], 2)
        with self.assertRaises(ValidationError):
            ext.link_knowledge_record(lib["id"], k["id"], item["id"], BOB)


class AccessibilityTests(unittest.TestCase):
    def test_request_is_reference_nothing_rendered_or_delivered(self):
        store, lib, item, ext = make()
        r = ext.record_accessibility_request(lib["id"], item["id"],
                                             "large-print", "patron-7", BOB)
        self.assertTrue(r["reference_stub"])
        self.assertFalse(r["rendered_here"])
        self.assertFalse(r["delivered_here"])
        o = ext.record_accessibility_outcome(lib["id"], r["id"],
                                             "supplied-by-branch", BOB)
        self.assertTrue(o["reference_stub"])


class AutomationTests(unittest.TestCase):
    def test_request_executes_nothing_and_core_workflow_untouched(self):
        store, lib, item, ext = make()
        wf = store.register_workflow(lib["id"], "wfl-1", "Nightly", BOB)
        before = store.list_workflows(lib["id"], BOB)
        req = ext.record_automation_request(lib["id"], wf["id"], BOB)
        self.assertTrue(req["reference_stub"])
        self.assertFalse(req["executed_here"])
        ext.record_automation_outcome(lib["id"], req["id"], "ran", BOB)
        self.assertEqual(store.list_workflows(lib["id"], BOB), before)


class TransportTests(unittest.TestCase):
    def test_receipt_transmits_nothing_and_core_integration_untouched(self):
        store, lib, item, ext = make()
        integ = store.register_integration(lib["id"], "int-1", "sys-x",
                                           "Catalogue sync", BOB)
        before = store.list_integrations(lib["id"], BOB)
        t = ext.record_transport_receipt(lib["id"], integ["id"],
                                         "acknowledged", BOB)
        self.assertTrue(t["reference_transport"])
        self.assertFalse(t["transmitted_here"])
        self.assertFalse(t["connected_here"])
        self.assertEqual(store.list_integrations(lib["id"], BOB), before)


class AccessAndScanTests(unittest.TestCase):
    def test_viewer_write_denied_and_audited(self):
        store, lib, item, ext = make()
        with self.assertRaises(PermissionDenied):
            ext.record_discovery_query(lib["id"], DIGEST, [], CAROL)
        denied = [e for e in store.audit.entries()
                  if e["action"].endswith(":denied")]
        self.assertTrue(any(e["action"] == "ext_catalogue_write:denied"
                            for e in denied))

    def test_no_score_or_money_shape_anywhere(self):
        store, lib, item, ext = make()
        q = ext.record_discovery_query(lib["id"], DIGEST, ["r"], BOB)
        ext.record_delivery_report(lib["id"], q["id"], item["id"], "ok", BOB)
        p = ext.register_preservation_record(lib["id"], item["id"],
                                             "prv-1", DIGEST, BOB)
        ext.record_fixity_report(lib["id"], p["id"], "match", BOB)
        lst = ext.create_course_list(lib["id"], "crs-1", "Course A", BOB)
        ext.add_course_list_entry(lib["id"], lst["id"], item["id"], BOB)
        r = ext.register_research_activity(lib["id"], "rsa-1", "Study", BOB)
        ext.record_research_outcome(lib["id"], r["id"], "filed", BOB)
        k = ext.create_knowledge_record(lib["id"], "knw-1", "Topic", BOB)
        ext.link_knowledge_record(lib["id"], k["id"], item["id"], BOB)
        a = ext.record_accessibility_request(lib["id"], item["id"],
                                             "braille", "patron-1", BOB)
        ext.record_accessibility_outcome(lib["id"], a["id"], "done", BOB)
        wf = store.register_workflow(lib["id"], "wfl-1", "Nightly", BOB)
        ar = ext.record_automation_request(lib["id"], wf["id"], BOB)
        ext.record_automation_outcome(lib["id"], ar["id"], "ran", BOB)
        integ = store.register_integration(lib["id"], "int-1", "sys-x",
                                           "Sync", BOB)
        ext.record_transport_receipt(lib["id"], integ["id"], "ack", BOB)
        surfaces = [
            ext.list_discovery_queries(lib["id"], BOB),
            ext.list_delivery_reports(lib["id"], BOB),
            ext.list_preservation_records(lib["id"], BOB),
            ext.list_fixity_reports(lib["id"], BOB),
            ext.list_course_lists(lib["id"], BOB),
            ext.list_research_activities(lib["id"], BOB),
            ext.list_knowledge_records(lib["id"], BOB),
            ext.list_accessibility_requests(lib["id"], BOB),
            ext.list_automation_requests(lib["id"], BOB),
            ext.list_transport_receipts(lib["id"], BOB),
            ext.extension_summary(lib["id"], BOB),
        ]
        for surface in surfaces:
            scan_no_score_or_money(surface)
        summary = ext.extension_summary(lib["id"], BOB)
        self.assertEqual(summary["course_entry_count"], 1)
        self.assertEqual(summary["transport_receipt_count"], 1)


if __name__ == "__main__":
    unittest.main()
