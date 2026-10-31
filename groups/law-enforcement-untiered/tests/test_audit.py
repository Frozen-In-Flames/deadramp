"""Append-only audit log.

Traces to: Core 11 (Audit log) and the AU control family in
UNION-SPEC.md -- entry shape, append-only behavior, JSONL persistence
and reload, the store recording every contract mutation action name,
and failed operations recording nothing.
"""

import os
import unittest

from lawenf.audit import AuditLog
from lawenf.errors import ValidationError
from lawenf_helpers import MEMBER, fresh_store, make_store

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scratch")


class TestAuditLog(unittest.TestCase):
    """Core 11: entries carry ts/actor/action/target/details."""

    def test_entry_shape_and_actor_normalization(self):
        log = AuditLog()
        entry = log.record(MEMBER, "matter_create", "mat-1")
        self.assertEqual(set(entry.keys()), {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "bob")
        self.assertEqual(entry["action"], "matter_create")
        self.assertIsNone(entry["details"])

    def test_entries_returns_copies(self):
        log = AuditLog()
        log.record("bob", "x", "y")
        got = log.entries()
        got[0]["action"] = "tampered"
        self.assertEqual(log.entries()[0]["action"], "x")

    def test_jsonl_persistence_and_reload(self):
        path = os.path.join(SCRATCH, "audit-test.jsonl")
        if os.path.exists(path):
            os.remove(path)
        log = AuditLog(path=path)
        log.record("bob", "matter_create", "mat-1")
        log.record("bob", "source_create", "src-1")
        reloaded = AuditLog(path=path)
        self.assertEqual([e["action"] for e in reloaded.entries()],
                         ["matter_create", "source_create"])


class TestStoreAuditing(unittest.TestCase):
    """Core 11: the store records each contract mutation action."""

    def test_mutation_action_names(self):
        store, audit, matter = make_store()
        mid = matter["id"]
        src = store.create_source(mid, "SRC-1", "statute", MEMBER)
        doc = store.register_document(mid, "DOC-1", "a" * 64, 10, MEMBER)
        store.begin_review(mid, doc["id"], MEMBER)
        store.save_search(mid, "SEA-1", "b" * 64, 3, MEMBER)
        store.add_annotation(mid, "source", src["id"], "ANN-1", "c" * 64, MEMBER)
        store.record_citation_check(mid, "CIT-1", "followed", MEMBER)
        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(actions, [
            "matter_create", "member_add", "source_create",
            "document_register", "document_begin_review", "search_save",
            "annotation_add", "citation_check_record",
        ])

    def test_failed_operations_record_nothing(self):
        store, audit, matter = make_store()
        before = len(audit.entries())
        with self.assertRaises(ValidationError):
            store.create_source(matter["id"], "SRC-X", "not-a-kind", MEMBER)
        self.assertEqual(len(audit.entries()), before)


if __name__ == "__main__":
    unittest.main()
