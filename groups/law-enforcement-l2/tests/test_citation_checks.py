"""Citation-check records (treatment recorded verbatim).

Traces to: Core 7 (Citation-check records) and claim family
``citation_validation`` (2 of 2) in UNION-SPEC.md -- the build
records the treatment a caller supplies, exactly as supplied. It
computes no treatment, normalizes nothing, and derives no score or
status from the recorded strings (the Group 21 records-not-engines
precedent).
"""

import unittest

from lawenf.errors import NotFoundError, ValidationError
from lawenf_helpers import MEMBER, make_store

CHECK_KEYS = {"id", "matter_id", "citation_ref", "source_id", "treatment",
              "created_by", "created_utc"}


class TestCitationChecks(unittest.TestCase):
    """Core 7: treatments are records, stored verbatim."""

    def setUp(self):
        self.store, _audit, self.matter = make_store()
        self.mid = self.matter["id"]
        self.src = self.store.create_source(self.mid, "SRC-1", "case_law", MEMBER)

    def test_shape_and_defaults(self):
        chk = self.store.record_citation_check(
            self.mid, "CIT-1", "followed", MEMBER)
        self.assertEqual(set(chk.keys()), CHECK_KEYS)
        self.assertIsNone(chk["source_id"])
        self.assertEqual(chk["treatment"], "followed")

    def test_treatment_stored_verbatim(self):
        weird = "Followed — but QUESTIONED in part, per J. Doe (unpub.)"
        chk = self.store.record_citation_check(self.mid, "CIT-1", weird, MEMBER)
        self.assertEqual(chk["treatment"], weird)
        listed = self.store.list_citation_checks(self.mid, MEMBER)
        self.assertEqual(listed[0]["treatment"], weird)

    def test_no_score_or_status_field_exists(self):
        chk = self.store.record_citation_check(
            self.mid, "CIT-1", "overruled", MEMBER)
        for forbidden in ("score", "status", "valid", "rating", "grade"):
            self.assertNotIn(forbidden, chk)

    def test_empty_treatment_rejected(self):
        for bad in ("", "  ", None):
            with self.assertRaises(ValidationError):
                self.store.record_citation_check(self.mid, "CIT-1", bad, MEMBER)

    def test_source_link_must_exist_in_matter(self):
        chk = self.store.record_citation_check(
            self.mid, "CIT-1", "distinguished", MEMBER, source_id=self.src["id"])
        self.assertEqual(chk["source_id"], self.src["id"])
        with self.assertRaises(NotFoundError):
            self.store.record_citation_check(
                self.mid, "CIT-2", "followed", MEMBER, source_id="src-999")

    def test_same_citation_may_be_checked_repeatedly(self):
        self.store.record_citation_check(self.mid, "CIT-1", "followed", MEMBER)
        again = self.store.record_citation_check(
            self.mid, "CIT-1", "questioned", MEMBER)
        self.assertEqual(again["id"], "cit-2")
        self.assertEqual(len(self.store.list_citation_checks(self.mid, MEMBER)), 2)


if __name__ == "__main__":
    unittest.main()
