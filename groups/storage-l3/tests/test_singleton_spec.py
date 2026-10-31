"""Singleton-spec tests: pin the Commvault spec sheet, the
zero-claim finding, and the carried-substrate cases.

Discipline under test:

- Group membership is exactly the census unit
  ``new-singleton:Storage|L3-adjacent`` = {FR2115384377}, the
  unit's ``extends_group`` is null (a new singleton), and the
  fork's recorded fields match forks.json.
- The honest zero: Commvault's description fires NO family of the
  category taxonomy after exclusion discipline. The description's
  five fragments include a workloads catalogue (fragment 2,
  marker "capabilities include the following workloads") which is
  excluded before matching; the raw-hit record in
  scratch/raw_hits.json shows exactly one raw hit -- "Active
  Directory" inside that catalogue, a protected-workload label,
  not unified-login integration -- removed by the exclusion, and
  zero kept hits. ``functions_claimed`` is pinned EMPTY.
- Verification != claim: the single census citation verifies
  strict-verbatim and is pinned as citation material, never claim
  evidence (scratch/citation_check.json: verbatim true,
  is_claim_evidence false, tags no family).
- The parent's named absences were rechecked against this fork's
  own words token-by-token (scratch/ARTIFACTS.md): the absence
  tokens pinned below are verified absent from THIS description.
  Two parent absences retire in SUBSTANCE here, on this fork's
  words -- backup (x1, with recovery x2: the headline function)
  and audit ("integrated audit reports") -- as baseline substrate,
  never as claims; both tokens are therefore deliberately NOT in
  the absent list.
- ZERO core function is claim-supported by this fork. The classes
  at the bottom pin substrate behavior only: "the substrate runs
  at the L3-adjacent tier," never "Commvault claims this."
"""

import ast
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from storage.errors import PermissionDenied, ValidationError  # noqa: E402

import storage_helpers as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

FORK_ID = "FR2115384377"
UNIT_ID = "new-singleton:Storage|L3-adjacent"
EXPECTED_FAMILIES = {
    "message_archiving", "storage_management", "retention",
    "search_discovery", "supervision", "policy_enforcement",
    "retrieval_export", "mail_platform_integration",
    "directory_integration", "message_encryption",
    "customer_key_custody",
}
# Tokens verified absent from THIS fork's description
# (scratch/ARTIFACTS.md). "backup" and "audit" are absent from
# this list on purpose: both occur (backup x1, audit x1) and their
# parent absences retire in substance, as substrate, not claims.
ABSENT_TOKENS = (
    "retention", "legal hold", "hold", "immutab", "worm", "fips",
    "supervision", "enforcement", "storage management", "searchable",
    "encrypt", "decrypt", "dedup", "compress", "tier", "version",
    "capacity", "journal", "migrat", "at rest", "snapshot",
    "replicat", "malware", "quota", "lifecycle", "ingest",
)


def load(rel):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


class SingletonSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheets = {s["fork_id"]: s
                      for s in json.loads(
                          (ROOT / "specs" / "specs.json").read_text(
                              encoding="utf-8"))}
        cls.registry = {row_id: row for row_id, row in
                        ((r["source_url"].rstrip("/").rsplit("/", 1)[-1], r)
                         for r in load("forks.json"))}
        cls.census = load("remainder.json")

    def test_membership_is_exactly_the_census_unit(self):
        units = {u["unit_id"]: u for u in self.census["build_units"]}
        unit = units[UNIT_ID]
        self.assertIsNone(unit["extends_group"])
        self.assertEqual(set(unit["fork_ids"]), {FORK_ID})
        self.assertEqual(set(self.sheets), {FORK_ID})

    def test_recorded_fields_match_registry(self):
        sheet = self.sheets[FORK_ID]
        row = self.registry[FORK_ID]
        self.assertEqual(sheet["vendor"], row["vendor"])
        self.assertEqual(sheet["product"], row["product"])
        self.assertEqual(sheet["vendor"], "Commvault Systems, Inc.")
        self.assertEqual(sheet["product"],
                         "Commvault Cloud for Government")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["fedramp_impact_level"], "High")
        self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["deadramp_category"], "Storage")
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_description_matches_source_verbatim(self):
        dump = load("raw/data_dump.json")
        (record,) = [r for r in
                     dump[3]["data"]["fedRAMPData"]["data"]["Products"]
                     if r.get("id") == FORK_ID]
        self.assertEqual(self.sheets[FORK_ID]["description"],
                         record["service_desc"])

    def test_zero_claims(self):
        """The honest zero: no family pattern fires on the kept
        fragments, so the claim table is empty -- pinned, not
        defaulted."""
        self.assertEqual(self.sheets[FORK_ID]["functions_claimed"], [])

    def test_taxonomy_is_the_parents_verbatim(self):
        """The spec ran under the founding taxonomy parsed (ast,
        never executed) out of the L2 extractor: the family universe
        is the parent's 11 families, unchanged."""
        source = (REPO / "groups" / "storage-l2" / "scratch"
                  / "extract.py").read_text(encoding="utf-8")
        taxonomy = None
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "TAXONOMY"
                    for t in node.targets):
                taxonomy = ast.literal_eval(node.value)
        self.assertIsNotNone(taxonomy)
        self.assertEqual({f for f, _label, _p in taxonomy},
                         EXPECTED_FAMILIES)

    def test_census_citation_verifies_but_is_not_a_claim(self):
        """Verification != claim: the single census citation verifies
        strict-verbatim against the description and is not evidence
        for any claim (there are none)."""
        check = json.loads(
            (ROOT / "scratch" / "citation_check.json").read_text(
                encoding="utf-8"))
        results = check[FORK_ID]
        self.assertEqual(len(results), 1)
        (result,) = results
        self.assertTrue(result["verbatim_in_description"])
        self.assertFalse(result["is_claim_evidence"])
        self.assertFalse(result["tags_a_family"])
        self.assertIn(result["citation"],
                      self.sheets[FORK_ID]["description"])

    def test_catalogue_hit_removed_by_exclusion(self):
        """The catalogue discipline, pinned from the raw-hit record:
        exactly one raw hit (directory_integration on "Active
        Directory"), inside excluded fragment 2; zero kept hits."""
        hits = json.loads(
            (ROOT / "scratch" / "raw_hits.json").read_text(
                encoding="utf-8"))[FORK_ID]
        self.assertEqual(hits["excluded_sentence_indices"], [2])
        self.assertEqual(len(hits["raw_hits_all_fragments"]), 1)
        self.assertEqual(len(hits["removed_hits"]), 1)
        self.assertEqual(hits["removed_hits"][0]["function_id"],
                         "directory_integration")
        self.assertEqual(hits["removed_hits"][0]["matched_text"],
                         "Active Directory")
        self.assertEqual(hits["kept_hits"], [])
        description = self.sheets[FORK_ID]["description"].lower()
        self.assertIn("active directory", description)
        self.assertIn("capabilities include the following workloads",
                      description)

    def test_checked_absences_hold(self):
        description = self.sheets[FORK_ID]["description"].lower()
        for token in ABSENT_TOKENS:
            self.assertNotIn(token, description, token)

    def test_retired_absences_occur_in_substance(self):
        """The two substance retirements, pinned at token level:
        "backup" and "audit" DO occur in this description -- that
        is exactly why their parent absences retire here, as
        substrate observations, while functions_claimed stays
        empty."""
        description = self.sheets[FORK_ID]["description"].lower()
        self.assertEqual(description.count("backup"), 1)
        self.assertEqual(description.count("recovery"), 2)
        self.assertEqual(description.count("audit"), 1)
        self.assertIn("integrated audit reports", description)


class CarriedSubstrateCaseTests(unittest.TestCase):
    """Substrate cases (NOT this fork's claims): the Storage L2
    substrate carried up whole under the Merge Rule and uplifted to
    the High baseline. Zero functions here are claim-supported by
    Commvault -- every case below pins "the substrate runs at this
    tier," never "Commvault claims this." """

    def setUp(self):
        self.store, self.audit = H.make_store()

    def test_custody_linked_archival_reaches_the_disposition_gate(self):
        """(a) The founding signature invariant runs at this tier: a
        custody-linked archival record derives "retained" before the
        boundary, an early disposition is refused, and a disposition
        at/after the boundary flips the derived state to "disposed".
        The stored record never carries a state field."""
        org, _policy, collection = H.make_archive(self.store)
        custody = H.make_custody(self.store, org, collection)
        message = H.make_message(self.store, collection,
                                 custody_id=custody["id"])
        before = self.store.get_message(H.ADMIN, message["id"],
                                        now=H.BEFORE_BOUNDARY)
        self.assertEqual(before["retention_state"], "retained")
        with self.assertRaises(ValidationError):
            self.store.record_disposition(H.ADMIN, message["id"], "shredded",
                                          at=H.BEFORE_BOUNDARY)
        self.store.record_disposition(H.ADMIN, message["id"], "shredded",
                                      at=H.AFTER_BOUNDARY)
        after = self.store.get_message(H.ADMIN, message["id"],
                                       now=H.BEFORE_BOUNDARY)
        self.assertEqual(after["retention_state"], "disposed")
        stored = self.store._messages[message["id"]]
        self.assertNotIn("retention_state", stored)
        self.assertNotIn("status", stored)

    def test_auditor_separation_at_store_level(self):
        """(b) AC-5 [L3]: the auditor reads the audit trail and can
        do nothing else -- no organization create, no record list."""
        H.make_archive(self.store)
        result = self.store.audit_read(H.AUDITOR)
        self.assertGreater(result["count"], 0)
        with self.assertRaises(PermissionDenied):
            self.store.create_organization(H.AUDITOR, "ORG-2", "Rogue")
        with self.assertRaises(PermissionDenied):
            self.store.list_organizations(H.AUDITOR)

    def test_audit_chain_verifies_after_a_flow(self):
        """(c) AU-9 [L3]: after a full carried-substrate flow the
        hash chain verifies clean."""
        org, _policy, collection = H.make_archive(self.store)
        custody = H.make_custody(self.store, org, collection)
        H.make_message(self.store, collection, custody_id=custody["id"])
        self.assertEqual(self.audit.verify_chain(), (True, None))


if __name__ == "__main__":
    unittest.main()
