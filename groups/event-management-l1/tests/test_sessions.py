"""Core function 5: session (gathering) records.

Claims traced: webinars, networking_roundtables,
speaker_engagements. A session's window must lie within its
event's window; its status is derived at read, never stored. A
speaker is named only by an opaque reference.
"""

import unittest

from events.errors import NotFoundError, ValidationError

from events_helpers import (AFTER, BEFORE, DURING, ENDS, SESS_DURING,
                            SESS_ENDS, SESS_STARTS, STARTS, ADMIN, MEMBER,
                            VIEWER, make_event, make_organizer, make_store)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.organizer = make_organizer(self.store)
        self.event = make_event(self.store, self.organizer)

    def test_create_each_claimed_kind(self):
        for kind in ("webinar", "roundtable", "speaker_engagement"):
            session = self.store.create_session(
                MEMBER, self.event["id"], kind, "Session " + kind,
                SESS_STARTS, SESS_ENDS,
                speaker_ref="SPK-1" if kind == "speaker_engagement" else None)
            self.assertEqual(session["kind"], kind)
            self.assertTrue(session["id"].startswith("ses-"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_session(MEMBER, self.event["id"], "keynote",
                                      "X", SESS_STARTS, SESS_ENDS)

    def test_window_must_lie_within_event(self):
        with self.assertRaises(ValidationError):
            self.store.create_session(MEMBER, self.event["id"], "webinar",
                                      "Early", BEFORE, SESS_ENDS)
        with self.assertRaises(ValidationError):
            self.store.create_session(MEMBER, self.event["id"], "webinar",
                                      "Late", SESS_STARTS, AFTER)

    def test_status_derived_at_read(self):
        session = self.store.create_session(
            MEMBER, self.event["id"], "webinar", "Briefing",
            SESS_STARTS, SESS_ENDS)
        stored = self.store._sessions[session["id"]]
        self.assertNotIn("status", stored)
        self.assertEqual(
            self.store.get_session(VIEWER, session["id"],
                                   now=BEFORE)["status"], "upcoming")
        self.assertEqual(
            self.store.get_session(VIEWER, session["id"],
                                   now=SESS_DURING)["status"], "live")
        self.assertEqual(
            self.store.get_session(VIEWER, session["id"],
                                   now=AFTER)["status"], "concluded")

    def test_speaker_is_an_opaque_ref_only(self):
        session = self.store.create_session(
            MEMBER, self.event["id"], "speaker_engagement", "Talk",
            SESS_STARTS, SESS_ENDS, speaker_ref="SPK-0042")
        self.assertEqual(session["speaker_ref"], "SPK-0042")
        self.assertNotIn("speaker_name", session)
        self.assertNotIn("speaker_email", session)

    def test_list_filters_and_counts_on_event_view(self):
        self.store.create_session(MEMBER, self.event["id"], "webinar",
                                  "W", SESS_STARTS, SESS_ENDS)
        self.store.create_session(MEMBER, self.event["id"], "roundtable",
                                  "R", SESS_STARTS, SESS_ENDS)
        self.assertEqual(
            len(self.store.list_sessions(VIEWER, event_id=self.event["id"])),
            2)
        self.assertEqual(
            len(self.store.list_sessions(VIEWER, kind="webinar")), 1)
        view = self.store.get_event(ADMIN, self.event["id"], now=DURING)
        self.assertEqual(view["session_count"], 2)
        with self.assertRaises(NotFoundError):
            self.store.get_session(VIEWER, "ses-99")


if __name__ == "__main__":
    unittest.main()
