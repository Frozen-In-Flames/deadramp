"""Access-request / grant governance tests.

Traces to: Core functions -- Access requests, Access decisions,
Grants; contract for ``request_access`` /
``decide_access_request`` / ``get_access_request`` /
``list_access_requests`` / ``get_grant`` / ``list_grants`` /
``revoke_grant`` / ``active_grants``; control families AC-3/AC-5
(separation of duties: a requester never decides their own request),
AC-6. Failed operations must consume no ids (neither ar- nor gr-).
Expiry math: grant expires_utc = grant created_utc + duration_days.
"""

import unittest
from datetime import datetime, timedelta

from datamgmt_helpers import ADMIN, STEWARD, VIEWER, make_store
from datamgmt.errors import NotFoundError, PermissionDenied, ValidationError


def _parse(ts):
    """Core: Access governance. Timestamps parse as ISO-8601."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _iso(dt):
    """Core: Access governance. Datetime -> ISO string for explicit now arguments."""
    return dt.isoformat().replace("+00:00", "Z")


class TestRequestAccess(unittest.TestCase):
    """Core: Access requests -- request_access."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()

    def test_request_shape(self):
        """Core: Access requests. A new request carries ar-1 and the pinned requested-state fields."""
        req = self.store.request_access(self.dataset["id"], "research use", VIEWER)
        self.assertEqual(req["id"], "ar-1")
        self.assertEqual(req["dataset_id"], self.dataset["id"])
        self.assertEqual(req["requester"], "carol")
        self.assertEqual(req["purpose"], "research use")
        self.assertEqual(req["duration_days"], 30)
        self.assertEqual(req["status"], "requested")
        self.assertIsNone(req["reason"])
        self.assertIsNone(req["decided_by"])
        self.assertIsNone(req["decided_utc"])
        self.assertIsNone(req["grant_id"])
        self.assertIn("created_utc", req)

    def test_request_custom_duration(self):
        """Core: Access requests. An explicit duration_days in 1..365 is preserved."""
        req = self.store.request_access(self.dataset["id"], "p", VIEWER, duration_days=7)
        self.assertEqual(req["duration_days"], 7)

    def test_request_duration_bounds(self):
        """Core: Access requests (SI-10). duration_days 1 and 365 pass; 0 and 366 are rejected."""
        self.assertEqual(
            self.store.request_access(self.dataset["id"], "p", VIEWER, duration_days=1)["duration_days"], 1
        )
        ds2 = self.store.create_dataset("D2", "d", STEWARD)
        self.assertEqual(
            self.store.request_access(ds2["id"], "p", VIEWER, duration_days=365)["duration_days"], 365
        )

    def test_request_bad_duration_no_id(self):
        """Core: Access requests (SI-10). duration_days 0/366/negative/non-int -> ValidationError, no id consumed."""
        for bad in (0, 366, -5, "30", True):
            with self.subTest(duration_days=bad):
                with self.assertRaises(ValidationError):
                    self.store.request_access(self.dataset["id"], "p", VIEWER, duration_days=bad)
        req = self.store.request_access(self.dataset["id"], "p", VIEWER)
        self.assertEqual(req["id"], "ar-1")

    def test_request_unknown_dataset_not_found(self):
        """Core: Access requests. Unknown dataset -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.request_access("ds-999", "p", VIEWER)

    def test_duplicate_pending_rejected_no_id(self):
        """Core: Access requests (AC-5). A second pending request by the same requester for the same dataset -> ValidationError, no id."""
        self.store.request_access(self.dataset["id"], "first", VIEWER)
        with self.assertRaises(ValidationError):
            self.store.request_access(self.dataset["id"], "second", VIEWER)
        # A different requester may still request the same dataset.
        req = self.store.request_access(self.dataset["id"], "steward ask", STEWARD)
        self.assertEqual(req["id"], "ar-2")

    def test_duplicate_after_decision_allowed(self):
        """Core: Access requests. Once the pending request is denied, the same requester may request again."""
        req = self.store.request_access(self.dataset["id"], "first", VIEWER)
        self.store.decide_access_request(req["id"], False, STEWARD, reason="no")
        again = self.store.request_access(self.dataset["id"], "retry", VIEWER)
        self.assertEqual(again["status"], "requested")
        self.assertEqual(again["id"], "ar-2")

    def test_get_and_list_requests(self):
        """Core: Access requests. get_access_request round-trips; list filters by dataset, viewer-readable."""
        req = self.store.request_access(self.dataset["id"], "p", VIEWER)
        self.assertEqual(self.store.get_access_request(req["id"], VIEWER)["id"], req["id"])
        self.assertEqual(
            [r["id"] for r in self.store.list_access_requests(dataset_id=self.dataset["id"], actor=VIEWER)],
            [req["id"]],
        )
        self.assertEqual(len(self.store.list_access_requests(actor=VIEWER)), 1)
        with self.assertRaises(NotFoundError):
            self.store.get_access_request("ar-999", STEWARD)

    def test_none_actor_request_denied(self):
        """Core: Access requests (IA-2). None actor on request_access -> PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.request_access(self.dataset["id"], "p", None)


class TestDecideAccess(unittest.TestCase):
    """Core: Access decisions -- decide_access_request."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()
        self.req = self.store.request_access(self.dataset["id"], "research use", VIEWER, duration_days=10)

    def test_self_decision_denied_request_stays_requested_no_grant(self):
        """Core: Access decisions (AC-3/AC-5 separation of duties). Requester deciding own request -> PermissionDenied; request stays requested; no grant exists."""
        own = self.store.request_access(self.dataset["id"], "mine", STEWARD)
        with self.assertRaises(PermissionDenied):
            self.store.decide_access_request(own["id"], True, STEWARD)
        after = self.store.get_access_request(own["id"], STEWARD)
        self.assertEqual(after["status"], "requested")
        self.assertIsNone(after["grant_id"])
        self.assertEqual(self.store.list_grants(actor=STEWARD), [])

    def test_admin_self_decision_also_denied(self):
        """Core: Access decisions (AC-5). Even an admin may not decide their own request."""
        own = self.store.request_access(self.dataset["id"], "admin ask", ADMIN)
        with self.assertRaises(PermissionDenied):
            self.store.decide_access_request(own["id"], True, ADMIN)
        self.assertEqual(self.store.get_access_request(own["id"], ADMIN)["status"], "requested")

    def test_viewer_decide_denied(self):
        """Core: Access decisions (AC-3). Viewer lacks access_decide -> PermissionDenied; request unchanged."""
        with self.assertRaises(PermissionDenied):
            self.store.decide_access_request(self.req["id"], True, VIEWER)
        self.assertEqual(
            self.store.get_access_request(self.req["id"], STEWARD)["status"], "requested"
        )
        self.assertEqual(self.store.list_grants(actor=STEWARD), [])

    def test_approve_creates_grant_and_updates_request(self):
        """Core: Access decisions. Steward approving carol's request -> request approved with grant_id, decided_by/utc set."""
        decided = self.store.decide_access_request(self.req["id"], True, STEWARD)
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(decided["decided_by"], "bob")
        self.assertIsNotNone(decided["decided_utc"])
        self.assertEqual(decided["grant_id"], "gr-1")
        grant = self.store.get_grant("gr-1", STEWARD)
        self.assertEqual(grant["dataset_id"], self.dataset["id"])
        self.assertEqual(grant["grantee"], "carol")

    def test_grant_fields_and_expiry_math(self):
        """Core: Grants. Grant carries grantee/purpose/granted_by, revoked False, and expires = created + duration_days (10)."""
        self.store.decide_access_request(self.req["id"], True, STEWARD)
        grant = self.store.get_grant("gr-1", STEWARD)
        self.assertEqual(grant["purpose"], "research use")
        self.assertEqual(grant["granted_by"], "bob")
        self.assertFalse(grant["revoked"])
        self.assertIsNone(grant["revoked_utc"])
        created = _parse(grant["created_utc"])
        expires = _parse(grant["expires_utc"])
        self.assertEqual(expires - created, timedelta(days=10))

    def test_deny_path_no_grant(self):
        """Core: Access decisions. approve=False -> status denied, grant_id stays None, no grant created (no gr id consumed)."""
        decided = self.store.decide_access_request(self.req["id"], False, STEWARD, reason="insufficient purpose")
        self.assertEqual(decided["status"], "denied")
        self.assertIsNone(decided["grant_id"])
        self.assertEqual(decided["decided_by"], "bob")
        self.assertEqual(self.store.list_grants(actor=STEWARD), [])
        # A later approval elsewhere still gets gr-1.
        req2 = self.store.request_access(self.dataset["id"], "again", ADMIN)
        self.store.decide_access_request(req2["id"], True, STEWARD)
        self.assertEqual(self.store.list_grants(actor=STEWARD)[0]["id"], "gr-1")

    def test_decide_non_pending_validation(self):
        """Core: Access decisions (SI-10). Deciding an already-decided request -> ValidationError."""
        self.store.decide_access_request(self.req["id"], True, STEWARD)
        with self.assertRaises(ValidationError):
            self.store.decide_access_request(self.req["id"], True, ADMIN)
        denied_req = self.store.request_access(self.dataset["id"], "x", ADMIN)
        self.store.decide_access_request(denied_req["id"], False, STEWARD)
        with self.assertRaises(ValidationError):
            self.store.decide_access_request(denied_req["id"], False, STEWARD)

    def test_decide_unknown_not_found(self):
        """Core: Access decisions. Unknown request id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.decide_access_request("ar-999", True, STEWARD)


class TestGrants(unittest.TestCase):
    """Core: Grants -- get/list/revoke/active."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()
        req = self.store.request_access(self.dataset["id"], "research use", VIEWER, duration_days=30)
        self.store.decide_access_request(req["id"], True, STEWARD)
        self.grant = self.store.get_grant("gr-1", STEWARD)

    def test_get_unknown_grant_not_found(self):
        """Core: Grants. Unknown grant id -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.get_grant("gr-999", STEWARD)

    def test_list_grants_filters(self):
        """Core: Grants. list_grants filters by dataset and by grantee."""
        self.assertEqual(
            [g["id"] for g in self.store.list_grants(dataset_id=self.dataset["id"], actor=VIEWER)],
            ["gr-1"],
        )
        self.assertEqual(
            [g["id"] for g in self.store.list_grants(grantee="carol", actor=VIEWER)], ["gr-1"]
        )
        self.assertEqual(self.store.list_grants(grantee="nobody", actor=VIEWER), [])

    def test_revoke_grant(self):
        """Core: Grants. revoke_grant sets revoked True and revoked_utc."""
        revoked = self.store.revoke_grant(self.grant["id"], STEWARD)
        self.assertTrue(revoked["revoked"])
        self.assertIsNotNone(revoked["revoked_utc"])
        self.assertTrue(self.store.get_grant(self.grant["id"], STEWARD)["revoked"])

    def test_double_revoke_validation(self):
        """Core: Grants (SI-10). Revoking an already-revoked grant -> ValidationError."""
        self.store.revoke_grant(self.grant["id"], STEWARD)
        with self.assertRaises(ValidationError):
            self.store.revoke_grant(self.grant["id"], STEWARD)

    def test_revoke_unknown_not_found(self):
        """Core: Grants. Revoking an unknown grant -> NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.revoke_grant("gr-999", STEWARD)

    def test_viewer_revoke_denied(self):
        """Core: Grants (AC-3). Viewer may not revoke a grant; grant stays active."""
        with self.assertRaises(PermissionDenied):
            self.store.revoke_grant(self.grant["id"], VIEWER)
        self.assertFalse(self.store.get_grant(self.grant["id"], STEWARD)["revoked"])

    def test_active_grants_includes_live_grant(self):
        """Core: Grants. active_grants includes a non-revoked, unexpired grant (explicit now = created + 1 day)."""
        now = _iso(_parse(self.grant["created_utc"]) + timedelta(days=1))
        active = self.store.active_grants(self.dataset["id"], actor=VIEWER, now=now)
        self.assertEqual([g["id"] for g in active], ["gr-1"])

    def test_active_grants_excludes_expired(self):
        """Core: Grants. active_grants excludes a grant once now passes expires_utc (created + 31 days for a 30-day grant)."""
        now = _iso(_parse(self.grant["created_utc"]) + timedelta(days=31))
        self.assertEqual(self.store.active_grants(self.dataset["id"], actor=VIEWER, now=now), [])

    def test_active_grants_excludes_revoked(self):
        """Core: Grants. active_grants excludes a revoked grant even before expiry."""
        self.store.revoke_grant(self.grant["id"], STEWARD)
        now = _iso(_parse(self.grant["created_utc"]) + timedelta(days=1))
        self.assertEqual(self.store.active_grants(self.dataset["id"], actor=VIEWER, now=now), [])


if __name__ == "__main__":
    unittest.main()
