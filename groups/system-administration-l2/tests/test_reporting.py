"""Core 8 (Registry search) and Core 9 (Registry summary):
literal substring search over accessible records only, and a
counts-only summary including the derived overdue request count.
"""

import unittest

import sysadmin_helpers as H


class TestSearch(unittest.TestCase):
    def test_search_matches_systems_applications_requests_changes(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        H.make_request(store, org, system)
        H.make_change(store, org, system)
        by_label = store.search(H.MEMBER, "portal")
        self.assertEqual([a["ref"] for a in by_label["applications"]],
                         ["APP-PORTAL"])
        by_summary = store.search(H.MEMBER, "maintenance")
        self.assertEqual(len(by_summary["requests"]), 1)
        by_kernel = store.search(H.MEMBER, "kernel")
        self.assertEqual(len(by_kernel["changes"]), 1)
        by_ref = store.search(H.MEMBER, "sys-os")
        self.assertEqual([s["ref"] for s in by_ref["systems"]], ["SYS-OS-1"])

    def test_search_is_scoped_to_accessible_orgs(self):
        store, org = H.make_store()
        H.make_estate(store, org)
        result = store.search(H.OUTSIDER, "portal")
        self.assertEqual(result, {"systems": [], "applications": [],
                                  "requests": [], "changes": []})

    def test_empty_query_returns_nothing(self):
        store, org = H.make_store()
        H.make_estate(store, org)
        self.assertEqual(store.search(H.MEMBER, "")["systems"], [])


class TestSummary(unittest.TestCase):
    def test_summary_counts(self):
        store, org = H.make_store()
        system, application = H.make_estate(store, org)
        H.make_system(store, org, ref="SYS-SVC-1", kind="platform_service")
        request = H.make_request(store, org, system)
        H.make_request(store, org, system, summary="Second request",
                       due_date="2999-01-01")
        change = H.make_change(store, org, system)
        store.decide_change(H.STAFF, change["id"], True)
        H.make_control(store, org, system)
        H.make_control(store, org, system, control_ref="AC-2",
                       source="local", note="")
        summary = store.organization_summary(H.MEMBER, org["id"])
        self.assertEqual(summary["systems"], 2)
        self.assertEqual(summary["systems_by_kind"],
                         {"operating_system": 1, "platform_service": 1})
        self.assertEqual(summary["applications"], 1)
        self.assertEqual(summary["requests"], 2)
        self.assertEqual(summary["requests_by_status"]["open"], 2)
        # The canonical due date (2026-06-10) is in the past at the
        # real read clock; the 2999 request is not.
        self.assertEqual(summary["requests_overdue"], 1)
        self.assertEqual(summary["changes_by_status"]["approved"], 1)
        self.assertEqual(summary["controls_by_source"],
                         {"inherited": 1, "local": 1, "shared": 0})
        self.assertEqual(summary["org_id"], org["id"])


if __name__ == "__main__":
    unittest.main()
