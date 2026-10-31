"""Spec integrity: the 2 untiered forks of this group.

Traces to: remainder.json build unit ``untiered:Law Enforcement``
(kind ``untiered_set``, tier null, 2 forks) and the spec sheets built
for it in ``specs/specs.json``.

This is the untiered set for Law Enforcement: its forks carry no
tier in the source census, so the sheets must carry no tier either.
The pins here are:

- The spec sheet count is exactly 2.
- The sheet fork_id set is exactly the fork_ids set of the
  remainder.json unit ``untiered:Law Enforcement``.
- TIER DISCIPLINE: every sheet's ``cmmc_tier`` is None and every
  sheet's ``fedramp_impact_level`` is ``"Unknown"`` — no tier or
  impact level is invented for forks the census left untiered.
- Every claim's evidence is a verbatim substring of that sheet's
  description, or a truncated form of it (evidence ending in
  ``"..."`` whose prefix is a verbatim substring — the truncation
  rule: description-sentence[:397] + ``"..."``).
- Every sheet's ``deadramp_category`` is ``"Law Enforcement"``.
- The literal claim totals: exactly 0 claims across the set, and
  both forks zero-claim (FR2628943632, Pryme Infil, and
  FR2631258113, TRM Labs on GovCloud). The founding taxonomy is a
  legal-research taxonomy applied verbatim; these two operational
  descriptions fire none of its phrases, and the taxonomy is not
  re-tuned to catch them.
- CATEGORY DISCIPLINE: the founding group's excluded vocabulary —
  facial recognition, predictive policing, surveillance,
  camera/sensor monitoring, real-time intelligence feeds — is never
  attributed to a fork. The tokens ``facial``, ``predictive``,
  ``surveillance``, ``camera``, ``sensor`` and the phrase
  ``real-time intelligence`` occur 0 times in each description
  (Pryme Infil's own words are "real-time team coordination", a
  coordination phrase, recorded as an Extended gap, never as an
  intelligence feed).
- Every sheet's description is exactly the description recorded for
  that fork in ``remainder/uncovered.json``.
- The census citations for these forks verify as verbatim
  substrings of their descriptions (2 of 2); neither serves as a
  claim evidence sentence, because there are no claims.
"""

import json
import os
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")
_UNCOVERED_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder",
                               "uncovered.json")

UNIT_ID = "untiered:Law Enforcement"
EXPECTED_CATEGORY = "Law Enforcement"
EXPECTED_COUNT = 2
EXPECTED_TOTAL_CLAIMS = 0
EXPECTED_ZERO_CLAIM_FORKS = {"FR2628943632", "FR2631258113"}
DISCIPLINE_TOKENS = ["facial", "predictive", "surveillance", "camera",
                     "sensor", "real-time intelligence"]


def _load_sheets():
    with open(_SPECS_PATH) as fh:
        return json.load(fh)


def _load_unit():
    with open(_REMAINDER_PATH) as fh:
        rem = json.load(fh)
    units = [u for u in rem["build_units"] if u["unit_id"] == UNIT_ID]
    assert len(units) == 1, units
    return units[0]


def _load_census():
    with open(_REMAINDER_PATH) as fh:
        rem = json.load(fh)
    return {r["fork_id"]: r for r in rem["forks"]}


def _load_uncovered():
    with open(_UNCOVERED_PATH) as fh:
        rows = json.load(fh)
    return {r["fork_id"]: r for r in rows}


class TestUntieredSpecSheets(unittest.TestCase):
    """Spec integrity + tier-discipline pins for the 2 untiered forks."""

    def test_sheet_count_is_exactly_2(self):
        """The untiered set holds exactly 2 sheets, each fork once."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), EXPECTED_COUNT)
        ids = [s["fork_id"] for s in sheets]
        self.assertEqual(len(set(ids)), EXPECTED_COUNT)

    def test_fork_id_set_matches_remainder_unit(self):
        """The sheet fork_id set == the fork_ids set of remainder.json
        unit `untiered:Law Enforcement` — no more, no fewer."""
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
            # The founding extractor's sentence rule replaces \r with
            # a space before splitting where a parent rule did so;
            # this set's descriptions contain no \r at all, and with
            # zero claims the check is vacuous — it stands so a
            # future claim cannot drift in unverified.
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
        ``"Law Enforcement"`` (the census assignment)."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertEqual(sheet["deadramp_category"],
                                 EXPECTED_CATEGORY)

    def test_claim_totals_are_pinned_literally(self):
        """The set carries exactly 0 claims in total, and the
        zero-claim set is exactly {FR2628943632, FR2631258113} — a
        fork gaining a claim fails here rather than drifting in
        silently, because a claim here could only come from
        re-tuning the founding taxonomy."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        zero = {s["fork_id"] for s in sheets if not s["functions_claimed"]}
        self.assertEqual(zero, EXPECTED_ZERO_CLAIM_FORKS)

    def test_category_discipline_tokens_absent(self):
        """CATEGORY DISCIPLINE: ``facial``, ``predictive``,
        ``surveillance``, ``camera``, ``sensor`` and the phrase
        ``real-time intelligence`` occur 0 times in each sheet's
        description — the founding group's excluded vocabulary is
        not attributed to these forks in any form."""
        for sheet in _load_sheets():
            low = sheet["description"].lower()
            for token in DISCIPLINE_TOKENS:
                with self.subTest(fork=sheet["fork_id"], token=token):
                    self.assertEqual(low.count(token), 0,
                                     (sheet["fork_id"], token))

    def test_descriptions_match_the_census_record(self):
        """Every sheet's description is exactly the description in
        remainder/uncovered.json for that fork."""
        uncovered = _load_uncovered()
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertEqual(sheet["description"],
                                 uncovered[sheet["fork_id"]]["description"])

    def test_census_citations_verify_verbatim(self):
        """Every census citation for these forks is a verbatim
        substring of the fork's description (whitespace-normalized
        fallback allowed, per the house rule), and none serves as a
        claim evidence sentence — verification is not a claim, in
        either direction."""
        census = _load_census()
        for sheet in _load_sheets():
            cites = census[sheet["fork_id"]].get("citations") or []
            self.assertTrue(cites, sheet["fork_id"])
            desc = sheet["description"]
            norm = " ".join(desc.split())
            evidence = {" ".join(c["evidence"].split())
                        for c in sheet["functions_claimed"]}
            for cite in cites:
                txt = cite if isinstance(cite, str) else (
                    cite.get("sentence") or cite.get("text") or "")
                with self.subTest(fork=sheet["fork_id"], cite=txt[:40]):
                    self.assertTrue(
                        txt in desc or " ".join(txt.split()) in norm)
                    self.assertNotIn(" ".join(txt.split()), evidence)


if __name__ == "__main__":
    unittest.main()
