"""Status view, registry reporting & search (Core functions 7, 9).

Claim trace: PagerDuty "Real-time status updates and external-facing
status pages keep stakeholders informed" (status_communication).
Reporting beyond registry counts is Extended and claimed by neither
sibling (reporting_dashboards: 0 claims, carried substrate).
"""

import unittest

from custsvc_helpers import (ADMIN, AGENT, NOW, PAST_DUE,
                             make_case, make_store)


class TestStatusView(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, _, _ = make_store()

    def test_operational_when_quiet(self):
        view = self.store.public_status(AGENT, now=NOW)
        self.assertEqual(view["overall"], "operational")
        self.assertEqual(view["open_cases"], 0)

    def test_critical_open_case_is_outage(self):
        make_case(self.store, self.requester, priority="critical")
        self.assertEqual(self.store.public_status(AGENT, now=NOW)["overall"],
                         "outage")

    def test_high_or_breached_is_degraded(self):
        make_case(self.store, self.requester, priority="high")
        self.assertEqual(self.store.public_status(AGENT, now=NOW)["overall"],
                         "degraded")

    def test_breached_normal_case_is_degraded(self):
        make_case(self.store, self.requester, due_at=PAST_DUE)
        view = self.store.public_status(AGENT, now=NOW)
        self.assertEqual(view["overall"], "degraded")
        self.assertEqual(view["breached_cases"], 1)

    def test_terminal_cases_do_not_affect_status(self):
        case = make_case(self.store, self.requester, priority="critical")
        cid = case["id"]
        for nxt in ("open", "resolved"):
            self.store.set_case_status(cid, nxt, AGENT)
        self.assertEqual(self.store.public_status(AGENT, now=NOW)["overall"],
                         "operational")

    def test_only_public_updates_are_shown(self):
        case = make_case(self.store, self.requester)
        self.store.add_case_update(case["id"], "internal note", AGENT, public=False)
        self.store.add_case_update(case["id"], "we are investigating", AGENT,
                                   public=True)
        view = self.store.public_status(AGENT, now=NOW)
        bodies = [u["body"] for u in view["public_updates"]]
        self.assertEqual(bodies, ["we are investigating"])


class TestReportsSearch(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, _, _ = make_store()

    def test_report_counts(self):
        make_case(self.store, self.requester, priority="high", due_at=PAST_DUE)
        make_case(self.store, self.requester, title="Second case")
        self.store.ingest_alert("mon", "evt", "major", AGENT)
        rep = self.store.report_summary(ADMIN, now=NOW)
        self.assertEqual(rep["cases_by_status"]["new"], 2)
        self.assertEqual(rep["cases_by_priority"]["high"], 1)
        self.assertEqual(rep["breached_cases"], 1)
        self.assertEqual(rep["alerts_by_state"]["new"], 1)
        self.assertEqual(rep["requesters"], 1)
        self.assertEqual(rep["responders"], 2)

    def test_search_matches_title_body_and_requester_label(self):
        make_case(self.store, self.requester, title="Portal outage")
        make_case(self.store, self.requester, title="Billing question",
                  body="Invoice portal")
        self.assertEqual(len(self.store.search_cases("portal", AGENT)), 2)
        self.assertEqual(len(self.store.search_cases("billing", AGENT)), 1)
        self.assertEqual(len(self.store.search_cases("citizen one", AGENT)), 2)
        self.assertEqual(len(self.store.search_cases("nonexistent", AGENT)), 0)


if __name__ == "__main__":
    unittest.main()
