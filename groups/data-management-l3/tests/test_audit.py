"""Audit-log tests.

Traces to: Core function -- Append-only audit log; contract for
``datamgmt/audit.py`` and the store audit action names
(dataset_create, dataset_update, schema_update, source_register,
ingestion_record, quality_rule_create, quality_check_run,
access_request, access_decide, grant_revoke, retention_set,
retention_update, export_create, search); AU-2/AU-3/AU-6/AU-9.
JSONL persistence files are written into the group's ``scratch/``
directory via a path relative to this tests directory's parent.
"""

import json
import os
import unittest
from datetime import datetime

from datamgmt_helpers import ADMIN, STEWARD, VIEWER, fresh_store, make_store
from datamgmt.audit import AuditLog

GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(GROUP_ROOT, "scratch")


def _parse_ts(ts):
    """Core: Audit log. Entry timestamps parse as ISO-8601."""
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLog(unittest.TestCase):
    """Core: Audit log -- record()/entries() contract."""

    def test_record_roundtrip(self):
        """Core: Audit log. entries() returns {ts, actor, action, target, details} plus the High-uplift chain fields {seq, prev_hash, hash} (AU-3/AU-9)."""
        log = AuditLog()
        log.record("alice", "dataset_create", "ds-1", {"name": "Claims"})
        e = log.entries()[0]
        self.assertEqual(
            set(e.keys()),
            {"ts", "actor", "action", "target", "details", "seq", "prev_hash", "hash"},
        )
        self.assertEqual(e["actor"], "alice")
        self.assertEqual(e["action"], "dataset_create")
        self.assertEqual(e["target"], "ds-1")
        self.assertEqual(e["details"], {"name": "Claims"})
        _parse_ts(e["ts"])

    def test_actor_user_object_normalised_to_name(self):
        """Core: Audit log. A User actor is recorded as its name string."""
        log = AuditLog()
        log.record(ADMIN, "dataset_create", "ds-1")
        self.assertEqual(log.entries()[0]["actor"], "alice")
        log.record(STEWARD, "search", "search")
        self.assertEqual(log.entries()[1]["actor"], "bob")

    def test_details_default(self):
        """Core: Audit log. details defaults to None or an empty mapping."""
        log = AuditLog()
        log.record("alice", "dataset_create", "ds-1")
        self.assertIn(log.entries()[0]["details"], (None, {}))

    def test_order_preserved_and_append_only(self):
        """Core: Audit log (AU-2/AU-9). Order preserved, earlier entries unchanged, no delete/update API."""
        log = AuditLog()
        log.record("alice", "dataset_create", "ds-1")
        snap = dict(log.entries()[0])
        log.record("bob", "search", "search")
        self.assertEqual(len(log.entries()), 2)
        self.assertEqual(log.entries()[0], snap)
        self.assertEqual(log.entries()[1]["action"], "search")
        self.assertFalse(hasattr(log, "delete"))
        self.assertFalse(hasattr(log, "update"))

    def test_entries_are_copies(self):
        """Core: Audit log (AU-9). Mutating a returned entry does not mutate the log."""
        log = AuditLog()
        log.record("alice", "dataset_create", "ds-1", {"a": 1})
        log.entries()[0]["action"] = "hacked"
        self.assertEqual(log.entries()[0]["action"], "dataset_create")

    def test_empty(self):
        """Core: Audit log. A fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])

    def test_jsonl_persistence_and_reload(self):
        """Core: Audit log. JSONL persistence with reload on construction (group scratch/)."""
        os.makedirs(SCRATCH, exist_ok=True)
        path = os.path.join(SCRATCH, "test_audit_datamgmt.jsonl")
        if os.path.exists(path):
            os.remove(path)
        try:
            log = AuditLog(path)
            log.record("alice", "dataset_create", "ds-1")
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

    def test_make_store_records_dataset_and_source(self):
        """Core: Audit log. dataset_create and source_register are recorded by make_store."""
        audit = AuditLog()
        make_store(audit=audit)
        actions = [e["action"] for e in audit.entries()]
        self.assertIn("dataset_create", actions)
        self.assertIn("source_register", actions)

    def test_store_records_each_mutation_action(self):
        """Core: Audit log. Every contract mutation action is recorded exactly under its pinned name."""
        audit = AuditLog()
        store, dataset, source = make_store(audit=audit)
        store.update_dataset(dataset["id"], STEWARD, description="Updated")
        store.update_schema(
            dataset["id"],
            [{"name": "patient_id", "type": "string", "required": True, "sensitive": True}],
            STEWARD,
        )
        store.record_ingestion(dataset["id"], source["id"], STEWARD, record_count=5)
        rule = store.create_quality_rule(
            dataset["id"], "complete-pid", "completeness", "patient_id", STEWARD
        )
        store.run_quality_check(rule["id"], [{"patient_id": "P1"}], STEWARD)
        req = store.request_access(dataset["id"], "research", VIEWER)
        store.decide_access_request(req["id"], True, STEWARD)
        grants = store.list_grants(dataset_id=dataset["id"], actor=STEWARD)
        store.revoke_grant(grants[0]["id"], STEWARD)
        policy = store.set_retention_policy(dataset["id"], 365, "archive", STEWARD)
        store.update_retention_policy(policy["id"], STEWARD, retention_days=180)
        store.export_dataset(dataset["id"], STEWARD, records=[{"patient_id": "P1"}])
        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "dataset_create", "dataset_update", "schema_update",
            "source_register", "ingestion_record", "quality_rule_create",
            "quality_check_run", "access_request", "access_decide",
            "grant_revoke", "retention_set", "retention_update",
            "export_create",
        ):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)

    def test_search_is_audited(self):
        """Core: Audit log. search records a 'search' entry."""
        audit = AuditLog()
        store, dataset, source = make_store(audit=audit)
        store.search("claims", STEWARD)
        self.assertIn("search", [e["action"] for e in audit.entries()])

    def test_failed_validation_records_nothing(self):
        """Core: Audit log / SI-10. A failed validation records no audit entry."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        try:
            store.create_dataset("Bad", "x", STEWARD, classification="secret")
        except Exception:
            pass
        self.assertEqual(audit.entries(), [])

    def test_failed_permission_records_nothing(self):
        """Core: Audit log / AC-3. A permission-denied write records no audit entry."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        try:
            store.create_dataset("Nope", "x", VIEWER)
        except Exception:
            pass
        self.assertEqual(audit.entries(), [])


if __name__ == "__main__":
    unittest.main()
