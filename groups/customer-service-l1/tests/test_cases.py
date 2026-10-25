"""Case registry + lifecycle (Core function 1) and assignment (3).

Claim trace: PagerDuty "triage events, including customer support
tickets" (case_ticket_management); "mobilize the appropriate
responders" (responder_assignment).
"""

import unittest

from custsvc.errors import NotFoundError, ValidationError
from custsvc_helpers import AGENT, make_case, make_store


class TestCases(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, self.rsp1, self.rsp2 = make_store()

    def test_create_defaults(self):
        case = make_case(self.store, self.requester)
        self.assertTrue(case["id"].startswith("case-"))
        self.assertEqual(case["status"], "new")
        self.assertEqual(case["priority"], "normal")
        self.assertFalse(case["breached"])
        self.assertEqual(case["requester_ref"], "citizen-001")

    def test_unknown_requester_rejected(self):
        with self.assertRaises(NotFoundError):
            self.store.create_case("t", "b", "ghost-ref", AGENT)

    def test_bad_priority_rejected(self):
        with self.assertRaises(ValidationError):
            make_case(self.store, self.requester, priority="whenever")

    def test_full_lifecycle(self):
        case = make_case(self.store, self.requester)
        cid = case["id"]
        for nxt in ("open", "in_progress", "resolved", "closed"):
            case = self.store.set_case_status(cid, nxt, AGENT)
            self.assertEqual(case["status"], nxt)

    def test_invalid_transition_rejected(self):
        case = make_case(self.store, self.requester)
        with self.assertRaises(ValidationError):
            self.store.set_case_status(case["id"], "in_progress", AGENT)  # new -/-> in_progress
        with self.assertRaises(ValidationError):
            self.store.set_case_status(case["id"], "bogus", AGENT)

    def test_reopen_from_resolved_and_closed(self):
        case = make_case(self.store, self.requester)
        cid = case["id"]
        for nxt in ("open", "resolved", "open", "in_progress", "resolved", "closed", "open"):
            case = self.store.set_case_status(cid, nxt, AGENT)
        self.assertEqual(case["status"], "open")

    def test_assignment_and_reassignment(self):
        case = make_case(self.store, self.requester)
        case = self.store.assign_case(case["id"], self.rsp1["id"], AGENT)
        self.assertEqual(case["assignee"], self.rsp1["id"])
        case = self.store.assign_case(case["id"], self.rsp2["id"], AGENT)
        self.assertEqual(case["assignee"], self.rsp2["id"])
        with self.assertRaises(NotFoundError):
            self.store.assign_case(case["id"], "rsp-999", AGENT)

    def test_list_filters(self):
        a = make_case(self.store, self.requester, priority="high")
        make_case(self.store, self.requester, title="Second case")
        self.store.assign_case(a["id"], self.rsp1["id"], AGENT)
        self.assertEqual(len(self.store.list_cases(AGENT, priority="high")), 1)
        self.assertEqual(len(self.store.list_cases(AGENT, assignee=self.rsp1["id"])), 1)
        self.assertEqual(len(self.store.list_cases(AGENT, status="new")), 2)


if __name__ == "__main__":
    unittest.main()
