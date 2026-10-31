"""Spec integrity: the 6 untiered forks of this group.

Traces to: remainder.json build unit ``untiered:Education & Training``
(kind ``untiered_set``, tier null, 6 forks) and the spec sheets built
for it in ``specs/specs.json``.

This is the FIRST untiered set for Education & Training: its forks
carry no tier in the source census, so the sheets must carry no tier
either. The pins here are:

- The spec sheet count is exactly 6.
- The sheet fork_id set is exactly the fork_ids set of the
  remainder.json unit ``untiered:Education & Training``.
- TIER DISCIPLINE: every sheet's ``cmmc_tier`` is None and every
  sheet's ``fedramp_impact_level`` is ``"Unknown"`` — no tier or
  impact level is invented for forks the census left untiered.
  (Dossier's prose FIPS 199 categorization statement does not
  convert into a tier; see scratch/ARTIFACTS.md.)
- Every claim's evidence is a verbatim substring of that sheet's
  description, or a truncated form of it (evidence ending in
  ``"..."`` whose prefix is a verbatim substring — the truncation
  rule: description-sentence[:397] + ``"..."``).
- Every sheet's ``deadramp_category`` is ``"Education & Training"``.
- The literal claim totals: exactly 29 claims across the set, the
  exact per-fork claim table, and exactly one zero-claim fork
  (FR1916744879, Proofpoint — its outcome prose fires no family
  pattern; the taxonomy is not re-tuned to catch it).
- The exclusion-pass pin: no claim's evidence sentence carries
  scope-exclusion phrasing, and Toonimo (FR2635050850) carries no
  certificates_credentials claim — its one raw hit rested on its own
  FedRAMP target-certification sentence and was removed (see
  scratch/ARTIFACTS.md).
"""

import json
import os
import re
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")

UNIT_ID = "untiered:Education & Training"
EXPECTED_CATEGORY = "Education & Training"
EXPECTED_COUNT = 6
EXPECTED_TOTAL_CLAIMS = 29
EXPECTED_ZERO_CLAIM_FORKS = {"FR1916744879"}
EXPECTED_CLAIMS = {
    "FR2700137041": ["course_catalog", "learner_progress", "assessments",
                     "certificates_credentials", "scheduling",
                     "reporting_analytics", "access_control",
                     "ai_automation", "hosting_platform"],
    "FR1912662229": ["course_catalog", "enrollment_registration",
                     "learner_progress", "scheduling", "content_media",
                     "reporting_analytics", "ai_automation"],
    "FR2635447609": ["course_catalog", "assessments",
                     "certificates_credentials", "scheduling",
                     "reporting_analytics", "recruitment_workforce"],
    "FR1916744879": [],
    "FR2633734917": ["course_catalog", "scheduling", "simulations",
                     "reporting_analytics", "hosting_platform"],
    "FR2635050850": ["reporting_analytics", "ai_automation"],
}
_SCOPE_EXCLUSION_RX = re.compile(
    r"(not authorized|not included|not part of|out of scope|"
    r"outside (the )?(scope|boundary|assessed scope)|not covered by|"
    r"excluded from|not offered to|undergoing approval|"
    r"target certification|for transparency only)", re.I)


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
    """Spec integrity + tier-discipline pins for the 6 untiered forks."""

    def test_sheet_count_is_exactly_6(self):
        """The untiered set holds exactly 6 sheets, each fork once."""
        sheets = _load_sheets()
        self.assertEqual(len(sheets), EXPECTED_COUNT)
        ids = [s["fork_id"] for s in sheets]
        self.assertEqual(len(set(ids)), EXPECTED_COUNT)

    def test_fork_id_set_matches_remainder_unit(self):
        """The sheet fork_id set == the fork_ids set of remainder.json
        unit `untiered:Education & Training` — no more, no fewer."""
        sheets = _load_sheets()
        unit = _load_unit()
        self.assertEqual(len(unit["fork_ids"]), EXPECTED_COUNT)
        self.assertIsNone(unit["tier"])
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
            # group's test_additions.py — a raw substring check
            # against an un-normalized description can fail claims
            # whose source descriptions contain \r despite the
            # evidence being verbatim). No description in this set
            # contains \r; the normalization is applied anyway so
            # the pin states the rule, not an accident of the data.
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
        ``"Education & Training"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertEqual(sheet["deadramp_category"],
                                 EXPECTED_CATEGORY)

    def test_claim_totals_are_pinned_literally(self):
        """The set carries exactly 29 claims in total, and the
        zero-claim set is exactly {FR1916744879} — a fork gaining or
        losing a claim, or a second fork falling to zero, fails here
        rather than drifting silently."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        zero = {s["fork_id"] for s in sheets if not s["functions_claimed"]}
        self.assertEqual(zero, EXPECTED_ZERO_CLAIM_FORKS)

    def test_per_fork_claim_table_is_pinned_literally(self):
        """The exact per-fork family lists, in taxonomy order — the
        table scratch/extract.py produced under the founding group's
        verbatim taxonomy (see scratch/ARTIFACTS.md for the weights:
        Dossier's and KnowBe4's ai_automation hits are automation
        wording, and Dossier's certificates claim is records weight)."""
        sheets = _load_sheets()
        got = {s["fork_id"]: [c["function_id"]
                              for c in s["functions_claimed"]]
               for s in sheets}
        self.assertEqual(got, EXPECTED_CLAIMS)

    def test_no_claim_evidence_is_scope_exclusion_prose(self):
        """Exclusion-pass pin: no claim's evidence sentence carries
        scope-exclusion phrasing. The set's one removed hit (Toonimo,
        FR2635050850 — its own "Target certification: FedRAMP 20x
        Class C (Moderate) via Program Certification" sentence)
        supports no claim; if a future re-extraction ever rested a
        claim on such a sentence, it fails here."""
        for sheet in _load_sheets():
            for claim in sheet["functions_claimed"]:
                with self.subTest(fork=sheet["fork_id"],
                                  function=claim["function_id"]):
                    self.assertIsNone(
                        _SCOPE_EXCLUSION_RX.search(claim["evidence"]),
                        (sheet["fork_id"], claim["function_id"],
                         claim["evidence"][:80]),
                    )

    def test_toonimo_certification_hit_stays_removed(self):
        """The exclusion removal itself is pinned: Toonimo's sheet
        carries no certificates_credentials claim, even though its
        description contains the word "certification" — the word
        occurs only in its own FedRAMP target-certification and
        program-certification sentences."""
        sheets = {s["fork_id"]: s for s in _load_sheets()}
        toonimo = sheets["FR2635050850"]
        self.assertIn("certification", toonimo["description"])
        fams = [c["function_id"] for c in toonimo["functions_claimed"]]
        self.assertNotIn("certificates_credentials", fams)


if __name__ == "__main__":
    unittest.main()
