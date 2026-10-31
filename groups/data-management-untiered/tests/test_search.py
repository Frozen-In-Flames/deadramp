"""Search tests.

Traces to: Core function -- Search; contract for
``DataMgmtStore.search`` -- literal case-insensitive substring over
datasets (name/description/tags/schema field names), sources
(name/kind/location) and quality rules (name/field/kind); returns
{datasets, sources, quality_rules}; a blank query returns all-empty
lists.
"""

import unittest

from datamgmt_helpers import STEWARD, VIEWER, make_store
from datamgmt.errors import ValidationError


class TestSearch(unittest.TestCase):
    """Core: Search."""

    def setUp(self):
        self.store, self.dataset, self.source = make_store()
        self.rule = self.store.create_quality_rule(
            self.dataset["id"], "amount-range", "range", "amount",
            STEWARD, params={"min": 0, "max": 100},
        )

    def test_shape(self):
        """Core: Search. Result keys are exactly datasets/sources/quality_rules."""
        result = self.store.search("claims", STEWARD)
        self.assertEqual(set(result.keys()), {"datasets", "sources", "quality_rules"})

    def test_dataset_by_name_and_description(self):
        """Core: Search. Dataset matched by name substring and by description substring."""
        result = self.store.search("claims extract", STEWARD)
        self.assertEqual([d["id"] for d in result["datasets"]], [self.dataset["id"]])
        result = self.store.search("nightly extract of", STEWARD)
        self.assertEqual([d["id"] for d in result["datasets"]], [self.dataset["id"]])

    def test_dataset_by_tag(self):
        """Core: Search. Dataset matched by a tag value (a unique tag appearing nowhere else)."""
        tagged = self.store.create_dataset(
            "Payroll Snapshot", "Quarterly snapshot", STEWARD, tags=["payroll-only-tag"]
        )
        result = self.store.search("payroll-only-tag", STEWARD)
        self.assertEqual([d["id"] for d in result["datasets"]], [tagged["id"]])
        result = self.store.search("nightly", STEWARD)
        self.assertIn(self.dataset["id"], [d["id"] for d in result["datasets"]])

    def test_dataset_by_schema_field_name(self):
        """Core: Search. Dataset matched by a schema field name (patient_id)."""
        result = self.store.search("patient_id", STEWARD)
        self.assertEqual([d["id"] for d in result["datasets"]], [self.dataset["id"]])

    def test_source_by_name_kind_location(self):
        """Core: Search. Source matched by name, by kind and by location."""
        for query in ("ehr-feed", "api", "ehr.internal"):
            with self.subTest(query=query):
                result = self.store.search(query, STEWARD)
                self.assertIn(self.source["id"], [s["id"] for s in result["sources"]])

    def test_rule_by_name_field_kind(self):
        """Core: Search. Quality rule matched by name, by field and by kind."""
        for query in ("amount-range", "amount", "range"):
            with self.subTest(query=query):
                result = self.store.search(query, STEWARD)
                self.assertIn(self.rule["id"], [r["id"] for r in result["quality_rules"]])

    def test_case_insensitive(self):
        """Core: Search. Matching is case-insensitive in every section."""
        result = self.store.search("CLAIMS EXTRACT", STEWARD)
        self.assertIn(self.dataset["id"], [d["id"] for d in result["datasets"]])
        result = self.store.search("EHR-FEED", STEWARD)
        self.assertIn(self.source["id"], [s["id"] for s in result["sources"]])
        result = self.store.search("AMOUNT-RANGE", STEWARD)
        self.assertIn(self.rule["id"], [r["id"] for r in result["quality_rules"]])

    def test_no_match(self):
        """Core: Search. No match -> empty lists under the three keys."""
        result = self.store.search("zzzz-nope", STEWARD)
        self.assertEqual(result, {"datasets": [], "sources": [], "quality_rules": []})

    def test_blank_query_all_empty(self):
        """Core: Search. A blank (empty or whitespace) query returns all-empty lists, not everything."""
        for query in ("", "   "):
            with self.subTest(query=query):
                result = self.store.search(query, STEWARD)
                self.assertEqual(
                    result, {"datasets": [], "sources": [], "quality_rules": []}
                )

    def test_literal_not_regex(self):
        """Core: Search. Regex characters in the query are literal and do not explode or pattern-match."""
        result = self.store.search("claims.*", STEWARD)
        self.assertEqual(result["datasets"], [])
        result = self.store.search("[a-z]+", STEWARD)
        self.assertEqual(result, {"datasets": [], "sources": [], "quality_rules": []})
        # An unbalanced regex metacharacter must not raise.
        result = self.store.search("claims(", STEWARD)
        self.assertEqual(result["datasets"], [])

    def test_viewer_can_search(self):
        """Core: Search. A viewer (read access) can search."""
        result = self.store.search("claims", VIEWER)
        self.assertIn(self.dataset["id"], [d["id"] for d in result["datasets"]])

    def test_non_string_query_validation(self):
        """Core: Search (SI-10). A non-string query -> ValidationError."""
        with self.assertRaises(ValidationError):
            self.store.search(123, STEWARD)


if __name__ == "__main__":
    unittest.main()
