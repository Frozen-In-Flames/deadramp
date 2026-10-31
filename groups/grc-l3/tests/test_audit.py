"""Audit log tests.

Traces to: Core function 10 (append-only audit log — every mutation
and every denied attempt recorded with actor, action, target, and UTC
timestamp); control families AU-2 / AU-3 / AU-6 / AU-9.
"""

import json
import os
import tempfile
import unittest

from grc_helpers import ADMIN, MEMBER, fresh_store, make_store
from grc.audit import AuditLog, actor_name
from grc.access import User
from grc.errors import PermissionDenied


class TestAuditLogUnit(unittest.TestCase):
    """Core 10: the AuditLog itself."""

    def test_entry_keys_and_actor_normalization(self):
        """Core 10 (AU-3 content of audit records). An entry carries
        ts/actor/action/target/details plus, at this tier [L3], the
        hash-chain fields seq/prev_hash/hash (AU-9); a User actor is
        normalized to its name; a string actor passes through; None
        stays None; ts is a UTC ISO-8601 string."""
        log = AuditLog()
        entry = log.record(User("alice", "admin"), "act", "tgt", details={"k": 1})
        self.assertTrue(
            {"ts", "actor", "action", "target", "details",
             "seq", "prev_hash", "hash"} <= set(entry))
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["details"], {"k": 1})
        self.assertTrue(entry["ts"].endswith("+00:00"))
        self.assertEqual(log.record("bob", "a", "t")["actor"], "bob")
        self.assertIsNone(log.record(None, "a", "t")["actor"])
        self.assertEqual(actor_name("carol"), "carol")

    def test_append_only_no_update_or_delete_api(self):
        """Core 10 (AU-9 protection of audit information). The log
        exposes record/entries only — no update, delete, clear, or
        pop surface — and entries() returns copies the caller cannot
        use to rewrite history."""
        log = AuditLog()
        for name in ["update", "delete", "clear", "pop", "remove", "__delitem__"]:
            self.assertFalse(hasattr(log, name), name)
        log.record("alice", "a", "t")
        snapshot = log.entries()
        snapshot[0]["action"] = "forged"
        snapshot.append({"fake": True})
        self.assertEqual(len(log.entries()), 1)
        self.assertEqual(log.entries()[0]["action"], "a")

    def test_jsonl_persistence_and_reload(self):
        """Core 10. With a path, each entry is appended as one JSON
        line, and a new AuditLog on the same path reloads them in
        order."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            log = AuditLog(path=path)
            log.record("alice", "first", "t1")
            log.record("bob", "second", "t2", details={"n": 2})
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual([e["action"] for e in lines], ["first", "second"])
            reloaded = AuditLog(path=path)
            self.assertEqual(
                [e["action"] for e in reloaded.entries()], ["first", "second"]
            )
            reloaded.record("carol", "third", "t3")
            self.assertEqual(len(AuditLog(path=path).entries()), 3)


class TestStoreAuditing(unittest.TestCase):
    """Core 10: the store records every mutation."""

    def test_each_mutation_action_is_recorded(self):
        """Core 10. Each store mutation writes exactly one audit entry
        with its action name and target: framework_create,
        control_create, system_create, indicator_create,
        indicator_result_record, evidence_create, evidence_review,
        finding_create, finding_transition, assessment_create,
        authorization_create, authorization_transition."""
        from grc.audit import AuditLog

        audit = AuditLog()
        store = fresh_store(audit=audit)
        store.create_framework("ORG-FW-1", "One", "1", actor=ADMIN)
        store.create_control("ORG-FW-1", "GV-1", "Governance", actor=ADMIN)
        store.create_system("SYS-001", "label", actor=MEMBER)
        store.create_indicator("KSI-1", "ind", ["AC-2"], actor=MEMBER)
        store.record_indicator_result("KSI-1", "SYS-001", "pass", actor=MEMBER)
        evidence = store.create_evidence("e", "content", [], [], actor=MEMBER)
        store.review_evidence(evidence["id"], "accepted", actor=ADMIN)
        finding = store.create_finding(
            "t", "SYS-001", "high", "src", "2026-06-30", actor=MEMBER
        )
        store.transition_finding(finding["id"], "in_progress", actor=MEMBER)
        store.create_assessment(
            "SYS-001", "ORG-FW-1", "scope", "assessor-1", "2026-09-15", "done",
            actor=MEMBER,
        )
        auth = store.create_authorization("SYS-001", "ORG-FW-1", actor=ADMIN)
        store.transition_authorization(auth["id"], "in_progress", actor=ADMIN)

        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(
            actions,
            [
                "framework_create", "control_create", "system_create",
                "indicator_create", "indicator_result_record",
                "evidence_create", "evidence_review", "finding_create",
                "finding_transition", "assessment_create",
                "authorization_create", "authorization_transition",
            ],
        )
        actors = {e["actor"] for e in audit.entries()}
        self.assertTrue(actors <= {"alice", "bob"})
        self.assertTrue(all(e["target"] for e in audit.entries()))

    def test_transition_details_payload(self):
        """Core 10 (AU-3). A lifecycle transition entry records the
        from/to states in its details."""
        from grc.audit import AuditLog
        from grc_helpers import make_finding

        audit = AuditLog()
        store, _, _ = make_store(audit=audit)
        finding = make_finding(store)
        store.transition_finding(finding["id"], "in_progress", actor=MEMBER)
        transitions = [
            e for e in audit.entries() if e["action"] == "finding_transition"
        ]
        self.assertEqual(len(transitions), 1)
        self.assertEqual(
            transitions[0]["details"], {"from": "open", "to": "in_progress"}
        )
        self.assertEqual(transitions[0]["target"], finding["id"])

    def test_reads_and_failed_ops_write_nothing(self):
        """Core 10. Plain reads write no audit entries, and a failed
        operation (validation error) writes none either — the store
        audits successes only; denials over HTTP are the service
        layer's job (see test_service)."""
        from grc.audit import AuditLog
        from grc.errors import ValidationError

        audit = AuditLog()
        store, system, indicator = make_store(audit=audit)
        baseline = len(audit.entries())
        store.list_frameworks(actor=ADMIN)
        store.list_controls(actor=ADMIN)
        store.get_system("SYS-001", actor=ADMIN)
        store.list_findings(actor=ADMIN)
        with self.assertRaises(ValidationError):
            store.create_system("SYS-001", "duplicate", actor=MEMBER)
        self.assertEqual(len(audit.entries()), baseline)

    def test_denied_attempt_at_store_level_raises_permission_denied(self):
        """Core 10 + Core 9 RBAC. A store-level denial raises
        PermissionDenied (the service layer turns it into an audited
        403; see test_service for the audit-of-denial record)."""
        from grc_helpers import VIEWER

        store, _, _ = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_finding(
                "t", "SYS-001", "high", "src", "2026-06-30", actor=VIEWER
            )


if __name__ == "__main__":
    unittest.main()
