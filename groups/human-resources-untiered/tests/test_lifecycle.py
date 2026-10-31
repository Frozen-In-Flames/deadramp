"""Lifecycle case & derived-status tests.

Traces to: Core function 6 (Employee lifecycle cases -- onboarding /
separation task checklists with status derived deterministically at
read time from tasks + cancelled flag; AU-6, CA-7, CM-6). Status is
derived at read time -- never stored on the case record itself.
"""

import unittest

from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


class TestLifecycle(unittest.TestCase):
    """Core 6: lifecycle cases and deterministic status derivation."""

    def _setup(self, titles=("Badge", "Laptop")):
        store, _, _ = make_store()
        case = store.create_lifecycle_case("carol", "onboarding", SPECIALIST, task_titles=list(titles))
        return store, case

    def test_create_case_tasks_shape(self):
        """Core 6 (CM-6): a case carries lif- id, kind, sequential t-N pending tasks and cancelled=False; view starts not_started when tasks are pending."""
        _, case = self._setup()
        self.assertEqual(case["id"], "lif-1")
        self.assertEqual(
            case["tasks"],
            [
                {"task_id": "t-1", "title": "Badge", "state": "pending"},
                {"task_id": "t-2", "title": "Laptop", "state": "pending"},
            ],
        )
        self.assertFalse(case["cancelled"])
        self.assertEqual(case["status"], "not_started")
        self.assertFalse(case["complete"])

    def test_empty_case_is_not_started(self):
        """Core 6: a case with no tasks derives not_started."""
        store, _, _ = make_store()
        case = store.create_lifecycle_case("carol", "separation", SPECIALIST)
        view = store.get_lifecycle_case(case["id"], ADMIN)
        self.assertEqual(view["status"], "not_started")
        self.assertFalse(view["complete"])

    def test_status_derivation_progression(self):
        """Core 6: pending -> in_progress (one done) -> complete (all done/waived), derived at each read."""
        store, case = self._setup()
        store.set_task_state(case["id"], "t-1", "done", SPECIALIST)
        view = store.get_lifecycle_case(case["id"], ADMIN)
        self.assertEqual(view["status"], "in_progress")
        self.assertFalse(view["complete"])
        store.set_task_state(case["id"], "t-2", "waived", SPECIALIST)
        view = store.get_lifecycle_case(case["id"], ADMIN)
        self.assertEqual(view["status"], "complete")
        self.assertTrue(view["complete"])

    def test_cancelled_overrides_tasks(self):
        """Core 6: cancel_case records cancelled=True and the derived status reads cancelled even with all tasks done."""
        store, case = self._setup()
        store.set_task_state(case["id"], "t-1", "done", SPECIALIST)
        store.set_task_state(case["id"], "t-2", "done", SPECIALIST)
        cancelled = store.cancel_case(case["id"], SPECIALIST)
        self.assertTrue(cancelled["cancelled"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertFalse(cancelled["complete"])

    def test_add_task_appends_pending(self):
        """Core 6: add_task appends the next sequential t-N task as pending, moving a complete case back to in_progress."""
        store, case = self._setup(titles=("Only",))
        store.set_task_state(case["id"], "t-1", "done", SPECIALIST)
        self.assertEqual(store.get_lifecycle_case(case["id"], ADMIN)["status"], "complete")
        view = store.add_task(case["id"], "Extra", SPECIALIST)
        self.assertEqual(view["tasks"][-1], {"task_id": "t-2", "title": "Extra", "state": "pending"})
        self.assertEqual(view["status"], "in_progress")

    def test_validation_and_permissions(self):
        """Core 6 (SI-10/AC-3): unknown person -> NotFoundError; bad kind/task state -> ValidationError; unknown task -> NotFoundError; employee may not write and reads only own cases."""
        store, _, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.create_lifecycle_case("ghost", "onboarding", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.create_lifecycle_case("carol", "transfer", SPECIALIST)
        with self.assertRaises(PermissionDenied):
            store.create_lifecycle_case("carol", "onboarding", EMPLOYEE)
        store.create_person("erin", ADMIN, kind="employee")
        own = store.create_lifecycle_case("carol", "onboarding", SPECIALIST)
        other = store.create_lifecycle_case("erin", "separation", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.set_task_state(own["id"], "t-1", "skipped", SPECIALIST)
        store.add_task(own["id"], "Task", SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.set_task_state(own["id"], "t-99", "done", SPECIALIST)
        self.assertEqual(store.get_lifecycle_case(own["id"], EMPLOYEE)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_lifecycle_case(other["id"], EMPLOYEE)
        self.assertEqual([c["id"] for c in store.list_lifecycle_cases(EMPLOYEE)], [own["id"]])


if __name__ == "__main__":
    unittest.main()
