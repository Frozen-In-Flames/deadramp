"""Tamper-evident audit hash-chain tests (L3 High uplift).

Traces to: UNION-SPEC.md Core function 12 (Audit log) as uplifted to
the FedRAMP High baseline -- AU-9 (protection of audit information)
and AU-3 (content of audit records): every entry carries ``seq``,
``prev_hash`` and ``hash`` (SHA-256 of the canonical JSON of
{seq, ts, actor, action, target, details, prev_hash}), and
``AuditLog.verify_chain()`` recomputes the chain. Includes the
audit-tamper NEGATIVE CONTROL: an in-place mutated entry must be
detected at exactly its index. Also covers ``GET /audit/verify``.
"""

import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest

from cms_helpers import USERS
from cms.audit import AuditLog
from cms.service import make_server
from cms.store import CmsStore

GENESIS = "0" * 64
ALICE = {"X-User": "alice", "X-Role": "admin"}
DANA = {"X-User": "dana", "X-Role": "auditor"}
BOB = {"X-User": "bob", "X-Role": "publisher"}


def _expected_hash(entry):
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


def _populated_log(n=4):
    log = AuditLog()
    for i in range(n):
        log.record("alice", "op-%d" % i, "ci-%d" % i, {"i": i})
    return log


class TestHashChainFields(unittest.TestCase):
    """[L3] AU-3 / AU-9: entries carry seq, prev_hash and hash."""

    def test_entries_carry_chain_fields(self):
        """[L3] AU-3: every entry has seq/prev_hash/hash alongside the original five keys."""
        log = _populated_log(3)
        for i, entry in enumerate(log.entries()):
            self.assertEqual(entry["seq"], i)
            self.assertEqual(len(entry["prev_hash"]), 64)
            self.assertEqual(len(entry["hash"]), 64)
            for key in ("ts", "actor", "action", "target", "details"):
                self.assertIn(key, entry)

    def test_genesis_prev_hash(self):
        """[L3] AU-9: the first entry's prev_hash is the genesis value "0"*64."""
        log = _populated_log(1)
        self.assertEqual(log.entries()[0]["prev_hash"], GENESIS)

    def test_chain_links(self):
        """[L3] AU-9: each entry's prev_hash equals its predecessor's hash."""
        entries = _populated_log(5).entries()
        for prev, cur in zip(entries, entries[1:]):
            self.assertEqual(cur["prev_hash"], prev["hash"])

    def test_hash_is_sha256_of_canonical_json(self):
        """[L3] AU-9: stored hash recomputes from the canonical payload."""
        for entry in _populated_log(4).entries():
            self.assertEqual(entry["hash"], _expected_hash(entry))

    def test_empty_log_verifies(self):
        """[L3] AU-9: an empty log verifies (True, None)."""
        self.assertEqual(AuditLog().verify_chain(), (True, None))

    def test_clean_log_verifies(self):
        """[L3] AU-9: an untouched populated log verifies (True, None)."""
        self.assertEqual(_populated_log(6).verify_chain(), (True, None))


class TestTamperDetection(unittest.TestCase):
    """[L3] AU-9: verify_chain localizes tampering (negative control)."""

    def test_negative_control_mutated_entry_fails_at_its_index(self):
        """[L3] NEGATIVE CONTROL (AU-9): mutating entry 1's actor in place makes verify_chain report (False, 1); the clean log verifies first."""
        log = _populated_log(4)
        self.assertEqual(log.verify_chain(), (True, None))
        log._entries[1]["actor"] = "mallory"
        self.assertEqual(log.verify_chain(), (False, 1))

    def test_mutated_last_entry_fails_at_last_index(self):
        """[L3] AU-9: tampering with the final entry is localized to its index."""
        log = _populated_log(4)
        log._entries[3]["action"] = "site_delete"
        self.assertEqual(log.verify_chain(), (False, 3))

    def test_stripped_hash_field_detected(self):
        """[L3] AU-9: an entry missing its hash field fails at its index."""
        log = _populated_log(3)
        del log._entries[2]["hash"]
        self.assertEqual(log.verify_chain(), (False, 2))

    def test_rewritten_prev_hash_detected(self):
        """[L3] AU-9: rewriting an entry's prev_hash breaks the link at that index."""
        log = _populated_log(3)
        log._entries[1]["prev_hash"] = "f" * 64
        self.assertEqual(log.verify_chain(), (False, 1))

    def test_deleted_entry_detected(self):
        """[L3] AU-9: deleting a middle entry breaks seq/linkage at the gap."""
        log = _populated_log(4)
        del log._entries[1]
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 1)


class TestChainPersistence(unittest.TestCase):
    """[L3] AU-9: the chain survives JSONL persistence and detects file edits."""

    def test_jsonl_round_trip_verifies(self):
        """[L3] AU-9: a file-backed log reloads with its chain intact."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "site_create", "site-1")
            log.record("bob", "item_create", "ci-1")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 2)
            self.assertEqual(reloaded.verify_chain(), (True, None))

    def test_edited_jsonl_line_detected_after_reload(self):
        """[L3] AU-9: editing one stored JSONL line is detected after reload at that index."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record("alice", "site_create", "site-1")
            log.record("bob", "item_create", "ci-1")
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            entry = json.loads(lines[1])
            entry["actor"] = "mallory"
            lines[1] = json.dumps(entry)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            reloaded = AuditLog(path)
            self.assertEqual(reloaded.verify_chain(), (False, 1))


class TestVerifyEndpoint(unittest.TestCase):
    """[L3] AU-9 / AU-6: GET /audit/verify over HTTP."""

    def setUp(self):
        self.audit = AuditLog()
        self.store = CmsStore(audit=self.audit)
        self.server = make_server("127.0.0.1", 0, self.store, self.audit, dict(USERS))
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _get(self, path, headers):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        parsed = json.loads(resp.read().decode("utf-8"))
        status = resp.status
        conn.close()
        return status, parsed

    def test_verify_endpoint_clean(self):
        """[L3] AU-9: GET /audit/verify as admin reports ok with the pre-request entry count."""
        from cms_helpers import ADMIN
        self.store.create_site(ADMIN, "Main", "main")
        before = len(self.audit.entries())
        status, parsed = self._get("/audit/verify", ALICE)
        self.assertEqual(status, 200)
        self.assertEqual(parsed, {"ok": True, "entries": before, "first_bad_index": None})

    def test_verify_endpoint_auditor_allowed(self):
        """[L3] AC-5 / AU-6: the auditor role (audit_read only) may call /audit/verify."""
        status, parsed = self._get("/audit/verify", DANA)
        self.assertEqual(status, 200)
        self.assertTrue(parsed["ok"])

    def test_verify_endpoint_publisher_denied(self):
        """[L3] AU-6: a role without audit_read (publisher) gets 403 on /audit/verify."""
        status, _ = self._get("/audit/verify", BOB)
        self.assertEqual(status, 403)

    def test_verify_endpoint_reports_tamper(self):
        """[L3] AU-9: after an in-place tamper, /audit/verify reports ok=False at the bad index."""
        from cms_helpers import ADMIN
        self.store.create_site(ADMIN, "Main", "main")
        self.store.create_site(ADMIN, "Two", "two")
        self.audit._entries[1]["actor"] = "mallory"
        status, parsed = self._get("/audit/verify", ALICE)
        self.assertEqual(status, 200)
        self.assertFalse(parsed["ok"])
        self.assertEqual(parsed["first_bad_index"], 1)


if __name__ == "__main__":
    unittest.main()
