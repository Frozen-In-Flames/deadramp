"""Export tests.

Traces to: Core function -- Dataset export; contract for
``export_dataset`` / ``get_export`` / ``list_exports``. When records
are given, checksum is the sha256 hex of the canonical JSON
``json.dumps(records, sort_keys=True, separators=(",", ":"))`` and
record_count is len(records); otherwise record_count is the sum of
completed ingestion record_counts and checksum is None. SI-10, AC-3.
Failed operations must consume no ids.
"""

import hashlib
import json
import unittest

from datamgmt_helpers import STEWARD, VIEWER, make_store
from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError

RECORDS = [
    {"patient_id": "P2", "amount": 20},
    {"patient_id": "P1", "amount": 10.5},
]


def _expected_checksum(records):
    """Core: Export. Locally compute the pinned canonical-JSON sha256."""
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TestExportWithRecords(unittest.TestCase):
    """Core: Export -- manifests built from explicit records."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def test_manifest_shape(self):
        """Core: Export. A manifest carries ex-1, dataset, format, count, checksum, schema_version, exported_by."""
        manifest = self.store.export_dataset(
            self.dataset["id"], STEWARD, format="json", records=RECORDS
        )
        self.assertEqual(manifest["id"], "ex-1")
        self.assertEqual(manifest["dataset_id"], self.dataset["id"])
        self.assertEqual(manifest["format"], "json")
        self.assertEqual(manifest["record_count"], 2)
        self.assertEqual(manifest["schema_version"], self.dataset["schema_version"])
        self.assertEqual(manifest["exported_by"], "bob")
        self.assertIn("created_utc", manifest)

    def test_checksum_matches_local_canonical_sha256(self):
        """Core: Export. checksum equals the locally computed sha256 of the canonical JSON of the records."""
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD, records=RECORDS)
        self.assertEqual(manifest["checksum"], _expected_checksum(RECORDS))

    def test_checksum_key_order_independent(self):
        """Core: Export. Canonical JSON (sort_keys) makes the checksum independent of dict key order."""
        shuffled = [
            {"amount": 20, "patient_id": "P2"},
            {"amount": 10.5, "patient_id": "P1"},
        ]
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD, records=shuffled)
        self.assertEqual(manifest["checksum"], _expected_checksum(RECORDS))

    def test_csv_format_accepted(self):
        """Core: Export. format csv is accepted with the same checksum rule."""
        manifest = self.store.export_dataset(
            self.dataset["id"], STEWARD, format="csv", records=RECORDS
        )
        self.assertEqual(manifest["format"], "csv")
        self.assertEqual(manifest["record_count"], 2)
        self.assertEqual(manifest["checksum"], _expected_checksum(RECORDS))

    def test_empty_records_list(self):
        """Core: Export. An explicit empty records list -> count 0 and the checksum of '[]'."""
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD, records=[])
        self.assertEqual(manifest["record_count"], 0)
        self.assertEqual(manifest["checksum"], _expected_checksum([]))

    def test_ids_sequential(self):
        """Core: Export. Ids are ex-1, ex-2, ... in export order."""
        a = self.store.export_dataset(self.dataset["id"], STEWARD, records=RECORDS)
        b = self.store.export_dataset(self.dataset["id"], STEWARD, records=RECORDS)
        self.assertEqual((a["id"], b["id"]), ("ex-1", "ex-2"))


class TestExportWithoutRecords(unittest.TestCase):
    """Core: Export -- manifests derived from ingestion totals."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def test_count_from_completed_ingestions_checksum_none(self):
        """Core: Export. Without records: count sums completed ingestions only (100+25), checksum is None."""
        self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD, record_count=100)
        self.store.record_ingestion(
            self.dataset["id"], self.source["id"], STEWARD, record_count=50, status="failed"
        )
        self.store.record_ingestion(self.dataset["id"], self.source["id"], STEWARD, record_count=25)
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD)
        self.assertEqual(manifest["record_count"], 125)
        self.assertIsNone(manifest["checksum"])

    def test_count_zero_when_no_ingestions(self):
        """Core: Export. Without records and without ingestions -> count 0, checksum None."""
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD)
        self.assertEqual(manifest["record_count"], 0)
        self.assertIsNone(manifest["checksum"])

    def test_schema_version_reflects_current_schema(self):
        """Core: Export. The manifest's schema_version is the dataset's current schema_version."""
        self.store.update_schema(
            self.dataset["id"],
            [{"name": "patient_id", "type": "string", "required": True, "sensitive": True}],
            STEWARD,
        )
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD)
        self.assertEqual(manifest["schema_version"], 2)


class TestExportErrors(unittest.TestCase):
    """Core: Export -- validation, permission, get/list."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def test_bad_format_rejected_no_id(self):
        """Core: Export (SI-10). Bad format -> ValidationError and no id consumed."""
        with self.assertRaises(ValidationError):
            self.store.export_dataset(self.dataset["id"], STEWARD, format="xml", records=RECORDS)
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD, records=RECORDS)
        self.assertEqual(manifest["id"], "ex-1")

    def test_unknown_dataset_not_found(self):
        """Core: Export. Unknown dataset -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.export_dataset("ds-999", STEWARD, records=RECORDS)

    def test_viewer_export_denied_no_id(self):
        """Core: Export (AC-3). Viewer export -> PermissionDenied and no id consumed."""
        with self.assertRaises(PermissionDenied):
            self.store.export_dataset(self.dataset["id"], VIEWER, records=RECORDS)
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD, records=RECORDS)
        self.assertEqual(manifest["id"], "ex-1")

    def test_none_actor_export_denied(self):
        """Core: Export (IA-2). None actor on export -> PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.export_dataset(self.dataset["id"], None, records=RECORDS)

    def test_get_and_list_exports(self):
        """Core: Export. get_export round-trips; list_exports filters by dataset, viewer-readable."""
        manifest = self.store.export_dataset(self.dataset["id"], STEWARD, records=RECORDS)
        self.assertEqual(self.store.get_export(manifest["id"], VIEWER)["id"], "ex-1")
        self.assertEqual(
            [e["id"] for e in self.store.list_exports(dataset_id=self.dataset["id"], actor=VIEWER)],
            ["ex-1"],
        )
        self.assertEqual(len(self.store.list_exports(actor=VIEWER)), 1)
        with self.assertRaises(NotFoundError):
            self.store.get_export("ex-999", STEWARD)


if __name__ == "__main__":
    unittest.main()
