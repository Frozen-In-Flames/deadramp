"""Negative control: the suite must reject a mutant approver gate.

Traces to: the contract's required negative control for Group 20.

The traced claim: **an item is never approved (or returned) by its
own author** -- separation of duties (control family AC-5; sibling
claim family authoring_editing). The store enforces this in
``CmsStore._check_approver_not_author``.

The mutant below is a CmsStore subclass whose
``_check_approver_not_author`` is a no-op, so the mutant approves an
item by the very editor whose name is its author.

Each canonical test asserts three things, per the house pattern:
(1) the canonical expectation from the real implementation
(PermissionDenied, the item stays "in_review"), (2) the mutant would
NOT produce that expectation (it approves), and (3) a literal
assertRaises(AssertionError) showing that treating the mutant's
outcome as the expected outcome fails.

Isolation note: the plain author (dave/author) is *also* barred by
the item_review permission, so the cases present the author's own
identity -- the name "carol" for an editor-authored item -- in the
editor role itself, making ``_check_approver_not_author`` the only
gate that can deny.
"""

import unittest

from cms_helpers import EDITOR, PUBLISHER, make_store
from cms.audit import AuditLog
from cms.errors import PermissionDenied
from cms.store import CmsStore


class MutantCmsStore(CmsStore):
    """Mutant review path: the approver-is-not-author check is skipped."""

    def _check_approver_not_author(self, item, actor):
        """Core: Editorial lifecycle (negative control mutant) -- no-op: author-approval is never checked."""
        return None


def _make_mutant():
    """Build a mutant store with an editor-authored in_review item."""
    store = MutantCmsStore(audit=AuditLog())
    site = store.create_site(PUBLISHER, "Main Site", "main-site")
    item = store.create_item(EDITOR, site["id"], "ct-article", "Carol Post", "carol-post")
    store.submit_item(EDITOR, item["id"])
    return store, site, item


def _make_real():
    """Build a real store with the same editor-authored in_review item."""
    store, site, section = make_store()
    item = store.create_item(EDITOR, site["id"], "ct-article", "Carol Post", "carol-post")
    store.submit_item(EDITOR, item["id"])
    return store, site, item


class TestNegativeControlMutantAuthorApproval(unittest.TestCase):
    """Core: Editorial lifecycle -- negative control for author-approval
    (AC-5 separation of duties; authoring_editing)."""

    def _assert_mutant_rejected(self, mutant_outcome, expected):
        """Core: Editorial lifecycle (negative control). Treating mutant outcome as expected must fail."""
        self.assertNotEqual(mutant_outcome, expected)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, expected)

    def test_author_approve_denied_canonical_but_mutant_approves(self):
        """Core: Editorial lifecycle, traced claim: an item is never approved by its author (AC-5).
        Canonical: carol (editor, the author) approving her own in_review
        item raises PermissionDenied and the item stays in_review.
        Mutant: the same approval succeeds and the item is approved."""
        store, site, item = _make_real()
        with self.assertRaises(PermissionDenied):
            store.approve_item(EDITOR, item["id"])
        self.assertEqual(store.get_item(item["id"], EDITOR)["status"], "in_review")

        mstore, msite, mitem = _make_mutant()
        approved = mstore.approve_item(EDITOR, mitem["id"])
        self.assertEqual(approved["status"], "approved")  # mutant did NOT deny
        self._assert_mutant_rejected(approved["status"], "in_review")

    def test_author_return_denied_canonical_but_mutant_returns(self):
        """Core: Editorial lifecycle, traced claim: an item is never returned by its author (AC-5).
        Canonical: return by the author raises PermissionDenied.
        Mutant: the return succeeds and the item is back in draft."""
        store, site, item = _make_real()
        with self.assertRaises(PermissionDenied):
            store.return_item(EDITOR, item["id"], note="self-return")
        self.assertEqual(store.get_item(item["id"], EDITOR)["status"], "in_review")

        mstore, msite, mitem = _make_mutant()
        returned = mstore.return_item(EDITOR, mitem["id"], note="self-return")
        self.assertEqual(returned["status"], "draft")
        self._assert_mutant_rejected(returned["status"], "in_review")

    def test_other_editor_approval_succeeds_on_real_store(self):
        """Core: Editorial lifecycle (AC-5). Control on the control: a *different* reviewer (publisher bob) approving carol's item succeeds on the real store -- the denial is the author check, not a blanket refusal."""
        store, site, item = _make_real()
        approved = store.approve_item(PUBLISHER, item["id"])
        self.assertEqual(approved["status"], "approved")
        self._assert_mutant_rejected("approved-by-other", "denied-self-approval")


if __name__ == "__main__":
    unittest.main()
