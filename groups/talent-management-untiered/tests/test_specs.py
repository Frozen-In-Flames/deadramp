"""Spec integrity: the 2 untiered forks of this group.

Traces to: remainder.json build unit ``untiered:Talent Management``
(kind ``untiered_set``, tier null, 2 forks) and the spec sheets
built for it in ``specs/specs.json`` (Untiered Set 21).

These forks carry no tier in the source census, so the sheets must
carry no tier either. The pins here are:

- The spec sheet count is exactly 2, in census unit order.
- The sheet fork_id list is exactly the fork_ids list of the
  remainder.json unit ``untiered:Talent Management``.
- TIER DISCIPLINE: the unit's tier is null, every sheet's
  ``cmmc_tier`` is None and every sheet's
  ``fedramp_impact_level`` is ``"Unknown"`` — no tier or impact
  level is invented for forks the census left untiered.
- Every sheet's description is byte-equal to the cached
  ``service_desc`` and to the census copy in
  ``remainder/uncovered.json``; registry fields match forks.json;
  source business categories are recorded as-is.
- The literal claim table: exactly 0 claims across the set, and
  BOTH forks are zero-claim. The founding taxonomy's phrases occur
  in neither description (substance nearby is itemized in
  scratch/ARTIFACTS.md and registered as gaps, never tagged).
- Census citations: 4 of 4 verify as verbatim substrings of the
  descriptions; 0 serve as claim evidence (there are no claims).
- certified_services discipline: CodeSignal's record carries a
  14-entry certified_services list (including "SSO (SAML) and
  SCIM Provisioning" and assessment entries naming scores and
  session recordings); that field is never matched, and no claim
  or documented control rests on it — pinned by the zero-claim
  table together with the token checks below.
"""

import json
import os
import re
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")

UNIT_ID = "untiered:Talent Management"
EXPECTED_CATEGORY = "Talent Management"
EXPECTED_COUNT = 2
EXPECTED_TOTAL_CLAIMS = 0
EXPECTED_ZERO_CLAIM_FORKS = {"FR2635930425", "FR2631747327"}
EXPECTED_ORDER = ["FR2635930425", "FR2631747327"]


def _load_repo(relpath):
    with open(os.path.join(_REPO_ROOT, relpath), encoding="utf-8") as fh:
        return json.load(fh)


def _load_sheets():
    with open(_SPECS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _load_unit():
    rem = _load_repo("remainder.json")
    units = [u for u in rem["build_units"] if u["unit_id"] == UNIT_ID]
    assert len(units) == 1, units
    return units[0], rem


class TestUntieredSpecSheets(unittest.TestCase):
    """Spec integrity + tier-discipline pins for the 2 untiered forks."""

    @classmethod
    def setUpClass(cls):
        cls.sheets = _load_sheets()
        cls.unit, cls.remainder = _load_unit()
        dump = _load_repo("raw/data_dump.json")
        products = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
        cls.cache = {p["id"]: p for p in products
                     if isinstance(p, dict) and "id" in p}
        cls.uncovered = {r["fork_id"]: r
                         for r in _load_repo("remainder/uncovered.json")}
        registry = _load_repo("forks.json")
        cls.registry = {r["source_url"].rstrip("/").rsplit("/", 1)[-1]: r
                        for r in registry}
        cls.census = {r["fork_id"]: r for r in cls.remainder["forks"]}

    def test_sheet_count_and_order(self):
        """The untiered set holds exactly 2 sheets, in census order."""
        self.assertEqual(len(self.sheets), EXPECTED_COUNT)
        self.assertEqual([s["fork_id"] for s in self.sheets],
                         EXPECTED_ORDER)

    def test_membership_matches_remainder_unit(self):
        """Sheet fork IDs == the fork_ids of remainder.json unit
        `untiered:Talent Management` — no more, no fewer, in order."""
        self.assertEqual(self.unit["kind"], "untiered_set")
        self.assertEqual(len(self.unit["fork_ids"]), EXPECTED_COUNT)
        self.assertEqual([s["fork_id"] for s in self.sheets],
                         self.unit["fork_ids"])

    def test_tier_discipline_no_tier_is_invented(self):
        """TIER DISCIPLINE: the unit's tier is null, so every sheet's
        ``cmmc_tier`` is None and every sheet's
        ``fedramp_impact_level`` is ``"Unknown"``."""
        self.assertIsNone(self.unit["tier"])
        for sheet in self.sheets:
            with self.subTest(fork=sheet["fork_id"]):
                self.assertIsNone(sheet["cmmc_tier"])
                self.assertEqual(sheet["fedramp_impact_level"],
                                 "Unknown")
                self.assertIsNone(
                    self.registry[sheet["fork_id"]]["cmmc_tier"])
                self.assertEqual(
                    self.registry[sheet["fork_id"]]
                    ["fedramp_impact_level"], "Unknown")

    def test_descriptions_byte_equal_to_cache_and_census(self):
        """Each sheet's description is the cached service_desc
        verbatim and equals the census copy in uncovered.json;
        neither contains a carriage return."""
        for sheet in self.sheets:
            with self.subTest(fork=sheet["fork_id"]):
                record = self.cache[sheet["fork_id"]]
                self.assertEqual(sheet["description"],
                                 record["service_desc"])
                self.assertEqual(
                    sheet["description"],
                    self.uncovered[sheet["fork_id"]]["description"])
                self.assertNotIn("\r", sheet["description"])

    def test_registry_fields_and_categories_recorded_as_is(self):
        """Vendor, product, status, and service model match
        forks.json; deadramp_category is Talent Management on both
        sheets; source business categories are recorded as-is
        (CodeSignal's five, including Talent Management; VOS
        Sapphire's empty list — its filed category is
        "Uncategorized (none in source)")."""
        for sheet in self.sheets:
            with self.subTest(fork=sheet["fork_id"]):
                reg = self.registry[sheet["fork_id"]]
                self.assertEqual(sheet["vendor"], reg["vendor"])
                self.assertEqual(sheet["product"], reg["product"])
                self.assertEqual(sheet["authorization_status"],
                                 reg["authorization_status"])
                self.assertEqual(sheet["authorization_status"],
                                 "Initial Implementation")
                self.assertEqual(sheet["service_model"], ["SaaS"])
                self.assertEqual(sheet["deadramp_category"],
                                 EXPECTED_CATEGORY)
                self.assertEqual(
                    sheet["business_categories_in_source"],
                    self.cache[sheet["fork_id"]].get(
                        "business_categories") or [])
        by_id = {s["fork_id"]: s for s in self.sheets}
        self.assertEqual(
            by_id["FR2635930425"]["business_categories_in_source"],
            ["Human Resources", "Talent Management",
             "Talent Development", "Education & Training",
             "Artificial Intelligence (AI)"])
        self.assertEqual(
            by_id["FR2631747327"]["business_categories_in_source"],
            [])
        self.assertEqual(self.registry["FR2635930425"]["category"],
                         "Human Resources")
        self.assertEqual(self.registry["FR2631747327"]["category"],
                         "Uncategorized (none in source)")

    def test_literal_claim_table_zero_claims(self):
        """The set carries exactly 0 claims in total, and the
        zero-claim set is exactly both forks — a fork gaining a
        claim fails here rather than drifting silently."""
        total = sum(len(s["functions_claimed"]) for s in self.sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        zero = {s["fork_id"] for s in self.sheets
                if not s["functions_claimed"]}
        self.assertEqual(zero, EXPECTED_ZERO_CLAIM_FORKS)
        for sheet in self.sheets:
            self.assertEqual(sheet["functions_claimed"], [])

    def test_evidence_rule_is_vacuously_verbatim(self):
        """Every claim's evidence is a verbatim substring of its
        sheet's description (the set has no claims; the rule is
        pinned so a future claim is held to it)."""
        for sheet in self.sheets:
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"])

    def test_census_citations_verify_but_are_not_claims(self):
        """4 of 4 census citations verify as whitespace-normalized
        verbatim substrings of the forks' own descriptions, and
        none serves as claim evidence (there are no claims).
        Verification is not a claim, in either direction."""
        verified = 0
        total = 0
        for sheet in self.sheets:
            desc = re.sub(r"\s+", " ", sheet["description"])
            for citation in self.census[sheet["fork_id"]]["citations"]:
                total += 1
                self.assertIn(re.sub(r"\s+", " ", citation), desc,
                              (sheet["fork_id"], citation[:60]))
                verified += 1
        self.assertEqual((verified, total), (4, 4))

    def test_substance_tokens_present_but_untagged(self):
        """Verb discipline pins: substance is present in other
        words and earns no claim. CodeSignal carries "screening
        interviews" and "pre-hire assessments" but never
        "recruitment assessments" or "video interviews"; VOS
        Sapphire carries the noun "automation" but never the verb
        "automate" the pipeline_automation pattern requires."""
        by_id = {s["fork_id"]: s for s in self.sheets}
        cs = by_id["FR2635930425"]["description"]
        vos = by_id["FR2631747327"]["description"]
        self.assertIn("screening interviews", cs)
        self.assertIn("pre-hire assessments", cs)
        self.assertNotIn("recruitment assessments", cs)
        self.assertNotIn("video interviews", cs)
        self.assertNotIn("artificial intelligence", cs)
        self.assertIn("automation", vos)
        self.assertIsNone(re.search(r"\bautomate\b", vos))
        for desc in (cs, vos):
            self.assertNotIn("talent acquisition", desc)
            self.assertNotIn("develop talent", desc)

    def test_certified_services_never_matched(self):
        """CodeSignal's certified_services list (14 entries) names
        scores, session recordings, and an "SSO (SAML) and SCIM
        Provisioning" service; none of that text is in its
        service_desc claim surface: "score" occurs in neither
        description, and no sheet carries a claim sourced from the
        field (both sheets carry no claims at all)."""
        record = self.cache["FR2635930425"]
        services = record.get("certified_services") or []
        self.assertEqual(len(services), 14)
        names = [e.get("serviceName") for e in services]
        self.assertIn("SSO (SAML) and SCIM Provisioning", names)
        joined = json.dumps(services)
        self.assertIn("scores", joined)
        for sheet in self.sheets:
            self.assertIsNone(
                re.search(r"\bscore", sheet["description"],
                          re.IGNORECASE), sheet["fork_id"])
            self.assertEqual(sheet["functions_claimed"], [])


if __name__ == "__main__":
    unittest.main()
