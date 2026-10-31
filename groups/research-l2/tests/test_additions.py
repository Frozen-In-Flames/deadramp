"""Remainder additions — unit ``addition:research-l2`` (see ADDENDUM.md).

Traces to: the 5 previously uncategorized forks appended to this
group's spec sheets by ``scratch/additions_extract.py`` — Terra,
Ipsos Research, ROSALIND, Seven Bridges Platform, Wellspring
WTIMS — spec'd under the group's existing 9-family taxonomy
applied verbatim.

Two halves:

- **Spec integrity.** Sheet count and unit order, membership
  against ``../../remainder.json``, the literal per-fork claim
  table, verbatim evidence, the census citations, the zero-claim
  forks and zero-claim families pinned (not hidden), and the
  near-miss pins: this taxonomy's patterns are the Gen3 fork's own
  literal phrases, so "analysis" is not ``data_analysis``
  (``analyzing`` required), "manage" is not ``data_management``
  (``managing`` required), "multi-tenant SaaS" is not the
  spelled-out ``saas_multi_tenancy`` phrase, and the word
  "workspaces" never appears in any newcomer's description.
- **Substrate cases.** One case per addition fork against the
  unchanged core. The two ``data_sharing`` claimants (Terra,
  ROSALIND) exercise the sharing records the claim presupposes:
  access requests, separation-of-duties decisions, and time-boxed
  grants whose status is derived at read and never stored. The
  three zero-claim forks exercise the registry records their
  census Research classification presupposes — dataset, workspace,
  and organization records, metadata + checksum only — while
  their own engines (survey platform, analysis pipelines,
  tech-transfer suite) stay the Extended gaps named in
  ADDENDUM.md §5: no substrate case performs or pretends them.
"""

import hashlib
import json
import os
import re
import unittest

from research.errors import PermissionDenied, ValidationError

import research_helpers as H
from research_helpers import (
    MEMBER,
    OUTSIDER,
    STAFF,
    make_dataset,
    make_grant,
    make_store,
    make_workspace,
)

_GROUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ROOT = os.path.abspath(os.path.join(_GROUP_DIR, "..", ".."))
CATEGORY = "Research"
UNIT_ID = "addition:research-l2"

ORIGINAL_IDS = ["FR2125059322"]
UNIT_IDS = [
    "FR2000939520",  # Broad Institute, Inc. / Terra
    "FR2104636677",  # Ipsos America, Inc. / Ipsos Research
    "FR2204842850",  # Rosalind, Inc. / ROSALIND
    "FR2033152148",  # Seven Bridges Genomics, Inc / Seven Bridges Platform
    "FR1924344515",  # Wellspring Worldwide, Inc. / Wellspring WTIMS
]

# The literal claim table the taxonomy produces for the additions,
# in taxonomy order per sheet. Pinned so any taxonomy drift — or
# any hand-edit of a sheet — fails the suite.
EXPECTED_CLAIMS = {
    "FR2000939520": ["data_sharing"],
    "FR2104636677": [],
    "FR2204842850": ["data_sharing"],
    "FR2033152148": [],
    "FR1924344515": [],
}

# Forks claiming zero families, pinned rather than left implicit.
ZERO_CLAIM_FORKS = ["FR2104636677", "FR2033152148", "FR1924344515"]

# Families no addition claims, pinned rather than left implicit.
ZERO_CLAIM_FAMILIES = [
    "data_commons_operation",
    "data_ecosystems_meshes",
    "workspaces",
    "data_management",
    "data_analysis",
    "access_tiers_open_controlled",
    "open_source_platform",
    "saas_multi_tenancy",
]

DATASET_KEYS = {
    "id", "commons_id", "name", "description", "access_tier",
    "sha256", "size_bytes", "created_by", "created_utc",
}


def load_sheets():
    with open(os.path.join(_GROUP_DIR, "specs", "specs.json")) as fh:
        return json.load(fh)


def addition_sheets():
    return {s["fork_id"]: s for s in load_sheets()[len(ORIGINAL_IDS):]}


class TestAdditionSpecIntegrity(unittest.TestCase):
    """The appended sheets are exactly the census unit, tagged by
    the group's taxonomy verbatim."""

    def test_sheet_count_and_unit_order(self):
        sheets = load_sheets()
        self.assertEqual(len(sheets), 6)
        self.assertEqual(
            [s["fork_id"] for s in sheets], ORIGINAL_IDS + UNIT_IDS
        )

    def test_membership_matches_remainder_unit(self):
        with open(os.path.join(_ROOT, "remainder.json")) as fh:
            remainder = json.load(fh)
        unit = next(
            u for u in remainder["build_units"] if u["unit_id"] == UNIT_ID
        )
        self.assertEqual(unit["fork_ids"], UNIT_IDS)
        self.assertEqual(unit["category"], CATEGORY)
        self.assertEqual(unit["tier"], "L2")
        self.assertEqual(unit["extends_group"], "research-l2")

    def test_per_fork_claim_table_is_literal(self):
        sheets = addition_sheets()
        self.assertEqual(set(sheets), set(UNIT_IDS))
        for fid, expected in EXPECTED_CLAIMS.items():
            with self.subTest(fork=fid):
                self.assertEqual(
                    [c["function_id"] for c in sheets[fid]["functions_claimed"]],
                    expected,
                )
        self.assertEqual(sum(len(v) for v in EXPECTED_CLAIMS.values()), 2)

    def test_sheet_fields_and_verbatim_evidence(self):
        for fid, sheet in addition_sheets().items():
            with self.subTest(fork=fid):
                self.assertEqual(sheet["deadramp_category"], CATEGORY)
                self.assertEqual(sheet["cmmc_tier"], "L2")
                self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
                self.assertEqual(
                    sheet["business_categories_in_source"], []
                )
                self.assertTrue(sheet["description"])
                for claim in sheet["functions_claimed"]:
                    # Evidence is the fork's own sentence, verbatim.
                    self.assertIn(claim["evidence"], sheet["description"])

    def test_census_citations_verify_against_descriptions(self):
        with open(os.path.join(_ROOT, "remainder.json")) as fh:
            remainder = json.load(fh)
        census = {e["fork_id"]: e for e in remainder["forks"]}
        sheets = addition_sheets()
        checked = 0
        for fid in UNIT_IDS:
            desc = sheets[fid]["description"]
            normalized = re.sub(r"\s+", " ", desc)
            for cite in census[fid].get("citations", []):
                text = cite if isinstance(cite, str) else cite.get("sentence", "")
                self.assertTrue(
                    text in desc or re.sub(r"\s+", " ", text) in normalized,
                    (fid, text),
                )
                checked += 1
        self.assertEqual(checked, 8)

    def test_zero_claim_forks_and_families_are_pinned(self):
        sheets = addition_sheets()
        for fid in ZERO_CLAIM_FORKS:
            with self.subTest(fork=fid):
                self.assertEqual(sheets[fid]["functions_claimed"], [])
        claimed = {
            c["function_id"]
            for s in sheets.values()
            for c in s["functions_claimed"]
        }
        self.assertEqual(claimed, {"data_sharing"})
        for family in ZERO_CLAIM_FAMILIES:
            with self.subTest(family=family):
                self.assertNotIn(family, claimed)

    def test_near_miss_pins(self):
        sheets = addition_sheets()
        terra = sheets["FR2000939520"]
        # Terra's description says "analysis" throughout but never
        # "analyzing": data_analysis does not fire. It hosts data
        # ("access datasets sponsored by partner organizations")
        # but never writes "open access and controlled access
        # data": the tier family does not fire. And the word
        # "workspaces" — Terra's own product concept — never
        # appears; it writes "sharing work", which is its
        # data_sharing claim instead.
        self.assertIn("analysis", terra["description"])
        self.assertNotIn("workspaces", terra["description"].lower())
        self.assertNotIn(
            "open access and controlled access data", terra["description"]
        )
        rosalind = sheets["FR2204842850"]
        # "multi-tenant SaaS" is not the spelled-out pattern
        # "multi-tenant Software as a Service"; "analyze and
        # interpret" is not "analyzing"; "permissions-based data
        # sharing" fires data_sharing but not the tier family,
        # whose phrase is the Gen3 sentence's own.
        self.assertIn("multi-tenant SaaS", rosalind["description"])
        self.assertIn("analyze and interpret", rosalind["description"])
        self.assertIn("permissions-based data sharing", rosalind["description"])
        for fid in ("FR2204842850",):
            ids = [c["function_id"] for c in sheets[fid]["functions_claimed"]]
            self.assertNotIn("saas_multi_tenancy", ids)
            self.assertNotIn("data_analysis", ids)
            self.assertNotIn("access_tiers_open_controlled", ids)
        ipsos = sheets["FR2104636677"]
        # "We manage the complete paper survey lifecycle" and
        # "All data is managed" are not "managing": no
        # data_management claim, despite the census Research
        # classification resting on the research-lifecycle prose.
        self.assertIn(
            "manage the complete paper survey lifecycle", ipsos["description"]
        )
        seven = sheets["FR2033152148"]
        # "store, analyze, and jointly interpret" — the verb is
        # "analyze", and "store" alone fires no family either.
        self.assertIn(
            "store, analyze, and jointly interpret", seven["description"]
        )
        wellspring = sheets["FR1924344515"]
        # SaaS and multi-tenant both appear, but never as the
        # contiguous spelled-out phrase; "used to manage" and
        # "Manages electronic signature workflows" are not
        # "managing".
        self.assertIn("multi-tenant", wellspring["description"])
        self.assertIn("SaaS offering", wellspring["description"])
        self.assertIn("used to manage", wellspring["description"])


class TestAdditionSubstrateCases(unittest.TestCase):
    """One substrate case per addition fork against the unchanged
    core (Core functions per UNION-SPEC)."""

    def setUp(self):
        self.store, self.commons, self.org = make_store()

    def test_terra_sharing_flow_and_grant_derivation(self):
        # Terra: "built-in capabilities for sharing work
        # selectively, protecting data from unwanted
        # re-distribution" — sharing as records (Core 6): a
        # request, a decision by someone who is not the requester,
        # and a time-boxed grant whose status is derived at read
        # (Core 7) and never stored. The dataset record itself is
        # metadata + checksum, verified against caller content
        # hashed transiently (Core 4).
        content = b"terra hosted dataset bytes"
        dataset = make_dataset(
            self.store, self.commons,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
        )
        check = self.store.verify_dataset(MEMBER, dataset["id"], content)
        self.assertTrue(check["matches"])
        self.assertFalse(
            self.store.verify_dataset(MEMBER, dataset["id"], b"other")["matches"]
        )
        grant = make_grant(self.store, self.commons, dataset=dataset)
        gid = grant["id"]
        self.assertEqual(
            self.store.get_grant(STAFF, gid, now=H.BEFORE_T0)["status"],
            "scheduled",
        )
        self.assertEqual(
            self.store.get_grant(STAFF, gid, now=H.INSIDE_WINDOW)["status"],
            "active",
        )
        self.assertEqual(
            self.store.get_grant(STAFF, gid, now=H.AFTER_EXPIRY)["status"],
            "expired",
        )
        # The stored grant record carries no status key at all.
        self.assertNotIn("status", self.store._grants[gid])
        summary = self.store.commons_summary(
            STAFF, self.commons["id"], now=H.AFTER_EXPIRY
        )
        self.assertEqual(summary["grants_by_status"]["expired"], 1)
        self.assertEqual(summary["grants_by_status"]["active"], 0)

    def test_rosalind_tier_gate_and_revocation(self):
        # ROSALIND: "permissions-based data sharing between
        # authorized users" — the tier designation is recorded on
        # the dataset (Core 7): open data takes no request (a
        # request record for it would be a false gate), and a
        # controlled dataset's grant can be revoked, the
        # revocation beating the window in the derivation.
        open_ds = make_dataset(
            self.store, self.commons, name="open-reference",
            access_tier="open",
        )
        with self.assertRaises(ValidationError):
            H.make_access_request(self.store, open_ds)
        grant = make_grant(self.store, self.commons)
        gid = grant["id"]
        self.assertEqual(
            self.store.get_grant(STAFF, gid, now=H.INSIDE_WINDOW)["status"],
            "active",
        )
        self.store.revoke_grant(STAFF, gid)
        self.assertEqual(
            self.store.get_grant(STAFF, gid, now=H.INSIDE_WINDOW)["status"],
            "revoked",
        )
        revoked = self.store.list_grants(
            STAFF, self.commons["id"], status="revoked", now=H.INSIDE_WINDOW
        )
        self.assertEqual([g["id"] for g in revoked], [gid])

    def test_ipsos_dataset_registry_metadata_only(self):
        # Ipsos claims nothing, and its survey / AI-analytics
        # surface is Extended (ADDENDUM §5) — what the records
        # substrate holds for a data platform is the dataset
        # record (Core 4): a pinned key set with no field that
        # could hold response data or any payload, verified by
        # content hashed transiently and discarded.
        content = b"survey wave metadata"
        dataset = make_dataset(
            self.store, self.commons, name="survey-wave-2026",
            description="Metadata record for a survey wave",
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
        )
        self.assertEqual(set(dataset.keys()), DATASET_KEYS)
        self.assertTrue(
            self.store.verify_dataset(MEMBER, dataset["id"], content)["matches"]
        )
        summary = self.store.commons_summary(STAFF, self.commons["id"])
        self.assertEqual(summary["datasets_by_tier"]["controlled"], 1)

    def test_seven_bridges_workspace_and_tier_listing(self):
        # Seven Bridges claims nothing; its analysis-pipeline
        # engine is Extended (ADDENDUM §5). The substrate case is
        # the workspace and dataset registries (Core 3/4): an open
        # and a controlled dataset listed by tier, found by
        # substring search, and invisible to a non-member.
        workspace = make_workspace(self.store, self.commons)
        self.assertEqual(workspace["commons_id"], self.commons["id"])
        make_dataset(self.store, self.commons, name="open-panel",
                     access_tier="open")
        make_dataset(self.store, self.commons, name="controlled-panel")
        open_only = self.store.list_datasets(
            MEMBER, self.commons["id"], access_tier="open"
        )
        self.assertEqual([d["name"] for d in open_only], ["open-panel"])
        found = self.store.search(MEMBER, "panel")
        self.assertEqual(len(found["datasets"]), 2)
        with self.assertRaises(PermissionDenied):
            self.store.list_datasets(OUTSIDER, self.commons["id"])

    def test_wellspring_organization_and_summary_records(self):
        # Wellspring claims nothing; its tech-transfer suite is
        # Extended (ADDENDUM §5). The substrate case is the
        # organization registry (Core 2 — opaque references, a
        # pinned shape with no field for a real identifier) and
        # summary counts computed on read (Core 8).
        self.assertEqual(
            set(self.org.keys()),
            {"id", "ref", "label", "created_by", "created_utc"},
        )
        with self.assertRaises(ValidationError):
            self.store.create_organization(MEMBER, H.ORG_REF, "Duplicate")
        before = self.store.commons_summary(STAFF, self.commons["id"])
        self.assertEqual(before["workspaces"], 0)
        make_workspace(self.store, self.commons)
        after = self.store.commons_summary(STAFF, self.commons["id"])
        self.assertEqual(after["workspaces"], 1)


if __name__ == "__main__":
    unittest.main()
