"""Report and search tests.

Traces to: Core function 8 -- Reports (``ContactStore.report``,
all counts derived deterministically at the given ``now``) and
Core function 9 -- Search (``ContactStore.search``, literal
case-insensitive substring, NOT regex).
"""

import unittest

from contact_helpers import OPERATOR, VIEWER, fresh_store, make_store
from contact.errors import PermissionDenied, ValidationError

NOW = "2025-06-01T00:00:00Z"


def _populated():
    """Core 8/9: Reports/Search -- shared populated fixture."""
    store, agent, contact, queue = make_store()
    c1 = store.create_case(OPERATOR, "claim", "Widget broken", queue_id=queue["id"],
                           due_at="2020-01-01T00:00:00Z")
    c2 = store.create_case(OPERATOR, "inquiry", "Hours question")
    store.transition_case(c2["id"], OPERATOR, "in_progress")
    store.record_interaction(OPERATOR, "voice", "inbound", "Call about widget",
                             case_id=c1["id"], outcome="resolved", external_ref="CALL-77")
    store.record_interaction(OPERATOR, "chat", "outbound", "Chat follow-up")
    store.raise_alert(OPERATOR, "warning", "Widget queue slow")
    a2 = store.raise_alert(OPERATOR, "critical", "Widget outage")
    store.acknowledge_alert(a2["id"], OPERATOR)
    store.schedule_callback(OPERATOR, contact["id"], "2020-01-01T00:00:00Z")
    store.schedule_callback(OPERATOR, contact["id"], "2030-01-01T00:00:00Z")
    cb3 = store.schedule_callback(OPERATOR, contact["id"], "2020-01-01T00:00:00Z")
    store.complete_callback(cb3["id"], OPERATOR)
    return store, agent, contact, queue


class TestReport(unittest.TestCase):
    """Core 8: Reports."""

    def test_report_shape_and_counts(self):
        """Core 8: Reports. report() returns cases/interactions/alerts/callbacks counts derived at now."""
        store, agent, contact, queue = _populated()
        rep = store.report(OPERATOR, now=NOW)
        self.assertEqual(rep["cases"]["total"], 2)
        self.assertEqual(rep["cases"]["by_status"], {"open": 1, "in_progress": 1})
        self.assertEqual(rep["cases"]["by_type"], {"claim": 1, "inquiry": 1})
        self.assertEqual(rep["cases"]["by_queue"][queue["id"]], 1)
        self.assertEqual(rep["cases"]["by_queue"]["unassigned"], 1)
        self.assertEqual(rep["cases"]["breached"], 1)
        self.assertEqual(rep["interactions"]["total"], 2)
        self.assertEqual(rep["interactions"]["by_channel"], {"voice": 1, "chat": 1})
        self.assertEqual(rep["interactions"]["by_outcome"], {"resolved": 1, "none": 1})
        self.assertEqual(rep["alerts"]["total"], 2)
        self.assertEqual(rep["alerts"]["by_severity"], {"warning": 1, "critical": 1})
        self.assertEqual(rep["alerts"]["by_status"], {"raised": 1, "acknowledged": 1})
        self.assertEqual(rep["callbacks"]["total"], 3)
        self.assertEqual(rep["callbacks"]["by_state"],
                         {"overdue": 1, "scheduled": 1, "completed": 1})

    def test_report_breach_is_now_dependent(self):
        """Core 8: Reports (derived status). The same store reports breached=0 before the due date and 1 after."""
        store, agent, contact, queue = _populated()
        self.assertEqual(store.report(OPERATOR, now="2019-01-01T00:00:00Z")["cases"]["breached"], 0)
        self.assertEqual(store.report(OPERATOR, now=NOW)["cases"]["breached"], 1)
        early = store.report(OPERATOR, now="2019-01-01T00:00:00Z")
        self.assertEqual(early["callbacks"]["by_state"].get("overdue", 0), 0)

    def test_report_empty_store(self):
        """Core 8: Reports. An empty store reports zero totals and empty breakdowns."""
        rep = fresh_store().report(VIEWER, now=NOW)
        self.assertEqual(rep["cases"]["total"], 0)
        self.assertEqual(rep["cases"]["breached"], 0)
        self.assertEqual(rep["interactions"]["total"], 0)
        self.assertEqual(rep["alerts"]["total"], 0)
        self.assertEqual(rep["callbacks"]["total"], 0)

    def test_report_readable_by_viewer(self):
        """Core 8/11: Reports/RBAC. report_read is held by all roles including viewer."""
        store, agent, contact, queue = _populated()
        self.assertEqual(store.report(VIEWER, now=NOW)["cases"]["total"], 2)


class TestSearch(unittest.TestCase):
    """Core 9: Search."""

    def test_search_shape_and_people(self):
        """Core 9: Search. search() returns {people, cases, interactions, alerts}; people matches agent/contact names and contact reference."""
        store, agent, contact, queue = _populated()
        result = store.search("dana", OPERATOR)
        self.assertEqual(set(result.keys()), {"people", "cases", "interactions", "alerts"})
        self.assertEqual([p["id"] for p in result["people"]], [agent["id"]])
        by_ref = store.search("ext-1001", OPERATOR)
        self.assertEqual([p["id"] for p in by_ref["people"]], [contact["id"]])
        by_name = store.search("CASEY", OPERATOR)
        self.assertEqual([p["id"] for p in by_name["people"]], [contact["id"]])

    def test_search_cases_interactions_alerts(self):
        """Core 9: Search. Cases match on subject, interactions on summary + external_ref, alerts on message (case-insensitive)."""
        store, agent, contact, queue = _populated()
        result = store.search("WIDGET", OPERATOR)
        self.assertEqual(len(result["cases"]), 1)
        self.assertEqual(len(result["interactions"]), 1)
        self.assertEqual(len(result["alerts"]), 2)
        by_ref = store.search("call-77", OPERATOR)
        self.assertEqual(len(by_ref["interactions"]), 1)

    def test_search_is_literal_not_regex(self):
        """Core 9: Search. The query is a literal substring: regex metacharacters match literally, not as patterns."""
        store, agent, contact, queue = _populated()
        self.assertEqual(store.search("w.dget", OPERATOR)["cases"], [])
        self.assertEqual(store.search(".*", OPERATOR)["cases"], [])
        self.assertEqual(len(store.search("widget", OPERATOR)["cases"]), 1)

    def test_search_empty_query_validation(self):
        """Core 9: Search (SI-10). Empty/blank/non-string query -> ValidationError."""
        store, agent, contact, queue = _populated()
        for bad in ("", "   ", None, 42):
            with self.assertRaises(ValidationError):
                store.search(bad, OPERATOR)

    def test_search_no_match_returns_empty_lists(self):
        """Core 9: Search. A query matching nothing returns empty lists in every bucket."""
        store, agent, contact, queue = _populated()
        result = store.search("zzzz-no-match", VIEWER)
        self.assertEqual(result, {"people": [], "cases": [], "interactions": [], "alerts": []})


if __name__ == "__main__":
    unittest.main()
