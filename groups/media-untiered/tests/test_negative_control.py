"""Mutation-verified negative control for the one-live-session
guard.

An oracle that passes whether or not the guard enforces is
testing that code ran, not that the guard holds. So the
canonical guard expectation is asserted here against a MUTANT
seam that never refuses a start — under the mutant, a second
live session can be started on a route that already has one —
and the test asserts the canonical check FAILS against the
mutant. If the guard tests ever stopped discriminating, this
test fails.

The external drill (the same patch applied to the real
``src/media/store.py``, suite re-run, file restored
byte-identical) is recorded in tests/README.md.
"""

import unittest

from media_helpers import (ADMIN, OPERATOR, STARTED, STOPPED,
                           make_org, make_route, make_store)

import media.store as store_module

from media.errors import ValidationError


def _mutant_guard(open_session):
    """Mutant seam: the guard never refuses."""
    return None


def canonical_second_start_is_refused(store, route_id):
    """The guard suite's core expectation, stated once.

    Raises AssertionError when a second session start succeeds
    on a route with a live session, or when the refusal leaves a
    record behind or consumes an id.
    """
    first = store.start_session(OPERATOR, route_id, started_at=STARTED)
    try:
        store.start_session(OPERATOR, route_id)
    except ValidationError:
        pass
    else:
        raise AssertionError(
            "a second session was started on a route with a live "
            "session; the guard did not refuse")
    sessions = store.list_sessions(ADMIN, route_id=route_id)
    assert len(sessions) == 1, (
        "the refused start left a record behind: %r" % (sessions,))
    store.stop_session(OPERATOR, first["id"], stopped_at=STOPPED)
    second = store.start_session(OPERATOR, route_id)
    assert second["id"] == "ses-2", (
        "the refused start consumed an id: next session is %r"
        % (second["id"],))


class NegativeControlTests(unittest.TestCase):
    def _setup(self):
        store, _audit = make_store()
        org = make_org(store)
        route, _s, _d = make_route(store, org)
        return store, route["id"]

    def test_canonical_check_passes_on_the_real_store(self):
        store, route_id = self._setup()
        canonical_second_start_is_refused(store, route_id)

    def test_canonical_check_fails_on_the_mutant(self):
        store, route_id = self._setup()
        original = store_module._check_route_available
        store_module._check_route_available = _mutant_guard
        try:
            with self.assertRaises(AssertionError):
                canonical_second_start_is_refused(store, route_id)
        finally:
            store_module._check_route_available = original

    def test_guard_is_route_scoped_on_the_real_store(self):
        """The other arm discriminates too: on the canonical store
        a start on a DIFFERENT route succeeds while the first
        route's session is live, so the invariant is per-route,
        not store-wide."""
        store, route_id = self._setup()
        orgs = store.list_organizations(ADMIN)
        route_b, _s, _d = make_route(store, orgs[0], tag="B")
        store.start_session(OPERATOR, route_id, started_at=STARTED)
        other = store.start_session(OPERATOR, route_b["id"],
                                    started_at=STARTED)
        self.assertEqual(other["state"], "live")


ORACLE_EXPECTED = (
    "test_negative_control.NegativeControlTests."
    "test_canonical_check_passes_on_the_real_store, "
    "test_session_guard.SessionGuardTests."
    "test_second_start_refused_while_live, "
    "test_session_guard.SessionGuardTests."
    "test_refused_start_records_nothing_and_consumes_no_id, "
    "test_service.ServiceTests.test_full_flow_with_session_guard"
)

if __name__ == "__main__":
    unittest.main()
