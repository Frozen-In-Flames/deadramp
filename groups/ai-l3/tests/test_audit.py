"""Audit-log tests.

Traces to: UNION-SPEC Core function 10 (Audit log); Implementation
contract for ``aigateway/audit.py`` and the store's audit action names;
control families AU-2, AU-3, AU-6, AU-9 (append-only store).
"""

import json
import os
import unittest
from datetime import datetime

from aigateway_helpers import (
    ADMIN,
    MEMBER,
    fresh_store,
    make_scratch_dir,
    make_store,
    remove_scratch_dir,
)
from aigateway.audit import AuditLog
from aigateway.errors import PermissionDenied


def _parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class TestAuditLogInMemory(unittest.TestCase):
    """Core function 10: Audit log — record()/entries() contract."""

    def test_record_and_entries_roundtrip(self):
        """Core 10 / audit contract: entries are dicts with keys
        ts, actor, action, target, details. [L3: the High uplift adds
        the hash-chain fields seq, prev_hash, hash to every entry.]"""
        log = AuditLog()
        log.record("alice", "model_register", "mdl-1", {"name": "echoer"})
        entries = log.entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(
            set(entry.keys()),
            {"ts", "actor", "action", "target", "details",
             "seq", "prev_hash", "hash"},
        )
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "model_register")
        self.assertEqual(entry["target"], "mdl-1")
        self.assertEqual(entry["details"], {"name": "echoer"})

    def test_details_defaults_to_none_or_empty(self):
        """Core 10 / audit contract: record(..., details=None)."""
        log = AuditLog()
        log.record("bob", "invoke", "req-1")
        self.assertIn(log.entries()[0]["details"], (None, {}))

    def test_timestamp_is_parseable_utc(self):
        """Core 10 (AU-3): each entry carries a parseable UTC timestamp."""
        log = AuditLog()
        log.record("alice", "model_register", "mdl-1")
        parsed = _parse_ts(log.entries()[0]["ts"])
        self.assertIsNotNone(parsed.tzinfo)

    def test_entries_preserve_record_order(self):
        """Core 10 (AU-2): the trail is chronological."""
        log = AuditLog()
        for i in range(5):
            log.record("alice", "invoke", "req-%d" % i)
        self.assertEqual(
            [e["target"] for e in log.entries()],
            ["req-0", "req-1", "req-2", "req-3", "req-4"],
        )

    def test_append_only_earlier_entries_never_change(self):
        """Core 10 (AU-9): later records never mutate or drop earlier
        entries."""
        log = AuditLog()
        log.record("alice", "model_register", "mdl-1")
        snapshot = dict(log.entries()[0])
        log.record("alice", "invoke", "req-1")
        log.record("bob", "invoke:denied", "req-2")
        entries = log.entries()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0], snapshot)

    def test_empty_log_has_no_entries(self):
        """Core 10: a fresh log is empty."""
        self.assertEqual(AuditLog().entries(), [])


class TestAuditLogFile(unittest.TestCase):
    """Core function 10: Audit log — JSONL file backing (contract)."""

    def setUp(self):
        self.scratch = make_scratch_dir()
        self.addCleanup(remove_scratch_dir, self.scratch)

    def test_file_backed_log_writes_jsonl(self):
        """Core 10: with a path, each record is one JSON line."""
        path = os.path.join(self.scratch, "audit.jsonl")
        log = AuditLog(path)
        log.record("alice", "model_register", "mdl-1", {"name": "e"})
        log.record("bob", "invoke", "req-1")
        with open(path, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        parsed = [json.loads(ln) for ln in lines]
        self.assertEqual(parsed[0]["actor"], "alice")
        self.assertEqual(parsed[1]["action"], "invoke")

    def test_file_backed_log_reloads_on_construction(self):
        """Core 10 (AU-9): a new AuditLog over the same file reloads
        the prior trail and stays append-only across restarts."""
        path = os.path.join(self.scratch, "audit.jsonl")
        AuditLog(path).record("alice", "model_register", "mdl-1")
        reopened = AuditLog(path)
        self.assertEqual(len(reopened.entries()), 1)
        self.assertEqual(reopened.entries()[0]["target"], "mdl-1")
        reopened.record("alice", "invoke", "req-1")
        self.assertEqual(len(AuditLog(path).entries()), 2)


class TestStoreAuditing(unittest.TestCase):
    """Core function 10: Audit log — the store records each mutation."""

    def test_store_records_full_mutation_flow(self):
        """Core 10: contract action names — model_register,
        template_register, key_create, quota_set, session_create,
        invoke, policy_add, policy_remove, eval_dataset_create,
        eval_run, model_status."""
        store, audit, _ = make_store()
        store.register_template("greet", "Hi {prompt}", ADMIN)
        store.create_api_key("bob", MEMBER)
        store.set_quota("bob", 1000, ADMIN)
        session = store.create_session("chat", MEMBER)
        store.invoke("echoer", "hello", MEMBER, session_id=session["id"])
        rule = store.add_rule("input", "term", "spam", ADMIN)
        store.remove_rule(rule["id"], ADMIN)
        dataset = store.create_eval_dataset(
            "ds", [{"prompt": "hello", "expected": "hello"}], MEMBER
        )
        store.run_eval(dataset["id"], "echoer", MEMBER)
        store.set_model_status("echoer", 1, "deprecated", ADMIN)

        actions = [e["action"] for e in audit.entries()]
        for expected in (
            "model_register", "template_register", "key_create",
            "quota_set", "session_create", "invoke", "policy_add",
            "policy_remove", "eval_dataset_create", "eval_run",
            "model_status",
        ):
            with self.subTest(action=expected):
                self.assertIn(expected, actions)

    def test_store_entries_carry_actor_and_target(self):
        """Core 10 (AU-3): store entries name actor and target id."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        model = store.register_model("solo", "echo", ADMIN)
        entry = audit.entries()[0]
        self.assertEqual(entry["actor"], "alice")
        self.assertEqual(entry["action"], "model_register")
        self.assertEqual(entry["target"], model["id"])

    def test_failed_mutation_records_no_success_action(self):
        """Core 10: the store records *successful* mutations only —
        a viewer's denied register_model adds no model_register entry
        (denials are the HTTP layer's job)."""
        audit = AuditLog()
        store = fresh_store(audit=audit)
        from aigateway_helpers import VIEWER
        with self.assertRaises(PermissionDenied):
            store.register_model("nope", "echo", VIEWER)
        self.assertEqual(audit.entries(), [])

    def test_store_without_audit_log_still_works(self):
        """Core 10: AIGatewayStore(audit=None) — the audit log is
        optional; mutations succeed with none attached."""
        store = fresh_store()
        model = store.register_model("quiet", "echo", ADMIN)
        self.assertEqual(model["id"], "mdl-1")
        record = store.invoke("quiet", "hi", MEMBER)
        self.assertEqual(record["status"], "completed")


if __name__ == "__main__":
    unittest.main()
