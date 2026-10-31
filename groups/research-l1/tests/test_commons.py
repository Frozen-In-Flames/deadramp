"""Core: Data commons registry & membership. Traces to UNION-SPEC
core functions 1 (data commons development, configuration &
operation — the registry substrate) and 2 (data ecosystems / data
meshes, recorded as commons kinds), the membership boundary of
core function 10, and SI-10 input validation. The lifecycle is
event-driven (draft -> active -> retired), so status is stored."""

import unittest

import research_helpers as H
from research.errors import NotFoundError, PermissionDenied, ValidationError

EXPECTED_KEYS = {"id", "name", "title", "kind", "sponsor_ref", "status",
                 "owner", "members", "created_by", "created_utc"}


class TestCommonsCreation(unittest.TestCase):
    def setUp(self):
        self.store = H.fresh_store()

    def test_create_shape_and_defaults(self):
        commons = H.make_commons(self.store)
        self.assertEqual(set(commons.keys()), EXPECTED_KEYS)
        self.assertTrue(commons["id"].startswith("com-"))
        self.assertEqual(commons["name"], H.COMMONS_NAME)
        self.assertEqual(commons["kind"], "commons")
        self.assertEqual(commons["sponsor_ref"], "SPONSOR-1")
        self.assertEqual(commons["status"], "draft")
        self.assertEqual(commons["owner"], "bob")
        self.assertEqual(commons["members"], ["bob"])
        self.assertEqual(commons["created_by"], "bob")

    def test_all_kinds_accepted(self):
        for kind in ("commons", "ecosystem", "mesh"):
            commons = H.make_commons(self.store, name="%s-net" % kind,
                                     kind=kind)
            self.assertEqual(commons["kind"], kind)

    def test_duplicate_name_rejected(self):
        H.make_commons(self.store)
        with self.assertRaises(ValidationError):
            H.make_commons(self.store)

    def test_bad_kind_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_commons(self.store, kind="portal")

    def test_empty_fields_rejected_and_no_id_consumed(self):
        for overrides in (
            {"name": ""},
            {"name": "  "},
            {"title": "  "},
            {"sponsor_ref": ""},
        ):
            with self.assertRaises(ValidationError, msg=repr(overrides)):
                H.make_commons(self.store, **overrides)
        # Nothing was stored and no id was consumed by the failures.
        commons = H.make_commons(self.store)
        self.assertEqual(commons["id"], "com-1")

    def test_viewer_cannot_create_commons(self):
        with self.assertRaises(PermissionDenied):
            H.make_commons(self.store, actor=H.VIEWER)


class TestCommonsLifecycle(unittest.TestCase):
    def setUp(self):
        self.store = H.fresh_store()
        self.commons = H.make_commons(self.store)

    def test_draft_to_active_to_retired(self):
        cid = self.commons["id"]
        self.assertEqual(self.commons["status"], "draft")
        active = self.store.activate_commons(H.MEMBER, cid)
        self.assertEqual(active["status"], "active")
        retired = self.store.retire_commons(H.MEMBER, cid)
        self.assertEqual(retired["status"], "retired")
        self.assertEqual(
            self.store.get_commons(H.MEMBER, cid)["status"], "retired")

    def test_activate_requires_draft(self):
        cid = self.commons["id"]
        self.store.activate_commons(H.MEMBER, cid)
        with self.assertRaises(ValidationError):
            self.store.activate_commons(H.MEMBER, cid)

    def test_retire_from_draft_allowed(self):
        retired = self.store.retire_commons(H.MEMBER, self.commons["id"])
        self.assertEqual(retired["status"], "retired")

    def test_retired_is_terminal(self):
        cid = self.commons["id"]
        self.store.retire_commons(H.MEMBER, cid)
        with self.assertRaises(ValidationError):
            self.store.activate_commons(H.MEMBER, cid)
        with self.assertRaises(ValidationError):
            self.store.retire_commons(H.MEMBER, cid)


class TestMembershipBoundary(unittest.TestCase):
    def setUp(self):
        self.store, self.commons, self.org = H.make_store()

    def test_stored_record_shape_is_pinned(self):
        raw = self.store._commons[self.commons["id"]]
        self.assertEqual(set(raw.keys()), EXPECTED_KEYS)
        view = self.store.get_commons(H.MEMBER, self.commons["id"])
        self.assertEqual(set(view.keys()), EXPECTED_KEYS)
        # The view copies the member list: mutating it changes nothing.
        view["members"].append("mallory")
        self.assertNotIn("mallory",
                         self.store._commons[self.commons["id"]]["members"])

    def test_outsider_denied_read_and_write(self):
        cid = self.commons["id"]
        with self.assertRaises(PermissionDenied):
            self.store.get_commons(H.OUTSIDER, cid)
        with self.assertRaises(PermissionDenied):
            H.make_workspace(self.store, self.commons, actor=H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            H.make_dataset(self.store, self.commons, actor=H.OUTSIDER)
        self.assertEqual(self.store.list_commons(H.OUTSIDER), [])

    def test_admin_reaches_commons_without_membership(self):
        view = self.store.get_commons(H.ADMIN, self.commons["id"])
        self.assertEqual(view["name"], H.COMMONS_NAME)
        self.assertNotIn("alice", view["members"])
        self.assertEqual(len(self.store.list_commons(H.ADMIN)), 1)

    def test_unknown_commons_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.store.get_commons(H.ADMIN, "com-99")

    def test_add_member_then_member_can_read(self):
        updated = self.store.add_member(H.ADMIN, self.commons["id"],
                                        H.OUTSIDER.name)
        self.assertIn("dave", updated["members"])
        view = self.store.get_commons(H.OUTSIDER, self.commons["id"])
        self.assertEqual(view["id"], self.commons["id"])
        self.assertEqual(len(self.store.list_commons(H.OUTSIDER)), 1)

    def test_member_role_cannot_manage_members(self):
        with self.assertRaises(PermissionDenied):
            self.store.add_member(H.MEMBER, self.commons["id"], "zoe")

    def test_list_commons_scoped_to_membership(self):
        self.assertEqual(len(self.store.list_commons(H.MEMBER)), 1)
        self.assertEqual(len(self.store.list_commons(H.STAFF)), 1)
        self.assertEqual(self.store.list_commons(H.OUTSIDER), [])
        self.assertEqual(len(self.store.list_commons(H.ADMIN)), 1)


if __name__ == "__main__":
    unittest.main()
