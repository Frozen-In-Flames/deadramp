"""Audit-log tests.

Traces to: Core function 12 -- Append-only audit log; contract for
``contact/audit.py`` and store audit action names; AU-2/AU-3/AU-6/AU-9.
JSONL persistence files live in the group ``scratch/`` directory.
"""

import json
import os
import unittest
from datetime import datetime

from contact_helpers import ADMIN, OPERATOR, fresh_store, make_store
from contact.audit import AuditLog

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch")


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLog(unittest.TestCase):
    """Core 12: Audit log -- record()/entries() contract."""

    def test_record_roundtrip(self):
        """Core 12: Audit log. entries() returns {ts, actor, action, target, details}."""
        log = AuditLog()
        log.record("alice", "agent_create", "agt-1", {"name": "Dana"})
        e = log.entries()[0]
        self.assertEqual(set(e.keys()), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(e["actor"], "alice")
        self.assertEqual(e["action"], "agent_create")
        self.assertEqual(e["target"], "agt-1")
        self.assertEqual(e["details"], {"name": "Dana"})
        _parse_ts(e["ts"])

    def test_actor_user_object_normalised_to_name(self):
        """Core 12: Audit log. A User actor is recorded as its name string."""
        log = AuditLog()
        log.record(ADMIN, "rule_create", "rule-1")
        self.assertEqual(log.entries()[0]["actor"], "alice")

    def test_details_default_and_order_and_append_only(self):
        """Core 12: Audit log (AU-2/AU-9). Order preserved, earlier entries unchanged, no mutation API."""
        log = AuditLog()
        log.record("alice", "agent_create", "agt-1")
        snap = dict(log.entries()[0])
        self.assertIn(log.entries()[0]["details"], (None, {}))
        log.record("bob", "search", "search")
        self.assertEqual(len(log.entries()), 2)
        self.assertEqual(log.entries()[0], snap)
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))

    def test_entries_are_copies(self):
        """Core 12: Audit log (AU-9). Mutating a returned entry does not mutate the log."""
        log = AuditLog()
        log.record("alice", "agent_create", "agt-1", {"a": 1})
        log.entries()[0]["action"] = "hacked"
        self.assertEqual(log.entries()[0]["action"], "agent_create")

    def test_empty(self):
        """Core 12: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_jsonl_persistence_and_reload(self):
        """Core 12: Audit log. JSONL persistence with reload on construction."""
        os.makedirs(SCRATCH, exist_ok=True)
        path = os.path.join(SCRATCH, "test_audit.jsonl")
        if os.path.exists(path):
            os.remove(path)
        try:
            log = AuditLog(path)
            log.record("alice", "agent_create", "agt-1")
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
    """Core 12: Audit log -- store records each mutation action."""

    def test_store_records_mutations(self):
        """Core 12: Audit log. agent_create/contact_create/queue_create/queue_add_agent are recorded."""
        audit = AuditLog()
        make_store(audit=audit)
        actions = [e["action"] for e in audit.entries()]
        for expected in ("agent_create", "contact_create", "queue_create", "queue_add_agent"):
            self.assertIn(expected, actions)

    def test_all_mutation_action_names(self):
        """Core 12: Audit log. Every contract mutation action name is recorded by its operation."""
        audit = AuditLog()
        store, agent, contact, queue = make_store(audit=audit)
        case = store.create_case(OPERATOR, "inquiry", "Help", contact_id=contact["id"])
        store.assign_case(case["id"], OPERATOR, agent_id=agent["id"])
        store.transition_case(case["id"], OPERATOR, "in_progress")
        cb = store.schedule_callback(OPERATOR, contact["id"], "2030-01-01T00:00:00Z")
        store.complete_callback(cb["id"], OPERATOR, outcome="reached")
        cb2 = store.schedule_callback(OPERATOR, contact["id"], "2030-01-02T00:00:00Z")
        store.cancel_callback(cb2["id"], OPERATOR)
        store.record_interaction(OPERATOR, "chat", "inbound", "hi", case_id=case["id"])
        alert = store.raise_alert(OPERATOR, "warning", "slow queue")
        store.acknowledge_alert(alert["id"], OPERATOR)
        store.resolve_alert(alert["id"], OPERATOR)
        store.create_rule(ADMIN, "r1", "all", "c", "a")
        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "case_create", "case_assign", "case_transition",
            "callback_create", "callback_complete", "callback_cancel",
            "interaction_record", "alert_raise", "alert_ack", "alert_resolve",
            "rule_create",
        ):
            self.assertIn(expected, actions)

    def test_search_is_audited(self):
        """Core 12: Audit log. search records a 'search' entry."""
        audit = AuditLog()
        store, agent, contact, queue = make_store(audit=audit)
        store.search("casey", OPERATOR)
        self.assertIn("search", [e["action"] for e in audit.entries()])

    def test_failed_op_records_nothing(self):
        """Core 12: Audit log / SI-10. A failed validation records no audit entry."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        try:
            store.create_agent("", OPERATOR)
        except Exception:
            pass
        self.assertEqual(audit.entries(), [])


if __name__ == "__main__":
    unittest.main()
