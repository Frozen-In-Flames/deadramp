"""Audit log: traces to AU in the UNION-SPEC baseline."""
import json, tempfile, unittest
from pathlib import Path
from librarysys.audit import AuditLog

class AuditTests(unittest.TestCase):
    def test_append_and_shape(self):
        log = AuditLog(); e = log.record("alice", "item_create", "cat-1")
        self.assertEqual(set(e), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(len(log.entries()), 1)
    def test_append_only_no_mutators(self):
        log = AuditLog()
        self.assertFalse(hasattr(log, "delete")); self.assertFalse(hasattr(log, "update"))
    def test_persistence_reload(self):
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "a.jsonl"); log = AuditLog(p)
            log.record("bob", "loan_record", "lon-1")
            self.assertEqual(len(AuditLog(p).entries()), 1)
            self.assertEqual(json.loads(Path(p).read_text().strip())["action"], "loan_record")
    def test_entries_are_copies(self):
        log = AuditLog(); log.record("a", "x", "y"); log.entries()[0]["action"] = "z"
        self.assertEqual(log.entries()[0]["action"], "x")
if __name__ == "__main__": unittest.main()
