"""Append-only audit log.

Traces to: Core function 13 (Access control & audit) and the AU
control family in UNION-SPEC.md — entry shape is exactly
{ts, actor, action, target, details}; the store records every
successful mutation under the contract's action names; failed
operations record nothing; JSONL persistence reloads on
construction. Denied attempts are the service layer's entries
(suffixed ``:denied``) — covered in test_service.py.
"""

import os
import unittest

import legalpol_helpers as H
from legalpol.audit import AuditLog
from legalpol.errors import ValidationError

SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scratch")


class TestAuditLog(unittest.TestCase):
    """Core 13 / AU-2, AU-3: entries carry ts/actor/action/target/details."""

    def test_entry_shape_and_actor_normalization(self):
        """Core 13: an entry has exactly the five contract keys and
        a User actor is normalized to its name."""
        log = AuditLog()
        entry = log.record(H.MEMBER, "agency_create", "agy-1")
        self.assertEqual(set(entry.keys()),
                         {"ts", "actor", "action", "target", "details"})
        self.assertEqual(entry["actor"], "bob")
        self.assertEqual(entry["action"], "agency_create")
        self.assertIsNone(entry["details"])

    def test_entries_returns_copies(self):
        """Core 13: mutating returned entries does not rewrite history."""
        log = AuditLog()
        log.record("bob", "x", "y")
        got = log.entries()
        got[0]["action"] = "tampered"
        self.assertEqual(log.entries()[0]["action"], "x")

    def test_no_mutation_api(self):
        """Core 13 / AU: the log exposes no update or delete API."""
        self.assertFalse(hasattr(AuditLog, "delete"))
        self.assertFalse(hasattr(AuditLog, "update"))
        self.assertFalse(hasattr(AuditLog, "clear"))

    def test_jsonl_persistence_and_reload(self):
        """Core 13: entries persist as JSONL and reload on construction."""
        path = os.path.join(SCRATCH, "audit-test.jsonl")
        if os.path.exists(path):
            os.remove(path)
        log = AuditLog(path=path)
        log.record("alice", "agency_create", "agy-1")
        log.record("alice", "member_add", "agy-1")
        reloaded = AuditLog(path=path)
        self.assertEqual([e["action"] for e in reloaded.entries()],
                         ["agency_create", "member_add"])
        os.remove(path)


class TestStoreAuditing(unittest.TestCase):
    """Core 13: the store records each contract mutation action."""

    def test_mutation_action_names(self):
        """Core 13 / AU-2: every successful mutation is recorded
        under its contract action name, in order."""
        store, audit, agency = H.make_store()
        aid = agency["id"]
        workspace = H.make_workspace(store, agency)
        session = H.make_session(store, agency, workspace, sandbox=True)
        store.record_execution(aid, session["id"], "EXE-1", H.MEMBER)
        store.register_library_source("LIB-1", "statute", H.MEMBER)
        store.save_search(aid, "SEA-1", H.QUERY_SHA256, 1, H.MEMBER)
        store.register_document(aid, workspace["id"], "DOC-1",
                                H.DOC_SHA256, 1, H.MEMBER)
        store.record_usage(aid, "USE-1", "search", 1, H.MEMBER)
        store.export_usage(aid, "EXP-1", H.MEMBER)
        store.close_session(aid, session["id"], H.MEMBER)
        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(actions, [
            "agency_create", "member_add", "member_add",
            "workspace_create", "session_create", "execution_record",
            "library_register", "search_save", "document_register",
            "usage_record", "usage_export", "session_close",
        ])
        for entry in audit.entries():
            self.assertEqual(set(entry.keys()),
                             {"ts", "actor", "action", "target", "details"})

    def test_failed_operations_record_nothing(self):
        """Core 13: a rejected operation appends no audit entry."""
        store, audit, agency = H.make_store()
        before = len(audit.entries())
        with self.assertRaises(ValidationError):
            store.create_workspace(agency["id"], "", "No ref", H.MEMBER)
        self.assertEqual(len(audit.entries()), before)

    def test_reads_are_not_audited_by_the_store(self):
        """Core 13: store reads record nothing (audit_read is the
        service layer's entry, so nothing is recorded twice)."""
        store, audit, agency = H.make_store()
        before = len(audit.entries())
        store.get_agency(agency["id"], H.MEMBER)
        store.list_agencies(H.MEMBER)
        store.agency_report(agency["id"], H.MEMBER)
        self.assertEqual(len(audit.entries()), before)


if __name__ == "__main__":
    unittest.main()
