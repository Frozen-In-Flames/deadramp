"""Spec integrity: the 8 untiered forks of this group.

Traces to: remainder.json build unit ``untiered:Data Management``
(kind ``untiered_set``, tier null, 8 forks) and the spec sheets built
for it in ``specs/specs.json``.

This is an untiered set for Data Management: its forks carry no tier
in the source census, so the sheets must carry no tier either. The
pins here are:

- The spec sheet count is exactly 8.
- The sheet fork_id set is exactly the fork_ids set of the
  remainder.json unit ``untiered:Data Management``.
- TIER DISCIPLINE: every sheet's ``cmmc_tier`` is None and every
  sheet's ``fedramp_impact_level`` is ``"Unknown"`` — no tier or
  impact level is invented for forks the census left untiered.
- Every claim's evidence is a verbatim substring of that sheet's
  description, or a truncated form of it (evidence ending in
  ``"..."`` whose prefix is a verbatim substring — the truncation
  rule: description-sentence[:397] + ``"..."``).
- Every sheet's ``deadramp_category`` is ``"Data Management"``.
- The literal claim totals: exactly 13 claims across the set, and
  exactly two zero-claim forks (FR2630354495, Files.com — "transfer
  files" is not "managed file transfer"; FR2629068832, OATI
  Marketplace — "warehousing, and retrieval" matches no family; the
  taxonomy is not re-tuned to catch either).
"""

import json
import os
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")

UNIT_ID = "untiered:Data Management"
EXPECTED_CATEGORY = "Data Management"
EXPECTED_COUNT = 8
EXPECTED_TOTAL_CLAIMS = 13
EXPECTED_ZERO_CLAIM_FORKS = {"FR2630354495", "FR2629068832"}


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
    """Spec integrity + tier-discipline pins for the 8 untiered forks."""

    def test_sheet_count_is_exactly_8(self):
        """The untiered set holds exactly 8 sheets, each fork once."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), EXPECTED_COUNT)
        ids = [s["fork_id"] for s in sheets]
        self.assertEqual(len(set(ids)), EXPECTED_COUNT)

    def test_fork_id_set_matches_remainder_unit(self):
        """The sheet fork_id set == the fork_ids set of remainder.json
        unit `untiered:Data Management` — no more, no fewer."""
        sheets = _load_sheets()
        unit = _load_unit()
        self.assertEqual(len(unit["fork_ids"]), EXPECTED_COUNT)
        self.assertEqual({s["fork_id"] for s in sheets},
                         set(unit["fork_ids"]))

    def test_tier_discipline_no_tier_is_invented(self):
        """TIER DISCIPLINE: the unit's tier is null, so every sheet's
        ``cmmc_tier`` is None and every sheet's
        ``fedramp_impact_level`` is ``"Unknown"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertIsNone(sheet["cmmc_tier"])
                self.assertEqual(sheet["fedramp_impact_level"],
                                 "Unknown")

    def test_every_claim_evidence_is_verbatim(self):
        """Every claim's evidence is a verbatim substring of that
        sheet's description, OR equals description-sentence[:397] +
        '...' under the truncation rule (evidence ends with '...'
        and evidence[:-3] is a verbatim substring)."""
        for sheet in _load_sheets():
            # extract.py's sentence rule replaces \r with a space
            # before splitting; evidence is verbatim under that one
            # documented normalization (carried from the parent
            # group's test suites).
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
        """Every sheet's ``deadramp_category`` is
        ``"Data Management"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertEqual(sheet["deadramp_category"],
                                 EXPECTED_CATEGORY)

    def test_claim_totals_are_pinned_literally(self):
        """The set carries exactly 13 claims in total, and the
        zero-claim set is exactly {FR2630354495, FR2629068832} — a
        fork gaining or losing a claim, or a third fork falling to
        zero, fails here rather than drifting silently."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        zero = {s["fork_id"] for s in sheets if not s["functions_claimed"]}
        self.assertEqual(zero, EXPECTED_ZERO_CLAIM_FORKS)


if __name__ == "__main__":
    unittest.main()
