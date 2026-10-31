"""Individual development plan (IDP) tests.

Traces to: Core function 5 (Development plans) --
create_development_plan (``idp-``) with a goal, an optional target
date, and activities; each activity is a dict with a non-empty
"activity" text and an optional existing "course_id". Activities are
deep-copied at creation. plan_write is an instructor write; learner
scope applies (Core function 12).
"""

import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError


class TestDevelopmentPlans(unittest.TestCase):
    """Core 5: individual development plan records."""

    def test_create_plan_shape(self):
        """Core 5: creation returns an idp- record with learner_ref/goal/target_date/activities and provenance."""
        store, _, course = make_store()
        plan = store.create_development_plan(
            "carol", "Become safety lead", INSTRUCTOR,
            target_date="2026-12-31",
            activities=[{"activity": "Take Safety Basics", "course_id": course["id"]},
                        {"activity": "Shadow an audit"}],
        )
        self.assertEqual(plan["id"], "idp-1")
        self.assertEqual(plan["learner_ref"], "carol")
        self.assertEqual(plan["goal"], "Become safety lead")
        self.assertEqual(plan["target_date"], "2026-12-31")
        self.assertEqual(plan["activities"][0]["course_id"], course["id"])
        self.assertEqual(plan["activities"][1]["activity"], "Shadow an audit")
        self.assertEqual(plan["created_by"], "bob")
        bare = store.create_development_plan("carol", "Grow", INSTRUCTOR)
        self.assertIsNone(bare["target_date"])
        self.assertEqual(bare["activities"], [])

    def test_activities_deep_copied(self):
        """Core 5: activities are deep-copied at creation -- mutating the caller's list or its dicts afterwards does not change the stored plan."""
        store, _, course = make_store()
        activities = [{"activity": "Take Safety Basics", "course_id": course["id"]}]
        plan = store.create_development_plan("carol", "Grow", INSTRUCTOR,
                                             activities=activities)
        activities[0]["activity"] = "Tampered"
        activities.append({"activity": "Sneaked In"})
        stored = store.get_development_plan(plan["id"], ADMIN)
        self.assertEqual(len(stored["activities"]), 1)
        self.assertEqual(stored["activities"][0]["activity"], "Take Safety Basics")
        # Mutating a returned record's activities must not leak either.
        stored["activities"][0]["activity"] = "Tampered Again"
        reread = store.get_development_plan(plan["id"], ADMIN)
        self.assertEqual(reread["activities"][0]["activity"], "Take Safety Basics")

    def test_activity_validation(self):
        """Core 5: an activity missing its 'activity' text, or with empty text, -> ValidationError; an activity naming an unknown course_id -> NotFoundError; failed creates consume no id."""
        store, _, course = make_store()
        for bad in ([{}], [{"activity": ""}], [{"activity": "  "}],
                    [{"course_id": course["id"]}], ["not-a-dict"]):
            with self.subTest(activities=bad):
                with self.assertRaises(ValidationError):
                    store.create_development_plan("carol", "Grow", INSTRUCTOR,
                                                  activities=bad)
        with self.assertRaises(NotFoundError):
            store.create_development_plan(
                "carol", "Grow", INSTRUCTOR,
                activities=[{"activity": "Ghost course", "course_id": "crs-999"}],
            )
        plan = store.create_development_plan("carol", "Grow", INSTRUCTOR)
        self.assertEqual(plan["id"], "idp-1")

    def test_target_date_and_goal_validation(self):
        """Core 5: a malformed target_date -> ValidationError; an empty goal -> ValidationError."""
        store, _, _ = make_store()
        for bad_date in ("June 1", "2026-13-01", "2026-02-30", "31-12-2026"):
            with self.subTest(target_date=bad_date):
                with self.assertRaises(ValidationError):
                    store.create_development_plan("carol", "Grow", INSTRUCTOR,
                                                  target_date=bad_date)
        with self.assertRaises(ValidationError):
            store.create_development_plan("carol", "", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.get_development_plan("idp-999", ADMIN)

    def test_learner_scope_and_permissions(self):
        """Core 5 / Core 12: plan_write is an instructor write -- a learner may not create plans; a learner reads her own plan, is denied another's, and lists only her own."""
        store, _, _ = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.create_development_plan("carol", "Grow", LEARNER)
        own = store.create_development_plan("carol", "Mine", INSTRUCTOR)
        other = store.create_development_plan("erin", "Theirs", INSTRUCTOR)
        self.assertEqual(store.get_development_plan(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_development_plan(other["id"], LEARNER)
        self.assertEqual([p["id"] for p in store.list_development_plans(LEARNER)],
                         [own["id"]])
        self.assertEqual(
            len(store.list_development_plans(ADMIN, learner_ref="erin")), 1
        )


if __name__ == "__main__":
    unittest.main()
