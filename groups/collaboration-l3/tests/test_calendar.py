"""Calendaring & scheduling tests.

Traces to: UNION-SPEC Core function 4 (Calendaring & scheduling —
workspace events with title, start and end (ISO-8601), location, and
attendees; member attendees are notified of the invite) / ranking row
19 (Calendaring & scheduling, 3 siblings); Implementation contract for
``collab/store.py`` event methods; control families AC-3 (membership
boundary) and SI-10 (malformed input rejected, never partially
applied).
"""

import unittest

from collab_helpers import (
    ADMIN,
    EVENT_END,
    EVENT_START,
    MEMBER,
    OUTSIDER,
    VIEWER,
    create_sample_event,
    fresh_store,
    make_store,
)
from collab.errors import PermissionDenied, ValidationError

EVENT_KEYS = {
    "id", "workspace_id", "title", "start", "end", "location",
    "attendees", "created_by", "created_utc",
}


class TestCreateEvent(unittest.TestCase):
    """Core: Calendaring — creation shape and stored fields."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_create_event_returns_the_contract_dict(self):
        """Core: Calendaring. Contract: create_event returns {id,
        workspace_id, title, start, end, location, attendees,
        created_by, created_utc} with an evt- id."""
        event = create_sample_event(
            self.store, self.ws_id, title="Team sync",
            attendees=["carol"], location="Room 4",
        )
        self.assertEqual(set(event.keys()), EVENT_KEYS)
        self.assertEqual(event["id"], "evt-1")
        self.assertEqual(event["workspace_id"], self.ws_id)
        self.assertEqual(event["title"], "Team sync")
        self.assertEqual(event["start"], EVENT_START)
        self.assertEqual(event["end"], EVENT_END)
        self.assertEqual(event["location"], "Room 4")
        self.assertEqual(event["attendees"], ["carol"])
        self.assertEqual(event["created_by"], "bob")

    def test_location_defaults_to_empty_string(self):
        """Core: Calendaring. Contract: location defaults to ""."""
        event = create_sample_event(self.store, self.ws_id)
        self.assertEqual(event["location"], "")

    def test_event_ids_are_sequential(self):
        """Core: Calendaring. Event ids increment evt-1, evt-2."""
        first = create_sample_event(self.store, self.ws_id, title="one")
        second = create_sample_event(self.store, self.ws_id, title="two")
        self.assertEqual([first["id"], second["id"]], ["evt-1", "evt-2"])

    def test_list_events_returns_created_events(self):
        """Core: Calendaring. list_events returns the workspace's
        events for a member (read)."""
        create_sample_event(self.store, self.ws_id, title="one")
        create_sample_event(self.store, self.ws_id, title="two")
        titles = [e["title"] for e in self.store.list_events(self.ws_id, VIEWER)]
        self.assertEqual(titles, ["one", "two"])


class TestEventValidation(unittest.TestCase):
    """Core: Calendaring (SI-10) — time-window validation."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_end_equal_to_start_is_validation_error(self):
        """Core: Calendaring. Contract: 'end must be after start, else
        ValidationError' — an empty window is rejected."""
        with self.assertRaises(ValidationError):
            create_sample_event(
                self.store, self.ws_id, start=EVENT_START, end=EVENT_START
            )

    def test_end_before_start_is_validation_error(self):
        """Core: Calendaring. A backwards window is rejected."""
        with self.assertRaises(ValidationError):
            create_sample_event(
                self.store, self.ws_id, start=EVENT_END, end=EVENT_START
            )

    def test_malformed_start_is_validation_error(self):
        """Core: Calendaring. Contract: start 'must parse as ISO-8601
        datetimes ... else ValidationError'."""
        with self.assertRaises(ValidationError):
            create_sample_event(
                self.store, self.ws_id, start="not-a-date", end=EVENT_END
            )

    def test_malformed_end_is_validation_error(self):
        """Core: Calendaring. A malformed end is rejected the same
        way."""
        with self.assertRaises(ValidationError):
            create_sample_event(
                self.store, self.ws_id, start=EVENT_START,
                end="2026-13-99T99:99:99",
            )

    def test_failed_events_consume_no_id_and_store_nothing(self):
        """Core: Calendaring (SI-10). Rejected events are never
        partially applied: nothing is listed and the next valid event
        is still evt-1."""
        store = fresh_store()
        ws = store.create_workspace("solo", MEMBER)
        for start, end in (
            (EVENT_START, EVENT_START),
            ("junk", EVENT_END),
            (EVENT_START, "junk"),
        ):
            with self.assertRaises(ValidationError):
                store.create_event(ws["id"], "bad", start, end, [], MEMBER)
        self.assertEqual(store.list_events(ws["id"], MEMBER), [])
        event = store.create_event(
            ws["id"], "good", EVENT_START, EVENT_END, [], MEMBER
        )
        self.assertEqual(event["id"], "evt-1")


class TestEventAccessAndNotifications(unittest.TestCase):
    """Core: Calendaring — access boundary and invite notifications."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_member_attendees_get_an_event_invite_notification(self):
        """Core: Calendaring. Contract: 'attendees who are workspace
        members (other than the creator) get a notification (kind
        event_invite, ref_id = the event id)'."""
        event = create_sample_event(
            self.store, self.ws_id, attendees=["carol"]
        )
        notes = self.store.notifications_for("carol")
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["kind"], "event_invite")
        self.assertEqual(notes[0]["ref_id"], event["id"])
        self.assertEqual(notes[0]["workspace_id"], self.ws_id)

    def test_non_member_attendees_are_not_notified(self):
        """Core: Calendaring. An attendee who is not a workspace
        member (dave) gets no invite notification."""
        create_sample_event(self.store, self.ws_id, attendees=["dave"])
        self.assertEqual(self.store.notifications_for("dave"), [])

    def test_creator_listed_as_attendee_is_not_notified(self):
        """Core: Calendaring. The creator is excluded from invite
        notifications even when listed as an attendee."""
        create_sample_event(
            self.store, self.ws_id, attendees=["bob", "carol"]
        )
        self.assertEqual(self.store.notifications_for("bob"), [])
        self.assertEqual(len(self.store.notifications_for("carol")), 1)

    def test_event_with_no_attendees_notifies_nobody(self):
        """Core: Calendaring. An attendee-less event is silent."""
        create_sample_event(self.store, self.ws_id, attendees=[])
        self.assertEqual(self.store.notifications_for("carol"), [])

    def test_non_member_cannot_create_or_list_events(self):
        """Core: Calendaring (AC-3). Membership is enforced on events."""
        with self.assertRaises(PermissionDenied):
            create_sample_event(self.store, self.ws_id, actor=OUTSIDER)
        with self.assertRaises(PermissionDenied):
            self.store.list_events(self.ws_id, OUTSIDER)

    def test_viewer_member_can_list_but_cannot_schedule(self):
        """Core: Calendaring + Access control. Viewer holds read, not
        schedule."""
        create_sample_event(self.store, self.ws_id)
        self.assertEqual(len(self.store.list_events(self.ws_id, VIEWER)), 1)
        with self.assertRaises(PermissionDenied):
            create_sample_event(self.store, self.ws_id, actor=VIEWER)

    def test_platform_admin_may_create_and_list_events(self):
        """Core: Calendaring + Access control. The platform admin role
        satisfies the membership rule for events."""
        event = create_sample_event(self.store, self.ws_id, actor=ADMIN)
        listed = self.store.list_events(self.ws_id, ADMIN)
        self.assertEqual([e["id"] for e in listed], [event["id"]])


if __name__ == "__main__":
    unittest.main()
