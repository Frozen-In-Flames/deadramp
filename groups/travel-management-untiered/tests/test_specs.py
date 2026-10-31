"""Spec integrity: the 1 untiered fork of this set.

Traces to: remainder.json build unit ``untiered:Travel Management``
(kind ``untiered_set``, tier null, 1 fork) and the spec sheet built
for it in ``specs/specs.json``.

This is the FIRST untiered set for Travel Management (Untiered Set
28, the last untiered set): its fork carries no tier in the source
census, so the sheet must carry no tier either. The pins here are:

- The spec sheet count is exactly 1.
- The sheet fork_id set is exactly the fork_ids set of the
  remainder.json unit ``untiered:Travel Management``, and the
  unit's tier is null.
- TIER DISCIPLINE: the sheet's ``cmmc_tier`` is None and its
  ``fedramp_impact_level`` is ``"Unknown"`` — no tier or impact
  level is invented for a fork the census left untiered, and the
  founding group's Moderate baseline is not inherited anywhere in
  this tree (the carried source is the founding build's,
  byte-identical — accounted in tests/README.md).
- The literal claim table: exactly 0 claims across the set, on no
  family; the zero-claim set is exactly {FR2632558740} and the
  whole-taxonomy zero set is all 9 families. The taxonomy was
  applied verbatim (the extractor reproduced the founding group's
  shipped tables first: GO.gov 9 claims deep-equal, the addition
  fork 0 deep-equal), so the zero is the taxonomy's answer to this
  fork's words, not a tagging gap.
- The description is verbatim against the cached source (both
  duplicate cached records), and the sheet's
  ``deadramp_category`` is ``"Travel Management"``.
- Census citation accounting: the fork's 1 census citation
  verifies as a verbatim substring of its description and serves
  as claim evidence for nothing (there are no claims) —
  verification is not a claim, in either direction (recorded in
  scratch/citation_check.json).
- The no-exclusion-trap pin: the cached record's
  ``certified_services`` is empty — no third-party catalogue was
  attached to the listing, so no claim rests on an exclusion.
- The founding build's five checked absences, re-searched on THIS
  fork's own words at the token level (token lists from the
  founding scratch/ARTIFACTS.md): booking/reservation, per-diem,
  reimbursement, approval, receipt — ALL FIVE SURVIVE. An absence
  retires only on a fork's own words, never by transfer.
- Near-miss pins: "reporting" and "analysis" occur but the
  family's phrase "reporting services" does not; "aggregation"
  occurs (the fork's described function) with no family in the
  taxonomy to hold it; no control-language token (security,
  privacy, compliance, access control, audit, encrypt,
  authentication) occurs anywhere.
"""

import json
import os
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_ROOT, "remainder.json")
_DUMP_PATH = os.path.join(_ROOT, "raw", "data_dump.json")

UNIT_ID = "untiered:Travel Management"
EXPECTED_CATEGORY = "Travel Management"
EXPECTED_COUNT = 1
EXPECTED_TOTAL_CLAIMS = 0
EXPECTED_ZERO_CLAIM_FORKS = {"FR2632558740"}
ALL_FAMILIES = {
    "travel_services", "expense_services", "integration_services",
    "notification_services", "reporting_services",
    "travel_expense_operations", "security_privacy_compliance",
    "system_of_systems_composition", "cloud_hosting_platform",
}
# The founding build's checked absences, token lists verbatim from
# groups/travel-management-l2/scratch/ARTIFACTS.md (the approval
# list is probed at both stems, "approv"/"authoriz", the wider of
# the founding and addition token lists — neither occurs).
ABSENCE_TOKENS = {
    "booking_reservation": ["book", "reserv", "itinerary", "flight",
                            "airline", "hotel", "lodging", "rental"],
    "per_diem": ["per diem", "allowance", "rate table"],
    "reimbursement": ["reimburs", "voucher", "disburs"],
    "approval": ["approv", "authoriz"],
    "receipt": ["receipt", "scan", "ocr"],
}
CONTROL_TOKENS = [
    "security", "privacy", "compliance", "access control", "audit",
    "encrypt", "authentication", "single sign-on",
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


def _cached_records(fork_id):
    with open(_DUMP_PATH) as fh:
        data = json.load(fh)
    found = []

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("id") == fork_id and "service_desc" in obj:
                found.append(obj)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(data)
    return found


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
        unit `untiered:Travel Management` — no more, no fewer — and
        the unit's tier is null."""
        sheets = _load_sheets()
        unit = _load_unit()
        self.assertEqual(len(unit["fork_ids"]), EXPECTED_COUNT)
        self.assertEqual({s["fork_id"] for s in sheets},
                         set(unit["fork_ids"]))
        self.assertIsNone(unit["tier"])

    def test_tier_discipline_no_tier_is_invented(self):
        """TIER DISCIPLINE: the unit's tier is null, so the sheet's
        ``cmmc_tier`` is None and its ``fedramp_impact_level`` is
        ``"Unknown"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertIsNone(sheet["cmmc_tier"])
                self.assertEqual(sheet["fedramp_impact_level"],
                                 "Unknown")

    def test_claim_totals_are_pinned_literally(self):
        """The set carries exactly 0 claims in total; the zero-claim
        set is exactly {FR2632558740} and every one of the 9
        taxonomy families stands at zero for this fork — a fork
        gaining a claim fails here rather than drifting silently."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        families = {c["function_id"] for s in sheets
                    for c in s["functions_claimed"]}
        self.assertEqual(families, set())
        self.assertEqual(ALL_FAMILIES - families, ALL_FAMILIES)
        zero = {s["fork_id"] for s in sheets if not s["functions_claimed"]}
        self.assertEqual(zero, EXPECTED_ZERO_CLAIM_FORKS)

    def test_description_is_verbatim_against_cached_source(self):
        """The sheet's description equals the cached record's
        service_desc (whitespace-collapsed, the founding rule), for
        both duplicate cached records."""
        for sheet in _load_sheets():
            records = _cached_records(sheet["fork_id"])
            self.assertEqual(len(records), 2)
            for rec in records:
                self.assertEqual(
                    sheet["description"],
                    " ".join(rec["service_desc"].split()))

    def test_every_sheet_carries_the_group_category(self):
        """The sheet's ``deadramp_category`` is
        ``"Travel Management"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertEqual(sheet["deadramp_category"],
                                 EXPECTED_CATEGORY)

    def test_census_citation_verifies_but_tags_nothing(self):
        """The fork's single census citation is its description
        sentence: it verifies verbatim against the description and
        is the evidence sentence for no claim (there are none) —
        verification is not a claim, in either direction."""
        with open(_REMAINDER_PATH) as fh:
            rem = json.load(fh)
        census = {r["fork_id"]: r for r in rem["forks"]}
        for sheet in _load_sheets():
            entry = census[sheet["fork_id"]]
            self.assertEqual(entry["build_unit"], UNIT_ID)
            self.assertEqual(len(entry["citations"]), 1)
            cite = " ".join(entry["citations"][0].split())
            self.assertIn(cite, sheet["description"])
            evidence = {c["evidence"] for c in sheet["functions_claimed"]}
            self.assertNotIn(cite, evidence)

    def test_no_exclusion_trap_certified_services_empty(self):
        """The cached record's ``certified_services`` is empty: no
        third-party hosted-application catalogue is attached to
        the listing, so the excluded-catalogue precedent does not
        arise and no claim rests on an exclusion."""
        for sheet in _load_sheets():
            for rec in _cached_records(sheet["fork_id"]):
                self.assertEqual(rec.get("certified_services"), [])

    def test_founding_five_absences_survive_on_this_forks_words(self):
        """All five of the founding build's checked absences
        SURVIVE on this fork's own words: none of the founding
        token lists finds a token in this description."""
        for sheet in _load_sheets():
            desc = sheet["description"].lower()
            for absence, tokens in ABSENCE_TOKENS.items():
                for token in tokens:
                    with self.subTest(absence=absence, token=token):
                        self.assertNotIn(token, desc)

    def test_near_miss_reporting_substance_without_the_phrase(self):
        """Near-miss pins: the description carries reporting
        substance ("reporting", "analysis", "aggregation") but
        none of the suite-list phrases the taxonomy's families
        require — "reporting services", "suite of travel",
        "expense, integration", "notification, and reporting" all
        absent; substance without the phrase earns no tag."""
        for sheet in _load_sheets():
            desc = sheet["description"].lower()
            self.assertIn("reporting", desc)
            self.assertIn("analysis", desc)
            self.assertIn("aggregation", desc)
            for phrase in ("reporting services", "suite of travel",
                           "expense, integration",
                           "notification, and reporting",
                           "streamline and standardize"):
                with self.subTest(phrase=phrase):
                    self.assertNotIn(phrase, desc)

    def test_no_control_language_anywhere(self):
        """No control-language token occurs in the description —
        the ground for the union spec's Documented control claims
        section listing every family as not documented."""
        for sheet in _load_sheets():
            desc = sheet["description"].lower()
            for token in CONTROL_TOKENS:
                with self.subTest(token=token):
                    self.assertNotIn(token, desc)


if __name__ == "__main__":
    unittest.main()
