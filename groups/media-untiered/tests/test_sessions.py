"""Stream sessions (core function 4): lifecycle and the derived
session state."""

import unittest

from media_helpers import (OPERATOR, STARTED, STOPPED, VIEWER,
                           make_org, make_route, make_store)

from media.errors import NotFoundError, ValidationError


class SessionTests(unittest.TestCase):
    def _route(self, store):
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        return route

    def test_session_shape_and_derived_state(self):
        store, _audit = make_store()
        route = self._route(store)
        session = store.start_session(OPERATOR, route["id"],
                                      started_at=STARTED)
        self.assertEqual(session["state"], "live")
        self.assertIsNone(session["stopped_at"])
        stored = store._sessions[session["id"]]
        self.assertNotIn("state", stored)
        ended = store.stop_session(OPERATOR, session["id"],
                                   stopped_at=STOPPED)
        self.assertEqual(ended["state"], "ended")
        self.assertEqual(ended["stopped_at"], STOPPED)

    def test_stop_of_ended_session_refused(self):
        store, _audit = make_store()
        route = self._route(store)
        session = store.start_session(OPERATOR, route["id"],
                                      started_at=STARTED)
        store.stop_session(OPERATOR, session["id"], stopped_at=STOPPED)
        with self.assertRaises(ValidationError):
            store.stop_session(OPERATOR, session["id"])

    def test_stop_before_start_refused_and_changes_nothing(self):
        store, _audit = make_store()
        route = self._route(store)
        session = store.start_session(OPERATOR, route["id"],
                                      started_at=STOPPED)
        with self.assertRaises(ValidationError):
            store.stop_session(OPERATOR, session["id"],
                               stopped_at=STARTED)
        self.assertEqual(
            store.get_session(VIEWER, session["id"])["state"], "live")

    def test_unknown_route_and_bad_moment_refused(self):
        store, _audit = make_store()
        route = self._route(store)
        with self.assertRaises(NotFoundError):
            store.start_session(OPERATOR, "rou-99")
        with self.assertRaises(ValidationError):
            store.start_session(OPERATOR, route["id"],
                                started_at="not a moment")

    def test_list_sessions_filters(self):
        store, _audit = make_store()
        route = self._route(store)
        first = store.start_session(OPERATOR, route["id"],
                                    started_at=STARTED)
        store.stop_session(OPERATOR, first["id"], stopped_at=STOPPED)
        second = store.start_session(OPERATOR, route["id"])
        self.assertEqual(
            [s["id"] for s in store.list_sessions(
                VIEWER, route_id=route["id"], state="ended")],
            [first["id"]])
        self.assertEqual(
            [s["id"] for s in store.list_sessions(
                VIEWER, state="live")],
            [second["id"]])
        with self.assertRaises(ValidationError):
            store.list_sessions(VIEWER, state="paused")


if __name__ == "__main__":
    unittest.main()
