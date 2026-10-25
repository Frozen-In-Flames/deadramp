"""Organizations, projects and participants tests.

Traces to: Core -- Organizations (org-), Projects (prj-) and
participants; contract for ``ConstructStore.create_org`` /
``create_project`` / ``transition_project`` / ``add_participant``.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from construct.errors import NotFoundError, PermissionDenied, ValidationError


class TestOrgs(unittest.TestCase):
    """Organizations: shape, provenance, validation."""

    def test_org_shape_and_provenance(self):
        """Orgs. create_org returns org- id with name/reference/attributes/created_by."""
        store = fresh_store()
        org = store.create_org("Prime Co", OPERATOR, reference="REF-9", attributes={"x": 1})
        self.assertEqual(org["id"], "org-1")
        self.assertEqual(org["name"], "Prime Co")
        self.assertEqual(org["reference"], "REF-9")
        self.assertEqual(org["attributes"], {"x": 1})
        self.assertEqual(org["created_by"], "bob")
        self.assertIn("created_utc", org)
        self.assertEqual(store.get_org("org-1", VIEWER)["name"], "Prime Co")
        self.assertEqual([o["id"] for o in store.list_orgs(VIEWER)], ["org-1"])

    def test_org_defaults_and_copies(self):
        """Orgs. reference defaults None, attributes {}; returned dicts are copies."""
        store = fresh_store()
        org = store.create_org("Solo", ADMIN)
        self.assertIsNone(org["reference"])
        self.assertEqual(org["attributes"], {})
        org["attributes"]["evil"] = True
        org["name"] = "hacked"
        again = store.get_org(org["id"], ADMIN)
        self.assertEqual(again["attributes"], {})
        self.assertEqual(again["name"], "Solo")

    def test_org_validation_and_no_id_on_failure(self):
        """Orgs. Empty name / bad reference / bad attributes -> ValidationError, no id consumed."""
        store = fresh_store()
        for kwargs in ({"name": ""}, {"name": "  "}, {"name": None}):
            with self.assertRaises(ValidationError):
                store.create_org(kwargs["name"], ADMIN)
        with self.assertRaises(ValidationError):
            store.create_org("X", ADMIN, reference=42)
        with self.assertRaises(ValidationError):
            store.create_org("X", ADMIN, attributes=["nope"])
        org = store.create_org("Good", ADMIN)
        self.assertEqual(org["id"], "org-1")

    def test_org_unknown_and_viewer_write_denied(self):
        """Orgs. Unknown id -> NotFoundError; viewer write -> PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_org("org-99", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.create_org("X", VIEWER)


class TestProjects(unittest.TestCase):
    """Projects: shape, lifecycle, filters."""

    def test_project_shape_and_defaults(self):
        """Projects. create_project returns prj- id, status planned, provenance fields."""
        store = fresh_store()
        p = store.create_project("Tower", OPERATOR, agency_ref="AG-1", location="Dallas",
                                 start_at="2025-01-01T00:00:00Z", end_at="2026-01-01T00:00:00Z")
        self.assertEqual(p["id"], "prj-1")
        self.assertEqual(p["status"], "planned")
        self.assertEqual(p["agency_ref"], "AG-1")
        self.assertEqual(p["location"], "Dallas")
        self.assertEqual(p["created_by"], "bob")
        self.assertEqual(p["created_utc"], p["updated_utc"])

    def test_project_date_validation_and_no_id_on_failure(self):
        """Projects. Bad ISO dates / empty name -> ValidationError, no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_project("T", ADMIN, start_at="not-a-date")
        with self.assertRaises(ValidationError):
            store.create_project("", ADMIN)
        p = store.create_project("T", ADMIN)
        self.assertEqual(p["id"], "prj-1")

    def test_project_lifecycle_full(self):
        """Projects. planned->active->on_hold->active->completed->closed succeeds."""
        store = fresh_store()
        p = store.create_project("Tower", ADMIN)
        for to in ("active", "on_hold", "active", "completed", "closed"):
            p = store.transition_project(p["id"], OPERATOR, to)
            self.assertEqual(p["status"], to)

    def test_project_cancel_paths(self):
        """Projects. planned->cancelled and on_hold->cancelled succeed."""
        store = fresh_store()
        p1 = store.create_project("A", ADMIN)
        self.assertEqual(store.transition_project(p1["id"], ADMIN, "cancelled")["status"], "cancelled")
        p2 = store.create_project("B", ADMIN)
        store.transition_project(p2["id"], ADMIN, "active")
        store.transition_project(p2["id"], ADMIN, "on_hold")
        self.assertEqual(store.transition_project(p2["id"], ADMIN, "cancelled")["status"], "cancelled")

    def test_project_invalid_transitions(self):
        """Projects. planned->completed, closed->active, cancelled->active -> ValidationError."""
        store = fresh_store()
        p = store.create_project("Tower", ADMIN)
        with self.assertRaises(ValidationError):
            store.transition_project(p["id"], ADMIN, "completed")
        with self.assertRaises(ValidationError):
            store.transition_project(p["id"], ADMIN, "bogus")
        store.transition_project(p["id"], ADMIN, "cancelled")
        with self.assertRaises(ValidationError):
            store.transition_project(p["id"], ADMIN, "active")
        with self.assertRaises(NotFoundError):
            store.transition_project("prj-99", ADMIN, "active")

    def test_project_list_status_filter(self):
        """Projects. list_projects(status=) filters on stored status."""
        store, project, prime, sub = make_store()
        store.create_project("Second", ADMIN)
        self.assertEqual(len(store.list_projects(VIEWER)), 2)
        active = store.list_projects(VIEWER, status="active")
        self.assertEqual([p["id"] for p in active], [project["id"]])
        planned = store.list_projects(VIEWER, status="planned")
        self.assertEqual(len(planned), 1)


class TestParticipants(unittest.TestCase):
    """Participants: tier rules, duplicates, sorting."""

    def test_participant_shape_and_sorting(self):
        """Participants. list_participants sorts by (tier, org_id number)."""
        store = fresh_store()
        project = store.create_project("Tower", ADMIN)
        o1 = store.create_org("One", ADMIN)
        o2 = store.create_org("Two", ADMIN)
        o3 = store.create_org("Three", ADMIN)
        store.add_participant(project["id"], o3["id"], ADMIN, tier=2)
        store.add_participant(project["id"], o2["id"], ADMIN, tier=1)
        store.add_participant(project["id"], o1["id"], ADMIN, tier=2, role="sub")
        parts = store.list_participants(project["id"], VIEWER)
        self.assertEqual([(p["tier"], p["org_id"]) for p in parts],
                         [(1, o2["id"]), (2, o1["id"]), (2, o3["id"])])
        self.assertEqual(parts[0]["project_id"], project["id"])
        self.assertEqual(parts[0]["added_by"], "alice")
        self.assertIn("added_utc", parts[0])
        self.assertIsNone(parts[0]["role"])

    def test_participant_tier_validation(self):
        """Participants. tier bool/float/0/negative/string -> ValidationError."""
        store, project, prime, sub = make_store()
        extra = store.create_org("Extra", ADMIN)
        for bad in (True, False, 1.5, 0, -1, "1", None):
            with self.subTest(tier=bad):
                with self.assertRaises(ValidationError):
                    store.add_participant(project["id"], extra["id"], ADMIN, tier=bad)
        ok = store.add_participant(project["id"], extra["id"], ADMIN, tier=3)
        self.assertEqual(ok["tier"], 3)

    def test_participant_duplicate_and_unknown(self):
        """Participants. Duplicate org -> ValidationError; unknown ids -> NotFoundError."""
        store, project, prime, sub = make_store()
        with self.assertRaises(ValidationError):
            store.add_participant(project["id"], prime["id"], ADMIN, tier=5)
        with self.assertRaises(NotFoundError):
            store.add_participant("prj-99", prime["id"], ADMIN, tier=1)
        with self.assertRaises(NotFoundError):
            store.add_participant(project["id"], "org-99", ADMIN, tier=1)
        with self.assertRaises(NotFoundError):
            store.list_participants("prj-99", ADMIN)

    def test_participant_viewer_write_denied(self):
        """Participants. Viewer add -> PermissionDenied (project_write)."""
        store, project, prime, sub = make_store()
        extra = store.create_org("Extra", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.add_participant(project["id"], extra["id"], VIEWER, tier=2)


if __name__ == "__main__":
    unittest.main()
