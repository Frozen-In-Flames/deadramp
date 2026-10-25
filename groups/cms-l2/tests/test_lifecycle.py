"""Editorial lifecycle tests.

Traces to: Core function 4 -- Editorial lifecycle / sibling claim
family authoring_editing; separation of duties AC-5.
"""

import unittest

from cms_helpers import ADMIN, AUTHOR, EDITOR, PUBLISHER, VIEWER, make_item, make_store
from cms.access import User
from cms.errors import PermissionDenied, ValidationError


class TestLifecycle(unittest.TestCase):
    """Core: Lifecycle transitions (authoring_editing)."""

    def test_happy_path_draft_in_review_approved(self):
        """Core: Lifecycle. draft -> in_review (submit) -> approved (approve by non-author)."""
        store, site, _ = make_store()
        item = make_item(store, site)
        submitted = store.submit_item(AUTHOR, item["id"])
        self.assertEqual(submitted["status"], "in_review")
        approved = store.approve_item(EDITOR, item["id"])
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["approved_by"], "carol")

    def test_return_sends_to_draft_with_note(self):
        """Core: Lifecycle. return_item: in_review -> draft, note stored."""
        store, site, _ = make_store()
        item = make_item(store, site)
        store.submit_item(AUTHOR, item["id"])
        returned = store.return_item(PUBLISHER, item["id"], note="Needs work")
        self.assertEqual(returned["status"], "draft")
        self.assertEqual(returned["return_note"], "Needs work")
        # And it can be resubmitted after return.
        self.assertEqual(store.submit_item(AUTHOR, item["id"])["status"], "in_review")

    def test_invalid_transitions(self):
        """Core: Lifecycle (SI-10). submit/approve/return from wrong status -> ValidationError, status unchanged."""
        store, site, _ = make_store()
        item = make_item(store, site)
        with self.assertRaises(ValidationError):
            store.approve_item(EDITOR, item["id"])  # draft
        with self.assertRaises(ValidationError):
            store.return_item(EDITOR, item["id"])  # draft
        store.submit_item(AUTHOR, item["id"])
        with self.assertRaises(ValidationError):
            store.submit_item(AUTHOR, item["id"])  # already in_review
        store.approve_item(EDITOR, item["id"])
        with self.assertRaises(ValidationError):
            store.submit_item(AUTHOR, item["id"])  # approved
        with self.assertRaises(ValidationError):
            store.approve_item(PUBLISHER, item["id"])  # approved
        self.assertEqual(store.get_item(item["id"], ADMIN)["status"], "approved")

    def test_review_roles(self):
        """Core: Lifecycle (AC-3). item_review is admin/publisher/editor only: author and viewer denied."""
        store, site, _ = make_store()
        item = make_item(store, site)
        store.submit_item(AUTHOR, item["id"])
        for user in (AUTHOR, VIEWER):
            with self.assertRaises(PermissionDenied):
                store.approve_item(user, item["id"])

    def test_author_cannot_approve_own_item_store_level(self):
        """Core: Lifecycle (AC-5 separation of duties). Approver whose NAME equals the item author is denied even in a role holding item_review."""
        store, site, _ = make_store()
        item = make_item(store, site)  # author dave
        store.submit_item(AUTHOR, item["id"])
        # Dave-as-editor isolates _check_approver_not_author: role passes, name matches author.
        with self.assertRaises(PermissionDenied):
            store.approve_item(User("dave", "editor"), item["id"])
        with self.assertRaises(PermissionDenied):
            store.return_item(User("dave", "publisher"), item["id"], note="self")
        self.assertEqual(store.get_item(item["id"], ADMIN)["status"], "in_review")
        # A different editor can still approve: denial is SoD, not blanket.
        self.assertEqual(store.approve_item(EDITOR, item["id"])["status"], "approved")

    def test_editor_who_authored_cannot_review_own(self):
        """Core: Lifecycle (AC-5). An editor-authored item cannot be approved by that same editor."""
        store, site, _ = make_store()
        item = store.create_item(EDITOR, site["id"], "ct-page", "Carol Draft", "carol-draft")
        store.submit_item(EDITOR, item["id"])
        with self.assertRaises(PermissionDenied):
            store.approve_item(EDITOR, item["id"])
        self.assertEqual(store.approve_item(PUBLISHER, item["id"])["status"], "approved")


if __name__ == "__main__":
    unittest.main()
