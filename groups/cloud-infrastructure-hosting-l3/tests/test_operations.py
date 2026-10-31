"""Operations side: operations tasks (derived overdue), cloud
accounts, utilization records (integer units, never money), and
recommendation records (Core functions 11, 12, 13)."""

import unittest

import cloudinfra_helpers as H
from cloudinfra.errors import ValidationError


class _OrgCase(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()
        self.org = H.make_org(self.store)
        self.oid = self.org["id"]


class TestOperationsTasks(_OrgCase):
    def _task(self, ref="ops-1", due="2026-01-15", kind="patching"):
        return self.store.create_operations_task(
            self.oid, ref, kind, "env-1", "Monthly OS patching", due, H.MEMBER)

    def test_create_task_defaults_open_not_overdue(self):
        task = self._task(due="2999-01-15")
        self.assertEqual(task["status"], "open")
        self.assertFalse(task["overdue"])
        # overdue is derived, never stored.
        self.assertNotIn("overdue", self.store._operations_tasks[task["id"]])

    def test_overdue_derived_at_read(self):
        task = self._task()
        view = self.store.get_operations_task(
            self.oid, task["id"], H.MEMBER, at="2026-01-14")
        self.assertFalse(view["overdue"])
        view = self.store.get_operations_task(
            self.oid, task["id"], H.MEMBER, at="2026-01-16")
        self.assertTrue(view["overdue"])

    def test_completed_task_never_overdue(self):
        task = self._task()
        self.store.set_operations_task_status(
            self.oid, task["id"], "completed", H.MEMBER)
        view = self.store.get_operations_task(
            self.oid, task["id"], H.MEMBER, at="2027-01-01")
        self.assertFalse(view["overdue"])

    def test_task_lifecycle_terminal_states(self):
        task = self._task()
        done = self.store.set_operations_task_status(
            self.oid, task["id"], "completed", H.MEMBER)
        self.assertEqual(done["status"], "completed")
        with self.assertRaises(ValidationError):
            self.store.set_operations_task_status(
                self.oid, task["id"], "cancelled", H.MEMBER)
        other = self._task(ref="ops-2")
        cancelled = self.store.set_operations_task_status(
            self.oid, other["id"], "cancelled", H.MEMBER)
        self.assertEqual(cancelled["status"], "cancelled")

    def test_task_kind_and_due_at_validated(self):
        with self.assertRaises(ValidationError):
            self._task(kind="reboot")
        with self.assertRaises(ValidationError):
            self._task(due="next tuesday")

    def test_each_operations_kind(self):
        for i, kind in enumerate(("patching", "vulnerability_scanning",
                                  "configuration_management", "support")):
            task = self._task(ref="ops-k%d" % i, kind=kind)
            self.assertEqual(task["kind"], kind)


class TestAccountsAndUtilization(_OrgCase):
    def _account(self, ref="acc-agency-1"):
        return self.store.open_account(self.oid, ref, "Agency account", H.MEMBER)

    def test_account_lifecycle(self):
        account = self._account()
        self.assertEqual(account["status"], "open")
        closed = self.store.close_account(self.oid, account["id"], H.MEMBER)
        self.assertEqual(closed["status"], "closed")
        with self.assertRaises(ValidationError):
            self.store.close_account(self.oid, account["id"], H.MEMBER)

    def test_utilization_recorded_in_integer_units(self):
        account = self._account()
        record = self.store.record_utilization(
            self.oid, account["id"], "2026-09", 1250, H.MEMBER)
        self.assertEqual(record["units"], 1250)
        self.assertEqual(record["period"], "2026-09")

    def test_utilization_rejects_non_integer_units(self):
        account = self._account()
        for bad in (12.5, True, "1250", -1, None):
            with self.assertRaises(ValidationError):
                self.store.record_utilization(
                    self.oid, account["id"], "2026-09", bad, H.MEMBER)

    def test_utilization_period_format_validated(self):
        account = self._account()
        for bad in ("2026-13", "2026-1", "Sep 2026", 202609):
            with self.assertRaises(ValidationError):
                self.store.record_utilization(
                    self.oid, account["id"], bad, 10, H.MEMBER)

    def test_utilization_one_record_per_account_period(self):
        account = self._account()
        self.store.record_utilization(
            self.oid, account["id"], "2026-09", 10, H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.record_utilization(
                self.oid, account["id"], "2026-09", 20, H.MEMBER)
        # A different period or a different account is fine.
        self.store.record_utilization(
            self.oid, account["id"], "2026-10", 20, H.MEMBER)
        other = self._account(ref="acc-agency-2")
        self.store.record_utilization(
            self.oid, other["id"], "2026-09", 30, H.MEMBER)

    def test_utilization_on_closed_account_rejected(self):
        account = self._account()
        self.store.close_account(self.oid, account["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.record_utilization(
                self.oid, account["id"], "2026-09", 10, H.MEMBER)

    def test_list_utilization_filter(self):
        first = self._account()
        second = self._account(ref="acc-agency-2")
        self.store.record_utilization(self.oid, first["id"], "2026-09", 1, H.MEMBER)
        self.store.record_utilization(self.oid, second["id"], "2026-09", 2, H.MEMBER)
        self.assertEqual(len(self.store.list_utilization(self.oid, H.MEMBER)), 2)
        only = self.store.list_utilization(
            self.oid, H.MEMBER, account_id=first["id"])
        self.assertEqual(len(only), 1)
        self.assertEqual(only[0]["units"], 1)


class TestRecommendations(_OrgCase):
    def test_record_recommendation_kinds(self):
        for kind in ("resource_optimization", "ai_recommendation"):
            rec = self.store.record_recommendation(
                self.oid, "rec-%s" % kind, kind, "dep-1", kind, H.MEMBER,
                detail="shift workload to the warm tier")
            self.assertEqual(rec["kind"], kind)
            self.assertEqual(rec["detail"], "shift workload to the warm tier")

    def test_recommendation_detail_optional(self):
        rec = self.store.record_recommendation(
            self.oid, "rec-1", "resource_optimization", "dep-1", "R", H.MEMBER)
        self.assertIsNone(rec["detail"])

    def test_recommendation_invalid_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.record_recommendation(
                self.oid, "rec-x", "upsell", "dep-1", "X", H.MEMBER)


if __name__ == "__main__":
    unittest.main()
