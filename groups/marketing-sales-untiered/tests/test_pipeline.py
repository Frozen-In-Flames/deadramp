"""Core functions 4 and 5: capture-pipeline records (stage moves
only along the recorded transition map) and proposal-content
version records (metadata only; versions unique per item) —
taxonomy families capture_pipeline / proposal_content."""

import unittest

from marketsales_helpers import (ADMIN, OPERATOR, make_opportunity,
                                 make_org, make_store)

from marketsales.errors import NotFoundError, ValidationError


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.store, _audit = make_store()
        self.org = make_org(self.store)
        self.opp = make_opportunity(self.store, self.org)
        self.entry = self.store.create_pipeline_entry(
            OPERATOR, self.opp["id"])

    def test_full_path_to_award(self):
        entry = self.entry
        for stage in ("qualified", "capture", "proposal", "submitted",
                      "awarded"):
            entry = self.store.transition_pipeline(OPERATOR, entry["id"],
                                                   stage)
        self.assertEqual(entry["stage"], "awarded")

    def test_illegal_transitions_change_nothing(self):
        with self.assertRaises(ValidationError):
            self.store.transition_pipeline(OPERATOR, self.entry["id"],
                                           "submitted")
        with self.assertRaises(ValidationError):
            self.store.transition_pipeline(OPERATOR, self.entry["id"],
                                           "identified")
        current = self.store.get_pipeline_entry(ADMIN, self.entry["id"])
        self.assertEqual(current["stage"], "identified")

    def test_terminal_stages_are_terminal(self):
        entry = self.store.transition_pipeline(OPERATOR, self.entry["id"],
                                               "no_bid")
        with self.assertRaises(ValidationError):
            self.store.transition_pipeline(OPERATOR, entry["id"],
                                           "qualified")

    def test_unknown_stage_and_entry(self):
        with self.assertRaises(ValidationError):
            self.store.create_pipeline_entry(OPERATOR, self.opp["id"],
                                             stage="closing")
        with self.assertRaises(NotFoundError):
            self.store.transition_pipeline(OPERATOR, "pip-99", "qualified")


class ContentTests(unittest.TestCase):
    def setUp(self):
        self.store, _audit = make_store()
        self.org = make_org(self.store)
        self.opp = make_opportunity(self.store, self.org)

    def test_versions_accumulate(self):
        v1 = self.store.create_content_version(
            OPERATOR, self.opp["id"], "Volume I", "section", 1, 4096)
        v2 = self.store.create_content_version(
            OPERATOR, self.opp["id"], "Volume I", "section", 2, 5120)
        self.assertEqual((v1["version"], v2["version"]), (1, 2))
        records = self.store.list_content(ADMIN,
                                          opportunity_id=self.opp["id"])
        self.assertEqual(len(records), 2)

    def test_duplicate_version_refused(self):
        self.store.create_content_version(
            OPERATOR, self.opp["id"], "Volume I", "section", 1, 4096)
        with self.assertRaises(ValidationError):
            self.store.create_content_version(
                OPERATOR, self.opp["id"], "Volume I", "section", 1, 9999)

    def test_version_and_size_validation(self):
        with self.assertRaises(ValidationError):
            self.store.create_content_version(
                OPERATOR, self.opp["id"], "Volume I", "section", 0, 10)
        with self.assertRaises(ValidationError):
            self.store.create_content_version(
                OPERATOR, self.opp["id"], "Volume I", "section", 1.5, 10)
        with self.assertRaises(ValidationError):
            self.store.create_content_version(
                OPERATOR, self.opp["id"], "Volume I", "section", 1, True)
        with self.assertRaises(ValidationError):
            self.store.create_content_version(
                OPERATOR, self.opp["id"], "Volume I", "section", 1, -5)

    def test_pipeline_link_must_match_the_opportunity(self):
        other_opp = self.store.create_opportunity(
            OPERATOR, self.org["id"], "OPP-REF-2", "Agency", "Other",
            "2026-01-06")
        entry = self.store.create_pipeline_entry(OPERATOR,
                                                 other_opp["id"])
        with self.assertRaises(ValidationError):
            self.store.create_content_version(
                OPERATOR, self.opp["id"], "Volume I", "section", 1, 10,
                pipeline_id=entry["id"])

    def test_no_content_field_exists(self):
        record = self.store.create_content_version(
            OPERATOR, self.opp["id"], "Volume I", "section", 1, 4096)
        self.assertEqual(
            set(record),
            {"id", "opportunity_id", "pipeline_id", "item_label",
             "kind_label", "version", "size_bytes", "created_by",
             "created_utc"})


if __name__ == "__main__":
    unittest.main()
