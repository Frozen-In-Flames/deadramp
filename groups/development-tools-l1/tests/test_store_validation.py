"""Store validation tests.

Traces to: SI-10 (information input validation) and the contract rule
that malformed input raises ValidationError and changes nothing
(no id consumed), with permission checked before any state change.
"""

import unittest

from devtools_helpers import ADMIN, VIEWER, fresh_store, make_store
from devtools.errors import PermissionDenied, ValidationError


class TestStoreValidation(unittest.TestCase):
    """SI-10: validation leaves the store unchanged; permission precedes allocation."""

    def test_invalid_inputs_consume_no_ids_across_types(self):
        """SI-10: failed creates across types consume no sequential ids."""
        store, project = make_store()
        with self.assertRaises(ValidationError):
            store.create_issue(project["id"], "", ADMIN)
        with self.assertRaises(ValidationError):
            store.record_build(project["id"], ADMIN, status="nope")
        with self.assertRaises(ValidationError):
            store.create_release(project["id"], "", ADMIN)
        with self.assertRaises(ValidationError):
            store.register_artifact(project["id"], "a", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_environment("", ADMIN)
        self.assertEqual(store.create_issue(project["id"], "ok", ADMIN)["id"], "iss-1")
        self.assertEqual(store.record_build(project["id"], ADMIN)["id"], "bld-1")
        self.assertEqual(store.create_release(project["id"], "v1", ADMIN)["id"], "rel-1")
        self.assertEqual(store.register_artifact(project["id"], "a", ADMIN, content="x")["id"], "art-1")
        self.assertEqual(store.create_environment("prod", ADMIN)["id"], "env-1")

    def test_permission_checked_before_validation_and_id(self):
        """AC-3/SI-10: a denied actor gets PermissionDenied even with malformed input, and nothing is allocated."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_project("", VIEWER)
        self.assertEqual(store.list_projects(ADMIN), [])
        self.assertEqual(store.create_project("First", ADMIN)["id"], "prj-1")

    def test_none_actor_write_denied(self):
        """AC-3: a write with no actor is PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_project("X", None)

    def test_bad_types_rejected(self):
        """SI-10: non-string names / wrong-typed optional fields -> ValidationError."""
        store, project = make_store()
        with self.assertRaises(ValidationError):
            store.create_project(123, ADMIN)
        with self.assertRaises(ValidationError):
            store.create_project("Ok", ADMIN, description=42)
        with self.assertRaises(ValidationError):
            store.record_build(project["id"], ADMIN, config="not-a-dict")


if __name__ == "__main__":
    unittest.main()
