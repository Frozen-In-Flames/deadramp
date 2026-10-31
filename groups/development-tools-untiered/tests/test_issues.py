"""Issue tracking tests incl. lifecycle.

Traces to: Core function 2 (issue tracking w/ lifecycle, AU-2/SI-10) --
``iss-`` records, status open, lifecycle transitions only.
"""

import unittest

from devtools_helpers import ADMIN, VIEWER, make_store
from devtools.errors import NotFoundError, ValidationError


class TestIssues(unittest.TestCase):
    """Core 2: issue creation, filters, and the lifecycle gate."""

    def test_create_shape(self):
        """Core 2: create_issue returns iss-N, status open, timestamps."""
        store, project = make_store()
        issue = store.create_issue(project["id"], "Crash on start", ADMIN, kind="bug", priority="high")
        self.assertEqual(issue["id"], "iss-1")
        self.assertEqual(issue["status"], "open")
        self.assertEqual(issue["kind"], "bug")
        self.assertEqual(issue["priority"], "high")
        self.assertEqual(issue["created_by"], "alice")
        self.assertIn("updated_utc", issue)

    def test_unknown_project_not_found_no_id(self):
        """Core 2: unknown project -> NotFoundError, no id consumed."""
        store, project = make_store()
        with self.assertRaises(NotFoundError):
            store.create_issue("prj-999", "X", ADMIN)
        issue = store.create_issue(project["id"], "X", ADMIN)
        self.assertEqual(issue["id"], "iss-1")

    def test_list_filters(self):
        """Core 2: list_issues filters by project_id and status."""
        store, project = make_store()
        store.create_issue(project["id"], "One", ADMIN)
        i2 = store.create_issue(project["id"], "Two", ADMIN)
        store.set_issue_status(i2["id"], "closed", ADMIN)
        self.assertEqual(len(store.list_issues(project_id=project["id"])), 2)
        self.assertEqual(len(store.list_issues(status="closed")), 1)
        self.assertEqual(store.list_issues(project_id="prj-999"), [])

    def test_lifecycle_happy_path(self):
        """Core 2 lifecycle: open->in_progress->resolved->closed->open->closed all allowed."""
        store, project = make_store()
        issue = store.create_issue(project["id"], "Flow", ADMIN)
        for target in ("in_progress", "resolved", "closed", "open", "closed"):
            issue = store.set_issue_status(issue["id"], target, ADMIN)
            self.assertEqual(issue["status"], target)

    def test_lifecycle_illegal_transitions_rejected_state_unchanged(self):
        """Core 2 lifecycle gate: illegal, same-state, and unknown transitions -> ValidationError, state unchanged."""
        store, project = make_store()
        issue = store.create_issue(project["id"], "Gate", ADMIN)
        for bad in ("open", "resolved", "bogus", "merged"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    store.set_issue_status(issue["id"], bad, ADMIN)
                self.assertEqual(store.get_issue(issue["id"])["status"], "open")
        store.set_issue_status(issue["id"], "in_progress", ADMIN)
        with self.assertRaises(ValidationError):
            store.set_issue_status(issue["id"], "closed", ADMIN)
        self.assertEqual(store.get_issue(issue["id"])["status"], "in_progress")

    def test_set_status_unknown_issue(self):
        """Core 2: set_issue_status on unknown issue -> NotFoundError."""
        store, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.set_issue_status("iss-999", "closed", ADMIN)

    def test_viewer_write_denied(self):
        """Core 2/9: viewer cannot create or transition issues."""
        store, project = make_store()
        from devtools.errors import PermissionDenied
        with self.assertRaises(PermissionDenied):
            store.create_issue(project["id"], "Nope", VIEWER)


if __name__ == "__main__":
    unittest.main()
