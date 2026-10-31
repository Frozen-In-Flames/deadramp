"""Core: Search & summary reporting. Traces to UNION-SPEC core
function 8: literal case-insensitive substring search over
accessible records, and a per-commons summary computed on read
from records only — counts (by tier, by stored request status,
by derived grant status), never scores."""

import unittest

import research_helpers as H
from research.errors import PermissionDenied


class TestCommonsSummary(unittest.TestCase):
    def setUp(self):
        self.store, self.commons, self.org = H.make_store()

    def test_empty_commons_summary(self):
        summary = self.store.commons_summary(H.MEMBER, self.commons["id"],
                                             now=H.INSIDE_WINDOW)
        self.assertEqual(summary["commons_id"], self.commons["id"])
        self.assertEqual(summary["kind"], "commons")
        self.assertEqual(summary["status"], "draft")
        self.assertEqual(summary["workspaces"], 0)
        self.assertEqual(summary["datasets_by_tier"],
                         {"open": 0, "controlled": 0})
        self.assertEqual(summary["requests_by_status"],
                         {"pending": 0, "approved": 0, "denied": 0,
                          "withdrawn": 0})
        self.assertEqual(summary["grants_by_status"],
                         {"scheduled": 0, "active": 0, "expired": 0,
                          "revoked": 0})

    def test_summary_counts_computed_from_records(self):
        cid = self.commons["id"]
        self.store.activate_commons(H.MEMBER, cid)
        H.make_workspace(self.store, self.commons)
        H.make_workspace(self.store, self.commons,
                         name="sharing-workspace",
                         purpose="Workspace for sharing records")
        H.make_dataset(self.store, self.commons, name="open-registry",
                       access_tier="open", sha256=H.SHA256_B)
        controlled_a = H.make_dataset(self.store, self.commons,
                                      name="controlled-a")
        controlled_b = H.make_dataset(self.store, self.commons,
                                      name="controlled-b")

        approved = H.make_access_request(self.store, controlled_a)
        self.store.decide_access_request(H.STAFF, approved["id"], True,
                                         starts_at=H.T0)
        denied = H.make_access_request(self.store, controlled_a,
                                       purpose="Second planned analysis")
        self.store.decide_access_request(H.STAFF, denied["id"], False,
                                         note="Out of scope")
        H.make_access_request(self.store, controlled_b,
                              purpose="Third planned analysis")
        withdrawn = H.make_access_request(self.store, controlled_b,
                                          purpose="Fourth planned analysis")
        self.store.withdraw_access_request(H.MEMBER, withdrawn["id"])

        summary = self.store.commons_summary(H.MEMBER, cid,
                                             now=H.INSIDE_WINDOW)
        self.assertEqual(summary["status"], "active")
        self.assertEqual(summary["workspaces"], 2)
        self.assertEqual(summary["datasets_by_tier"],
                         {"open": 1, "controlled": 2})
        self.assertEqual(summary["requests_by_status"],
                         {"pending": 1, "approved": 1, "denied": 1,
                          "withdrawn": 1})
        self.assertEqual(summary["grants_by_status"],
                         {"scheduled": 0, "active": 1, "expired": 0,
                          "revoked": 0})
        # At a later read clock the same grant counts as expired:
        # the summary is computed on read, never stored.
        later = self.store.commons_summary(H.MEMBER, cid,
                                           now=H.AFTER_EXPIRY)
        self.assertEqual(later["grants_by_status"],
                         {"scheduled": 0, "active": 0, "expired": 1,
                          "revoked": 0})

    def test_outsider_summary_denied(self):
        with self.assertRaises(PermissionDenied):
            self.store.commons_summary(H.OUTSIDER, self.commons["id"],
                                       now=H.INSIDE_WINDOW)


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.store, self.commons, self.org = H.make_store()
        self.dataset = H.make_dataset(self.store, self.commons)

    def test_search_finds_commons_org_and_dataset(self):
        hits = self.store.search(H.MEMBER, "gen3")
        self.assertEqual([c["id"] for c in hits["commons"]],
                         [self.commons["id"]])
        hits = self.store.search(H.MEMBER, "northstar")
        self.assertEqual([o["id"] for o in hits["organizations"]],
                         [self.org["id"]])
        hits = self.store.search(H.MEMBER, "trial")
        self.assertEqual([d["id"] for d in hits["datasets"]],
                         [self.dataset["id"]])

    def test_search_is_case_insensitive(self):
        hits = self.store.search(H.MEMBER, "TRIAL")
        self.assertEqual(len(hits["datasets"]), 1)
        hits = self.store.search(H.MEMBER, "GEN3")
        self.assertEqual(len(hits["commons"]), 1)

    def test_outsider_search_sees_no_commons_content(self):
        hits = self.store.search(H.OUTSIDER, "gen3")
        self.assertEqual(hits["commons"], [])
        self.assertEqual(hits["datasets"], [])
        hits = self.store.search(H.OUTSIDER, "trial")
        self.assertEqual(hits["datasets"], [])
        # Organizations are a global registry, visible to any reader.
        hits = self.store.search(H.OUTSIDER, "northstar")
        self.assertEqual(len(hits["organizations"]), 1)


if __name__ == "__main__":
    unittest.main()
