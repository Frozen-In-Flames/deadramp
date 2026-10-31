"""Core 16 (registry reporting) and Core 17 (registry search).

Traces to: UNION-SPEC.md core functions 16-17 — counts and cent
sums computed on read, derived overdue counts, membership-scoped
substring search. Nothing is scored anywhere.
"""

import unittest

import contractmgmt_helpers as H
from contractmgmt.errors import ValidationError

REPORT_KEYS = {
    "org_id", "contract_count", "contracts_by_status",
    "obligated_cents_total", "ceiling_cents_total",
    "modification_count", "requirement_count",
    "requirements_by_status", "protest_count", "open_protests",
    "datacall_count", "open_datacalls", "overdue_datacalls",
    "risk_count", "open_risks", "communication_count",
    "opportunity_count", "opportunities_by_kind",
    "opportunities_by_status", "submission_count", "award_count",
    "award_cents_total", "payment_count", "payment_cents_total",
    "payments_by_kind", "workflow_count", "integration_count",
}


def _populated(store, org):
    """One of everything, with known amounts."""
    contract = H.make_contract(store, org)
    store.record_modification(org["id"], contract["id"], "MOD-1",
                              100_000, H.MEMBER)
    store.create_requirement(org["id"], "REQ-1", "FAR compliance",
                             H.MEMBER)
    req2 = store.create_requirement(org["id"], "REQ-2", "DFARS compliance",
                                    H.MEMBER)
    store.satisfy_requirement(org["id"], req2["id"], H.MEMBER)
    store.create_protest(org["id"], "PRO-1", "Protest", "2027-01-01",
                         H.MEMBER, contract_id=contract["id"])
    store.create_datacall(org["id"], "DCL-1", "AUDITOR-REF", "Data call",
                          "2020-01-01", H.MEMBER)
    store.create_risk(org["id"], "RSK-1", "Risk", H.MEMBER)
    store.record_communication(org["id"], "COM-1", H.COUNTERPARTY_REF,
                               "inbound", "Question", H.MEMBER)
    H.make_participant(store)
    opp = H.make_opportunity(store, org)
    sub = store.record_submission(org["id"], opp["id"], "SUB-1",
                                  H.PARTICIPANT_REF, H.MEMBER)
    store.record_award(org["id"], opp["id"], sub["id"], "AWD-1",
                       500_000, H.MEMBER)
    store.record_payment(org["id"], "PAY-1", "subscription", 120_000,
                         H.MEMBER)
    store.record_payment(org["id"], "PAY-2", "award_fee", 25_000,
                         H.MEMBER)
    store.register_workflow(org["id"], "WFL-1", "Workflow", H.MEMBER)
    store.register_integration(org["id"], "INT-1", "SYS-REF", "Interface",
                               H.MEMBER)
    return contract


class TestReport(unittest.TestCase):
    """Core 16: the organization report."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()

    def test_empty_report_shape_and_zeros(self):
        """Core 16: the report carries exactly the contract's keys,
        zero-filled for an empty organization."""
        report = self.store.org_report(self.org["id"], H.MEMBER)
        self.assertEqual(set(report.keys()), REPORT_KEYS)
        self.assertEqual(report["contract_count"], 0)
        self.assertEqual(report["contracts_by_status"],
                         {"active": 0, "closed": 0})
        self.assertEqual(report["opportunities_by_kind"],
                         {"erfx": 0, "reverse_auction": 0,
                          "financial_assistance": 0})
        self.assertEqual(report["payments_by_kind"],
                         {"subscription": 0, "award_fee": 0})

    def test_report_counts_and_sums(self):
        """Core 16: counts and cent sums are computed on read from
        the records (obligated = base award + modifications)."""
        _populated(self.store, self.org)
        report = self.store.org_report(self.org["id"], H.MEMBER,
                                       now="2026-06-01")
        self.assertEqual(report["contract_count"], 1)
        self.assertEqual(report["obligated_cents_total"],
                         H.AWARD + 100_000)
        self.assertEqual(report["ceiling_cents_total"], H.CEILING)
        self.assertEqual(report["modification_count"], 1)
        self.assertEqual(report["requirements_by_status"],
                         {"open": 1, "satisfied": 1, "waived": 0})
        self.assertEqual(report["open_protests"], 1)
        self.assertEqual(report["open_datacalls"], 1)
        self.assertEqual(report["overdue_datacalls"], 1)
        self.assertEqual(report["open_risks"], 1)
        self.assertEqual(report["communication_count"], 1)
        self.assertEqual(report["submission_count"], 1)
        self.assertEqual(report["award_count"], 1)
        self.assertEqual(report["award_cents_total"], 500_000)
        self.assertEqual(report["payment_cents_total"], 145_000)
        self.assertEqual(report["payments_by_kind"],
                         {"subscription": 120_000, "award_fee": 25_000})
        self.assertEqual(report["workflow_count"], 1)
        self.assertEqual(report["integration_count"], 1)

    def test_report_has_no_score_keys(self):
        """Core 16 / privacy: no key anywhere in the report names a
        score, rating, or ranking."""
        _populated(self.store, self.org)
        report = self.store.org_report(self.org["id"], H.MEMBER)

        def scan(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    lowered = str(key).lower()
                    for banned in ("score", "rating", "rank", "grade"):
                        self.assertNotIn(banned, lowered)
                    scan(value)
            elif isinstance(obj, list):
                for value in obj:
                    scan(value)

        scan(report)


class TestSearch(unittest.TestCase):
    """Core 17: registry search."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        _populated(self.store, self.org)

    def test_search_matches_refs_titles_kinds(self):
        """Core 17: substring match over refs, titles, labels, and
        kinds, case-insensitive."""
        hits = self.store.search_registry(H.MEMBER, "con-ref")
        self.assertEqual(len(hits["contracts"]), 1)
        hits = self.store.search_registry(H.MEMBER, "ERFX")
        self.assertEqual(len(hits["opportunities"]), 1)
        hits = self.store.search_registry(H.MEMBER, "par-ref")
        self.assertEqual(len(hits["participants"]), 1)
        hits = self.store.search_registry(H.MEMBER, "office")
        self.assertEqual(len(hits["organizations"]), 1)

    def test_search_scoped_to_membership(self):
        """Core 17 / AC: an outsider sees only the platform
        participant registry; organization records stay hidden."""
        hits = self.store.search_registry(H.OUTSIDER, "con-ref")
        self.assertEqual(hits["contracts"], [])
        self.assertEqual(hits["organizations"], [])
        hits = self.store.search_registry(H.OUTSIDER, "par-ref")
        self.assertEqual(len(hits["participants"]), 1)

    def test_search_empty_query_rejected(self):
        """Core 17 / SI-10: an empty query is a validation error."""
        with self.assertRaises(ValidationError):
            self.store.search_registry(H.MEMBER, "  ")
        with self.assertRaises(ValidationError):
            self.store.search_registry(H.MEMBER, "")


if __name__ == "__main__":
    unittest.main()
