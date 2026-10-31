"""Usage-record tests: immutable metering records.

Traces to: Core function 6 -- Usage records; contract for
``OpsStore.record_usage/list_usage``; AU-2/AU-3, SC-28 (not claimed).
Quantity rule traced from the implementation: quantity must be an
``int`` (bool and float rejected); the implementation imposes no
sign/range check, so zero and negative integers are accepted as
recorded -- that behaviour is pinned here as implemented.
Immutability: no update/delete API; returned records are copies.
"""

import unittest

from opsmgmt_helpers import OPERATOR, VIEWER, fresh_store, make_store
from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestRecordUsage(unittest.TestCase):
    """Core 6: Usage records -- recording and validation."""

    def test_record_shape(self):
        """Core 6: Usage records. record_usage returns use- id with project/metric/quantity/period."""
        store, person, organization, project = make_store()
        rec = store.record_usage(OPERATOR, project["id"], "api_calls", 42, "2026-10")
        self.assertEqual(rec["id"], "use-1")
        self.assertEqual(rec["project_id"], project["id"])
        self.assertEqual(rec["metric"], "api_calls")
        self.assertEqual(rec["quantity"], 42)
        self.assertEqual(rec["period"], "2026-10")
        self.assertEqual(rec["created_by"], "bob")

    def test_integer_quantity_accepted(self):
        """Core 6: Usage records. Integer quantities (including large ints) are accepted verbatim."""
        store, person, organization, project = make_store()
        for qty in (1, 7, 1000000):
            rec = store.record_usage(OPERATOR, project["id"], "hours", qty, "2026-10")
            self.assertEqual(rec["quantity"], qty)

    def test_float_quantity_rejected_no_id(self):
        """Core 6: Usage records (SI-10). Float quantity (incl. integral floats) -> ValidationError, no id consumed."""
        store, person, organization, project = make_store()
        for bad in (1.5, 2.0, 0.0):
            with self.assertRaises(ValidationError):
                store.record_usage(OPERATOR, project["id"], "hours", bad, "2026-10")
        self.assertEqual(
            store.record_usage(OPERATOR, project["id"], "hours", 2, "2026-10")["id"], "use-1")

    def test_bool_quantity_rejected_no_id(self):
        """Core 6: Usage records (SI-10). Bool quantity (True/False, an int subclass) -> ValidationError, no id consumed."""
        store, person, organization, project = make_store()
        for bad in (True, False):
            with self.assertRaises(ValidationError):
                store.record_usage(OPERATOR, project["id"], "hours", bad, "2026-10")
        self.assertEqual(
            store.record_usage(OPERATOR, project["id"], "hours", 1, "2026-10")["id"], "use-1")

    def test_non_int_quantity_rejected(self):
        """Core 6: Usage records (SI-10). String/None quantity -> ValidationError."""
        store, person, organization, project = make_store()
        for bad in ("42", None, [1]):
            with self.assertRaises(ValidationError):
                store.record_usage(OPERATOR, project["id"], "hours", bad, "2026-10")

    def test_zero_and_negative_quantities_as_implemented(self):
        """Core 6: Usage records. As implemented, zero and negative ints are accepted (no sign/range check in record_usage)."""
        store, person, organization, project = make_store()
        zero = store.record_usage(OPERATOR, project["id"], "hours", 0, "2026-10")
        self.assertEqual(zero["quantity"], 0)
        negative = store.record_usage(OPERATOR, project["id"], "hours", -5, "2026-10")
        self.assertEqual(negative["quantity"], -5)

    def test_unknown_project_not_found_no_id(self):
        """Core 6: Usage records. Unknown project -> NotFoundError, no id consumed."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.record_usage(OPERATOR, "proj-999", "hours", 1, "2026-10")
        store2, person, organization, project = make_store()
        self.assertEqual(
            store2.record_usage(OPERATOR, project["id"], "hours", 1, "2026-10")["id"], "use-1")

    def test_metric_and_period_validation(self):
        """Core 6: Usage records (SI-10). Empty metric/period -> ValidationError, no id consumed."""
        store, person, organization, project = make_store()
        with self.assertRaises(ValidationError):
            store.record_usage(OPERATOR, project["id"], "", 1, "2026-10")
        with self.assertRaises(ValidationError):
            store.record_usage(OPERATOR, project["id"], "hours", 1, "")
        self.assertEqual(
            store.record_usage(OPERATOR, project["id"], "hours", 1, "2026-10")["id"], "use-1")

    def test_viewer_cannot_record(self):
        """Core 6/11: Usage records/RBAC. Viewer record_usage -> PermissionDenied."""
        store, person, organization, project = make_store()
        with self.assertRaises(PermissionDenied):
            store.record_usage(VIEWER, project["id"], "hours", 1, "2026-10")


class TestUsageImmutabilityFiltersReport(unittest.TestCase):
    """Core 6: Usage records -- immutability, listing, and report sums."""

    def test_no_update_or_delete_api(self):
        """Core 6: Usage records (immutability). The store exposes no update/delete usage API."""
        store = fresh_store()
        for name in ("update_usage", "delete_usage", "remove_usage", "edit_usage"):
            self.assertFalse(hasattr(store, name), name)

    def test_returned_records_are_copies(self):
        """Core 6: Usage records (immutability). Mutating a returned record does not mutate the store."""
        store, person, organization, project = make_store()
        rec = store.record_usage(OPERATOR, project["id"], "hours", 3, "2026-10")
        rec["quantity"] = 999
        listed = store.list_usage(OPERATOR)
        listed[0]["quantity"] = 999
        self.assertEqual(store.list_usage(OPERATOR)[0]["quantity"], 3)

    def test_list_filters(self):
        """Core 6: Usage records. list_usage filters by project_id and metric; viewer may read."""
        store, person, organization, project = make_store()
        project2 = store.create_project("Beta", OPERATOR)
        u1 = store.record_usage(OPERATOR, project["id"], "hours", 3, "2026-10")
        store.record_usage(OPERATOR, project2["id"], "hours", 4, "2026-10")
        store.record_usage(OPERATOR, project["id"], "api_calls", 10, "2026-10")
        self.assertEqual(len(store.list_usage(VIEWER)), 3)
        self.assertEqual(
            [u["id"] for u in store.list_usage(VIEWER, project_id=project["id"])],
            [u1["id"], "use-3"])
        self.assertEqual(
            len(store.list_usage(VIEWER, metric="hours")), 2)
        self.assertEqual(
            [u["quantity"] for u in store.list_usage(VIEWER, project_id=project2["id"])], [4])

    def test_report_sums_quantities_by_metric(self):
        """Core 6/8: Usage records/Reports. report usage by_metric SUMS quantities, total counts records."""
        store, person, organization, project = make_store()
        store.record_usage(OPERATOR, project["id"], "hours", 3, "2026-10")
        store.record_usage(OPERATOR, project["id"], "hours", 4, "2026-11")
        store.record_usage(OPERATOR, project["id"], "api_calls", 10, "2026-10")
        rep = store.report(OPERATOR)
        self.assertEqual(rep["usage"]["total"], 3)
        self.assertEqual(rep["usage"]["by_metric"], {"hours": 7, "api_calls": 10})


if __name__ == "__main__":
    unittest.main()
