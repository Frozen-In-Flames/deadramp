import json
import os
import tempfile
import unittest

from talentdev.audit import AuditLog, actor_name
from talentdev_helpers import ADMIN


class TestAudit(unittest.TestCase):
    def test_append_only_entries(self):
        log = AuditLog()
        first = log.record(ADMIN, "create_program", "prg-1", {"kind": "x"})
        second = log.record("bob", "enroll", "enr-1")
        entries = log.entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["actor"], "alice")
        self.assertEqual(entries[0]["action"], "create_program")
        self.assertEqual(entries[0]["target"], "prg-1")
        self.assertEqual(entries[0]["details"], {"kind": "x"})
        self.assertIsNone(entries[1]["details"])
        self.assertIn("ts", first)
        self.assertEqual(second["actor"], "bob")

    def test_jsonl_persistence_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path)
            log.record(ADMIN, "record_snapshot", "ins-1")
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(len(lines), 1)
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 1)
            self.assertEqual(reloaded.entries()[0]["target"], "ins-1")

    def test_actor_name(self):
        self.assertEqual(actor_name(ADMIN), "alice")
        self.assertEqual(actor_name("carol"), "carol")
        self.assertIsNone(actor_name(None))


if __name__ == "__main__":
    unittest.main()
