"""Spec-sheet pins for the Content Management System (CMS)
untiered set (Untiered Set 14).

Traces to: UNION-SPEC.md (this group) — census membership, tier
discipline, and the literal claim table. These tests pin the
specs, not the code: exactly 2 sheets, membership exact against
census unit ``untiered:Content Management System (CMS)`` in
../../../remainder.json, every sheet recording the source's
impact level as-is ("Unknown") with ``cmmc_tier`` null, every
description equal to the census's recorded description for the
fork, and the literal result of the verbatim taxonomy
application — **1 claim across the set (Liferay SaaS:
search_discovery), Nintex Drawloop DocGen zero-claim** — so a
future re-extraction that quietly re-tunes the taxonomy, or a
sheet edit that manufactures a claim, fails here instead of
drifting. The category's "no fork has zero claims" floor fell
at the tiered L2 addition and falls here; the zero is pinned,
not repaired.
"""

import json
import os
import re
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

UNIT_ID = "untiered:Content Management System (CMS)"
LIFERAY = "FR2701857792"
NINTEX = "FR2001462460"
EXPECTED_CLAIMS = {
    LIFERAY: ["search_discovery"],
    NINTEX: [],
}
EXPECTED_ZERO_CLAIM = [NINTEX]


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _ws(t):
    return re.sub(r"\s+", " ", t)


class TestSpecSheets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = _load(os.path.join(_GROUP_DIR, "specs", "specs.json"))
        cls.by_id = {s["fork_id"]: s for s in cls.specs}
        rem = _load(os.path.join(_ROOT, "remainder.json"))
        unit = [u for u in rem["build_units"] if u["unit_id"] == UNIT_ID]
        assert len(unit) == 1
        cls.unit_ids = unit[0]["fork_ids"]
        cls.census = {r["fork_id"]: r for r in rem["forks"]}
        cls.uncovered = {
            u["fork_id"]: u
            for u in _load(os.path.join(_ROOT, "remainder", "uncovered.json"))
        }
        forks = _load(os.path.join(_ROOT, "forks.json"))
        rows = forks if isinstance(forks, list) else forks.get("forks", forks)
        cls.registry = {
            r["source_url"].rstrip("/").split("/")[-1]: r for r in rows
        }

    def test_exactly_two_sheets(self):
        self.assertEqual(len(self.specs), 2)

    def test_membership_exact_against_census_unit(self):
        self.assertEqual([s["fork_id"] for s in self.specs], self.unit_ids)
        self.assertEqual(set(self.by_id), set(self.unit_ids))
        self.assertEqual(len(self.unit_ids), 2)

    def test_tier_discipline_on_every_sheet(self):
        for sheet in self.specs:
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             sheet["fork_id"])
            self.assertIsNone(sheet["cmmc_tier"], sheet["fork_id"])
            self.assertEqual(sheet["deadramp_category"],
                             "Content Management System (CMS)",
                             sheet["fork_id"])

    def test_registry_fields_match_forks_json(self):
        for fid, sheet in self.by_id.items():
            reg = self.registry[fid]
            self.assertEqual(sheet["vendor"], reg["vendor"], fid)
            self.assertEqual(sheet["product"], reg["product"], fid)
            self.assertEqual(sheet["authorization_status"],
                             reg["authorization_status"], fid)
            self.assertEqual(sheet["service_model"],
                             [reg["service_model"]], fid)
            self.assertEqual(sheet["source_url"], reg["source_url"], fid)

    def test_business_categories_recorded_as_in_source(self):
        # Recorded as-is from the source record. Liferay is filed
        # Collaboration-first with CMS among five business
        # categories; Nintex carries none at all — both sit in
        # this category because the census assigned them from
        # their own descriptions. Both facts are pinned.
        expected = {
            LIFERAY: ["Collaboration", "Content Management System (CMS)",
                      "Customer Service", "Development Tools",
                      "Marketing & Sales"],
            NINTEX: [],
        }
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["business_categories_in_source"],
                             expected[fid], fid)

    def test_descriptions_equal_census_record(self):
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["description"],
                             self.uncovered[fid]["description"], fid)
            self.assertNotIn("\r", sheet["description"], fid)

    def test_literal_claim_table(self):
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 1)
        for fid, sheet in self.by_id.items():
            self.assertEqual(
                [c["function_id"] for c in sheet["functions_claimed"]],
                EXPECTED_CLAIMS[fid], fid)
        self.assertEqual(
            sorted(s["fork_id"] for s in self.specs
                   if not s["functions_claimed"]),
            sorted(EXPECTED_ZERO_CLAIM))

    def test_liferay_evidence_is_founding_rule_truncation(self):
        # The one claim's evidence sentence (the fork's "Core
        # capabilities" list sentence) exceeds 400 characters, so
        # the stored evidence is the founding rule's truncation:
        # 397 characters + '...', and the 397 are an exact prefix
        # substring of the description.
        claim = self.by_id[LIFERAY]["functions_claimed"][0]
        ev = claim["evidence"]
        self.assertEqual(claim["function_id"], "search_discovery")
        self.assertEqual(len(ev), 400)
        self.assertTrue(ev.endswith("..."))
        self.assertIn(ev[:397], self.by_id[LIFERAY]["description"])
        # The matching phrase ("enterprise search") sits past
        # character 397 of its sentence, so the truncated
        # evidence does not itself contain it — the founding
        # rule truncates the sentence, not around the match.
        # The phrase is in the full description sentence.
        self.assertIn("enterprise search",
                      self.by_id[LIFERAY]["description"])

    def test_near_miss_tokens_earn_nothing(self):
        # Substance present in the prose, absent from the claim
        # table — pinned so the taxonomy cannot be quietly
        # broadened to harvest them.
        lif = self.by_id[LIFERAY]
        lif_ids = [c["function_id"] for c in lif["functions_claimed"]]
        self.assertIn("editorial approval workflows", lif["description"])
        self.assertNotIn("authoring_editing", lif_ids)   # 'editorial' != \beditor\b
        self.assertIn("Google Cloud Platform", lif["description"])
        self.assertNotIn("platform_hosting", lif_ids)    # substrate, founding corr. 1
        self.assertIn("role-based permissions", lif["description"])
        self.assertNotIn("access_administration", lif_ids)
        self.assertIn("personalization", lif["description"])
        self.assertNotIn("content_registry", lif_ids)    # 'Content and site management'
        nin = self.by_id[NINTEX]
        self.assertIn("create, manage and generate document packages",
                      nin["description"])
        self.assertEqual(nin["functions_claimed"], [])
        self.assertIn("documents such as contracts", nin["description"])
        self.assertNotIn("media_assets",
                         [c["function_id"] for c in nin["functions_claimed"]])

    def test_certified_services_names_earn_nothing(self):
        # Liferay's source record carries a certified_services
        # entry naming itself. Record fields are never matched —
        # the house method matches service_desc only — and the
        # literal claim table above is the whole result.
        claims = [c["function_id"] for s in self.specs
                  for c in s["functions_claimed"]]
        self.assertEqual(claims, ["search_discovery"])

    def test_census_citations_verify(self):
        # 3 citations recorded for these forks: Nintex's two are
        # exact substrings; Liferay's one verifies only after
        # whitespace normalization (the source's line breaks are
        # "\n"; the citation renders them as spaces). None of the
        # three is a claim evidence sentence — verification is
        # not a claim, in either direction.
        verified = 0
        total = 0
        for fid, sheet in self.by_id.items():
            for citation in self.census[fid].get("citations") or []:
                total += 1
                self.assertIn(_ws(citation), _ws(sheet["description"]), fid)
                verified += 1
        self.assertEqual((verified, total), (3, 3))
        self.assertIn(self.census[NINTEX]["citations"][0],
                      self.by_id[NINTEX]["description"])


if __name__ == "__main__":
    unittest.main()
