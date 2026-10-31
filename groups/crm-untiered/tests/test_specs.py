"""Spec integrity: the untiered fork of this set.

Traces to: remainder.json build unit
``untiered:Customer Relations Management (CRM)`` (kind
``untiered_set``, tier null, 1 fork) and the spec sheet built for
it in ``specs/specs.json``.

This is the FIRST untiered set for CRM: its fork carries no tier
in the source census, so the sheet must carry no tier either. The
pins here are:

- The spec sheet count is exactly 1.
- The sheet fork_id set is exactly the fork_ids set of the
  remainder.json unit ``untiered:Customer Relations Management
  (CRM)``.
- TIER DISCIPLINE: the sheet's ``cmmc_tier`` is None and its
  ``fedramp_impact_level`` is ``"Unknown"`` — no tier or impact
  level is invented for a fork the census left untiered.
- Every claim's evidence is a verbatim substring of the sheet's
  description (the CRM category's founding evidence rule: raw
  substring, no normalization — the description's literal
  newlines are part of the stored text and of the evidence).
- The sheet's ``deadramp_category`` is ``"CRM"`` (the category
  line's sheet convention at every tier).
- The literal claim totals: exactly 2 claims on the single fork
  (``account_contact_registry`` and ``ai_scoring``), and no
  zero-claim fork.
- CATALOGUE DISCIPLINE: the source record's ``certified_services``
  catalogue asserts "Sales pipeline management" in its own text,
  yet ``opportunity_pipeline`` is NOT claimed — claims rest on the
  marketplace description only, never on the catalogue field.
"""

import json
import os
import unittest

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPECS_PATH = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_REMAINDER_PATH = os.path.join(_GROUP_ROOT, "..", "..", "remainder.json")
_RAW_PATH = os.path.join(_GROUP_ROOT, "..", "..", "raw", "data_dump.json")

UNIT_ID = "untiered:Customer Relations Management (CRM)"
EXPECTED_CATEGORY = "CRM"
EXPECTED_COUNT = 1
EXPECTED_FORK = "FR2635050861"
EXPECTED_CLAIMS = {"account_contact_registry", "ai_scoring"}
EXPECTED_TOTAL_CLAIMS = 2


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
        remainder.json unit `untiered:Customer Relations Management
        (CRM)` — no more, no fewer."""
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
        sheet's description (raw substring — the CRM founding
        extractor's evidence rule, with no normalization)."""
        for sheet in _load_sheets():
            desc = sheet["description"]
            for claim in sheet["functions_claimed"]:
                ev = claim["evidence"]
                with self.subTest(fork=sheet["fork_id"],
                                  function=claim["function_id"]):
                    self.assertIn(ev, desc)

    def test_description_matches_raw_cache(self):
        """The sheet's description is the raw cache's service_desc
        for this fork, byte for byte (literal newlines included)."""
        product = _load_raw_product()
        for sheet in _load_sheets():
            self.assertEqual(sheet["description"],
                             product["service_desc"])

    def test_every_sheet_carries_the_group_category(self):
        """The sheet's ``deadramp_category`` is ``"CRM"``."""
        for sheet in _load_sheets():
            with self.subTest(fork=sheet["fork_id"]):
                self.assertEqual(sheet["deadramp_category"],
                                 EXPECTED_CATEGORY)

    def test_claim_totals_are_pinned_literally(self):
        """The set carries exactly 2 claims in total, on exactly
        the two recorded families, and the zero-claim set is empty
        — a fork gaining or losing a claim, or falling to zero,
        fails here rather than drifting silently."""
        sheets = _load_sheets()
        total = sum(len(s["functions_claimed"]) for s in sheets)
        self.assertEqual(total, EXPECTED_TOTAL_CLAIMS)
        claimed = {c["function_id"] for s in sheets
                   for c in s["functions_claimed"]}
        self.assertEqual(claimed, EXPECTED_CLAIMS)
        zero = {s["fork_id"] for s in sheets if not s["functions_claimed"]}
        self.assertEqual(zero, set())

    def test_certified_services_catalogue_never_matched(self):
        """CATALOGUE DISCIPLINE: the source record's
        ``certified_services`` text asserts "Sales pipeline
        management" — a phrase that would fire
        ``opportunity_pipeline`` — yet that family is not claimed,
        because claims rest on the marketplace description only."""
        product = _load_raw_product()
        catalogue_text = " ".join(
            f"{c.get('serviceName', '')}: "
            f"{c.get('serviceDescription', '')}"
            for c in product.get("certified_services") or [])
        self.assertIn("Sales pipeline", catalogue_text)
        claimed = {c["function_id"] for s in _load_sheets()
                   for c in s["functions_claimed"]}
        self.assertNotIn("opportunity_pipeline", claimed)


if __name__ == "__main__":
    unittest.main()
