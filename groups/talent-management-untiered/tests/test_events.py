"""Core 6 Recruitment events & Core 7 Event registrations.

Traces to: UNION-SPEC.md Core 6-7 and Yello's recruitment-events
claim — events of the description's own kinds (in_person /
virtual) with guarded lifecycles, and registrations of registered
candidates against scheduled events with a check-in transition.
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.errors import ValidationError


class TestEvents(unittest.TestCase):
    """Core 6: recruitment event records."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        self.event = H.make_event(self.store, self.org)

    def test_event_shape(self):
        """Core 6: the event dict has exactly the contract's
        keys and starts scheduled."""
        self.assertEqual(set(self.event), {
            "id", "org_id", "event_ref", "title", "kind", "starts_at",
            "requisition_id", "label", "status", "created_by",
            "created_utc"})
        self.assertEqual(self.event["status"], "scheduled")
        self.assertEqual(self.event["kind"], "in_person")

    def test_virtual_kind_from_the_description(self):
        """Core 6 (Yello's claim): a virtual event is the other
        kind the description names."""
        virtual = H.make_event(self.store, self.org, event_ref="EVT-V",
                               kind="virtual")
        self.assertEqual(virtual["kind"], "virtual")

    def test_kind_and_starts_at_validation(self):
        """Core 6 / SI-10: an unknown kind, a missing start time,
        and an unparseable start time are each rejected."""
        with self.assertRaises(ValidationError):
            H.make_event(self.store, self.org, event_ref="EVT-B1",
                         kind="webinar")
        with self.assertRaises(ValidationError):
            H.make_event(self.store, self.org, event_ref="EVT-B2",
                         starts_at=None)
        with self.assertRaises(ValidationError):
            H.make_event(self.store, self.org, event_ref="EVT-B3",
                         starts_at="next spring")

    def test_event_lifecycle_guarded(self):
        """Core 6: complete and cancel are one-way transitions
        out of scheduled; a completed event cannot be cancelled."""
        done = self.store.complete_event(self.org["id"], self.event["id"],
                                         H.MEMBER)
        self.assertEqual(done["status"], "completed")
        with self.assertRaises(ValidationError):
            self.store.cancel_event(self.org["id"], self.event["id"],
                                    H.MEMBER)
        other = H.make_event(self.store, self.org, event_ref="EVT-2")
        gone = self.store.cancel_event(self.org["id"], other["id"], H.MEMBER)
        self.assertEqual(gone["status"], "cancelled")

    def test_requisition_link_and_filters(self):
        """Core 6: an event may link a requisition in the same
        organization; kind and requisition filters work; a
        dangling link raises NotFoundError."""
        requisition = H.make_requisition(self.store, self.org)
        linked = H.make_event(self.store, self.org, event_ref="EVT-L",
                              requisition_id=requisition["id"])
        self.assertEqual(linked["requisition_id"], requisition["id"])
        self.assertEqual(self.store.list_events(
            self.org["id"], H.MEMBER, kind="virtual"), [])
        self.assertEqual(len(self.store.list_events(
            self.org["id"], H.MEMBER,
            requisition_id=requisition["id"])), 1)
        from talentmgmt.errors import NotFoundError
        with self.assertRaises(NotFoundError):
            H.make_event(self.store, self.org, event_ref="EVT-D",
                         requisition_id="req-999")


class TestRegistrations(unittest.TestCase):
    """Core 7: event registration records."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        H.make_candidate(self.store, self.org)
        self.event = H.make_event(self.store, self.org)

    def test_registration_shape_and_check_in(self):
        """Core 7: the registration dict has the contract's keys;
        check-in moves registered -> checked_in exactly once."""
        registration = self.store.register_for_event(
            self.org["id"], self.event["id"], "REG-1", H.CANDIDATE_REF,
            H.MEMBER)
        self.assertEqual(set(registration), {
            "id", "org_id", "event_id", "registration_ref",
            "candidate_ref", "status", "created_by", "created_utc"})
        self.assertEqual(registration["status"], "registered")
        checked = self.store.check_in_registration(
            self.org["id"], registration["id"], H.MEMBER)
        self.assertEqual(checked["status"], "checked_in")
        with self.assertRaises(ValidationError):
            self.store.check_in_registration(
                self.org["id"], registration["id"], H.MEMBER)

    def test_registration_requires_scheduled_event(self):
        """Core 7: a completed or cancelled event takes no new
        registrations."""
        self.store.complete_event(self.org["id"], self.event["id"], H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_for_event(
                self.org["id"], self.event["id"], "REG-1", H.CANDIDATE_REF,
                H.MEMBER)

    def test_registration_requires_registered_candidate(self):
        """Core 7: an unregistered candidate reference is
        rejected."""
        with self.assertRaises(ValidationError):
            self.store.register_for_event(
                self.org["id"], self.event["id"], "REG-1", "CAN-GHOST",
                H.MEMBER)

    def test_one_registration_per_candidate_per_event(self):
        """Core 7 / SI-10: a candidate registers for an event at
        most once, and registration_ref is unique within the
        event; a second candidate is unaffected."""
        self.store.register_for_event(
            self.org["id"], self.event["id"], "REG-1", H.CANDIDATE_REF,
            H.MEMBER)
        with self.assertRaises(ValidationError):
            self.store.register_for_event(
                self.org["id"], self.event["id"], "REG-2", H.CANDIDATE_REF,
                H.MEMBER)
        H.make_candidate(self.store, self.org,
                         candidate_ref=H.CANDIDATE2_REF)
        with self.assertRaises(ValidationError):
            self.store.register_for_event(
                self.org["id"], self.event["id"], "REG-1", H.CANDIDATE2_REF,
                H.MEMBER)
        second = self.store.register_for_event(
            self.org["id"], self.event["id"], "REG-2", H.CANDIDATE2_REF,
            H.MEMBER)
        self.assertEqual(second["candidate_ref"], H.CANDIDATE2_REF)


if __name__ == "__main__":
    unittest.main()
