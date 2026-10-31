"""Tamper-evident audit hash-chain tests (L3 High uplift).

Traces to: UNION-SPEC Core function 10 (append-only audit) as
uplifted to the FedRAMP High baseline — AU-9 (protection of audit
information) and AU-3 (content of audit records): every entry
carries ``seq``, ``prev_hash`` and ``hash`` (SHA-256 of the
canonical JSON of {seq, ts, actor, action, target, details,
prev_hash}), and ``AuditLog.verify_chain()`` recomputes the chain.
Includes NEGATIVE CONTROL #2: an in-place mutated entry must be
detected at its index. Also covers the ``GET /audit/verify``
endpoint (service layer).
"""

import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest

import grc_helpers as H
from grc.audit import AuditLog
from grc.service import make_server
from grc.store import GrcStore

GENESIS = "0" * 64


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
        log.record("alice", "op-%d" % i, "find-%d" % i, {"i": i})
    return log


class TestHashChainFields(unittest.TestCase):
    """AU-3 / AU-9: entries carry seq, prev_hash and hash."""

    def test_entries_carry_chain_fields(self):
        """AU-3: every recorded entry gains seq (0-based), prev_hash
        and hash alongside the original ts/actor/action/target/details."""
        entries = _populated_log(3).entries()
        self.assertEqual([e["seq"] for e in entries], [0, 1, 2])
        for entry in entries:
            self.assertEqual(len(entry["hash"]), 64)
            self.assertEqual(len(entry["prev_hash"]), 64)
            int(entry["hash"], 16)  # hex, must not raise
            self.assertEqual(entry["actor"], "alice")

    def test_genesis_prev_hash_is_all_zeros(self):
        """AU-9: the first entry chains from the genesis prev_hash
        "0"*64."""
        entry = _populated_log(1).entries()[0]
        self.assertEqual(entry["prev_hash"], GENESIS)

    def test_hash_is_sha256_of_canonical_json(self):
        """AU-3 / AU-9: hash equals an independent recomputation of
        SHA-256 over the canonical JSON of the hashed fields."""
        for entry in _populated_log(3).entries():
            self.assertEqual(entry["hash"], _expected_hash(entry))

    def test_chain_links_correctly(self):
        """AU-9: each entry's prev_hash equals the previous entry's
        hash, so the trail is one continuous chain."""
        entries = _populated_log(5).entries()
        for previous, current in zip(entries, entries[1:]):
            self.assertEqual(current["prev_hash"], previous["hash"])


class TestVerifyChain(unittest.TestCase):
    """AU-9: verify_chain() detects tampering, at the right index."""

    def test_verify_chain_ok_on_clean_log(self):
        """AU-9: an untouched log verifies: (True, None)."""
        ok, first_bad = _populated_log(4).verify_chain()
        self.assertTrue(ok)
        self.assertIsNone(first_bad)

    def test_verify_chain_ok_on_empty_log(self):
        """AU-9: an empty log is trivially a valid chain."""
        self.assertEqual(AuditLog().verify_chain(), (True, None))

    def test_negative_control_2_mutated_entry_fails_at_index_1(self):
        """NEGATIVE CONTROL #2 (AU-9): mutating a stored entry in
        place — log._entries[1]["actor"] = "mallory" — must make
        verify_chain() report failure at index 1, proving the chain
        detects edits rather than merely existing."""
        log = _populated_log(4)
        self.assertEqual(log.verify_chain(), (True, None))
        log._entries[1]["actor"] = "mallory"
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 1)

    def test_verify_chain_detects_missing_hash_fields(self):
        """AU-9: an entry stripped of its hash fields (e.g. a legacy
        or forged line) fails verification at its own index."""
        log = _populated_log(3)
        del log._entries[2]["hash"]
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 2)

    def test_verify_chain_detects_broken_link(self):
        """AU-9: rewriting an entry's prev_hash breaks the link and
        is detected at that entry."""
        log = _populated_log(3)
        log._entries[2]["prev_hash"] = GENESIS
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 2)


class TestHashChainPersistence(unittest.TestCase):
    """AU-9: the chain survives the JSONL round-trip and detects
    file-level edits after reload."""

    def test_jsonl_roundtrip_verifies_ok(self):
        """AU-9: write entries to JSONL, reload into a new AuditLog,
        and the chain still verifies."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            for i in range(3):
                log.record("alice", "op-%d" % i, "find-1")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 3)
            self.assertEqual(reloaded.verify_chain(), (True, None))
            # The chain continues seamlessly after reload.
            reloaded.record("bob", "finding_transition", "find-1")
            self.assertEqual(reloaded.verify_chain(), (True, None))
            self.assertEqual(reloaded.entries()[3]["seq"], 3)

    def test_edited_jsonl_line_fails_verification_after_reload(self):
        """AU-9: editing one line of the JSONL file (changing the
        actor) is detected after reload, at that line's index."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            for i in range(3):
                log.record("alice", "op-%d" % i, "find-1")
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            forged = json.loads(lines[1])
            forged["actor"] = "mallory"
            lines[1] = json.dumps(forged)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            reloaded = AuditLog(path)
            ok, first_bad = reloaded.verify_chain()
            self.assertFalse(ok)
            self.assertEqual(first_bad, 1)


class TestAuditVerifyEndpoint(unittest.TestCase):
    """AU-9 / AU-6 over HTTP: GET /audit/verify requires audit_read
    and reports {ok, entries, first_bad_index} from verify_chain()."""

    @classmethod
    def setUpClass(cls):
        cls.audit = AuditLog()
        cls.store = GrcStore(audit=cls.audit)
        cls.server = make_server(
            "127.0.0.1", 0, cls.store, cls.audit, dict(H.USERS_REGISTRY))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def _get(self, path, headers):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        return status, json.loads(raw.decode("utf-8"))

    def test_verify_endpoint_reports_clean_chain(self):
        """AU-9: GET /audit/verify on a clean log returns ok=true,
        the entry count, and first_bad_index=null."""
        before = len(self.audit.entries())
        status, payload = self._get(
            "/audit/verify", {"X-User": "alice", "X-Role": "admin"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["first_bad_index"])
        # The count is read before the endpoint's own audit_read
        # entry is appended, so it equals the pre-request length.
        self.assertEqual(payload["entries"], before)

    def test_verify_endpoint_allows_auditor(self):
        """AC-5 / AU-6: the auditor role (audit_read only) may call
        GET /audit/verify."""
        status, payload = self._get(
            "/audit/verify", {"X-User": "dana", "X-Role": "auditor"})
        self.assertEqual(status, 200)
        self.assertIn("ok", payload)

    def test_verify_endpoint_denies_viewer(self):
        """AU-6: a role without audit_read (viewer) gets 403."""
        status, payload = self._get(
            "/audit/verify", {"X-User": "carol", "X-Role": "viewer"})
        self.assertEqual(status, 403)
        self.assertIn("error", payload)

    def test_verify_endpoint_denies_member(self):
        """AU-6: the member role (no audit_read) also gets 403."""
        status, payload = self._get(
            "/audit/verify", {"X-User": "bob", "X-Role": "member"})
        self.assertEqual(status, 403)
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
