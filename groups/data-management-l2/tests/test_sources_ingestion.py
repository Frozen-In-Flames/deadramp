"""Source registration, ingestion recording and provenance tests.

Traces to: Core functions -- Source registry, Ingestion recording,
Dataset provenance; contract for ``register_source`` / ``get_source``
/ ``list_sources`` / ``record_ingestion`` / ``get_ingestion`` /
``list_ingestions`` / ``dataset_provenance``; SI-10, AC-3. Failed
operations must consume no ids. Provenance total_records sums only
completed ingestions.
"""

import unittest

from datamgmt_helpers import STEWARD, VIEWER, fresh_store, make_store
from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestSources(unittest.TestCase):
    """Core: Sources -- register/get/list."""

    def test_register_shape(self):
        """Core: Sources. Registered source carries id src-1, name, kind, location, provenance."""
        store, dataset, source = make_store()
        self.assertEqual(source["id"], "src-1")
        self.assertEqual(source["name"], "ehr-feed")
        self.assertEqual(source["kind"], "api")
        self.assertEqual(source["location"], "ehr.internal")
        self.assertIn("created_utc", source)

    def test_register_ids_sequential(self):
        """Core: Sources. Ids are src-1, src-2, ... in registration order."""
        store = fresh_store()
        a = store.register_source("a", "file", STEWARD)
        b = store.register_source("b", "manual", STEWARD)
        self.assertEqual((a["id"], b["id"]), ("src-1", "src-2"))

    def test_all_kinds_accepted(self):
        """Core: Sources. kind in {file, database, api, stream, manual} is accepted."""
        store = fresh_store()
        for kind in ("file", "database", "api", "stream", "manual"):
            with self.subTest(kind=kind):
                src = store.register_source("s-%s" % kind, kind, STEWARD)
                self.assertEqual(src["kind"], kind)

    def test_bad_kind_rejected_no_id(self):
        """Core: Sources (SI-10). Bad kind -> ValidationError and no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.register_source("bad", "carrier-pigeon", STEWARD)
        self.assertEqual(store.register_source("ok", "file", STEWARD)["id"], "src-1")

    def test_get_and_list(self):
        """Core: Sources. get_source round-trips; list_sources is in id order and viewer-readable."""
        store, dataset, source = make_store()
        extra = store.register_source("flat-files", "file", STEWARD, location="/data/in")
        self.assertEqual(store.get_source(source["id"], VIEWER)["name"], "ehr-feed")
        self.assertEqual(
            [s["id"] for s in store.list_sources(VIEWER)],
            [source["id"], extra["id"]],
        )

    def test_get_unknown_not_found(self):
        """Core: Sources. Unknown source id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_source("src-999", STEWARD)

    def test_viewer_register_denied_no_id(self):
        """Core: Sources (AC-3). Viewer register -> PermissionDenied and no id consumed."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.register_source("nope", "file", VIEWER)
        self.assertEqual(store.register_source("ok", "file", STEWARD)["id"], "src-1")

    def test_none_actor_register_denied(self):
        """Core: Sources (IA-2). None actor on register -> PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.register_source("nope", "file", None)


class TestIngestion(unittest.TestCase):
    """Core: Ingestion -- record_ingestion/get/list."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def test_record_happy_path(self):
        """Core: Ingestion. A completed ingestion carries ing-1 and all recorded fields."""
        ing = self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD,
            mode="incremental", record_count=42, checksum="abc123",
            status="completed", notes="nightly",
        )
        self.assertEqual(ing["id"], "ing-1")
        self.assertEqual(ing["dataset_id"], self.dataset["id"])
        self.assertEqual(ing["source_id"], self.source["id"])
        self.assertEqual(ing["mode"], "incremental")
        self.assertEqual(ing["record_count"], 42)
        self.assertEqual(ing["checksum"], "abc123")
        self.assertEqual(ing["status"], "completed")
        self.assertIn("created_utc", ing)

    def test_record_defaults(self):
        """Core: Ingestion. Defaults: mode full, record_count 0, status completed."""
        ing = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD)
        self.assertEqual(ing["mode"], "full")
        self.assertEqual(ing["record_count"], 0)
        self.assertEqual(ing["status"], "completed")

    def test_all_modes_and_statuses_accepted(self):
        """Core: Ingestion. mode in {full, incremental, stream} and status in {completed, failed} accepted."""
        for mode in ("full", "incremental", "stream"):
            with self.subTest(mode=mode):
                ing = self.store.record_ingestion(
                    self.dataset["id"], self.source["id"], STEWARD, mode=mode
                )
                self.assertEqual(ing["mode"], mode)
        failed = self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD, status="failed"
        )
        self.assertEqual(failed["status"], "failed")

    def test_unknown_dataset_not_found_no_id(self):
        """Core: Ingestion. Unknown dataset -> NotFoundError and no id consumed."""
        with self.assertRaises(NotFoundError):
            self.store.record_ingestion("ds-999", self.source["id"], STEWARD)
        ing = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD)
        self.assertEqual(ing["id"], "ing-1")

    def test_unknown_source_not_found_no_id(self):
        """Core: Ingestion. Unknown source -> NotFoundError and no id consumed."""
        with self.assertRaises(NotFoundError):
            self.store.record_ingestion(self.dataset["id"], "src-999", STEWARD)
        ing = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD)
        self.assertEqual(ing["id"], "ing-1")

    def test_bad_mode_rejected_no_id(self):
        """Core: Ingestion (SI-10). Bad mode -> ValidationError and no id consumed."""
        with self.assertRaises(ValidationError):
            self.store.record_ingestion(
                self.dataset["id"], self.source["id"], STEWARD, mode="delta"
            )
        ing = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD)
        self.assertEqual(ing["id"], "ing-1")

    def test_bad_status_rejected_no_id(self):
        """Core: Ingestion (SI-10). Bad status -> ValidationError and no id consumed."""
        with self.assertRaises(ValidationError):
            self.store.record_ingestion(
                self.dataset["id"], self.source["id"], STEWARD, status="pending"
            )
        ing = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD)
        self.assertEqual(ing["id"], "ing-1")

    def test_negative_record_count_rejected_no_id(self):
        """Core: Ingestion (SI-10). Negative record_count -> ValidationError, no id consumed."""
        with self.assertRaises(ValidationError):
            self.store.record_ingestion(
                self.dataset["id"], self.source["id"], STEWARD, record_count=-1
            )
        ing = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD)
        self.assertEqual(ing["id"], "ing-1")

    def test_bool_record_count_rejected_no_id(self):
        """Core: Ingestion (SI-10). bool record_count is rejected (bool is not an int count), no id consumed."""
        with self.assertRaises(ValidationError):
            self.store.record_ingestion(
                self.dataset["id"], self.source["id"], STEWARD, record_count=True
            )
        ing = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD)
        self.assertEqual(ing["id"], "ing-1")

    def test_non_int_record_count_rejected(self):
        """Core: Ingestion (SI-10). Non-int record_count (str/float) -> ValidationError."""
        for bad in ("42", 4.2, None):
            with self.subTest(record_count=bad):
                with self.assertRaises(ValidationError):
                    self.store.record_ingestion(
                        self.dataset["id"], self.source["id"], STEWARD, record_count=bad
                    )

    def test_zero_record_count_accepted(self):
        """Core: Ingestion. record_count 0 is a valid count."""
        ing = self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD, record_count=0
        )
        self.assertEqual(ing["record_count"], 0)

    def test_get_and_list_ingestions(self):
        """Core: Ingestion. get_ingestion round-trips; list_ingestions filters by dataset."""
        a = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD, record_count=1)
        other = self.store.create_dataset("Other", "d", STEWARD)
        b = self.store.record_ingestion(other["id"], self.source["id"], STEWARD, record_count=2)
        self.assertEqual(self.store.get_ingestion(a["id"], VIEWER)["record_count"], 1)
        self.assertEqual(
            [i["id"] for i in self.store.list_ingestions(dataset_id=self.dataset["id"], actor=VIEWER)],
            [a["id"]],
        )
        self.assertEqual(len(self.store.list_ingestions(actor=VIEWER)), 2)
        with self.assertRaises(NotFoundError):
            self.store.get_ingestion("ing-999", STEWARD)

    def test_viewer_record_denied_no_id(self):
        """Core: Ingestion (AC-3). Viewer record_ingestion -> PermissionDenied, no id consumed."""
        with self.assertRaises(PermissionDenied):
            self.store.record_ingestion(self.dataset["id"], self.source["id"], VIEWER)
        ing = self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD)
        self.assertEqual(ing["id"], "ing-1")


class TestProvenance(unittest.TestCase):
    """Core: Provenance -- dataset_provenance totals."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def test_provenance_empty(self):
        """Core: Provenance. No ingestions -> empty sources/ingestions and total_records 0."""
        prov = self.store.dataset_provenance(self.dataset["id"], VIEWER)
        self.assertEqual(prov["dataset_id"], self.dataset["id"])
        self.assertEqual(prov["sources"], [])
        self.assertEqual(prov["ingestions"], [])
        self.assertEqual(prov["total_records"], 0)

    def test_provenance_totals_completed_only(self):
        """Core: Provenance. total_records sums completed ingestions only, not failed ones."""
        self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD, record_count=100)
        self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD, record_count=50, status="failed"
        )
        self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD, record_count=25)
        prov = self.store.dataset_provenance(self.dataset["id"], STEWARD)
        self.assertEqual(prov["total_records"], 125)
        self.assertEqual(len(prov["ingestions"]), 3)

    def test_provenance_lists_sources(self):
        """Core: Provenance. Sources that fed the dataset are listed."""
        self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD, record_count=3)
        prov = self.store.dataset_provenance(self.dataset["id"], STEWARD)
        source_ids = [s["id"] for s in prov["sources"]]
        self.assertIn(self.source["id"], source_ids)

    def test_provenance_unknown_dataset(self):
        """Core: Provenance. Unknown dataset -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.dataset_provenance("ds-999", STEWARD)


if __name__ == "__main__":
    unittest.main()
