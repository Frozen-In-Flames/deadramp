"""Spec integrity: the 1 untiered fork of this set.

Traces to: remainder.json build unit ``untiered:Finance`` (kind
``untiered_set``, tier null, 1 fork) and the spec sheet built for it
in ``specs/specs.json``.

This is the FIRST untiered set for Finance: its fork carries no tier
in the source census, so the sheet must carry no tier either. The
pins here are:

- The spec sheet count is exactly 1.
- The sheet fork_id set is exactly the fork_ids set of the
  remainder.json unit ``untiered:Finance``.
- TIER DISCIPLINE: the sheet's ``cmmc_tier`` is None and its
  ``fedramp_impact_level`` is ``"Unknown"`` — no tier or impact
  level is invented for a fork the census left untiered, and the
  Finance L3 singleton's High uplifts are not inherited anywhere in
  this tree (the carried source is the L2 founding build's,
  byte-identical — accounted in tests/README.md).
- Every claim's evidence is a verbatim substring of the sheet's
  description. The founding Finance extractor applies no truncation
  and no carriage-return normalization (its evidence rule stores the
  first matching sentence whole), so the check here is a raw
  substring check; the description contains no carriage return,
  pinned below.
- The sheet's ``deadramp_category`` is ``"Finance"``.
- The literal claim table: exactly 1 claim across the set, on
  exactly the family {reporting}; the zero-claim set is empty. The
  one claim stands at artifact weight (it fires on "employee
  expense reporting", the filing workflow — recorded in
  scratch/ARTIFACTS.md), and artifact weight is a reading note, not
  a different claim: the table pins the claim as tagged.
- Named-absence tokens: the words and phrases the absent families
  would need occur nowhere in the description — "spend" (the fork's
  whole domain is expenses, yet the token never occurs; "expense"
  does not contain it), "booking", "travel management", "travel
  for meetings", "access to earned wages", "financial wellness",
  "open technology platform", "SaaS offering", "multi-tenant", and
  "encrypt" (no encryption claim is documented anywhere in this
  set).
- The census citation for this fork verifies as a verbatim
  substring of the description AND is the claim's evidence sentence
  (1 of 1 in both directions — recorded in
  scratch/citation_check.json; verification is not what makes it a
  claim, the taxonomy match is).
"""

import json
import os
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")

UNIT_ID = "untiered:Finance"
EXPECTED_CATEGORY = "Finance"
EXPECTED_COUNT = 1
EXPECTED_TOTAL_CLAIMS = 1
EXPECTED_FAMILIES = {"reporting"}
EXPECTED_ZERO_CLAIM_FORKS = set()
ABSENT_TOKENS = [
    "spend", "booking", "travel management", "travel for meetings",
    "access to earned wages", "financial wellness",
    "open technology platform", "saas offering", "multi-tenant",
    "encrypt",
]


def _load_sheets():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


def _load_unit():
    with open(_REMAINDER_PATH) as fh:
        rem = json.load(fh)
    units = [u for u in rem["build_units"] if u["unit_id"] == UNIT_ID]
    assert len(units) == 1, units
    return units[0]


class TestUntieredSpecSheets(unittest.TestCase):
    """Spec integrity + tier-discipline pins for the untiered fork."""

    def test_sheet_count_is_exactly_1(self):
        """The untiered set holds exactly 1 sheet."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), EXPECTED_COUNT)
        ids = [s["fork_id"] for s in sheets]
        self.assertEqual(len(set(ids)), EXPECTED_COUNT)

    def test_fork_id_set_matches_remainder_unit(self):
        """The sheet fork_id set == the fork_ids set of remainder.json
        unit `untiered:Finance` — no more, no fewer."""
        sheets = _load_sheets()
        unit = _load_unit()
        self.assertEqual(len(unit["fork_ids"]), EXPECTED_COUNT)
        self.assertEqual({s["fork_id"] for s in sheets},
                         set(unit["fork_ids"]))

    def test_tier_discipline_no_tier_is_invented(self):
        """TIER DISCIPLINE: the unit's tier is null, so the sheet's
        ``cmmc_tier`` is None and its ``fedramp_impact_level`` is
        ``"Unknown"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertIsNone(sheet["cmmc_tier"])
                self.assertEqual(sheet["fedramp_impact_level"],
                                 "Unknown")

    def test_every_claim_evidence_is_verbatim(self):
        """Every claim's evidence is a verbatim substring of the
        sheet's description. The founding Finance evidence rule
        stores the first matching sentence whole (no truncation, no
        normalization), so this is a raw substring check; the
        description is also pinned carriage-return-free, the
        condition under which the founding group's evidence checks
        need no normalization note."""
        for sheet in _load_sheets():
            self.assertNotIn("\r", sheet["description"])
            for claim in sheet["functions_claimed"]:
                ev = claim["evidence"]
                with self.subTest(fork=sheet["fork_id"],
                                  function=claim["function_id"]):
                    self.assertIn(ev, sheet["description"])

    def test_every_sheet_carries_the_group_category(self):
        """The sheet's ``deadramp_category`` is ``"Finance"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertEqual(sheet["deadramp_category"],
                                 EXPECTED_CATEGORY)

    def test_claim_totals_are_pinned_literally(self):
        """The set carries exactly 1 claim in total, on exactly the
        family {reporting}, and the zero-claim set is empty — a fork
        gaining or losing a claim fails here rather than drifting
        silently."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        families = {c["function_id"] for s in sheets
                    for c in s["functions_claimed"]}
        self.assertEqual(families, EXPECTED_FAMILIES)
        zero = {s["fork_id"] for s in sheets if not s["functions_claimed"]}
        self.assertEqual(zero, EXPECTED_ZERO_CLAIM_FORKS)

    def test_named_absence_tokens_occur_nowhere(self):
        """The phrases the seven absent families (and any encryption
        claim) would need occur nowhere in the description — the
        absences are provable from the record, not asserted."""
        for sheet in _load_sheets():
            desc = sheet["description"].lower()
            for token in ABSENT_TOKENS:
                with self.subTest(token=token):
                    self.assertNotIn(token, desc)


if __name__ == "__main__":
    unittest.main()
