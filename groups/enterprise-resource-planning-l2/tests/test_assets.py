"""Core functions 10-11: asset records and maintenance work
order records (CM-6, AU-2/AU-3, SI-10).

Asset criticality is a caller-stated label, never a computed
assessment. Work order kinds are the fork's own vocabulary --
preventive and corrective -- and the lifecycle changes only
through recorded actions.
"""

import unittest

from erp.errors import NotFoundError, ValidationError

from erp_helpers import OPERATOR, make_org, make_store


def make_asset(store, org, actor=OPERATOR, ref="ASSET-0001"):
    return store.create_asset(actor, org["id"], ref, "Pump station 4",
                              "High (caller-stated label)")


class AssetTests(unittest.TestCase):
    def test_asset_records_with_caller_labels(self):
        store, _ = make_store()
        org = make_org(store)
        asset = make_asset(store, org)
        self.assertEqual(asset["criticality_label"],
                         "High (caller-stated label)")
        with self.assertRaises(ValidationError):
            make_asset(store, org)
        with self.assertRaises(NotFoundError):
            store.get_asset(OPERATOR, "ast-99")


class WorkOrderTests(unittest.TestCase):
    def setUp(self):
        self.store, _ = make_store()
        self.org = make_org(self.store)
        self.asset = make_asset(self.store, self.org)

    def test_lifecycle_assign_then_complete(self):
        order = self.store.create_work_order(
            OPERATOR, self.org["id"], self.asset["id"], "WO-0001",
            "preventive")
        self.assertEqual(order["status"], "open")
        assigned = self.store.transition_work_order(
            OPERATOR, order["id"], "assign", assignee_ref="TECH-REF-1")
        self.assertEqual(assigned["status"], "assigned")
        self.assertEqual(assigned["assignee_ref"], "TECH-REF-1")
        done = self.store.transition_work_order(
            OPERATOR, order["id"], "complete")
        self.assertEqual(done["status"], "completed")
        with self.assertRaises(ValidationError):
            self.store.transition_work_order(OPERATOR, order["id"],
                                             "complete")
        with self.assertRaises(ValidationError):
            self.store.transition_work_order(
                OPERATOR, order["id"], "assign", assignee_ref="TECH-REF-2")

    def test_open_can_complete_directly(self):
        order = self.store.create_work_order(
            OPERATOR, self.org["id"], self.asset["id"], "WO-0002",
            "corrective")
        done = self.store.transition_work_order(
            OPERATOR, order["id"], "complete")
        self.assertEqual(done["status"], "completed")

    def test_kind_vocabulary_is_the_forks_own(self):
        with self.assertRaises(ValidationError):
            self.store.create_work_order(
                OPERATOR, self.org["id"], self.asset["id"], "WO-X",
                "emergency")

    def test_asset_must_belong_to_the_org(self):
        from erp_helpers import ADMIN
        other = self.store.create_organization(ADMIN, "ORG-2", "Second org")
        with self.assertRaises(ValidationError):
            self.store.create_work_order(
                OPERATOR, other["id"], self.asset["id"], "WO-9",
                "preventive")


if __name__ == "__main__":
    unittest.main()
