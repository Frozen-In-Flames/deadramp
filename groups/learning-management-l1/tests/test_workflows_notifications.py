"""Workflow & notification record tests.

Traces to: Core function 10 (Workflows & notifications) --
create_workflow (``wfl-``) records a named, non-empty list of
non-empty step strings, and registering a workflow NEVER executes
it: it changes no other record. Notifications (``ntf-``) are plain
records. workflow_write is an instructor write (Core function 13).
"""

import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError


class TestWorkflows(unittest.TestCase):
    """Core 10: workflow records (registration only, never execution)."""

    def test_create_workflow_shape(self):
        """Core 10: creation returns a wfl- record with name/steps/scope and provenance; steps are held as given."""
        store, _, _ = make_store()
        workflow = store.create_workflow(
            "Onboarding", ["create account", "assign safety course"], INSTRUCTOR,
            scope="new hires",
        )
        self.assertEqual(workflow["id"], "wfl-1")
        self.assertEqual(workflow["name"], "Onboarding")
        self.assertEqual(workflow["steps"],
                         ["create account", "assign safety course"])
        self.assertEqual(workflow["scope"], "new hires")
        self.assertEqual(workflow["created_by"], "bob")
        bare = store.create_workflow("Bare", ["only step"], INSTRUCTOR)
        self.assertEqual(bare["scope"], "")
        self.assertEqual(store.get_workflow(workflow["id"], ADMIN)["name"], "Onboarding")
        self.assertEqual(len(store.list_workflows(ADMIN)), 2)

    def test_workflow_validation(self):
        """Core 10: empty steps list, an empty/blank step string, a non-list steps value, or an empty name -> ValidationError; no id consumed."""
        store, _, _ = make_store()
        for bad_steps in ([], [""], ["  "], ["ok", ""], "not-a-list", None):
            with self.subTest(steps=bad_steps):
                with self.assertRaises(ValidationError):
                    store.create_workflow("Bad", bad_steps, INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.create_workflow("", ["step"], INSTRUCTOR)
        workflow = store.create_workflow("Good", ["step"], INSTRUCTOR)
        self.assertEqual(workflow["id"], "wfl-1")
        with self.assertRaises(NotFoundError):
            store.get_workflow("wfl-999", ADMIN)

    def test_workflow_never_executes(self):
        """Core 10 (never-executes pin): creating a workflow whose steps name a registration, an authorization decision and a notification changes NO other record -- registration/authorization/notification counts and states are exactly as before."""
        store, _, course = make_store()
        event = store.create_event("Briefing", "2026-07-01T09:00:00Z", INSTRUCTOR,
                                   course_id=course["id"])
        auth = store.create_authorization("carol", "Attend Briefing", INSTRUCTOR,
                                          event_id=event["id"])
        before_registrations = store.list_registrations(ADMIN)
        before_notifications = store.list_notifications(ADMIN)
        before_auth_state = store.get_authorization(auth["id"], ADMIN)["state"]

        workflow = store.create_workflow(
            "Briefing Flow",
            ["register carol for event %s" % event["id"],
             "approve authorization %s" % auth["id"],
             "notify carol about the briefing"],
            INSTRUCTOR,
        )
        self.assertEqual(workflow["id"], "wfl-1")
        self.assertEqual(store.list_registrations(ADMIN), before_registrations)
        self.assertEqual(store.list_notifications(ADMIN), before_notifications)
        self.assertEqual(store.get_authorization(auth["id"], ADMIN)["state"],
                         before_auth_state)
        self.assertEqual(before_auth_state, "requested")
        view = store.get_event(event["id"], ADMIN)
        self.assertEqual(view["seats_taken"], 0)
        self.assertEqual(view["waitlist_count"], 0)

    def test_workflow_permissions(self):
        """Core 10 / Core 13: workflow_write is an instructor write -- a learner may not create workflows."""
        store, _, _ = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_workflow("Nope", ["step"], LEARNER)
        self.assertEqual(store.list_workflows(ADMIN), [])


class TestNotifications(unittest.TestCase):
    """Core 10: notification records."""

    def test_record_notification_shape(self):
        """Core 10: recording returns an ntf- record with recipient_ref/subject/body/kind and provenance; defaults are body '' and kind 'general'."""
        store, _, _ = make_store()
        note = store.record_notification("carol", "Briefing tomorrow", INSTRUCTOR,
                                         body="Room 4, 9am", kind="reminder")
        self.assertEqual(note["id"], "ntf-1")
        self.assertEqual(note["recipient_ref"], "carol")
        self.assertEqual(note["subject"], "Briefing tomorrow")
        self.assertEqual(note["body"], "Room 4, 9am")
        self.assertEqual(note["kind"], "reminder")
        self.assertEqual(note["recorded_by"], "bob")
        bare = store.record_notification("erin", "Hello", INSTRUCTOR)
        self.assertEqual(bare["body"], "")
        self.assertEqual(bare["kind"], "general")
        self.assertEqual(store.get_notification(note["id"], ADMIN)["subject"],
                         "Briefing tomorrow")
        with self.assertRaises(NotFoundError):
            store.get_notification("ntf-999", ADMIN)

    def test_notification_validation_and_filter(self):
        """Core 10: an empty recipient_ref or subject -> ValidationError; list filters by recipient_ref; a learner may not record notifications."""
        store, _, _ = make_store()
        with self.assertRaises(ValidationError):
            store.record_notification("", "Subject", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.record_notification("carol", "", INSTRUCTOR)
        with self.assertRaises(PermissionDenied):
            store.record_notification("carol", "Subject", LEARNER)
        store.record_notification("carol", "One", INSTRUCTOR)
        store.record_notification("erin", "Two", INSTRUCTOR)
        store.record_notification("carol", "Three", INSTRUCTOR)
        self.assertEqual(
            len(store.list_notifications(ADMIN, recipient_ref="carol")), 2
        )
        self.assertEqual(len(store.list_notifications(ADMIN)), 3)


if __name__ == "__main__":
    unittest.main()
