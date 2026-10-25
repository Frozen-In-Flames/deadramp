"""Tamper-evident audit hash-chain tests (L3 High uplift).

Traces to: UNION-SPEC Core function 11 (Audit log) as uplifted to the
FedRAMP High baseline -- AU-9 (protection of audit information) and
AU-3 (content of audit records): every entry carries ``seq``,
``prev_hash`` and ``hash`` (SHA-256 of the canonical JSON of
{seq, ts, actor, action, target, details, prev_hash}), and
``AuditLog.verify_chain()`` recomputes the chain, localising the
first bad entry.
"""

import hashlib
import json
import os
import tempfile
import unittest

from collab.audit import AuditLog

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
        log.record("alice", "op-%d" % i, "ws-%d" % i, {"i": i})
    return log


class TestHashChainFields(unittest.TestCase):
    """AU-9/AU-3: chain fields and linkage across several records."""

    def test_chain_linkage_across_several_records(self):
        """AU-9: the genesis entry's prev_hash is "0"*64 and every
        later entry's prev_hash equals the previous entry's hash."""
        entries = _populated_log(5).entries()
        self.assertEqual([e["seq"] for e in entries], [0, 1, 2, 3, 4])
        self.assertEqual(entries[0]["prev_hash"], GENESIS)
        for previous, current in zip(entries, entries[1:]):
            self.assertEqual(current["prev_hash"], previous["hash"])

    def test_hash_is_sha256_of_canonical_json(self):
        """AU-3/AU-9: hash equals an independent recomputation of
        SHA-256 over the canonical JSON of the hashed fields."""
        for entry in _populated_log(3).entries():
            self.assertEqual(len(entry["hash"]), 64)
            int(entry["hash"], 16)  # hex, must not raise
            self.assertEqual(entry["hash"], _expected_hash(entry))


class TestVerifyChain(unittest.TestCase):
    """AU-9: verify_chain() validates a clean log and localises damage."""

    def test_verify_chain_ok_on_clean_log(self):
        """AU-9: an untouched log verifies: (True, None)."""
        self.assertEqual(_populated_log(4).verify_chain(), (True, None))

    def test_verify_chain_ok_on_empty_log(self):
        """AU-9: an empty log is trivially a valid chain."""
        self.assertEqual(AuditLog().verify_chain(), (True, None))

    def test_verify_chain_localizes_in_place_mutation(self):
        """AU-9: mutating a stored entry in place (its actor) is
        detected at exactly that entry's index."""
        log = _populated_log(4)
        self.assertEqual(log.verify_chain(), (True, None))
        log._entries[2]["actor"] = "mallory"
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 2)

    def test_verify_chain_detects_deleted_entry(self):
        """AU-9: deleting an entry from the trail is detected --
        the following entry's seq / prev_hash no longer line up."""
        log = _populated_log(4)
        del log._entries[1]
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 1)

    def test_verify_chain_detects_missing_hash_fields(self):
        """AU-9: an entry stripped of its hash fields fails
        verification at its own index."""
        log = _populated_log(3)
        del log._entries[2]["hash"]
        ok, first_bad = log.verify_chain()
        self.assertFalse(ok)
        self.assertEqual(first_bad, 2)


class TestHashChainPersistence(unittest.TestCase):
    """AU-9: the chain survives the JSONL round-trip and detects
    file-level edits after reload."""

    def test_entries_loaded_from_jsonl_verify(self):
        """AU-9: entries written to a JSONL file and loaded into a
        new AuditLog still verify, and the chain continues after
        reload."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            for i in range(3):
                log.record("alice", "op-%d" % i, "ws-1")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 3)
            self.assertEqual(reloaded.verify_chain(), (True, None))
            reloaded.record("bob", "search", "ws-1")
            self.assertEqual(reloaded.verify_chain(), (True, None))
            self.assertEqual(reloaded.entries()[3]["seq"], 3)

    def test_edited_jsonl_line_detected_after_reload_at_right_index(self):
        """AU-9: editing one line of the JSONL file (changing the
        actor) is detected after reload, at that line's index."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            for i in range(3):
                log.record("alice", "op-%d" % i, "ws-1")
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


if __name__ == "__main__":
    unittest.main()
