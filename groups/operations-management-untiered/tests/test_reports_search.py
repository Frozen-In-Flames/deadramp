"""Report and search tests.

Traces to: Core function 8 -- Reports (``OpsStore.report``, all
counts derived deterministically at the given ``now``) and Core
function 9 -- Search (``OpsStore.search``, literal case-insensitive
substring, NOT regex). Search permission note (builder's documented
convention, traced here): store search uses the ``project_read``
action, held by all three roles.
"""

import unittest

from opsmgmt_helpers import OPERATOR, VIEWER, fresh_store, make_store
from opsmgmt.errors import PermissionDenied, ValidationError

NOW = "2025-06-01T00:00:00Z"


def _populated():
    """Core 8/9: Reports/Search -- shared populated fixture."""
    store, person, organization, project = make_store()
    asset = store.create_asset("Pump Alpha", OPERATOR, project_id=project["id"])
    asset2 = store.create_asset("Valve Beta", OPERATOR)
    store.transition_asset(asset2["id"], OPERATOR, "in_maintenance")
    w1 = store.create_work_order(
        OPERATOR, "maintenance", "Pump broken", project_id=project["id"],
        asset_id=asset["id"], due_at="2020-01-01T00:00:00Z")
    w2 = store.create_work_order(OPERATOR, "task", "Hours question")
    store.transition_work_order(w2["id"], OPERATOR, "in_progress")
    store.record_inspection(OPERATOR, "Pump inspection summary", asset_id=asset["id"], outcome="pass")
    store.record_inspection(OPERATOR, "Valve follow-up", asset_id=asset2["id"], outcome="follow_up")
    store.record_usage(OPERATOR, project["id"], "hours", 3, "2026-10")
    store.record_usage(OPERATOR, project["id"], "hours", 4, "2026-11")
    store.record_usage(OPERATOR, project["id"], "api_calls", 10, "2026-10")
    return store, person, organization, project


class TestReport(unittest.TestCase):
    """Core 8: Reports."""

    def test_report_shape_and_counts(self):
        """Core 8: Reports. report() returns work_orders/assets/inspections/usage exactly per UNION-SPEC, with by_project incl. 'unassigned' and usage by_metric summed."""
        store, person, organization, project = _populated()
        rep = store.report(OPERATOR, now=NOW)
        self.assertEqual(set(rep.keys()), {"work_orders", "assets", "inspections", "usage"})
        self.assertEqual(
            set(rep["work_orders"].keys()),
            {"total", "by_status", "by_type", "by_project", "overdue"})
        self.assertEqual(rep["work_orders"]["total"], 2)
        self.assertEqual(rep["work_orders"]["by_status"], {"open": 1, "in_progress": 1})
        self.assertEqual(rep["work_orders"]["by_type"], {"maintenance": 1, "task": 1})
        self.assertEqual(rep["work_orders"]["by_project"][project["id"]], 1)
        self.assertEqual(rep["work_orders"]["by_project"]["unassigned"], 1)
        self.assertEqual(rep["work_orders"]["overdue"], 1)
        self.assertEqual(set(rep["assets"].keys()), {"total", "by_status"})
        self.assertEqual(rep["assets"]["total"], 2)
        self.assertEqual(rep["assets"]["by_status"], {"in_service": 1, "in_maintenance": 1})
        self.assertEqual(set(rep["inspections"].keys()), {"total", "by_outcome"})
        self.assertEqual(rep["inspections"]["total"], 2)
        self.assertEqual(rep["inspections"]["by_outcome"], {"pass": 1, "follow_up": 1})
        self.assertEqual(set(rep["usage"].keys()), {"total", "by_metric"})
        self.assertEqual(rep["usage"]["total"], 3)
        # by_metric SUMS quantities (3+4 hours), it does not count records.
        self.assertEqual(rep["usage"]["by_metric"], {"hours": 7, "api_calls": 10})

    def test_report_overdue_is_now_dependent(self):
        """Core 8: Reports (derived status). The same store reports overdue=0 before the due date and 1 after."""
        store, person, organization, project = _populated()
        self.assertEqual(store.report(OPERATOR, now="2019-01-01T00:00:00Z")["work_orders"]["overdue"], 0)
        self.assertEqual(store.report(OPERATOR, now=NOW)["work_orders"]["overdue"], 1)

    def test_report_empty_store(self):
        """Core 8: Reports. An empty store reports zero totals and empty breakdowns."""
        rep = fresh_store().report(VIEWER, now=NOW)
        self.assertEqual(rep["work_orders"]["total"], 0)
        self.assertEqual(rep["work_orders"]["by_status"], {})
        self.assertEqual(rep["work_orders"]["by_type"], {})
        self.assertEqual(rep["work_orders"]["by_project"], {})
        self.assertEqual(rep["work_orders"]["overdue"], 0)
        self.assertEqual(rep["assets"]["total"], 0)
        self.assertEqual(rep["assets"]["by_status"], {})
        self.assertEqual(rep["inspections"]["total"], 0)
        self.assertEqual(rep["inspections"]["by_outcome"], {})
        self.assertEqual(rep["usage"]["total"], 0)
        self.assertEqual(rep["usage"]["by_metric"], {})

    def test_report_readable_by_viewer(self):
        """Core 8/11: Reports/RBAC. report_read is held by all roles including viewer."""
        store, person, organization, project = _populated()
        self.assertEqual(store.report(VIEWER, now=NOW)["work_orders"]["total"], 2)


class TestSearch(unittest.TestCase):
    """Core 9: Search."""

    def test_search_shape_and_people_organizations(self):
        """Core 9: Search. search() returns {people, organizations, projects, work_orders, assets, inspections}; people/organizations match name and reference."""
        store, person, organization, project = _populated()
        result = store.search("pat", OPERATOR)
        self.assertEqual(
            set(result.keys()),
            {"people", "organizations", "projects", "work_orders", "assets", "inspections"})
        self.assertEqual([p["id"] for p in result["people"]], [person["id"]])
        by_ref = store.search("ext-1001", OPERATOR)
        self.assertEqual([p["id"] for p in by_ref["people"]], [person["id"]])
        by_name = store.search("ACME", OPERATOR)
        self.assertEqual([o["id"] for o in by_name["organizations"]], [organization["id"]])
        by_org_ref = store.search("org-1001", OPERATOR)
        self.assertEqual([o["id"] for o in by_org_ref["organizations"]], [organization["id"]])

    def test_search_projects_work_orders_assets_inspections(self):
        """Core 9: Search. Projects match on name, work orders on subject, assets on name, inspections on summary (case-insensitive)."""
        store, person, organization, project = _populated()
        result = store.search("PUMP", OPERATOR)
        self.assertEqual([w["id"] for w in result["work_orders"]], [
            w for w in [store.list_work_orders(OPERATOR)[0]["id"]]])
        self.assertEqual(len(result["assets"]), 1)
        self.assertEqual(result["assets"][0]["name"], "Pump Alpha")
        self.assertEqual(len(result["inspections"]), 1)
        self.assertEqual(result["inspections"][0]["summary"], "Pump inspection summary")
        by_project = store.search("alpha project", OPERATOR)
        self.assertEqual([p["id"] for p in by_project["projects"]], [project["id"]])
        # Work-order search views carry the derived overdue field.
        self.assertIn("overdue", result["work_orders"][0])

    def test_search_is_literal_not_regex(self):
        """Core 9: Search. The query is a literal substring: regex metacharacters match literally, not as patterns."""
        store, person, organization, project = _populated()
        self.assertEqual(store.search("p.mp", OPERATOR)["work_orders"], [])
        self.assertEqual(store.search(".*", OPERATOR)["work_orders"], [])
        self.assertEqual(len(store.search("pump", OPERATOR)["work_orders"]), 1)

    def test_search_empty_query_validation(self):
        """Core 9: Search (SI-10). Empty/blank/non-string query -> ValidationError."""
        store, person, organization, project = _populated()
        for bad in ("", "   ", None, 42):
            with self.assertRaises(ValidationError):
                store.search(bad, OPERATOR)

    def test_search_no_match_returns_empty_lists(self):
        """Core 9: Search. A query matching nothing returns empty lists in every bucket."""
        store, person, organization, project = _populated()
        result = store.search("zzzz-no-match", VIEWER)
        self.assertEqual(result, {
            "people": [], "organizations": [], "projects": [],
            "work_orders": [], "assets": [], "inspections": [],
        })

    def test_search_uses_project_read_permission(self):
        """Core 9/11: Search/RBAC (builder's documented convention). Search requires project_read: all roles hold it, a role-less/None actor is denied."""
        store, person, organization, project = _populated()
        for actor in (OPERATOR, VIEWER):
            self.assertIn("people", store.search("pat", actor))
        with self.assertRaises(PermissionDenied):
            store.search("pat", None)


if __name__ == "__main__":
    unittest.main()
