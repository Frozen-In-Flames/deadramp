"""Remainder additions — unit addition:data-management-l1 (1 fork).

Traces to: the addendum for DevResults / DevResults
(FR2100845343), appended to the shipped Data Management L1
singleton group under its existing 19-family taxonomy applied
verbatim (parsed via ast from the original scratch/extract.py and
asserted equal to the Group 12 parent's taxonomy — the verbatim
inheritance proof lives in scratch/additions_extract.py). The
newcomer is a ZERO-CLAIM fork: its four-sentence marketplace
description produces no raw hit across any of the 19 families, so
its sheet claims nothing and the pins below are pins on an
absence: sheet count and append order, unit membership against
../../remainder.json, the literal (empty) claim table, the
original fork's claim table reproduced exactly (also empty — this
group is now 0 claims across 2 forks), the census citations
(verified as text; both tag nothing), the near-miss pins, and the
group totals. Two substrate cases exercise the shipped Core in
the shape the fork's described function presupposes — partner
results data registered as a dataset, fed by recorded ingestions,
governed by purpose-bound access, and exported under manifest —
the records substrate, carried not claimed. The access-governance
case trips under the group's self-approval guard mutant.
"""

import hashlib
import json
import os
import unittest

from datamgmt_helpers import ADMIN, STEWARD, VIEWER, fresh_store
from datamgmt.access import User
from datamgmt.errors import PermissionDenied

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "FR2100845343"
ORIGINAL_ID = "FR2409367364"
ALL_FAMILIES = [
    "dataset_registry", "catalog_search", "ingestion_collection",
    "integration_exchange", "record_linkage", "data_governance",
    "privacy_deidentification", "retention_disposition",
    "content_processing", "quality_validation",
    "workflow_automation", "guided_collection", "query_reporting",
    "api_access", "asset_lifecycle", "platform_hosting",
    "case_management", "file_transfer", "ai_ml",
]


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(fork_id):
    for row in _load_specs():
        if row["fork_id"] == fork_id:
            return row
    raise AssertionError("sheet missing: %s" % fork_id)


class TestAdditionSpecIntegrity(unittest.TestCase):
    """Addendum sections 1/2: membership, order, the empty claim table."""

    def test_sheet_count_and_append_order(self):
        """2 sheets: the original singleton first, newcomer appended."""
        ids = [r["fork_id"] for r in _load_specs()]
        self.assertEqual(ids, [ORIGINAL_ID, FORK_ID])

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork list,
        and the unit extends this group."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u.get("unit_id") == "addition:data-management-l1"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], [FORK_ID])
        self.assertEqual(unit[0]["extends_group"], "data-management-l1")
        self.assertIn(FORK_ID, [r["fork_id"] for r in _load_specs()])

    def test_literal_claim_table_newcomer_is_empty(self):
        """The newcomer claims exactly nothing under the verbatim
        taxonomy — zero raw hits across all 19 families."""
        self.assertEqual(_sheet(FORK_ID)["functions_claimed"], [])

    def test_original_claim_table_unchanged(self):
        """The original fork's shipped claim table stands exactly as
        shipped: empty (the extractor's reproduction proof, pinned)."""
        self.assertEqual(_sheet(ORIGINAL_ID)["functions_claimed"], [])
        self.assertEqual(_sheet(ORIGINAL_ID)["vendor"],
                         "Pagefreezer Software Inc.")
        self.assertEqual(_sheet(ORIGINAL_ID)["product"],
                         "Pagefreezer Website Archiving")

    def test_zero_claim_set_is_the_whole_taxonomy(self):
        """Every one of the 19 families is unclaimed by the newcomer."""
        claimed = {c["function_id"]
                   for c in _sheet(FORK_ID)["functions_claimed"]}
        self.assertEqual(claimed, set())
        self.assertEqual(set(ALL_FAMILIES) - claimed, set(ALL_FAMILIES))

    def test_registry_fields_as_published(self):
        """Sheet fields record the source as published: LI-SaaS at
        L1, FedRAMP Certified, SaaS / Public Cloud, empty business
        categories; forks.json files the fork as uncategorized and
        the census assignment recorded in deadramp_category is
        Data Management."""
        sheet = _sheet(FORK_ID)
        self.assertEqual(sheet["vendor"], "DevResults")
        self.assertEqual(sheet["product"], "DevResults")
        self.assertEqual(sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"], "Data Management")

    def test_census_citations_verify_but_tag_nothing(self):
        """Both census citations are verbatim description text — the
        description's first two sentences — and neither is a claim's
        evidence, because there are no claims (verification is not
        a claim, and classification is not a claim either)."""
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "class_all.json")) as fh:
            cls = json.load(fh)
        rows = cls if isinstance(cls, list) else cls.get(
            "classifications", [])
        entry = [r for r in rows if r.get("fork_id") == FORK_ID]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["proposed_category"], "Data Management")
        citations = entry[0]["citations"]
        self.assertEqual(len(citations), 2)
        sheet = _sheet(FORK_ID)
        for cit in citations:
            self.assertIn(cit, sheet["description"])
        self.assertTrue(sheet["description"].startswith(citations[0]))

    def test_near_miss_pins(self):
        """Family-adjacent phrases are present in the text yet tag
        no family: 'data capture' without 'data collection' /
        'collecting information' / 'ingest' (ingestion_collection);
        'analysis, reporting, visualizations' with neither
        'analytics', nor 'query and report', nor the contiguous
        'report visualization' (query_reporting); 'streamline
        fragmented data processes into a single proven system' with
        no integration/connectivity token (integration_exchange);
        'managing data' with no dataset/registry/repository token
        (dataset_registry); and no 'search' token anywhere
        (catalog_search)."""
        desc = _sheet(FORK_ID)["description"]
        self.assertIn("data capture", desc)
        self.assertNotIn("data collection", desc)
        self.assertIn("analysis, reporting, visualizations", desc)
        self.assertNotIn("analytics", desc)
        self.assertNotIn("report visualization", desc)
        self.assertIn("streamline fragmented data processes", desc)
        self.assertNotIn("integration", desc)
        self.assertNotIn("search", desc.lower())
        claimed = {c["function_id"]
                   for c in _sheet(FORK_ID)["functions_claimed"]}
        for fam in ("ingestion_collection", "query_reporting",
                    "integration_exchange", "dataset_registry",
                    "catalog_search"):
            self.assertNotIn(fam, claimed)

    def test_group_totals(self):
        """Updated union: 2 forks, 0 claims in total, 0 of 2
        claiming, exactly 2 zero-claim forks, and the group's
        composition is LI-SaaS 2 at L1."""
        rows = _load_specs()
        total = sum(len(r["functions_claimed"]) for r in rows)
        claiming = sum(1 for r in rows if r["functions_claimed"])
        zero = [r["fork_id"] for r in rows if not r["functions_claimed"]]
        self.assertEqual(total, 0)
        self.assertEqual(claiming, 0)
        self.assertEqual(zero, [ORIGINAL_ID, FORK_ID])
        levels = [r["fedramp_impact_level"] for r in rows]
        self.assertEqual(levels.count("LI-SaaS"), 2)


RESULTS_SCHEMA = [
    {"name": "indicator", "type": "string", "required": True,
     "sensitive": False},
    {"name": "value", "type": "number", "required": True,
     "sensitive": False},
]


def _results_store():
    store = fresh_store()
    dataset = store.create_dataset(
        "Partner Activity Results",
        "Monitoring and evaluation results reported by partners",
        STEWARD,
        classification="internal",
        tags=["results", "field"],
        schema=[dict(f) for f in RESULTS_SCHEMA],
    )
    return store, dataset


class TestDevResultsSubstrate(unittest.TestCase):
    """The described function's shape on the shipped Core. The fork
    claims no family, so these cases exercise the records substrate
    its operation presupposes — results data arriving from partner
    sources as recorded ingestions, access to the consolidated
    dataset governed by purpose, and the consolidated set leaving
    under an export manifest — carried not claimed."""

    def test_results_ingestion_provenance_export_and_search(self):
        """A partner-results flow: a manual field-reports source is
        registered; a completed ingestion of 1,200 records and a
        failed one of 50 land; provenance counts completed runs
        only (1,200) and lists the source; an export of supplied
        result records carries the canonical checksum; catalog
        search finds the dataset by tag and by schema field name."""
        store, dataset = _results_store()
        source = store.register_source(
            "field-reports", "manual", STEWARD, location="partner-upload")
        store.record_ingestion(dataset["id"], source["id"], STEWARD,
                               record_count=1200)
        store.record_ingestion(dataset["id"], source["id"], STEWARD,
                               record_count=50, status="failed")
        prov = store.dataset_provenance(dataset["id"], VIEWER)
        self.assertEqual(prov["total_records"], 1200)
        self.assertEqual([s["id"] for s in prov["sources"]],
                         [source["id"]])
        records = [{"indicator": "households_reached", "value": 1200},
                   {"indicator": "sites_reporting", "value": 34}]
        manifest = store.export_dataset(dataset["id"], STEWARD,
                                        records=records)
        canonical = json.dumps(records, sort_keys=True,
                               separators=(",", ":"))
        self.assertEqual(
            manifest["checksum"],
            hashlib.sha256(canonical.encode("utf-8")).hexdigest())
        self.assertEqual(manifest["record_count"], 2)
        by_tag = store.search("field", VIEWER)
        self.assertEqual([d["id"] for d in by_tag["datasets"]],
                         [dataset["id"]])
        by_field = store.search("indicator", VIEWER)
        self.assertEqual([d["id"] for d in by_field["datasets"]],
                         [dataset["id"]])

    def test_access_to_results_dataset_is_never_self_approved(self):
        """Access governance in the fork's shape: carol requests
        access to the partner-results dataset for field reporting
        review; a decider carrying carol's own name in a role
        holding access_decide is denied by the self-approval guard
        (this is the assertion the group's guard mutant breaks) —
        the request stays 'requested' and no grant exists; bob the
        steward then approves and exactly one grant, to carol, is
        minted."""
        store, dataset = _results_store()
        req = store.request_access(dataset["id"],
                                   "field reporting review", VIEWER,
                                   duration_days=30)
        with self.assertRaises(PermissionDenied):
            store.decide_access_request(
                req["id"], True, User("carol", "steward"))
        self.assertEqual(
            store.get_access_request(req["id"], ADMIN)["status"],
            "requested")
        self.assertEqual(store.list_grants(dataset_id=dataset["id"],
                                           actor=ADMIN), [])
        decided = store.decide_access_request(req["id"], True, STEWARD)
        self.assertEqual(decided["status"], "approved")
        grants = store.list_grants(dataset_id=dataset["id"], actor=ADMIN)
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["grantee"], "carol")
        self.assertEqual(grants[0]["purpose"], "field reporting review")


if __name__ == "__main__":
    unittest.main()
