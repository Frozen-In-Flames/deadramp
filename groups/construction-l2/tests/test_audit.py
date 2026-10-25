"""Audit-log tests.

Traces to: Core function -- Append-only audit log; contract for
``construct/audit.py`` and store audit action names; AU-2/AU-3/AU-6/AU-9.
JSONL persistence files live in the group ``scratch/`` directory.
"""

import json
import os
import unittest
from datetime import datetime

from construct_helpers import ADMIN, OPERATOR, fresh_store, make_store
from construct.audit import AuditLog

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch")


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLog(unittest.TestCase):
    """Audit log: record()/entries() contract."""

    def test_record_roundtrip(self):
        """Audit log. entries() returns {ts, actor, action, target, details}."""
        log = AuditLog()
        log.record("alice", "org_create", "org-1", {"name": "Prime"})
        e = log.entries()[0]
        self.assertEqual(set(e.keys()), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(e["actor"], "alice")
        self.assertEqual(e["action"], "org_create")
        self.assertEqual(e["target"], "org-1")
        self.assertEqual(e["details"], {"name": "Prime"})
        _parse_ts(e["ts"])

    def test_actor_user_object_normalised_to_name(self):
        """Audit log. A User actor is recorded as its name string."""
        log = AuditLog()
        log.record(ADMIN, "org_create", "org-1")
        self.assertEqual(log.entries()[0]["actor"], "alice")

    def test_details_default_and_order_and_append_only(self):
        """Audit log (AU-2/AU-9). Order preserved, earlier entries unchanged, no mutation API."""
        log = AuditLog()
        log.record("alice", "org_create", "org-1")
        snap = dict(log.entries()[0])
        self.assertIn(log.entries()[0]["details"], (None, {}))
        log.record("bob", "search", "search")
        self.assertEqual(len(log.entries()), 2)
        self.assertEqual(log.entries()[0], snap)
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))

    def test_entries_are_copies(self):
        """Audit log (AU-9). Mutating a returned entry does not mutate the log."""
        log = AuditLog()
        log.record("alice", "org_create", "org-1", {"a": 1})
        log.entries()[0]["action"] = "hacked"
        self.assertEqual(log.entries()[0]["action"], "org_create")

    def test_empty(self):
        """Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_jsonl_persistence_and_reload(self):
        """Audit log. JSONL persistence with reload on construction."""
        os.makedirs(SCRATCH, exist_ok=True)
        path = os.path.join(SCRATCH, "test_audit.jsonl")
        if os.path.exists(path):
            os.remove(path)
        try:
            log = AuditLog(path)
            log.record("alice", "org_create", "org-1")
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
    """Audit log: store records each mutation action."""

    def test_store_records_mutations(self):
        """Audit log. org_create/project_create/project_transition/participant_add are recorded."""
        audit = AuditLog()
        make_store(audit=audit)
        actions = [e["action"] for e in audit.entries()]
        for expected in ("org_create", "project_create", "project_transition", "participant_add"):
            self.assertIn(expected, actions)

    def test_all_mutation_action_names(self):
        """Audit log. Every contract mutation action name is recorded by its operation."""
        audit = AuditLog()
        store, project, prime, sub = make_store(audit=audit)
        pid = project["id"]
        doc = store.create_document(OPERATOR, "Spec", project_id=pid)
        store.update_document(doc["id"], OPERATOR, note="rev")
        con = store.create_contract(OPERATOR, "Main contract", pid)
        store.transition_contract(con["id"], OPERATOR, "in_review")
        subt = store.create_submittal(OPERATOR, pid, "Steel submittal")
        store.transition_submittal(subt["id"], OPERATOR, "submitted")
        rfi = store.create_rfi(OPERATOR, pid, "Which steel?")
        store.transition_rfi(rfi["id"], OPERATOR, "answered")
        ms = store.create_milestone(OPERATOR, pid, "Topping out", "2030-01-01T00:00:00Z")
        store.complete_milestone(ms["id"], OPERATOR)
        dsp = store.create_dispatch(OPERATOR, pid, "Pour deck")
        store.transition_dispatch(dsp["id"], OPERATOR, "in_progress")
        insp = store.create_inspection(OPERATOR, pid, "framing", result="pass")
        pun = store.create_punch_item(OPERATOR, pid, "Fix paint", inspection_id=insp["id"])
        store.transition_punch_item(pun["id"], OPERATOR, "corrected")
        inc = store.create_incident(OPERATOR, pid, "safety", "Near miss")
        store.transition_incident(inc["id"], OPERATOR, "under_review")
        wrk = store.create_worker(OPERATOR, pid, prime["id"], "W-REF-1", trade="welder")
        store.create_time_entry(OPERATOR, wrk["id"], 60)
        store.create_payroll(OPERATOR, pid, prime["id"],
                             "2025-01-01T00:00:00Z", "2025-01-15T00:00:00Z", certified=True)
        vio = store.create_violation(ADMIN, pid, prime["id"], "wage", "Late pay")
        store.resolve_violation(vio["id"], ADMIN, resolution="paid")
        store.create_cost_entry(OPERATOR, pid, "materials", "Steel", budgeted_cents=100)
        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "document_create", "document_update", "contract_create", "contract_transition",
            "submittal_create", "submittal_transition", "rfi_create", "rfi_transition",
            "milestone_create", "milestone_complete", "dispatch_create", "dispatch_transition",
            "inspection_create", "punch_create", "punch_transition",
            "incident_create", "incident_transition", "worker_create",
            "time_entry_create", "payroll_create", "violation_create", "violation_resolve",
            "cost_create",
        ):
            self.assertIn(expected, actions)

    def test_search_is_audited(self):
        """Audit log. search records a 'search' entry."""
        audit = AuditLog()
        store, project, prime, sub = make_store(audit=audit)
        store.search("prime", OPERATOR)
        self.assertIn("search", [e["action"] for e in audit.entries()])

    def test_failed_op_records_nothing(self):
        """Audit log / SI-10. A failed validation records no audit entry."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        try:
            store.create_org("", OPERATOR)
        except Exception:
            pass
        self.assertEqual(audit.entries(), [])


if __name__ == "__main__":
    unittest.main()
