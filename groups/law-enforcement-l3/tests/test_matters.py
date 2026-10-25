"""Matter registry & members.

Traces to: Core 1 (Matter registry & members) in UNION-SPEC.md --
creation shape, opaque-reference keying, the membership boundary on
every matter-scoped operation, the add-member rule, and the guarded
open/closed lifecycle (writes to a closed matter are rejected).
"""

import unittest

from lawenf.errors import NotFoundError, PermissionDenied, ValidationError
from lawenf_helpers import ADMIN, MATTER_REF, MEMBER, OUTSIDER, VIEWER, fresh_store, make_store

MATTER_KEYS = {"id", "matter_ref", "status", "members", "created_by", "created_utc"}


class TestMatterCreation(unittest.TestCase):
    """Core 1: a matter's shape is pinned and its ref is opaque."""

    def test_shape_and_defaults(self):
        store = fresh_store()
        matter = store.create_matter("REF-1", MEMBER)
        self.assertEqual(set(matter.keys()), MATTER_KEYS)
        self.assertEqual(matter["id"], "mat-1")
        self.assertEqual(matter["status"], "open")
        self.assertEqual(matter["members"], ["bob"])
        self.assertEqual(matter["created_by"], "bob")

    def test_duplicate_ref_rejected_and_consumes_no_id(self):
        store = fresh_store()
        store.create_matter("REF-1", MEMBER)
        with self.assertRaises(ValidationError):
            store.create_matter("REF-1", MEMBER)
        second = store.create_matter("REF-2", MEMBER)
        self.assertEqual(second["id"], "mat-2")

    def test_empty_ref_rejected(self):
        store = fresh_store()
        for bad in ("", "   ", None, 42):
            with self.assertRaises(ValidationError):
                store.create_matter(bad, MEMBER)

    def test_viewer_cannot_create(self):
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_matter("REF-1", VIEWER)


class TestMembershipBoundary(unittest.TestCase):
    """Core 1 + Core 10: non-members see nothing; admin bypasses."""

    def test_outsider_read_denied(self):
        store, _audit, matter = make_store()
        with self.assertRaises(PermissionDenied):
            store.get_matter(matter["id"], OUTSIDER)

    def test_outsider_scoped_write_denied(self):
        store, _audit, matter = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_source(matter["id"], "SRC-1", "statute", OUTSIDER)

    def test_outsider_list_excludes_matter(self):
        store, _audit, matter = make_store()
        self.assertEqual(store.list_matters(OUTSIDER), [])
        self.assertEqual([m["id"] for m in store.list_matters(VIEWER)],
                         [matter["id"]])

    def test_admin_bypasses_membership(self):
        store, _audit, matter = make_store()
        self.assertEqual(store.get_matter(matter["id"], ADMIN)["id"], matter["id"])
        self.assertEqual(len(store.list_matters(ADMIN)), 1)

    def test_unknown_matter_is_not_found(self):
        store, _audit, _matter = make_store()
        with self.assertRaises(NotFoundError):
            store.get_matter("mat-999", ADMIN)


class TestAddMember(unittest.TestCase):
    """Core 1: only the creator or a platform admin may add members."""

    def test_creator_adds_and_new_member_can_read(self):
        store, _audit, matter = make_store()
        updated = store.add_member(matter["id"], "mallory", MEMBER)
        self.assertIn("mallory", updated["members"])
        self.assertEqual(store.get_matter(matter["id"], OUTSIDER)["id"],
                         matter["id"])

    def test_non_creator_member_cannot_add(self):
        store, _audit, matter = make_store()
        with self.assertRaises(PermissionDenied):
            store.add_member(matter["id"], "dave", VIEWER)

    def test_admin_can_add(self):
        store, _audit, matter = make_store()
        updated = store.add_member(matter["id"], "dave", ADMIN)
        self.assertIn("dave", updated["members"])

    def test_duplicate_member_rejected(self):
        store, _audit, matter = make_store()
        with self.assertRaises(ValidationError):
            store.add_member(matter["id"], "carol", MEMBER)


class TestMatterLifecycle(unittest.TestCase):
    """Core 1: close/reopen is guarded; a closed matter takes no writes."""

    def test_close_and_reopen(self):
        store, _audit, matter = make_store()
        closed = store.close_matter(matter["id"], MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            store.close_matter(matter["id"], MEMBER)
        reopened = store.reopen_matter(matter["id"], MEMBER)
        self.assertEqual(reopened["status"], "open")
        with self.assertRaises(ValidationError):
            store.reopen_matter(matter["id"], MEMBER)

    def test_closed_matter_rejects_writes_but_allows_reads(self):
        store, _audit, matter = make_store()
        mid = matter["id"]
        store.close_matter(mid, MEMBER)
        with self.assertRaises(ValidationError):
            store.create_source(mid, "SRC-1", "statute", MEMBER)
        with self.assertRaises(ValidationError):
            store.register_document(mid, "DOC-1", "a" * 64, 1, MEMBER)
        self.assertEqual(store.get_matter(mid, MEMBER)["status"], "closed")
        self.assertEqual(store.list_sources(mid, MEMBER), [])


if __name__ == "__main__":
    unittest.main()
