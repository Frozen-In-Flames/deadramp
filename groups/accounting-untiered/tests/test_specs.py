"""Spec integrity: the 1 untiered fork of this group.

Traces to: remainder.json build unit ``untiered:Accounting`` (kind
``untiered_set``, tier null, 1 fork) and the spec sheet built for it
in ``specs/specs.json``.

This is an untiered set for Accounting: its fork carries no tier in
the source census, so the sheet must carry no tier either. The pins
here are:

- The spec sheet count is exactly 1.
- The sheet fork_id set is exactly the fork_ids set of the
  remainder.json unit ``untiered:Accounting``.
- TIER DISCIPLINE: the sheet's ``cmmc_tier`` is None and its
  ``fedramp_impact_level`` is ``"Unknown"`` — no tier or impact
  level is invented for a fork the census left untiered.
- Every claim's evidence is a verbatim substring of the sheet's
  description, or a truncated form of it (evidence ending in
  ``"..."`` whose prefix is a verbatim substring — the truncation
  rule: description-sentence[:397] + ``"..."``).
- The sheet's ``deadramp_category`` is ``"Accounting"``.
- The literal claim totals: exactly 3 claims on the one fork, and
  no zero-claim fork. One of the three (``financial_reporting``)
  stands at artifact weight — it fires on "vulnerability-reporting
  processes", a security-transparency phrase, not a financial
  reporting function; the artifact is recorded in
  ``scratch/ARTIFACTS.md``, and the pin here keeps the count from
  drifting silently in either direction.
"""

import json
import os
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")

UNIT_ID = "untiered:Accounting"
EXPECTED_CATEGORY = "Accounting"
EXPECTED_COUNT = 1
EXPECTED_TOTAL_CLAIMS = 3
EXPECTED_ZERO_CLAIM_FORKS = set()
EXPECTED_CLAIM_FAMILIES = {"financial_reporting", "audit",
                           "access_control"}


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
    """Spec integrity + tier-discipline pins for the 1 untiered fork."""

    def test_sheet_count_is_exactly_1(self):
        """The untiered set holds exactly 1 sheet."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), EXPECTED_COUNT)
        ids = [s["fork_id"] for s in sheets]
        self.assertEqual(len(set(ids)), EXPECTED_COUNT)

    def test_fork_id_set_matches_remainder_unit(self):
        """The sheet fork_id set == the fork_ids set of remainder.json
        unit `untiered:Accounting` — no more, no fewer."""
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
        sheet's description, OR equals description-sentence[:397] +
        '...' under the truncation rule (evidence ends with '...'
        and evidence[:-3] is a verbatim substring)."""
        for sheet in _load_sheets():
            # extract.py's sentence rule replaces \r with a space
            # before splitting; evidence is verbatim under that one
            # documented normalization (carried from the parent
            # group's method — this set's description contains no
            # \r, so the normalization changes nothing here).
            desc = sheet["description"].replace("\r", " ")
            for claim in sheet["functions_claimed"]:
                ev = claim["evidence"]
                with self.subTest(fork=sheet["fork_id"],
                                  function=claim["function_id"]):
                    self.assertTrue(
                        ev in desc
                        or (ev.endswith("...") and ev[:-3] in desc),
                        (sheet["fork_id"], claim["function_id"], ev[:80]),
                    )

    def test_every_sheet_carries_the_group_category(self):
        """The sheet's ``deadramp_category`` is ``"Accounting"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertEqual(sheet["deadramp_category"],
                                 EXPECTED_CATEGORY)

    def test_claim_totals_are_pinned_literally(self):
        """The set carries exactly 3 claims in total, on exactly the
        families {financial_reporting, audit, access_control}, and
        the zero-claim set is empty — a claim gained or lost, or the
        fork falling to zero, fails here rather than drifting
        silently."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        families = {c["function_id"] for s in sheets
                    for c in s["functions_claimed"]}
        self.assertEqual(families, EXPECTED_CLAIM_FAMILIES)
        zero = {s["fork_id"] for s in sheets if not s["functions_claimed"]}
        self.assertEqual(zero, EXPECTED_ZERO_CLAIM_FORKS)


if __name__ == "__main__":
    unittest.main()
