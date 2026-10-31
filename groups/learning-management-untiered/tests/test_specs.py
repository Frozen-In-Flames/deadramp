"""Spec integrity: the untiered fork of this set.

Traces to: remainder.json build unit ``untiered:Learning
Management`` (kind ``untiered_set``, tier null, 1 fork) and the
spec sheet built for it in ``specs/specs.json``.

This is the FIRST untiered set for Learning Management: its fork
carries no tier in the source census, so the sheet must carry no
tier either. The pins here are:

- The spec sheet count is exactly 1.
- The sheet fork_id set is exactly the fork_ids set of the
  remainder.json unit ``untiered:Learning Management``.
- TIER DISCIPLINE: the sheet's ``cmmc_tier`` is None and its
  ``fedramp_impact_level`` is ``"Unknown"`` -- no tier or impact
  level is invented for a fork the census left untiered.
- The sheet's ``deadramp_category`` is ``"Learning Management"``
  (the census assignment; ``forks.json`` files the fork under
  Education & Training, and that filing is recorded, not hidden).
- The literal claim totals: exactly 0 claims, and the fork is a
  zero-claim fork. The zero is pinned MECHANICALLY: the founding
  taxonomy (AST-parsed out of the founding group's extractor,
  never executed) is re-applied here and reproduces the empty
  claim table, so the zero cannot drift silently.
- Evidence discipline is vacuous but stated: there are no claims,
  so no evidence exists to check; the census citation for the
  fork verifies verbatim against the raw description yet is
  evidence for no claim (verification is not a claim).
- Near-miss pins: "grading", "Reporting and data analysis", and
  "User management" all occur in the description (substance is
  present) while no family fires -- the taxonomy was not re-tuned.
- CATALOGUE DISCIPLINE: the source record's ``certified_services``
  list is empty; no claim could have rested on a catalogue.
"""

import ast
import json
import os
import re
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")
_RAW_PATH = os.path.join(_GROUP_ROOT, "..", "..", "raw", "data_dump.json")
_FORKS_PATH = os.path.join(_GROUP_ROOT, "..", "..", "forks.json")
_FOUNDING_EXTRACT = os.path.join(
    _GROUP_ROOT, "..", "learning-management-l2", "scratch", "extract.py")

UNIT_ID = "untiered:Learning Management"
EXPECTED_CATEGORY = "Learning Management"
EXPECTED_COUNT = 1
EXPECTED_FORK = "FR2634357692"
EXPECTED_TOTAL_CLAIMS = 0


def _load_sheets():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


def _load_unit():
    with open(_REMAINDER_PATH) as fh:
        rem = json.load(fh)
    units = [u for u in rem["build_units"] if u["unit_id"] == UNIT_ID]
    assert len(units) == 1, units
    return units[0]


def _load_raw_product():
    with open(_RAW_PATH) as fh:
        dump = json.load(fh)
    prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in prods}[EXPECTED_FORK]


def _normalize(text):
    # The founding extractor's documented normalization, verbatim.
    return re.sub(r"\s+", " ", text).strip()


def _founding_taxonomy():
    with open(_FOUNDING_EXTRACT) as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "TAXONOMY"
                for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("TAXONOMY literal not found")


class TestUntieredSpecSheets(unittest.TestCase):
    """Spec integrity + tier-discipline pins for the untiered fork."""

    def test_sheet_count_is_exactly_1(self):
        """The untiered set holds exactly 1 sheet."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), EXPECTED_COUNT)
        ids = [s["fork_id"] for s in sheets]
        self.assertEqual(len(set(ids)), EXPECTED_COUNT)

    def test_fork_id_set_matches_remainder_unit(self):
        """The sheet fork_id set == the fork_ids set of
        remainder.json unit `untiered:Learning Management` -- no
        more, no fewer."""
        sheets = _load_sheets()
        unit = _load_unit()
        self.assertEqual(len(unit["fork_ids"]), EXPECTED_COUNT)
        self.assertEqual({s["fork_id"] for s in sheets},
                         set(unit["fork_ids"]))
        self.assertEqual({s["fork_id"] for s in sheets}, {EXPECTED_FORK})

    def test_tier_discipline_no_tier_is_invented(self):
        """TIER DISCIPLINE: the unit's tier is null, so the sheet's
        ``cmmc_tier`` is None and its ``fedramp_impact_level`` is
        ``"Unknown"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertIsNone(sheet["cmmc_tier"])
                self.assertEqual(sheet["fedramp_impact_level"],
                                 "Unknown")

    def test_description_matches_raw_cache_under_founding_normalization(self):
        """The sheet's description is the raw cache's service_desc
        under the founding extractor's documented normalization
        (whitespace runs collapse to single spaces; words
        verbatim)."""
        product = _load_raw_product()
        for sheet in _load_sheets():
            self.assertEqual(sheet["description"],
                             _normalize(product["service_desc"]))

    def test_every_sheet_carries_the_group_category(self):
        """The sheet's ``deadramp_category`` is
        ``"Learning Management"`` -- the census assignment. The
        forks.json filing (Education & Training) is recorded in
        the same test so the assignment is never hidden."""
        for sheet in _load_sheets():
            self.assertEqual(sheet["deadramp_category"],
                             EXPECTED_CATEGORY)
        with open(_FORKS_PATH) as fh:
            forks = json.load(fh)
        rows = forks if isinstance(forks, list) else forks.get("forks", forks)
        filed = [r for r in rows if r["product"] ==
                 "Collaborative Learning Environment"]
        self.assertEqual(len(filed), 1)
        self.assertEqual(filed[0]["category"], "Education & Training")

    def test_claim_totals_are_pinned_literally(self):
        """The set carries exactly 0 claims in total, and the
        zero-claim set is exactly {FR2634357692} -- a fork gaining
        a claim fails here rather than drifting silently."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        zero = {s["fork_id"] for s in sheets if not s["functions_claimed"]}
        self.assertEqual(zero, {EXPECTED_FORK})

    def test_zero_claims_reproduce_mechanically(self):
        """The zero is a measurement, not an assertion: the
        founding 26-family taxonomy is re-applied to the sheet's
        description with the founding sentence split and
        first-match evidence rule, and reproduces the empty claim
        table exactly."""
        taxonomy = _founding_taxonomy()
        self.assertEqual(len(taxonomy), 26)
        for sheet in _load_sheets():
            sentences = [p.strip() for p in re.split(
                r"(?<=[.!?])\s+", sheet["description"].strip()) if p.strip()]
            reproduced = []
            for function_id, label, pattern in taxonomy:
                regex = re.compile(pattern, re.IGNORECASE)
                for sentence in sentences:
                    if regex.search(sentence):
                        reproduced.append({
                            "function_id": function_id,
                            "function": label,
                            "evidence": sentence,
                        })
                        break
            self.assertEqual(reproduced, sheet["functions_claimed"])
            self.assertEqual(reproduced, [])

    def test_census_citation_verifies_but_is_not_evidence(self):
        """The census recorded exactly 1 citation for this fork;
        it verifies as a verbatim substring of the raw description
        and of the sheet's normalized description, and it is the
        evidence sentence for no claim (there are no claims).
        Verification is not a claim, in either direction."""
        with open(_REMAINDER_PATH) as fh:
            rem = json.load(fh)
        census = [r for r in rem["forks"] if r["fork_id"] == EXPECTED_FORK]
        self.assertEqual(len(census), 1)
        self.assertEqual(len(census[0]["citations"]), 1)
        citation = census[0]["citations"][0]
        product = _load_raw_product()
        self.assertIn(citation, product["service_desc"])
        for sheet in _load_sheets():
            self.assertIn(citation, sheet["description"])
            evidence = {c["evidence"] for c in sheet["functions_claimed"]}
            self.assertNotIn(citation, evidence)

    def test_near_miss_substance_present_but_unclaimed(self):
        """Substance pins: the description DOES contain grading
        vocabulary, a reporting phrase, and a user-management
        phrase (the zero is not an empty description), and no
        scoring family exists in the taxonomy for the grading
        words to fire."""
        for sheet in _load_sheets():
            desc = sheet["description"]
            self.assertIn("grading", desc)
            self.assertIn("Reporting and data analysis", desc)
            self.assertIn("User management", desc)
            self.assertNotIn("scor", desc.lower())
        family_ids = {fid for fid, _, _ in _founding_taxonomy()}
        self.assertFalse(any("scor" in fid or "grad" in fid
                             for fid in family_ids))

    def test_certified_services_catalogue_is_empty(self):
        """CATALOGUE DISCIPLINE: the source record's
        ``certified_services`` list is empty -- no claim could
        have rested on a third-party catalogue, and the exclusion
        pass had nothing to remove."""
        product = _load_raw_product()
        self.assertEqual(product.get("certified_services") or [], [])


if __name__ == "__main__":
    unittest.main()
