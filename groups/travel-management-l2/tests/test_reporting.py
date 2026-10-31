import unittest

from travel_helpers import (MEMBER, make_approved_authorization,
                            make_approved_report, make_authorization,
                            make_store, make_traveler)

SCORE_KEYS = ("score", "rating", "risk", "grade", "rank", "index")


def assert_no_score_keys(testcase, obj, path="root"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            for bad in SCORE_KEYS:
                testcase.assertNotIn(
                    bad, key.lower(),
                    "score-like key %r at %s" % (key, path))
            assert_no_score_keys(testcase, value, path + "." + str(key))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            assert_no_score_keys(testcase, value, "%s[%d]" % (path, i))


class TestReporting(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()
        self.traveler = make_traveler(self.store, self.org)
        self.auth = make_approved_authorization(self.store, self.org,
                                                self.traveler)
        self.report = make_approved_report(self.store, self.auth)
        self.store.record_voucher(MEMBER, self.report["id"], 40_000)

    def test_search_finds_traveler(self):
        result = self.store.search(MEMBER, self.org["id"], "TRV-100")
        self.assertEqual(len(result["travelers"]), 1)

    def test_search_finds_authorization_by_destination(self):
        result = self.store.search(MEMBER, self.org["id"], "denver")
        self.assertEqual(len(result["authorizations"]), 1)

    def test_search_finds_report_by_title(self):
        result = self.store.search(MEMBER, self.org["id"], "expenses")
        self.assertEqual(len(result["expense_reports"]), 1)

    def test_search_no_match(self):
        result = self.store.search(MEMBER, self.org["id"], "zzz-no-match")
        self.assertEqual(result["travelers"], [])
        self.assertEqual(result["authorizations"], [])
        self.assertEqual(result["expense_reports"], [])

    def test_summary_counts_and_sums(self):
        make_authorization(self.store, self.org, self.traveler,
                           purpose="Draft trip")
        summary = self.store.summary(MEMBER, self.org["id"])
        self.assertEqual(summary["travelers"], 1)
        self.assertEqual(summary["authorizations"]["approved"], 1)
        self.assertEqual(summary["authorizations"]["draft"], 1)
        self.assertEqual(summary["expense_reports"]["approved"], 1)
        self.assertEqual(summary["authorized_cents"], 1_000_000)
        self.assertEqual(summary["claimed_cents"], 150_000)
        self.assertEqual(summary["reimbursed_cents"], 40_000)

    def test_authorization_view_carries_claimed_and_reimbursed(self):
        view = self.store.get_authorization(MEMBER, self.auth["id"])
        self.assertEqual(view["claimed_cents"], 150_000)
        self.assertEqual(view["reimbursed_cents"], 40_000)

    def test_no_score_keys_anywhere(self):
        summary = self.store.summary(MEMBER, self.org["id"])
        assert_no_score_keys(self, summary)
        assert_no_score_keys(
            self, self.store.get_authorization(MEMBER, self.auth["id"]))
        assert_no_score_keys(
            self, self.store.get_expense_report(MEMBER, self.report["id"]))
        assert_no_score_keys(
            self, self.store.search(MEMBER, self.org["id"], "Denver"))


if __name__ == "__main__":
    unittest.main()
