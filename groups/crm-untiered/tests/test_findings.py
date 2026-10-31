"""Gap-finding record tests.

Traces to: Core 5 (Gap-finding records) -- claim basis
gap_identification (WalkMe). The build records findings with their
text verbatim; the identification engine is Extended.
"""

import unittest

import crm_helpers as H
from crm.errors import NotFoundError, ValidationError


class TestFindings(unittest.TestCase):
    """Core 5: findings (find-) with lifecycle."""

    def setUp(self):
        self.store, self.account, self.contact = H.make_store()

    def test_create_shape_verbatim(self):
        """Core 5: finding shape; detail stored verbatim, status open."""
        detail = "Users abandon the renewal flow at step 3 (observed)."
        finding = self.store.create_finding(
            H.OPERATOR, "Renewal flow drop-off", detail=detail,
            severity="warning", account_id=self.account["id"],
            source="adoption review")
        self.assertEqual(finding["id"], "find-1")
        self.assertEqual(finding["detail"], detail)
        self.assertEqual(finding["status"], "open")

    def test_severities(self):
        """Core 5: all severities accepted; unknown -> ValidationError."""
        for severity in ("info", "warning", "critical"):
            f = self.store.create_finding(H.OPERATOR, "t", severity=severity)
            self.assertEqual(f["severity"], severity)
        with self.assertRaises(ValidationError):
            self.store.create_finding(H.OPERATOR, "t", severity="blocker")

    def test_unknown_account(self):
        """Core 5: unknown account link -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.create_finding(H.OPERATOR, "t", account_id="acct-99")

    def test_lifecycle(self):
        """Core 5: open -> acknowledged -> addressed; dismiss from
        open and from acknowledged."""
        f = self.store.create_finding(H.OPERATOR, "gap A")
        out = self.store.transition_finding(f["id"], H.OPERATOR, "acknowledged")
        self.assertEqual(out["status"], "acknowledged")
        out = self.store.transition_finding(f["id"], H.OPERATOR, "addressed")
        self.assertEqual(out["status"], "addressed")
        f2 = self.store.create_finding(H.OPERATOR, "gap B")
        out = self.store.transition_finding(f2["id"], H.OPERATOR, "dismissed")
        self.assertEqual(out["status"], "dismissed")

    def test_invalid_transitions(self):
        """Core 5: skipping states and leaving terminal states ->
        ValidationError."""
        f = self.store.create_finding(H.OPERATOR, "gap")
        with self.assertRaises(ValidationError):
            self.store.transition_finding(f["id"], H.OPERATOR, "addressed")
        self.store.transition_finding(f["id"], H.OPERATOR, "dismissed")
        with self.assertRaises(ValidationError):
            self.store.transition_finding(f["id"], H.OPERATOR, "acknowledged")

    def test_filters(self):
        """Core 5: list filters by status and account."""
        self.store.create_finding(H.OPERATOR, "a", account_id=self.account["id"])
        f2 = self.store.create_finding(H.OPERATOR, "b")
        self.store.transition_finding(f2["id"], H.OPERATOR, "dismissed")
        self.assertEqual(len(self.store.list_findings(H.VIEWER, status="open")), 1)
        self.assertEqual(
            len(self.store.list_findings(H.VIEWER, account_id=self.account["id"])), 1)
        self.assertEqual(len(self.store.list_findings(H.VIEWER)), 2)


if __name__ == "__main__":
    unittest.main()
