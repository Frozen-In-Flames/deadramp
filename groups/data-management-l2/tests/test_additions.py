"""Remainder additions — unit `addition:data-management-l2` (5 forks).

Traces to: ADDENDUM.md (the additions addendum to UNION-SPEC.md) and
remainder unit `addition:data-management-l2` in ../../remainder.json.
Two halves:

1. Spec integrity — the appended sheets are pinned literally: sheet
   count (8 original + 5 additions = 13), the original 8 fork IDs in
   shipped order, the additions in unit order, membership against
   remainder.json, the per-fork claim table under the group's
   19-family taxonomy applied verbatim, the zero-claim set, verbatim
   evidence, and the single-tier (Moderate / L2) invariant.
2. Substrate cases — each addition fork is exercised against the
   unchanged core surface its claims name (access governance for
   Collibra and IICS, sources/ingestion/provenance for DNAnexus,
   catalog search for OpenFLIS, ingestion + export-manifest records
   for Vaultara, which carries zero taxonomy claims and is pinned
   as such rather than hidden).
"""

import hashlib
import json
import os
import unittest

from datamgmt_helpers import ADMIN, STEWARD, VIEWER, fresh_store  # noqa: F401
from datamgmt.access import User
from datamgmt.errors import PermissionDenied

_SPECS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "specs", "specs.json")
_REMAINDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "..", "..", "remainder.json")

ORIGINAL_IDS = ['FR2128235497', 'FR1916254386', 'FR2522249893',
                'FR2128562231', 'FR2112152882', 'FR1724526654',
                'F1311222650', 'FR2531434700']
UNIT_IDS = ["FR1706403967", "FR1814557199", "FR2029331613",
            "FR1901136437", "FR2025456731"]
EXPECTED_CLAIMS = {
    "FR1706403967": ["workflow_automation"],          # Collibra CPG
    "FR1814557199": ["integration_exchange"],         # DNAnexus
    "FR2029331613": ["data_governance",               # Informatica IICS
                     "integration_exchange",
                     "query_reporting"],
    "FR1901136437": ["catalog_search"],               # OpenFLIS
    "FR2025456731": [],                               # Vaultara Flare
}
ZERO_CLAIM = {"FR2025456731"}


def _sheets():
    with open(_SPECS) as fh:
        return json.load(fh)


class TestAdditionSpecIntegrity(unittest.TestCase):
    """Addendum §1/§2: the appended sheets, pinned literally."""

    def test_sheet_count_and_order(self):
        """13 sheets: the original 8 in shipped order, then the unit's 5."""
        sheets = _sheets()
        self.assertEqual(len(sheets), 13)
        self.assertEqual([s["fork_id"] for s in sheets[:8]], ORIGINAL_IDS)
        self.assertEqual([s["fork_id"] for s in sheets[8:]], UNIT_IDS)

    def test_membership_matches_remainder_unit(self):
        """The additions are exactly remainder unit addition:data-management-l2."""
        with open(_REMAINDER) as fh:
            rem = json.load(fh)
        units = rem["build_units"]
        unit = [u for u in units if u["unit_id"] == "addition:data-management-l2"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], UNIT_IDS)
        self.assertEqual({s["fork_id"] for s in _sheets()[8:]},
                         set(unit[0]["fork_ids"]))

    def test_claim_table(self):
        """Per-fork claims under the verbatim taxonomy (addendum §2)."""
        for sheet in _sheets()[8:]:
            got = sorted(c["function_id"] for c in sheet["functions_claimed"])
            self.assertEqual(got, sorted(EXPECTED_CLAIMS[sheet["fork_id"]]),
                             sheet["fork_id"])

    def test_zero_claim_set(self):
        """Vaultara alone carries zero claims — pinned, not hidden."""
        zero = {s["fork_id"] for s in _sheets()[8:]
                if not s["functions_claimed"]}
        self.assertEqual(zero, ZERO_CLAIM)

    def test_group_totals(self):
        """34 claims over 13 forks; 12 of 13 forks carry at least one."""
        sheets = _sheets()
        self.assertEqual(sum(len(s["functions_claimed"]) for s in sheets), 34)
        self.assertEqual(
            sum(1 for s in sheets if s["functions_claimed"]), 12)

    def test_evidence_is_verbatim(self):
        """Every addition claim's evidence is a substring of its description."""
        for sheet in _sheets()[8:]:
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"],
                              (sheet["fork_id"], claim["function_id"]))

    def test_single_tier_and_category(self):
        """All additions are Moderate / L2 / Data Management (baseline unchanged)."""
        for sheet in _sheets()[8:]:
            self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
            self.assertEqual(sheet["cmmc_tier"], "L2")
            self.assertEqual(sheet["deadramp_category"], "Data Management")


class TestAdditionSubstrateCases(unittest.TestCase):
    """Addendum §2/§3: one substrate case per addition fork."""

    def test_collibra_approval_substrate_and_self_decision_denied(self):
        """Collibra claims workflow_automation; its Core side is the
        approval substrate: a request decided by another mints an
        active grant, and the requester's self-decision is denied
        (the group's negative-control seam, exercised for a newcomer)."""
        store = fresh_store()
        ds = store.create_dataset("Collibra Governed Catalog",
                                  "Governed data catalog records", STEWARD,
                                  classification="internal", tags=["collibra"])
        req = store.request_access(ds["id"], "catalog stewardship review",
                                   VIEWER, duration_days=10)
        with self.assertRaises(PermissionDenied):
            store.decide_access_request(req["id"], True, VIEWER)
        # The guard itself, isolated the way test_negative_control.py
        # isolates it: a name-identical decider holding access_decide
        # (carol-as-steward) is denied by _check_decider_not_requester
        # alone — this leg fails if that guard is mutated away.
        with self.assertRaises(PermissionDenied):
            store.decide_access_request(req["id"], True,
                                        User("carol", "steward"))
        decided = store.decide_access_request(req["id"], True, STEWARD,
                                              reason="approved")
        self.assertEqual(decided["status"], "approved")
        actives = store.active_grants(ds["id"], actor=STEWARD)
        self.assertEqual([g["id"] for g in actives], [decided["grant_id"]])

    def test_dnanexus_integration_substrate(self):
        """DNAnexus claims integration_exchange: registered sources,
        ingestion records, and the provenance view are its Core form."""
        store = fresh_store()
        ds = store.create_dataset("DNAnexus Analysis Results",
                                  "Molecular analysis result records", STEWARD,
                                  classification="phi", tags=["dnanexus"])
        src = store.register_source("lims-upstream", "api", STEWARD,
                                    location="lims.internal")
        ing = store.record_ingestion(ds["id"], src["id"], STEWARD,
                                     mode="incremental", record_count=42,
                                     checksum="ab12cd")
        self.assertEqual(ing["status"], "completed")
        prov = store.dataset_provenance(ds["id"], actor=STEWARD)
        self.assertEqual(prov["total_records"], 42)
        self.assertEqual([s["id"] for s in prov["sources"]], [src["id"]])

    def test_informatica_governance_search_and_quality(self):
        """IICS claims data_governance (Core), query_reporting (Core
        substrate), integration_exchange: governance flow, catalog
        search, and a deterministic quality check answer its claims."""
        store = fresh_store()
        ds = store.create_dataset("Informatica Governed Feed",
                                  "Integrated feed under governance", STEWARD,
                                  classification="cui", tags=["informatica"])
        req = store.request_access(ds["id"], "integration operations",
                                   VIEWER, duration_days=5)
        store.decide_access_request(req["id"], True, STEWARD)
        self.assertEqual(len(store.active_grants(ds["id"], actor=STEWARD)), 1)
        hits = store.search("informatica", actor=STEWARD)
        self.assertEqual([d["id"] for d in hits["datasets"]], [ds["id"]])
        rule = store.create_quality_rule(
            ds["id"], "amount present", "completeness", "amount", STEWARD)
        check = store.run_quality_check(
            rule["id"], [{"amount": 3}, {"amount": None}], STEWARD)
        self.assertEqual(check["violations"], 1)
        self.assertFalse(check["passed"])

    def test_openflis_catalog_search(self):
        """OpenFLIS claims catalog_search: literal metadata search
        finds its dataset by name token and by tag."""
        store = fresh_store()
        ds = store.create_dataset("OpenFLIS Logistics Index",
                                  "Collated logistics information index",
                                  STEWARD, classification="internal",
                                  tags=["openflis", "logistics"])
        by_name = store.search("openflis", actor=VIEWER)
        self.assertEqual([d["id"] for d in by_name["datasets"]], [ds["id"]])
        by_tag = store.search("LOGISTICS", actor=VIEWER)
        self.assertEqual([d["id"] for d in by_tag["datasets"]], [ds["id"]])

    def test_vaultara_transfer_records_despite_zero_claims(self):
        """Vaultara carries zero taxonomy claims (its transfer phrasing
        matches neither 'managed file transfer' nor 'MFT'); the
        transfer-shaped records it presupposes — ingestion with a
        checksum, and an export manifest over supplied records — are
        Core, and are exercised here under its own name."""
        store = fresh_store()
        ds = store.create_dataset("Vaultara Delivery Ledger",
                                  "Secure delivery records", STEWARD,
                                  classification="cui", tags=["vaultara"])
        src = store.register_source("vaultara-drop", "file", STEWARD,
                                    location="drop.internal")
        store.record_ingestion(ds["id"], src["id"], STEWARD,
                               record_count=2, checksum="ff00aa")
        records = [{"file": "a.pdf"}, {"file": "b.pdf"}]
        exp = store.export_dataset(ds["id"], STEWARD, format="json",
                                   records=records)
        canonical = json.dumps(records, sort_keys=True,
                               separators=(",", ":"))
        self.assertEqual(exp["checksum"],
                         hashlib.sha256(canonical.encode()).hexdigest())
        self.assertEqual(exp["record_count"], 2)


if __name__ == "__main__":
    unittest.main()
