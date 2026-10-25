"""Dataset tests.

Traces to: Core function -- Dataset registry (create/get/list/update,
schema versioning); contract for ``DataMgmtStore.create_dataset`` /
``get_dataset`` / ``list_datasets`` / ``update_dataset`` /
``update_schema``; control families AC-3, SI-10. Failed operations
must consume no ids.
"""

import unittest
from datetime import datetime

from datamgmt_helpers import ADMIN, STEWARD, VIEWER, fresh_store, make_store
from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError


def _parse_ts(ts):
    """Core: Datasets. Timestamps parse as ISO-8601."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestCreateDataset(unittest.TestCase):
    """Core: Datasets -- create_dataset shape, provenance, defaults."""

    def test_create_shape(self):
        """Core: Datasets. Created dataset carries every pinned field with the fixture values."""
        store, dataset, source = make_store()
        self.assertEqual(dataset["id"], "ds-1")
        self.assertEqual(dataset["name"], "Claims Extract")
        self.assertEqual(dataset["description"], "Nightly extract of claims records")
        self.assertEqual(dataset["classification"], "cui")
        self.assertEqual(dataset["tags"], ["claims", "nightly"])
        self.assertEqual(dataset["schema_version"], 1)
        self.assertEqual(dataset["created_by"], "bob")
        self.assertIn("owner", dataset)
        self.assertIn("created_utc", dataset)
        self.assertIn("updated_utc", dataset)
        _parse_ts(dataset["created_utc"])
        _parse_ts(dataset["updated_utc"])

    def test_create_schema_preserved(self):
        """Core: Datasets. Schema entries keep name/type/required/sensitive."""
        store, dataset, source = make_store()
        self.assertEqual(len(dataset["schema"]), 2)
        self.assertEqual(dataset["schema"][0]["name"], "patient_id")
        self.assertEqual(dataset["schema"][0]["type"], "string")
        self.assertEqual(dataset["schema"][0]["required"], True)
        self.assertEqual(dataset["schema"][0]["sensitive"], True)
        self.assertEqual(dataset["schema"][1]["name"], "amount")
        self.assertEqual(dataset["schema"][1]["type"], "number")

    def test_create_defaults(self):
        """Core: Datasets. Defaults: classification internal, tags [], schema [], schema_version 1."""
        store = fresh_store()
        ds = store.create_dataset("Minimal", "desc", STEWARD)
        self.assertEqual(ds["classification"], "internal")
        self.assertEqual(ds["tags"], [])
        self.assertEqual(ds["schema"], [])
        self.assertEqual(ds["schema_version"], 1)

    def test_create_explicit_owner(self):
        """Core: Datasets. An explicit owner is preserved on the dataset."""
        store = fresh_store()
        ds = store.create_dataset("Owned", "desc", STEWARD, owner="dana")
        self.assertEqual(ds["owner"], "dana")

    def test_ids_sequential(self):
        """Core: Datasets. Ids are ds-1, ds-2, ... in creation order."""
        store = fresh_store()
        a = store.create_dataset("A", "a", STEWARD)
        b = store.create_dataset("B", "b", ADMIN)
        self.assertEqual((a["id"], b["id"]), ("ds-1", "ds-2"))

    def test_all_classifications_accepted(self):
        """Core: Datasets. classification in {public, internal, cui, phi} is accepted."""
        store = fresh_store()
        for i, cls in enumerate(("public", "internal", "cui", "phi"), start=1):
            with self.subTest(classification=cls):
                ds = store.create_dataset("D%d" % i, "d", STEWARD, classification=cls)
                self.assertEqual(ds["classification"], cls)

    def test_bad_classification_rejected_no_id(self):
        """Core: Datasets (SI-10). Bad classification -> ValidationError and no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_dataset("Bad", "d", STEWARD, classification="secret")
        ds = store.create_dataset("Good", "d", STEWARD)
        self.assertEqual(ds["id"], "ds-1")
        self.assertEqual(store.list_datasets(STEWARD)[0]["name"], "Good")

    def test_empty_name_rejected_no_id(self):
        """Core: Datasets (SI-10). Empty/blank name -> ValidationError and no id consumed."""
        store = fresh_store()
        for bad in ("", "   ", None):
            with self.subTest(name=bad):
                with self.assertRaises(ValidationError):
                    store.create_dataset(bad, "d", STEWARD)
        self.assertEqual(store.create_dataset("Ok", "d", STEWARD)["id"], "ds-1")

    def test_schema_bad_type_rejected_no_id(self):
        """Core: Datasets (SI-10). Schema field with a bad type -> ValidationError, no id consumed."""
        store = fresh_store()
        bad = [{"name": "x", "type": "blob", "required": True, "sensitive": False}]
        with self.assertRaises(ValidationError):
            store.create_dataset("Bad", "d", STEWARD, schema=bad)
        self.assertEqual(store.create_dataset("Ok", "d", STEWARD)["id"], "ds-1")

    def test_schema_duplicate_field_rejected_no_id(self):
        """Core: Datasets (SI-10). Duplicate schema field names -> ValidationError, no id consumed."""
        store = fresh_store()
        dup = [
            {"name": "x", "type": "string", "required": True, "sensitive": False},
            {"name": "x", "type": "integer", "required": False, "sensitive": False},
        ]
        with self.assertRaises(ValidationError):
            store.create_dataset("Bad", "d", STEWARD, schema=dup)
        self.assertEqual(store.create_dataset("Ok", "d", STEWARD)["id"], "ds-1")

    def test_schema_all_types_accepted(self):
        """Core: Datasets. All pinned schema types are accepted."""
        store = fresh_store()
        schema = [
            {"name": "f_%s" % t, "type": t, "required": False, "sensitive": False}
            for t in ("string", "integer", "number", "boolean", "date", "datetime")
        ]
        ds = store.create_dataset("Types", "d", STEWARD, schema=schema)
        self.assertEqual(len(ds["schema"]), 6)

    def test_viewer_write_denied_no_id(self):
        """Core: Datasets (AC-3). Viewer create -> PermissionDenied and no id consumed."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_dataset("Nope", "d", VIEWER)
        self.assertEqual(store.list_datasets(STEWARD), [])
        self.assertEqual(store.create_dataset("Ok", "d", STEWARD)["id"], "ds-1")

    def test_none_actor_write_denied_no_id(self):
        """Core: Datasets (IA-2). None actor on a write -> PermissionDenied, no id consumed."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_dataset("Nope", "d", None)
        self.assertEqual(store.create_dataset("Ok", "d", STEWARD)["id"], "ds-1")

    def test_plain_string_actor_carries_identity(self):
        """Core: Datasets. A plain-string actor carries identity only (created_by = the string)."""
        store = fresh_store()
        ds = store.create_dataset("Str", "d", "erin")
        self.assertEqual(ds["created_by"], "erin")


class TestGetListDataset(unittest.TestCase):
    """Core: Datasets -- get/list."""

    def test_get_roundtrip(self):
        """Core: Datasets. get_dataset returns the created dataset, readable by viewer."""
        store, dataset, source = make_store()
        got = store.get_dataset(dataset["id"], VIEWER)
        self.assertEqual(got["id"], dataset["id"])
        self.assertEqual(got["name"], "Claims Extract")

    def test_get_unknown_not_found(self):
        """Core: Datasets. Unknown id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_dataset("ds-999", STEWARD)

    def test_list_sorted_by_id(self):
        """Core: Datasets. list_datasets returns datasets in id order."""
        store = fresh_store()
        ids = [store.create_dataset("D%d" % i, "d", STEWARD)["id"] for i in range(3)]
        listed = store.list_datasets(VIEWER)
        self.assertEqual([d["id"] for d in listed], sorted(ids))

    def test_list_empty(self):
        """Core: Datasets. A fresh store lists no datasets."""
        self.assertEqual(fresh_store().list_datasets(STEWARD), [])


class TestUpdateDataset(unittest.TestCase):
    """Core: Datasets -- update_dataset / update_schema."""

    def test_update_description_tags_classification(self):
        """Core: Datasets. update_dataset changes description, tags and classification."""
        store, dataset, source = make_store()
        updated = store.update_dataset(
            dataset["id"], STEWARD, description="New desc",
            tags=["updated"], classification="phi",
        )
        self.assertEqual(updated["description"], "New desc")
        self.assertEqual(updated["tags"], ["updated"])
        self.assertEqual(updated["classification"], "phi")
        self.assertEqual(updated["name"], "Claims Extract")

    def test_update_partial_leaves_other_fields(self):
        """Core: Datasets. A partial update leaves unspecified fields unchanged."""
        store, dataset, source = make_store()
        updated = store.update_dataset(dataset["id"], STEWARD, description="Only desc")
        self.assertEqual(updated["tags"], ["claims", "nightly"])
        self.assertEqual(updated["classification"], "cui")

    def test_update_bad_classification_rejected_unchanged(self):
        """Core: Datasets (SI-10). Bad classification on update -> ValidationError, dataset unchanged."""
        store, dataset, source = make_store()
        with self.assertRaises(ValidationError):
            store.update_dataset(dataset["id"], STEWARD, classification="secret")
        self.assertEqual(store.get_dataset(dataset["id"], STEWARD)["classification"], "cui")

    def test_update_unknown_not_found(self):
        """Core: Datasets. update_dataset on an unknown id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.update_dataset("ds-999", STEWARD, description="x")

    def test_update_viewer_denied_unchanged(self):
        """Core: Datasets (AC-3). Viewer update -> PermissionDenied, dataset unchanged."""
        store, dataset, source = make_store()
        with self.assertRaises(PermissionDenied):
            store.update_dataset(dataset["id"], VIEWER, description="hacked")
        self.assertEqual(
            store.get_dataset(dataset["id"], STEWARD)["description"],
            "Nightly extract of claims records",
        )

    def test_update_schema_bumps_version(self):
        """Core: Datasets. update_schema replaces the schema and increments schema_version."""
        store, dataset, source = make_store()
        new_schema = [
            {"name": "patient_id", "type": "string", "required": True, "sensitive": True},
            {"name": "diagnosis", "type": "string", "required": False, "sensitive": True},
        ]
        updated = store.update_schema(dataset["id"], new_schema, STEWARD)
        self.assertEqual(updated["schema_version"], 2)
        self.assertEqual([f["name"] for f in updated["schema"]], ["patient_id", "diagnosis"])
        again = store.update_schema(dataset["id"], new_schema, ADMIN)
        self.assertEqual(again["schema_version"], 3)

    def test_update_schema_invalid_rejected_version_unchanged(self):
        """Core: Datasets (SI-10). Invalid schema -> ValidationError, schema_version unchanged."""
        store, dataset, source = make_store()
        dup = [
            {"name": "x", "type": "string", "required": True, "sensitive": False},
            {"name": "x", "type": "string", "required": True, "sensitive": False},
        ]
        with self.assertRaises(ValidationError):
            store.update_schema(dataset["id"], dup, STEWARD)
        self.assertEqual(store.get_dataset(dataset["id"], STEWARD)["schema_version"], 1)

    def test_update_schema_viewer_denied(self):
        """Core: Datasets (AC-3). Viewer update_schema -> PermissionDenied, version unchanged."""
        store, dataset, source = make_store()
        with self.assertRaises(PermissionDenied):
            store.update_schema(dataset["id"], [], VIEWER)
        self.assertEqual(store.get_dataset(dataset["id"], STEWARD)["schema_version"], 1)

    def test_update_schema_unknown_not_found(self):
        """Core: Datasets. update_schema on an unknown id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.update_schema("ds-999", [], STEWARD)


if __name__ == "__main__":
    unittest.main()
