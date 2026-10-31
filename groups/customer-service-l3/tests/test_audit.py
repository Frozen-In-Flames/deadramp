"""Append-only audit (Core function 10; AU family, High baseline [L3]).

Adaptation from the L1/L2 suite: audit entries now also carry the
hash-chain fields ``seq`` / ``prev_hash`` / ``hash`` (AU-9), so the
exact key-set assertion below names all eight keys.
"""

import unittest

from custsvc.audit import AuditLog
from custsvc_helpers import ADMIN, AGENT, make_case, make_store


class TestAuditLog(unittest.TestCase):
    def test_entries_shape_and_order(self):
        audit = AuditLog()
        audit.record("alice", "case_create", "case-1")
        audit.record("bob", "case_status", "case-1", {"from": "new", "to": "open"})
        entries = audit.entries()
        self.assertEqual([e["action"] for e in entries], ["case_create", "case_status"])
        self.assertEqual(set(entries[0].keys()),
                         {"ts", "actor", "action", "target", "details",
                          "seq", "prev_hash", "hash"})

    def test_no_update_or_delete_api(self):
        audit = AuditLog()
        for name in ("update", "delete", "remove", "clear", "pop"):
            self.assertFalse(hasattr(audit, name), name)

    def test_store_mutations_are_audited(self):
        store, audit, requester, rsp1, _ = make_store()
        baseline = len(audit.entries())
        case = make_case(store, requester)
        store.assign_case(case["id"], rsp1["id"], AGENT)
        actions = [e["action"] for e in audit.entries()[baseline:]]
        self.assertIn("case_create", actions)
        self.assertIn("case_assign", actions)
        assign = [e for e in audit.entries() if e["action"] == "case_assign"][0]
        self.assertEqual(assign["actor"], "bob")
        self.assertEqual(assign["details"]["to"], rsp1["id"])

    def test_user_actor_normalized_to_name(self):
        store, audit, requester, _, _ = make_store()
        make_case(store, requester)
        creates = [e for e in audit.entries() if e["action"] == "case_create"]
        self.assertEqual(creates[0]["actor"], "bob")


if __name__ == "__main__":
    unittest.main()
