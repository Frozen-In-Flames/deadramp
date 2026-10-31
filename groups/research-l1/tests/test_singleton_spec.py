"""Singleton spec integrity and substrate cases for the Research
L1 singleton (DeadRamp Phase 2 remainder, unit
new-singleton:Research|L1).

Traces to: UNION-SPEC.md for the Research L1 singleton. The
group's single fork (Evidence Prime / Laser AI) was spec'd under
the category's EXISTING 9-family taxonomy applied verbatim — the
extractor (../scratch/extract.py) parses the TAXONOMY literal out
of the Research L2 group's original shipped
``scratch/extract.py`` via ``ast`` (parsed, never executed, never
re-typed) and reproduces that group's original shipped claim
table exactly (Gen3, 9 claims) before tagging the newcomer.

The newcomer claims **zero families**: 0 raw hits across all 9
families and all 6 sentences of its description. The taxonomy is
data-commons-shaped — it was defined from the Gen3 description's
own vocabulary — and Laser AI's systematic-review automation
prose fires none of it. The zero is the finding, recorded plainly
in UNION-SPEC.md and ../scratch/ARTIFACTS.md; the patterns were
not loosened to fit this fork, and the substance the description
does assert (review automation, screening, extraction, quality
assessment) is named as gaps, not claims.

Citation accounting, pinned: the fork's single census citation
verifies as a strict verbatim substring — it IS the description's
first sentence — and tags no family. Verification is not a
claim, in either direction.

The substrate cases exercise the shipped core as records the
fork's domain presupposes, without touching the grant-status
derivation (so this file adds no failure to the group's signature
drill, tests/README.md): a controlled dataset record holding
review-evidence metadata — metadata + checksum only, content
verified transiently and never stored (Core 4) — behind the
membership boundary (Core 10); and the access-request gate
discipline (Core 5): open datasets reject requests, and a pending
request can be withdrawn by its requester. Every engine that
would *run* a systematic review is Extended (UNION-SPEC.md).
"""

import ast
import hashlib
import json
import os
import re
import unittest

import research_helpers as H
from research.errors import PermissionDenied, ValidationError

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "FR2207359708"
UNIT_ID = "new-singleton:Research|L1"

ALL_FAMILIES = [
    "data_commons_operation",
    "data_ecosystems_meshes",
    "workspaces",
    "data_management",
    "data_analysis",
    "data_sharing",
    "access_tiers_open_controlled",
    "open_source_platform",
    "saas_multi_tenancy",
]

_S1 = (
    "LASER is a system automating the development of Living "
    "Systematic Reviews using natural language processing (NLP) "
    "and artificial intelligence techniques, which synthesizes "
    "available knowledge about a given health problem continuously "
    "and with minimal human involvement."
)


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _raw_product(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in prods}[fork_id]


def _parse_taxonomy(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "TAXONOMY"
            for t in node.targets
        ):
            return [tuple(item) for item in ast.literal_eval(node.value)]
    raise AssertionError(f"no TAXONOMY literal in {path}")


def _parent_taxonomy():
    return _parse_taxonomy(os.path.join(
        _REPO_ROOT, "groups", "research-l2", "scratch", "extract.py"))


def _tag(taxonomy, description):
    sentences = [p.strip() for p in
                 re.split(r"(?<=[.!?])\s+", description.strip()) if p.strip()]
    claims = []
    for function_id, label, pattern in taxonomy:
        regex = re.compile(pattern, re.IGNORECASE)
        for sentence in sentences:
            if regex.search(sentence):
                claims.append({"function_id": function_id,
                               "function": label,
                               "evidence": sentence})
                break
    return claims


class TestSingletonSpecIntegrity(unittest.TestCase):
    """UNION-SPEC.md: membership, literal claim table (empty),
    taxonomy-verbatim proof, verbatim description, census citation
    accounting, near-miss pins."""

    def test_single_sheet_and_membership(self):
        """Exactly 1 sheet, and it is exactly the census unit's
        fork for this singleton."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs], [FORK_ID])
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == UNIT_ID)
        self.assertEqual(unit["fork_ids"], [FORK_ID])
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == FORK_ID)
        self.assertEqual(census["build_unit"], UNIT_ID)
        self.assertEqual(census["proposed_category"], "Research")

    def test_taxonomy_verbatim_and_reproduction(self):
        """The taxonomy applied here is the category's one
        taxonomy: the 9-family literal parsed (never executed) out
        of the parent group's original extractor, and it
        reproduces the parent group's original shipped claim
        table exactly (Gen3, 9 claims, evidence included) from
        the raw cache — the taxonomy-verbatim proof."""
        taxonomy = _parent_taxonomy()
        self.assertEqual([t[0] for t in taxonomy], ALL_FAMILIES)
        with open(os.path.join(_REPO_ROOT, "groups", "research-l2",
                               "specs", "specs.json")) as fh:
            parent_specs = json.load(fh)
        original = next(s for s in parent_specs
                        if s["fork_id"] == "FR2125059322")
        reproduced = _tag(taxonomy,
                          _raw_product("FR2125059322")["service_desc"])
        self.assertEqual(reproduced, original["functions_claimed"])
        self.assertEqual(len(reproduced), 9)

    def test_literal_claim_table_is_empty(self):
        """The fork claims exactly nothing: the literal claim
        table is the empty list."""
        sheet = _load_specs()[0]
        self.assertEqual(sheet["functions_claimed"], [])

    def test_zero_claim_set_is_all_families(self):
        """The zero-claim set is all 9 families — raw hits equal
        claims (0 = 0), verified by re-tagging the description
        under the verbatim taxonomy in this test."""
        taxonomy = _parent_taxonomy()
        sheet = _load_specs()[0]
        self.assertEqual(_tag(taxonomy, sheet["description"]), [])
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_tier_fields(self):
        """The fork is FedRAMP LI-SaaS / Certified / L1 / SaaS /
        Public Cloud — its actual impact level recorded, not
        rounded to Low. Its source record carries no business
        categories (uncategorized in the source; the DeadRamp
        category is the census proposal), and forks.json files
        it Uncategorized at L1."""
        sheet = _load_specs()[0]
        self.assertEqual(sheet["vendor"], "Evidence Prime")
        self.assertEqual(sheet["product"], "Laser AI")
        self.assertEqual(sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"], "Research")
        with open(os.path.join(_REPO_ROOT, "forks.json")) as fh:
            forks = json.load(fh)
        fork = next(f for f in forks if f["source_url"].rstrip("/")
                    .rsplit("/", 1)[-1] == FORK_ID)
        self.assertEqual(fork["category"],
                         "Uncategorized (none in source)")
        self.assertEqual(fork["cmmc_tier"], "L1")

    def test_description_equals_cached_source(self):
        """The sheet's description is the fork's own cached
        marketplace description, verbatim."""
        sheet = _load_specs()[0]
        self.assertEqual(sheet["description"],
                         _raw_product(FORK_ID)["service_desc"])

    def test_census_citation_verifies_and_tags_nothing(self):
        """Citation accounting: the fork's single census citation
        verifies as a strict verbatim substring — it IS the
        description's first sentence — and tags no family under
        the verbatim taxonomy. Verification is not a claim."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == FORK_ID)
        self.assertEqual(census["citations"], [_S1])
        sheet = _load_specs()[0]
        self.assertIn(_S1, sheet["description"])
        self.assertEqual(_tag(_parent_taxonomy(), _S1), [])

    def test_no_exclusion_trap_for_newcomer(self):
        """No exclusion applied: the source record carries no
        certified-services catalogue, and no sentence of the
        description is a scope-exclusion sentence. Matched text
        is the full text; raw hits equal claims (0 = 0)."""
        self.assertEqual(_raw_product(FORK_ID)["certified_services"],
                         [])

    def test_near_miss_pins_laser(self):
        """Laser AI: the systematic-review substance is present in
        its own words; every family's operative phrase is absent,
        so all 9 families stay at zero for this fork and the
        substance is named as gaps, not claims."""
        desc = _load_specs()[0]["description"]
        low = desc.lower()
        # Substance present (the gaps' basis):
        self.assertIn("living systematic reviews", low)
        self.assertIn("natural language processing", low)
        self.assertIn("artificial intelligence", low)
        self.assertIn("search strategy", low)
        self.assertIn("screening of full texts", low)
        self.assertIn("data extraction", low)
        self.assertIn("quality assessment", low)
        self.assertIn("shared dictionaries", low)
        self.assertIn("management of projects", low)
        self.assertIn("meta-analysis", low)
        # Family tokens absent:
        self.assertNotIn("data commons", low)
        self.assertNotIn("data ecosystems", low)
        self.assertNotIn("workspaces", low)
        self.assertNotIn("managing", low)
        self.assertNotIn("analyzing", low)
        self.assertNotIn("sharing", low)
        self.assertNotIn("open access and controlled access", low)
        self.assertNotIn("open-source", low)
        self.assertNotIn("multi-tenant", low)


class TestSingletonSubstrateCases(unittest.TestCase):
    """Substrate cases for the singleton fork (UNION-SPEC.md core
    section). The core is carried; each case runs the records form
    the fork's domain presupposes. Neither case touches the grant
    derivation."""

    def test_review_evidence_dataset_record_and_verify(self):
        """Laser shape: a controlled dataset record whose shape is
        the records form of a living review's evidence index —
        metadata + checksum only (Core 4): the evidence content is
        hashed transiently for verification and never stored, the
        stored record's key set is exactly the pinned set, and the
        membership boundary denies an outsider (Core 10). No
        review content, protocol text, or screening result exists
        in any field — those are the fork's engines, Extended."""
        store, commons, _org = H.make_store()
        content = b"evidence-index-export-v1"
        digest = hashlib.sha256(content).hexdigest()
        dataset = H.make_dataset(
            store, commons, name="living-review-evidence-index",
            description="Metadata index of a living review's "
                        "evidence records",
            sha256=digest, size_bytes=len(content))
        self.assertEqual(
            set(dataset.keys()),
            {"id", "commons_id", "name", "description",
             "access_tier", "sha256", "size_bytes", "created_by",
             "created_utc"})
        ok = store.verify_dataset(H.MEMBER, dataset["id"], content)
        self.assertTrue(ok["matches"])
        bad = store.verify_dataset(H.MEMBER, dataset["id"], b"other")
        self.assertFalse(bad["matches"])
        with self.assertRaises(PermissionDenied):
            store.get_dataset(H.OUTSIDER, dataset["id"])

    def test_access_gate_discipline(self):
        """Laser shape: the request gate (Core 5) — a request
        against an OPEN dataset is rejected whole (open data needs
        no request; a request record for one would be a false
        gate), and a request against a controlled dataset can be
        withdrawn by its requester while pending, ending in the
        stored ``withdrawn`` status. No decision is taken and no
        grant is minted in this case."""
        store, commons, _org = H.make_store()
        open_ds = H.make_dataset(store, commons, name="open-index",
                                 access_tier="open")
        with self.assertRaises(ValidationError):
            H.make_access_request(store, open_ds)
        controlled = H.make_dataset(store, commons,
                                    name="controlled-index")
        request = H.make_access_request(store, controlled)
        self.assertEqual(request["status"], "pending")
        withdrawn = store.withdraw_access_request(H.MEMBER,
                                                  request["id"])
        self.assertEqual(withdrawn["status"], "withdrawn")


if __name__ == "__main__":
    unittest.main()
