"""Append-only audit log tests.

Traces to: Core function 10 (Audit log, AU-2/AU-3/AU-9) -- a baseline
hook with 0/5 descriptive claims in the union spec, included because
the L2/Moderate baseline requires it. Carried-not-claimed.
"""

import os
import unittest

from health_helpers import ADMIN, CLINICIAN, MEMBER, fresh_store, make_store
from health.audit import AuditLog
from health.errors import PermissionDenied

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRATCH = os.path.join(_GROUP_ROOT, "scratch")


class TestAuditLog(unittest.TestCase):
    """Core 10 (AU-2/AU-3): audit entry shape and append-only behaviour."""

    def test_entry_keys_and_actor_normalisation(self):
        """Core 10 (AU-3): entries carry ts/actor/action/target/details plus [L3] the hash-chain fields seq/prev_hash/hash; a User actor is normalised to its name."""
        log = AuditLog()
        entry = log.record(ADMIN, "program_create", "prg-1", details={"title": "X"})
        self.assertTrue({"ts", "actor", "action", "target", "details"} <= set(entry))
        self.assertTrue({"seq", "prev_hash", "hash"} <= set(entry))
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(log.entries()[0]["action"], "program_create")

    def test_append_only_copies(self):
        """Core 10 (AU-9): entries() returns copies; mutating them does not alter the log, and there is no mutation API."""
        log = AuditLog()
        log.record("alice", "a", "t")
        copied = log.entries()
        copied[0]["action"] = "tampered"
        self.assertEqual(log.entries()[0]["action"], "a")
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))
        self.assertFalse(hasattr(log, "clear"))

    def test_jsonl_persistence_reload(self):
        """Core 10 (AU-2): JSONL persistence in group scratch/ reloads on construction; malformed lines are skipped."""
        path = os.path.join(_SCRATCH, "audit-test.jsonl")
        if os.path.exists(path):
            os.remove(path)
        log = AuditLog(path=path)
        log.record("alice", "program_create", "prg-1")
        log.record("bob", "enrollment_create", "enr-1")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("not-json\n")
        reloaded = AuditLog(path=path)
        self.assertEqual(len(reloaded.entries()), 2)
        self.assertEqual(reloaded.entries()[1]["actor"], "bob")
        os.remove(path)

    def test_store_records_mutations(self):
        """Core 10 (AU-2): the store records each successful mutation action."""
        audit = AuditLog()
        store, program, participant = make_store(audit=audit)
        store.create_enrollment(participant["id"], program["id"], CLINICIAN)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("program_create", actions)
        self.assertIn("participant_create", actions)
        self.assertIn("enrollment_create", actions)

    def test_failed_ops_record_nothing(self):
        """Core 10 / SI-10: a denied store op records no mutation entry."""
        audit = AuditLog()
        store, _, _ = make_store(audit=audit)
        before = len(audit.entries())
        with self.assertRaises(PermissionDenied):
            store.create_program("Nope", MEMBER)
        self.assertEqual(len(audit.entries()), before)

    def test_report_and_scorecard_reads_audited(self):
        """Core 10 / Core 8 (AU-2): report and scorecard reads are audited by the store."""
        audit = AuditLog()
        store, program, _ = make_store(audit=audit)
        store.report(ADMIN, as_of="2026-06-15")
        store.scorecard(program["id"], ADMIN, as_of="2026-06-15")
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("report", actions)
        self.assertIn("scorecard", actions)


if __name__ == "__main__":
    unittest.main()
