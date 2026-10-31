"""Spec integrity: the spec sheets in specs/specs.json are pinned
against the census unit, the forks registry, and the literal claim
tables from UNION-SPEC.md.

Traces to: UNION-SPEC.md membership and taxonomy decisions -- the
group is exactly the remainder census unit
``new-group:Learning Management|L1`` (fork IDs FR2113157410 and
FR2135043135); the taxonomy applied is the L2 taxonomy verbatim
(both extractors' TAXONOMY literals, parsed with ``ast``, are
equal); TRAIN Learning Network claims [] and CloudLCMS claims
exactly ["content_standards_distribution"]; every claim's evidence
is a verbatim sentence of its sheet's normalized description; every
remainder.json census citation for the two forks is a verbatim
substring of the sheet description; and the near-misses hold:
TRAIN's description contains "multi-tenant" while the multi_tenancy
pattern does not match it, and CloudLCMS's description contains
"learning content management" while the learning_content_management
pattern does not match it.
"""

import ast
import json
import os
import re
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_IDS = ["FR2113157410", "FR2135043135"]
UNIT_ID = "new-group:Learning Management|L1"

EXPECTED_CLAIMS = {
    "FR2113157410": [],
    "FR2135043135": ["content_standards_distribution"],
}


def _load_json(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return json.load(fh)


def _taxonomy(extract_path):
    """Parse (never execute) an extractor and return its TAXONOMY."""
    with open(extract_path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "TAXONOMY"
                for t in node.targets):
            return [tuple(row) for row in ast.literal_eval(node.value)]
    raise AssertionError("TAXONOMY not found in %s" % extract_path)


def _normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def _sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


class TestSpecIntegrity(unittest.TestCase):
    """Specs: the spec sheets are exactly what the spec claims."""

    @classmethod
    def setUpClass(cls):
        cls.sheets = _load_json(_GROUP_ROOT, "specs", "specs.json")
        cls.by_id = {s["fork_id"]: s for s in cls.sheets}
        cls.remainder = _load_json(_REPO_ROOT, "remainder.json")
        forks = _load_json(_REPO_ROOT, "forks.json")
        rows = forks if isinstance(forks, list) else forks.get("forks", forks)
        cls.registry = {}
        for row in rows:
            url = row.get("source_url", "")
            for fork_id in FORK_IDS:
                if url.rstrip("/").endswith(fork_id):
                    cls.registry[fork_id] = row
        cls.taxonomy_l1 = _taxonomy(
            os.path.join(_GROUP_ROOT, "scratch", "extract.py"))
        cls.taxonomy_l2 = _taxonomy(os.path.join(
            _REPO_ROOT, "groups", "learning-management-l2", "scratch",
            "extract.py"))
        cls.patterns = {fid: pattern for fid, _label, pattern
                        in cls.taxonomy_l1}

    def test_exactly_two_sheets_with_the_census_fork_ids(self):
        """Specs: specs.json has exactly 2 sheets, with fork IDs FR2113157410 and FR2135043135 (the census unit membership)."""
        self.assertEqual(len(self.sheets), 2)
        self.assertEqual([s["fork_id"] for s in self.sheets], FORK_IDS)

    def test_remainder_unit_lists_exactly_these_ids(self):
        """Specs: remainder.json's unit "new-group:Learning Management|L1" lists exactly these fork IDs."""
        units = [u for u in self.remainder["build_units"]
                 if u.get("unit_id") == UNIT_ID]
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["fork_ids"], FORK_IDS)
        self.assertEqual(units[0]["category"], "Learning Management")
        self.assertEqual(units[0]["tier"], "L1")

    def test_taxonomy_equals_l2_taxonomy_verbatim(self):
        """Specs: the taxonomy the L1 extractor used equals the L2 taxonomy verbatim (same families, same labels, same patterns, parsed via ast from both extractors)."""
        self.assertEqual(self.taxonomy_l1, self.taxonomy_l2)
        self.assertEqual(len(self.taxonomy_l1), 26)

    def test_literal_claim_table(self):
        """Specs: TRAIN functions_claimed == [] and CloudLCMS functions_claimed function_ids == ["content_standards_distribution"], exactly (1 claim total)."""
        total = 0
        for sheet in self.sheets:
            claimed = [c["function_id"] for c in sheet["functions_claimed"]]
            self.assertEqual(claimed, EXPECTED_CLAIMS[sheet["fork_id"]],
                             sheet["fork_id"])
            total += len(claimed)
        self.assertEqual(total, 1)
        claim = self.by_id["FR2135043135"]["functions_claimed"][0]
        labels = {fid: label for fid, label, _p in self.taxonomy_l1}
        self.assertEqual(claim["function"],
                         labels["content_standards_distribution"])

    def test_every_evidence_is_a_verbatim_sentence(self):
        """Specs: every claim's evidence is a verbatim sentence of that sheet's normalized description."""
        for sheet in self.sheets:
            sentences = _sentences(sheet["description"])
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sentences,
                              (sheet["fork_id"], claim["function_id"]))

    def test_census_citations_are_verbatim_substrings(self):
        """Specs: every remainder.json census citation for the two forks is a verbatim substring of the sheet description (whitespace-normalized, as the extractor verifies)."""
        census = {f["fork_id"]: f for f in self.remainder["forks"]
                  if f["fork_id"] in FORK_IDS}
        self.assertEqual(set(census), set(FORK_IDS))
        for fork_id, entry in census.items():
            self.assertTrue(entry["citations"], fork_id)
            self.assertEqual(entry["build_unit"], UNIT_ID)
            for citation in entry["citations"]:
                self.assertIn(_normalize(citation),
                              self.by_id[fork_id]["description"],
                              (fork_id, citation))

    def test_near_miss_train_multi_tenancy(self):
        """Specs (near-miss pin): TRAIN's description contains "multi-tenant" and the multi_tenancy pattern does not match its description -- substance asserted, literally unclaimed."""
        description = self.by_id["FR2113157410"]["description"]
        self.assertIn("multi-tenant", description)
        pattern = re.compile(self.patterns["multi_tenancy"], re.IGNORECASE)
        self.assertIsNone(pattern.search(description))

    def test_near_miss_cloudlcms_learning_content_management(self):
        """Specs (near-miss pin): CloudLCMS's description contains "learning content management" and the learning_content_management pattern does not match it -- substance asserted, literally unclaimed."""
        description = self.by_id["FR2135043135"]["description"]
        self.assertIn("learning content management", description)
        pattern = re.compile(
            self.patterns["learning_content_management"], re.IGNORECASE)
        self.assertIsNone(pattern.search(description))

    def test_sheet_fields_match_forks_registry(self):
        """Specs: sheet fields (vendor/product/impact/status/tier) match the forks.json rows for the two fork IDs; both sheets are L1 in the Learning Management category."""
        self.assertEqual(set(self.registry), set(FORK_IDS))
        for fork_id, sheet in self.by_id.items():
            row = self.registry[fork_id]
            with self.subTest(fork_id=fork_id):
                self.assertEqual(sheet["vendor"], row["vendor"])
                self.assertEqual(sheet["product"], row["product"])
                self.assertEqual(sheet["fedramp_impact_level"],
                                 row["fedramp_impact_level"])
                self.assertEqual(sheet["authorization_status"],
                                 row["authorization_status"])
                self.assertEqual(sheet["cmmc_tier"], row["cmmc_tier"])
                self.assertEqual(sheet["cmmc_tier"], "L1")
                self.assertEqual(sheet["service_model"],
                                 [row["service_model"]])
                self.assertEqual(sheet["deadramp_category"],
                                 "Learning Management")
                self.assertEqual(sheet["source_url"], row["source_url"])


if __name__ == "__main__":
    unittest.main()
