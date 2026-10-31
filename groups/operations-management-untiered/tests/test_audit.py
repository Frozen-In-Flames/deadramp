"""Audit-log tests.

Traces to: Core function 12 -- Append-only audit log; contract for
``opsmgmt/audit.py`` and store audit action names; AU-2/AU-3/AU-6/AU-9.
JSONL persistence files live in the group ``scratch/`` directory.
"""

import json
import os
import unittest
from datetime import datetime

from opsmgmt_helpers import ADMIN, OPERATOR, fresh_store, make_store
from opsmgmt.audit import AuditLog

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch")


def _parse_ts(ts):
    """Core 12: Audit log -- parse an entry timestamp."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLog(unittest.TestCase):
    """Core 12: Audit log -- record()/entries() contract."""

    def test_record_roundtrip(self):
        """Core 12: Audit log. entries() returns {ts, actor, action, target, details}."""
        log = AuditLog()
        log.record("alice", "person_create", "per-1", {"name": "Pat"})
        e = log.entries()[0]
        self.assertEqual(set(e.keys()), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(e["actor"], "alice")
        self.assertEqual(e["action"], "person_create")
        self.assertEqual(e["target"], "per-1")
        self.assertEqual(e["details"], {"name": "Pat"})
        _parse_ts(e["ts"])

    def test_actor_user_object_normalised_to_name(self):
        """Core 12: Audit log. A User actor is recorded as its name string."""
        log = AuditLog()
        log.record(ADMIN, "workflow_create", "wf-1")
        self.assertEqual(log.entries()[0]["actor"], "alice")

    def test_details_default_and_order_and_append_only(self):
        """Core 12: Audit log (AU-2/AU-9). Order preserved, earlier entries unchanged, no mutation API."""
        log = AuditLog()
        log.record("alice", "person_create", "per-1")
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
        log.record("alice", "person_create", "per-1", {"a": 1})
        log.entries()[0]["action"] = "hacked"
        log.entries()[0]["details"]["a"] = 99
        self.assertEqual(log.entries()[0]["action"], "person_create")
        self.assertEqual(log.entries()[0]["details"], {"a": 1})

    def test_empty(self):
        """Core 12: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_jsonl_persistence_and_reload(self):
        """Core 12: Audit log. JSONL persistence with reload on construction (in group scratch/)."""
        os.makedirs(SCRATCH, exist_ok=True)
        path = os.path.join(SCRATCH, "test_audit.jsonl")
        if os.path.exists(path):
            os.remove(path)
        try:
            log = AuditLog(path)
            log.record("alice", "person_create", "per-1")
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
        """Core 12: Audit log. person_create/organization_create/project_create/project_add_person are recorded."""
        audit = AuditLog()
        make_store(audit=audit)
        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "person_create", "organization_create", "project_create", "project_add_person",
        ):
            self.assertIn(expected, actions)

    def test_all_mutation_action_names(self):
        """Core 12: Audit log. Every contract mutation action name is recorded by its operation."""
        audit = AuditLog()
        store, person, organization, project = make_store(audit=audit)
        asset = store.create_asset("Pump", OPERATOR, project_id=project["id"])
        store.transition_asset(asset["id"], OPERATOR, "in_maintenance")
        wo = store.create_work_order(
            OPERATOR, "maintenance", "Fix pump", project_id=project["id"],
            asset_id=asset["id"], person_id=person["id"])
        store.assign_work_order(wo["id"], OPERATOR, person_id=person["id"])
        store.transition_work_order(wo["id"], OPERATOR, "in_progress")
        store.record_inspection(
            OPERATOR, "Checked pump", asset_id=asset["id"], outcome="pass")
        store.record_usage(OPERATOR, project["id"], "hours", 3, "2026-10")
        wf = store.create_workflow(ADMIN, "wf1", "all", "on create", "notify")
        store.update_workflow(wf["id"], ADMIN, trigger_text="on update")
        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "asset_create", "asset_transition",
            "work_order_create", "work_order_assign", "work_order_transition",
            "inspection_record", "usage_record",
            "workflow_create", "workflow_update",
        ):
            self.assertIn(expected, actions)

    def test_search_is_audited(self):
        """Core 12: Audit log. search records a 'search' entry."""
        audit = AuditLog()
        store, person, organization, project = make_store(audit=audit)
        store.search("pat", OPERATOR)
        self.assertIn("search", [e["action"] for e in audit.entries()])

    def test_failed_op_records_nothing(self):
        """Core 12: Audit log / SI-10. A failed validation records no audit entry."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        try:
            store.create_person("", OPERATOR)
        except Exception:
            pass
        self.assertEqual(audit.entries(), [])
        try:
            store.create_work_order(OPERATOR, "bogus", "s")
        except Exception:
            pass
        self.assertEqual(audit.entries(), [])


if __name__ == "__main__":
    unittest.main()
