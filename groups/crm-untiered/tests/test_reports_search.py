"""Report and search tests.

Traces to: Core 7 (Reports) and Core 8 (Search) -- registry
mechanics over the build's own records, AU-6. Counts only; no
score or aggregate the claims do not define is computed.
"""

import unittest

import crm_helpers as H
from crm.errors import ValidationError

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"


def _populated():
    store, account, contact = H.make_store()
    store.create_case(H.OPERATOR, "inquiry", "Alpha question",
                      account_id=account["id"], due_at=PAST)
    c2 = store.create_case(H.OPERATOR, "problem", "Beta outage")
    store.transition_case(c2["id"], H.OPERATOR, "in_progress")
    store.record_interaction(H.OPERATOR, "chat", "inbound", "Alpha chat",
                             outcome="answered")
    store.record_interaction(H.OPERATOR, "email", "outbound", "Beta mail")
    store.create_guide(H.OPERATOR, "Alpha tour", "walkthrough", "surface:a")
    store.create_guide(H.OPERATOR, "Beta tip", "tooltip", "surface:b",
                       enabled=False)
    store.create_finding(H.OPERATOR, "Alpha gap", severity="critical")
    store.create_module(H.ADMIN, "Alpha module", "service", "x=1")
    return store, account, contact


class TestReport(unittest.TestCase):
    """Core 7: deterministic aggregate report."""

    def test_report_shape_and_counts(self):
        """Core 7: report shape and counts incl. derived breach."""
        store, account, contact = _populated()
        report = store.report(H.ADMIN, now=NOW)
        self.assertEqual(report["accounts"]["total"], 1)
        self.assertEqual(report["contacts"]["total"], 1)
        self.assertEqual(report["cases"]["total"], 2)
        self.assertEqual(report["cases"]["by_status"], {"open": 1, "in_progress": 1})
        self.assertEqual(report["cases"]["by_type"], {"inquiry": 1, "problem": 1})
        self.assertEqual(report["cases"]["by_account"],
                         {account["id"]: 1, "unassigned": 1})
        self.assertEqual(report["cases"]["breached"], 1)
        self.assertEqual(report["interactions"]["by_channel"],
                         {"chat": 1, "email": 1})
        self.assertEqual(report["interactions"]["by_outcome"],
                         {"answered": 1, "none": 1})
        self.assertEqual(report["guides"],
                         {"total": 2, "by_kind": {"walkthrough": 1, "tooltip": 1},
                          "enabled": 1})
        self.assertEqual(report["findings"],
                         {"total": 1, "by_severity": {"critical": 1},
                          "by_status": {"open": 1}})
        self.assertEqual(report["modules"], {"total": 1, "enabled": 1})

    def test_report_breach_is_now_dependent(self):
        """Core 7: breach count follows the report's now (derived)."""
        store, account, contact = _populated()
        early = store.report(H.ADMIN, now="2019-01-01T00:00:00Z")
        self.assertEqual(early["cases"]["breached"], 0)
        late = store.report(H.ADMIN, now=NOW)
        self.assertEqual(late["cases"]["breached"], 1)

    def test_empty_store_report(self):
        """Core 7: an empty store reports zero totals and empty maps."""
        report = H.fresh_store().report(H.ADMIN, now=NOW)
        self.assertEqual(report["cases"]["total"], 0)
        self.assertEqual(report["cases"]["by_status"], {})
        self.assertEqual(report["guides"]["enabled"], 0)


class TestSearch(unittest.TestCase):
    """Core 8: literal substring search."""

    def test_search_shape_and_matching(self):
        """Core 8: search returns all six buckets and matches
        label/reference, subject, summary, title, detail."""
        store, account, contact = _populated()
        result = store.search("alpha", H.OPERATOR)
        self.assertEqual(set(result.keys()),
                         {"accounts", "contacts", "cases",
                          "interactions", "findings", "guides"})
        self.assertEqual(len(result["accounts"]), 1)       # label "Agency Alpha"
        self.assertEqual(len(result["cases"]), 1)          # "Alpha question"
        self.assertEqual(len(result["interactions"]), 1)   # "Alpha chat"
        self.assertEqual(len(result["findings"]), 1)       # "Alpha gap"
        self.assertEqual(len(result["guides"]), 1)         # "Alpha tour"
        by_ref = store.search("ACCT-100", H.OPERATOR)
        self.assertEqual(len(by_ref["accounts"]), 1)
        by_contact_ref = store.search("PERSON-200", H.OPERATOR)
        self.assertEqual(len(by_contact_ref["contacts"]), 1)

    def test_search_is_literal_not_regex(self):
        """Core 8: search is a literal substring match, not regex."""
        store, account, contact = _populated()
        result = store.search("a.pha", H.OPERATOR)
        self.assertEqual(result["cases"], [])
        result = store.search(".*", H.OPERATOR)
        self.assertEqual(result["accounts"], [])

    def test_search_empty_query(self):
        """Core 8 (SI-10): empty query -> ValidationError."""
        store, account, contact = _populated()
        with self.assertRaises(ValidationError):
            store.search("  ", H.OPERATOR)

    def test_search_audited(self):
        """Core 8/9 (AU-2): a search records a 'search' audit entry."""
        audit = H.AuditLog()
        store = H.CrmStore(audit=audit)
        store.create_account(H.ADMIN, "ACCT-1", label="Alpha")
        store.search("alpha", H.OPERATOR)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("search", actions)


if __name__ == "__main__":
    unittest.main()
