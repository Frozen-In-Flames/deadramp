"""THE signature invariant (core function 4): the
one-live-session guard.

A route carries at most one live session. A second start while
one is live is refused, records nothing, and consumes no id;
stopping the live session frees the route; the guard is
per-route. The mutation drill against the guard seam is in
test_negative_control.py and tests/README.md.
"""

import unittest

from media_helpers import (ADMIN, OPERATOR, STARTED, STOPPED,
                           make_endpoints, make_org, make_route,
                           make_store)

from media.errors import ValidationError


class SessionGuardTests(unittest.TestCase):
    def test_second_start_refused_while_live(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        store.start_session(OPERATOR, route["id"], started_at=STARTED)
        with self.assertRaises(ValidationError):
            store.start_session(OPERATOR, route["id"])

    def test_refused_start_records_nothing_and_consumes_no_id(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        first = store.start_session(OPERATOR, route["id"],
                                    started_at=STARTED)
        with self.assertRaises(ValidationError):
            store.start_session(OPERATOR, route["id"])
        self.assertEqual(len(store.list_sessions(ADMIN)), 1)
        store.stop_session(OPERATOR, first["id"], stopped_at=STOPPED)
        second = store.start_session(OPERATOR, route["id"])
        self.assertEqual(second["id"], "ses-2")

    def test_stop_frees_the_route(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        first = store.start_session(OPERATOR, route["id"],
                                    started_at=STARTED)
        store.stop_session(OPERATOR, first["id"], stopped_at=STOPPED)
        second = store.start_session(OPERATOR, route["id"])
        self.assertEqual(second["state"], "live")

    def test_guard_is_per_route(self):
        store, _audit = make_store()
        org = make_org(store)
        route_a, _s, _d = make_route(store, org)
        src_b = store.create_endpoint(OPERATOR, org["id"], "NET-B",
                                      "Second network", "agency_network")
        dst_b = store.create_endpoint(OPERATOR, org["id"], "CLOUD-B",
                                      "Second cloud", "cloud_destination")
        route_b = store.create_route(OPERATOR, org["id"], "Route B",
                                     src_b["id"], dst_b["id"])
        store.start_session(OPERATOR, route_a["id"], started_at=STARTED)
        other = store.start_session(OPERATOR, route_b["id"],
                                    started_at=STARTED)
        self.assertEqual(other["state"], "live")
        self.assertEqual(other["route_id"], route_b["id"])


if __name__ == "__main__":
    unittest.main()
