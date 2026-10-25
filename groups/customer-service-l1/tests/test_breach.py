"""Priority & due records; breach DERIVED at read (Core function 4).

Claim trace: PagerDuty "prioritize critical alerts"
(alert_prioritization). No sibling claims SLA terms, so there is no
SLA policy engine in the union: the substrate holds a per-case due
time and derives breach from it. This derivation is the group's
negative-control target (see test_negative_control.py + README).
"""

import unittest

from custsvc_helpers import (AGENT, FUTURE_DUE, NOW, PAST_DUE,
                             make_case, make_store)


class TestBreachDerivation(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, _, _ = make_store()

    def test_past_due_open_case_is_breached(self):
        case = make_case(self.store, self.requester, due_at=PAST_DUE)
        view = self.store.get_case(case["id"], AGENT, now=NOW)
        self.assertTrue(view["breached"])

    def test_future_due_not_breached(self):
        case = make_case(self.store, self.requester, due_at=FUTURE_DUE)
        self.assertFalse(self.store.get_case(case["id"], AGENT, now=NOW)["breached"])

    def test_no_due_never_breached(self):
        case = make_case(self.store, self.requester)
        self.assertFalse(self.store.get_case(case["id"], AGENT, now=NOW)["breached"])

    def test_terminal_status_not_breached_even_past_due(self):
        case = make_case(self.store, self.requester, due_at=PAST_DUE)
        cid = case["id"]
        for nxt in ("open", "resolved"):
            self.store.set_case_status(cid, nxt, AGENT)
        self.assertFalse(self.store.get_case(cid, AGENT, now=NOW)["breached"])

    def test_breach_is_derived_not_stored(self):
        case = make_case(self.store, self.requester, due_at=PAST_DUE)
        early = self.store.get_case(case["id"], AGENT, now="2019-06-01T00:00:00+00:00")
        late = self.store.get_case(case["id"], AGENT, now=NOW)
        self.assertFalse(early["breached"])
        self.assertTrue(late["breached"])

    def test_priority_recorded_and_validated(self):
        case = make_case(self.store, self.requester, priority="critical")
        self.assertEqual(case["priority"], "critical")


if __name__ == "__main__":
    unittest.main()
