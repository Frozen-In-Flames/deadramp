"""Costs tests.

Traces to: Core -- Cost entries (cost-, immutable) and
``ConstructStore.project_cost_summary``; COST_KINDS =
(budget, estimate, change_order, actual); money rule on both amounts.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from construct.errors import NotFoundError, ValidationError
from construct.store import COST_KINDS


class TestCostEntries(unittest.TestCase):
    """Costs: creation validation."""

    def test_create_shape_and_kinds(self):
        """Costs. create makes cost- (default kind actual); every COST_KINDS value accepted."""
        store, project, prime, sub = make_store()
        e = store.create_cost_entry(OPERATOR, project["id"], "materials", "Steel beams",
                                    budgeted_cents=10000, actual_cents=9000)
        self.assertEqual(e["id"], "cost-1")
        self.assertEqual(e["kind"], "actual")
        for kind in COST_KINDS:
            rec = store.create_cost_entry(OPERATOR, project["id"], "c", "d", kind=kind)
            self.assertEqual(rec["kind"], kind)
        self.assertEqual(store.get_cost_entry(e["id"], VIEWER)["budgeted_cents"], 10000)

    def test_money_rule_both_fields(self):
        """Costs. budgeted_cents/actual_cents float/bool/negative/string -> ValidationError."""
        store, project, prime, sub = make_store()
        for field in ("budgeted_cents", "actual_cents"):
            for bad in (1.5, True, False, -1, "5"):
                with self.subTest(field=field, value=bad):
                    with self.assertRaises(ValidationError):
                        store.create_cost_entry(OPERATOR, project["id"], "c", "d", **{field: bad})
        ok = store.create_cost_entry(OPERATOR, project["id"], "c", "d", budgeted_cents=0, actual_cents=None)
        self.assertEqual(ok["id"], "cost-1")
        self.assertEqual(ok["budgeted_cents"], 0)
        self.assertIsNone(ok["actual_cents"])

    def test_kind_and_text_validation(self):
        """Costs. Bad kind / empty category / empty description / unknown project -> errors."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.create_cost_entry(OPERATOR, project["id"], "c", "d", kind="guess")
        with self.assertRaises(ValidationError):
            store.create_cost_entry(OPERATOR, project["id"], "", "d")
        with self.assertRaises(ValidationError):
            store.create_cost_entry(OPERATOR, project["id"], "c", " ")
        with self.assertRaises(NotFoundError):
            store.create_cost_entry(OPERATOR, "prj-99", "c", "d")

    def test_immutable_and_filters(self):
        """Costs. No update API; list filters by project_id and kind."""
        store, project, prime, sub = make_store()
        self.assertFalse(hasattr(store, "update_cost_entry"))
        store.create_cost_entry(OPERATOR, project["id"], "c", "d1", kind="budget")
        store.create_cost_entry(OPERATOR, project["id"], "c", "d2", kind="actual")
        self.assertEqual(len(store.list_cost_entries(VIEWER, project_id=project["id"])), 2)
        self.assertEqual(len(store.list_cost_entries(VIEWER, kind="budget")), 1)


class TestCostSummary(unittest.TestCase):
    """Costs: project_cost_summary sums and variance."""

    def test_summary_sums_and_variance(self):
        """Costs. Summary sums budgeted/actual (None counts 0); variance = budgeted - actual."""
        store, project, prime, sub = make_store()
        store.create_cost_entry(OPERATOR, project["id"], "a", "one", budgeted_cents=1000, actual_cents=400)
        store.create_cost_entry(OPERATOR, project["id"], "b", "two", budgeted_cents=None, actual_cents=100)
        store.create_cost_entry(OPERATOR, project["id"], "c", "three", budgeted_cents=500, actual_cents=None)
        summary = store.project_cost_summary(project["id"], VIEWER)
        self.assertEqual(summary, {"project_id": project["id"], "entries": 3,
                                   "total_budgeted_cents": 1500, "total_actual_cents": 500,
                                   "variance_cents": 1000})

    def test_summary_empty_project_zeros(self):
        """Costs. A project with no entries summarises to zeros."""
        store = fresh_store()
        p = store.create_project("Empty", ADMIN)
        summary = store.project_cost_summary(p["id"], ADMIN)
        self.assertEqual(summary["entries"], 0)
        self.assertEqual(summary["total_budgeted_cents"], 0)
        self.assertEqual(summary["total_actual_cents"], 0)
        self.assertEqual(summary["variance_cents"], 0)

    def test_summary_scoped_to_project_and_unknown(self):
        """Costs. Summary counts only that project's entries; unknown project -> NotFoundError."""
        store, project, prime, sub = make_store()
        other = store.create_project("Other", ADMIN)
        store.create_cost_entry(OPERATOR, project["id"], "a", "one", budgeted_cents=100)
        store.create_cost_entry(OPERATOR, other["id"], "a", "two", budgeted_cents=900)
        self.assertEqual(store.project_cost_summary(project["id"], ADMIN)["total_budgeted_cents"], 100)
        with self.assertRaises(NotFoundError):
            store.project_cost_summary("prj-99", ADMIN)


if __name__ == "__main__":
    unittest.main()
