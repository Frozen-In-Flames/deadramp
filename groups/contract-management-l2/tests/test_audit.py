"""Core 18 (audit): the append-only audit log.

Traces to: UNION-SPEC.md core function 18 and the AU control
family (AU-2, AU-3, AU-6) — every mutation recorded with actor,
action, target, timestamp; failed operations and store reads
record nothing; the log has no mutation API.
"""

import json
import os
import tempfile
import unittest

import contractmgmt_helpers as H
from contractmgmt.audit import AuditLog
from contractmgmt.errors import ValidationError


class TestAuditLog(unittest.TestCase):
    """Core 18 / AU: entry shape, ordering, and append-only discipline."""

    def test_entry_shape_pinned(self):
        """AU-3: an entry carries exactly {ts, actor, action, target,
        details}."""
        audit = AuditLog()
        entry = audit.record("alice", "organization_create", "org-1",
                             {"org_ref": "ORG-1"})
        self.assertEqual(set(entry.keys()),
                         {"ts", "actor", "action", "target", "details"})
        self.assertEqual(audit.entries(), [entry])

    def test_mutation_actions_recorded_in_order(self):
        """AU-2: the canonical flow records every mutation action
        name, in order."""
        audit = AuditLog()
        store = H.fresh_store(audit=audit)
        org = store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
        store.add_member(org["id"], "bob", H.ADMIN)
        store.register_participant(H.PARTICIPANT_REF, H.PARTICIPANT_LABEL,
                                   H.MEMBER)
        contract = H.make_contract(store, org)
        store.record_modification(org["id"], contract["id"], "MOD-1", 1,
                                  H.MEMBER)
        req = store.create_requirement(org["id"], "REQ-1", "Label", H.MEMBER)
        store.satisfy_requirement(org["id"], req["id"], H.MEMBER)
        req2 = store.create_requirement(org["id"], "REQ-2", "Label", H.MEMBER)
        store.waive_requirement(org["id"], req2["id"], H.MEMBER)
        protest = store.create_protest(org["id"], "PRO-1", "Label",
                                       "2027-01-01", H.MEMBER,
                                       contract_id=contract["id"])
        store.close_protest(org["id"], protest["id"], H.MEMBER)
        datacall = store.create_datacall(org["id"], "DCL-1", "REQ-REF",
                                         "Label", "2027-01-01", H.MEMBER)
        store.close_datacall(org["id"], datacall["id"], H.MEMBER)
        risk = store.create_risk(org["id"], "RSK-1", "Label", H.MEMBER)
        store.close_risk(org["id"], risk["id"], H.MEMBER)
        store.record_communication(org["id"], "COM-1", H.COUNTERPARTY_REF,
                                   "inbound", "Label", H.MEMBER)
        opp = H.make_opportunity(store, org)
        sub = store.record_submission(org["id"], opp["id"], "SUB-1",
                                      H.PARTICIPANT_REF, H.MEMBER)
        store.record_award(org["id"], opp["id"], sub["id"], "AWD-1", 1,
                           H.MEMBER)
        store.record_payment(org["id"], "PAY-1", "subscription", 1, H.MEMBER)
        store.register_workflow(org["id"], "WFL-1", "Label", H.MEMBER)
        store.register_integration(org["id"], "INT-1", "SYS-REF", "Label",
                                   H.MEMBER)
        store.close_opportunity(org["id"], opp["id"], H.MEMBER)
        store.close_contract(org["id"], contract["id"], H.MEMBER)
        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(actions, [
            "organization_create", "member_add", "participant_register",
            "contract_create", "modification_record", "requirement_create",
            "requirement_satisfy", "requirement_create",
            "requirement_waive", "protest_create", "protest_close",
            "datacall_create", "datacall_close", "risk_create",
            "risk_close", "communication_record", "opportunity_create",
            "submission_record", "award_record", "payment_record",
            "workflow_register", "integration_register",
            "opportunity_close", "contract_close",
        ])

    def test_failed_operations_record_nothing(self):
        """AU-2: a rejected operation appends no entry."""
        audit = AuditLog()
        store = H.fresh_store(audit=audit)
        org = store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
        store.add_member(org["id"], "bob", H.ADMIN)
        before = len(audit.entries())
        with self.assertRaises(ValidationError):
            store.create_organization(H.ORG_REF, "Clone", H.ADMIN)
        with self.assertRaises(ValidationError):
            H.make_contract(store, org, ceiling_cents=1, award_cents=2)
        self.assertEqual(len(audit.entries()), before)

    def test_store_reads_record_nothing(self):
        """AU-2: reads at the store layer are not audited (denials
        and audit reads are the HTTP layer's job)."""
        store, audit, org = H.make_store()
        before = len(audit.entries())
        store.get_organization(org["id"], H.ADMIN)
        store.list_contracts(org["id"], H.ADMIN)
        store.org_report(org["id"], H.ADMIN)
        store.search_registry(H.ADMIN, "org")
        self.assertEqual(len(audit.entries()), before)

    def test_jsonl_persistence_and_reload(self):
        """AU: with a path, entries persist as JSON lines and reload
        on construction."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = AuditLog(path=path)
            audit.record("alice", "organization_create", "org-1")
            audit.record("bob", "contract_create", "con-1")
            with open(path, encoding="utf-8") as fh:
                lines = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(len(lines), 2)
            reloaded = AuditLog(path=path)
            self.assertEqual(
                [e["action"] for e in reloaded.entries()],
                ["organization_create", "contract_create"])

    def test_no_mutation_api(self):
        """AU-6: the log exposes no update/delete operation."""
        for name in ("update", "delete", "remove", "clear", "pop"):
            self.assertFalse(hasattr(AuditLog, name), name)


if __name__ == "__main__":
    unittest.main()
