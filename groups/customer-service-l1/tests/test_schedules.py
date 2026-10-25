"""On-call schedules (Core function 6): rotation records + a pure
date-arithmetic derivation of who is on call.

Claim trace: PagerDuty "On-call scheduling capabilities ensure
continuous 24/7 coverage" (oncall_scheduling).
"""

import unittest

from custsvc.errors import NotFoundError, ValidationError
from custsvc_helpers import ADMIN, AGENT, make_store


class TestSchedules(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, _, self.rsp1, self.rsp2 = make_store()
        self.sched = self.store.create_schedule(
            "tier-1 rotation", [self.rsp1["id"], self.rsp2["id"]], ADMIN,
            period_days=7, anchor="2026-10-05")  # a Monday

    def test_anchor_week_is_first_member(self):
        oc = self.store.on_call(self.sched["id"], AGENT, at="2026-10-05")
        self.assertEqual(oc["responder_id"], self.rsp1["id"])
        oc = self.store.on_call(self.sched["id"], AGENT, at="2026-10-11")
        self.assertEqual(oc["responder_id"], self.rsp1["id"])

    def test_next_period_is_second_member(self):
        oc = self.store.on_call(self.sched["id"], AGENT, at="2026-10-12")
        self.assertEqual(oc["responder_id"], self.rsp2["id"])

    def test_rotation_wraps(self):
        oc = self.store.on_call(self.sched["id"], AGENT, at="2026-10-19")
        self.assertEqual(oc["responder_id"], self.rsp1["id"])

    def test_before_anchor_wraps_backwards(self):
        oc = self.store.on_call(self.sched["id"], AGENT, at="2026-09-28")
        self.assertEqual(oc["responder_id"], self.rsp2["id"])

    def test_daily_rotation(self):
        sched = self.store.create_schedule(
            "daily", [self.rsp1["id"], self.rsp2["id"]], ADMIN,
            period_days=1, anchor="2026-10-05")
        self.assertEqual(self.store.on_call(sched["id"], AGENT, at="2026-10-06")
                         ["responder_id"], self.rsp2["id"])
        self.assertEqual(self.store.on_call(sched["id"], AGENT, at="2026-10-07")
                         ["responder_id"], self.rsp1["id"])

    def test_unknown_responder_rejected(self):
        with self.assertRaises(NotFoundError):
            self.store.create_schedule("bad", ["rsp-999"], ADMIN,
                                       period_days=7, anchor="2026-10-05")

    def test_empty_rotation_and_bad_period_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_schedule("bad", [], ADMIN)
        with self.assertRaises(ValidationError):
            self.store.create_schedule("bad", [self.rsp1["id"]], ADMIN,
                                       period_days=0)


if __name__ == "__main__":
    unittest.main()
