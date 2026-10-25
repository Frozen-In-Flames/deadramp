"""Audit-log tests.

Traces to: Core function -- Append-only audit log; contract for
``comm/audit.py`` and store audit action names; AU-2/AU-3/AU-6/AU-9.
Uses scratch/ inside the group for JSONL persistence (never /tmp
per house rule for this build's own scratch, though stdlib tempfile
in the group scratch dir is used explicitly here).
"""

import json
import os
import unittest
from datetime import datetime

from comm_helpers import ADMIN, OPERATOR, make_store, fresh_store
from comm.audit import AuditLog

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch")


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLog(unittest.TestCase):
    """Core: Audit log -- record()/entries() contract."""

    def test_record_roundtrip(self):
        """Core: Audit log. entries() returns {ts, actor, action, target, details}."""
        log = AuditLog()
        log.record("alice", "contact_create", "ct-1", {"name": "Dana"})
        e = log.entries()[0]
        self.assertEqual(set(e.keys()), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(e["actor"], "alice")
        self.assertEqual(e["action"], "contact_create")
        self.assertEqual(e["target"], "ct-1")
        self.assertEqual(e["details"], {"name": "Dana"})
        _parse_ts(e["ts"])

    def test_actor_user_object_normalised_to_name(self):
        """Core: Audit log. A User actor is recorded as its name string."""
        log = AuditLog()
        log.record(ADMIN, "channel_create", "ch-1")
        self.assertEqual(log.entries()[0]["actor"], "alice")

    def test_details_default_and_order_and_append_only(self):
        """Core: Audit log (AU-2/AU-9). Order preserved, earlier entries unchanged, details defaults to None/{ }."""
        log = AuditLog()
        log.record("alice", "contact_create", "ct-1")
        snap = dict(log.entries()[0])
        self.assertIn(log.entries()[0]["details"], (None, {}))
        log.record("bob", "search", "search")
        self.assertEqual(len(log.entries()), 2)
        self.assertEqual(log.entries()[0], snap)
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))

    def test_entries_are_copies(self):
        """Core: Audit log (AU-9). Mutating a returned entry does not mutate the log."""
        log = AuditLog()
        log.record("alice", "contact_create", "ct-1", {"a": 1})
        log.entries()[0]["action"] = "hacked"
        self.assertEqual(log.entries()[0]["action"], "contact_create")

    def test_empty(self):
        """Core: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_jsonl_persistence_and_reload(self):
        """Core: Audit log. JSONL persistence with reload on construction."""
        os.makedirs(SCRATCH, exist_ok=True)
        path = os.path.join(SCRATCH, "test_audit.jsonl")
        if os.path.exists(path):
            os.remove(path)
        try:
            log = AuditLog(path)
            log.record("alice", "contact_create", "ct-1")
            log.record("bob", "search", "search")
            with open(path, encoding="utf-8") as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["actor"], "alice")
            reloaded = AuditLog(path)
            self.assertEqual(len(reloaded.entries()), 2)
            self.assertEqual(reloaded.entries()[1]["action"], "search")
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestStoreAuditActions(unittest.TestCase):
    """Core: Audit log -- store records each mutation action."""

    def test_store_records_mutations(self):
        """Core: Audit log. contact_create/group_create/group_add_member/channel_create are recorded."""
        audit = AuditLog()
        make_store(audit=audit)
        actions = [e["action"] for e in audit.entries()]
        for expected in ("contact_create", "group_create", "group_add_member", "channel_create"):
            self.assertIn(expected, actions)

    def test_search_is_audited(self):
        """Core: Audit log. search records a 'search' entry."""
        audit = AuditLog()
        store, contact, group, channel = make_store(audit=audit)
        store.search("dana", OPERATOR)
        self.assertIn("search", [e["action"] for e in audit.entries()])

    def test_failed_op_records_nothing(self):
        """Core: Audit log / SI-10. A failed validation records no audit entry."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        try:
            store.create_contact("", {"email": "x@y.z"}, OPERATOR)
        except Exception:
            pass
        self.assertEqual(audit.entries(), [])


if __name__ == "__main__":
    unittest.main()
