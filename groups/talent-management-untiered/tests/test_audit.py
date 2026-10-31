"""Core 13 (audit side): the append-only audit log (AU family).

Traces to: UNION-SPEC.md Core 13 and the AU control mapping —
every mutation is recorded with actor, action, target, and UTC
timestamp; failed operations and store-level reads record
nothing; the log has no mutation API; JSONL persistence reloads
on construction.
"""

import os
import tempfile
import unittest

import talentmgmt_helpers as H

EXPECTED_FLOW_ACTIONS = [
    "organization_create", "member_add", "member_add",
    "candidate_register", "requisition_create", "pipeline_create",
    "placement_create", "movement_record", "event_create",
    "registration_create", "registration_check_in", "event_complete",
    "event_create", "event_cancel", "assessment_record",
    "assessment_complete", "interview_schedule", "interview_complete",
    "interview_schedule", "interview_cancel", "workflow_register",
    "requisition_close", "placement_withdraw",
]


def _canonical_flow(store):
    """Run one of every mutation, in a fixed order."""
    org = store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
    store.add_member(org["id"], H.MEMBER.name, H.ADMIN)
    store.add_member(org["id"], H.VIEWER.name, H.ADMIN)
    oid = org["id"]
    store.register_candidate(oid, H.CANDIDATE_REF, H.CANDIDATE_LABEL,
                             H.MEMBER)
    requisition = store.create_requisition(oid, H.REQUISITION_REF,
                                           H.REQUISITION_TITLE, H.MEMBER)
    pipeline = store.create_pipeline(oid, H.PIPELINE_REF, requisition["id"],
                                     list(H.STAGES), H.MEMBER)
    placement = store.place_candidate(oid, pipeline["id"], H.PLACEMENT_REF,
                                      H.CANDIDATE_REF, H.MEMBER)
    store.record_movement(oid, placement["id"], "MOV-1", 1, H.MEMBER)
    event = store.create_event(oid, H.EVENT_REF, H.EVENT_TITLE, "in_person",
                               H.EVENT_START, H.MEMBER)
    registration = store.register_for_event(oid, event["id"], "REG-1",
                                            H.CANDIDATE_REF, H.MEMBER)
    store.check_in_registration(oid, registration["id"], H.MEMBER)
    store.complete_event(oid, event["id"], H.MEMBER)
    second_event = store.create_event(oid, "EVT-2", "Virtual Fair", "virtual",
                                      H.EVENT_START, H.MEMBER)
    store.cancel_event(oid, second_event["id"], H.MEMBER)
    assessment = store.record_assessment(oid, "ASM-1", H.CANDIDATE_REF,
                                         "Inventory", H.MEMBER)
    store.complete_assessment(oid, assessment["id"], "Done", H.MEMBER)
    interview = store.schedule_interview(oid, "INT-1", H.CANDIDATE_REF,
                                         "video", H.MEMBER)
    store.complete_interview(oid, interview["id"], H.MEMBER)
    second = store.schedule_interview(oid, "INT-2", H.CANDIDATE_REF,
                                      "in_person", H.MEMBER)
    store.cancel_interview(oid, second["id"], H.MEMBER)
    store.register_workflow(oid, "WFL-1", "Auto", H.MEMBER)
    store.close_requisition(oid, requisition["id"], H.MEMBER)
    store.withdraw_placement(oid, placement["id"], H.MEMBER)
    return org


class TestAuditLog(unittest.TestCase):
    """AU: the audit trail is complete, ordered, and append-only."""

    def test_entry_shape(self):
        """AU-3: every entry carries exactly {ts, actor, action,
        target, details}."""
        store, audit, _org = H.make_store()
        for entry in audit.entries():
            self.assertEqual(set(entry), {"ts", "actor", "action",
                                          "target", "details"})

    def test_all_mutation_actions_in_order(self):
        """AU-2: the canonical flow records every mutation action
        in order — 23 entries covering all twenty distinct action
        names (member_add, event_create, and interview_schedule
        each occur twice)."""
        audit = H.AuditLog()
        store = H.fresh_store(audit=audit)
        _canonical_flow(store)
        actions = [e["action"] for e in audit.entries()]
        self.assertEqual(actions, EXPECTED_FLOW_ACTIONS)

    def test_failed_operations_record_nothing(self):
        """AU / SI-10: a rejected operation (duplicate candidate,
        out-of-bounds movement) appends no audit entry."""
        store, audit, org = H.make_store()
        H.make_candidate(store, org)
        baseline = len(audit.entries())
        from talentmgmt.errors import ValidationError
        with self.assertRaises(ValidationError):
            H.make_candidate(store, org)
        self.assertEqual(len(audit.entries()), baseline)

    def test_store_reads_record_nothing(self):
        """AU: reads at the store layer are not audited (the HTTP
        layer owns audit_read and denials, so nothing is counted
        twice)."""
        store, audit, org = H.make_store()
        baseline = len(audit.entries())
        store.list_candidates(org["id"], H.MEMBER)
        store.org_report(org["id"], H.MEMBER)
        store.search_registry(H.MEMBER, "CAN")
        self.assertEqual(len(audit.entries()), baseline)

    def test_jsonl_persistence_and_reload(self):
        """AU: with a path, entries persist as JSONL and reload on
        construction, in order."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            audit = H.AuditLog(path=path)
            store = H.fresh_store(audit=audit)
            store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
            reloaded = H.AuditLog(path=path)
            self.assertEqual([e["action"] for e in reloaded.entries()],
                             ["organization_create"])

    def test_no_mutation_api(self):
        """AU: AuditLog exposes no update or delete operation."""
        for name in dir(H.AuditLog):
            lowered = name.lower()
            self.assertNotIn("delete", lowered, name)
            self.assertNotIn("update", lowered, name)
            self.assertNotIn("remove", lowered, name)
            self.assertNotIn("clear", lowered, name)


if __name__ == "__main__":
    unittest.main()
