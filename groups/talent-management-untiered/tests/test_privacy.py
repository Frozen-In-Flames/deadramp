"""Privacy discipline: exact shapes, banned keys, smuggled kwargs.

Traces to: UNION-SPEC.md "Privacy discipline (hard rule)" —
candidates are opaque references; assessments store labels, never
content; interviews store metadata, never media; nothing is
scored. Every stored entity's key set is pinned exactly, derived
views add exactly the derived keys, a recursive scan finds no
identity- or score-shaped key in any stored record or the report,
and methods reject smuggled keyword arguments with TypeError
(there is no parameter that could accept them).
"""

import inspect
import unittest

import talentmgmt_helpers as H

BANNED_KEYS = {
    "name", "first_name", "last_name", "email", "phone", "ssn",
    "address", "dob", "date_of_birth", "resume", "cv", "score",
    "scores", "rating", "rank", "ranking", "match_score",
    "content", "transcript", "recording", "notes", "gender",
    "race", "ethnicity", "salary",
}

EXPECTED_SHAPES = {
    "_organizations": {"id", "org_ref", "label", "members",
                       "created_by", "created_utc"},
    "_candidates": {"id", "org_id", "candidate_ref", "label",
                    "created_by", "created_utc"},
    "_requisitions": {"id", "org_id", "requisition_ref", "title",
                      "opens_at", "closes_at", "status", "created_by",
                      "created_utc"},
    "_pipelines": {"id", "org_id", "pipeline_ref", "requisition_id",
                   "stages", "label", "created_by", "created_utc"},
    "_placements": {"id", "org_id", "pipeline_id", "placement_ref",
                    "candidate_ref", "status", "created_by",
                    "created_utc"},
    "_movements": {"id", "org_id", "placement_id", "movement_ref",
                   "stage_index", "label", "created_by", "created_utc"},
    "_events": {"id", "org_id", "event_ref", "title", "kind",
                "starts_at", "requisition_id", "label", "status",
                "created_by", "created_utc"},
    "_registrations": {"id", "org_id", "event_id", "registration_ref",
                       "candidate_ref", "status", "created_by",
                       "created_utc"},
    "_assessments": {"id", "org_id", "assessment_ref", "candidate_ref",
                     "instrument_label", "requisition_id", "status",
                     "outcome_label", "created_by", "created_utc"},
    "_interviews": {"id", "org_id", "interview_ref", "candidate_ref",
                    "kind", "requisition_id", "scheduled_at", "status",
                    "created_by", "created_utc"},
    "_workflows": {"id", "org_id", "workflow_ref", "label",
                   "created_by", "created_utc"},
}


def _all_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _all_keys(value)


class TestPrivacy(unittest.TestCase):
    """The stored substrate can hold references and labels only."""

    def setUp(self):
        self.store, self.audit, self.org = H.make_store()
        oid = self.org["id"]
        H.make_candidate(self.store, self.org)
        requisition = H.make_requisition(self.store, self.org)
        pipeline = H.make_pipeline(self.store, self.org, requisition)
        placement = H.make_placement(self.store, self.org, pipeline)
        self.store.record_movement(oid, placement["id"], "MOV-1", 1,
                                   H.MEMBER)
        event = H.make_event(self.store, self.org)
        self.store.register_for_event(oid, event["id"], "REG-1",
                                      H.CANDIDATE_REF, H.MEMBER)
        assessment = self.store.record_assessment(
            oid, "ASM-1", H.CANDIDATE_REF, "Inventory", H.MEMBER)
        self.store.complete_assessment(oid, assessment["id"], "Done",
                                       H.MEMBER)
        self.store.schedule_interview(oid, "INT-1", H.CANDIDATE_REF,
                                      "video", H.MEMBER)
        self.store.register_workflow(oid, "WFL-1", "Auto", H.MEMBER)
        self.placement_id = placement["id"]

    def test_every_stored_shape_is_pinned(self):
        """Privacy: each of the eleven stored entity shapes has
        exactly its contracted key set."""
        for attribute, expected in EXPECTED_SHAPES.items():
            records = getattr(self.store, attribute)
            self.assertTrue(records, attribute)
            for record in records.values():
                self.assertEqual(set(record), expected,
                                 (attribute, record.get("id")))

    def test_derived_views_add_exactly_the_derived_keys(self):
        """Privacy: read views add past_close to requisitions and
        current_stage_index / current_stage to placements — and
        nothing else beyond the stored shapes."""
        oid = self.org["id"]
        requisition = self.store.list_requisitions(oid, H.MEMBER)[0]
        stored_req = self.store._requisitions[requisition["id"]]
        self.assertEqual(set(requisition), set(stored_req) | {"past_close"})
        placement = self.store.get_placement(oid, self.placement_id,
                                             H.MEMBER)
        stored_plc = self.store._placements[self.placement_id]
        self.assertEqual(set(placement),
                         set(stored_plc) | {"current_stage_index",
                                            "current_stage"})

    def test_no_banned_key_anywhere(self):
        """Privacy: a recursive scan over every stored record and
        the report finds no identity- or score-shaped key."""
        for attribute in EXPECTED_SHAPES:
            for record in getattr(self.store, attribute).values():
                for key in _all_keys(record):
                    self.assertNotIn(str(key).lower(), BANNED_KEYS,
                                     (attribute, key))
        report = self.store.org_report(self.org["id"], H.MEMBER)
        for key in _all_keys(report):
            self.assertNotIn(str(key).lower(), BANNED_KEYS, key)

    def test_smuggled_kwargs_raise_type_error(self):
        """Privacy / SI-10: store methods have no parameter that
        could accept a resume, a score, content, or a recording —
        smuggled keywords raise TypeError."""
        oid = self.org["id"]
        with self.assertRaises(TypeError):
            self.store.register_candidate(oid, "CAN-9", "L", H.MEMBER,
                                          resume="...")
        with self.assertRaises(TypeError):
            self.store.record_assessment(oid, "ASM-9", H.CANDIDATE_REF,
                                         "Inv", H.MEMBER, score=42)
        with self.assertRaises(TypeError):
            self.store.schedule_interview(oid, "INT-9", H.CANDIDATE_REF,
                                          "video", H.MEMBER,
                                          recording="...")
        with self.assertRaises(TypeError):
            self.store.record_movement(oid, self.placement_id, "MOV-9", 1,
                                       H.MEMBER, content="...")

    def test_signatures_carry_no_substance_parameters(self):
        """Privacy: the assessment, interview, and movement
        signatures contain no substance-shaped parameter name."""
        for method in (self.store.record_assessment,
                       self.store.schedule_interview,
                       self.store.record_movement):
            for parameter in inspect.signature(method).parameters:
                self.assertNotIn(parameter.lower(), BANNED_KEYS,
                                 (method.__name__, parameter))


if __name__ == "__main__":
    unittest.main()
