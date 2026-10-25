"""Negative control: the breach derivation must be load-bearing.

The mutation drill (performed by hand, recorded in tests/README.md)
patches ``CustsvcStore._is_breached`` to return False unconditionally.
Under that mutant, the tests in this file -- and the breach tests in
test_breach.py, test_status_reports.py and test_service.py -- MUST
fail. If they pass, the suite is testing that code ran, not that
breach state is derived, and the build does not ship.
"""

import unittest

from custsvc_helpers import AGENT, NOW, PAST_DUE, make_case, make_store


class TestNegativeControl(unittest.TestCase):
    def setUp(self):
        self.store, self.audit, self.requester, _, _ = make_store()

    def test_overdue_open_case_reads_breached(self):
        case = make_case(self.store, self.requester, due_at=PAST_DUE)
        view = self.store.get_case(case["id"], AGENT, now=NOW)
        self.assertTrue(view["breached"],
                        "an overdue open case must read breached=True")

    def test_overdue_case_counts_in_report_and_status(self):
        make_case(self.store, self.requester, due_at=PAST_DUE)
        rep = self.store.report_summary(AGENT, now=NOW)
        self.assertEqual(rep["breached_cases"], 1)
        view = self.store.public_status(AGENT, now=NOW)
        self.assertEqual(view["breached_cases"], 1)


if __name__ == "__main__":
    unittest.main()
