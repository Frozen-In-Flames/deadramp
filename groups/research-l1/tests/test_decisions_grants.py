"""Core: Decision records and access grant records. Traces to
UNION-SPEC core functions 6 (decisions — a decision on a pending
request by someone who is not the requester) and 7's grant
records, the separation-of-duties seam (AC-5), and SI-10 (a
decision on a non-pending request is rejected whole).

A grant's status (scheduled / active / expired / revoked) is the
group's signature derivation: it is derived at read from the
start, expiry, and revocation timestamp against the read clock
and is never stored — the stored grant record carries no
``status`` key."""

import unittest

import research_helpers as H
from research.errors import PermissionDenied, ValidationError

DECISION_KEYS = {"id", "request_id", "dataset_id", "commons_id", "decider",
                 "approve", "note", "created_utc"}
GRANT_STORED_KEYS = {"id", "dataset_id", "commons_id", "request_id",
                     "grantee", "starts_at", "expires_at", "revoked_at",
                     "created_by", "created_utc"}


class TestDecisions(unittest.TestCase):
    def setUp(self):
        self.store, self.commons, self.org = H.make_store()
        self.dataset = H.make_dataset(self.store, self.commons)

    def _request(self, **overrides):
        return H.make_access_request(self.store, self.dataset, **overrides)

    def test_requester_cannot_decide_own_request(self):
        """AC-5: the decider of a request is never its requester."""
        request = self._request()
        with self.assertRaises(PermissionDenied):
            self.store.decide_access_request(H.MEMBER, request["id"], True,
                                             starts_at=H.T0)
        # The failed attempt changed nothing.
        self.assertEqual(
            self.store.get_access_request(H.STAFF, request["id"])["status"],
            "pending")
        self.assertEqual(
            self.store.list_grants(H.MEMBER, self.commons["id"],
                                   now=H.INSIDE_WINDOW), [])

    def test_deciding_non_pending_request_rejected(self):
        approved = self._request()
        self.store.decide_access_request(H.STAFF, approved["id"], True,
                                         starts_at=H.T0)
        with self.assertRaises(ValidationError):
            self.store.decide_access_request(H.STAFF, approved["id"], True,
                                             starts_at=H.T0)
        declined = self._request(purpose="Another planned analysis")
        self.store.decide_access_request(H.STAFF, declined["id"], False,
                                         note="Out of scope")
        with self.assertRaises(ValidationError):
            self.store.decide_access_request(H.STAFF, declined["id"], True,
                                             starts_at=H.T0)

    def test_decline_mints_no_grant(self):
        request = self._request()
        result = self.store.decide_access_request(
            H.STAFF, request["id"], False, note="Out of scope")
        self.assertNotIn("grant", result)
        self.assertEqual(set(result.keys()), {"decision", "request"})
        decision = result["decision"]
        self.assertEqual(set(decision.keys()), DECISION_KEYS)
        self.assertTrue(decision["id"].startswith("dec-"))
        self.assertEqual(decision["decider"], "erin")
        self.assertEqual(decision["approve"], False)
        self.assertEqual(decision["note"], "Out of scope")
        self.assertEqual(result["request"]["status"], "denied")
        self.assertEqual(
            self.store.list_grants(H.MEMBER, self.commons["id"],
                                   now=H.INSIDE_WINDOW), [])

    def test_approval_mints_grant_with_computed_expiry(self):
        request = self._request(duration_days=30)
        result = self.store.decide_access_request(
            H.STAFF, request["id"], True, note="Approved as reviewed",
            starts_at=H.T0)
        decision = result["decision"]
        self.assertEqual(set(decision.keys()), DECISION_KEYS)
        self.assertEqual(decision["decider"], "erin")
        self.assertEqual(decision["approve"], True)
        self.assertEqual(result["request"]["status"], "approved")
        grant = result["grant"]
        # The decision result carries the grant *view*: the stored
        # record's pinned keys plus the derived status.
        self.assertEqual(set(grant.keys()), GRANT_STORED_KEYS | {"status"})
        self.assertTrue(grant["id"].startswith("gr-"))
        self.assertEqual(grant["request_id"], request["id"])
        self.assertEqual(grant["dataset_id"], self.dataset["id"])
        self.assertEqual(grant["commons_id"], self.commons["id"])
        self.assertEqual(grant["grantee"], "bob")
        self.assertEqual(grant["starts_at"], H.T0)
        # expires_at = starts_at + the requested duration in days.
        self.assertEqual(grant["expires_at"], H.EXPIRES_AT)
        self.assertIsNone(grant["revoked_at"])


class TestGrantDerivation(unittest.TestCase):
    def setUp(self):
        self.store, self.commons, self.org = H.make_store()
        self.dataset = H.make_dataset(self.store, self.commons)
        self.grant = H.make_grant(self.store, self.commons, self.dataset,
                                  starts_at=H.T0, duration_days=30)

    def _status(self, now, actor=H.MEMBER):
        return self.store.get_grant(actor, self.grant["id"], now=now)["status"]

    def test_status_is_derived_from_the_read_clock(self):
        self.assertEqual(self._status(H.BEFORE_T0), "scheduled")
        self.assertEqual(self._status(H.T0), "active")
        self.assertEqual(self._status(H.INSIDE_WINDOW), "active")
        # Derivation per contract: expired only when moment > expires_at.
        self.assertEqual(self._status(H.EXPIRES_AT), "active")
        self.assertEqual(self._status(H.AFTER_EXPIRY), "expired")

    def test_revocation_beats_expiry(self):
        self.store.revoke_grant(H.STAFF, self.grant["id"])
        # Inside the window the grant would be active, and after the
        # window it would be expired — revocation wins over both.
        self.assertEqual(self._status(H.INSIDE_WINDOW), "revoked")
        self.assertEqual(self._status(H.AFTER_EXPIRY), "revoked")
        raw = self.store._grants[self.grant["id"]]
        self.assertIsNotNone(raw["revoked_at"])

    def test_double_revoke_rejected(self):
        self.store.revoke_grant(H.STAFF, self.grant["id"])
        with self.assertRaises(ValidationError):
            self.store.revoke_grant(H.STAFF, self.grant["id"])

    def test_stored_grant_record_carries_no_status(self):
        raw = self.store._grants[self.grant["id"]]
        self.assertNotIn("status", raw)
        self.assertEqual(set(raw.keys()), GRANT_STORED_KEYS)

    def test_list_grants_status_filter_uses_derived_status(self):
        scheduled = H.make_grant(self.store, self.commons, self.dataset,
                                 starts_at=H.FUTURE_START, duration_days=30,
                                 purpose="Later planned analysis")
        cid = self.commons["id"]
        all_grants = self.store.list_grants(H.MEMBER, cid,
                                            now=H.INSIDE_WINDOW)
        self.assertEqual(len(all_grants), 2)
        active = self.store.list_grants(H.MEMBER, cid, status="active",
                                        now=H.INSIDE_WINDOW)
        self.assertEqual([g["id"] for g in active], [self.grant["id"]])
        upcoming = self.store.list_grants(H.MEMBER, cid, status="scheduled",
                                          now=H.INSIDE_WINDOW)
        self.assertEqual([g["id"] for g in upcoming], [scheduled["id"]])
        self.assertEqual(
            self.store.list_grants(H.MEMBER, cid, status="expired",
                                   now=H.INSIDE_WINDOW), [])
        self.store.revoke_grant(H.STAFF, self.grant["id"])
        revoked = self.store.list_grants(H.MEMBER, cid, status="revoked",
                                         now=H.INSIDE_WINDOW)
        self.assertEqual([g["id"] for g in revoked], [self.grant["id"]])
        self.assertEqual(
            self.store.list_grants(H.MEMBER, cid, status="active",
                                   now=H.INSIDE_WINDOW), [])

    def test_outsider_cannot_read_list_or_revoke_grant(self):
        with self.assertRaises(PermissionDenied):
            self.store.get_grant(H.OUTSIDER, self.grant["id"],
                                 now=H.INSIDE_WINDOW)
        with self.assertRaises(PermissionDenied):
            self.store.list_grants(H.OUTSIDER, self.commons["id"],
                                   now=H.INSIDE_WINDOW)
        with self.assertRaises(PermissionDenied):
            self.store.revoke_grant(H.OUTSIDER, self.grant["id"])


if __name__ == "__main__":
    unittest.main()
