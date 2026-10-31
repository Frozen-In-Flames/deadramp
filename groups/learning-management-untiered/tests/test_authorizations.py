"""Training authorization (SF-182 style) tests.

Traces to: Core function 4 (Authorizations) -- create_authorization
(``aut-``) starts in state "requested"; decide_authorization applies
decision approved|declined only from "requested", and the decider may
NOT be the record's creator (PermissionDenied). Learner scope applies
under Core function 12.
"""

import unittest

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError


class TestAuthorizations(unittest.TestCase):
    """Core 4: authorization requests and decisions."""

    def test_create_shape(self):
        """Core 4: creation returns an aut- record in state 'requested' with subject/bindings, provenance, and no decision applied yet."""
        store, _, course = make_store()
        auth = store.create_authorization("carol", "SF-182 Safety Training", INSTRUCTOR,
                                          course_id=course["id"])
        self.assertEqual(auth["id"], "aut-1")
        self.assertEqual(auth["learner_ref"], "carol")
        self.assertEqual(auth["subject"], "SF-182 Safety Training")
        self.assertEqual(auth["course_id"], course["id"])
        self.assertIsNone(auth["event_id"])
        self.assertEqual(auth["state"], "requested")
        self.assertEqual(auth["created_by"], "bob")
        for key in ("decision", "decided_by", "decision_note", "note"):
            if key in auth:
                self.assertFalse(auth[key], "decision field %r must start empty" % key)

    def test_decide_approve_and_decline(self):
        """Core 4: a decider other than the creator may approve or decline from 'requested'; the record then carries that terminal state."""
        store, _, course = make_store()
        approved = store.create_authorization("carol", "Course A", INSTRUCTOR,
                                              course_id=course["id"])
        decided = store.decide_authorization(approved["id"], "approved", ADMIN,
                                             note="funds available")
        self.assertEqual(decided["state"], "approved")
        self.assertEqual(store.get_authorization(approved["id"], ADMIN)["state"], "approved")

        declined = store.create_authorization("carol", "Course B", ADMIN,
                                              course_id=course["id"])
        decided = store.decide_authorization(declined["id"], "declined", INSTRUCTOR)
        self.assertEqual(decided["state"], "declined")

    def test_decider_may_not_be_creator(self):
        """Core 4: the record's creator deciding their own authorization -> PermissionDenied, and the record stays 'requested'."""
        store, _, course = make_store()
        auth = store.create_authorization("carol", "Self Deal", INSTRUCTOR,
                                          course_id=course["id"])
        with self.assertRaises(PermissionDenied):
            store.decide_authorization(auth["id"], "approved", INSTRUCTOR)
        self.assertEqual(store.get_authorization(auth["id"], ADMIN)["state"], "requested")
        admin_auth = store.create_authorization("carol", "Admin Self Deal", ADMIN,
                                                course_id=course["id"])
        with self.assertRaises(PermissionDenied):
            store.decide_authorization(admin_auth["id"], "approved", ADMIN)

    def test_decide_twice_and_bad_decision(self):
        """Core 4: deciding an already-decided authorization -> ValidationError; a decision outside approved|declined -> ValidationError; failed decides consume/change nothing."""
        store, _, course = make_store()
        auth = store.create_authorization("carol", "Course A", INSTRUCTOR,
                                          course_id=course["id"])
        with self.assertRaises(ValidationError):
            store.decide_authorization(auth["id"], "maybe", ADMIN)
        self.assertEqual(store.get_authorization(auth["id"], ADMIN)["state"], "requested")
        store.decide_authorization(auth["id"], "approved", ADMIN)
        with self.assertRaises(ValidationError):
            store.decide_authorization(auth["id"], "declined", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.decide_authorization("aut-999", "approved", ADMIN)

    def test_unknown_references(self):
        """Core 4: unknown learner_ref / course_id / event_id at creation -> NotFoundError; no id consumed."""
        store, _, course = make_store()
        with self.assertRaises(NotFoundError):
            store.create_authorization("ghost", "X", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.create_authorization("carol", "X", INSTRUCTOR, course_id="crs-999")
        with self.assertRaises(NotFoundError):
            store.create_authorization("carol", "X", INSTRUCTOR, event_id="evt-999")
        auth = store.create_authorization("carol", "X", INSTRUCTOR, course_id=course["id"])
        self.assertEqual(auth["id"], "aut-1")

    def test_event_bound_authorization(self):
        """Core 4: an authorization may bind to an event instead of a course."""
        store, _, course = make_store()
        event = store.create_event("Briefing", "2026-07-01T09:00:00Z", INSTRUCTOR,
                                   course_id=course["id"])
        auth = store.create_authorization("carol", "Attend Briefing", INSTRUCTOR,
                                          event_id=event["id"])
        self.assertEqual(auth["event_id"], event["id"])
        self.assertIsNone(auth["course_id"])

    def test_learner_scope_and_permissions(self):
        """Core 4 / Core 12: a learner may not create or decide authorizations; a learner reads her own authorization, is denied another's, and lists only her own."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.create_authorization("carol", "X", LEARNER, course_id=course["id"])
        own = store.create_authorization("carol", "Mine", INSTRUCTOR, course_id=course["id"])
        other = store.create_authorization("erin", "Theirs", INSTRUCTOR, course_id=course["id"])
        with self.assertRaises(PermissionDenied):
            store.decide_authorization(own["id"], "approved", AUDITOR)
        self.assertEqual(store.get_authorization(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_authorization(other["id"], LEARNER)
        self.assertEqual([a["id"] for a in store.list_authorizations(LEARNER)], [own["id"]])
        self.assertEqual(
            len(store.list_authorizations(ADMIN, learner_ref="erin")), 1
        )


if __name__ == "__main__":
    unittest.main()
