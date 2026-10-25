"""Append-only audit log tests.

Traces to: Core function 10 (Audit log, AU-2/AU-3) -- Low-baseline
side only; FAR 52.204-21 carries no audit practice.
"""

import os
import unittest

from devtools_helpers import ADMIN, VIEWER, fresh_store, make_store
from devtools.audit import AuditLog
from devtools.errors import PermissionDenied

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRATCH = os.path.join(_GROUP_ROOT, "scratch")


class TestAuditLog(unittest.TestCase):
    """Core 10 (AU-2/AU-3): audit entry shape, append-only, persistence, denied attempts."""

    def test_entry_keys_and_actor_normalisation(self):
        """Core 10 (AU-3): entries carry ts/actor/action/target/details; User normalised to name."""
        log = AuditLog()
        entry = log.record(ADMIN, "project_create", "prj-1", details={"name": "X"})
        self.assertEqual(set(entry), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "alice")

    def test_append_only_copies(self):
        """Core 10: entries() returns copies; no mutation/deletion API exists."""
        log = AuditLog()
        log.record("alice", "a", "t")
        copied = log.entries()
        copied[0]["action"] = "tampered"
        self.assertEqual(log.entries()[0]["action"], "a")
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))
        self.assertFalse(hasattr(log, "clear"))

    def test_jsonl_persistence_reload(self):
        """Core 10 (AU-2): JSONL persistence in group scratch/ reloads on construction."""
        path = os.path.join(_SCRATCH, "audit-test.jsonl")
        if os.path.exists(path):
            os.remove(path)
        log = AuditLog(path=path)
        log.record("alice", "project_create", "prj-1")
        log.record("bob", "issue_create", "iss-1")
        reloaded = AuditLog(path=path)
        self.assertEqual(len(reloaded.entries()), 2)
        self.assertEqual(reloaded.entries()[1]["actor"], "bob")
        os.remove(path)

    def test_store_records_mutations(self):
        """Core 10 (AU-2): the store records each successful mutation."""
        audit = AuditLog()
        store, project = make_store(audit=audit)
        store.create_issue(project["id"], "Bug", ADMIN)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("project_create", actions)
        self.assertIn("issue_create", actions)

    def test_store_records_denied_attempts(self):
        """Core 10 / Core 9: a denied User attempt is audited with ':denied' suffix."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        with self.assertRaises(PermissionDenied):
            store.create_project("Nope", VIEWER)
        denied = [e for e in audit.entries() if e["action"].endswith(":denied")]
        self.assertEqual(len(denied), 1)
        self.assertEqual(denied[0]["actor"], "carol")
        self.assertEqual(denied[0]["action"], "project_write:denied")


if __name__ == "__main__":
    unittest.main()
