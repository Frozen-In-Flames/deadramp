"""Storage & ingest tests.

Traces to: UNION-SPEC Core functions 1 (Ingest) and 2 (Storage) /
ranking rows 9 (Data ingest & collection, 19 siblings), 8 (Connectors —
open-format CSV/JSON slice, 20 siblings) and 6 (Data storage /
warehouse / lake, 27 siblings); Implementation contract for
``analytics/store.py``; control family SI-10 (malformed input is
rejected, never partially applied).
"""

import unittest
from datetime import datetime

from analytics_helpers import (
    ADMIN,
    ANALYST,
    SALES_COLUMNS,
    VIEWER,
    as_dicts,
    sales_csv_text,
    sales_json_text,
    sales_rows,
)
from analytics.audit import AuditLog
from analytics.errors import NotFoundError, PermissionDenied, ValidationError
from analytics.store import DatasetStore


class TestIngestJson(unittest.TestCase):
    """Core: Ingest + Storage — JSON ingest and the dataset registry."""

    def setUp(self):
        self.store = DatasetStore()

    def test_ingest_json_returns_dataset_dict(self):
        """Core: Storage. Contract: ingest returns {id, name, columns,
        row_count, created_by, created_utc}."""
        ds = self.store.ingest_json("sales", sales_json_text(), ADMIN)
        for key in ("id", "name", "columns", "row_count", "created_by",
                    "created_utc"):
            self.assertIn(key, ds)
        self.assertEqual(ds["name"], "sales")
        self.assertEqual(ds["columns"], SALES_COLUMNS)
        self.assertEqual(ds["row_count"], 5)
        self.assertEqual(ds["created_by"], "alice")

    def test_first_dataset_id_is_ds_1(self):
        """Core: Storage. Contract: ids are sequential strings ds-1, ds-2..."""
        ds = self.store.ingest_json("sales", sales_json_text(), ADMIN)
        self.assertEqual(ds["id"], "ds-1")

    def test_ids_are_sequential_across_formats(self):
        """Core: Storage. Contract: ids increment across CSV and JSON."""
        first = self.store.ingest_json("a", sales_json_text(), ADMIN)
        second = self.store.ingest_csv("b", sales_csv_text(), ADMIN)
        third = self.store.ingest_json("c", sales_json_text(), ADMIN)
        self.assertEqual(
            [first["id"], second["id"], third["id"]], ["ds-1", "ds-2", "ds-3"]
        )

    def test_created_utc_is_parseable_timestamp(self):
        """Core: Storage (provenance: who loaded it, when)."""
        ds = self.store.ingest_json("sales", sales_json_text(), ADMIN)
        self.assertIsInstance(ds["created_utc"], str)
        datetime.fromisoformat(ds["created_utc"].replace("Z", "+00:00"))

    def test_get_returns_the_registered_dataset(self):
        """Core: Storage. .get(dataset_id) returns the registry entry."""
        ds = self.store.ingest_json("sales", sales_json_text(), ADMIN)
        got = self.store.get(ds["id"])
        self.assertEqual(got["id"], ds["id"])
        self.assertEqual(got["name"], "sales")
        self.assertEqual(got["columns"], SALES_COLUMNS)
        self.assertEqual(got["row_count"], 5)
        self.assertEqual(got["created_by"], "alice")

    def test_list_returns_datasets_in_creation_order(self):
        """Core: Storage. .list() is the dataset registry."""
        self.store.ingest_json("a", sales_json_text(), ADMIN)
        self.store.ingest_csv("b", sales_csv_text(), ANALYST)
        listing = self.store.list()
        self.assertEqual([d["name"] for d in listing], ["a", "b"])
        self.assertEqual([d["id"] for d in listing], ["ds-1", "ds-2"])
        for entry in listing:
            self.assertIn("row_count", entry)
            self.assertIn("columns", entry)

    def test_rows_returns_ingested_records_verbatim(self):
        """Core: Storage. .rows(dataset_id) returns what was ingested,
        with JSON types preserved."""
        ds = self.store.ingest_json("sales", sales_json_text(), ADMIN)
        rows = as_dicts(self.store.rows(ds["id"]), SALES_COLUMNS)
        self.assertEqual(rows, sales_rows())

    def test_analyst_may_ingest(self):
        """Core: Ingest + Access control. Analyst holds the ingest
        permission, so ingest by an analyst succeeds."""
        ds = self.store.ingest_json("sales", sales_json_text(), ANALYST)
        self.assertEqual(ds["created_by"], "bob")


class TestIngestCsv(unittest.TestCase):
    """Core: Ingest — CSV ingest (open-format file ingest slice)."""

    def setUp(self):
        self.store = DatasetStore()

    def test_ingest_csv_schema_from_header(self):
        """Core: Ingest/Storage. CSV columns are inferred from the header,
        in header order."""
        ds = self.store.ingest_csv("sales", sales_csv_text(), ADMIN)
        self.assertEqual(ds["columns"], SALES_COLUMNS)
        self.assertEqual(ds["row_count"], 5)

    def test_ingest_csv_rows_are_retrievable(self):
        """Core: Ingest/Storage. CSV rows come back via .rows()."""
        ds = self.store.ingest_csv("sales", sales_csv_text(), ADMIN)
        rows = as_dicts(self.store.rows(ds["id"]), SALES_COLUMNS)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["region"], "north")
        self.assertEqual(rows[0]["product"], "widget")
        self.assertEqual(float(rows[4]["units"]), 50.0)
        self.assertEqual(float(rows[4]["revenue"]), 500.0)


class TestStoreErrorsAndAtomicity(unittest.TestCase):
    """Core: Ingest (SI-10) — malformed input rejected, nothing applied."""

    def setUp(self):
        self.store = DatasetStore()
        self.good = self.store.ingest_json("sales", sales_json_text(), ADMIN)

    def test_malformed_json_raises_validation_error(self):
        """Core: Ingest (SI-10). Contract: malformed input raises
        ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.ingest_json("bad", "{not json", ADMIN)

    def test_non_object_json_rows_raise_validation_error(self):
        """Core: Ingest (SI-10). JSON rows must be records."""
        with self.assertRaises(ValidationError):
            self.store.ingest_json("bad", "[1, 2, 3]", ADMIN)

    def test_empty_csv_raises_validation_error(self):
        """Core: Ingest (SI-10). An empty CSV has no schema to infer."""
        with self.assertRaises(ValidationError):
            self.store.ingest_csv("bad", "", ADMIN)

    def test_failed_ingest_changes_nothing(self):
        """Core: Ingest (SI-10). Contract: malformed input 'changes
        nothing' — registry and existing rows are untouched."""
        before_list = [dict(d) for d in self.store.list()]
        before_rows = as_dicts(
            self.store.rows(self.good["id"]), SALES_COLUMNS
        )
        for bad_call in (
            lambda: self.store.ingest_json("bad", "{oops", ADMIN),
            lambda: self.store.ingest_json("bad", "[1, 2]", ADMIN),
            lambda: self.store.ingest_csv("bad", "", ADMIN),
        ):
            with self.assertRaises(ValidationError):
                bad_call()
        self.assertEqual([dict(d) for d in self.store.list()], before_list)
        self.assertEqual(
            as_dicts(self.store.rows(self.good["id"]), SALES_COLUMNS),
            before_rows,
        )

    def test_get_unknown_dataset_raises_not_found(self):
        """Core: Storage. Contract: unknown ids raise NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get("ds-999")

    def test_rows_unknown_dataset_raises_not_found(self):
        """Core: Storage. .rows() on an unknown id raises NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.rows("ds-999")

    def test_viewer_ingest_is_denied_and_stores_nothing(self):
        """Core: Ingest + Access control (AC-3). Viewer lacks ingest;
        the denied attempt must not create a dataset."""
        store = DatasetStore()
        with self.assertRaises(PermissionDenied):
            store.ingest_json("sales", sales_json_text(), VIEWER)
        self.assertEqual(store.list(), [])


class TestIngestAuditing(unittest.TestCase):
    """Core: Ingest + Audit log — ingest is recorded in the trail."""

    def test_ingest_records_an_audit_entry(self):
        """Core: Audit log. Contract: every ingest is recorded with
        actor, action, target and timestamp."""
        audit = AuditLog()
        store = DatasetStore(audit=audit)
        ds = store.ingest_json("sales", sales_json_text(), ADMIN)
        entries = audit.entries()
        self.assertGreaterEqual(len(entries), 1)
        matching = [
            e
            for e in entries
            if e["actor"] == "alice"
            and (ds["id"] in str(e["target"]) or "sales" in str(e["target"]))
        ]
        self.assertTrue(
            matching, "no audit entry names the ingesting actor and target"
        )


if __name__ == "__main__":
    unittest.main()
