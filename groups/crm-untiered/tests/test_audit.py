"""Audit log tests.

Traces to: Core 9 (Append-only audit log) -- baseline substrate,
carried not claimed -- and control families AU-2, AU-3, AU-9.
"""

import json
import os
import unittest

import crm_helpers as H
from crm.audit import AuditLog

SCRATCH = os.path.join(H._GROUP_ROOT, "scratch")


class TestAuditLog(unittest.TestCase):
    """Core 9: the AuditLog itself."""

    def test_entry_keys(self):
        """Core 9 (AU-3): entries carry ts/actor/action/target/details."""
        log = AuditLog()
        entry = log.record("alice", "case_create", "case-1", details={"x": 1})
        self.assertEqual(set(entry.keys()),
                         {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["details"], {"x": 1})

    def test_user_actor_normalised(self):
        """Core 9: a User actor is normalised to its name."""
        log = AuditLog()
        entry = log.record(H.ADMIN, "case_create", "case-1")
        self.assertEqual(entry["actor"], "alice")

    def test_append_only_copies(self):
        """Core 9 (AU-9): entries() returns copies; there is no
        mutation API."""
        log = AuditLog()
        log.record("alice", "a", "t")
        entries = log.entries()
        entries[0]["action"] = "tampered"
        entries.append({"fake": True})
        fresh = log.entries()
        self.assertEqual(len(fresh), 1)
        self.assertEqual(fresh[0]["action"], "a")
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))

    def test_jsonl_persistence(self):
        """Core 9: JSONL persistence -- entries written to the file
        are reloaded on construction."""
        path = os.path.join(SCRATCH, "test-audit.jsonl")
        if os.path.exists(path):
            os.remove(path)
        log = AuditLog(path=path)
        log.record("alice", "case_create", "case-1")
        log.record("bob", "case_transition", "case-1")
        with open(path, encoding="utf-8") as fh:
            lines = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(len(lines), 2)
        reloaded = AuditLog(path=path)
        self.assertEqual(len(reloaded.entries()), 2)
        self.assertEqual(reloaded.entries()[1]["actor"], "bob")
        os.remove(path)


class TestStoreAuditing(unittest.TestCase):
    """Core 9: the store records its mutations and nothing else."""

    def test_mutation_actions_recorded(self):
        """Core 9 (AU-2): every contract mutation action name is
        recorded by the store."""
        audit = AuditLog()
        store, account, contact = H.make_store(audit=audit)
        case = store.create_case(H.OPERATOR, "inquiry", "q",
                                 account_id=account["id"])
        store.assign_case(case["id"], H.OPERATOR, "STAFF-1")
        store.transition_case(case["id"], H.OPERATOR, "in_progress")
        store.record_interaction(H.OPERATOR, "chat", "inbound", "s",
                                 case_id=case["id"])
        guide = store.create_guide(H.OPERATOR, "t", "tooltip", "surface:x")
        store.update_guide(guide["id"], H.OPERATOR, enabled=False)
        finding = store.create_finding(H.OPERATOR, "gap")
        store.transition_finding(finding["id"], H.OPERATOR, "acknowledged")
        module = store.create_module(H.ADMIN, "m", "service", "x=1")
        store.update_module(module["id"], H.ADMIN, enabled=False)
        actions = [e["action"] for e in audit.entries()]
        for expected in ("account_create", "contact_create", "case_create",
                         "case_assign", "case_transition", "interaction_record",
                         "guide_create", "guide_update", "finding_create",
                         "finding_transition", "module_create", "module_update"):
            self.assertIn(expected, actions)

    def test_failed_ops_record_nothing(self):
        """Core 9: a failed operation (validation) appends no entry."""
        audit = AuditLog()
        store = H.CrmStore(audit=audit)
        from crm.errors import ValidationError
        with self.assertRaises(ValidationError):
            store.create_case(H.OPERATOR, "ticket", "bad type")
        self.assertEqual(audit.entries(), [])


if __name__ == "__main__":
    unittest.main()
