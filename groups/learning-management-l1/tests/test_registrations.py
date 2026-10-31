"""Event & registration tests.

Traces to: Core function 3 (Events & registrations) -- events
(``evt-``) for live/virtual sessions with optional positive-int
capacity, and registrations (``reg-``) whose initial state is
"waitlisted" once capacity is reached, else "registered".
get_event returns a VIEW with derived seats_taken / waitlist_count /
seats_open; the stored record carries no such keys. Learner scope
applies under Core function 13.
"""

import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER, fresh_store, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError

STARTS = "2026-07-01T09:00:00Z"
ENDS = "2026-07-01T10:00:00Z"


def _event(store, course, capacity=None, title="Safety Briefing"):
    return store.create_event(title, STARTS, INSTRUCTOR, course_id=course["id"],
                              ends_at=ENDS, capacity=capacity)


class TestEvents(unittest.TestCase):
    """Core 3: event records and validation."""

    def test_create_event_shape(self):
        """Core 3: creation returns an evt- record with kind/course/capacity/location and provenance, and no derived seat keys."""
        store, _, course = make_store()
        event = store.create_event("Briefing", STARTS, INSTRUCTOR, course_id=course["id"],
                                   ends_at=ENDS, kind="virtual", capacity=10,
                                   location="Room 4")
        self.assertEqual(event["id"], "evt-1")
        self.assertEqual(event["kind"], "virtual")
        self.assertEqual(event["course_id"], course["id"])
        self.assertEqual(event["capacity"], 10)
        self.assertEqual(event["location"], "Room 4")
        self.assertEqual(event["starts_at"], STARTS)
        self.assertEqual(event["ends_at"], ENDS)
        self.assertEqual(event["created_by"], "bob")
        for derived in ("seats_taken", "waitlist_count", "seats_open"):
            self.assertNotIn(derived, event)
        defaults = store.create_event("Plain", STARTS, INSTRUCTOR)
        self.assertEqual(defaults["kind"], "live")
        self.assertIsNone(defaults["capacity"])
        self.assertIsNone(defaults["course_id"])

    def test_event_validation(self):
        """Core 3: bad kind, ends_at before starts_at, malformed starts_at, and capacity 0/negative/bool/float/string all -> ValidationError; failed creates consume no id."""
        store, _, course = make_store()
        with self.assertRaises(ValidationError):
            store.create_event("Bad Kind", STARTS, INSTRUCTOR, kind="hybrid")
        with self.assertRaises(ValidationError):
            store.create_event("Backwards", STARTS, INSTRUCTOR, ends_at="2026-07-01T08:00:00Z")
        with self.assertRaises(ValidationError):
            store.create_event("No Date", "next Tuesday", INSTRUCTOR)
        for bad_capacity in (0, -3, True, False, 1.5, "2"):
            with self.subTest(capacity=bad_capacity):
                with self.assertRaises(ValidationError):
                    store.create_event("Bad Cap", STARTS, INSTRUCTOR, capacity=bad_capacity)
        with self.assertRaises(ValidationError):
            store.create_event("", STARTS, INSTRUCTOR)
        event = store.create_event("Ok", STARTS, INSTRUCTOR, course_id=course["id"])
        self.assertEqual(event["id"], "evt-1")

    def test_unknown_course_and_event(self):
        """Core 3: binding an event to an unknown course -> NotFoundError; unknown event id -> NotFoundError."""
        store, _, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.create_event("Ghost", STARTS, INSTRUCTOR, course_id="crs-999")
        with self.assertRaises(NotFoundError):
            store.get_event("evt-999", ADMIN)

    def test_event_write_is_registration_write(self):
        """Core 3 / Core 13: events are created under registration_write -- instructor and admin may, learner and auditor may not."""
        store, _, course = make_store()
        for actor in (LEARNER,):
            with self.assertRaises(PermissionDenied):
                store.create_event("Nope", STARTS, actor, course_id=course["id"])
        self.assertEqual(store.list_events(ADMIN), [])


class TestEventView(unittest.TestCase):
    """Core 3: the derived seats view on get_event / list_events."""

    def test_derived_view_changes_with_registrations(self):
        """Core 3: the get_event view derives seats_taken/waitlist_count/seats_open from live registrations while the event's own fields stay fixed; the create-returned (stored) record has no derived keys."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        store.create_learner("frank", "Frank Learner", ADMIN)
        created = _event(store, course, capacity=2)
        self.assertNotIn("seats_taken", created)

        view = store.get_event(created["id"], ADMIN)
        self.assertEqual(view["seats_taken"], 0)
        self.assertEqual(view["waitlist_count"], 0)
        self.assertEqual(view["seats_open"], 2)

        store.register_learner(created["id"], "carol", INSTRUCTOR)
        view = store.get_event(created["id"], ADMIN)
        self.assertEqual(view["seats_taken"], 1)
        self.assertEqual(view["seats_open"], 1)

        store.register_learner(created["id"], "erin", INSTRUCTOR)
        store.register_learner(created["id"], "frank", INSTRUCTOR)
        view = store.get_event(created["id"], ADMIN)
        self.assertEqual(view["seats_taken"], 2)
        self.assertEqual(view["waitlist_count"], 1)
        self.assertEqual(view["seats_open"], 0)
        # Same event, unchanged identity fields across views.
        self.assertEqual(view["id"], created["id"])
        self.assertEqual(view["title"], created["title"])
        listed = store.list_events(ADMIN)
        self.assertEqual(listed[0]["seats_taken"], 2)

    def test_unlimited_capacity_seats_open_none(self):
        """Core 3: with capacity None the view reports seats_open None while counts still derive."""
        store, _, course = make_store()
        event = _event(store, course, capacity=None)
        store.register_learner(event["id"], "carol", INSTRUCTOR)
        view = store.get_event(event["id"], ADMIN)
        self.assertEqual(view["seats_taken"], 1)
        self.assertEqual(view["waitlist_count"], 0)
        self.assertIsNone(view["seats_open"])


class TestRegistrations(unittest.TestCase):
    """Core 3: registration records, capacity and waitlist behaviour."""

    def test_register_shape_and_initial_state(self):
        """Core 3: registering returns a reg- record in state 'registered' when seats are open."""
        store, _, course = make_store()
        event = _event(store, course)
        reg = store.register_learner(event["id"], "carol", INSTRUCTOR)
        self.assertEqual(reg["id"], "reg-1")
        self.assertEqual(reg["event_id"], event["id"])
        self.assertEqual(reg["learner_ref"], "carol")
        self.assertEqual(reg["state"], "registered")
        self.assertEqual(reg["created_by"], "bob")

    def test_capacity_waitlist_and_promotion(self):
        """Core 3: capacity=1 -> first registration is 'registered', second is 'waitlisted'; promoting the waitlisted one at capacity -> ValidationError; after cancelling the first, promotion succeeds."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        event = _event(store, course, capacity=1)
        first = store.register_learner(event["id"], "carol", INSTRUCTOR)
        second = store.register_learner(event["id"], "erin", INSTRUCTOR)
        self.assertEqual(first["state"], "registered")
        self.assertEqual(second["state"], "waitlisted")
        with self.assertRaises(ValidationError):
            store.set_registration_state(second["id"], "registered", INSTRUCTOR)
        cancelled = store.set_registration_state(first["id"], "cancelled", INSTRUCTOR)
        self.assertEqual(cancelled["state"], "cancelled")
        promoted = store.set_registration_state(second["id"], "registered", INSTRUCTOR)
        self.assertEqual(promoted["state"], "registered")
        attended = store.set_registration_state(second["id"], "attended", INSTRUCTOR)
        self.assertEqual(attended["state"], "attended")

    def test_duplicate_active_rejected_no_id_consumed(self):
        """Core 3: a duplicate active (registered|waitlisted) registration for the same learner+event -> ValidationError and consumes no id; after cancellation the learner may register again."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        event = _event(store, course, capacity=1)
        first = store.register_learner(event["id"], "carol", INSTRUCTOR)
        store.register_learner(event["id"], "erin", INSTRUCTOR)  # waitlisted (active)
        with self.assertRaises(ValidationError):
            store.register_learner(event["id"], "carol", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.register_learner(event["id"], "erin", INSTRUCTOR)
        store.set_registration_state(first["id"], "cancelled", INSTRUCTOR)
        again = store.register_learner(event["id"], "carol", INSTRUCTOR)
        self.assertEqual(again["id"], "reg-3")
        # The cancelled seat is open again (a waitlist entry holds no
        # seat), so the re-registration starts as "registered".
        self.assertEqual(again["state"], "registered")

    def test_unknown_learner_or_event(self):
        """Core 3: registering a learner_ref with no learner record -> NotFoundError; an unknown event -> NotFoundError."""
        store, _, course = make_store()
        event = _event(store, course)
        with self.assertRaises(NotFoundError):
            store.register_learner(event["id"], "ghost", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.register_learner("evt-999", "carol", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.get_registration("reg-999", ADMIN)

    def test_set_state_validation(self):
        """Core 3: a state outside registered|waitlisted|cancelled|attended -> ValidationError; unknown registration -> NotFoundError."""
        store, _, course = make_store()
        event = _event(store, course)
        reg = store.register_learner(event["id"], "carol", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.set_registration_state(reg["id"], "maybe", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.set_registration_state("reg-999", "cancelled", INSTRUCTOR)
        self.assertEqual(store.get_registration(reg["id"], ADMIN)["state"], "registered")

    def test_learner_scope_and_write_denied(self):
        """Core 3 / Core 13: a learner may not register anyone; a learner reads her own registration, is denied another's, and lists only her own."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        event = _event(store, course)
        with self.assertRaises(PermissionDenied):
            store.register_learner(event["id"], "carol", LEARNER)
        own = store.register_learner(event["id"], "carol", INSTRUCTOR)
        other = store.register_learner(event["id"], "erin", INSTRUCTOR)
        self.assertEqual(store.get_registration(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_registration(other["id"], LEARNER)
        with self.assertRaises(PermissionDenied):
            store.list_registrations(LEARNER, learner_ref="erin")
        self.assertEqual([r["id"] for r in store.list_registrations(LEARNER)], [own["id"]])

    def test_list_filters(self):
        """Core 3: list_registrations filters by event_id and learner_ref for staff roles."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        event = _event(store, course)
        other_event = _event(store, course, title="Second Briefing")
        store.register_learner(event["id"], "carol", INSTRUCTOR)
        store.register_learner(event["id"], "erin", INSTRUCTOR)
        store.register_learner(other_event["id"], "carol", INSTRUCTOR)
        self.assertEqual(len(store.list_registrations(ADMIN, event_id=event["id"])), 2)
        self.assertEqual(len(store.list_registrations(ADMIN, learner_ref="carol")), 2)
        self.assertEqual(len(store.list_registrations(ADMIN)), 3)


if __name__ == "__main__":
    unittest.main()
