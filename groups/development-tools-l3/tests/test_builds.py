"""Build records tests.

Traces to: Core function 4 (build records, AU-2/SI-10) -- ``bld-``
records only; nothing executes.
"""

import unittest

from devtools_helpers import ADMIN, make_store
from devtools.errors import NotFoundError, ValidationError


class TestBuilds(unittest.TestCase):
    """Core 4: build record creation and status validation."""

    def test_record_shape_default_succeeded(self):
        """Core 4: record_build returns bld-N, default status succeeded, config held as record."""
        store, project = make_store()
        b = store.record_build(project["id"], ADMIN, ref="main", config={"os": "linux"})
        self.assertEqual(b["id"], "bld-1")
        self.assertEqual(b["status"], "succeeded")
        self.assertEqual(b["ref"], "main")
        self.assertEqual(b["config"], {"os": "linux"})
        self.assertEqual(b["recorded_by"], "alice")

    def test_all_statuses_accepted_bad_rejected(self):
        """Core 4 (SI-10): status must be in {queued,running,succeeded,failed} else ValidationError, no id consumed."""
        store, project = make_store()
        for s in ("queued", "running", "succeeded", "failed"):
            self.assertEqual(store.record_build(project["id"], ADMIN, status=s)["status"], s)
        with self.assertRaises(ValidationError):
            store.record_build(project["id"], ADMIN, status="exploded")
        self.assertEqual(store.record_build(project["id"], ADMIN)["id"], "bld-5")

    def test_unknown_project_and_list(self):
        """Core 4: unknown project -> NotFoundError; list_builds filters by project."""
        store, project = make_store()
        with self.assertRaises(NotFoundError):
            store.record_build("prj-999", ADMIN)
        store.record_build(project["id"], ADMIN)
        self.assertEqual(len(store.list_builds(project_id=project["id"])), 1)
        with self.assertRaises(NotFoundError):
            store.get_build("bld-999")


if __name__ == "__main__":
    unittest.main()
