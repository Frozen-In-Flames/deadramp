"""Catalog tests: courses, content items, lesson plans.

Traces to: Core function 2 (Catalog) -- courses/programs (``crs-``),
content items (``cnt-``) bound to the fixed content-standard set, and
lesson plans (``les-``) whose item_refs must resolve to a course or a
content item. Lesson plans sit in the catalog family, so creation is
under catalog_write (admin-only); plan_write governs development
plans (Core function 12).
"""

import unittest

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, fresh_store, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError

STANDARDS = (
    "scorm_1_2", "scorm_2004", "aicc", "xapi", "cmi5",
    "mp3", "mp4", "pdf", "other",
)


class TestCourses(unittest.TestCase):
    """Core 2: course/program registry entries."""

    def test_create_course_shape_and_ids(self):
        """Core 2: creation returns a crs- record with kind/code/description and provenance; ids are sequential."""
        store = fresh_store()
        first = store.create_course("Safety Basics", ADMIN, code="SAFE-101",
                                    description="Intro safety")
        second = store.create_course("Safety Program", ADMIN, kind="program")
        self.assertEqual(first["id"], "crs-1")
        self.assertEqual(second["id"], "crs-2")
        self.assertEqual(first["kind"], "course")
        self.assertEqual(second["kind"], "program")
        self.assertEqual(first["code"], "SAFE-101")
        self.assertEqual(first["description"], "Intro safety")
        self.assertIsNone(second["code"])
        self.assertEqual(second["description"], "")
        self.assertEqual(first["created_by"], "alice")
        self.assertIn("created_utc", first)

    def test_get_and_list_sorted(self):
        """Core 2: get returns the record; list is sorted by id; all roles may read."""
        store = fresh_store()
        store.create_course("B Course", ADMIN)
        store.create_course("A Course", ADMIN)
        self.assertEqual([c["id"] for c in store.list_courses(LEARNER)], ["crs-1", "crs-2"])
        self.assertEqual(store.get_course("crs-1", AUDITOR)["title"], "B Course")

    def test_validation(self):
        """Core 2: empty title / bad kind rejected; failed creates consume no id."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_course("", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_course("X", ADMIN, kind="module")
        course = store.create_course("Ok", ADMIN)
        self.assertEqual(course["id"], "crs-1")

    def test_catalog_write_admin_only(self):
        """Core 2 / Core 12: catalog_write is admin-only -- instructor, learner and auditor may not create courses or content items."""
        store = fresh_store()
        for actor in (INSTRUCTOR, LEARNER, AUDITOR):
            with self.subTest(actor=actor.name):
                with self.assertRaises(PermissionDenied):
                    store.create_course("Nope", actor)
                with self.assertRaises(PermissionDenied):
                    store.create_content_item("Nope", "pdf", actor)
        self.assertEqual(store.list_courses(ADMIN), [])
        self.assertEqual(store.list_content_items(ADMIN), [])

    def test_unknown_course_not_found(self):
        """Core 2: unknown course id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_course("crs-999", ADMIN)


class TestContentItems(unittest.TestCase):
    """Core 2: content items and the fixed standard set."""

    def test_each_standard_accepted(self):
        """Core 2: every standard in the contract set (scorm_1_2, scorm_2004, aicc, xapi, cmi5, mp3, mp4, pdf, other) is accepted, with sequential cnt- ids."""
        store, _, _ = make_store()
        for index, standard in enumerate(STANDARDS, start=1):
            item = store.create_content_item("Item %s" % standard, standard, ADMIN)
            self.assertEqual(item["id"], "cnt-%d" % index)
            self.assertEqual(item["standard"], standard)
        self.assertEqual(len(store.list_content_items(ADMIN)), len(STANDARDS))

    def test_bad_standard_rejected_no_id_consumed(self):
        """Core 2: a standard outside the contract set -> ValidationError and consumes no id."""
        store, _, _ = make_store()
        for bad in ("scorm_2004_4th", "zip", "", "SCORM_1_2"):
            with self.subTest(standard=bad):
                with self.assertRaises(ValidationError):
                    store.create_content_item("Bad", bad, ADMIN)
        item = store.create_content_item("Good", "pdf", ADMIN)
        self.assertEqual(item["id"], "cnt-1")

    def test_course_binding_and_unknown_course(self):
        """Core 2: a content item may bind to a course; an unknown course_id -> NotFoundError; list filters by course_id."""
        store, _, course = make_store()
        bound = store.create_content_item("Bound Video", "mp4", ADMIN,
                                          course_id=course["id"])
        unbound = store.create_content_item("Loose PDF", "pdf", ADMIN)
        self.assertEqual(bound["course_id"], course["id"])
        self.assertIsNone(unbound["course_id"])
        with self.assertRaises(NotFoundError):
            store.create_content_item("Ghost", "pdf", ADMIN, course_id="crs-999")
        self.assertEqual(
            [i["id"] for i in store.list_content_items(ADMIN, course_id=course["id"])],
            [bound["id"]],
        )
        self.assertEqual(len(store.list_content_items(ADMIN)), 2)
        with self.assertRaises(NotFoundError):
            store.get_content_item("cnt-999", ADMIN)


class TestLessonPlans(unittest.TestCase):
    """Core 2: lesson plans whose item_refs must resolve."""

    def test_create_lesson_plan_shape(self):
        """Core 2: a lesson plan returns a les- record bound to its course, holding the item_refs that resolve to a course or content item."""
        store, _, course = make_store()
        item = store.create_content_item("Video", "mp4", ADMIN, course_id=course["id"])
        other = store.create_course("Other Course", ADMIN)
        plan = store.create_lesson_plan(
            "Week 1 Plan", course["id"], ADMIN,
            item_refs=[course["id"], item["id"], other["id"]],
        )
        self.assertEqual(plan["id"], "les-1")
        self.assertEqual(plan["course_id"], course["id"])
        self.assertEqual(plan["item_refs"], [course["id"], item["id"], other["id"]])
        self.assertEqual(plan["created_by"], "alice")
        empty = store.create_lesson_plan("Empty Plan", course["id"], ADMIN)
        self.assertEqual(empty["item_refs"], [])

    def test_unknown_ref_or_course_rejected(self):
        """Core 2: an item_ref that resolves to neither a course nor a content item -> NotFoundError; an unknown course_id -> NotFoundError; no id consumed."""
        store, _, course = make_store()
        with self.assertRaises(NotFoundError):
            store.create_lesson_plan("Bad Refs", course["id"], ADMIN,
                                     item_refs=["cnt-999"])
        with self.assertRaises(NotFoundError):
            store.create_lesson_plan("Bad Course", "crs-999", ADMIN)
        plan = store.create_lesson_plan("Good", course["id"], ADMIN)
        self.assertEqual(plan["id"], "les-1")

    def test_list_filter_and_permissions(self):
        """Core 2 / Core 12: list filters by course_id; lesson-plan creation is catalog_write (admin-only), so instructor and learner may not create lesson plans."""
        store, _, course = make_store()
        other = store.create_course("Other Course", ADMIN)
        store.create_lesson_plan("Plan A", course["id"], ADMIN)
        store.create_lesson_plan("Plan B", other["id"], ADMIN)
        self.assertEqual(
            len(store.list_lesson_plans(ADMIN, course_id=course["id"])), 1
        )
        self.assertEqual(len(store.list_lesson_plans(ADMIN)), 2)
        for actor in (INSTRUCTOR, LEARNER):
            with self.subTest(actor=actor.name):
                with self.assertRaises(PermissionDenied):
                    store.create_lesson_plan("Nope", course["id"], actor)
        with self.assertRaises(NotFoundError):
            store.get_lesson_plan("les-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
