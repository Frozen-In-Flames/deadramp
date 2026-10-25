"""Derived alerts, report and search tests.

Traces to: Core -- Derived alerts (``list_alerts``, report_read),
aggregate report (``report``) and literal search (``search``,
project_read). All derived values are computed at the call's ``now``
from the single derivation points in the store.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from construct.errors import ValidationError

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"
PS = "2025-01-01T00:00:00Z"
PE = "2025-01-15T00:00:00Z"


def _executed(store, project_id, title, end_at):
    """Alerts/reports helper: an executed contract."""
    con = store.create_contract(OPERATOR, title, project_id, end_at=end_at)
    store.transition_contract(con["id"], OPERATOR, "in_review")
    store.transition_contract(con["id"], OPERATOR, "executed")
    return con


class TestAlerts(unittest.TestCase):
    """Alerts: each kind produced deterministically, sorted."""

    def test_compliance_no_records_for_bare_participants(self):
        """Alerts. Bare participants produce compliance_no_records alerts only."""
        store, project, prime, sub = make_store()
        alerts = store.list_alerts(VIEWER, now=NOW)
        self.assertEqual(len(alerts), 2)
        self.assertTrue(all(a["kind"] == "compliance_no_records" for a in alerts))
        self.assertEqual({a["ref_id"] for a in alerts}, {prime["id"], sub["id"]})
        self.assertTrue(all(a["project_id"] == project["id"] for a in alerts))
        self.assertTrue(all(set(a.keys()) == {"kind", "project_id", "ref_id", "message"} for a in alerts))

    def test_each_alert_kind(self):
        """Alerts. contract_expired/expiring, milestone/submittal/rfi/punch overdue, compliance kinds."""
        store, project, prime, sub = make_store()
        pid = project["id"]
        _executed(store, pid, "Old deal", PAST)
        _executed(store, pid, "Soon deal", "2025-06-20T00:00:00Z")
        _executed(store, pid, "Far deal", "2030-01-01T00:00:00Z")
        store.create_milestone(OPERATOR, pid, "Late milestone", PAST)
        store.create_submittal(OPERATOR, pid, "Late submittal", due_at=PAST)
        store.create_rfi(OPERATOR, pid, "Late question?", due_at=PAST)
        store.create_punch_item(OPERATOR, pid, "Late fix", due_at=PAST)
        store.create_violation(ADMIN, pid, prime["id"], "wage", "Issue")
        store.create_payroll(OPERATOR, pid, sub["id"], PS, PE, certified=True)
        alerts = store.list_alerts(ADMIN, now=NOW)
        kinds = [a["kind"] for a in alerts]
        self.assertIn("contract_expired", kinds)
        self.assertIn("contract_expiring", kinds)
        self.assertIn("milestone_overdue", kinds)
        self.assertIn("submittal_overdue", kinds)
        self.assertIn("rfi_overdue", kinds)
        self.assertIn("punch_overdue", kinds)
        self.assertIn("compliance_noncompliant", kinds)
        # prime is noncompliant (not no_records); sub is compliant -> neither compliance alert for sub.
        self.assertNotIn("compliance_no_records", kinds)
        noncomp = [a for a in alerts if a["kind"] == "compliance_noncompliant"][0]
        self.assertEqual(noncomp["ref_id"], prime["id"])
        expired = [a for a in alerts if a["kind"] == "contract_expired"][0]
        self.assertIn(expired["ref_id"], expired["message"])

    def test_alerts_sorted_by_kind_then_ref(self):
        """Alerts. Output is sorted by (kind, ref_id)."""
        store, project, prime, sub = make_store()
        pid = project["id"]
        _executed(store, pid, "Old deal", PAST)
        store.create_milestone(OPERATOR, pid, "Late", PAST)
        store.create_rfi(OPERATOR, pid, "Q?", due_at=PAST)
        alerts = store.list_alerts(ADMIN, now=NOW)
        keys = [(a["kind"], a["ref_id"]) for a in alerts]
        self.assertEqual(keys, sorted(keys))

    def test_alerts_now_dependent(self):
        """Alerts. At an early now the same records produce no overdue/expired alerts."""
        store, project, prime, sub = make_store()
        pid = project["id"]
        _executed(store, pid, "Deal", "2025-06-20T00:00:00Z")
        store.create_milestone(OPERATOR, pid, "M", "2025-06-20T00:00:00Z")
        early = store.list_alerts(ADMIN, now="2025-01-01T00:00:00Z")
        kinds = {a["kind"] for a in early}
        self.assertNotIn("contract_expired", kinds)
        self.assertNotIn("contract_expiring", kinds)
        self.assertNotIn("milestone_overdue", kinds)
        late = store.list_alerts(ADMIN, now="2026-01-01T00:00:00Z")
        kinds = {a["kind"] for a in late}
        self.assertIn("contract_expired", kinds)
        self.assertIn("milestone_overdue", kinds)


class TestReport(unittest.TestCase):
    """Report: shape, counts, now-dependence."""

    def test_report_shape_and_counts(self):
        """Report. Full shape with counts over all entity families."""
        store, project, prime, sub = make_store()
        pid = project["id"]
        _executed(store, pid, "Deal", PAST)
        store.create_contract(OPERATOR, "Draft deal", pid)
        store.create_milestone(OPERATOR, pid, "Late", PAST)
        store.create_milestone(OPERATOR, pid, "Far", "2030-01-01T00:00:00Z")
        s = store.create_submittal(OPERATOR, pid, "Late sub", due_at=PAST)
        store.create_rfi(OPERATOR, pid, "Late q?", due_at=PAST)
        store.create_punch_item(OPERATOR, pid, "Late fix", due_at=PAST)
        store.create_incident(OPERATOR, pid, "safety", "Near miss")
        store.create_payroll(OPERATOR, pid, prime["id"], PS, PE, certified=True)
        store.create_violation(ADMIN, pid, sub["id"], "wage", "Issue")
        store.create_cost_entry(OPERATOR, pid, "m", "Steel", budgeted_cents=1000, actual_cents=250)
        rep = store.report(VIEWER, now=NOW)
        self.assertEqual(rep["projects"], {"total": 1, "by_status": {"active": 1}})
        self.assertEqual(rep["contracts"]["total"], 2)
        self.assertEqual(rep["contracts"]["by_status"], {"executed": 1, "draft": 1})
        self.assertEqual(rep["contracts"]["by_expiry_state"], {"expired": 1, "pre_execution": 1})
        self.assertEqual(rep["milestones"]["total"], 2)
        self.assertEqual(rep["milestones"]["by_due_state"], {"overdue": 1, "upcoming": 1})
        self.assertEqual(rep["submittals"], {"total": 1, "overdue": 1})
        self.assertEqual(rep["rfis"], {"total": 1, "overdue": 1})
        self.assertEqual(rep["punch_items"], {"total": 1, "open": 1, "overdue": 1})
        self.assertEqual(rep["incidents"], {"total": 1, "by_status": {"reported": 1}})
        self.assertEqual(rep["compliance"], {"compliant": 1, "noncompliant": 1, "no_records": 0})
        self.assertEqual(rep["costs"], {"entries": 1, "total_budgeted_cents": 1000,
                                        "total_actual_cents": 250, "variance_cents": 750})

    def test_report_expiry_is_now_dependent(self):
        """Report. Contract by_expiry_state counts change with now (expiring -> expired)."""
        store, project, prime, sub = make_store()
        _executed(store, project["id"], "Deal", "2025-06-20T00:00:00Z")
        early = store.report(ADMIN, now=NOW)
        self.assertEqual(early["contracts"]["by_expiry_state"], {"expiring": 1})
        late = store.report(ADMIN, now="2026-01-01T00:00:00Z")
        self.assertEqual(late["contracts"]["by_expiry_state"], {"expired": 1})

    def test_report_empty_store(self):
        """Report. An empty store reports zero totals and empty breakdowns."""
        store = fresh_store()
        rep = store.report(ADMIN, now=NOW)
        self.assertEqual(rep["projects"]["total"], 0)
        self.assertEqual(rep["contracts"]["total"], 0)
        self.assertEqual(rep["compliance"], {"compliant": 0, "noncompliant": 0, "no_records": 0})
        self.assertEqual(rep["costs"]["entries"], 0)
        self.assertEqual(rep["submittals"]["overdue"], 0)


class TestSearch(unittest.TestCase):
    """Search: shape, matching, literal semantics."""

    def _seed(self):
        """Search helper: one matchable record per family."""
        store, project, prime, sub = make_store()
        store.create_document(OPERATOR, "Tower drawings", project_id=project["id"], doc_type="drawing")
        _executed(store, project["id"], "Tower contract", "2030-01-01T00:00:00Z")
        return store, project, prime, sub

    def test_search_shape(self):
        """Search. Result keys are exactly {projects, organizations, documents, contracts}."""
        store, project, prime, sub = self._seed()
        result = store.search("tower", OPERATOR)
        self.assertEqual(set(result.keys()), {"projects", "organizations", "documents", "contracts"})

    def test_search_matching(self):
        """Search. Projects by name, orgs by name+reference, documents/contracts by title (case-insensitive)."""
        store, project, prime, sub = self._seed()
        result = store.search("TOWER", OPERATOR)
        self.assertEqual([p["name"] for p in result["projects"]], ["Tower One"])
        self.assertEqual([d["title"] for d in result["documents"]], ["Tower drawings"])
        self.assertEqual([c["title"] for c in result["contracts"]], ["Tower contract"])
        self.assertIn("expiry_state", result["contracts"][0])
        by_name = store.search("prime builders", OPERATOR)
        self.assertEqual([o["id"] for o in by_name["organizations"]], [prime["id"]])
        by_ref = store.search("sub-1", OPERATOR)
        self.assertEqual([o["id"] for o in by_ref["organizations"]], [sub["id"]])
        none = store.search("nonexistent", OPERATOR)
        self.assertEqual(none["projects"], [])

    def test_search_literal_not_regex(self):
        """Search. The query is a literal substring: '.*' and 'a.c' match nothing extra."""
        store, project, prime, sub = self._seed()
        self.assertEqual(store.search(".*", OPERATOR)["projects"], [])
        self.assertEqual(store.search("t.wer", OPERATOR)["projects"], [])
        self.assertEqual(len(store.search("tower", OPERATOR)["projects"]), 1)

    def test_search_empty_query(self):
        """Search. Empty/blank/non-string query -> ValidationError."""
        store, project, prime, sub = self._seed()
        for bad in ("", "   ", None):
            with self.subTest(query=bad):
                with self.assertRaises(ValidationError):
                    store.search(bad, OPERATOR)


if __name__ == "__main__":
    unittest.main()
