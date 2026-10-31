"""Inspection tests: immutable records.

Traces to: Core function 5 -- Inspections; contract for
``OpsStore.record_inspection/get_inspection/list_inspections``;
CA-2, AU-2, SI-12 (partial). Immutability traced here: the store
exposes no update/delete API for inspections, and returned records
are copies. No score is computed from outcomes anywhere.
"""

import unittest

from opsmgmt_helpers import OPERATOR, VIEWER, fresh_store, make_store
from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError


def _fixture():
    """Core 5: Inspections -- store + asset + work order fixture."""
    store, person, organization, project = make_store()
    asset = store.create_asset("Pump", OPERATOR, project_id=project["id"])
    wo = store.create_work_order(OPERATOR, "inspection", "Inspect pump", asset_id=asset["id"])
    return store, person, project, asset, wo


class TestRecordInspection(unittest.TestCase):
    """Core 5: Inspections -- recording and validation."""

    def test_record_shape(self):
        """Core 5: Inspections. record_inspection returns insp- id with summary/links/outcome verbatim."""
        store, person, project, asset, wo = _fixture()
        insp = store.record_inspection(
            OPERATOR, "Pump checked", asset_id=asset["id"], work_order_id=wo["id"],
            inspector_id=person["id"], outcome="pass",
        )
        self.assertEqual(insp["id"], "insp-1")
        self.assertEqual(insp["summary"], "Pump checked")
        self.assertEqual(insp["asset_id"], asset["id"])
        self.assertEqual(insp["work_order_id"], wo["id"])
        self.assertEqual(insp["inspector_id"], person["id"])
        self.assertEqual(insp["outcome"], "pass")
        self.assertEqual(insp["created_by"], "bob")

    def test_record_defaults(self):
        """Core 5: Inspections. outcome defaults to not_recorded; inspector/work/asset links default as given."""
        store, person, project, asset, wo = _fixture()
        insp = store.record_inspection(OPERATOR, "Quick check", asset_id=asset["id"])
        self.assertEqual(insp["outcome"], "not_recorded")
        self.assertIsNone(insp["work_order_id"])
        self.assertIsNone(insp["inspector_id"])

    def test_all_outcomes_verbatim(self):
        """Core 5: Inspections. All four outcomes {pass, fail, follow_up, not_recorded} are recorded verbatim."""
        store, person, project, asset, wo = _fixture()
        for outcome in ("pass", "fail", "follow_up", "not_recorded"):
            insp = store.record_inspection(
                OPERATOR, "s " + outcome, asset_id=asset["id"], outcome=outcome)
            self.assertEqual(insp["outcome"], outcome)
            self.assertEqual(store.get_inspection(insp["id"], OPERATOR)["outcome"], outcome)

    def test_at_least_one_of_asset_or_work_order_required(self):
        """Core 5: Inspections (SI-10). Neither asset_id nor work_order_id -> ValidationError; either alone is accepted."""
        store, person, project, asset, wo = _fixture()
        with self.assertRaises(ValidationError):
            store.record_inspection(OPERATOR, "orphan")
        self.assertEqual(
            store.record_inspection(OPERATOR, "by asset", asset_id=asset["id"])["id"], "insp-1")
        self.assertEqual(
            store.record_inspection(OPERATOR, "by wo", work_order_id=wo["id"])["id"], "insp-2")

    def test_validation_no_id_on_failure(self):
        """Core 5: Inspections (SI-10). Empty summary / bad outcome -> ValidationError; unknown links -> NotFoundError; no id consumed."""
        store, person, project, asset, wo = _fixture()
        with self.assertRaises(ValidationError):
            store.record_inspection(OPERATOR, "", asset_id=asset["id"])
        with self.assertRaises(ValidationError):
            store.record_inspection(OPERATOR, "s", asset_id=asset["id"], outcome="scored-90")
        with self.assertRaises(NotFoundError):
            store.record_inspection(OPERATOR, "s", asset_id="ast-999")
        with self.assertRaises(NotFoundError):
            store.record_inspection(OPERATOR, "s", work_order_id="wo-999")
        with self.assertRaises(NotFoundError):
            store.record_inspection(OPERATOR, "s", asset_id=asset["id"], inspector_id="per-999")
        self.assertEqual(
            store.record_inspection(OPERATOR, "ok", asset_id=asset["id"])["id"], "insp-1")

    def test_viewer_cannot_record(self):
        """Core 5/11: Inspections/RBAC. Viewer record_inspection -> PermissionDenied."""
        store, person, project, asset, wo = _fixture()
        with self.assertRaises(PermissionDenied):
            store.record_inspection(VIEWER, "s", asset_id=asset["id"])


class TestImmutabilityAndFilters(unittest.TestCase):
    """Core 5: Inspections -- immutability and listing."""

    def test_no_update_or_delete_api(self):
        """Core 5: Inspections (immutability). The store exposes no update/delete inspection API."""
        store = fresh_store()
        for name in ("update_inspection", "delete_inspection", "remove_inspection",
                     "edit_inspection"):
            self.assertFalse(hasattr(store, name), name)

    def test_returned_records_are_copies(self):
        """Core 5: Inspections (immutability). Mutating a returned record does not mutate the store."""
        store, person, project, asset, wo = _fixture()
        insp = store.record_inspection(OPERATOR, "original summary", asset_id=asset["id"])
        insp["summary"] = "hacked"
        insp["outcome"] = "fail"
        listed = store.list_inspections(OPERATOR)
        listed[0]["summary"] = "hacked again"
        again = store.get_inspection(insp["id"], OPERATOR)
        self.assertEqual(again["summary"], "original summary")
        self.assertEqual(again["outcome"], "not_recorded")

    def test_get_and_list_with_filters(self):
        """Core 5: Inspections. get_inspection/list_inspections with asset_id and work_order_id filters; unknown id -> NotFoundError."""
        store, person, project, asset, wo = _fixture()
        asset2 = store.create_asset("Valve", OPERATOR)
        i1 = store.record_inspection(OPERATOR, "a", asset_id=asset["id"])
        i2 = store.record_inspection(OPERATOR, "b", asset_id=asset2["id"], work_order_id=wo["id"])
        self.assertEqual(store.get_inspection(i1["id"], VIEWER)["id"], i1["id"])
        self.assertEqual(len(store.list_inspections(VIEWER)), 2)
        self.assertEqual(
            [i["id"] for i in store.list_inspections(VIEWER, asset_id=asset["id"])], [i1["id"]])
        self.assertEqual(
            [i["id"] for i in store.list_inspections(VIEWER, work_order_id=wo["id"])], [i2["id"]])
        with self.assertRaises(NotFoundError):
            store.get_inspection("insp-999", OPERATOR)


if __name__ == "__main__":
    unittest.main()
