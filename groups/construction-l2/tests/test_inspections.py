"""Inspections and punch items tests.

Traces to: Core -- Inspections (insp-, immutable) and Punch items
(pun-) lifecycle with overdue derivation via ``_record_overdue``.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER, make_store
from construct.errors import NotFoundError, ValidationError

NOW = "2025-06-01T00:00:00Z"
PAST = "2020-01-01T00:00:00Z"
FUTURE = "2030-01-01T00:00:00Z"


class TestInspections(unittest.TestCase):
    """Inspections: creation, result validation, immutability."""

    def test_create_shape(self):
        """Inspections. create_inspection makes insp- with all fields."""
        store, project, prime, sub = make_store()
        i = store.create_inspection(OPERATOR, project["id"], "framing",
                                     inspector_ref="INSP-7", occurred_at="2025-05-01T00:00:00Z",
                                     result="pass")
        self.assertEqual(i["id"], "insp-1")
        self.assertEqual(i["result"], "pass")
        self.assertEqual(i["inspector_ref"], "INSP-7")
        self.assertEqual(store.get_inspection(i["id"], VIEWER)["inspection_type"], "framing")

    def test_result_validation(self):
        """Inspections. result must be pass/fail/conditional or None."""
        store, project, prime, sub = make_store()
        for ok in ("pass", "fail", "conditional", None):
            rec = store.create_inspection(OPERATOR, project["id"], "check", result=ok)
            self.assertEqual(rec["result"], ok)
        with self.assertRaises(ValidationError):
            store.create_inspection(OPERATOR, project["id"], "check", result="great")
        with self.assertRaises(ValidationError):
            store.create_inspection(OPERATOR, project["id"], "")
        with self.assertRaises(NotFoundError):
            store.create_inspection(OPERATOR, "prj-99", "check")

    def test_immutable_no_update_api(self):
        """Inspections. The store exposes no update/transition method for inspections."""
        store, project, prime, sub = make_store()
        self.assertFalse(hasattr(store, "update_inspection"))
        self.assertFalse(hasattr(store, "transition_inspection"))
        rec = store.create_inspection(OPERATOR, project["id"], "framing", result="pass")
        rec["result"] = "fail"
        self.assertEqual(store.get_inspection(rec["id"], ADMIN)["result"], "pass")
        self.assertEqual(len(store.list_inspections(VIEWER, project_id=project["id"])), 1)


class TestPunchItems(unittest.TestCase):
    """Punch items: lifecycle, overdue, reopen."""

    def test_create_shape_and_refs(self):
        """Punch. create makes pun- open; inspection/org must exist if given."""
        store, project, prime, sub = make_store()
        insp = store.create_inspection(OPERATOR, project["id"], "framing", result="fail")
        p = store.create_punch_item(OPERATOR, project["id"], "Fix frame",
                                    inspection_id=insp["id"], org_id=prime["id"], due_at=FUTURE)
        self.assertEqual(p["id"], "pun-1")
        self.assertEqual(p["status"], "open")
        self.assertFalse(p["overdue"])
        with self.assertRaises(NotFoundError):
            store.create_punch_item(OPERATOR, project["id"], "X", inspection_id="insp-99")
        with self.assertRaises(NotFoundError):
            store.create_punch_item(OPERATOR, project["id"], "X", org_id="org-99")
        with self.assertRaises(ValidationError):
            store.create_punch_item(OPERATOR, project["id"], "")

    def test_lifecycle_and_reopen(self):
        """Punch. open->corrected->open (reopen)->corrected->verified succeeds; verified terminal."""
        store, project, prime, sub = make_store()
        p = store.create_punch_item(OPERATOR, project["id"], "Fix paint")
        for to in ("corrected", "open", "corrected", "verified"):
            p = store.transition_punch_item(p["id"], OPERATOR, to)
            self.assertEqual(p["status"], to)
        with self.assertRaises(ValidationError):
            store.transition_punch_item(p["id"], OPERATOR, "open")

    def test_invalid_transition(self):
        """Punch. open->verified directly -> ValidationError."""
        store, project, prime, sub = make_store()
        p = store.create_punch_item(OPERATOR, project["id"], "Fix paint")
        with self.assertRaises(ValidationError):
            store.transition_punch_item(p["id"], OPERATOR, "verified")

    def test_overdue_derivation(self):
        """Punch. Past-due open/corrected items are overdue; verified never is."""
        store, project, prime, sub = make_store()
        p = store.create_punch_item(OPERATOR, project["id"], "Late fix", due_at=PAST)
        self.assertTrue(store.get_punch_item(p["id"], VIEWER, now=NOW)["overdue"])
        store.transition_punch_item(p["id"], OPERATOR, "corrected")
        self.assertTrue(store.get_punch_item(p["id"], VIEWER, now=NOW)["overdue"])
        store.transition_punch_item(p["id"], OPERATOR, "verified")
        self.assertFalse(store.get_punch_item(p["id"], VIEWER, now=NOW)["overdue"])
        future = store.create_punch_item(OPERATOR, project["id"], "Future fix", due_at=FUTURE)
        self.assertFalse(store.get_punch_item(future["id"], VIEWER, now=NOW)["overdue"])
        self.assertEqual(len(store.list_punch_items(VIEWER, now=NOW, project_id=project["id"])), 2)


if __name__ == "__main__":
    unittest.main()
