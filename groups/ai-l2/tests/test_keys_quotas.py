"""API-key and quota/usage tests.

Traces to: UNION-SPEC Core function 9 (Access control & API keys),
Core function 4 (Usage metering & quotas), and the Implementation
contract for ``create_api_key`` / ``authenticate_key`` /
``list_api_keys`` / ``set_quota`` / ``get_quota`` / ``usage_for``;
control families AC-2, IA-5 (authenticator hygiene: SHA-256 only).
"""

import hashlib
import unittest
from datetime import datetime, timezone

from aigateway_helpers import ADMIN, MEMBER, OTHER_MEMBER, VIEWER, make_store
from aigateway.errors import PermissionDenied, QuotaExceeded, ValidationError


class TestApiKeys(unittest.TestCase):
    """Core function 9: API keys."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_create_key_shape_and_secret_shown_once(self):
        """Core 9: create_api_key returns {id, owner, secret,
        created_by, created_utc} with a key- id; the secret appears
        only in this return value."""
        key = self.store.create_api_key("bob", MEMBER)
        self.assertEqual(
            set(key.keys()), {"id", "owner", "secret", "created_by", "created_utc"}
        )
        self.assertEqual(key["id"], "key-1")
        self.assertEqual(key["owner"], "bob")
        self.assertTrue(key["secret"])
        listed = self.store.list_api_keys(MEMBER)
        self.assertNotIn(key["secret"], str(listed))

    def test_store_keeps_only_sha256_of_secret(self):
        """Core 9 (IA-5): the store keeps secret_hash = SHA-256 hex of
        the secret and no other copy of the secret (white-box check of
        the internal record, plus the public list hides the hash)."""
        key = self.store.create_api_key("bob", MEMBER)
        internal = self.store._keys[key["id"]]
        expected = hashlib.sha256(key["secret"].encode("utf-8")).hexdigest()
        self.assertEqual(internal["secret_hash"], expected)
        self.assertNotIn("secret", {k for k in internal if k != "secret_hash"})
        self.assertNotIn(key["secret"], str(internal))
        listed = self.store.list_api_keys(ADMIN)[0]
        self.assertNotIn("secret", listed)
        self.assertNotIn("secret_hash", listed)
        self.assertEqual(
            set(listed.keys()), {"id", "owner", "created_by", "created_utc"}
        )

    def test_secret_is_never_audited(self):
        """Core 9: key_create is audited, but the secret value never
        appears in the audit trail."""
        key = self.store.create_api_key("bob", MEMBER)
        self.assertIn("key_create", [e["action"] for e in self.audit.entries()])
        self.assertNotIn(key["secret"], str(self.audit.entries()))

    def test_authenticate_key(self):
        """Core 9: authenticate_key(secret) returns the owner's name;
        a wrong or malformed secret returns None."""
        key = self.store.create_api_key("bob", MEMBER)
        self.assertEqual(self.store.authenticate_key(key["secret"]), "bob")
        self.assertIsNone(self.store.authenticate_key("sk-deadbeef"))
        self.assertIsNone(self.store.authenticate_key(""))
        self.assertIsNone(self.store.authenticate_key(None))

    def test_create_key_owner_or_admin_only(self):
        """Core 9: the actor must be the owner themself or a platform
        admin, else PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.create_api_key("bob", OTHER_MEMBER)
        by_admin = self.store.create_api_key("bob", ADMIN)
        self.assertEqual(by_admin["owner"], "bob")
        self.assertEqual(by_admin["created_by"], "alice")
        own = self.store.create_api_key("dave", OTHER_MEMBER)
        self.assertEqual(own["owner"], "dave")

    def test_viewer_cannot_create_key(self):
        """Core 9: a viewer lacks registry_write, so even creating
        their own key is PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.create_api_key("carol", VIEWER)

    def test_list_keys_scoped_for_non_admin(self):
        """Core 9: a non-admin actor sees only their own keys in
        list_api_keys; an admin sees all."""
        self.store.create_api_key("bob", MEMBER)
        self.store.create_api_key("dave", OTHER_MEMBER)
        bob_keys = self.store.list_api_keys(MEMBER)
        self.assertEqual([k["owner"] for k in bob_keys], ["bob"])
        all_keys = self.store.list_api_keys(ADMIN)
        self.assertEqual(sorted(k["owner"] for k in all_keys), ["bob", "dave"])


class TestQuotasAndUsage(unittest.TestCase):
    """Core function 4: Usage metering & quotas."""

    def setUp(self):
        self.store, self.audit, _ = make_store()

    def test_set_and_get_quota(self):
        """Core 4: set_quota returns {owner, token_limit, updated_utc};
        get_quota returns it to the owner and to an admin."""
        quota = self.store.set_quota("bob", 500, ADMIN)
        self.assertEqual(
            set(quota.keys()), {"owner", "token_limit", "updated_utc"}
        )
        self.assertEqual(quota["token_limit"], 500)
        self.assertEqual(self.store.get_quota("bob", MEMBER)["token_limit"], 500)
        self.assertEqual(self.store.get_quota("bob", ADMIN)["token_limit"], 500)

    def test_get_quota_none_when_unset(self):
        """Core 4: get_quota returns None when no quota was set."""
        self.assertIsNone(self.store.get_quota("bob", MEMBER))

    def test_set_quota_replaces(self):
        """Core 4: one quota per owner; setting replaces."""
        self.store.set_quota("bob", 100, ADMIN)
        replaced = self.store.set_quota("bob", 250, ADMIN)
        self.assertEqual(replaced["token_limit"], 250)
        self.assertEqual(self.store.get_quota("bob", ADMIN)["token_limit"], 250)

    def test_set_quota_validation(self):
        """Core 4 (SI-10): token_limit must be a positive integer,
        else ValidationError."""
        for bad in (0, -5, "100", 2.5, True, None):
            with self.subTest(limit=bad):
                with self.assertRaises(ValidationError):
                    self.store.set_quota("bob", bad, ADMIN)

    def test_set_quota_admin_only(self):
        """Core 4 + 9: set_quota is the 'admin' action — a member
        setting a quota raises PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.store.set_quota("bob", 100, MEMBER)

    def test_get_quota_and_usage_owner_or_admin_only(self):
        """Core 4: get_quota / usage_for are owner-or-admin; another
        member gets PermissionDenied."""
        self.store.set_quota("bob", 100, ADMIN)
        with self.assertRaises(PermissionDenied):
            self.store.get_quota("bob", OTHER_MEMBER)
        with self.assertRaises(PermissionDenied):
            self.store.usage_for("bob", OTHER_MEMBER)

    def test_usage_for_aggregates_current_month(self):
        """Core 4: usage_for returns {owner, month, prompt_tokens,
        completion_tokens, total_tokens, requests} aggregated over
        the current UTC month's request records."""
        self.store.invoke("echoer", "abcd", MEMBER)       # 1 + 1 tokens
        self.store.invoke("echoer", "abcdefgh", MEMBER)   # 2 + 2 tokens
        usage = self.store.usage_for("bob", MEMBER)
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        self.assertEqual(usage["owner"], "bob")
        self.assertEqual(usage["month"], month)
        self.assertEqual(usage["prompt_tokens"], 3)
        self.assertEqual(usage["completion_tokens"], 3)
        self.assertEqual(usage["total_tokens"], 6)
        self.assertEqual(usage["requests"], 2)

    def test_usage_for_empty_is_zeroes(self):
        """Core 4: an owner with no invocations has zero usage."""
        usage = self.store.usage_for("dave", OTHER_MEMBER)
        self.assertEqual(usage["total_tokens"], 0)
        self.assertEqual(usage["requests"], 0)

    def test_quota_exceeded_refuses_before_running(self):
        """Core 4 / invoke step 5: a request whose prompt estimate
        would exceed the quota raises QuotaExceeded; nothing is
        stored and no responder runs."""
        self.store.set_quota("bob", 3, ADMIN)
        self.store.invoke("echoer", "abcd", MEMBER)  # total 2, allowed
        with self.assertRaises(QuotaExceeded):
            # estimate("abcd")=1; 2 used + 1 <= 3 would pass, so use a
            # prompt whose estimate alone pushes past the limit:
            self.store.invoke("echoer", "abcdefghijkl", MEMBER)  # est 3; 2+3>3
        records = self.store.list_requests(MEMBER)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "completed")

    def test_quota_exact_limit_is_allowed(self):
        """Core 4 / invoke step 5: 'would exceed' is strict — usage
        landing exactly on the limit is allowed."""
        self.store.set_quota("bob", 2, ADMIN)
        record = self.store.invoke("echoer", "abcd", MEMBER)  # est 1; 0+1<=2
        self.assertEqual(record["status"], "completed")
        # total_tokens now 2; next prompt estimate 1 would exceed.
        with self.assertRaises(QuotaExceeded):
            self.store.invoke("echoer", "abcd", MEMBER)

    def test_quota_charged_to_key_owner(self):
        """Core 4 / invoke step 5: when key_id is given, the quota
        owner is the key's owner, not necessarily the actor (an admin
        invoking with bob's key is charged to bob)."""
        key = self.store.create_api_key("bob", MEMBER)
        self.store.set_quota("bob", 1, ADMIN)
        with self.assertRaises(QuotaExceeded):
            self.store.invoke("echoer", "abcdefgh", ADMIN, key_id=key["id"])
        self.assertEqual(self.store.list_requests(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
