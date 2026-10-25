"""Environment & deployment records tests.

Traces to: Core function 7 (environment & deployment records, AU-2) --
``env-`` / ``dep-`` records only; nothing deploys.
"""

import unittest

from devtools_helpers import ADMIN, make_store
from devtools.errors import NotFoundError, ValidationError


class TestDeployments(unittest.TestCase):
    """Core 7: environment creation and deployment records."""

    def test_environment_shape(self):
        """Core 7: create_environment returns env-N with tier."""
        store, _ = make_store()
        env = store.create_environment("prod", ADMIN, tier="production")
        self.assertEqual(env["id"], "env-1")
        self.assertEqual(env["tier"], "production")
        self.assertEqual([e["name"] for e in store.list_environments()], ["prod"])

    def test_record_deployment_shape(self):
        """Core 7: record_deployment returns dep-N linked to env/project/release/artifact."""
        store, project = make_store()
        env = store.create_environment("prod", ADMIN)
        rel = store.create_release(project["id"], "v1", ADMIN)
        art = store.register_artifact(project["id"], "pkg", ADMIN, content="data")
        dep = store.record_deployment(env["id"], project["id"], ADMIN, release_id=rel["id"], artifact_id=art["id"])
        self.assertEqual(dep["id"], "dep-1")
        self.assertEqual(dep["status"], "deployed")
        self.assertEqual(dep["release_id"], rel["id"])

    def test_bad_status_and_unknown_refs(self):
        """Core 7 (SI-10): bad status -> ValidationError; unknown env/project/release/artifact -> NotFoundError."""
        store, project = make_store()
        env = store.create_environment("prod", ADMIN)
        with self.assertRaises(ValidationError):
            store.record_deployment(env["id"], project["id"], ADMIN, status="lost")
        with self.assertRaises(NotFoundError):
            store.record_deployment("env-999", project["id"], ADMIN)
        with self.assertRaises(NotFoundError):
            store.record_deployment(env["id"], "prj-999", ADMIN)
        with self.assertRaises(NotFoundError):
            store.record_deployment(env["id"], project["id"], ADMIN, release_id="rel-999")
        with self.assertRaises(NotFoundError):
            store.record_deployment(env["id"], project["id"], ADMIN, artifact_id="art-999")
        self.assertEqual(store.list_deployments(), [])

    def test_list_filters_and_statuses(self):
        """Core 7: list_deployments filters by environment/project; failed/rolled_back accepted."""
        store, project = make_store()
        env = store.create_environment("staging", ADMIN)
        store.record_deployment(env["id"], project["id"], ADMIN, status="failed")
        store.record_deployment(env["id"], project["id"], ADMIN, status="rolled_back")
        self.assertEqual(len(store.list_deployments(environment_id=env["id"])), 2)
        self.assertEqual(len(store.list_deployments(project_id=project["id"])), 2)
        self.assertEqual(store.list_deployments(environment_id="env-999"), [])


if __name__ == "__main__":
    unittest.main()
