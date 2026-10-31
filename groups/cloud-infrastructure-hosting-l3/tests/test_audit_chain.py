"""[L3] AU-9 / AU-3: the audit hash chain.

Every entry carries seq / prev_hash / hash; the hash is the
SHA-256 of the canonical JSON of the entry's hashed fields,
recomputed independently here with hashlib; verify_chain()
localizes tampering at the first bad index; the chain survives a
JSONL round trip and detects an edited line after reload; and
GET /audit/verify exposes the result (admin and auditor may read
it; member may not).
"""

import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest

import cloudinfra_helpers as H
from cloudinfra.audit import GENESIS_PREV_HASH, AuditLog
from cloudinfra.service import USERS, make_server
from cloudinfra.store import CloudInfraStore


def _independent_hash(entry):
    payload = {
        "seq": entry["seq"],
        "ts": entry["ts"],
        "actor": entry["actor"],
        "action": entry["action"],
        "target": entry["target"],
        "details": entry["details"],
        "prev_hash": entry["prev_hash"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def call(port, method, path, user=None, role=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Content-Type": "application/json"}
    if user is not None:
        headers["X-User"] = user
    if role is not None:
        headers["X-Role"] = role
    conn.request(method, path,
                 body=json.dumps(body) if body is not None else None,
                 headers=headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(raw) if raw else {}


class TestHashChainFields(unittest.TestCase):
    def setUp(self):
        self.log = AuditLog()
        self.log.record("alice", "organization_create", "org-1", {"a": 1})
        self.log.record("bob", "tenancy_create", "ten-1")
        self.log.record("alice", "deployment_status", "dep-1",
                        {"status": "active"})

    def test_chain_fields_present_and_sequential(self):
        entries = self.log.entries()
        self.assertEqual([e["seq"] for e in entries], [0, 1, 2])
        self.assertEqual(entries[0]["prev_hash"], GENESIS_PREV_HASH)
        self.assertEqual(entries[0]["prev_hash"], "0" * 64)
        self.assertEqual(entries[1]["prev_hash"], entries[0]["hash"])
        self.assertEqual(entries[2]["prev_hash"], entries[1]["hash"])

    def test_hash_is_sha256_of_canonical_json(self):
        for entry in self.log.entries():
            self.assertEqual(entry["hash"], _independent_hash(entry))

    def test_verify_chain_ok_on_clean_log(self):
        self.assertEqual(self.log.verify_chain(), (True, None))

    def test_verify_chain_ok_on_empty_log(self):
        self.assertEqual(AuditLog().verify_chain(), (True, None))


class TestHashChainTamper(unittest.TestCase):
    def setUp(self):
        self.log = AuditLog()
        self.log.record("alice", "organization_create", "org-1")
        self.log.record("bob", "tenancy_create", "ten-1")
        self.log.record("alice", "deployment_status", "dep-1")

    def test_in_place_edit_localized(self):
        self.log._entries[1]["action"] = "tampered"
        self.assertEqual(self.log.verify_chain(), (False, 1))

    def test_stripped_hash_field_fails(self):
        del self.log._entries[2]["hash"]
        self.assertEqual(self.log.verify_chain(), (False, 2))

    def test_deleted_entry_fails_at_the_gap(self):
        del self.log._entries[1]
        self.assertEqual(self.log.verify_chain(), (False, 1))

    def test_rewritten_prev_hash_fails(self):
        self.log._entries[2]["prev_hash"] = "f" * 64
        self.assertEqual(self.log.verify_chain(), (False, 2))


class TestHashChainPersistence(unittest.TestCase):
    def test_jsonl_round_trip_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path=path)
            log.record(H.ADMIN, "organization_create", "org-1")
            log.record("bob", "deployment_status", "dep-1")
            reloaded = AuditLog(path=path)
            self.assertEqual(reloaded.verify_chain(), (True, None))
            self.assertEqual(
                [e["hash"] for e in reloaded.entries()],
                [e["hash"] for e in log.entries()])

    def test_edited_jsonl_line_fails_verification_after_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path=path)
            log.record("alice", "organization_create", "org-1")
            log.record("bob", "tenancy_create", "ten-1")
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            edited = json.loads(lines[1])
            edited["action"] = "forged"
            lines[1] = json.dumps(edited)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            reloaded = AuditLog(path=path)
            self.assertEqual(reloaded.verify_chain(), (False, 1))


class TestAuditVerifyEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = CloudInfraStore(audit=cls.audit)
        cls.server = make_server("127.0.0.1", 0, cls.store, cls.audit,
                                 dict(USERS))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_verify_endpoint_reports_ok_and_pre_request_count(self):
        call(self.port, "POST", "/organizations", user="alice",
             role="admin", body={"org_ref": "org-verify", "label": "V"})
        before = len(self.audit.entries())
        status, body = call(self.port, "GET", "/audit/verify",
                            user="alice", role="admin")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True, "entries": before,
                                "first_bad_index": None})

    def test_verify_endpoint_allows_auditor(self):
        status, body = call(self.port, "GET", "/audit/verify",
                            user="dana", role="auditor")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_verify_endpoint_denies_member(self):
        status, _ = call(self.port, "GET", "/audit/verify",
                         user="bob", role="member")
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
